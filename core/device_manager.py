#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5设备管理器
适配原Tkinter版本的设备管理功能
"""

import subprocess
from PyQt5.QtCore import QObject, pyqtSignal


class PyQtDeviceManager(QObject):
    """PyQt5设备管理器"""
    
    # 信号定义
    devices_updated = pyqtSignal(list)  # 设备列表更新
    device_selected = pyqtSignal(str)   # 设备选择变化
    status_message = pyqtSignal(str)    # 状态消息
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.available_devices = []
        self.selected_device = ""
        # 从父窗口获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            # 如果没有父窗口或语言管理器，使用单例
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager.get_instance()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
        
    def refresh_devices(self):
        """刷新可用设备列表"""
        try:
            # 执行adb devices命令
            result = subprocess.run(
                ["adb", "devices"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                # 解析设备列表
                lines = result.stdout.strip().split('\n')[1:]  # 跳过第一行标题
                self.available_devices = []
                
                for line in lines:
                    line = line.strip()
                    if line and ('device' in line or 'unauthorized' in line or 'offline' in line):
                        parts = line.split()
                        if len(parts) >= 2:
                            device_id = parts[0]
                            status = parts[1]
                            if status == 'device':
                                self.available_devices.append(device_id)
                
                # 发送设备列表更新信号
                self.devices_updated.emit(self.available_devices)
                
                # 如果只有一个设备，自动选择
                if len(self.available_devices) == 1:
                    self.selected_device = self.available_devices[0]
                    self.device_selected.emit(self.selected_device)
                    self.status_message.emit(f"{self.lang_manager.tr('检测到')} {len(self.available_devices)} {self.lang_manager.tr('个设备，已自动选择')}")
                elif len(self.available_devices) > 1:
                    self.status_message.emit(f"{self.lang_manager.tr('检测到')} {len(self.available_devices)} {self.lang_manager.tr('个设备，请选择一个')}")
                else:
                    self.status_message.emit(self.lang_manager.tr("未检测到设备"))
                    
            else:
                error_msg = result.stderr.strip() if result.stderr else self.lang_manager.tr("未知错误")
                self.status_message.emit("❌ " + self.tr("设备检测失败: ") + str(error_msg))
                
        except subprocess.TimeoutExpired:
            self.status_message.emit(self.lang_manager.tr("设备检测超时"))
        except FileNotFoundError:
            self.status_message.emit(self.lang_manager.tr("未找到adb命令，请确保adb已安装并添加到PATH"))
        except Exception as e:
            self.status_message.emit("❌ " + self.tr("设备检测错误: ") + str(e))
    
    def validate_device_selection(self):
        """验证设备选择"""
        if not self.selected_device or self.selected_device == self.lang_manager.tr("无设备"):
            self.status_message.emit(self.lang_manager.tr("请先选择一个设备"))
            return None
        
        # 检查设备是否真正连接
        if not self.check_device_connection(self.selected_device):
            return None
            
        return self.selected_device
    
    def check_device_connection(self, device):
        """检查设备连接状态"""
        try:
            devices_cmd = ["adb", "devices"]
            result = subprocess.run(devices_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                self.status_message.emit(self.lang_manager.tr("检查设备连接失败"))
                return False
            
            # 检查设备是否在列表中且状态为device（已连接）
            device_connected = False
            for line in result.stdout.strip().split('\n'):
                if device in line and 'device' in line:
                    device_connected = True
                    break
            
            if not device_connected:
                self.status_message.emit(self.tr("设备 ") + device + self.tr(" 未连接或连接异常"))
                return False
            
            return True
                
        except subprocess.TimeoutExpired:
            self.status_message.emit(self.lang_manager.tr("检查设备连接超时"))
            return False
        except FileNotFoundError:
            self.status_message.emit(self.lang_manager.tr("未找到adb命令，请确保Android SDK已安装并配置PATH"))
            return False
        except Exception as e:
            self.status_message.emit("❌ " + self.tr("检查设备连接时发生错误: ") + str(e))
            return False
    
    def set_selected_device(self, device):
        """设置选中的设备"""
        if device in self.available_devices:
            self.selected_device = device
            self.device_selected.emit(device)
            return True
        return False
    
    def ensure_screen_unlocked(self, device):
        """确保屏幕亮屏且解锁状态"""
        try:
            # 1. 检查屏幕是否亮屏
            screen_on = self._check_screen_on(device)
            if not screen_on:
                self._wake_screen(device)
            
            # 2. 检查屏幕是否解锁
            screen_unlocked = self._check_screen_unlocked(device)
            if not screen_unlocked:
                self._unlock_screen(device)
            
            return True
            
        except Exception as e:
            self.status_message.emit("❌ " + self.tr("检查屏幕状态时发生错误: ") + str(e))
            return False
    
    def _check_screen_on(self, device):
        """检查屏幕是否亮屏"""
        try:
            cmd = ["adb", "-s", device, "shell", "dumpsys", "deviceidle"]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=10, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode == 0:
                # 查找 mScreenOn 状态
                for line in result.stdout.split('\n'):
                    if 'mScreenOn' in line:
                        return 'true' in line.lower()
            
            return False
            
        except Exception:
            return False
    
    def _check_screen_unlocked(self, device):
        """检查屏幕是否解锁"""
        try:
            cmd = ["adb", "-s", device, "shell", "dumpsys", "deviceidle"]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=10, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode == 0:
                # 查找 mScreenLocked 状态
                for line in result.stdout.split('\n'):
                    if 'mScreenLocked' in line:
                        return 'false' in line.lower()  # false表示解锁状态
            
            return False
            
        except Exception:
            return False
    
    def _wake_screen(self, device):
        """点亮屏幕"""
        try:
            cmd = ["adb", "-s", device, "shell", "input", "keyevent", "224"]
            subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=10, 
                          creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
        except Exception:
            pass
    
    def _unlock_screen(self, device):
        """解锁屏幕"""
        try:
            cmd = ["adb", "-s", device, "shell", "input", "keyevent", "82"]
            subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=10, 
                          creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
        except Exception:
            pass

