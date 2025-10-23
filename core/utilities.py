#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用工具函数
包含设备操作、adb命令等通用功能
"""

import subprocess
import time
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QMessageBox


class RebootDeviceWorker(QThread):
    """异步重启设备Worker"""
    
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, device, lang_manager=None):
        super().__init__()
        self.device = device
        self.lang_manager = lang_manager
    
    def run(self):
        """执行重启命令"""
        try:
            result = subprocess.run(
                ["adb", "-s", self.device, "reboot"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                self.finished.emit(True, f"{self.lang_manager.tr('设备')} {self.device} {self.lang_manager.tr('重启命令已执行')}")
            else:
                error_msg = result.stderr.strip() if result.stderr else (self.tr("未知错误") if self.lang_manager else "未知错误")
                self.finished.emit(False, f"{self.lang_manager.tr('重启设备失败:')} {error_msg}")
                
        except subprocess.TimeoutExpired:
            self.finished.emit(False, self.tr("重启设备超时，请检查设备连接"))
        except FileNotFoundError:
            self.finished.emit(False, self.tr("未找到adb命令，请确保Android SDK已安装并配置PATH"))
        except Exception as e:
            self.finished.emit(False, f"{self.lang_manager.tr('重启设备时发生错误:')} {e}")


class DeviceUtilities(QObject):
    """设备通用工具类"""
    
    # 信号定义
    status_message = pyqtSignal(str)
    reboot_started = pyqtSignal(str)  # device
    reboot_finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def reboot_device(self, parent_widget=None):
        """重启设备（异步执行）"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return False
        
        reply = QMessageBox.question(
            parent_widget,
            self.tr("确认重启"),
            f"{self.tr('确定要重启设备')} {device} {self.tr('吗？')}\n\n{self.tr('这将执行')} 'adb reboot' {self.tr('命令')}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return False
        
        # 创建并启动异步Worker
        self.reboot_worker = RebootDeviceWorker(device, self.lang_manager)
        self.reboot_worker.finished.connect(self._on_reboot_finished)
        
        # 发送开始信号
        self.reboot_started.emit(device)
        self.status_message.emit(f"{self.lang_manager.tr('正在重启设备')} {device}...")
        
        # 启动Worker线程
        self.reboot_worker.start()
        
        return True  # 立即返回，表示重启命令已开始
    
    def _on_reboot_finished(self, success, message):
        """重启完成回调"""
        self.reboot_finished.emit(success, message)
        if success:
            self.status_message.emit(message)
        else:
            self.status_message.emit(f"{self.lang_manager.tr('重启失败:')} {message}")
        
        # 清理Worker
        if hasattr(self, 'reboot_worker'):
            self.reboot_worker.deleteLater()
            delattr(self, 'reboot_worker')
    
    def clear_device_logs(self, parent_widget=None):
        """清除设备日志缓存"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return False
        
        reply = QMessageBox.question(
            parent_widget,
            self.tr("确认"),
            self.tr("确定要清除设备上的日志缓存吗？\n\n这将执行 'adb logcat -c' 命令"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return False
        
        try:
            result = subprocess.run(
                ["adb", "-s", device, "logcat", "-c"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                self.status_message.emit(self.tr("设备日志缓存已清除"))
                return True
            else:
                error_msg = result.stderr.strip() if result.stderr else self.tr("未知错误")
                QMessageBox.critical(parent_widget, self.tr("错误"), f"清除设备日志缓存失败:\n{error_msg}")
                self.status_message.emit(self.tr("清除设备日志缓存失败"))
                return False
                
        except subprocess.TimeoutExpired:
            QMessageBox.critical(parent_widget, self.tr("错误"), "清除设备日志缓存超时，请检查设备连接")
            self.status_message.emit(self.tr("清除设备日志缓存超时"))
            return False
        except FileNotFoundError:
            QMessageBox.critical(parent_widget, self.tr("错误"), "未找到adb命令，请确保Android SDK已安装并配置PATH")
            self.status_message.emit(self.tr("未找到adb命令"))
            return False
        except Exception as e:
            QMessageBox.critical(parent_widget, self.tr("错误"), f"清除设备日志缓存时发生错误: {e}")
            self.status_message.emit(self.tr("清除设备日志缓存失败"))
            return False
    
    def execute_adb_command(self, command, parent_widget=None, timeout=30):
        """执行通用adb命令"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return False, self.tr("请先选择设备")
        
        try:
            # 构建完整的adb命令
            if isinstance(command, str):
                cmd_parts = command.split()
            else:
                cmd_parts = command
            
            # 确保命令以adb开头
            if not cmd_parts[0] == "adb":
                cmd_parts.insert(0, "adb")
            
            # 插入设备参数
            if "-s" not in cmd_parts:
                cmd_parts.insert(1, "-s")
                cmd_parts.insert(2, device)
            
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                self.status_message.emit(f"{self.lang_manager.tr('命令执行成功:')} {' '.join(cmd_parts)}")
                return True, result.stdout.strip()
            else:
                error_msg = result.stderr.strip() if result.stderr else self.tr("未知错误")
                self.status_message.emit(f"{self.lang_manager.tr('命令执行失败:')} {error_msg}")
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            self.status_message.emit(self.tr("命令执行超时"))
            return False, self.tr("命令执行超时")
        except FileNotFoundError:
            self.status_message.emit(self.tr("未找到adb命令"))
            return False, self.tr("未找到adb命令，请确保Android SDK已安装并配置PATH")
        except Exception as e:
            self.status_message.emit(f"{self.lang_manager.tr('命令执行时发生错误:')} {e}")
            return False, f"{self.tr('命令执行时发生错误:')} {e}"
    
    def get_device_info(self):
        """获取设备信息"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return None
        
        info = {}
        
        # 获取设备型号
        success, output = self.execute_adb_command("shell getprop ro.product.model")
        if success:
            info['model'] = output
        
        # 获取Android版本
        success, output = self.execute_adb_command("shell getprop ro.build.version.release")
        if success:
            info['android_version'] = output
        
        # 获取API级别
        success, output = self.execute_adb_command("shell getprop ro.build.version.sdk")
        if success:
            info['api_level'] = output
        
        # 获取设备制造商
        success, output = self.execute_adb_command("shell getprop ro.product.manufacturer")
        if success:
            info['manufacturer'] = output
        
        return info if info else None
    
    def wait_for_device(self, timeout=60):
        """等待设备连接"""
        device = self.device_manager.selected_device
        if not device:
            return False
        
        try:
            result = subprocess.run(
                ["adb", "-s", device, "wait-for-device"],
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                self.status_message.emit(f"{self.lang_manager.tr('设备')} {device} {self.lang_manager.tr('已连接')}")
                return True
            else:
                self.status_message.emit(f"{self.lang_manager.tr('等待设备')} {device} {self.lang_manager.tr('连接超时')}")
                return False
                
        except subprocess.TimeoutExpired:
            self.status_message.emit(f"{self.lang_manager.tr('等待设备')} {device} {self.lang_manager.tr('连接超时')}")
            return False
        except Exception as e:
            self.status_message.emit(f"{self.lang_manager.tr('等待设备连接时发生错误:')} {e}")
            return False
