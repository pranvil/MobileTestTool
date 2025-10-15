#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5 截图管理器
适配原Tkinter版本的截图功能
"""

import subprocess
import os
import time
import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QMutex
from PyQt5.QtWidgets import QMessageBox


class ScreenshotWorker(QThread):
    """截图工作线程"""
    
    finished = pyqtSignal(bool, str)  # success, message
    progress = pyqtSignal(int, str)   # progress, status
    
    def __init__(self, device, parent=None):
        super().__init__(parent)
        self.device = device
        self._mutex = QMutex()
        self._stop_requested = False
        
    def run(self):
        """执行截图操作"""
        try:
            # 1. 检查并创建screenshot文件夹
            self.progress.emit(20, "检查截图文件夹...")
            
            current_time = datetime.datetime.now()
            date_str = current_time.strftime("%Y%m%d")
            log_dir = f"c:\\log\\{date_str}"
            screenshot_folder = os.path.join(log_dir, "screenshot")
            
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            if not os.path.exists(screenshot_folder):
                os.makedirs(screenshot_folder)
            
            # 2. 等待设备连接
            self.progress.emit(40, "等待设备连接...")
            wait_cmd = ["adb", "-s", self.device, "wait-for-device"]
            result = subprocess.run(
                wait_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode != 0:
                raise Exception(f"设备连接失败: {result.stderr.strip()}")
            
            # 3. 设备截图
            self.progress.emit(60, "正在截图...")
            screencap_cmd = ["adb", "-s", self.device, "shell", "/system/bin/screencap", "-p", "/sdcard/screenshot.png"]
            result = subprocess.run(
                screencap_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode != 0:
                raise Exception(f"截图失败: {result.stderr.strip()}")
            
            # 4. 再次等待设备
            self.progress.emit(80, "等待设备就绪...")
            wait_cmd2 = ["adb", "-s", self.device, "wait-for-device"]
            subprocess.run(
                wait_cmd2,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # 5. 生成文件名并拉取截图
            self.progress.emit(90, "保存截图...")
            current_time = datetime.datetime.now()
            time_str = current_time.strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{time_str}.png"
            local_path = os.path.join(screenshot_folder, filename)
            
            pull_cmd = ["adb", "-s", self.device, "pull", "/sdcard/screenshot.png", local_path]
            result = subprocess.run(
                pull_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode != 0:
                raise Exception(f"保存截图失败: {result.stderr.strip()}")
            
            # 6. 完成
            self.progress.emit(100, "截图完成!")
            
            # 打开截图文件夹
            os.startfile(screenshot_folder)
            time.sleep(2)
            # 打开截图文件
            os.startfile(local_path)
            
            self.finished.emit(True, f"截图已保存: {local_path}")
            
        except Exception as e:
            self.finished.emit(False, f"截图失败: {str(e)}")


class PyQtScreenshotManager(QObject):
    """PyQt5 截图管理器"""
    
    # 信号定义
    screenshot_completed = pyqtSignal(str)  # filename
    progress_updated = pyqtSignal(int, str)  # progress, status
    status_message = pyqtSignal(str)
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self.worker = None
        
    def take_screenshot(self):
        """截图功能"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 创建工作线程
        self.worker = ScreenshotWorker(device)
        self.worker.progress.connect(self.progress_updated.emit)
        self.worker.finished.connect(self._on_screenshot_finished)
        self.worker.start()
        
    def _on_screenshot_finished(self, success, message):
        """截图完成"""
        if success:
            self.screenshot_completed.emit(message)
        # 只发送一次状态消息，避免重复打印
        # self.status_message.emit(message)

