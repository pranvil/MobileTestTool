#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AEE日志管理模块
负责AEE日志的打包和导出
"""

import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog
import os
import datetime
import time
import threading

class AEELogManager:
    def __init__(self, app_instance):
        self.app = app_instance
        self.is_running = False
        self.waiting_thread = None
        self.original_button_text = "aee log"
    
    def start_aee_log(self):
        """开始AEE日志收集"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        try:
            # 1. 检查com.tcl.logger是否已安装
            self.app.ui.status_var.set("检查com.tcl.logger是否已安装...")
            
            if not self._check_tcl_logger_installed(device):
                # 如果未安装，开始安装流程
                self._handle_installation(device)
                return
            
            # 2. 执行AEE日志打包命令
            self.app.ui.status_var.set("执行AEE日志打包命令...")
            
            pack_cmd = ["adb", "-s", device, "shell", "am", "startservice", 
                       "-n", "com.tcl.logger/com.tcl.logger.service.ClearLogService", 
                       "-a", "com.tcl.logger.packlog"]
            
            result = subprocess.run(pack_cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                raise Exception(f"执行AEE日志打包命令失败: {result.stderr.strip()}")
            
            # 3. 显示提示并开始等待
            self.app.ui.status_var.set("AEE日志打包命令已执行")
            
            # 确保消息框显示在前台
            self.app.root.lift()
            self.app.root.attributes('-topmost', True)
            messagebox.showinfo("提示", "log打包中，保持手机连接5分钟")
            self.app.root.attributes('-topmost', False)
            
            # 更新状态
            self.is_running = True
            self.app.ui.status_var.set(f"AEE log打包中 - {device}")
            
            # 在后台线程中等待并拉取日志
            self.waiting_thread = threading.Thread(target=self._wait_and_pull_logs, args=(device,), daemon=True)
            self.waiting_thread.start()
            
        except Exception as e:
            error_msg = f"启动AEE log时发生错误: {e}"
            print(error_msg)
            self.app.root.lift()
            self.app.root.attributes('-topmost', True)
            messagebox.showerror("错误", error_msg)
            self.app.root.attributes('-topmost', False)
            self.app.ui.status_var.set("启动AEE log失败")
    
    def _handle_installation(self, device):
        """处理com.tcl.logger安装流程"""
        try:
            # 循环询问用户是否安装，直到安装成功或用户取消
            while True:
                # 确保消息框显示在前台
                self.app.root.lift()
                self.app.root.attributes('-topmost', True)
                
                if messagebox.askyesno("安装提示", 
                    "com.tcl.logger未安装，是否选择APK文件进行安装？\n\n"
                    "点击'是'选择APK文件进行安装\n"
                    "点击'否'取消操作"):
                    
                    self.app.root.attributes('-topmost', False)
                    
                    # 选择APK文件
                    apk_file = filedialog.askopenfilename(
                        title="选择com.tcl.logger APK文件",
                        filetypes=[("APK文件", "*.apk"), ("所有文件", "*.*")],
                        parent=self.app.root
                    )
                    
                    if not apk_file:
                        self.app.ui.status_var.set("用户取消安装")
                        return
                    
                    # 安装APK
                    if self._install_tcl_logger(device, apk_file):
                        # 安装完成后再次检查包是否存在
                        if self._check_tcl_logger_installed(device):
                            # 安装成功，重新启动AEE log流程
                            self.start_aee_log()
                            return
                        else:
                            # 安装后仍然没有找到包，继续询问
                            continue
                    else:
                        # 安装失败，继续询问
                        continue
                else:
                    self.app.root.attributes('-topmost', False)
                    self.app.ui.status_var.set("用户取消AEE log操作")
                    return
                    
        except Exception as e:
            error_msg = f"处理安装流程时发生错误: {e}"
            print(error_msg)
            self.app.root.lift()
            self.app.root.attributes('-topmost', True)
            messagebox.showerror("错误", error_msg)
            self.app.root.attributes('-topmost', False)
    
    def _check_tcl_logger_installed(self, device):
        """检查com.tcl.logger是否已安装"""
        try:
            cmd = ["adb", "-s", device, "shell", "pm", "list", "packages", "-e"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                return "com.tcl.logger" in result.stdout
            else:
                print(f"检查包列表失败: {result.stderr.strip()}")
                return False
                
        except Exception as e:
            print(f"检查com.tcl.logger安装状态时发生错误: {e}")
            return False
    
    def _install_tcl_logger(self, device, apk_file):
        """安装com.tcl.logger APK"""
        try:
            # 直接执行安装命令，不使用模态执行器，以便能够返回结果
            install_cmd = ["adb", "-s", device, "install", "--bypass-low-target-sdk-block", apk_file]
            result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=120, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "安装失败"
                messagebox.showerror("安装失败", f"APK安装失败:\n{error_msg}")
                return False
            
            # 检查安装结果
            if "Success" not in result.stdout and "success" not in result.stdout.lower():
                messagebox.showerror("安装失败", f"安装可能失败:\n{result.stdout.strip()}")
                return False
            
            # 等待安装完成
            time.sleep(2)
            
            # 验证安装
            if self._check_tcl_logger_installed(device):
                messagebox.showinfo("安装成功", 
                    f"com.tcl.logger安装成功!\n\n"
                    f"设备: {device}\n"
                    f"APK文件: {apk_file}")
                self.app.ui.status_var.set(f"com.tcl.logger安装成功 - {device}")
                return True
            else:
                messagebox.showerror("验证失败", "未找到usersupport应用，请确认安装了正确的apk")
                return False
            
        except Exception as e:
            error_msg = f"安装com.tcl.logger时发生错误: {e}"
            print(error_msg)
            messagebox.showerror("安装错误", error_msg)
            return False
    
    def _wait_and_pull_logs(self, device):
        """等待5分钟并拉取日志文件"""
        try:
            # 等待5分钟
            print(f"开始等待5分钟，设备: {device}")
            
            # 每分钟检查一次设备连接状态
            for minute in range(5):
                if not self._check_device_connection(device):
                    print(f"设备 {device} 连接断开，提前结束等待")
                    break
                
                remaining_minutes = 5 - minute - 1
                if remaining_minutes > 0:
                    print(f"等待中... 剩余 {remaining_minutes} 分钟")
                    time.sleep(60)  # 等待1分钟
                else:
                    print("等待完成")
            
            # 拉取日志文件（不使用模态执行器）
            self._pull_aee_logs_direct(device)
            
        except Exception as e:
            print(f"等待和拉取日志时发生错误: {e}")
            # 确保异常错误消息框显示在前台
            self.app.root.lift()
            self.app.root.attributes('-topmost', True)
            messagebox.showerror("错误", f"等待和拉取日志时发生错误: {e}")
            self.app.root.attributes('-topmost', False)
        finally:
            # 重置运行状态
            self.is_running = False
    
    def _check_device_connection(self, device):
        """检查设备连接状态"""
        try:
            cmd = ["adb", "devices"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                return device in result.stdout and '\tdevice' in result.stdout
            else:
                return False
                
        except Exception:
            return False
    
    def _pull_aee_logs_direct(self, device):
        """直接拉取AEE日志文件（不使用模态执行器）"""
        try:
            # 1. 创建日志目录
            current_date = datetime.datetime.now().strftime("%Y%m%d")
            log_dir = f"c:\\log\\{current_date}"
            aee_log_dir = os.path.join(log_dir, "aeelog")
            
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            if not os.path.exists(aee_log_dir):
                os.makedirs(aee_log_dir)
            
            # 2. 检查远程日志目录是否存在
            check_cmd = ["adb", "-s", device, "shell", "ls", "/storage/emulated/0/.usersupport/log/zip"]
            result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                error_msg = f"远程日志目录不存在或无法访问: {result.stderr.strip()}"
                print(error_msg)
                # 确保错误消息框显示在前台
                self.app.root.lift()
                self.app.root.attributes('-topmost', True)
                messagebox.showerror("错误", error_msg)
                self.app.root.attributes('-topmost', False)
                return
            
            # 3. 拉取日志文件
            pull_cmd = ["adb", "-s", device, "pull", "/storage/emulated/0/.usersupport/log/zip", aee_log_dir]
            result = subprocess.run(pull_cmd, capture_output=True, text=True, timeout=300, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                error_msg = f"拉取AEE日志失败: {result.stderr.strip()}"
                print(error_msg)
                # 确保错误消息框显示在前台
                self.app.root.lift()
                self.app.root.attributes('-topmost', True)
                messagebox.showerror("错误", error_msg)
                self.app.root.attributes('-topmost', False)
                return
            
            # 4. 完成 - 显示成功消息
            # 确保成功消息框显示在前台
            self.app.root.lift()
            self.app.root.attributes('-topmost', True)
            messagebox.showinfo("完成", 
                f"AEE日志导出完成！\n\n"
                f"导出目录: {aee_log_dir}\n"
                f"设备: {device}\n\n"
                f"文件夹已自动打开。")
            self.app.root.attributes('-topmost', False)
            
            # 打开日志文件夹
            os.startfile(aee_log_dir)
            
            # 更新状态
            self.app.ui.status_var.set(f"AEE日志已导出 - {device}")
            
        except Exception as e:
            error_msg = f"拉取AEE日志时发生错误: {e}"
            print(error_msg)
            # 确保异常错误消息框显示在前台
            self.app.root.lift()
            self.app.root.attributes('-topmost', True)
            messagebox.showerror("错误", error_msg)
            self.app.root.attributes('-topmost', False)
    
    def is_running(self):
        """检查AEE日志是否正在运行"""
        return self.is_running
