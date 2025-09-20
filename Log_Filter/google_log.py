#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google日志管理模块
负责Google日志的收集和管理
"""

import subprocess
import os
import datetime
import threading


class GoogleLogManager:
    def __init__(self, app_instance):
        self.app = app_instance
        self.google_log_running = False
        self.google_log_folder = None
    
    def start_google_log(self, device, ui_manager):
        """开始Google日志收集"""
        # 定义后台工作函数
        def google_log_worker(progress_var, status_label, progress_dialog):
            # 1. 创建日志目录
            status_label.config(text="创建Google日志目录...")
            progress_var.set(10)
            progress_dialog.update()
            
            current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.google_log_folder = f"C:\\log\\Google_log_{current_time}"
            
            if not os.path.exists(self.google_log_folder):
                os.makedirs(self.google_log_folder)
            
            # 2. 执行Google日志相关命令
            status_label.config(text="配置Google日志设置...")
            progress_var.set(20)
            progress_dialog.update()
            
            commands = [
                ["adb", "-s", device, "shell", "logcat", "-G", "16M"],
                ["adb", "-s", device, "logcat", "-c"],
                ["adb", "-s", device, "shell", "getprop", "|", "findstr", "fingerprint"],
                ["adb", "-s", device, "shell", "getprop", "|", "findstr", "gms"],
                ["adb", "-s", device, "shell", "getprop", "|", "findstr", "model"],
                ["adb", "-s", device, "shell", "wm", "size"],
                ["adb", "-s", device, "shell", "setprop", "log.tag.Telecom", "VERBOSE"],
                ["adb", "-s", device, "shell", "setprop", "log.tag.Telephony", "VERBOSE"],
                ["adb", "-s", device, "shell", "setprop", "log.tag.InCall", "VERBOSE"],
                ["adb", "-s", device, "shell", "setprop", "log.tag.TelecomFramework", "VERBOSE"],
                ["adb", "-s", device, "shell", "setprop", "log.tag.ImsCall", "VERBOSE"],
                ["adb", "-s", device, "shell", "setprop", "log.tag.Dialer", "VERBOSE"]
            ]
            
            # 执行命令
            other_info_file = os.path.join(self.google_log_folder, "otherInfo.txt")
            
            # 前两个命令直接执行
            for i in range(2):
                status_label.config(text=f"执行命令 {i+1}/2...")
                progress_var.set(20 + (i * 5))
                progress_dialog.update()
                subprocess.run(commands[i], capture_output=True, text=True, timeout=30, 
                             creationflags=subprocess.CREATE_NO_WINDOW)
            
            # 后面的命令需要写入文件
            with open(other_info_file, 'w', encoding='utf-8') as f:
                for i in range(2, len(commands)):
                    status_label.config(text=f"收集设备信息 {i-1}/{len(commands)-2}...")
                    progress_var.set(30 + ((i-2) * 8))
                    progress_dialog.update()
                    
                    # 重新构建命令，使用shell执行管道
                    if i == 2:  # fingerprint
                        cmd_str = f"adb -s {device} shell getprop | findstr fingerprint"
                    elif i == 3:  # gms
                        cmd_str = f"adb -s {device} shell getprop | findstr gms"
                    elif i == 4:  # model
                        cmd_str = f"adb -s {device} shell getprop | findstr model"
                    elif i == 5:  # wm size
                        cmd_str = f"adb -s {device} shell wm size"
                    
                    result = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, timeout=30)
                    if result.returncode == 0 and result.stdout.strip():
                        f.write(result.stdout + "\n")
                
                # 执行setprop命令
                for i in range(6, len(commands)):
                    status_label.config(text=f"设置日志级别 {i-5}/{len(commands)-6}...")
                    progress_var.set(60 + ((i-6) * 3))
                    progress_dialog.update()
                    subprocess.run(commands[i], capture_output=True, text=True, timeout=30, 
                                 creationflags=subprocess.CREATE_NO_WINDOW)
            
            # 3. 启动ADB日志
            status_label.config(text="启动ADB日志...")
            progress_var.set(80)
            progress_dialog.update()
            
            # 调用ADB日志管理器启动日志
            log_name = f"adb_log"
            success = self.app.adblog_manager.start_google_adblog(device, log_name, self.google_log_folder)
            if not success:
                raise Exception("启动ADB日志失败")
            
            # 4. 启动视频录制
            status_label.config(text="启动视频录制...")
            progress_var.set(90)
            progress_dialog.update()
            
            # 调用视频管理器开始录制
            success = self.app.video_manager.start_google_recording(device, self.google_log_folder)
            if not success:
                raise Exception("启动视频录制失败")
            
            # 5. 完成
            status_label.config(text="Google日志收集已启动!")
            progress_var.set(100)
            progress_dialog.update()
            
            return {"folder": self.google_log_folder, "device": device}
        
        # 定义完成回调
        def on_google_log_start_done(result):
            self.google_log_running = True
            ui_manager.google_log_button.config(text="停止Google日志")
            self.app.ui.status_var.set(f"Google日志收集已启动 - {result['folder']}")
        
        # 定义错误回调
        def on_google_log_start_error(error):
            from tkinter import messagebox
            messagebox.showerror("错误", f"启动Google日志收集时发生错误: {error}")
            self.app.ui.status_var.set("启动Google日志收集失败")
        
        # 使用模态执行器
        ui_manager.run_with_modal("启动Google日志收集", google_log_worker, on_google_log_start_done, on_google_log_start_error)
    
    def start_bugreport_only(self, device, ui_manager):
        """仅执行bugreport"""
        # 定义后台工作函数
        def bugreport_only_worker(progress_var, status_label, progress_dialog):
            # 1. 创建日志目录
            status_label.config(text="创建Google日志目录...")
            progress_var.set(20)
            progress_dialog.update()
            
            current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.google_log_folder = f"C:\\log\\Google_log_{current_time}"
            
            if not os.path.exists(self.google_log_folder):
                os.makedirs(self.google_log_folder)
            
            # 2. 执行bugreport
            status_label.config(text="生成bugreport...")
            progress_var.set(50)
            progress_dialog.update()
            
            bugreport_cmd = ["adb", "-s", device, "bugreport", self.google_log_folder]
            result = subprocess.run(bugreport_cmd, capture_output=True, text=True, timeout=300, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                raise Exception(f"bugreport执行失败: {result.stderr.strip()}")
            
            # 3. 完成
            status_label.config(text="bugreport生成完成!")
            progress_var.set(100)
            progress_dialog.update()
            
            return {"folder": self.google_log_folder, "device": device}
        
        # 定义完成回调
        def on_bugreport_done(result):
            ui_manager.google_log_button.config(text="Google日志")
            self.app.ui.status_var.set(f"bugreport生成完成 - {result['folder']}")
            
            # 打开日志文件夹
            if result["folder"]:
                os.startfile(result["folder"])
        
        # 定义错误回调
        def on_bugreport_error(error):
            from tkinter import messagebox
            messagebox.showerror("错误", f"生成bugreport时发生错误: {error}")
            self.app.ui.status_var.set("生成bugreport失败")
        
        # 使用模态执行器
        ui_manager.run_with_modal("生成bugreport", bugreport_only_worker, on_bugreport_done, on_bugreport_error)
    
    def stop_google_log(self, device, ui_manager):
        """停止Google日志收集"""
        # 定义后台工作函数
        def google_log_stop_worker(progress_var, status_label, progress_dialog):
            # 1. 停止ADB日志并导出
            status_label.config(text="停止ADB日志并导出...")
            progress_var.set(25)
            progress_dialog.update()
            
            # 调用ADB日志管理器停止并导出到指定目录
            success = self.app.adblog_manager.stop_and_export_to_folder(device, self.google_log_folder)
            if not success:
                print("警告: ADB日志停止导出失败")
            
            # 2. 停止视频录制并导出
            status_label.config(text="停止视频录制并导出...")
            progress_var.set(50)
            progress_dialog.update()
            
            # 调用视频管理器停止录制并导出到指定目录
            success = self.app.video_manager.stop_and_export_to_folder(device, self.google_log_folder)
            if not success:
                print("警告: 视频录制停止导出失败")
            
            # 3. 执行bugreport
            status_label.config(text="生成bugreport...")
            progress_var.set(75)
            progress_dialog.update()
            
            bugreport_cmd = ["adb", "-s", device, "bugreport", self.google_log_folder]
            result = subprocess.run(bugreport_cmd, capture_output=True, text=True, timeout=300, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                print(f"警告: bugreport执行失败: {result.stderr.strip()}")
            
            # 4. 完成
            status_label.config(text="Google日志收集已完成!")
            progress_var.set(100)
            progress_dialog.update()
            
            return {"folder": self.google_log_folder, "device": device}
        
        # 定义完成回调
        def on_google_log_stop_done(result):
            self.google_log_running = False
            ui_manager.google_log_button.config(text="Google日志")
            self.app.ui.status_var.set(f"Google日志收集已完成 - {result['folder']}")
            
            # 打开日志文件夹
            if result["folder"]:
                os.startfile(result["folder"])
        
        # 定义错误回调
        def on_google_log_stop_error(error):
            self.google_log_running = False
            ui_manager.google_log_button.config(text="Google日志")
            from tkinter import messagebox
            messagebox.showerror("错误", f"停止Google日志收集时发生错误: {error}")
            self.app.ui.status_var.set("停止Google日志收集失败")
        
        # 使用模态执行器
        ui_manager.run_with_modal("停止Google日志收集", google_log_stop_worker, on_google_log_stop_done, on_google_log_stop_error)
    
    def is_running(self):
        """检查Google日志是否正在运行"""
        return self.google_log_running
