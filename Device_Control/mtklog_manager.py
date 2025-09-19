#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MTKLOG管理模块
负责MTKLOG的开启、停止、导出、删除和模式切换
"""

import subprocess
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
import os
import datetime
import time

class MTKLogManager:
    def __init__(self, app_instance):
        self.app = app_instance
    
    def start_mtklog(self):
        """开启MTKLOG"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        if not self.app.device_manager.check_mtklogger_exists(device):
            return
        
        # 定义后台工作函数
        def mtklog_start_worker(progress_var, status_label, progress_dialog):
            # 命令序列：停止logger -> 清除旧日志 -> 设置缓存大小 -> 开启logger
            commands = [
                # 1. 停止logger,加5s时间保护
                ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                 "-e", "cmd_name", "stop", "--ei", "cmd_target", "-1", "-n", "com.debug.loggerui/.framework.LogReceiver"],
                
                # 2. 清除旧日志,加2s时间保护
                ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                 "-e", "cmd_name", "clear_logs_all", "--ei", "cmd_target", "0", "-n", "com.debug.loggerui/.framework.LogReceiver"],
                
                # 3. 设置MD log缓存大小20GB,加1s时间保护
                ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                 "-e", "cmd_name", "set_log_size_20000", "--ei", "cmd_target", "2", "-n", "com.debug.loggerui/.framework.LogReceiver"],
                
                # 4. 开启MTK LOGGER
                ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                 "-e", "cmd_name", "start", "--ei", "cmd_target", "-1", "-n", "com.debug.loggerui/.framework.LogReceiver"]
            ]
            
            step_names = ["停止logger", "清除旧日志", "设置缓存大小", "开启logger"]
            
            # 执行命令序列
            for i, cmd in enumerate(commands, 1):
                # 更新状态
                status_label.config(text=f"步骤 {i}/4: {step_names[i-1]}")
                progress_var.set((i-1) * 25)
                progress_dialog.update()
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, 
                                      creationflags=subprocess.CREATE_NO_WINDOW)
                if result.returncode != 0:
                    error_msg = result.stderr.strip() if result.stderr else "未知错误"
                    raise Exception(f"开启MTKLOG失败 (步骤{i}): {error_msg}")
                
                # 更新进度
                progress_var.set(i * 25)
                progress_dialog.update()
                
                # 添加时间保护
                if i == 1:  # 停止logger后等待5秒
                    status_label.config(text="等待5秒...")
                    progress_dialog.update()
                    time.sleep(5)
                elif i == 2:  # 清除日志后等待2秒
                    status_label.config(text="等待2秒...")
                    progress_dialog.update()
                    time.sleep(2)
                elif i == 3:  # 设置缓存大小后等待1秒
                    status_label.config(text="等待1秒...")
                    progress_dialog.update()
                    time.sleep(1)
            time.sleep(5)   # 加5s时间保护等待开启完成
            # 完成
            status_label.config(text="完成!")
            progress_var.set(100)
            progress_dialog.update()
            
            return {"device": device}
        
        # 定义完成回调
        def on_mtklog_start_done(result):
            self.app.ui.status_var.set(f"MTKLOG已开启 - {result['device']}")
        
        # 定义错误回调
        def on_mtklog_start_error(error):
            messagebox.showerror("错误", f"开启MTKLOG时发生错误: {error}")
            self.app.ui.status_var.set("开启MTKLOG失败")
        
        # 使用模态执行器
        self.app.ui.run_with_modal("开启MTKLOG", mtklog_start_worker, on_mtklog_start_done, on_mtklog_start_error)
    
    def stop_and_export_mtklog(self):
        """停止并导出MTKLOG"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        if not self.app.device_manager.check_mtklogger_exists(device):
            return
        
        # 获取日志名称
        log_name = simpledialog.askstring("输入日志名称", "请输入日志名称:", parent=self.app.root)
        if not log_name:
            return
        
        # 定义后台工作函数
        def mtklog_worker(progress_var, status_label, progress_dialog):
            # 1. 停止logger命令,加5s时间保护
            status_label.config(text="停止logger...")
            progress_var.set(20)
            progress_dialog.update()
            
            stop_cmd = ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                       "-e", "cmd_name", "stop", "--ei", "cmd_target", "-1", "-n", "com.debug.loggerui/.framework.LogReceiver"]
            
            result = subprocess.run(stop_cmd, capture_output=True, text=True, timeout=15, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                raise Exception(f"停止logger失败: {result.stderr.strip()}")
            
            # 添加5秒时间保护
            status_label.config(text="等待5秒保护时间...")
            progress_dialog.update()
            time.sleep(5)
            
            # 2. 创建日志目录
            status_label.config(text="创建日志目录...")
            progress_var.set(40)
            progress_dialog.update()
            
            curredate = datetime.datetime.now().strftime("%Y%m%d")
            log_dir = f"c:\\log\\{curredate}"
            log_folder = f"{log_dir}\\log_{log_name}"
            
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # 3. 执行adb pull命令序列
            pull_commands = [
                ("/sdcard/TCTReport", "TCTReport"),
                ("/sdcard/mtklog", "mtklog"),
                ("/sdcard/debuglogger", "debuglogger"),
                ("/sdcard/logmanager", "logmanager"),
                ("/data/debuglogger", "data_debuglogger"),
                ("/sdcard/BugReport", "BugReport"),
                ("/data/media/logmanager", "data_logmanager")
            ]
            
            total_commands = len(pull_commands)
            
            for i, (source_path, folder_name) in enumerate(pull_commands):
                status_label.config(text=f"导出 {folder_name} ({i+1}/{total_commands})...")
                progress_var.set(50 + (i * 5))
                progress_dialog.update()
                
                # 执行adb pull
                cmd = ["adb", "-s", device, "pull", source_path, log_folder]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600, 
                                      creationflags=subprocess.CREATE_NO_WINDOW)
                
                if result.returncode != 0:
                    print(f"警告: {folder_name} 导出失败: {result.stderr.strip()}")
            
            # 4. 完成
            status_label.config(text="完成!")
            progress_var.set(100)
            progress_dialog.update()
            
            return {"log_folder": log_folder, "device": device}
        
        # 定义完成回调
        def on_mtklog_done(result):
            # 打开日志文件夹
            if result["log_folder"]:
                os.startfile(result["log_folder"])
            # 更新状态
            self.app.ui.status_var.set(f"MTKLOG已停止并导出 - {result['device']}")
        
        # 定义错误回调
        def on_mtklog_error(error):
            messagebox.showerror("错误", f"停止并导出MTKLOG时发生错误: {error}")
            self.app.ui.status_var.set("停止并导出MTKLOG失败")
        
        # 使用模态执行器
        self.app.ui.run_with_modal("停止并导出MTKLOG", mtklog_worker, on_mtklog_done, on_mtklog_error)
    
    def delete_mtklog(self):
        """删除MTKLOG"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        if not self.app.device_manager.check_mtklogger_exists(device):
            return
        
        # 定义后台工作函数
        def delete_worker(progress_var, status_label, progress_dialog):
            # 删除logger命令
            status_label.config(text="执行删除命令...")
            progress_var.set(50)
            progress_dialog.update()
            
            cmd = ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                   "-e", "cmd_name", "clear_logs_all", "--ei", "cmd_target", "0", "-n", "com.debug.loggerui/.framework.LogReceiver"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                raise Exception(f"删除MTKLOG失败: {error_msg}")
            
            # 完成
            status_label.config(text="删除完成!")
            progress_var.set(100)
            progress_dialog.update()
            
            return {"device": device}
        
        # 定义完成回调
        def on_delete_done(result):
            self.app.ui.status_var.set(f"MTKLOG已删除 - {result['device']}")
        
        # 定义错误回调
        def on_delete_error(error):
            messagebox.showerror("错误", f"删除MTKLOG时发生错误: {error}")
            self.app.ui.status_var.set("删除MTKLOG失败")
        
        # 使用模态执行器
        self.app.ui.run_with_modal("删除MTKLOG", delete_worker, on_delete_done, on_delete_error)
    
    def set_sd_mode(self):
        """设置SD模式"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        if not self.app.device_manager.check_mtklogger_exists(device):
            return
        
        try:
            cmd = ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                   "-e", "cmd_name", "switch_modem_log_mode_2", "--ei", "cmd_target", "1", "-n", "com.debug.loggerui/.framework.LogReceiver"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                messagebox.showinfo("成功", f"已设置为SD模式 \n(设备: {device})")
                self.app.ui.status_var.set(f"已设置为SD模式 - {device}")
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                messagebox.showerror("错误", f"设置SD模式失败:\n{error_msg}")
                self.app.ui.status_var.set("设置SD模式失败")
                
        except subprocess.TimeoutExpired:
            messagebox.showerror("错误", "设置SD模式超时，请检查设备连接")
            self.app.ui.status_var.set("设置SD模式超时")
        except FileNotFoundError:
            messagebox.showerror("错误", "未找到adb命令，请确保Android SDK已安装并配置PATH")
            self.app.ui.status_var.set("未找到adb命令")
        except Exception as e:
            messagebox.showerror("错误", f"设置SD模式时发生错误: {e}")
            self.app.ui.status_var.set("设置SD模式失败")
    
    def set_usb_mode(self):
        """设置USB模式"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        if not self.app.device_manager.check_mtklogger_exists(device):
            return
        
        try:
            cmd = ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                   "-e", "cmd_name", "switch_modem_log_mode_1", "--ei", "cmd_target", "1", "-n", "com.debug.loggerui/.framework.LogReceiver"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                messagebox.showinfo("成功", f"已设置为USB模式 \n(设备: {device})")
                self.app.ui.status_var.set(f"已设置为USB模式 - {device}")
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                messagebox.showerror("错误", f"设置USB模式失败:\n{error_msg}")
                self.app.ui.status_var.set("设置USB模式失败")
                
        except subprocess.TimeoutExpired:
            messagebox.showerror("错误", "设置USB模式超时，请检查设备连接")
            self.app.ui.status_var.set("设置USB模式超时")
        except FileNotFoundError:
            messagebox.showerror("错误", "未找到adb命令，请确保Android SDK已安装并配置PATH")
            self.app.ui.status_var.set("未找到adb命令")
        except Exception as e:
            messagebox.showerror("错误", f"设置USB模式时发生错误: {e}")
            self.app.ui.status_var.set("设置USB模式失败")
    
    def install_mtklogger(self):
        """安装MTKLOGGER"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 选择APK文件
        apk_file = filedialog.askopenfilename(
            title="选择MTKLOGGER APK文件",
            filetypes=[("APK文件", "*.apk"), ("所有文件", "*.*")],
            parent=self.app.root
        )
        
        if not apk_file:
            return
        
        # 定义后台工作函数
        def install_worker(progress_var, status_label, progress_dialog):
            # 1. 安装MTKLOGGER
            status_label.config(text="安装MTKLOGGER...")
            progress_var.set(30)
            progress_dialog.update()
            
            install_cmd = ["adb", "-s", device, "install", "--bypass-low-target-sdk-block", apk_file]
            result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=120, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                raise Exception(f"安装失败: {error_msg}")
            
            # 检查安装结果
            if "Success" not in result.stdout and "success" not in result.stdout.lower():
                raise Exception(f"安装可能失败: {result.stdout.strip()}")
            
            # 2. 启动MTKLOGGER
            status_label.config(text="启动MTKLOGGER...")
            progress_var.set(70)
            progress_dialog.update()
            
            # 确保屏幕亮屏且解锁
            if not self.app.device_manager.ensure_screen_unlocked(device):
                raise Exception("无法确保屏幕状态")
            
            start_cmd = ["adb", "-s", device, "shell", "am", "start", "-n", "com.debug.loggerui/.MainActivity"]
            result = subprocess.run(start_cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                print(f"警告: 启动MTKLOGGER失败: {result.stderr.strip()}")
            
            # 4. 完成
            status_label.config(text="安装完成!")
            progress_var.set(100)
            progress_dialog.update()
            
            return {"device": device, "apk_file": apk_file}
        
        # 定义完成回调
        def on_install_done(result):
            messagebox.showinfo("成功", 
                f"MTKLOGGER安装成功!\n\n"
                f"设备: {result['device']}\n"
                f"APK文件: {result['apk_file']}\n\n"
                f"MTKLOGGER已启动，现在可以使用MTKLOG相关功能。")
            self.app.ui.status_var.set(f"MTKLOGGER安装成功 - {result['device']}")
        
        # 定义错误回调
        def on_install_error(error):
            messagebox.showerror("错误", f"安装MTKLOGGER时发生错误: {error}")
            self.app.ui.status_var.set("安装MTKLOGGER失败")
        
        # 使用模态执行器
        self.app.ui.run_with_modal("安装MTKLOGGER", install_worker, on_install_done, on_install_error)
    
