#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5 MTKLOG管理器
适配原Tkinter版本的MTKLOG管理功能
"""

import subprocess
import os
import datetime
import time
import re
import sys
import shutil
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QMutex
from PyQt5.QtWidgets import QMessageBox, QInputDialog, QFileDialog, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDialogButtonBox, QFrame

# 导入资源工具
try:
    from core.resource_utils import get_aapt_path
except ImportError:
    # 如果导入失败，提供一个备用函数
    def get_aapt_path():
        return None

# 尝试导入apkutils库
try:
    from apkutils import APK
    APKUTILS_AVAILABLE = True
except ImportError:
    APKUTILS_AVAILABLE = False
    print("警告: apkutils库未安装，无法检查APK包名。请使用 'pip install apkutils' 安装。")

# 检测是否在PyInstaller打包环境中运行
def is_pyinstaller():
    """检测是否在PyInstaller打包环境中运行"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def get_device_chip_type(device):
    """
    检测设备的芯片类型
    
    Args:
        device: 设备ID或序列号
        
    Returns:
        str: "MTK" 或 "Qualcomm" 或 None（如果无法检测）
    """
    try:
        # 执行 adb shell getprop ro.hardware 命令
        cmd = ["adb", "-s", device, "shell", "getprop", "ro.hardware"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10,
                              creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
        
        if result.returncode != 0:
            return None
        
        hardware = result.stdout.strip().lower()
        
        # 检测高通芯片
        qualcomm_indicators = ["qcom", "msm", "sdm", "taro", "kalama", "pineapple"]
        if hardware.startswith("sm") or any(indicator in hardware for indicator in qualcomm_indicators):
            return "Qualcomm"
        
        # 检测MTK芯片
        if hardware.startswith("mt"):
            return "MTK"
        
        return None
    except Exception as e:
        print(f"检测芯片类型失败: {str(e)}")
        return None

def get_apk_package_name(apk_file_path):
    """
    获取APK文件的包名
    
    Args:
        apk_file_path: APK文件路径
        
    Returns:
        str: APK包名，如果无法获取则返回None
    """
    # 方法1: 尝试使用apkutils库
    if APKUTILS_AVAILABLE:
        try:
            # 尝试不同的导入方式
            try:
                from apkutils.apkfile import APKFile
                apk = APKFile(apk_file_path)
                package = apk.get_package()
                if package:
                    return package
            except (ImportError, AttributeError):
                pass
            
            try:
                # 尝试直接使用APK类
                apk = APK(apk_file_path)
                if hasattr(apk, 'package'):
                    return apk.package
                elif hasattr(apk, 'get_package'):
                    return apk.get_package()
            except Exception as e:
                print(f"apkutils获取包名失败: {str(e)}")
        except Exception as e:
            print(f"使用apkutils获取APK包名失败: {str(e)}")
    
    # 方法2: 尝试使用aapt工具（Android SDK的一部分）
    # 尝试多个aapt位置，按优先级顺序（打包的优先，如果失败则回退）
    aapt_candidates = []
    
    # 1. 优先使用打包的aapt.exe（在打包环境中应该总是存在）
    bundled_aapt = get_aapt_path()
    if bundled_aapt and os.path.exists(bundled_aapt):
        aapt_candidates.append(bundled_aapt)
    
    # 2. 系统PATH中的aapt
    if shutil.which("aapt"):
        aapt_candidates.append("aapt")
    
    # 3. Android SDK中的aapt.exe
    import glob
    sdk_paths = [
        os.path.join(os.environ.get("ANDROID_HOME", ""), "build-tools", "*", "aapt.exe"),
        os.path.join(os.environ.get("ANDROID_SDK_ROOT", ""), "build-tools", "*", "aapt.exe"),
    ]
    for pattern in sdk_paths:
        matches = glob.glob(pattern)
        if matches:
            aapt_candidates.extend(matches)
    
    # 依次尝试每个aapt，直到成功或全部失败
    for aapt_cmd in aapt_candidates:
        try:
            cmd = [aapt_cmd, "dump", "badging", apk_file_path]
            # 处理编码问题，使用二进制模式然后解码
            result = subprocess.run(cmd, capture_output=True, timeout=10,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode == 0:
                # 尝试多种编码解码
                stdout_text = None
                for encoding in ['utf-8', 'gbk', 'cp1252', 'latin-1']:
                    try:
                        stdout_text = result.stdout.decode(encoding, errors='ignore')
                        break
                    except:
                        continue
                
                if stdout_text:
                    for line in stdout_text.split('\n'):
                        if line.startswith('package: name='):
                            # 提取包名，格式: package: name='com.example.package' ...
                            try:
                                package = line.split("'")[1]
                                # 成功获取包名，返回结果
                                return package
                            except IndexError:
                                pass
        except FileNotFoundError:
            # 这个aapt不存在，尝试下一个
            continue
        except Exception as e:
            # 这个aapt执行失败，尝试下一个
            print(f"尝试使用 {aapt_cmd} 失败: {str(e)}")
            continue
    
    # 所有aapt都失败了
    print("所有aapt工具都无法使用，无法获取APK包名")
    
    return None

def check_logger_status(device, lang_manager):
    """检查logger状态的统一函数，兼容exe环境"""
    logger_is_running = False
    
    if U2_AVAILABLE:
        # 尝试使用UIAutomator2（在exe和非exe环境下都尝试）
        try:
            print(f"[DEBUG] {lang_manager.tr('尝试连接设备:')} {device}")
            d = u2.connect(device)
            print(f"[DEBUG] {lang_manager.tr('设备连接成功，查找按钮:')} com.debug.loggerui:id/startStopToggleButton")
            button = d(resourceId="com.debug.loggerui:id/startStopToggleButton")
            if button.exists:
                is_checked = button.info.get('checked', False)
                logger_is_running = is_checked
                print(f"[DEBUG] {lang_manager.tr('按钮存在，checked状态:')} {is_checked}, logger_is_running: {logger_is_running}")
            else:
                print(f"[DEBUG] {lang_manager.tr('按钮不存在，logger_is_running:')} {logger_is_running}")
        except Exception as e:
            print(f"[DEBUG] {lang_manager.tr('UIAutomator2连接失败:')} {str(e)}")
            print(f"{lang_manager.tr('警告:')} {lang_manager.tr('UIAutomator2不可用 -')} {str(e)}")
            print(f"{lang_manager.tr('提示:')} {lang_manager.tr('如果频繁出现此问题，建议重启手机后重试')}")
            
            # 如果UIAutomator2失败，在exe环境下假设logger正在运行
            if is_pyinstaller():
                print(f"[DEBUG] {lang_manager.tr('exe环境下UIAutomator2失败，假设logger正在运行')}")
                logger_is_running = True
            else:
                logger_is_running = False
    else:
        print(f"[DEBUG] {lang_manager.tr('UIAutomator2不可用')}")
        # 如果UIAutomator2不可用，在exe环境下假设logger正在运行
        if is_pyinstaller():
            print(f"[DEBUG] {lang_manager.tr('exe环境下UIAutomator2不可用，假设logger正在运行')}")
            logger_is_running = True
        else:
            logger_is_running = False
    
    return logger_is_running

def wait_for_logger_stop(device, progress_callback, tr_callback, max_wait_time=180):
    """等待logger停止的统一函数，兼容exe环境"""
    # 先等待2秒让logger有时间停止
    time.sleep(2)
    
    # 尝试使用UIAutomator2检查（在exe和非exe环境下都尝试）
    if U2_AVAILABLE:
        progress_callback(0, tr_callback("正在确认logger已完全停止..."))
        start_time = time.time()
        check_count = 0
        
        while time.time() - start_time < max_wait_time:
            check_count += 1
            elapsed_time = time.time() - start_time
            print(f"[DEBUG] {tr_callback('第')}{check_count}{tr_callback('次检查按钮状态，已等待')}{elapsed_time:.1f}{tr_callback('秒')}")
            
            try:
                d = u2.connect(device)
                button = d(resourceId="com.debug.loggerui:id/startStopToggleButton")
                if button.exists:
                    is_checked = button.info.get('checked', False)
                    print(f"[DEBUG] {tr_callback('按钮存在，checked状态:')} {is_checked}")
                    if not is_checked:
                        print(f"[DEBUG] {tr_callback('Logger已成功停止，checked=false')}")
                        break
                else:
                    print(f"[DEBUG] {tr_callback('按钮不存在')}")
            except Exception as e:
                print(f"[DEBUG] {tr_callback('检查按钮状态时出错:')} {str(e)}")
                # 如果UIAutomator2检查失败，在exe环境下等待固定时间后继续
                if is_pyinstaller():
                    print(f"[DEBUG] {tr_callback('exe环境下UIAutomator2检查失败，等待3秒后继续')}")
                    time.sleep(3)
                break
            time.sleep(1)
        
        final_elapsed = time.time() - start_time
        print(f"[DEBUG] {tr_callback('停止检查完成，总耗时:')} {final_elapsed:.1f}{tr_callback('秒，检查次数:')} {check_count}")
    else:
        # UIAutomator2不可用，根据环境选择等待时间
        if is_pyinstaller():
            print(f"[DEBUG] {tr_callback('exe环境下UIAutomator2不可用，等待5秒后继续')}")
            progress_callback(30, tr_callback("等待logger停止..."))
            time.sleep(5)
        else:
            print(f"[DEBUG] {tr_callback('UIAutomator2不可用，等待3秒后继续')}")
            progress_callback(30, tr_callback("等待logger停止..."))
            time.sleep(3)
    
    return True

# 尝试导入uiautomator2
try:
    import uiautomator2 as u2
    U2_AVAILABLE = True
except ImportError:
    u2 = None
    U2_AVAILABLE = False

def init_uiautomator2_for_exe(lang_manager=None):
    """在exe环境下初始化UIAutomator2"""
    if not is_pyinstaller() or not U2_AVAILABLE:
        return True
    
    try:
        # 在exe环境下，可能需要设置一些环境变量或路径
        import os
        import sys
        
        # 获取exe的临时目录
        if hasattr(sys, '_MEIPASS'):
            temp_dir = sys._MEIPASS
            print(f"[DEBUG] {lang_manager.tr('exe临时目录:') if lang_manager else 'exe临时目录:'} {temp_dir}")
            
            # 设置UIAutomator2相关的环境变量
            os.environ['UIAUTOMATOR2_TEMP_DIR'] = temp_dir
            
        return True
    except Exception as e:
        print(f"[DEBUG] {lang_manager.tr('exe环境下初始化UIAutomator2失败:') if lang_manager else 'exe环境下初始化UIAutomator2失败:'} {str(e)}")
        return False


class LogSizeDialog(QDialog):
    """Log大小设置对话框"""
    
    def __init__(self, device=None, parent=None):
        super().__init__(parent)
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.device = device
        self.setWindowTitle(self.tr("设置Log大小"))
        self.setModal(True)
        self.resize(400, 250)
        
        self.setup_ui()
        # 异步获取可用存储容量
        self.update_available_storage()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def get_available_storage(self):
        """获取设备可用存储容量（MB）"""
        if not self.device:
            return None
        
        try:
            # 执行 adb shell df /data 命令
            cmd = ["adb", "-s", self.device, "shell", "df", "/data"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                return None
            
            # 解析输出，提取可用容量
            # 输出格式类似：
            # Filesystem       1K-blocks     Used Available Use% Mounted on
            # /dev/block/dm-63 108259296 15264568  92457860  15% /storage/emulated/0/Android/obb
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                # 解析第二行，Available列是第4列（索引为3）
                parts = lines[1].split()
                if len(parts) >= 4:
                    # Available列的值单位是bytes，除以1024换算成MB
                    available_bytes = int(parts[3])
                    available_mb = available_bytes / 1024  # bytes除以1024得到MB
                    return int(available_mb)  # 转换为整数显示
            
            return None
        except (subprocess.TimeoutExpired, ValueError, IndexError, Exception) as e:
            print(f"[DEBUG] 获取可用存储容量失败: {str(e)}")
            return None
    
    def update_available_storage(self):
        """更新可用存储容量显示"""
        available_mb = self.get_available_storage()
        if available_mb is not None:
            self.storage_label.setText(self.tr("可用存储容量: {} MB").format(available_mb))
        else:
            self.storage_label.setText(self.tr("可用存储容量: 获取失败"))
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        
        # 可用存储容量显示
        storage_layout = QHBoxLayout()
        self.storage_label = QLabel(self.tr("可用存储容量: 正在获取..."))
        storage_layout.addWidget(self.storage_label)
        layout.addLayout(storage_layout)
        
        # 添加分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Modem Log
        modem_layout = QHBoxLayout()
        modem_layout.addWidget(QLabel("Modem Log (MB):"))
        self.modem_edit = QLineEdit()
        self.modem_edit.setText("20000")
        self.modem_edit.setPlaceholderText(self.tr("请输入Modem Log大小(MB)"))
        modem_layout.addWidget(self.modem_edit)
        layout.addLayout(modem_layout)
        
        # Mobile Log
        mobile_layout = QHBoxLayout()
        mobile_layout.addWidget(QLabel("Mobile Log (MB):"))
        self.mobile_edit = QLineEdit()
        self.mobile_edit.setText("2000")
        self.mobile_edit.setPlaceholderText(self.tr("请输入Mobile Log大小(MB)"))
        mobile_layout.addWidget(self.mobile_edit)
        layout.addLayout(mobile_layout)
        
        # Netlog
        netlog_layout = QHBoxLayout()
        netlog_layout.addWidget(QLabel("Netlog (MB):"))
        self.netlog_edit = QLineEdit()
        self.netlog_edit.setText("3000")
        self.netlog_edit.setPlaceholderText(self.tr("请输入Netlog大小(MB)"))
        netlog_layout.addWidget(self.netlog_edit)
        layout.addLayout(netlog_layout)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_values(self):
        """获取输入的三个值"""
        try:
            modem = int(self.modem_edit.text())
            mobile = int(self.mobile_edit.text())
            netlog = int(self.netlog_edit.text())
            return modem, mobile, netlog
        except ValueError:
            return None, None, None


class MTKLogWorker(QThread):
    """MTKLOG工作线程"""
    
    finished = pyqtSignal(bool, str)  # success, message
    progress = pyqtSignal(int, str)   # progress, status
    
    def __init__(self, device, operation, device_manager, parent=None, log_name=None, export_media=False, storage_path_func=None, should_record=False):
        super().__init__(parent)
        self.device = device
        self.operation = operation
        self.device_manager = device_manager
        self.log_name = log_name
        self.export_media = export_media
        self.storage_path_func = storage_path_func  # 存储路径获取函数
        self.should_record = should_record  # 是否在logger启动成功后录制视频
        self._mutex = QMutex()
        self._stop_requested = False
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        
        # 在exe环境下初始化UIAutomator2
        if is_pyinstaller():
            init_uiautomator2_for_exe(self.lang_manager)
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
        
    def run(self):
        """执行MTKLOG操作"""
        try:
            if self.operation == 'start':
                self._start_mtklog()
            elif self.operation == 'stop_export':
                self._stop_and_export_mtklog(self.log_name, self.export_media)
            elif self.operation == 'stop':
                self._stop_mtklog()
            elif self.operation == 'delete':
                self._delete_mtklog()
        except Exception as e:
            self.finished.emit(False, f"{self.lang_manager.tr('操作失败:')} {str(e)}")
    
    def _start_mtklog(self):
        """开启MTKLOG"""
        try:
            # 1. 确保屏幕亮屏且解锁
            self.progress.emit(0, self.tr("检查屏幕状态..."))
            if not self.device_manager.ensure_screen_unlocked(self.device):
                raise Exception(self.lang_manager.tr("无法确保屏幕状态"))
            
            # 2. 启动logger应用
            self.progress.emit(0, self.tr("启动logger应用..."))
            start_app_cmd = ["adb", "-s", self.device, "shell", "am", "start", "-n", "com.debug.loggerui/.MainActivity"]
            result = subprocess.run(start_app_cmd, capture_output=True, text=True, timeout=30,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            if result.returncode != 0:
                print(f"{self.lang_manager.tr('警告:')} {self.lang_manager.tr('启动logger应用失败:')} {result.stderr.strip()}")
            time.sleep(2)
            
            # 3. 检查logger状态
            self.progress.emit(0, self.tr("检查logger状态..."))
            logger_is_running = check_logger_status(self.device, self.lang_manager)
            
            # 4. 如果logger正在运行，先停止
            if logger_is_running:
                self.progress.emit(0, self.tr("停止logger..."))
                stop_cmd = ["adb", "-s", self.device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                           "-e", "cmd_name", "stop", "--ei", "cmd_target", "-1", "-n", "com.debug.loggerui/.framework.LogReceiver"]
                
                result = subprocess.run(stop_cmd, capture_output=True, text=True, timeout=15,
                                      creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                if result.returncode != 0:
                    raise Exception(f"{self.lang_manager.tr('停止logger失败:')} {result.stderr.strip()}")
                
                # 5. 等待2秒后检查按钮状态
                self.progress.emit(0, self.tr("等待logger停止..."))
                time.sleep(2)
                
                # 6. 检查按钮checked是否为false
                self.progress.emit(0, self.tr("正在确认logger已完全停止..."))
                max_wait_time = 120
                start_time = time.time()
                while time.time() - start_time < max_wait_time:
                    if U2_AVAILABLE:
                        try:
                            d = u2.connect(self.device)
                            button = d(resourceId="com.debug.loggerui:id/startStopToggleButton")
                            if button.exists:
                                is_checked = button.info.get('checked', False)
                                if not is_checked:
                                    break
                        except Exception as e:
                            break
                    time.sleep(1)
            
            # 7. 清除旧日志
            self.progress.emit(0, self.tr("清除旧日志..."))
            clear_cmd = ["adb", "-s", self.device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                        "-e", "cmd_name", "clear_logs_all", "--ei", "cmd_target", "0", "-n", "com.debug.loggerui/.framework.LogReceiver"]
            
            result = subprocess.run(clear_cmd, capture_output=True, text=True, timeout=15,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            if result.returncode != 0:
                raise Exception(f"{self.lang_manager.tr('清除旧日志失败:')} {result.stderr.strip()}")
            
            # 等待3秒确保清除完毕
            time.sleep(3)
            
            # 8. 设置MD log缓存大小20GB
            self.progress.emit(0, self.tr("设置缓存大小..."))
            size_cmd = ["adb", "-s", self.device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                       "-e", "cmd_name", "set_log_size_20000", "--ei", "cmd_target", "2", "-n", "com.debug.loggerui/.framework.LogReceiver"]
            
            result = subprocess.run(size_cmd, capture_output=True, text=True, timeout=15,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            if result.returncode != 0:
                raise Exception(f"{self.lang_manager.tr('设置缓存大小失败:')} {result.stderr.strip()}")
            
            # 9. 开启MTK LOGGER
            self.progress.emit(0, self.tr("开启logger..."))
            start_cmd = ["adb", "-s", self.device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                        "-e", "cmd_name", "start", "--ei", "cmd_target", "-1", "-n", "com.debug.loggerui/.framework.LogReceiver"]
            
            result = subprocess.run(start_cmd, capture_output=True, text=True, timeout=15,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            if result.returncode != 0:
                raise Exception(f"{self.lang_manager.tr('开启logger失败:')} {result.stderr.strip()}")
            
            # 10. 等待"Starting logs"对话框消失
            self.progress.emit(0, self.tr("等待logger启动..."))
            max_wait_time = 120
            start_time = time.time()
            dialog_appeared = False
            initial_wait_time = 5
            
            while time.time() - start_time < max_wait_time:
                if U2_AVAILABLE:
                    try:
                        d = u2.connect(self.device)
                        alert_title = d(resourceId="android:id/alertTitle", text="Starting logs")
                        if alert_title.exists:
                            if not dialog_appeared:
                                dialog_appeared = True
                        elif dialog_appeared and not alert_title.exists:
                            break
                        elif not dialog_appeared and (time.time() - start_time) > initial_wait_time:
                            break
                    except Exception as e:
                        break
                time.sleep(1)
            
            # 11. 检查按钮checked是否为true
            self.progress.emit(0, self.tr("正在确认logger已完全启动..."))
            start_time = time.time()
            logger_started = False
            while time.time() - start_time < max_wait_time:
                if U2_AVAILABLE:
                    try:
                        d = u2.connect(self.device)
                        button = d(resourceId="com.debug.loggerui:id/startStopToggleButton")
                        if button.exists:
                            is_checked = button.info.get('checked', False)
                            if is_checked:
                                logger_started = True
                                break
                    except Exception as e:
                        break
                time.sleep(1)
            
            # 12. 如果用户同意录制，在确认logger启动成功后开始录制
            if logger_started and self.should_record:
                self.progress.emit(0, self.tr("开始录制视频..."))
                try:
                    video_manager = self.parent().get_video_manager() if self.parent() and hasattr(self.parent(), 'get_video_manager') else None
                    if video_manager and not video_manager.is_recording:
                        video_manager.start_recording()
                except Exception as e:
                    print(f"{self.lang_manager.tr('警告:')} {self.lang_manager.tr('开始录制视频失败:')} {str(e)}")
            
            self.progress.emit(0, self.tr("完成!"))
            self.finished.emit(True, self.tr("MTKLOG启动成功"))
            
        except Exception as e:
            self.finished.emit(False, f"{self.lang_manager.tr('启动MTKLOG失败:')} {str(e)}")
    
    def _stop_and_export_mtklog(self, log_name, export_media):
        """停止并导出MTKLOG"""
        try:
            print(f"[DEBUG] {self.tr('开始停止并导出MTKLOG操作，设备:')} {self.device}{self.tr(', 日志名称:')} {log_name}{self.tr(', 导出媒体:')} {export_media}")
            
            # 1. 检查并停止screenrecord进程（通过video_manager）
            self.progress.emit(0, self.tr("检查并停止视频录制进程..."))
            try:
                # 首先尝试通过video_manager停止录制
                # MTKLogWorker的parent是PyQtMTKLogManager，PyQtMTKLogManager的parent是主窗口
                mtklog_manager = self.parent()
                video_manager = None
                if mtklog_manager and hasattr(mtklog_manager, 'get_video_manager'):
                    video_manager = mtklog_manager.get_video_manager()
                
                if video_manager and video_manager.is_recording:
                    print(f"[DEBUG] {self.tr('检测到video_manager正在录制，调用stop_recording()停止录制')}")
                    video_manager.stop_recording()
                    # 记录video_manager的引用，后续用于移动视频文件
                    self._video_manager = video_manager
                    
                    # 智能等待视频保存完成
                    print(f"[DEBUG] {self.tr('等待视频保存完成...')}")
                    video_storage_path = video_manager.get_storage_path()
                    default_video_dir = os.path.join(video_storage_path, "video")
                    
                    # 等待录制状态变为False（最多等待3秒）
                    check_interval = 0.5
                    waited_time = 0
                    while video_manager.is_recording and waited_time < 3:
                        time.sleep(check_interval)
                        waited_time += check_interval
                    
                    # 等待视频文件出现在目录中，并检查文件大小是否稳定
                    max_wait_seconds = 30
                    waited_time = 0
                    video_files_found = False
                    
                    while waited_time < max_wait_seconds:
                        if os.path.exists(default_video_dir):
                            video_files = [f for f in os.listdir(default_video_dir) if f.endswith('.mp4')]
                            if video_files:
                                # 检查文件大小是否稳定（连续两次检查文件大小不变）
                                time.sleep(1)
                                file_stable = True
                                file_sizes = {}
                                for filename in video_files:
                                    file_path = os.path.join(default_video_dir, filename)
                                    if os.path.exists(file_path):
                                        file_sizes[filename] = os.path.getsize(file_path)
                                
                                # 再等待1秒，检查文件大小是否变化
                                time.sleep(1)
                                for filename, size_before in file_sizes.items():
                                    file_path = os.path.join(default_video_dir, filename)
                                    if os.path.exists(file_path):
                                        size_after = os.path.getsize(file_path)
                                        if size_before != size_after:
                                            file_stable = False
                                            break
                                    else:
                                        file_stable = False
                                        break
                                
                                if file_stable:
                                    video_files_found = True
                                    print(f"[DEBUG] {self.tr('检测到视频文件已保存完成:')} {len(video_files)} {self.tr('个文件')}")
                                    break
                        
                        time.sleep(check_interval)
                        waited_time += check_interval
                        if int(waited_time) % 5 == 0 and waited_time > 0:
                            print(f"[DEBUG] {self.tr('等待视频保存中...')} ({int(waited_time)}s)")
                    
                    if not video_files_found:
                        print(f"[DEBUG] {self.tr('等待视频保存超时，继续执行后续流程')}")
                else:
                    # 如果没有通过video_manager管理，检查是否有screenrecord进程，使用kill停止
                    ps_cmd = ["adb", "-s", self.device, "shell", "ps", "-A"]
                    result = subprocess.run(ps_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30,
                                          creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                    
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        screenrecord_found = False
                        for line in lines:
                            if 'screenrecord' in line and 'grep' not in line:
                                parts = line.split()
                                if len(parts) >= 2:
                                    pid = parts[1]
                                    screenrecord_found = True
                                    print(f"[DEBUG] {self.tr('找到screenrecord进程，但video_manager未管理，使用kill停止 PID:')} {pid}")
                                    kill_cmd = ["adb", "-s", self.device, "shell", "kill", "-9", pid]
                                    kill_result = subprocess.run(kill_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30,
                                                              creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                                    if kill_result.returncode == 0:
                                        print(f"[DEBUG] {self.tr('成功停止screenrecord进程 PID:')} {pid}")
                                    else:
                                        print(f"[DEBUG] {self.tr('停止screenrecord进程 PID')} {pid} {self.tr('失败:')} {kill_result.stderr.strip()}")
                                    time.sleep(1)
                        
                        if not screenrecord_found:
                            print(f"[DEBUG] {self.tr('未检测到screenrecord进程')}")
            except Exception as e:
                print(f"[DEBUG] {self.tr('检查screenrecord进程时出错:')} {str(e)}")
                # 继续执行，不因检查失败而中断
            
            # 2. 确保屏幕亮屏且解锁
            self.progress.emit(0, self.tr("检查屏幕状态..."))
            if not self.device_manager.ensure_screen_unlocked(self.device):
                raise Exception(self.lang_manager.tr("无法确保屏幕状态"))
            print(f"[DEBUG] {self.tr('屏幕状态检查完成')}")
            
            # 2. 启动logger应用
            self.progress.emit(0, self.tr("启动logger应用..."))
            start_app_cmd = ["adb", "-s", self.device, "shell", "am", "start", "-n", "com.debug.loggerui/.MainActivity"]
            print(f"[DEBUG] {self.tr('启动logger应用命令:')} {' '.join(start_app_cmd)}")
            result = subprocess.run(start_app_cmd, capture_output=True, text=True, timeout=30,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            print(f"[DEBUG] {self.tr('启动应用结果 - returncode:')} {result.returncode}, stdout: {result.stdout.strip()}, stderr: {result.stderr.strip()}")
            if result.returncode != 0:
                print(f"{self.lang_manager.tr('警告:')} {self.lang_manager.tr('启动logger应用失败:')} {result.stderr.strip()}")
            time.sleep(2)
            
            # 3. 检查logger状态
            self.progress.emit(0, self.tr("检查logger状态..."))
            logger_is_running = check_logger_status(self.device, self.lang_manager)
            
            # 4. 如果logger正在运行，执行停止命令
            if logger_is_running:
                print(f"[DEBUG] {self.tr('Logger正在运行，开始执行停止命令')}")
                self.progress.emit(0, self.tr("停止logger..."))
                stop_cmd = ["adb", "-s", self.device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                           "-e", "cmd_name", "stop", "--ei", "cmd_target", "-1", "-n", "com.debug.loggerui/.framework.LogReceiver"]
                
                print(f"[DEBUG] {self.tr('执行停止命令:')} {' '.join(stop_cmd)}")
                result = subprocess.run(stop_cmd, capture_output=True, text=True, timeout=15,
                                      creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                print(f"[DEBUG] {self.tr('停止命令执行结果 - returncode:')} {result.returncode}")
                print(f"[DEBUG] {self.tr('停止命令stdout:')} {result.stdout.strip()}")
                print(f"[DEBUG] {self.tr('停止命令stderr:')} {result.stderr.strip()}")
                
                if result.returncode != 0:
                    raise Exception(f"{self.lang_manager.tr('停止logger失败:')} {result.stderr.strip()}")
                
                # 5. 等待2秒后检查按钮状态
                self.progress.emit(0, self.tr("等待logger停止..."))
                time.sleep(2)
                
                # 6. 等待logger停止（使用统一函数）
                wait_for_logger_stop(self.device, self.progress.emit, self.tr)
            else:
                print(f"[DEBUG] {self.tr('Logger未在运行，跳过停止操作')}")
            
            # 8. 创建日志目录
            self.progress.emit(0, self.tr("创建日志目录..."))
            curredate = datetime.datetime.now().strftime("%Y%m%d")
            if self.storage_path_func:
                log_dir = self.storage_path_func()
            else:
                log_dir = f"c:\\log\\{curredate}"
            log_folder = f"{log_dir}\\log_{log_name}"
            print(f"[DEBUG] {self.tr('创建日志目录:')} {log_folder}")
            
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                print(f"[DEBUG] {self.tr('创建目录:')} {log_dir}")
            else:
                print(f"[DEBUG] {self.tr('目录已存在:')} {log_dir}")
            
            # 确保log_folder（一级目录）存在
            if not os.path.exists(log_folder):
                os.makedirs(log_folder)
                print(f"[DEBUG] {self.tr('创建日志文件夹:')} {log_folder}")
            else:
                print(f"[DEBUG] {self.tr('日志文件夹已存在:')} {log_folder}")
            
            # 8.1 如果有视频录制，将视频文件移动到log文件夹
            if hasattr(self, '_video_manager') and self._video_manager:
                try:
                    self.progress.emit(0, self.tr("移动视频文件到log文件夹..."))
                    # 获取默认的视频目录
                    video_storage_path = self._video_manager.get_storage_path()
                    default_video_dir = os.path.join(video_storage_path, "video")
                    
                    # 目标视频目录（在log文件夹内）
                    target_video_dir = os.path.join(log_folder, "video")
                    
                    if os.path.exists(default_video_dir):
                        # 查找所有视频文件
                        video_files = []
                        for filename in os.listdir(default_video_dir):
                            if filename.endswith('.mp4'):
                                video_files.append(filename)
                        
                        if video_files:
                            # 创建目标视频目录
                            if not os.path.exists(target_video_dir):
                                os.makedirs(target_video_dir)
                                print(f"[DEBUG] {self.tr('创建目标视频目录:')} {target_video_dir}")
                            
                            # 移动视频文件
                            moved_count = 0
                            for filename in video_files:
                                source_path = os.path.join(default_video_dir, filename)
                                target_path = os.path.join(target_video_dir, filename)
                                try:
                                    shutil.move(source_path, target_path)
                                    print(f"[DEBUG] {self.tr('移动视频文件:')} {filename} -> {target_path}")
                                    moved_count += 1
                                except Exception as e:
                                    print(f"[DEBUG] {self.tr('移动视频文件失败:')} {filename}, {str(e)}")
                            
                            if moved_count > 0:
                                print(f"[DEBUG] {self.tr('成功移动')} {moved_count} {self.tr('个视频文件到log文件夹')}")
                            
                            # 如果源目录为空，尝试删除
                            try:
                                if not os.listdir(default_video_dir):
                                    os.rmdir(default_video_dir)
                                    print(f"[DEBUG] {self.tr('删除空的视频目录:')} {default_video_dir}")
                            except:
                                pass
                        else:
                            print(f"[DEBUG] {self.tr('默认视频目录中没有找到视频文件')}")
                    else:
                        print(f"[DEBUG] {self.tr('默认视频目录不存在，跳过移动操作')}")
                except Exception as e:
                    print(f"[DEBUG] {self.tr('移动视频文件时出错:')} {str(e)}")
                    # 不影响后续流程，继续执行
            
            # 9. 执行adb pull命令序列
            pull_commands = [
                ("/sdcard/TCTReport", "TCTReport"),
                ("/data/user_de/0/com.android.shell/files/bugreports/", "bugreports"),
                ("/sdcard/Android/data/com.tmobile.echolocate/cache/dia_debug", "echolocate_dia_debug"),
                ("/sdcard/mtklog", "mtklog"),
                ("/sdcard/logmanager", "logmanager"),
                ("/sdcard/BugReport", "BugReport"),
                ("/data/media/logmanager", "logmanager")
            ]
            
            # 如果用户选择导出媒体文件，添加媒体文件命令（在debuglogger之前）
            if export_media:
                media_commands = [
                    ("/sdcard/DCIM/Screen Recorder/.", "Screen_Recorder_DCIM"),
                    ("/sdcard/Screen Recorder/.", "Screen_Recorder"),
                    ("/storage/emulated/0/Screen Recorder/.", "Screen_Recorder_Storage"),
                    ("/sdcard/DCIM/ViewMe/.", "ViewMe_DCIM"),
                    ("/storage/emulated/0/Pictures/Screenshots/.", "Screenshots_Storage"),
                    ("/sdcard/Pictures/Screenshots/.", "Screenshots_DCIM")
                ]
                pull_commands.extend(media_commands)
            
            # 将debuglogger相关的文件夹放到最后（最容易超时的文件夹）
            debuglogger_commands = [
                ("/sdcard/debuglogger", "debuglogger"),
                ("/data/debuglogger", "debuglogger")
            ]
            pull_commands.extend(debuglogger_commands)
            
            total_commands = len(pull_commands)
            
            for i, (source_path, folder_name) in enumerate(pull_commands):
                try:
                    print(f"[DEBUG] {self.tr('检查文件夹:')} {source_path} -> {folder_name}")
                    
                    # 先检查文件夹是否存在
                    check_cmd = ["adb", "-s", self.device, "shell", "test", "-d", source_path]
                    check_result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=10,
                                                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                    print(f"[DEBUG] {self.tr('检查命令结果 - returncode:')} {check_result.returncode}, stdout: {check_result.stdout.strip()}, stderr: {check_result.stderr.strip()}")
                    
                    if check_result.returncode != 0:
                        print(f"[DEBUG] {self.tr('文件夹不存在，跳过:')} {source_path}")
                        # 对于bugreports路径，额外检查权限问题
                        if "bugreports" in source_path:
                            print(f"[DEBUG] {self.tr('尝试检查bugreports路径权限:')} {source_path}")
                            ls_cmd = ["adb", "-s", self.device, "shell", "ls", "-la", "/data/user_de/0/com.android.shell/files/"]
                            ls_result = subprocess.run(ls_cmd, capture_output=True, text=True, timeout=10,
                                                      creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                            print(f"[DEBUG] {self.tr('目录列表结果:')} {ls_result.stdout.strip()}")
                        continue
                    
                    # 文件夹存在，执行pull
                    self.progress.emit(0, f"{self.lang_manager.tr('正在导出')} {folder_name} ({i+1}/{total_commands})...")
                    target_path = os.path.join(log_folder, folder_name)
                    cmd = ["adb", "-s", self.device, "pull", source_path, target_path]
                    print(f"[DEBUG] {self.tr('执行pull命令:')} {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=6000,
                                          creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                    print(f"[DEBUG] {self.tr('Pull命令结果 - returncode:')} {result.returncode}, stdout: {result.stdout.strip()}, stderr: {result.stderr.strip()}")
                    
                    if result.returncode != 0:
                        print(f"{self.lang_manager.tr('警告:')} {folder_name} {self.lang_manager.tr('导出失败:')} {result.stderr.strip()}")
                    else:
                        print(f"[DEBUG] {folder_name} {self.tr('导出成功')}")
                        
                except subprocess.TimeoutExpired:
                    print(f"{self.lang_manager.tr('错误:')} {folder_name} {self.lang_manager.tr('导出超时，跳过')}")
                    continue
                except Exception as e:
                    print(f"{self.lang_manager.tr('错误:')} {folder_name} {self.lang_manager.tr('导出异常:')} {str(e)}")
                    continue
            
            print(f"[DEBUG] {self.tr('MTKLOG停止并导出操作完成，导出路径:')} {log_folder}")
            self.progress.emit(0, self.tr("完成!"))
            self.finished.emit(True, log_folder)
            
        except Exception as e:
            print(f"[DEBUG] {self.tr('MTKLOG停止并导出操作异常:')} {str(e)}")
            self.finished.emit(False, f"{self.lang_manager.tr('导出MTKLOG失败:')} {str(e)}")
    
    def _stop_mtklog(self):
        """停止MTKLOG（不导出）"""
        try:
            print(f"[DEBUG] {self.tr('开始停止MTKLOG操作，设备:')} {self.device}")
            
            # 1. 确保屏幕亮屏且解锁
            self.progress.emit(0, self.tr("检查屏幕状态..."))
            if not self.device_manager.ensure_screen_unlocked(self.device):
                raise Exception(self.lang_manager.tr("无法确保屏幕状态"))
            print(f"[DEBUG] {self.tr('屏幕状态检查完成')}")
            
            # 2. 启动logger应用
            self.progress.emit(0, self.tr("启动logger应用..."))
            start_app_cmd = ["adb", "-s", self.device, "shell", "am", "start", "-n", "com.debug.loggerui/.MainActivity"]
            print(f"[DEBUG] {self.tr('启动logger应用命令:')} {' '.join(start_app_cmd)}")
            result = subprocess.run(start_app_cmd, capture_output=True, text=True, timeout=30,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            print(f"[DEBUG] {self.tr('启动应用结果 - returncode:')} {result.returncode}, stdout: {result.stdout.strip()}, stderr: {result.stderr.strip()}")
            if result.returncode != 0:
                print(f"{self.lang_manager.tr('警告:')} {self.lang_manager.tr('启动logger应用失败:')} {result.stderr.strip()}")
            time.sleep(2)
            
            # 3. 检查logger状态
            self.progress.emit(0, self.tr("检查logger状态..."))
            logger_is_running = check_logger_status(self.device, self.lang_manager)
            
            # 4. 如果logger正在运行，执行停止命令
            if logger_is_running:
                print(f"[DEBUG] {self.tr('Logger正在运行，开始执行停止命令')}")
                self.progress.emit(0, self.tr("停止logger..."))
                stop_cmd = ["adb", "-s", self.device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                           "-e", "cmd_name", "stop", "--ei", "cmd_target", "-1", "-n", "com.debug.loggerui/.framework.LogReceiver"]
                
                print(f"[DEBUG] {self.tr('执行停止命令:')} {' '.join(stop_cmd)}")
                result = subprocess.run(stop_cmd, capture_output=True, text=True, timeout=15,
                                      creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                print(f"[DEBUG] {self.tr('停止命令执行结果 - returncode:')} {result.returncode}")
                print(f"[DEBUG] {self.tr('停止命令stdout:')} {result.stdout.strip()}")
                print(f"[DEBUG] {self.tr('停止命令stderr:')} {result.stderr.strip()}")
                
                if result.returncode != 0:
                    raise Exception(f"{self.lang_manager.tr('停止logger失败:')} {result.stderr.strip()}")
                
                # 5. 等待2秒后检查按钮状态
                self.progress.emit(0, self.tr("等待logger停止..."))
                time.sleep(2)
                
                # 6. 等待logger停止（使用统一函数）
                wait_for_logger_stop(self.device, self.progress.emit, self.tr)
            else:
                print(f"[DEBUG] {self.tr('Logger未在运行，跳过停止操作')}")
                self.progress.emit(0, self.tr("Logger已处于停止状态..."))
            
            print(f"[DEBUG] {self.tr('MTKLOG停止操作完成')}")
            self.progress.emit(0, self.tr("完成!"))
            self.finished.emit(True, self.tr("MTKLOG已停止"))
            
        except Exception as e:
            print(f"[DEBUG] {self.tr('MTKLOG停止操作异常:')} {str(e)}")
            self.finished.emit(False, f"{self.lang_manager.tr('停止MTKLOG失败:')} {str(e)}")
    
    def _delete_mtklog(self):
        """删除MTKLOG"""
        try:
            self.progress.emit(0, self.tr("执行删除命令..."))
            cmd = ["adb", "-s", self.device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                   "-e", "cmd_name", "clear_logs_all", "--ei", "cmd_target", "0", "-n", "com.debug.loggerui/.framework.LogReceiver"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else self.lang_manager.tr("未知错误")
                raise Exception(f"{self.lang_manager.tr('删除MTKLOG失败:')} {error_msg}")
            
            self.progress.emit(0, self.tr("删除完成!"))
            self.finished.emit(True, self.tr("MTKLOG已删除"))
        except Exception as e:
            self.finished.emit(False, f"{self.lang_manager.tr('删除MTKLOG失败:')} {str(e)}")

class PyQtMTKLogManager(QObject):
    """PyQt5 MTKLOG管理器"""
    
    # 信号定义
    mtklog_started = pyqtSignal()
    mtklog_stopped = pyqtSignal()
    mtklog_deleted = pyqtSignal()
    mtklog_exported = pyqtSignal(str)  # export_path
    progress_updated = pyqtSignal(int, str)  # progress, status
    status_message = pyqtSignal(str)
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.worker = None
        self.is_running = False
    
    def get_video_manager(self):
        """获取视频管理器"""
        if self.parent() and hasattr(self.parent(), 'video_manager'):
            return self.parent().video_manager
        return None
    
    def get_storage_path(self):
        """获取存储路径，优先使用用户配置的路径"""
        # 从父窗口获取工具配置
        if hasattr(self.parent(), 'tool_config') and self.parent().tool_config:
            storage_path = self.parent().tool_config.get("storage_path", "")
            if storage_path:
                return storage_path
        
        # 使用默认路径
        current_date = datetime.datetime.now().strftime("%Y%m%d")
        return f"c:\\log\\{current_date}"
        
    def start_mtklog(self):
        """开启MTKLOG"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 检查MTKLOGGER是否存在
        if not self._check_mtklogger_exists(device):
            self.status_message.emit(self.lang_manager.tr("未检测到MTKLOGGER，请先安装"))
            return
        
        # 询问用户是否需要录制视频
        video_manager = self.get_video_manager()
        should_record = False
        if video_manager:
            reply = QMessageBox.question(
                None,
                self.lang_manager.tr("开始录制视频"),
                (self.lang_manager.tr("是否在MTKLOG启动成功后开始录制视频？\n\n") +
                 self.lang_manager.tr("注意：录制视频过程中USB连接不能断开。")),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            should_record = (reply == QMessageBox.Yes)
        
        # 创建工作线程
        self.worker = MTKLogWorker(device, 'start', self.device_manager, self, storage_path_func=self.get_storage_path, should_record=should_record)
        self.worker.progress.connect(self.progress_updated.emit)
        self.worker.finished.connect(self._on_mtklog_started)
        self.is_running = True
        self.worker.start()
        
    def stop_and_export_mtklog(self):
        """停止并导出MTKLOG"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 获取日志名称
        log_name, ok = QInputDialog.getText(
            None,
            self.lang_manager.tr("输入日志名称"),
            self.lang_manager.tr("请输入日志名称:")
        )
        if not ok or not log_name:
            return
        
        # 询问是否导出截图和视频
        reply = QMessageBox.question(
            None,
            self.lang_manager.tr("导出媒体文件"),
            (self.lang_manager.tr("是否导出手机录制的视频和截图？\n\n") +
             self.lang_manager.tr("选择") + self.lang_manager.tr("是") + self.lang_manager.tr("将导出这些媒体文件。")),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        export_media = (reply == QMessageBox.Yes)
        
        # 创建工作线程
        self.worker = MTKLogWorker(device, 'stop_export', self.device_manager, self, log_name=log_name, export_media=export_media, storage_path_func=self.get_storage_path)
        self.worker.progress.connect(self.progress_updated.emit)
        self.worker.finished.connect(self._on_mtklog_stopped)
        self.is_running = True
        self.worker.start()
        
    def stop_mtklog(self):
        """停止MTKLOG（不导出）"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 创建工作线程
        self.worker = MTKLogWorker(device, 'stop', self.device_manager, self, storage_path_func=self.get_storage_path)
        self.worker.progress.connect(self.progress_updated.emit)
        self.worker.finished.connect(self._on_mtklog_stopped)
        self.is_running = True
        self.worker.start()
        
    def delete_mtklog(self):
        """删除MTKLOG"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 确认删除
        reply = QMessageBox.question(
            None,
            self.lang_manager.tr("确认删除"),
            self.lang_manager.tr("确定要删除设备上的MTKLOG吗？"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 创建工作线程
        self.worker = MTKLogWorker(device, 'delete', self.device_manager, self, storage_path_func=self.get_storage_path)
        self.worker.progress.connect(self.progress_updated.emit)
        self.worker.finished.connect(self._on_mtklog_deleted)
        self.is_running = True
        self.worker.start()
    
    def set_log_size(self):
        """设置Log大小"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        if not self._check_mtklogger_exists(device):
            self.status_message.emit(self.lang_manager.tr("未检测到MTKLOGGER，请先安装"))
            return
        
        # 显示对话框
        dialog = LogSizeDialog(device=device, parent=self.parent())
        if dialog.exec_() != QDialog.Accepted:
            return
        
        # 获取输入的值
        modem_size, mobile_size, netlog_size = dialog.get_values()
        if modem_size is None or mobile_size is None or netlog_size is None:
            self.status_message.emit(self.lang_manager.tr("输入的值无效，请输入数字"))
            return
        
        try:
            # 设置Modem Log大小 (cmd_target=2)
            modem_cmd = ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                        "-e", "cmd_name", f"set_log_size_{modem_size}", "--ei", "cmd_target", "2", 
                        "-n", "com.debug.loggerui/.framework.LogReceiver"]
            result = subprocess.run(modem_cmd, capture_output=True, text=True, timeout=15,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                raise Exception(f"{self.lang_manager.tr('设置Modem Log大小失败:')} {result.stderr.strip()}")
            
            # 设置Mobile Log大小 (cmd_target=1)
            mobile_cmd = ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                         "-e", "cmd_name", f"set_log_size_{mobile_size}", "--ei", "cmd_target", "1", 
                         "-n", "com.debug.loggerui/.framework.LogReceiver"]
            result = subprocess.run(mobile_cmd, capture_output=True, text=True, timeout=15,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                raise Exception(f"{self.lang_manager.tr('设置Mobile Log大小失败:')} {result.stderr.strip()}")
            
            # 设置Netlog大小 (cmd_target=4)
            netlog_cmd = ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                         "-e", "cmd_name", f"set_log_size_{netlog_size}", "--ei", "cmd_target", "4", 
                         "-n", "com.debug.loggerui/.framework.LogReceiver"]
            result = subprocess.run(netlog_cmd, capture_output=True, text=True, timeout=15,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                raise Exception(f"{self.lang_manager.tr('设置Netlog大小失败:')} {result.stderr.strip()}")
            
            self.status_message.emit(f"{self.lang_manager.tr('Log大小设置成功 - Modem:')}{modem_size}MB, Mobile:{mobile_size}MB, Netlog:{netlog_size}MB")
            
        except subprocess.TimeoutExpired:
            self.status_message.emit(self.lang_manager.tr("设置Log大小超时，请检查设备连接"))
        except FileNotFoundError:
            self.status_message.emit(self.lang_manager.tr("未找到adb命令，请确保Android SDK已安装并配置PATH"))
        except Exception as e:
            self.status_message.emit(f"{self.lang_manager.tr('设置Log大小失败:')} {str(e)}")
        
    def set_sd_mode(self):
        """设置SD模式"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        if not self._check_mtklogger_exists(device):
            self.status_message.emit(self.lang_manager.tr("未检测到MTKLOGGER，请先安装"))
            return
        
        try:
            cmd = ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                   "-e", "cmd_name", "switch_modem_log_mode_2", "--ei", "cmd_target", "1", "-n", "com.debug.loggerui/.framework.LogReceiver"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode == 0:
                self.status_message.emit(f"{self.lang_manager.tr('已设置为SD模式 -')} {device}")
            else:
                error_msg = result.stderr.strip() if result.stderr else self.lang_manager.tr("未知错误")
                self.status_message.emit(f"{self.lang_manager.tr('设置SD模式失败:')} {error_msg}")
        except subprocess.TimeoutExpired:
            self.status_message.emit(self.lang_manager.tr("设置SD模式超时，请检查设备连接"))
        except FileNotFoundError:
            self.status_message.emit(self.lang_manager.tr("未找到adb命令，请确保Android SDK已安装并配置PATH"))
        except Exception as e:
            self.status_message.emit(f"{self.lang_manager.tr('设置SD模式失败:')} {str(e)}")
    
    def set_usb_mode(self):
        """设置USB模式"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        if not self._check_mtklogger_exists(device):
            self.status_message.emit(self.lang_manager.tr("未检测到MTKLOGGER，请先安装"))
            return
        
        try:
            cmd = ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                   "-e", "cmd_name", "switch_modem_log_mode_1", "--ei", "cmd_target", "1", "-n", "com.debug.loggerui/.framework.LogReceiver"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode == 0:
                self.status_message.emit(f"{self.lang_manager.tr('已设置为USB模式 -')} {device}")
            else:
                error_msg = result.stderr.strip() if result.stderr else self.lang_manager.tr("未知错误")
                self.status_message.emit(f"{self.lang_manager.tr('设置USB模式失败:')} {error_msg}")
        except subprocess.TimeoutExpired:
            self.status_message.emit(self.lang_manager.tr("设置USB模式超时，请检查设备连接"))
        except FileNotFoundError:
            self.status_message.emit(self.lang_manager.tr("未找到adb命令，请确保Android SDK已安装并配置PATH"))
        except Exception as e:
            self.status_message.emit(f"{self.lang_manager.tr('设置USB模式失败:')} {str(e)}")
    
    def install_mtklogger(self):
        """安装MTKLOGGER"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 选择APK文件
        apk_file, _ = QFileDialog.getOpenFileName(
            None,
            self.lang_manager.tr("选择MTKLOGGER APK文件"),
            "",
            "APK Files (*.apk)"
        )
        
        if not apk_file:
            return
        
        # 检查芯片类型和APK包名的匹配性
        try:
            # 1. 检测设备芯片类型
            chip_type = get_device_chip_type(device)
            if chip_type:
                self.status_message.emit(f"{self.lang_manager.tr('检测到芯片类型:')} {chip_type}")
            
            # 2. 获取APK包名
            apk_package = get_apk_package_name(apk_file)
            if apk_package:
                self.status_message.emit(f"{self.lang_manager.tr('APK包名:')} {apk_package}")
            
            # 3. 检查匹配性并给出风险提示
            if chip_type:
                is_mtk_chip = (chip_type == "MTK")
                
                if apk_package:
                    # 如果成功获取到APK包名，进行精确匹配检查
                    is_mtk_apk = (apk_package == "com.debug.loggerui")
                    
                    # 检查不匹配的情况
                    if is_mtk_chip and not is_mtk_apk:
                        # MTK芯片但APK包名不是com.debug.loggerui
                        warning_msg = (
                            f"{self.lang_manager.tr('检测到不匹配:')}\n\n"
                            f"{self.lang_manager.tr('设备芯片类型:')} {chip_type}\n"
                            f"{self.lang_manager.tr('APK包名:')} {apk_package}\n\n"
                            f"{self.lang_manager.tr('MTK芯片设备应安装包名为com.debug.loggerui的APK。')}\n"
                            f"{self.lang_manager.tr('当前APK包名不匹配，可能无法正常工作。')}\n\n"
                            f"{self.lang_manager.tr('是否继续安装?')}"
                        )
                        reply = QMessageBox.warning(
                            None,
                            self.lang_manager.tr("安装警告"),
                            warning_msg,
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.No
                        )
                        if reply != QMessageBox.Yes:
                            self.status_message.emit(self.lang_manager.tr("用户取消安装"))
                            return
                    
                    elif not is_mtk_chip and is_mtk_apk:
                        # 高通芯片但APK包名是com.debug.loggerui（MTK的APK）
                        warning_msg = (
                            f"{self.lang_manager.tr('检测到不匹配:')}\n\n"
                            f"{self.lang_manager.tr('设备芯片类型:')} {chip_type}\n"
                            f"{self.lang_manager.tr('APK包名:')} {apk_package}\n\n"
                            f"{self.lang_manager.tr('此APK是专为MTK芯片设计的logger工具。')}\n"
                            f"{self.lang_manager.tr('当前设备是')}{chip_type}{self.lang_manager.tr('芯片，安装此APK可能无法正常工作。')}\n\n"
                            f"{self.lang_manager.tr('是否继续安装?')}"
                        )
                        reply = QMessageBox.warning(
                            None,
                            self.lang_manager.tr("安装警告"),
                            warning_msg,
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.No
                        )
                        if reply != QMessageBox.Yes:
                            self.status_message.emit(self.lang_manager.tr("用户取消安装"))
                            return
                else:
                    # 如果无法获取APK包名，根据芯片类型和文件名进行警告
                    # 检查文件名是否包含MTK相关的关键词
                    apk_filename = os.path.basename(apk_file).lower()
                    is_suspicious_mtk = any(keyword in apk_filename for keyword in ["debugloggerui", "mtk", "logger"])
                    
                    if not is_mtk_chip and is_suspicious_mtk:
                        # 高通芯片，但文件名看起来像MTK的APK
                        warning_msg = (
                            f"{self.lang_manager.tr('警告: 无法获取APK包名，但检测到可疑情况:')}\n\n"
                            f"{self.lang_manager.tr('设备芯片类型:')} {chip_type}\n"
                            f"{self.lang_manager.tr('APK文件名:')} {os.path.basename(apk_file)}\n\n"
                            f"{self.lang_manager.tr('文件名包含DebugLoggerUI，这通常是MTK芯片的logger工具。')}\n"
                            f"{self.lang_manager.tr('当前设备是')}{chip_type}{self.lang_manager.tr('芯片，安装此APK可能无法正常工作。')}\n\n"
                            f"{self.lang_manager.tr('建议:')}\n"
                            f"1. {self.lang_manager.tr('确认这是正确的APK文件')}\n"
                            f"2. {self.lang_manager.tr('如果是MTK的APK，建议使用匹配的logger工具')}\n\n"
                            f"{self.lang_manager.tr('是否继续安装?')}"
                        )
                        reply = QMessageBox.warning(
                            None,
                            self.lang_manager.tr("安装警告"),
                            warning_msg,
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.No
                        )
                        if reply != QMessageBox.Yes:
                            self.status_message.emit(self.lang_manager.tr("用户取消安装"))
                            return
                    elif not APKUTILS_AVAILABLE:
                        # 如果无法获取包名且apkutils库未安装，给出提示
                        self.status_message.emit(f"{self.lang_manager.tr('提示:')} {self.lang_manager.tr('无法检查APK包名，建议安装apkutils库: pip install apkutils')}")
        except Exception as e:
            # 如果检查过程中出错，给出提示但允许继续
            print(f"检查芯片类型或APK包名时出错: {str(e)}")
            self.status_message.emit(f"{self.lang_manager.tr('检查过程出现警告:')} {str(e)}，{self.lang_manager.tr('将继续安装')}")
        
        try:
            self.status_message.emit(self.lang_manager.tr("正在安装MTKLOGGER..."))
            
            # 1. 安装MTKLOGGER
            install_cmd = ["adb", "-s", device, "install", apk_file]
            result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=120,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else self.lang_manager.tr("未知错误")
                raise Exception(f"{self.lang_manager.tr('安装失败:')} {error_msg}")
            
            # 检查安装结果
            if "Success" not in result.stdout and "success" not in result.stdout.lower():
                raise Exception(f"{self.lang_manager.tr('安装可能失败:')} {result.stdout.strip()}")
            
            # 2. 启动MTKLOGGER
            self.status_message.emit(self.lang_manager.tr("启动MTKLOGGER..."))
            
            # 确保屏幕亮屏且解锁
            if not self.device_manager.ensure_screen_unlocked(device):
                raise Exception(self.lang_manager.tr("无法确保屏幕状态"))
            
            start_cmd = ["adb", "-s", device, "shell", "am", "start", "-n", "com.debug.loggerui/.MainActivity"]
            result = subprocess.run(start_cmd, capture_output=True, text=True, timeout=30,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                print(f"{self.lang_manager.tr('警告:')} {self.lang_manager.tr('启动MTKLOGGER失败:')} {result.stderr.strip()}")
            
            self.status_message.emit(self.lang_manager.tr("MTKLOGGER安装成功"))
            
        except Exception as e:
            self.status_message.emit(f"{self.lang_manager.tr('安装MTKLOGGER失败:')} {str(e)}")
    
    def _check_mtklogger_exists(self, device):
        """检查MTKLOGGER是否存在"""
        try:
            result = subprocess.run(
                ["adb", "-s", device, "shell", "pm", "list", "packages", "com.debug.loggerui"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            return "com.debug.loggerui" in result.stdout
        except:
            return False
    
    def _on_mtklog_started(self, success, message):
        """MTKLOG启动完成"""
        self.is_running = False
        if success:
            self.mtklog_started.emit()
        self.status_message.emit(message)
        
    def _on_mtklog_stopped(self, success, message):
        """MTKLOG停止并导出完成"""
        self.is_running = False
        if success:
            self.mtklog_stopped.emit()
            # message就是导出的文件夹路径
            export_path = message
            self.mtklog_exported.emit(export_path)
            # 直接打开文件夹
            try:
                os.startfile(export_path)
            except Exception as e:
                self.status_message.emit(f"{self.lang_manager.tr('打开文件夹失败:')} {str(e)}")
            self.status_message.emit(f"{self.lang_manager.tr('MTKLOG已停止并导出 -')} {export_path}")
        else:
            self.status_message.emit(message)
        
    def _on_mtklog_deleted(self, success, message):
        """MTKLOG删除完成"""
        self.is_running = False
        if success:
            self.mtklog_deleted.emit()
        self.status_message.emit(message)
