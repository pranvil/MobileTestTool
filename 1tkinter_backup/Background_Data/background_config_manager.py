#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
24小时背景数据配置管理器
负责配置手机和导出log相关功能
"""

import subprocess
import os
import time
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, filedialog, ttk

class BackgroundConfigManager:
    def __init__(self, app_instance):
        """
        初始化背景数据配置管理器
        
        Args:
            app_instance: 主应用程序实例
        """
        self.app = app_instance
        self.device_manager = app_instance.device_manager
        
    def configure_phone(self):
        """配置手机进行24小时背景数据收集"""
        try:
            # 获取选中的设备
            device = self.app.device_manager.validate_device_selection()
            if not device:
                return False
            
            # 执行配置步骤
            success_count = 0
            total_steps = 3
            
            # 步骤1: adb root
            if self._execute_adb_root(device):
                success_count += 1
                print(f"[INFO] adb root 执行成功")
            else:
                messagebox.showerror("配置失败", "adb root 执行失败！\n请检查设备是否已连接并支持root权限。")
                return False
            
            # 步骤2: 检查初始SELinux状态
            initial_status = self._get_selinux_status(device)
            print(f"[INFO] 初始SELinux状态: {initial_status}")
            
            # 步骤3: adb shell setenforce 0
            if self._execute_setenforce(device):
                success_count += 1
                print(f"[INFO] setenforce 0 执行成功")
            else:
                messagebox.showerror("配置失败", "setenforce 0 执行失败！\n无法设置SELinux为Permissive模式。")
                return False
            
            # 步骤4: 验证SELinux状态
            final_status = self._get_selinux_status(device)
            print(f"[INFO] 最终SELinux状态: {final_status}")
            
            if final_status == "Permissive":
                success_count += 1
                messagebox.showinfo("配置成功", 
                    f"手机配置完成！\n\n"
                    f"执行结果:\n"
                    f"• adb root: ✓ 成功\n"
                    f"• setenforce 0: ✓ 成功\n"
                    f"• SELinux状态: {initial_status} → {final_status} ✓\n\n"
                    f"设备已准备就绪，可以进行24小时背景数据收集。")
                return True
            else:
                messagebox.showerror("配置失败", 
                    f"SELinux状态设置失败！\n\n"
                    f"当前状态: {final_status}\n"
                    f"期望状态: Permissive\n\n"
                    f"请检查设备是否支持SELinux设置。")
                return False
                
        except Exception as e:
            messagebox.showerror("配置错误", f"配置过程中发生错误:\n{str(e)}")
            return False
    
    def export_background_logs(self):
        """导出24小时背景数据日志"""
        try:
            # 获取选中的设备
            device = self.app.device_manager.validate_device_selection()
            if not device:
                return False
            
            # 获取当前日期并创建目录
            current_date = datetime.now().strftime("%Y%m%d")
            log_base_dir = f"C:\\log\\{current_date}"
            
            # 创建日志目录
            if not os.path.exists(log_base_dir):
                os.makedirs(log_base_dir)
                print(f"[INFO] 创建日志目录: {log_base_dir}")
            
            # 获取用户输入的日志名称
            log_name = self._get_log_name()
            if not log_name:
                return False
            
            # 创建完整的日志目录路径
            log_dir = os.path.join(log_base_dir, log_name)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                print(f"[INFO] 创建日志子目录: {log_dir}")
            
            # 显示导出开始状态弹框
            progress_dialog = self._show_export_progress_dialog()
            
            # 执行adb pull命令
            pull_commands = [
                ("/sdcard/TCTReport", "TCTReport"),
                ("/sdcard/mtklog", "mtklog"),
                ("/sdcard/debuglogger", "debuglogger"),
                ("/data/debuglogger", "data_debuglogger"),
                ("/storage/emulated/0/debuglogger", "storage_debuglogger"),
                ("/data/user_de/0/com.android.shell/files/bugreports", "bugreports")
            ]
            
            success_count = 0
            total_commands = len(pull_commands)
            
            # 更新进度对话框
            self._update_progress_dialog(progress_dialog, "开始导出日志...", 0)
            
            for i, (source_path, folder_name) in enumerate(pull_commands):
                # 更新进度
                progress_text = f"正在导出: {folder_name} ({i+1}/{total_commands})"
                self._update_progress_dialog(progress_dialog, progress_text, (i / total_commands) * 100)
                
                if self._execute_adb_pull(device, source_path, log_dir, folder_name):
                    success_count += 1
                    print(f"[INFO] 成功导出: {source_path} -> {folder_name}")
                else:
                    print(f"[WARNING] 导出失败: {source_path}")
            
            # 关闭进度对话框
            progress_dialog.destroy()
            
            # 显示执行结果并打开文件夹
            if success_count > 0:
                # 自动打开文件夹
                self._open_folder(log_dir)
                
                messagebox.showinfo("导出完成", 
                    f"日志导出完成！\n\n"
                    f"导出目录: {log_dir}\n"
                    f"成功导出: {success_count}/{total_commands} 个目录\n\n"
                    f"导出的内容:\n"
                    f"• MTKLOG \n"
                    f"• bugreports \n\n"
                    f"文件夹已自动打开。")
                return True
            else:
                messagebox.showerror("导出失败", 
                    f"所有日志导出都失败了！\n\n"
                    f"可能的原因:\n"
                    f"• 设备未连接\n"
                    f"• 源目录不存在\n"
                    f"• 权限不足\n\n"
                    f"请检查设备连接状态和权限设置。")
                return False
                
        except Exception as e:
            messagebox.showerror("导出错误", f"导出过程中发生错误:\n{str(e)}")
            return False
    
    def _execute_adb_root(self, device):
        """执行adb root命令"""
        try:
            cmd = f"adb -s {device} root"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"[DEBUG] adb root 成功: {result.stdout.strip()}")
                return True
            else:
                print(f"[DEBUG] adb root 失败: {result.stderr.strip()}")
                return False
        except Exception as e:
            print(f"[DEBUG] adb root 执行异常: {str(e)}")
            return False
    
    def _execute_setenforce(self, device):
        """执行setenforce 0命令"""
        try:
            cmd = f"adb -s {device} shell setenforce 0"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"[DEBUG] setenforce 0 成功: {result.stdout.strip()}")
                return True
            else:
                print(f"[DEBUG] setenforce 0 失败: {result.stderr.strip()}")
                return False
        except Exception as e:
            print(f"[DEBUG] setenforce 0 执行异常: {str(e)}")
            return False
    
    def _get_selinux_status(self, device):
        """获取SELinux状态"""
        try:
            cmd = f"adb -s {device} shell getenforce"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                status = result.stdout.strip()
                print(f"[DEBUG] SELinux状态: {status}")
                return status
            else:
                print(f"[DEBUG] 获取SELinux状态失败: {result.stderr.strip()}")
                return "Unknown"
        except Exception as e:
            print(f"[DEBUG] 获取SELinux状态异常: {str(e)}")
            return "Unknown"
    
    def _get_log_name(self):
        """获取用户输入的日志名称"""
        try:
            # 创建输入对话框
            dialog = tk.Toplevel(self.app.root)
            dialog.title("输入日志名称")
            dialog.geometry("400x150")
            dialog.resizable(False, False)
            dialog.transient(self.app.root)
            dialog.grab_set()  # 模态对话框
            
            # 居中显示
            dialog.geometry("+%d+%d" % (
                self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 400) // 2,
                self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 150) // 2
            ))
            
            # 主框架
            main_frame = ttk.Frame(dialog, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 标题
            title_label = ttk.Label(main_frame, text="请输入日志名称:", font=('Arial', 12, 'bold'))
            title_label.pack(pady=(0, 10))
            
            # 输入框
            log_name_var = tk.StringVar()
            log_name_entry = ttk.Entry(main_frame, textvariable=log_name_var, width=30, font=('Arial', 10))
            log_name_entry.pack(pady=(0, 15))
            log_name_entry.focus()
            
            # 按钮框架
            button_frame = ttk.Frame(main_frame)
            button_frame.pack()
            
            result = [None]  # 使用列表来存储结果，以便在回调中修改
            
            def on_confirm():
                name = log_name_var.get().strip()
                if name:
                    result[0] = name
                    dialog.destroy()
                else:
                    messagebox.showwarning("输入错误", "请输入有效的日志名称！")
            
            def on_cancel():
                dialog.destroy()
            
            # 确认按钮
            ttk.Button(button_frame, text="确认", command=on_confirm).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="取消", command=on_cancel).pack(side=tk.LEFT)
            
            # 绑定回车键
            log_name_entry.bind('<Return>', lambda e: on_confirm())
            
            # 等待对话框关闭
            dialog.wait_window()
            
            return result[0]
            
        except Exception as e:
            print(f"[DEBUG] 获取日志名称异常: {str(e)}")
            return None
    
    def _execute_adb_pull(self, device, source_path, target_dir, folder_name):
        """执行adb pull命令"""
        try:
            # 创建目标文件夹路径
            target_path = os.path.join(target_dir, folder_name)
            
            # 执行adb pull命令
            cmd = f"adb -s {device} pull \"{source_path}\" \"{target_path}\""
            print(f"[DEBUG] 执行命令: {cmd}")
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"[DEBUG] adb pull 成功: {source_path} -> {target_path}")
                return True
            else:
                # 检查是否是目录不存在的错误
                error_msg = result.stderr.strip()
                if "does not exist" in error_msg or "No such file or directory" in error_msg:
                    print(f"[DEBUG] 源目录不存在: {source_path}")
                else:
                    print(f"[DEBUG] adb pull 失败: {error_msg}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"[DEBUG] adb pull 超时: {source_path}")
            return False
        except Exception as e:
            print(f"[DEBUG] adb pull 执行异常: {str(e)}")
            return False
    
    def _show_export_progress_dialog(self):
        """显示导出进度对话框"""
        try:
            # 创建进度对话框
            progress_dialog = tk.Toplevel(self.app.root)
            progress_dialog.title("正在导出日志")
            progress_dialog.geometry("400x200")
            progress_dialog.resizable(False, False)
            progress_dialog.transient(self.app.root)
            progress_dialog.grab_set()  # 模态对话框
            
            # 居中显示
            progress_dialog.geometry("+%d+%d" % (
                self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 400) // 2,
                self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 200) // 2
            ))
            
            # 主框架
            main_frame = ttk.Frame(progress_dialog, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 标题
            title_label = ttk.Label(main_frame, text="正在导出日志文件...", font=('Arial', 12, 'bold'))
            title_label.pack(pady=(0, 15))
            
            # 进度条
            progress_var = tk.DoubleVar()
            progress_bar = ttk.Progressbar(main_frame, variable=progress_var, maximum=100, length=300)
            progress_bar.pack(pady=(0, 15))
            
            # 状态标签
            status_label = ttk.Label(main_frame, text="准备中...", font=('Arial', 10))
            status_label.pack()
            
            # 存储进度条和状态标签的引用
            progress_dialog.progress_var = progress_var
            progress_dialog.status_label = status_label
            
            # 更新对话框
            progress_dialog.update()
            
            return progress_dialog
            
        except Exception as e:
            print(f"[DEBUG] 创建进度对话框异常: {str(e)}")
            return None
    
    def _update_progress_dialog(self, progress_dialog, status_text, progress_value):
        """更新进度对话框"""
        try:
            if progress_dialog and progress_dialog.winfo_exists():
                # 更新状态文本
                if hasattr(progress_dialog, 'status_label'):
                    progress_dialog.status_label.config(text=status_text)
                
                # 更新进度条
                if hasattr(progress_dialog, 'progress_var'):
                    progress_dialog.progress_var.set(progress_value)
                
                # 更新对话框
                progress_dialog.update()
                
        except Exception as e:
            print(f"[DEBUG] 更新进度对话框异常: {str(e)}")
    
    def _open_folder(self, folder_path):
        """打开文件夹"""
        try:
            import subprocess
            import platform
            
            system = platform.system()
            if system == "Windows":
                # Windows系统使用explorer，不使用check=True因为explorer可能返回非零退出码
                result = subprocess.run(["explorer", folder_path], capture_output=True, text=True)
                print(f"[INFO] 尝试打开文件夹: {folder_path}")
                print(f"[DEBUG] explorer命令执行完成，返回码: {result.returncode}")
                # explorer命令即使成功也可能返回非零退出码，所以不检查返回码
            elif system == "Darwin":  # macOS
                result = subprocess.run(["open", folder_path], check=True)
                print(f"[INFO] 成功打开文件夹: {folder_path}")
            elif system == "Linux":
                result = subprocess.run(["xdg-open", folder_path], check=True)
                print(f"[INFO] 成功打开文件夹: {folder_path}")
            else:
                print(f"[WARNING] 不支持的操作系统: {system}")
                messagebox.showinfo("文件夹位置", f"不支持的操作系统，请手动打开:\n{folder_path}")
                return
                
        except Exception as e:
            print(f"[DEBUG] 打开文件夹失败: {str(e)}")
            # 如果自动打开失败，至少告诉用户文件夹位置
            messagebox.showinfo("文件夹位置", f"无法自动打开文件夹，请手动打开:\n{folder_path}")
            return
        
        # 如果没有异常，说明命令执行了（Windows下即使返回非零码也可能成功）
        if system == "Windows":
            print(f"[INFO] 文件夹应该已经打开: {folder_path}")
        else:
            print(f"[INFO] 成功打开文件夹: {folder_path}")
