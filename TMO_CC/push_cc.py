#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TMO CC文件推送模块
负责向设备推送CC文件
"""

import subprocess
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

class PushCCManager:
    def __init__(self, app_instance):
        self.app = app_instance
    
    def push_cc_file(self):
        """推CC文件"""
        # 检查设备选择
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 1) 先做本地同步权限检查
        try:
            print(f"[DEBUG] 开始检查设备权限，设备: {device}")
            
            # 检查adb root
            cmd = ["adb", "-s", device, "root"]
            print(f"[DEBUG] 执行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, 
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            output = result.stdout + result.stderr
            print(f"[DEBUG] adb root命令输出: {output}")
            
            if "adbd cannot run as root in production builds" in output:
                messagebox.showerror("错误", "设备没有root权限，操作无法执行")
                self.app.ui.status_var.set("设备没有root权限")
                return
            
            # 检查adb remount
            cmd2 = ["adb", "-s", device, "remount"]
            print(f"[DEBUG] 执行命令: {' '.join(cmd2)}")
            result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=30, 
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            
            output2 = result2.stdout + result2.stderr
            print(f"[DEBUG] adb remount命令输出: {output2}")
            
            if "Now reboot your device for settings to take effect" in output2:
                # 需要重启设备
                if messagebox.askyesno("需要重启", 
                                    "检测到需要重启设备才能使设置生效。\n\n是否现在重启设备？"):
                    # 执行重启
                    reboot_cmd = ["adb", "-s", device, "reboot"]
                    try:
                        subprocess.run(reboot_cmd, timeout=10, 
                                     creationflags=subprocess.CREATE_NO_WINDOW)
                        self.app.ui.status_var.set(f"设备 {device} 正在重启...")
                        messagebox.showinfo("提示", "设备正在重启，请等待设备重启完成后再试")
                    except Exception as e:
                        messagebox.showerror("错误", f"重启设备失败: {str(e)}")
                return
            
            elif "Remount succeeded" in output2 or "remounted" in output2.lower():
                # remount成功，继续文件选择
                print(f"[DEBUG] 权限检查成功")
                self._select_and_push_files(device)
            else:
                messagebox.showerror("错误", f"Remount失败: {output2}")
                self.app.ui.status_var.set("Remount失败")
                return
                
        except subprocess.TimeoutExpired:
            print(f"[DEBUG] 权限检查超时")
            messagebox.showerror("错误", "权限检查超时")
            self.app.ui.status_var.set("权限检查超时")
        except FileNotFoundError:
            print(f"[DEBUG] 未找到adb命令")
            messagebox.showerror("错误", "未找到adb命令，请确保Android SDK已安装并配置PATH")
            self.app.ui.status_var.set("未找到adb命令")
        except Exception as e:
            print(f"[DEBUG] 权限检查异常: {str(e)}")
            messagebox.showerror("错误", f"权限检查失败:\n{str(e)}")
            self.app.ui.status_var.set(f"权限检查失败: {str(e)}")
    
    def _select_and_push_files(self, device):
        """选择文件并推送"""
        # 显示文件选择对话框
        file_paths = filedialog.askopenfilenames(
            title="选择要推送的CC文件",
            filetypes=[
                ("所有文件", "*.*"),
                ("文本文件", "*.txt"),
                ("配置文件", "*.conf"),
                ("设备信息文件", "deviceInfo*")
            ],
            parent=self.app.root
        )
        
        if not file_paths:
            print(f"[DEBUG] 用户取消文件选择")
            self.app.ui.status_var.set("用户取消文件选择")
            return
        
        print(f"[DEBUG] 用户选择了 {len(file_paths)} 个文件: {file_paths}")
        
        # 定义推送工作函数
        def push_files_worker(progress_var, status_label, progress_dialog):
            try:
                print(f"[DEBUG] 开始推送文件到设备: {device}")
                
                total_files = len(file_paths)
                success_count = 0
                failed_files = []
                
                for i, file_path in enumerate(file_paths):
                    file_name = os.path.basename(file_path)
                    status_label.config(text=f"推送文件 {i+1}/{total_files}: {file_name}")
                    progress_var.set((i / total_files) * 80)  # 80%用于文件推送
                    progress_dialog.update()
                    
                    print(f"[DEBUG] 推送文件: {file_path} -> /data/deviceInfo/{file_name}")
                    
                    # 执行adb push命令
                    push_cmd = ["adb", "-s", device, "push", file_path, f"/data/deviceInfo/{file_name}"]
                    result = subprocess.run(push_cmd, capture_output=True, text=True, timeout=60, 
                                          creationflags=subprocess.CREATE_NO_WINDOW)
                    
                    print(f"[DEBUG] push命令返回码: {result.returncode}")
                    print(f"[DEBUG] push命令输出: {result.stdout}")
                    print(f"[DEBUG] push命令错误: {result.stderr}")
                    
                    if result.returncode == 0:
                        success_count += 1
                        print(f"[DEBUG] 文件推送成功: {file_name}")
                    else:
                        failed_files.append(f"{file_name}: {result.stderr.strip()}")
                        print(f"[DEBUG] 文件推送失败: {file_name} - {result.stderr.strip()}")
                
                # 完成推送
                status_label.config(text="推送完成!")
                progress_var.set(100)
                progress_dialog.update()
                
                return {
                    "success": True, 
                    "device": device, 
                    "total_files": total_files,
                    "success_count": success_count,
                    "failed_files": failed_files,
                    "file_paths": file_paths
                }
                
            except subprocess.TimeoutExpired:
                print(f"[DEBUG] 推送操作超时")
                raise Exception("推送操作超时")
            except FileNotFoundError:
                print(f"[DEBUG] 未找到adb命令")
                raise Exception("未找到adb命令，请确保Android SDK已安装并配置PATH")
            except Exception as e:
                print(f"[DEBUG] 推送异常: {str(e)}")
                raise Exception(str(e))
        
        # 定义推送成功回调
        def on_push_done(result):
            total_files = result['total_files']
            success_count = result['success_count']
            failed_files = result['failed_files']
            
            if success_count == total_files:
                # 全部成功
                self.app.ui.status_var.set(f"CC文件推送完成 - {device} - 成功推送 {success_count} 个文件")
                messagebox.showinfo("推送成功", 
                    f"所有文件推送成功!\n\n"
                    f"设备: {device}\n"
                    f"成功推送: {success_count} 个文件\n"
                    f"目标路径: /data/deviceInfo/")
            elif success_count > 0:
                # 部分成功
                failed_info = "\n".join(failed_files)
                self.app.ui.status_var.set(f"CC文件部分推送完成 - {device} - 成功 {success_count}/{total_files}")
                messagebox.showwarning("部分推送成功", 
                    f"部分文件推送成功!\n\n"
                    f"设备: {device}\n"
                    f"成功推送: {success_count}/{total_files} 个文件\n"
                    f"失败文件:\n{failed_info}")
            else:
                # 全部失败
                failed_info = "\n".join(failed_files)
                self.app.ui.status_var.set(f"CC文件推送失败 - {device}")
                messagebox.showerror("推送失败", 
                    f"所有文件推送失败!\n\n"
                    f"设备: {device}\n"
                    f"失败文件:\n{failed_info}")
        
        # 定义推送错误回调
        def on_push_error(error):
            error_str = str(error)
            print(f"[DEBUG] 推送错误: {error_str}")
            self.app.ui.status_var.set(f"CC文件推送失败: {error_str}")
            messagebox.showerror("错误", f"CC文件推送失败:\n{error_str}")
        
        # 使用模态执行器进行文件推送
        self.app.ui.run_with_modal("推送CC文件", push_files_worker, on_push_done, on_push_error)
