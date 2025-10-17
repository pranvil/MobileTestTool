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
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QMutex
from PyQt5.QtWidgets import QMessageBox, QInputDialog, QFileDialog, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDialogButtonBox

# 尝试导入uiautomator2
try:
    import uiautomator2 as u2
    U2_AVAILABLE = True
except ImportError:
    u2 = None
    U2_AVAILABLE = False


class LogSizeDialog(QDialog):
    """Log大小设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置Log大小")
        self.setModal(True)
        self.resize(400, 200)
        
        layout = QVBoxLayout()
        
        # Modem Log
        modem_layout = QHBoxLayout()
        modem_layout.addWidget(QLabel("Modem Log (MB):"))
        self.modem_edit = QLineEdit()
        self.modem_edit.setText("68922")
        self.modem_edit.setPlaceholderText("请输入Modem Log大小(MB)")
        modem_layout.addWidget(self.modem_edit)
        layout.addLayout(modem_layout)
        
        # Mobile Log
        mobile_layout = QHBoxLayout()
        mobile_layout.addWidget(QLabel("Mobile Log (MB):"))
        self.mobile_edit = QLineEdit()
        self.mobile_edit.setText("68922")
        self.mobile_edit.setPlaceholderText("请输入Mobile Log大小(MB)")
        mobile_layout.addWidget(self.mobile_edit)
        layout.addLayout(mobile_layout)
        
        # Netlog
        netlog_layout = QHBoxLayout()
        netlog_layout.addWidget(QLabel("Netlog (MB):"))
        self.netlog_edit = QLineEdit()
        self.netlog_edit.setText("68922")
        self.netlog_edit.setPlaceholderText("请输入Netlog大小(MB)")
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
    
    def __init__(self, device, operation, device_manager, parent=None, log_name=None, export_media=False):
        super().__init__(parent)
        self.device = device
        self.operation = operation
        self.device_manager = device_manager
        self.log_name = log_name
        self.export_media = export_media
        self._mutex = QMutex()
        self._stop_requested = False
        
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
            self.finished.emit(False, f"操作失败: {str(e)}")
    
    def _start_mtklog(self):
        """开启MTKLOG"""
        try:
            # 1. 确保屏幕亮屏且解锁
            self.progress.emit(5, "检查屏幕状态...")
            if not self.device_manager.ensure_screen_unlocked(self.device):
                raise Exception("无法确保屏幕状态")
            
            # 2. 启动logger应用
            self.progress.emit(10, "启动logger应用...")
            start_app_cmd = ["adb", "-s", self.device, "shell", "am", "start", "-n", "com.debug.loggerui/.MainActivity"]
            result = subprocess.run(start_app_cmd, capture_output=True, text=True, timeout=30,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            if result.returncode != 0:
                print(f"警告: 启动logger应用失败: {result.stderr.strip()}")
            time.sleep(2)
            
            # 3. 检查logger状态
            self.progress.emit(15, "检查logger状态...")
            
            logger_is_running = False
            if U2_AVAILABLE:
                try:
                    d = u2.connect(self.device)
                    button = d(resourceId="com.debug.loggerui:id/startStopToggleButton")
                    if button.exists:
                        is_checked = button.info.get('checked', False)
                        logger_is_running = is_checked
                except Exception as e:
                    logger_is_running = False
            
            # 4. 如果logger正在运行，先停止
            if logger_is_running:
                self.progress.emit(20, "停止logger...")
                stop_cmd = ["adb", "-s", self.device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                           "-e", "cmd_name", "stop", "--ei", "cmd_target", "-1", "-n", "com.debug.loggerui/.framework.LogReceiver"]
                
                result = subprocess.run(stop_cmd, capture_output=True, text=True, timeout=15,
                                      creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                if result.returncode != 0:
                    raise Exception(f"停止logger失败: {result.stderr.strip()}")
                
                # 5. 等待2秒后检查按钮状态
                self.progress.emit(25, "等待logger停止...")
                time.sleep(2)
                
                # 6. 检查按钮checked是否为false
                self.progress.emit(30, "正在确认logger已完全停止...")
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
            self.progress.emit(40, "清除旧日志...")
            clear_cmd = ["adb", "-s", self.device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                        "-e", "cmd_name", "clear_logs_all", "--ei", "cmd_target", "0", "-n", "com.debug.loggerui/.framework.LogReceiver"]
            
            result = subprocess.run(clear_cmd, capture_output=True, text=True, timeout=15,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            if result.returncode != 0:
                raise Exception(f"清除旧日志失败: {result.stderr.strip()}")
            
            # 等待3秒确保清除完毕
            time.sleep(3)
            
            # 8. 设置MD log缓存大小20GB
            self.progress.emit(50, "设置缓存大小...")
            size_cmd = ["adb", "-s", self.device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                       "-e", "cmd_name", "set_log_size_20000", "--ei", "cmd_target", "2", "-n", "com.debug.loggerui/.framework.LogReceiver"]
            
            result = subprocess.run(size_cmd, capture_output=True, text=True, timeout=15,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            if result.returncode != 0:
                raise Exception(f"设置缓存大小失败: {result.stderr.strip()}")
            
            # 9. 开启MTK LOGGER
            self.progress.emit(60, "开启logger...")
            start_cmd = ["adb", "-s", self.device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                        "-e", "cmd_name", "start", "--ei", "cmd_target", "-1", "-n", "com.debug.loggerui/.framework.LogReceiver"]
            
            result = subprocess.run(start_cmd, capture_output=True, text=True, timeout=15,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            if result.returncode != 0:
                raise Exception(f"开启logger失败: {result.stderr.strip()}")
            
            # 10. 等待"Starting logs"对话框消失
            self.progress.emit(70, "等待logger启动...")
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
            self.progress.emit(90, "正在确认logger已完全启动...")
            start_time = time.time()
            while time.time() - start_time < max_wait_time:
                if U2_AVAILABLE:
                    try:
                        d = u2.connect(self.device)
                        button = d(resourceId="com.debug.loggerui:id/startStopToggleButton")
                        if button.exists:
                            is_checked = button.info.get('checked', False)
                            if is_checked:
                                break
                    except Exception as e:
                        break
                time.sleep(1)
            
            self.progress.emit(100, "完成!")
            self.finished.emit(True, "MTKLOG启动成功")
            
        except Exception as e:
            self.finished.emit(False, f"启动MTKLOG失败: {str(e)}")
    
    def _stop_and_export_mtklog(self, log_name, export_media):
        """停止并导出MTKLOG"""
        try:
            # 1. 确保屏幕亮屏且解锁
            self.progress.emit(5, "检查屏幕状态...")
            if not self.device_manager.ensure_screen_unlocked(self.device):
                raise Exception("无法确保屏幕状态")
            
            # 2. 启动logger应用
            self.progress.emit(10, "启动logger应用...")
            start_app_cmd = ["adb", "-s", self.device, "shell", "am", "start", "-n", "com.debug.loggerui/.MainActivity"]
            result = subprocess.run(start_app_cmd, capture_output=True, text=True, timeout=30,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            if result.returncode != 0:
                print(f"警告: 启动logger应用失败: {result.stderr.strip()}")
            time.sleep(2)
            
            # 3. 检查logger状态
            self.progress.emit(15, "检查logger状态...")
            
            logger_is_running = False
            if U2_AVAILABLE:
                try:
                    d = u2.connect(self.device)
                    button = d(resourceId="com.debug.loggerui:id/startStopToggleButton")
                    if button.exists:
                        is_checked = button.info.get('checked', False)
                        logger_is_running = is_checked
                except Exception as e:
                    print(f"警告: UIAutomator2不可用 - {str(e)}")
                    print("提示: 如果频繁出现此问题，建议重启手机后重试")
                    logger_is_running = False
            
            # 4. 如果logger正在运行，执行停止命令
            if logger_is_running:
                self.progress.emit(20, "停止logger...")
                stop_cmd = ["adb", "-s", self.device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                           "-e", "cmd_name", "stop", "--ei", "cmd_target", "-1", "-n", "com.debug.loggerui/.framework.LogReceiver"]
                
                result = subprocess.run(stop_cmd, capture_output=True, text=True, timeout=15,
                                      creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                if result.returncode != 0:
                    raise Exception(f"停止logger失败: {result.stderr.strip()}")
                
                # 5. 等待2秒后检查按钮状态
                self.progress.emit(25, "等待logger停止...")
                time.sleep(2)
                
                # 6. 检查按钮checked是否为false
                self.progress.emit(30, "正在确认logger已完全停止...")
                max_wait_time = 180
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
            
            # 7. 创建日志目录
            self.progress.emit(40, "创建日志目录...")
            curredate = datetime.datetime.now().strftime("%Y%m%d")
            log_dir = f"c:\\log\\{curredate}"
            log_folder = f"{log_dir}\\log_{log_name}"
            
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # 8. 执行adb pull命令序列
            pull_commands = [
                ("/sdcard/TCTReport", "TCTReport"),
                ("/sdcard/mtklog", "mtklog"),
                ("/sdcard/debuglogger", "debuglogger"),
                ("/sdcard/logmanager", "logmanager"),
                ("/data/debuglogger", "data_debuglogger"),
                ("/sdcard/BugReport", "BugReport"),
                ("/data/media/logmanager", "data_logmanager"),
                ("/data/user_de/0/com.android.shell/files/bugreports/", "bugreports"),
                ("/sdcard/Android/data/com.tmobile.echolocate/cache/dia_debug", "echolocate_dia_debug")
            ]
            
            # 如果用户选择导出媒体文件，添加额外的命令
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
            
            total_commands = len(pull_commands)
            
            for i, (source_path, folder_name) in enumerate(pull_commands):
                self.progress.emit(45 + (i * 5), f"检查 {folder_name} ({i+1}/{total_commands})...")
                
                # 先检查文件夹是否存在
                check_cmd = ["adb", "-s", self.device, "shell", "test", "-d", source_path]
                check_result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=10,
                                            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                
                if check_result.returncode != 0:
                    continue
                
                # 文件夹存在，执行pull
                self.progress.emit(45 + (i * 5), f"导出 {folder_name} ({i+1}/{total_commands})...")
                cmd = ["adb", "-s", self.device, "pull", source_path, log_folder]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                                      creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                
                if result.returncode != 0:
                    print(f"警告: {folder_name} 导出失败: {result.stderr.strip()}")
            
            self.progress.emit(100, "完成!")
            self.finished.emit(True, log_folder)
            
        except Exception as e:
            self.finished.emit(False, f"导出MTKLOG失败: {str(e)}")
    
    def _stop_mtklog(self):
        """停止MTKLOG（不导出）"""
        try:
            # 1. 确保屏幕亮屏且解锁
            self.progress.emit(5, "检查屏幕状态...")
            if not self.device_manager.ensure_screen_unlocked(self.device):
                raise Exception("无法确保屏幕状态")
            
            # 2. 启动logger应用
            self.progress.emit(10, "启动logger应用...")
            start_app_cmd = ["adb", "-s", self.device, "shell", "am", "start", "-n", "com.debug.loggerui/.MainActivity"]
            result = subprocess.run(start_app_cmd, capture_output=True, text=True, timeout=30,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            if result.returncode != 0:
                print(f"警告: 启动logger应用失败: {result.stderr.strip()}")
            time.sleep(2)
            
            # 3. 检查logger状态
            self.progress.emit(15, "检查logger状态...")
            
            logger_is_running = False
            if U2_AVAILABLE:
                try:
                    d = u2.connect(self.device)
                    button = d(resourceId="com.debug.loggerui:id/startStopToggleButton")
                    if button.exists:
                        is_checked = button.info.get('checked', False)
                        logger_is_running = is_checked
                except Exception as e:
                    print(f"警告: UIAutomator2不可用 - {str(e)}")
                    print("提示: 如果频繁出现此问题，建议重启手机后重试")
                    logger_is_running = False
            
            # 4. 如果logger正在运行，执行停止命令
            if logger_is_running:
                self.progress.emit(20, "停止logger...")
                stop_cmd = ["adb", "-s", self.device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                           "-e", "cmd_name", "stop", "--ei", "cmd_target", "-1", "-n", "com.debug.loggerui/.framework.LogReceiver"]
                
                result = subprocess.run(stop_cmd, capture_output=True, text=True, timeout=15,
                                      creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                if result.returncode != 0:
                    raise Exception(f"停止logger失败: {result.stderr.strip()}")
                
                # 5. 等待2秒后检查按钮状态
                self.progress.emit(25, "等待logger停止...")
                time.sleep(2)
                
                # 6. 检查按钮checked是否为false
                self.progress.emit(30, "正在确认logger已完全停止...")
                max_wait_time = 180
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
            else:
                self.progress.emit(50, "Logger已处于停止状态...")
            
            self.progress.emit(100, "完成!")
            self.finished.emit(True, "MTKLOG已停止")
            
        except Exception as e:
            self.finished.emit(False, f"停止MTKLOG失败: {str(e)}")
    
    def _delete_mtklog(self):
        """删除MTKLOG"""
        try:
            self.progress.emit(50, "执行删除命令...")
            cmd = ["adb", "-s", self.device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                   "-e", "cmd_name", "clear_logs_all", "--ei", "cmd_target", "0", "-n", "com.debug.loggerui/.framework.LogReceiver"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                raise Exception(f"删除MTKLOG失败: {error_msg}")
            
            self.progress.emit(100, "删除完成!")
            self.finished.emit(True, "MTKLOG已删除")
        except Exception as e:
            self.finished.emit(False, f"删除MTKLOG失败: {str(e)}")

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
        self.worker = None
        self.is_running = False
        
    def start_mtklog(self):
        """开启MTKLOG"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 检查MTKLOGGER是否存在
        if not self._check_mtklogger_exists(device):
            self.status_message.emit("未检测到MTKLOGGER，请先安装")
            return
        
        # 创建工作线程
        self.worker = MTKLogWorker(device, 'start', self.device_manager)
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
            "输入日志名称",
            "请输入日志名称:"
        )
        if not ok or not log_name:
            return
        
        # 询问是否导出截图和视频
        reply = QMessageBox.question(
            None,
            "导出媒体文件",
            "是否同时导出截图和录制的视频？\n\n"
            "包括:\n"
            "• 屏幕录制视频\n"
            "• 截图文件\n\n"
            "选择'是'将额外导出这些媒体文件。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        export_media = (reply == QMessageBox.Yes)
        
        # 创建工作线程
        self.worker = MTKLogWorker(device, 'stop_export', self.device_manager, log_name=log_name, export_media=export_media)
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
        self.worker = MTKLogWorker(device, 'stop', self.device_manager)
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
            "确认删除",
            "确定要删除设备上的MTKLOG吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 创建工作线程
        self.worker = MTKLogWorker(device, 'delete', self.device_manager)
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
            self.status_message.emit("未检测到MTKLOGGER，请先安装")
            return
        
        # 显示对话框
        dialog = LogSizeDialog()
        if dialog.exec_() != QDialog.Accepted:
            return
        
        # 获取输入的值
        modem_size, mobile_size, netlog_size = dialog.get_values()
        if modem_size is None or mobile_size is None or netlog_size is None:
            self.status_message.emit("输入的值无效，请输入数字")
            return
        
        try:
            # 设置Modem Log大小 (cmd_target=2)
            modem_cmd = ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                        "-e", "cmd_name", f"set_log_size_{modem_size}", "--ei", "cmd_target", "2", 
                        "-n", "com.debug.loggerui/.framework.LogReceiver"]
            result = subprocess.run(modem_cmd, capture_output=True, text=True, timeout=15,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                raise Exception(f"设置Modem Log大小失败: {result.stderr.strip()}")
            
            # 设置Mobile Log大小 (cmd_target=1)
            mobile_cmd = ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                         "-e", "cmd_name", f"set_log_size_{mobile_size}", "--ei", "cmd_target", "1", 
                         "-n", "com.debug.loggerui/.framework.LogReceiver"]
            result = subprocess.run(mobile_cmd, capture_output=True, text=True, timeout=15,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                raise Exception(f"设置Mobile Log大小失败: {result.stderr.strip()}")
            
            # 设置Netlog大小 (cmd_target=4)
            netlog_cmd = ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                         "-e", "cmd_name", f"set_log_size_{netlog_size}", "--ei", "cmd_target", "4", 
                         "-n", "com.debug.loggerui/.framework.LogReceiver"]
            result = subprocess.run(netlog_cmd, capture_output=True, text=True, timeout=15,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                raise Exception(f"设置Netlog大小失败: {result.stderr.strip()}")
            
            self.status_message.emit(f"Log大小设置成功 - Modem:{modem_size}MB, Mobile:{mobile_size}MB, Netlog:{netlog_size}MB")
            
        except subprocess.TimeoutExpired:
            self.status_message.emit("设置Log大小超时，请检查设备连接")
        except FileNotFoundError:
            self.status_message.emit("未找到adb命令，请确保Android SDK已安装并配置PATH")
        except Exception as e:
            self.status_message.emit(f"设置Log大小失败: {str(e)}")
        
    def set_sd_mode(self):
        """设置SD模式"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        if not self._check_mtklogger_exists(device):
            self.status_message.emit("未检测到MTKLOGGER，请先安装")
            return
        
        try:
            cmd = ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                   "-e", "cmd_name", "switch_modem_log_mode_2", "--ei", "cmd_target", "1", "-n", "com.debug.loggerui/.framework.LogReceiver"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode == 0:
                self.status_message.emit(f"已设置为SD模式 - {device}")
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                self.status_message.emit(f"设置SD模式失败: {error_msg}")
        except subprocess.TimeoutExpired:
            self.status_message.emit("设置SD模式超时，请检查设备连接")
        except FileNotFoundError:
            self.status_message.emit("未找到adb命令，请确保Android SDK已安装并配置PATH")
        except Exception as e:
            self.status_message.emit(f"设置SD模式失败: {str(e)}")
    
    def set_usb_mode(self):
        """设置USB模式"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        if not self._check_mtklogger_exists(device):
            self.status_message.emit("未检测到MTKLOGGER，请先安装")
            return
        
        try:
            cmd = ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                   "-e", "cmd_name", "switch_modem_log_mode_1", "--ei", "cmd_target", "1", "-n", "com.debug.loggerui/.framework.LogReceiver"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode == 0:
                self.status_message.emit(f"已设置为USB模式 - {device}")
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                self.status_message.emit(f"设置USB模式失败: {error_msg}")
        except subprocess.TimeoutExpired:
            self.status_message.emit("设置USB模式超时，请检查设备连接")
        except FileNotFoundError:
            self.status_message.emit("未找到adb命令，请确保Android SDK已安装并配置PATH")
        except Exception as e:
            self.status_message.emit(f"设置USB模式失败: {str(e)}")
    
    def install_mtklogger(self):
        """安装MTKLOGGER"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 选择APK文件
        apk_file, _ = QFileDialog.getOpenFileName(
            None,
            "选择MTKLOGGER APK文件",
            "",
            "APK Files (*.apk)"
        )
        
        if not apk_file:
            return
        
        try:
            self.status_message.emit("正在安装MTKLOGGER...")
            
            # 1. 安装MTKLOGGER
            install_cmd = ["adb", "-s", device, "install", "--bypass-low-target-sdk-block", apk_file]
            result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=120,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                raise Exception(f"安装失败: {error_msg}")
            
            # 检查安装结果
            if "Success" not in result.stdout and "success" not in result.stdout.lower():
                raise Exception(f"安装可能失败: {result.stdout.strip()}")
            
            # 2. 启动MTKLOGGER
            self.status_message.emit("启动MTKLOGGER...")
            
            # 确保屏幕亮屏且解锁
            if not self.device_manager.ensure_screen_unlocked(device):
                raise Exception("无法确保屏幕状态")
            
            start_cmd = ["adb", "-s", device, "shell", "am", "start", "-n", "com.debug.loggerui/.MainActivity"]
            result = subprocess.run(start_cmd, capture_output=True, text=True, timeout=30,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                print(f"警告: 启动MTKLOGGER失败: {result.stderr.strip()}")
            
            self.status_message.emit("MTKLOGGER安装成功")
            
        except Exception as e:
            self.status_message.emit(f"安装MTKLOGGER失败: {str(e)}")
    
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
                self.status_message.emit(f"打开文件夹失败: {str(e)}")
            self.status_message.emit(f"MTKLOG已停止并导出 - {export_path}")
        else:
            self.status_message.emit(message)
        
    def _on_mtklog_deleted(self, success, message):
        """MTKLOG删除完成"""
        self.is_running = False
        if success:
            self.mtklog_deleted.emit()
        self.status_message.emit(message)
