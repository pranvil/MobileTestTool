#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5 Echolocate管理器
适配原Tkinter版本的Echolocate功能
"""

import subprocess
import os
import glob
import datetime
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QInputDialog


class PyQtEcholocateManager(QObject):
    """PyQt5 Echolocate管理器"""
    
    # 信号定义
    echolocate_installed = pyqtSignal()
    echolocate_triggered = pyqtSignal()
    file_pulled = pyqtSignal(str)  # folder
    file_deleted = pyqtSignal()
    status_message = pyqtSignal(str)
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        
    def install_echolocate(self):
        """安装Echolocate"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        try:
            # 查找APK文件
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(os.path.dirname(current_dir))
            echolocate_dir = os.path.join(parent_dir, "Echolocate")
            
            apk_files = glob.glob(os.path.join(echolocate_dir, "*.apk"))
            
            if not apk_files:
                # 没有找到APK文件，让用户选择
                apk_file, _ = QFileDialog.getOpenFileName(
                    None,
                    "选择Echolocate APK文件",
                    "",
                    "APK文件 (*.apk);;所有文件 (*.*)"
                )
                
                if not apk_file:
                    return
                
                apk_files = [apk_file]
            
            # 安装APK
            self.status_message.emit(f"正在安装 {len(apk_files)} 个APK文件...")
            
            for apk_file in apk_files:
                result = subprocess.run(
                    ["adb", "-s", device, "install", "-r", apk_file],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                if result.returncode != 0:
                    self.status_message.emit(f"APK安装失败: {os.path.basename(apk_file)}")
                    return
            
            # 启动应用
            subprocess.run(
                ["adb", "-s", device, "shell", "am", "start", "-n", "com.tmobile.echolocate/.playground.activities.OEMToolHomeActivity"],
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            self.echolocate_installed.emit()
            self.status_message.emit("Echolocate安装完成并已启动")
            
        except Exception as e:
            self.status_message.emit(f"安装Echolocate失败: {str(e)}")
    
    def trigger_echolocate(self):
        """触发Echolocate"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        try:
            subprocess.run(
                ["adb", "-s", device, "shell", "am", "start", "-n", "com.tmobile.echolocate/.playground.activities.OEMToolHomeActivity"],
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            self.echolocate_triggered.emit()
            self.status_message.emit("Echolocate应用已启动")
            
        except Exception as e:
            self.status_message.emit(f"启动Echolocate失败: {str(e)}")
    
    def pull_echolocate_file(self):
        """Pull Echolocate文件"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        try:
            self.status_message.emit("开始拉取Echolocate文件...")
            
            # 创建保存目录
            current_time = datetime.datetime.now()
            date_str = current_time.strftime("%Y%m%d")
            target_dir = f"C:\\log\\{date_str}\\echolocate"
            os.makedirs(target_dir, exist_ok=True)
            
            # 拉取文件
            pull_cmd = ["adb", "-s", device, "pull", "/sdcard/Download/echolocate", target_dir]
            result = subprocess.run(
                pull_cmd,
                capture_output=True,
                text=True,
                timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                self.file_pulled.emit(target_dir)
                self.status_message.emit(f"Echolocate文件已拉取到: {target_dir}")
                # 直接打开文件夹
                try:
                    os.startfile(target_dir)
                except Exception as e:
                    self.status_message.emit(f"打开文件夹失败: {str(e)}")
            else:
                self.status_message.emit(f"拉取Echolocate文件失败: {result.stderr.strip()}")
                
        except Exception as e:
            self.status_message.emit(f"拉取Echolocate文件失败: {str(e)}")
    
    def delete_echolocate_file(self):
        """删除Echolocate文件"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        try:
            subprocess.run(
                ["adb", "-s", device, "shell", "rm", "-rf", "/sdcard/Download/echolocate"],
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            self.file_deleted.emit()
            self.status_message.emit("Echolocate文件已删除")
            
        except Exception as e:
            self.status_message.emit(f"删除Echolocate文件失败: {str(e)}")
    
    def filter_callid(self):
        """过滤CallID"""
        self._filter_echolocate("CallID")
    
    def filter_callstate(self):
        """过滤CallState"""
        self._filter_echolocate("CallState")
    
    def filter_uicallstate(self):
        """过滤UICallState"""
        self._filter_echolocate("UICallState")
    
    def filter_allcallstate(self):
        """过滤AllCallState"""
        self._filter_echolocate("AllCallState")
    
    def filter_ims_signalling(self):
        """过滤IMSSignallingMessageLine1"""
        self._filter_echolocate("IMSSignallingMessageLine1")
    
    def filter_allcallflow(self):
        """过滤AllCallFlow"""
        self._filter_echolocate("AllCallFlow")
    
    def filter_voice_intent(self):
        """过滤voice_intent测试"""
        self._filter_echolocate("voice_intent")
    
    def _filter_echolocate(self, filter_type):
        """执行Echolocate过滤"""
        self.status_message.emit(f"执行{filter_type}过滤...")
        # TODO: 实现具体的过滤逻辑

