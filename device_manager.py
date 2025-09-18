#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备管理模块
负责设备连接、检测和管理
"""

import subprocess
import tkinter as tk
from tkinter import messagebox

class DeviceManager:
    def __init__(self, app_instance):
        self.app = app_instance
    
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
                self.app.available_devices = []
                
                for line in lines:
                    if line.strip() and '\tdevice' in line:
                        device_id = line.split('\t')[0].strip()
                        self.app.available_devices.append(device_id)
                
                # 更新下拉框
                if self.app.ui.device_combo:
                    self.app.ui.device_combo['values'] = self.app.available_devices
                    
                    # 如果只有一个设备，自动选择
                    if len(self.app.available_devices) == 1:
                        self.app.selected_device.set(self.app.available_devices[0])
                    elif len(self.app.available_devices) > 1:
                        # 多个设备时，清空选择
                        self.app.selected_device.set("")
                    else:
                        # 没有设备
                        self.app.selected_device.set("无设备")
                        
                self.app.ui.status_var.set(f"检测到 {len(self.app.available_devices)} 个设备")
                
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                self.app.ui.status_var.set(f"设备检测失败: {error_msg}")
                if self.app.ui.device_combo:
                    self.app.ui.device_combo['values'] = ["检测失败"]
                    self.app.selected_device.set("检测失败")
                
        except subprocess.TimeoutExpired:
            self.app.ui.status_var.set("设备检测超时")
            if self.app.ui.device_combo:
                self.app.ui.device_combo['values'] = ["检测超时"]
                self.app.selected_device.set("检测超时")
        except FileNotFoundError:
            self.app.ui.status_var.set("未找到adb命令")
            if self.app.ui.device_combo:
                self.app.ui.device_combo['values'] = ["adb未安装"]
                self.app.selected_device.set("adb未安装")
        except Exception as e:
            self.app.ui.status_var.set(f"设备检测错误: {e}")
            if self.app.ui.device_combo:
                self.app.ui.device_combo['values'] = ["检测错误"]
                self.app.selected_device.set("检测错误")
    
    def check_device_connection(self, device):
        """检查设备连接状态"""
        try:
            devices_cmd = ["adb", "devices"]
            result = subprocess.run(devices_cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                messagebox.showerror("错误", "检查设备连接失败")
                self.app.ui.status_var.set("检查设备连接失败")
                return False
            
            # 检查设备是否在列表中
            if device not in result.stdout:
                messagebox.showerror("错误", f"设备 {device} 未连接")
                self.app.ui.status_var.set(f"设备 {device} 未连接")
                return False
            
            return True
                
        except Exception as e:
            messagebox.showerror("错误", f"检查设备连接时发生错误: {e}")
            self.app.ui.status_var.set("检查设备连接失败")
            return False
    
    def check_mtklogger_exists(self, device):
        """检查MTKlogger是否存在"""
        try:
            check_cmd = ["adb", "-s", device, "shell", "am", "start", "-n", "com.debug.loggerui/.MainActivity"]
            result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0 or "Error type 3" in result.stderr or "does not exist" in result.stderr:
                messagebox.showerror("错误", 
                    f"MTKlogger不存在，需要安装\n\n"
                    f"设备: {device}\n"
                    f"错误信息: {result.stderr.strip() if result.stderr else 'MTKlogger未安装'}\n\n"
                    f"请先安装MTKlogger工具后再使用此功能")
                self.app.ui.status_var.set("MTKlogger不存在，需要安装")
                return False
            
            return True
                
        except Exception as e:
            messagebox.showerror("错误", f"检查MTKlogger时发生错误: {e}")
            self.app.ui.status_var.set("检查MTKlogger失败")
            return False
    
    def get_selected_device(self):
        """获取当前选择的设备"""
        device = self.app.selected_device.get()
        if not device or device in ["无设备", "检测失败", "检测超时", "adb未安装", "检测错误"]:
            messagebox.showerror("错误", "请先选择有效设备")
            return None
        return device
    
    def validate_device_selection(self):
        """验证设备选择"""
        device = self.get_selected_device()
        if not device:
            return None
        
        if not self.check_device_connection(device):
            return None
        
        return device
