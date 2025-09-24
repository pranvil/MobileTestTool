#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
截图管理模块
负责设备截图功能
"""

import subprocess
import tkinter as tk
from tkinter import messagebox
import os
import datetime

class ScreenshotManager:
    def __init__(self, app_instance):
        self.app = app_instance
    
    def take_screenshot(self):
        """截图功能"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 定义后台工作函数
        def screenshot_worker(progress_var, status_label, progress_dialog, stop_flag):
            # 检查是否被要求停止
            if stop_flag and stop_flag.is_set():
                return {"success": False, "message": "操作已取消"}
            
            # 1. 检查并创建screenshot文件夹
            status_label.config(text="检查截图文件夹...")
            progress_var.set(20)
            progress_dialog.update()
            
            # 创建统一的日志目录路径 c:\log\yyyymmdd\screenshot
            current_time = datetime.datetime.now()
            date_str = current_time.strftime("%Y%m%d")
            log_dir = f"c:\\log\\{date_str}"
            screenshot_folder = os.path.join(log_dir, "screenshot")
            
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                print(f"创建日志目录: {log_dir}")
            if not os.path.exists(screenshot_folder):
                os.makedirs(screenshot_folder)
                print(f"创建截图文件夹: {screenshot_folder}")
            
            # 2. 等待设备连接
            status_label.config(text="等待设备连接...")
            progress_var.set(40)
            progress_dialog.update()
            
            wait_cmd = ["adb", "-s", device, "wait-for-device"]
            result = subprocess.run(wait_cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                raise Exception(f"设备连接失败: {result.stderr.strip()}")
            
            # 3. 设备截图
            status_label.config(text="正在截图...")
            progress_var.set(60)
            progress_dialog.update()
            
            screencap_cmd = ["adb", "-s", device, "shell", "/system/bin/screencap", "-p", "/sdcard/screenshot.png"]
            result = subprocess.run(screencap_cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                raise Exception(f"截图失败: {result.stderr.strip()}")
            
            # 4. 再次等待设备
            status_label.config(text="等待设备就绪...")
            progress_var.set(80)
            progress_dialog.update()
            
            wait_cmd2 = ["adb", "-s", device, "wait-for-device"]
            subprocess.run(wait_cmd2, capture_output=True, text=True, timeout=30, 
                         creationflags=subprocess.CREATE_NO_WINDOW)
            
            # 5. 生成文件名并拉取截图
            status_label.config(text="保存截图...")
            progress_var.set(90)
            progress_dialog.update()
            
            # 生成时间戳文件名
            current_time = datetime.datetime.now()
            time_str = current_time.strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{time_str}.png"
            local_path = os.path.join(screenshot_folder, filename)
            
            pull_cmd = ["adb", "-s", device, "pull", "/sdcard/screenshot.png", local_path]
            result = subprocess.run(pull_cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                raise Exception(f"保存截图失败: {result.stderr.strip()}")
            
            # 6. 完成
            status_label.config(text="截图完成!")
            progress_var.set(100)
            progress_dialog.update()
            
            return {"screenshot_folder": screenshot_folder, "filename": filename, "device": device}
        
        # 定义完成回调
        def on_screenshot_done(result):
            if result.get("success") == False and result.get("message") == "操作已取消":
                self.app.ui.status_var.set("操作已取消")
            else:
                # 打开截图文件夹
                if result["screenshot_folder"]:
                    os.startfile(result["screenshot_folder"])
                # 更新状态
                self.app.ui.status_var.set(f"截图已保存 - {result['device']} - {result['filename']}")
        
        # 定义错误回调
        def on_screenshot_error(error):
            messagebox.showerror("错误", f"截图时发生错误: {error}")
            self.app.ui.status_var.set("截图失败")
        
        # 使用模态执行器
        self.app.ui.run_with_modal("截图", screenshot_worker, on_screenshot_done, on_screenshot_error)
