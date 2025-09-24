#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TMO CC文件拉取模块
负责从设备拉取CC文件
"""

import subprocess
import os
import shutil
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

class PullCCManager:
    def __init__(self, app_instance):
        self.app = app_instance
    
    def _ask_file_exists(self, deviceinfo_path):
        """询问用户如何处理已存在的文件"""
        print(f"[DEBUG] 处理文件已存在情况: {deviceinfo_path}")
        
        # 创建自定义对话框，提供三个选项
        dialog = tk.Toplevel(self.app.root)
        dialog.title("文件已存在")
        dialog.geometry("500x300")
        dialog.resizable(False, False)
        dialog.transient(self.app.root)
        dialog.grab_set()
        
        # 居中显示
        dialog.geometry("+%d+%d" % (
            self.app.root.winfo_rootx() + 50,
            self.app.root.winfo_rooty() + 50
        ))
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="目标文件已存在", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # 文件路径显示
        path_label = ttk.Label(main_frame, text=deviceinfo_path, font=('Arial', 10), 
                             foreground="blue", wraplength=450)
        path_label.pack(pady=(0, 20))
        
        # 说明文本
        info_text = "请选择如何处理现有文件："
        info_label = ttk.Label(main_frame, text=info_text, font=('Arial', 10))
        info_label.pack(pady=(0, 20))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(0, 20))
        
        result_choice = {"choice": None}
        
        def on_overwrite():
            result_choice["choice"] = "overwrite"
            dialog.destroy()
        
        def on_backup():
            result_choice["choice"] = "backup"
            dialog.destroy()
        
        def on_cancel():
            result_choice["choice"] = "cancel"
            dialog.destroy()
        
        # 三个选项按钮
        ttk.Button(button_frame, text="覆盖现有文件", command=on_overwrite, 
                  width=20).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="重命名备份并继续", command=on_backup, 
                  width=20).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="取消操作", command=on_cancel, 
                  width=20).pack(side=tk.LEFT)
        
        # 等待用户选择
        dialog.wait_window()
        
        choice = result_choice["choice"]
        print(f"[DEBUG] 用户选择: {choice}")
        return choice

    def pull_cc_file(self):
        """拉CC文件"""
        # 检查设备选择
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 1) 先做本地同步检查
        # 创建统一的日志目录路径 c:\log\yyyymmdd\ccfile
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d")
        target_dir = f"C:\\log\\{date_str}\\ccfile"
        os.makedirs(target_dir, exist_ok=True)
        deviceinfo_path = os.path.join(target_dir, "deviceInfo")
        
        if os.path.exists(deviceinfo_path):
            choice = self._ask_file_exists(deviceinfo_path)
            if choice == "overwrite":
                print(f"[DEBUG] 用户选择覆盖文件")
                try:
                    print(f"[DEBUG] 尝试删除文件/目录: {deviceinfo_path}")
                    if os.path.isdir(deviceinfo_path):
                        shutil.rmtree(deviceinfo_path)
                        print(f"[DEBUG] 目录删除成功")
                    else:
                        os.remove(deviceinfo_path)
                        print(f"[DEBUG] 文件删除成功")
                except Exception as e:
                    print(f"[DEBUG] 删除文件/目录失败: {str(e)}")
                    messagebox.showerror("错误", f"删除现有文件/目录失败: {str(e)}")
                    return
            elif choice == "backup":
                print(f"[DEBUG] 用户选择重命名备份")
                try:
                    print(f"[DEBUG] 尝试重命名文件/目录: {deviceinfo_path}")
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_path = f"{deviceinfo_path}_backup_{timestamp}"
                    
                    if os.path.exists(backup_path):
                        # 如果备份文件也存在，添加序号
                        counter = 1
                        while os.path.exists(f"{backup_path}_{counter}"):
                            counter += 1
                        backup_path = f"{backup_path}_{counter}"
                    
                    if os.path.isdir(deviceinfo_path):
                        shutil.move(deviceinfo_path, backup_path)
                        print(f"[DEBUG] 目录重命名成功: {backup_path}")
                    else:
                        os.rename(deviceinfo_path, backup_path)
                        print(f"[DEBUG] 文件重命名成功: {backup_path}")
                except Exception as e:
                    print(f"[DEBUG] 重命名文件/目录失败: {str(e)}")
                    messagebox.showerror("错误", f"重命名现有文件/目录失败: {str(e)}")
                    return
            else:  # cancel
                print(f"[DEBUG] 用户选择取消")
                self.app.ui.status_var.set("用户取消操作")
                return
        
        # 2) 再启动真正的拉取
        def pull_cc_worker(progress_var, status_label, progress_dialog, stop_flag):
            try:
                # 检查是否被要求停止
                if stop_flag and stop_flag.is_set():
                    return {"success": False, "message": "操作已取消"}
                
                print(f"[DEBUG] 开始拉CC文件，设备: {device}")
                
                status_label.config(text="开始拉取 /data/deviceInfo...")
                progress_var.set(20)
                progress_dialog.update()
                
                pull_cmd = ["adb", "-s", device, "pull", "/data/deviceInfo", target_dir]
                print(f"[DEBUG] 执行pull命令: {' '.join(pull_cmd)}")
                result = subprocess.run(pull_cmd, capture_output=True, text=True, timeout=60, 
                                      creationflags=subprocess.CREATE_NO_WINDOW)
                
                print(f"[DEBUG] pull命令返回码: {result.returncode}")
                print(f"[DEBUG] pull命令输出: {result.stdout}")
                print(f"[DEBUG] pull命令错误: {result.stderr}")
                
                # 检查是否被要求停止
                if stop_flag and stop_flag.is_set():
                    return {"success": False, "message": "操作已取消"}
                
                # 检查是否出现Permission denied错误
                if result.returncode != 0 and "Permission denied" in result.stderr:
                    print(f"[DEBUG] 检测到Permission denied，需要检查root权限")
                    # 只执行 adb root 检查
                    status_label.config(text="检测到权限问题，检查 root 权限...")
                    progress_var.set(40)
                    progress_dialog.update()
                    
                    cmd = ["adb", "-s", device, "root"]
                    print(f"[DEBUG] 执行命令: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, 
                                          creationflags=subprocess.CREATE_NO_WINDOW)
                    
                    output = result.stdout + result.stderr
                    print(f"[DEBUG] adb root命令输出: {output}")
                    
                    if "adbd cannot run as root in production builds" in output:
                        raise Exception("设备没有root权限，操作无法执行")
                    
                    # 检查是否被要求停止
                    if stop_flag and stop_flag.is_set():
                        return {"success": False, "message": "操作已取消"}
                    
                    # root权限检查通过，重新执行pull
                    status_label.config(text="Root权限检查通过，重新拉取文件...")
                    progress_var.set(60)
                    progress_dialog.update()
                    
                    # 重新执行 adb pull
                    pull_cmd = ["adb", "-s", device, "pull", "/data/deviceInfo", target_dir]
                    print(f"[DEBUG] 重新执行pull命令: {' '.join(pull_cmd)}")
                    result = subprocess.run(pull_cmd, capture_output=True, text=True, timeout=60, 
                                          creationflags=subprocess.CREATE_NO_WINDOW)
                    
                    print(f"[DEBUG] 重新pull命令返回码: {result.returncode}")
                    print(f"[DEBUG] 重新pull命令输出: {result.stdout}")
                    print(f"[DEBUG] 重新pull命令错误: {result.stderr}")
                    
                    if result.returncode != 0:
                        raise Exception(f"拉取文件失败: {result.stderr}")
                
                elif result.returncode != 0:
                    # 其他错误
                    raise Exception(f"拉取文件失败: {result.stderr}")
                
                # 验证文件是否真的被拉取
                print(f"[DEBUG] 验证最终文件路径: {deviceinfo_path}")
                print(f"[DEBUG] 最终文件是否存在: {os.path.exists(deviceinfo_path)}")
                
                if not os.path.exists(deviceinfo_path):
                    raise Exception("文件拉取后验证失败，文件不存在")
                
                print(f"[DEBUG] 文件拉取成功")
                progress_var.set(100)
                return {"success": True, "device": device, "target_dir": target_dir, "deviceinfo_path": deviceinfo_path}
                
            except subprocess.TimeoutExpired:
                print(f"[DEBUG] 操作超时")
                raise Exception("操作超时")
            except FileNotFoundError:
                print(f"[DEBUG] 未找到adb命令")
                raise Exception("未找到adb命令，请确保Android SDK已安装并配置PATH")
            except Exception as e:
                print(f"[DEBUG] 发生异常: {str(e)}")
                raise Exception(str(e))
        
        # 定义成功回调
        def on_pull_cc_done(result):
            if result.get("success") == False and result.get("message") == "操作已取消":
                self.app.ui.status_var.set("操作已取消")
            else:
                # 正常完成的情况
                self.app.ui.status_var.set(f"CC文件已拉取完成 - {result['device']} - {result['deviceinfo_path']}")
                
                # 直接打开文件夹
                try:
                    os.startfile(result['target_dir'])
                except Exception as e:
                    messagebox.showerror("错误", f"无法打开文件夹: {str(e)}")
        
        # 定义错误回调
        def on_pull_cc_error(error):
            error_str = str(error)
            print(f"[DEBUG] 错误回调被调用，错误信息: {error_str}")
            
            # 处理所有错误
            self.app.ui.status_var.set(f"拉取CC文件失败: {error_str}")
            messagebox.showerror("错误", f"拉取CC文件失败:\n{error_str}")
        
        # 使用模态执行器
        self.app.ui.run_with_modal("拉取CC文件", pull_cc_worker, on_pull_cc_done, on_pull_cc_error)
