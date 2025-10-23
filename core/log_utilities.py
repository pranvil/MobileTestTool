#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5 其他管理器集合
包含TCPDUMP、Telephony、Google Log、AEE Log、Bugreport等管理器
"""

import subprocess
import os
import datetime
import threading
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QInputDialog, QFileDialog


class PyQtTCPDumpManager(QObject):
    """TCPDUMP管理器"""
    
    status_message = pyqtSignal(str)
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.process = None
    
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
        
    def show_tcpdump_dialog(self):
        """显示TCPDUMP对话框"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 获取用户输入
        interface, ok1 = QInputDialog.getText(None, "TCPDUMP", self.lang_manager.tr("请输入网络接口 (如 wlan0):"))
        if not ok1 or not interface:
            return
        
        duration, ok2 = QInputDialog.getInt(None, "TCPDUMP", self.lang_manager.tr("请输入持续时间(秒):"), 60, 1, 3600)
        if not ok2:
            return
        
        # 执行TCPDUMP
        try:
            self.status_message.emit(self.lang_manager.tr("开始TCPDUMP..."))
            
            # 创建保存目录
            current_time = datetime.datetime.now()
            date_str = current_time.strftime("%Y%m%d")
            time_str = current_time.strftime("%H%M%S")
            log_dir = self.get_storage_path()
            tcpdump_file = os.path.join(log_dir, f"tcpdump_{time_str}.pcap")
            
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # 执行TCPDUMP命令
            cmd = ["adb", "-s", device, "shell", "tcpdump", "-i", interface, "-w", "/sdcard/tcpdump.pcap"]
            self.process = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # 等待指定时间
            threading.Timer(duration, self._stop_tcpdump, args=[device, tcpdump_file]).start()
            
        except Exception as e:
            self.status_message.emit(f"{self.lang_manager.tr('TCPDUMP失败:')} {str(e)}")
    
    def _stop_tcpdump(self, device, output_file):
        """停止TCPDUMP并保存"""
        try:
            if self.process:
                self.process.terminate()
                self.process.wait(timeout=5)
            
            # 等待文件生成
            import time
            time.sleep(2)
            
            # 拉取文件
            subprocess.run(
                ["adb", "-s", device, "pull", "/sdcard/tcpdump.pcap", output_file],
                timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            self.status_message.emit(f"{self.lang_manager.tr('TCPDUMP已保存:')} {output_file}")
            
        except Exception as e:
            self.status_message.emit(f"{self.lang_manager.tr('保存TCPDUMP失败:')} {str(e)}")


class PyQtGoogleLogManager(QObject):
    """Google Log管理器"""
    
    status_message = pyqtSignal(str)
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.google_log_enabled = False
        
    def toggle_google_log(self):
        """切换Google日志"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        try:
            if self.google_log_enabled:
                # 禁用
                subprocess.run(
                    ["adb", "-s", device, "shell", "setprop", "log.tag.GoogleDialer", "ASSERT"],
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                self.google_log_enabled = False
                self.status_message.emit(self.lang_manager.tr("Google日志已禁用"))
            else:
                # 启用
                subprocess.run(
                    ["adb", "-s", device, "shell", "setprop", "log.tag.GoogleDialer", "VERBOSE"],
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                self.google_log_enabled = True
                self.status_message.emit(self.lang_manager.tr("Google日志已启用"))
        except Exception as e:
            self.status_message.emit(f"{self.lang_manager.tr('切换Google日志失败:')} {str(e)}")


class PyQtAEELogManager(QObject):
    """AEE Log管理器"""
    
    status_message = pyqtSignal(str)
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        
    def start_aee_log(self):
        """启动AEE Log"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        try:
            subprocess.run(
                ["adb", "-s", device, "shell", "am", "start", "-n", "com.mediatek.aee/.aee.AEEMainActivity"],
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            self.status_message.emit(self.lang_manager.tr("AEE Log已启动"))
        except Exception as e:
            self.status_message.emit(f"{self.lang_manager.tr('启动AEE Log失败:')} {str(e)}")


class PyQtBugreportManager(QObject):
    """Bugreport管理器"""
    
    status_message = pyqtSignal(str)
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        
    def generate_bugreport(self):
        """生成Bugreport"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        try:
            self.status_message.emit(self.lang_manager.tr("正在生成Bugreport..."))
            
            # 创建保存目录
            current_date = datetime.datetime.now().strftime("%Y%m%d")
            bugreport_folder = f"C:\\{current_date}\\bugreport"
            
            if not os.path.exists(bugreport_folder):
                os.makedirs(bugreport_folder)
            
            # 在后台线程中生成Bugreport
            from PyQt5.QtCore import QThread, pyqtSignal
            
            class BugreportWorker(QThread):
                finished = pyqtSignal(bool, str)
                
                def __init__(self, device, folder):
                    super().__init__()
                    self.device = device
                    self.folder = folder
                
                def run(self):
                    try:
                        subprocess.run(
                            ["adb", "-s", self.device, "bugreport", self.folder],
                            timeout=300,
                            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                        )
                        self.finished.emit(True, self.folder)
                    except Exception as e:
                        self.finished.emit(False, str(e))
            
            self.worker = BugreportWorker(device, bugreport_folder)
            self.worker.finished.connect(self._on_bugreport_generated)
            self.worker.start()
            
        except Exception as e:
            self.status_message.emit(f"{self.lang_manager.tr('生成Bugreport失败:')} {str(e)}")
    
    def _on_bugreport_generated(self, success, result):
        """Bugreport生成完成"""
        if success:
            self.status_message.emit(f"{self.lang_manager.tr('Bugreport已生成:')} {result}")
            # 打开文件夹
            os.startfile(result)
        else:
            self.status_message.emit(f"{self.lang_manager.tr('生成Bugreport失败:')} {result}")
    
    def pull_bugreport(self):
        """Pull Bugreport"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        try:
            # 先检查设备上是否有bugreport
            self.status_message.emit(self.lang_manager.tr("检查设备上的bugreport..."))
            
            check_result = subprocess.run(
                ["adb", "-s", device, "shell", "ls", "-l", "/data/user_de/0/com.android.shell/files/bugreports"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # 检查是否返回错误信息
            if "No such file or directory" in check_result.stderr or check_result.returncode != 0:
                self.status_message.emit(self.lang_manager.tr("设备上没有bugreport"))
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(None, self.lang_manager.tr("提示"), "设备上没有bugreport文件")
                return
            
            # 如果目录存在但为空，也提示
            if not check_result.stdout.strip():
                self.status_message.emit(self.lang_manager.tr("设备上的bugreport目录为空"))
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(None, self.lang_manager.tr("提示"), "设备上的bugreport目录为空")
                return
            
            self.status_message.emit(self.lang_manager.tr("正在拉取Bugreport..."))
            
            # 创建保存目录
            current_date = datetime.datetime.now().strftime("%Y%m%d")
            bugreport_folder = f"C:\\log\\{current_date}\\bugreport"
            
            if not os.path.exists(bugreport_folder):
                os.makedirs(bugreport_folder)
            
            # Pull bugreport
            subprocess.run(
                ["adb", "-s", device, "pull", "/data/user_de/0/com.android.shell/files/bugreports", bugreport_folder],
                timeout=300,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            self.status_message.emit(f"{self.lang_manager.tr('Bugreport已拉取:')} {bugreport_folder}")
            
            # 打开文件夹
            os.startfile(bugreport_folder)
            
        except Exception as e:
            self.status_message.emit(f"{self.lang_manager.tr('拉取Bugreport失败:')} {str(e)}")
    
    def delete_bugreport(self):
        """删除Bugreport"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 确认对话框
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            None,
            self.lang_manager.tr("确认删除"),
            self.lang_manager.tr("确定要删除设备上的bugreport吗？此操作不可恢复。"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            subprocess.run(
                ["adb", "-s", device, "shell", "rm", "-rf", "/data/user_de/0/com.android.shell/files/bugreports"],
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            self.status_message.emit(self.lang_manager.tr("Bugreport已删除"))
            QMessageBox.information(None, self.lang_manager.tr("成功"), "bugreport已成功删除")
        except Exception as e:
            self.status_message.emit(f"{self.lang_manager.tr('删除Bugreport失败:')} {str(e)}")
            QMessageBox.critical(None, self.lang_manager.tr("错误"), f"删除Bugreport失败: {str(e)}")


# 导出所有管理器
__all__ = [
    'PyQtTCPDumpManager',
    'PyQtTelephonyManager',
    'PyQtGoogleLogManager',
    'PyQtAEELogManager',
    'PyQtBugreportManager'
]

