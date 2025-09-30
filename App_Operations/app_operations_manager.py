#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APP操作管理器
负责Android应用的安装、卸载、查询等操作
"""

import subprocess
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading


class AppOperationsManager:
    """APP操作管理器"""
    
    def __init__(self, app_instance):
        """初始化APP操作管理器"""
        self.app = app_instance
        
    def query_package(self):
        """查询package信息"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 显示参数选择对话框
        self.show_package_query_dialog(device)
    
    def query_package_name(self):
        """查询包名"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 显示提示对话框
        self.show_package_name_query_dialog(device)
    
    def query_install_path(self):
        """查询安装路径"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 显示包名输入对话框
        self.show_package_name_input_dialog(device)
    
    def pull_apk(self):
        """拉取APK文件"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 显示路径输入对话框
        self.show_pull_apk_dialog(device)
    
    def install_apk(self):
        """安装APK文件"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 显示APK安装参数选择对话框
        self.show_install_apk_dialog(device)
    
    def view_processes(self):
        """查看进程"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 显示进程查看参数选择对话框
        self.show_process_view_dialog(device)
    
    def dump_app(self):
        """Dump应用信息"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 显示dump应用对话框
        self.show_dump_app_dialog(device)
    
    def enable_app(self):
        """启用应用"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 显示包名输入对话框
        self.show_enable_app_dialog(device)
    
    def disable_app(self):
        """禁用应用"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 显示包名输入对话框
        self.show_disable_app_dialog(device)
    
    def show_package_query_dialog(self, device):
        """显示package查询参数选择对话框"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("查询Package参数选择")
        dialog.geometry("500x500")
        dialog.resizable(True, True)
        dialog.minsize(500, 500)  # 设置最小尺寸
        dialog.transient(self.app.root)
        dialog.grab_set()  # 模态对话框
        
        # 居中显示
        dialog.geometry("+%d+%d" % (
            self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 500) // 2,
            self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 500) // 2
        ))
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="选择查询参数", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 参数选择框架
        params_frame = ttk.LabelFrame(main_frame, text="查询参数", padding="10")
        params_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # 创建参数变量
        param_vars = {}
        param_options = [
            ("-3", "显示第三方应用"),
            ("-s", "显示系统应用"),
            ("-f", "显示每个包名及其对应的APK文件路径"),
            ("-e", "显示enable的app"),
            ("-d", "显示disable的app"),
            ("-i", "显示app安装源")
        ]
        
        # 创建复选框
        for param, description in param_options:
            var = tk.BooleanVar()
            param_vars[param] = var
            cb = ttk.Checkbutton(params_frame, text=f"{param}: {description}", variable=var)
            cb.pack(anchor=tk.W, pady=2)
        
        # 过滤选项框架
        filter_frame = ttk.LabelFrame(main_frame, text="过滤选项", padding="10")
        filter_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 过滤复选框和输入框
        filter_enabled_var = tk.BooleanVar()
        filter_enabled_cb = ttk.Checkbutton(filter_frame, text="启用过滤", variable=filter_enabled_var)
        filter_enabled_cb.pack(anchor=tk.W, pady=(0, 5))
        
        # 过滤输入框框架
        filter_input_frame = ttk.Frame(filter_frame)
        filter_input_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(filter_input_frame, text="过滤字符:").pack(side=tk.LEFT, padx=(0, 5))
        filter_entry = ttk.Entry(filter_input_frame, width=30)
        filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))
        
        # 确定按钮
        def on_confirm():
            # 收集选中的参数
            selected_params = []
            for param, var in param_vars.items():
                if var.get():
                    selected_params.append(param)
            
            # 获取过滤选项
            filter_text = ""
            if filter_enabled_var.get():
                filter_text = filter_entry.get().strip()
            
            dialog.destroy()
            
            # 执行查询
            self.execute_package_query(device, selected_params, filter_text)
        
        # 取消按钮
        def on_cancel():
            dialog.destroy()
        
        ttk.Button(button_frame, text="确定", command=on_confirm).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=on_cancel).pack(side=tk.LEFT)
    
    def execute_package_query(self, device, selected_params, filter_text):
        """执行package查询命令"""
        # 构建adb命令（不包含过滤）
        cmd_parts = ["adb", "-s", device, "shell", "pm", "list", "packages"]
        cmd_parts.extend(selected_params)
        
        # 构建显示的命令字符串
        cmd = f"adb -s {device} shell \"pm list packages {' '.join(selected_params)}\""
        if filter_text:
            cmd += f" (过滤: {filter_text})"
        
        self._log_message(f"[APP操作] 执行命令: {cmd}")
        
        # 在后台线程中执行命令
        def run_command():
            try:
                # 直接执行adb命令，不包含grep
                process = subprocess.Popen(
                    cmd_parts,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                stdout, stderr = process.communicate()
                
                # 如果有过滤文本，在Python中过滤结果
                if filter_text and stdout:
                    filtered_lines = []
                    for line in stdout.split('\n'):
                        if filter_text.lower() in line.lower():  # 不区分大小写过滤
                            filtered_lines.append(line)
                    stdout = '\n'.join(filtered_lines)
                
                # 在主线程中更新UI
                self.app.root.after(0, lambda: self.handle_query_result(stdout, stderr, cmd))
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self.app.root.after(0, lambda: self.handle_query_error(error_msg))
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
    def handle_query_result(self, stdout, stderr, cmd):
        """处理查询结果"""
        if stderr:
            self._log_message(f"[APP操作] 错误信息: {stderr}")
        
        if stdout:
            # 显示结果
            self._log_message(f"[APP操作] 查询结果:")
            lines = stdout.strip().split('\n')
            for line in lines:
                if line.strip():
                    self._log_message(f"  {line}")
            
            # 显示结果统计
            result_count = len([line for line in lines if line.strip()])
            self._log_message(f"[APP操作] 共找到 {result_count} 个匹配的应用包")
        else:
            self._log_message(f"[APP操作] 未找到匹配的应用包")
    
    def handle_query_error(self, error_msg):
        """处理查询错误"""
        self._log_message(f"[APP操作] {error_msg}")
        messagebox.showerror("错误", error_msg)
    
    def _log_message(self, message):
        """在日志区域显示消息"""
        try:
            # 确保在主线程中执行UI更新
            self.app.root.after(0, lambda: self._update_log_display(message))
        except Exception as e:
            print(f"[DEBUG] 日志消息更新失败: {str(e)}")
    
    def _update_log_display(self, message):
        """更新日志显示"""
        try:
            self.app.ui.log_text.config(state='normal')
            
            # 添加时间戳
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_message = f"[{timestamp}] {message}\n"
            
            # 插入消息
            self.app.ui.log_text.insert(tk.END, log_message)
            self.app.ui.log_text.see(tk.END)
            self.app.ui.log_text.config(state='disabled')
            
            # 立即刷新显示
            self.app.ui.log_text.update_idletasks()
            
        except Exception as e:
            print(f"[DEBUG] 更新日志显示失败: {str(e)}")
    
    def show_package_name_query_dialog(self, device):
        """显示包名查询提示对话框"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("查询当前应用包名")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.transient(self.app.root)
        dialog.grab_set()  # 模态对话框
        
        # 居中显示
        dialog.geometry("+%d+%d" % (
            self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 400) // 2,
            self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 200) // 2
        ))
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="查询当前前台应用包名", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 提示信息
        info_label = ttk.Label(main_frame, text="请先在手机上打开需要查询的应用，\n然后点击确认按钮开始查询。", 
                              font=('Arial', 10), justify=tk.CENTER)
        info_label.pack(pady=(0, 20))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))
        
        # 确认按钮
        def on_confirm():
            dialog.destroy()
            self.execute_package_name_query(device)
        
        # 取消按钮
        def on_cancel():
            dialog.destroy()
        
        ttk.Button(button_frame, text="确认查询", command=on_confirm).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=on_cancel).pack(side=tk.LEFT)
    
    def execute_package_name_query(self, device):
        """执行包名查询命令"""
        cmd = f"adb -s {device} shell \"dumpsys window | findstr mCurrent\""
        self._log_message(f"[APP操作] 执行命令: {cmd}")
        
        # 在后台线程中执行命令
        def run_command():
            try:
                # 构建命令参数
                cmd_parts = ["adb", "-s", device, "shell", "dumpsys", "window"]
                
                # 执行命令
                process = subprocess.Popen(
                    cmd_parts,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                stdout, stderr = process.communicate()
                
                # 在主线程中更新UI
                self.app.root.after(0, lambda: self.handle_package_name_result(stdout, stderr, cmd))
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self.app.root.after(0, lambda: self.handle_query_error(error_msg))
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
    def handle_package_name_result(self, stdout, stderr, cmd):
        """处理包名查询结果"""
        if stderr:
            self._log_message(f"[APP操作] 错误信息: {stderr}")
        
        if stdout:
            # 解析输出，查找mCurrentFocus行
            package_name = self.extract_package_name(stdout)
            
            if package_name:
                self._log_message(f"[APP操作] 当前前台应用包名: {package_name}")
                # 显示包名提取的详细信息
                self._log_message(f"[APP操作] 包名提取成功")
            else:
                self._log_message(f"[APP操作] 未找到当前前台应用的包名")
                self._log_message(f"[APP操作] 原始输出:")
                for line in stdout.split('\n'):
                    if line.strip():
                        self._log_message(f"  {line}")
        else:
            self._log_message(f"[APP操作] 未获取到输出信息")
    
    def extract_package_name(self, output):
        """从dumpsys window输出中提取包名"""
        try:
            lines = output.split('\n')
            for line in lines:
                line = line.strip()
                if 'mCurrentFocus' in line:
                    # 查找包含包名的部分
                    # 格式: mCurrentFocus=Window{... u0 com.package.name/...}
                    if ' u0 ' in line:
                        # 分割字符串，找到u0后面的部分
                        parts = line.split(' u0 ')
                        if len(parts) > 1:
                            package_part = parts[1]
                            # 提取包名（在第一个/之前的部分）
                            if '/' in package_part:
                                package_name = package_part.split('/')[0]
                                return package_name
                            else:
                                # 如果没有/，直接返回u0后面的部分
                                return package_part
            return None
        except Exception as e:
            self._log_message(f"[APP操作] 解析包名时出错: {str(e)}")
            return None
    
    def show_package_name_input_dialog(self, device):
        """显示包名输入对话框"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("查询应用安装路径")
        dialog.geometry("450x250")
        dialog.resizable(False, False)
        dialog.transient(self.app.root)
        dialog.grab_set()  # 模态对话框
        
        # 居中显示
        dialog.geometry("+%d+%d" % (
            self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 450) // 2,
            self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 250) // 2
        ))
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="查询应用安装路径", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 说明信息
        info_label = ttk.Label(main_frame, text="请输入要查询的应用包名：", 
                              font=('Arial', 10))
        info_label.pack(pady=(0, 10))
        
        # 包名输入框
        package_var = tk.StringVar()
        package_entry = ttk.Entry(main_frame, textvariable=package_var, width=50, font=('Arial', 10))
        package_entry.pack(pady=(0, 10))
        package_entry.focus()  # 设置焦点
        
        # 示例标签
        example_label = ttk.Label(main_frame, text="例如: com.google.android.apps.messaging", 
                                 font=('Arial', 9), foreground="gray")
        example_label.pack(pady=(0, 20))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))
        
        # 确认按钮
        def on_confirm():
            package_name = package_var.get().strip()
            if not package_name:
                messagebox.showwarning("输入错误", "请输入应用包名")
                return
            
            dialog.destroy()
            self.execute_install_path_query(device, package_name)
        
        # 取消按钮
        def on_cancel():
            dialog.destroy()
        
        # 绑定回车键
        def on_enter(event):
            on_confirm()
        
        package_entry.bind('<Return>', on_enter)
        
        ttk.Button(button_frame, text="查询", command=on_confirm).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=on_cancel).pack(side=tk.LEFT)
    
    def execute_install_path_query(self, device, package_name):
        """执行安装路径查询命令"""
        cmd = f"adb -s {device} shell pm path {package_name}"
        self._log_message(f"[APP操作] 执行命令: {cmd}")
        self._log_message(f"[APP操作] 查询包名: {package_name}")
        
        # 在后台线程中执行命令
        def run_command():
            try:
                # 构建命令参数
                cmd_parts = ["adb", "-s", device, "shell", "pm", "path", package_name]
                
                # 执行命令
                process = subprocess.Popen(
                    cmd_parts,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                stdout, stderr = process.communicate()
                
                # 在主线程中更新UI
                self.app.root.after(0, lambda: self.handle_install_path_result(stdout, stderr, cmd, package_name))
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self.app.root.after(0, lambda: self.handle_query_error(error_msg))
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
    def handle_install_path_result(self, stdout, stderr, cmd, package_name):
        """处理安装路径查询结果"""
        if stderr:
            self._log_message(f"[APP操作] 错误信息: {stderr}")
        
        if stdout:
            # 解析输出，提取安装路径
            install_paths = self.extract_install_paths(stdout)
            
            if install_paths:
                self._log_message(f"[APP操作] 应用 {package_name} 的安装路径:")
                for i, path in enumerate(install_paths, 1):
                    self._log_message(f"  路径 {i}: {path}")
                self._log_message(f"[APP操作] 共找到 {len(install_paths)} 个安装路径")
            else:
                self._log_message(f"[APP操作] 未找到应用 {package_name} 的安装路径")
                self._log_message(f"[APP操作] 原始输出:")
                for line in stdout.split('\n'):
                    if line.strip():
                        self._log_message(f"  {line}")
        else:
            self._log_message(f"[APP操作] 未获取到输出信息，可能应用不存在或未安装")
    
    def extract_install_paths(self, output):
        """从pm path输出中提取安装路径"""
        try:
            paths = []
            lines = output.split('\n')
            for line in lines:
                line = line.strip()
                # 查找包含package:的行
                if line.startswith('package:'):
                    # 提取路径部分
                    path = line.replace('package:', '').strip()
                    if path:
                        paths.append(path)
            return paths
        except Exception as e:
            self._log_message(f"[APP操作] 解析安装路径时出错: {str(e)}")
            return []
    
    def show_pull_apk_dialog(self, device):
        """显示pull APK包名输入对话框"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("拉取APK文件")
        dialog.geometry("500x300")
        dialog.resizable(False, False)
        dialog.transient(self.app.root)
        dialog.grab_set()  # 模态对话框
        
        # 居中显示
        dialog.geometry("+%d+%d" % (
            self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 500) // 2,
            self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 300) // 2
        ))
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="拉取APK文件", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 说明信息
        info_label = ttk.Label(main_frame, text="请输入应用包名：", 
                              font=('Arial', 10))
        info_label.pack(pady=(0, 10))
        
        # 包名输入框
        package_var = tk.StringVar()
        package_entry = ttk.Entry(main_frame, textvariable=package_var, width=60, font=('Arial', 10))
        package_entry.pack(pady=(0, 10))
        package_entry.focus()  # 设置焦点
        
        # 示例标签
        example_label = ttk.Label(main_frame, text="例如: com.example.app", 
                                 font=('Arial', 9), foreground="gray")
        example_label.pack(pady=(0, 10))
        
        # 保存路径信息
        save_info_label = ttk.Label(main_frame, text="文件将保存到: c:\\log\\yyyymmdd\\<包名>", 
                                   font=('Arial', 9), foreground="blue")
        save_info_label.pack(pady=(0, 20))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))
        
        # 确认按钮
        def on_confirm():
            package_name = package_var.get().strip()
            if not package_name:
                messagebox.showwarning("输入错误", "请输入应用包名")
                return
            
            dialog.destroy()
            self.execute_pull_apk_by_package(device, package_name)
        
        # 取消按钮
        def on_cancel():
            dialog.destroy()
        
        # 绑定回车键
        def on_enter(event):
            on_confirm()
        
        package_entry.bind('<Return>', on_enter)
        
        ttk.Button(button_frame, text="开始拉取", command=on_confirm).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=on_cancel).pack(side=tk.LEFT)
    
    def execute_pull_apk_by_package(self, device, package_name):
        """通过包名执行APK拉取命令"""
        self._log_message(f"[APP操作] 开始通过包名拉取APK: {package_name}")
        
        # 在后台线程中执行命令
        def run_command():
            try:
                # 第一步：获取APK路径
                self._log_message(f"[APP操作] 正在获取包 {package_name} 的APK路径...")
                
                # 构建获取路径的命令
                cmd_parts = ["adb", "-s", device, "shell", "pm", "path", package_name]
                
                # 执行命令获取路径
                process = subprocess.Popen(
                    cmd_parts,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    error_msg = f"获取APK路径失败: {stderr.strip()}"
                    self.app.root.after(0, lambda: self.handle_query_error(error_msg))
                    return
                
                # 解析输出获取所有APK路径
                apk_paths = []
                for line in stdout.strip().split('\n'):
                    if line.startswith('package:'):
                        apk_path = line.replace('package:', '').strip()
                        apk_paths.append(apk_path)
                
                if not apk_paths:
                    error_msg = f"未找到包 {package_name} 的APK路径"
                    self.app.root.after(0, lambda: self.handle_query_error(error_msg))
                    return
                
                self._log_message(f"[APP操作] 找到 {len(apk_paths)} 个APK文件:")
                for i, path in enumerate(apk_paths, 1):
                    filename = os.path.basename(path)
                    self._log_message(f"[APP操作]   {i}. {filename}")
                
                # 第二步：执行pull操作（拉取所有APK文件）
                self._log_message(f"[APP操作] 开始拉取所有APK文件...")
                self.app.root.after(0, lambda: self.execute_pull_multiple_apks(device, apk_paths, package_name))
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self.app.root.after(0, lambda: self.handle_query_error(error_msg))
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
    def execute_pull_multiple_apks(self, device, apk_paths, package_name):
        """执行多个APK文件的拉取"""
        # 创建保存目录
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d")
        save_dir = f"c:\\log\\{date_str}\\{package_name}"
        
        try:
            os.makedirs(save_dir, exist_ok=True)
        except Exception as e:
            self._log_message(f"[APP操作] 创建保存目录失败: {str(e)}")
            messagebox.showerror("错误", f"创建保存目录失败: {str(e)}")
            return
        
        # 在后台线程中执行所有APK的拉取
        def run_multiple_pulls():
            success_count = 0
            failed_files = []
            
            for i, apk_path in enumerate(apk_paths, 1):
                try:
                    filename = os.path.basename(apk_path)
                    local_path = os.path.join(save_dir, filename)
                    
                    self._log_message(f"[APP操作] 正在拉取 {i}/{len(apk_paths)}: {filename}")
                    
                    # 构建命令参数
                    cmd_parts = ["adb", "-s", device, "pull", apk_path, local_path]
                    
                    # 执行命令
                    process = subprocess.Popen(
                        cmd_parts,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    stdout, stderr = process.communicate()
                    
                    if process.returncode == 0 and os.path.exists(local_path):
                        file_size = os.path.getsize(local_path)
                        self._log_message(f"[APP操作] ✓ {filename} 拉取成功 ({file_size} 字节)")
                        success_count += 1
                    else:
                        self._log_message(f"[APP操作] ✗ {filename} 拉取失败: {stderr.strip()}")
                        failed_files.append(filename)
                        
                except Exception as e:
                    self._log_message(f"[APP操作] ✗ {filename} 拉取异常: {str(e)}")
                    failed_files.append(filename)
            
            # 在主线程中显示结果
            self.app.root.after(0, lambda: self.handle_multiple_pull_result(
                success_count, len(apk_paths), failed_files, save_dir))
        
        # 启动后台线程
        thread = threading.Thread(target=run_multiple_pulls, daemon=True)
        thread.start()
    
    def handle_multiple_pull_result(self, success_count, total_count, failed_files, save_dir):
        """处理多个APK拉取结果"""
        if success_count == total_count:
            # 全部成功
            message = f"所有APK文件拉取成功！\n\n成功拉取: {success_count}/{total_count} 个文件\n保存位置: {save_dir}\n\n是否打开文件夹?"
            result = messagebox.askyesno("拉取成功", message)
            
            if result:
                self.open_folder_with_selection(save_dir)
        elif success_count > 0:
            # 部分成功
            failed_list = "\n".join(failed_files) if failed_files else "无"
            message = f"APK文件拉取完成（部分成功）\n\n成功: {success_count}/{total_count} 个文件\n失败: {len(failed_files)} 个文件\n\n失败的文件:\n{failed_list}\n\n保存位置: {save_dir}\n\n是否打开文件夹?"
            result = messagebox.askyesno("拉取完成", message)
            
            if result:
                self.open_folder_with_selection(save_dir)
        else:
            # 全部失败
            message = f"所有APK文件拉取失败！\n\n失败的文件数: {total_count}\n\n可能的原因:\n- 设备路径不存在\n- 权限不足\n- 网络连接问题"
            messagebox.showerror("拉取失败", message)
    
    def open_folder_with_selection(self, folder_path):
        """打开文件夹"""
        try:
            os.startfile(folder_path)
        except Exception as e:
            self._log_message(f"[APP操作] 打开文件夹失败: {str(e)}")
            messagebox.showerror("错误", f"打开文件夹失败: {str(e)}")
    
    def execute_pull_apk(self, device, device_path, package_name=None):
        """执行APK拉取命令"""
        # 创建保存目录
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d")
        
        if package_name:
            # 如果有包名，创建以包名命名的子文件夹
            save_dir = f"c:\\log\\{date_str}\\{package_name}"
        else:
            # 兼容旧版本，没有包名时使用原路径
            save_dir = f"c:\\log\\{date_str}"
        
        try:
            os.makedirs(save_dir, exist_ok=True)
        except Exception as e:
            self._log_message(f"[APP操作] 创建保存目录失败: {str(e)}")
            messagebox.showerror("错误", f"创建保存目录失败: {str(e)}")
            return
        
        # 从设备路径中提取文件名
        filename = os.path.basename(device_path)
        if not filename:
            filename = f"pulled_file_{datetime.now().strftime('%H%M%S')}.apk"
        
        local_path = os.path.join(save_dir, filename)
        
        cmd = f"adb -s {device} pull \"{device_path}\" \"{local_path}\""
        self._log_message(f"[APP操作] 执行命令: {cmd}")
        self._log_message(f"[APP操作] 保存路径: {local_path}")
        
        # 在后台线程中执行命令
        def run_command():
            try:
                # 构建命令参数
                cmd_parts = ["adb", "-s", device, "pull", device_path, local_path]
                
                # 执行命令
                process = subprocess.Popen(
                    cmd_parts,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                stdout, stderr = process.communicate()
                
                # 在主线程中更新UI
                self.app.root.after(0, lambda: self.handle_pull_apk_result(stdout, stderr, cmd, local_path))
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self.app.root.after(0, lambda: self.handle_query_error(error_msg))
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
    def handle_pull_apk_result(self, stdout, stderr, cmd, local_path):
        """处理APK拉取结果"""
        if stderr:
            self._log_message(f"[APP操作] 错误信息: {stderr}")
        
        if stdout:
            self._log_message(f"[APP操作] 拉取输出: {stdout}")
        
        # 检查文件是否成功拉取
        if os.path.exists(local_path):
            file_size = os.path.getsize(local_path)
            self._log_message(f"[APP操作] APK文件拉取成功!")
            self._log_message(f"[APP操作] 文件大小: {file_size} 字节")
            self._log_message(f"[APP操作] 保存位置: {local_path}")
            
            # 询问是否打开文件夹
            def open_folder():
                try:
                    # 在Windows上打开文件夹并选中文件（一步完成）
                    subprocess.run(['explorer', '/select,', local_path], check=True)
                except:
                    # 如果选中文件失败，则只打开文件夹
                    try:
                        os.startfile(os.path.dirname(local_path))
                    except Exception as e:
                        self._log_message(f"[APP操作] 打开文件夹失败: {str(e)}")
                        messagebox.showerror("错误", f"打开文件夹失败: {str(e)}")
            
            # 显示成功对话框并询问是否打开
            result = messagebox.askyesno("拉取成功", 
                f"APK文件已成功拉取到:\n{local_path}\n\n文件大小: {file_size} 字节\n\n是否打开文件夹?")
            
            if result:
                self.app.root.after(100, open_folder)
        else:
            self._log_message(f"[APP操作] APK文件拉取失败，文件不存在")
            if stderr:
                self._log_message(f"[APP操作] 可能的原因: 设备路径不存在或权限不足")
            messagebox.showerror("拉取失败", "APK文件拉取失败，请检查设备路径是否正确")
    
    def show_install_apk_dialog(self, device):
        """显示APK安装参数选择对话框"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("安装APK文件")
        dialog.geometry("600x500")
        dialog.resizable(True, True)
        dialog.minsize(600, 500)
        dialog.transient(self.app.root)
        dialog.grab_set()  # 模态对话框
        
        # 居中显示
        dialog.geometry("+%d+%d" % (
            self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 600) // 2,
            self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 500) // 2
        ))
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="安装APK文件", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 参数选择框架
        params_frame = ttk.LabelFrame(main_frame, text="安装参数（可选）", padding="10")
        params_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # 创建参数变量
        param_vars = {}
        param_options = [
            ("-r", "覆盖安装，保留用户数据"),
            ("-d", "允许降级安装"),
            ("-t", "安装测试版，即便签名不同"),
            ("-g", "自动授予运行时权限"),
            ("--bypass-low-target-sdk-block", "忽略低 targetSdk 限制"),
            ("install-multiple", "安装多个APK文件，针对 split APK")
        ]
        
        # 创建复选框
        for param, description in param_options:
            var = tk.BooleanVar()
            param_vars[param] = var
            cb = ttk.Checkbutton(params_frame, text=f"{param}: {description}", variable=var)
            cb.pack(anchor=tk.W, pady=2)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))
        
        # 下一步按钮
        def on_next():
            # 收集选中的参数
            selected_params = []
            for param, var in param_vars.items():
                if var.get():
                    selected_params.append(param)
            
            dialog.destroy()
            self.show_apk_selection_dialog(device, selected_params)
        
        # 取消按钮
        def on_cancel():
            dialog.destroy()
        
        ttk.Button(button_frame, text="下一步", command=on_next).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=on_cancel).pack(side=tk.LEFT)
    
    def show_apk_selection_dialog(self, device, selected_params):
        """显示APK文件选择对话框"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("选择APK文件")
        dialog.geometry("500x400")
        dialog.resizable(False, False)
        dialog.transient(self.app.root)
        dialog.grab_set()  # 模态对话框
        
        # 居中显示
        dialog.geometry("+%d+%d" % (
            self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 500) // 2,
            self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 400) // 2
        ))
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="选择APK文件", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 检查是否选择了install-multiple参数
        is_multiple_install = "install-multiple" in selected_params
        
        # 提示信息
        if is_multiple_install:
            info_text = "选择了 install-multiple 参数，可以选择多个APK文件（split APK）"
            filetypes = [("APK files", "*.apk"), ("All files", "*.*")]
            selection_mode = "multiple"
        else:
            info_text = "请选择一个APK文件进行安装"
            filetypes = [("APK files", "*.apk"), ("All files", "*.*")]
            selection_mode = "single"
        
        info_label = ttk.Label(main_frame, text=info_text, font=('Arial', 10))
        info_label.pack(pady=(0, 20))
        
        # 文件选择按钮
        def select_apk_files():
            if is_multiple_install:
                # 多选模式
                files = filedialog.askopenfilenames(
                    title="选择APK文件（可多选）",
                    filetypes=filetypes
                )
            else:
                # 单选模式
                file = filedialog.askopenfilename(
                    title="选择APK文件",
                    filetypes=filetypes
                )
                files = [file] if file else []
            
            if files:
                dialog.destroy()
                self.execute_install_apk(device, selected_params, files)
            else:
                messagebox.showwarning("提示", "请选择APK文件")
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(20, 0))
        
        ttk.Button(button_frame, text="选择APK文件", command=select_apk_files).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT)
    
    def execute_install_apk(self, device, selected_params, apk_files):
        """执行APK安装命令"""
        if not apk_files:
            return
        
        # 检查是否使用install-multiple命令
        is_multiple_install = "install-multiple" in selected_params
        
        if is_multiple_install:
            # 使用install-multiple命令
            cmd_parts = ["adb", "-s", device, "install-multiple"]
            # 移除install-multiple参数，因为它不是adb install的参数
            other_params = [p for p in selected_params if p != "install-multiple"]
            cmd_parts.extend(other_params)
            cmd_parts.extend(apk_files)
            
            cmd = f"adb -s {device} install-multiple {' '.join(other_params)} {' '.join(apk_files)}"
            self._log_message(f"[APP操作] 执行命令: {cmd}")
            self._log_message(f"[APP操作] 安装文件: {', '.join(apk_files)}")
            self._log_message(f"[APP操作] 安装参数: {', '.join(other_params) if other_params else '无'}")
        else:
            # 使用普通install命令
            cmd_parts = ["adb", "-s", device, "install"]
            cmd_parts.extend(selected_params)
            cmd_parts.extend(apk_files)
            
            cmd = f"adb -s {device} install {' '.join(selected_params)} {' '.join(apk_files)}"
            self._log_message(f"[APP操作] 执行命令: {cmd}")
            self._log_message(f"[APP操作] 安装文件: {', '.join(apk_files)}")
            self._log_message(f"[APP操作] 安装参数: {', '.join(selected_params) if selected_params else '无'}")
        
        # 在后台线程中执行命令
        def run_command():
            try:
                # 执行命令
                process = subprocess.Popen(
                    cmd_parts,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                stdout, stderr = process.communicate()
                
                # 在主线程中更新UI
                self.app.root.after(0, lambda: self.handle_install_apk_result(stdout, stderr, cmd, apk_files))
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self.app.root.after(0, lambda: self.handle_query_error(error_msg))
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
    def handle_install_apk_result(self, stdout, stderr, cmd, apk_files):
        """处理APK安装结果"""
        if stderr:
            self._log_message(f"[APP操作] 错误信息: {stderr}")
        
        if stdout:
            self._log_message(f"[APP操作] 安装输出: {stdout}")
            
            # 检查安装是否成功 - 严格按照"Success"判断
            if "Success" in stdout:
                self._log_message(f"[APP操作] APK安装成功!")
                messagebox.showinfo("安装成功", "APK文件安装成功!")
            else:
                # 没有"Success"就判定为安装失败
                self._log_message(f"[APP操作] APK安装失败!")
                error_msg = f"APK文件安装失败!\n\n输出信息:\n{stdout}"
                if stderr:
                    error_msg += f"\n\n错误信息:\n{stderr}"
                messagebox.showerror("安装失败", error_msg)
        else:
            self._log_message(f"[APP操作] 未获取到输出信息")
            messagebox.showerror("安装失败", "未获取到安装输出信息")
    
    def show_process_view_dialog(self, device):
        """显示进程查看参数选择对话框"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("查看进程")
        dialog.geometry("500x400")
        dialog.resizable(True, True)
        dialog.minsize(500, 400)
        dialog.transient(self.app.root)
        dialog.grab_set()  # 模态对话框
        
        # 居中显示
        dialog.geometry("+%d+%d" % (
            self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 500) // 2,
            self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 400) // 2
        ))
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="查看进程参数选择", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 参数选择框架
        params_frame = ttk.LabelFrame(main_frame, text="查看参数", padding="10")
        params_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # 创建参数变量
        param_vars = {}
        param_options = [
            ("-A", "显示所有进程"),
            ("-T", "显示线程"),
            ("-f", "显示完整格式")
        ]
        
        # 创建复选框，默认勾选-A
        for param, description in param_options:
            var = tk.BooleanVar()
            if param == "-A":  # 默认勾选-A
                var.set(True)
            param_vars[param] = var
            cb = ttk.Checkbutton(params_frame, text=f"{param}: {description}", variable=var)
            cb.pack(anchor=tk.W, pady=2)
        
        # 过滤选项框架
        filter_frame = ttk.LabelFrame(main_frame, text="过滤选项", padding="10")
        filter_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 过滤复选框和输入框
        filter_enabled_var = tk.BooleanVar()
        filter_enabled_cb = ttk.Checkbutton(filter_frame, text="启用过滤", variable=filter_enabled_var)
        filter_enabled_cb.pack(anchor=tk.W, pady=(0, 5))
        
        # 过滤输入框框架
        filter_input_frame = ttk.Frame(filter_frame)
        filter_input_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(filter_input_frame, text="过滤字符:").pack(side=tk.LEFT, padx=(0, 5))
        filter_entry = ttk.Entry(filter_input_frame, width=30)
        filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))
        
        # 确定按钮
        def on_confirm():
            # 收集选中的参数
            selected_params = []
            for param, var in param_vars.items():
                if var.get():
                    selected_params.append(param)
            
            # 获取过滤选项
            filter_text = ""
            if filter_enabled_var.get():
                filter_text = filter_entry.get().strip()
            
            dialog.destroy()
            
            # 执行进程查看
            self.execute_process_view(device, selected_params, filter_text)
        
        # 取消按钮
        def on_cancel():
            dialog.destroy()
        
        ttk.Button(button_frame, text="确定", command=on_confirm).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=on_cancel).pack(side=tk.LEFT)
    
    def execute_process_view(self, device, selected_params, filter_text):
        """执行进程查看命令"""
        # 构建adb命令
        cmd_parts = ["adb", "-s", device, "shell", "ps"]
        cmd_parts.extend(selected_params)
        
        # 构建显示的命令字符串
        cmd = f"adb -s {device} shell ps {' '.join(selected_params)}"
        if filter_text:
            cmd += f" (过滤: {filter_text})"
        
        self._log_message(f"[APP操作] 执行命令: {cmd}")
        
        # 在后台线程中执行命令
        def run_command():
            try:
                # 直接执行adb命令，不包含grep
                process = subprocess.Popen(
                    cmd_parts,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                stdout, stderr = process.communicate()
                
                # 如果有过滤文本，在Python中过滤结果
                if filter_text and stdout:
                    filtered_lines = []
                    for line in stdout.split('\n'):
                        if filter_text.lower() in line.lower():  # 不区分大小写过滤
                            filtered_lines.append(line)
                    stdout = '\n'.join(filtered_lines)
                
                # 在主线程中更新UI
                self.app.root.after(0, lambda: self.handle_process_view_result(stdout, stderr, cmd))
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self.app.root.after(0, lambda: self.handle_query_error(error_msg))
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
    def handle_process_view_result(self, stdout, stderr, cmd):
        """处理进程查看结果"""
        if stderr:
            self._log_message(f"[APP操作] 错误信息: {stderr}")
        
        if stdout:
            # 显示结果
            self._log_message(f"[APP操作] 进程信息:")
            lines = stdout.strip().split('\n')
            for line in lines:
                if line.strip():
                    self._log_message(f"  {line}")
            
            # 显示结果统计
            result_count = len([line for line in lines if line.strip()])
            self._log_message(f"[APP操作] 共找到 {result_count} 个进程")
        else:
            self._log_message(f"[APP操作] 未找到匹配的进程")
    
    def show_enable_app_dialog(self, device):
        """显示启用应用包名输入对话框"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("启用应用")
        dialog.geometry("450x250")
        dialog.resizable(False, False)
        dialog.transient(self.app.root)
        dialog.grab_set()  # 模态对话框
        
        # 居中显示
        dialog.geometry("+%d+%d" % (
            self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 450) // 2,
            self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 250) // 2
        ))
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="启用应用", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 说明信息
        info_label = ttk.Label(main_frame, text="请输入要启用的应用包名：", 
                              font=('Arial', 10))
        info_label.pack(pady=(0, 10))
        
        # 包名输入框
        package_var = tk.StringVar()
        package_entry = ttk.Entry(main_frame, textvariable=package_var, width=50, font=('Arial', 10))
        package_entry.pack(pady=(0, 10))
        package_entry.focus()  # 设置焦点
        
        # 示例标签
        example_label = ttk.Label(main_frame, text="例如: com.google.android.apps.messaging", 
                                 font=('Arial', 9), foreground="gray")
        example_label.pack(pady=(0, 20))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))
        
        # 确认按钮
        def on_confirm():
            package_name = package_var.get().strip()
            if not package_name:
                messagebox.showwarning("输入错误", "请输入应用包名")
                return
            
            dialog.destroy()
            self.execute_enable_app(device, package_name)
        
        # 取消按钮
        def on_cancel():
            dialog.destroy()
        
        # 绑定回车键
        def on_enter(event):
            on_confirm()
        
        package_entry.bind('<Return>', on_enter)
        
        ttk.Button(button_frame, text="启用", command=on_confirm).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=on_cancel).pack(side=tk.LEFT)
    
    def show_disable_app_dialog(self, device):
        """显示禁用应用包名输入对话框"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("禁用应用")
        dialog.geometry("450x250")
        dialog.resizable(False, False)
        dialog.transient(self.app.root)
        dialog.grab_set()  # 模态对话框
        
        # 居中显示
        dialog.geometry("+%d+%d" % (
            self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 450) // 2,
            self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 250) // 2
        ))
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="禁用应用", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 说明信息
        info_label = ttk.Label(main_frame, text="请输入要禁用的应用包名：", 
                              font=('Arial', 10))
        info_label.pack(pady=(0, 10))
        
        # 包名输入框
        package_var = tk.StringVar()
        package_entry = ttk.Entry(main_frame, textvariable=package_var, width=50, font=('Arial', 10))
        package_entry.pack(pady=(0, 10))
        package_entry.focus()  # 设置焦点
        
        # 示例标签
        example_label = ttk.Label(main_frame, text="例如: com.google.android.apps.messaging", 
                                 font=('Arial', 9), foreground="gray")
        example_label.pack(pady=(0, 20))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))
        
        # 确认按钮
        def on_confirm():
            package_name = package_var.get().strip()
            if not package_name:
                messagebox.showwarning("输入错误", "请输入应用包名")
                return
            
            dialog.destroy()
            self.execute_disable_app(device, package_name)
        
        # 取消按钮
        def on_cancel():
            dialog.destroy()
        
        # 绑定回车键
        def on_enter(event):
            on_confirm()
        
        package_entry.bind('<Return>', on_enter)
        
        ttk.Button(button_frame, text="禁用", command=on_confirm).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=on_cancel).pack(side=tk.LEFT)
    
    def execute_enable_app(self, device, package_name):
        """执行启用应用命令"""
        cmd = f"adb -s {device} shell pm enable {package_name}"
        self._log_message(f"[APP操作] 执行命令: {cmd}")
        self._log_message(f"[APP操作] 启用应用: {package_name}")
        
        # 在后台线程中执行命令
        def run_command():
            try:
                # 构建命令参数
                cmd_parts = ["adb", "-s", device, "shell", "pm", "enable", package_name]
                
                # 执行命令
                process = subprocess.Popen(
                    cmd_parts,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                stdout, stderr = process.communicate()
                
                # 在主线程中更新UI
                self.app.root.after(0, lambda: self.handle_enable_app_result(stdout, stderr, cmd, package_name))
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self.app.root.after(0, lambda: self.handle_query_error(error_msg))
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
    def execute_disable_app(self, device, package_name):
        """执行禁用应用命令"""
        cmd = f"adb -s {device} shell pm disable-user {package_name}"
        self._log_message(f"[APP操作] 执行命令: {cmd}")
        self._log_message(f"[APP操作] 禁用应用: {package_name}")
        
        # 在后台线程中执行命令
        def run_command():
            try:
                # 构建命令参数
                cmd_parts = ["adb", "-s", device, "shell", "pm", "disable-user", package_name]
                
                # 执行命令
                process = subprocess.Popen(
                    cmd_parts,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                stdout, stderr = process.communicate()
                
                # 在主线程中更新UI
                self.app.root.after(0, lambda: self.handle_disable_app_result(stdout, stderr, cmd, package_name))
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self.app.root.after(0, lambda: self.handle_query_error(error_msg))
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
    def handle_enable_app_result(self, stdout, stderr, cmd, package_name):
        """处理启用应用结果"""
        if stderr:
            self._log_message(f"[APP操作] 错误信息: {stderr}")
        
        if stdout:
            self._log_message(f"[APP操作] 启用输出: {stdout}")
            
            # 检查启用是否成功
            if "Success" in stdout or "success" in stdout or "enabled" in stdout.lower():
                self._log_message(f"[APP操作] 应用 {package_name} 启用成功!")
                messagebox.showinfo("启用成功", f"应用 {package_name} 启用成功!")
            elif "Failure" in stdout or "failure" in stdout or "Error" in stdout or "error" in stdout:
                self._log_message(f"[APP操作] 应用 {package_name} 启用失败!")
                messagebox.showerror("启用失败", f"应用 {package_name} 启用失败!")
            else:
                # 其他情况，显示完整输出
                self._log_message(f"[APP操作] 启用完成，请检查输出信息")
                messagebox.showinfo("启用完成", "应用启用完成，请查看日志了解详细信息")
        else:
            # 没有输出通常表示成功
            self._log_message(f"[APP操作] 应用 {package_name} 启用成功!")
            messagebox.showinfo("启用成功", f"应用 {package_name} 启用成功!")
    
    def handle_disable_app_result(self, stdout, stderr, cmd, package_name):
        """处理禁用应用结果"""
        if stderr:
            self._log_message(f"[APP操作] 错误信息: {stderr}")
        
        if stdout:
            self._log_message(f"[APP操作] 禁用输出: {stdout}")
            
            # 检查禁用是否成功
            if "Success" in stdout or "success" in stdout or "disabled" in stdout.lower():
                self._log_message(f"[APP操作] 应用 {package_name} 禁用成功!")
                messagebox.showinfo("禁用成功", f"应用 {package_name} 禁用成功!")
            elif "Failure" in stdout or "failure" in stdout or "Error" in stdout or "error" in stdout:
                self._log_message(f"[APP操作] 应用 {package_name} 禁用失败!")
                messagebox.showerror("禁用失败", f"应用 {package_name} 禁用失败!")
            else:
                # 其他情况，显示完整输出
                self._log_message(f"[APP操作] 禁用完成，请检查输出信息")
                messagebox.showinfo("禁用完成", "应用禁用完成，请查看日志了解详细信息")
        else:
            # 没有输出通常表示成功
            self._log_message(f"[APP操作] 应用 {package_name} 禁用成功!")
            messagebox.showinfo("禁用成功", f"应用 {package_name} 禁用成功!")
    
    def show_dump_app_dialog(self, device):
        """显示dump应用对话框"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Dump应用信息")
        dialog.geometry("600x500")
        dialog.resizable(True, True)
        dialog.minsize(600, 500)
        dialog.transient(self.app.root)
        dialog.grab_set()  # 模态对话框
        
        # 居中显示
        dialog.geometry("+%d+%d" % (
            self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 600) // 2,
            self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 500) // 2
        ))
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="Dump应用信息", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 包名输入框架
        package_frame = ttk.LabelFrame(main_frame, text="应用包名", padding="10")
        package_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 包名输入框
        package_var = tk.StringVar()
        package_entry = ttk.Entry(package_frame, textvariable=package_var, width=60, font=('Arial', 10))
        package_entry.pack(pady=(0, 5))
        package_entry.focus()  # 设置焦点
        
        # 示例标签
        example_label = ttk.Label(package_frame, text="例如: com.google.android.apps.messaging", 
                                 font=('Arial', 9), foreground="gray")
        example_label.pack()
        
        # 过滤选项框架
        filter_frame = ttk.LabelFrame(main_frame, text="过滤选项（可选）", padding="10")
        filter_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # 预定义过滤选项（单选）
        predefined_var = tk.StringVar()
        predefined_options = [
            ("permission", "权限"),
            ("versionName", "版本号"),
            ("path", "安装路径")
        ]
        
        # 创建预定义过滤单选按钮
        predefined_label = ttk.Label(filter_frame, text="预定义过滤选项:", font=('Arial', 10, 'bold'))
        predefined_label.pack(anchor=tk.W, pady=(0, 5))
        
        for keyword, description in predefined_options:
            rb = ttk.Radiobutton(filter_frame, text=f"{keyword}: {description}", 
                               variable=predefined_var, value=keyword)
            rb.pack(anchor=tk.W, pady=1)
        
        # 自定义过滤选项（单选）
        custom_filter_frame = ttk.Frame(filter_frame)
        custom_filter_frame.pack(fill=tk.X, pady=(10, 0))
        
        custom_var = tk.StringVar()
        custom_rb = ttk.Radiobutton(custom_filter_frame, text="自定义过滤:", variable=custom_var, value="custom")
        custom_rb.pack(side=tk.LEFT, padx=(0, 10))
        
        custom_entry = ttk.Entry(custom_filter_frame, width=30)
        custom_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 正则表达式控制选项
        regex_var = tk.BooleanVar(value=True)  # 默认启用正则表达式
        regex_cb = ttk.Checkbutton(custom_filter_frame, text="启用正则表达式", variable=regex_var)
        regex_cb.pack(side=tk.LEFT, padx=(10, 0))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))
        
        # 确定按钮
        def on_confirm():
            package_name = package_var.get().strip()
            if not package_name:
                messagebox.showwarning("输入错误", "请输入应用包名")
                return
            
            # 收集选中的过滤选项（单选）
            selected_filter = None
            selected_regex_enabled = False
            
            # 检查预定义选项
            predefined_value = predefined_var.get()
            if predefined_value:
                selected_filter = predefined_value
            
            # 检查自定义过滤
            custom_value = custom_var.get()
            if custom_value == "custom":
                custom_text = custom_entry.get().strip()
                if custom_text:
                    selected_filter = custom_text
                    selected_regex_enabled = regex_var.get()
            
            dialog.destroy()
            
            # 执行dump命令
            self.execute_dump_app(device, package_name, selected_filter, selected_regex_enabled)
        
        # 取消按钮
        def on_cancel():
            dialog.destroy()
        
        # 绑定回车键
        def on_enter(event):
            on_confirm()
        
        package_entry.bind('<Return>', on_enter)
        
        ttk.Button(button_frame, text="开始Dump", command=on_confirm).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=on_cancel).pack(side=tk.LEFT)
    
    def execute_dump_app(self, device, package_name, selected_filter, regex_enabled=False):
        """执行dump应用命令"""
        # 构建基础命令
        base_cmd = f"adb -s {device} shell dumpsys package {package_name}"
        
        # 构建完整命令（包含过滤）
        if selected_filter:
            if regex_enabled:
                # 使用正则表达式过滤
                cmd = f"{base_cmd} | findstr /R \"{selected_filter}\""
            else:
                # 使用普通字符串过滤
                cmd = f"{base_cmd} | findstr \"{selected_filter}\""
        else:
            # 无过滤
            cmd = base_cmd
        
        self._log_message(f"[APP操作] 执行命令: {cmd}")
        self._log_message(f"[APP操作] 应用包名: {package_name}")
        if selected_filter:
            filter_type = "正则表达式" if regex_enabled else "普通字符串"
            self._log_message(f"[APP操作] 过滤条件: {selected_filter} ({filter_type})")
        
        # 在后台线程中执行命令
        def run_command():
            try:
                # 构建命令参数
                cmd_parts = ["adb", "-s", device, "shell", "dumpsys", "package", package_name]
                
                # 执行基础命令
                process = subprocess.Popen(
                    cmd_parts,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                stdout, stderr = process.communicate()
                
                # 如果有过滤条件，在Python中过滤结果
                if selected_filter and stdout:
                    import re
                    filtered_lines = []
                    for line in stdout.split('\n'):
                        if regex_enabled:
                            # 使用正则表达式匹配
                            try:
                                if re.search(selected_filter, line, re.IGNORECASE):
                                    filtered_lines.append(line)
                            except re.error:
                                # 正则表达式错误，回退到普通字符串匹配
                                if selected_filter.lower() in line.lower():
                                    filtered_lines.append(line)
                        else:
                            # 使用普通字符串匹配
                            if selected_filter.lower() in line.lower():
                                filtered_lines.append(line)
                    stdout = '\n'.join(filtered_lines)
                
                # 在主线程中更新UI
                self.app.root.after(0, lambda: self.handle_dump_app_result(stdout, stderr, cmd, package_name))
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self.app.root.after(0, lambda: self.handle_query_error(error_msg))
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
    def handle_dump_app_result(self, stdout, stderr, cmd, package_name):
        """处理dump应用结果"""
        if stderr:
            self._log_message(f"[APP操作] 错误信息: {stderr}")
        
        if stdout:
            # 显示结果
            self._log_message(f"[APP操作] 应用 {package_name} 的dump信息:")
            lines = stdout.strip().split('\n')
            for line in lines:
                if line.strip():
                    self._log_message(f"  {line}")
            
            # 显示结果统计
            result_count = len([line for line in lines if line.strip()])
            self._log_message(f"[APP操作] 共找到 {result_count} 行相关信息")
        else:
            self._log_message(f"[APP操作] 未找到应用 {package_name} 的相关信息")
            self._log_message(f"[APP操作] 可能的原因: 应用不存在、未安装或权限不足")
    
    def push_apk(self):
        """推送文件到设备"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 显示推送目标路径对话框
        self.show_push_apk_dialog(device)
    
    def show_push_apk_dialog(self, device):
        """显示推送文件对话框"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("推送文件到设备")
        dialog.geometry("500x300")
        dialog.resizable(False, False)
        dialog.transient(self.app.root)
        dialog.grab_set()  # 模态对话框
        
        # 居中显示
        dialog.geometry("+%d+%d" % (
            self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 500) // 2,
            self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 300) // 2
        ))
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="推送文件到设备", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 目标路径输入框架
        path_frame = ttk.LabelFrame(main_frame, text="设备目标路径", padding="10")
        path_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 目标路径输入框
        target_path_var = tk.StringVar()
        target_path_entry = ttk.Entry(path_frame, textvariable=target_path_var, width=50, font=('Arial', 10))
        target_path_entry.pack(pady=(0, 5))
        target_path_entry.focus()  # 设置焦点
        
        # 示例标签
        example_label = ttk.Label(path_frame, text="例如: /system/app/ 或 /data/local/tmp/", 
                                 font=('Arial', 9), foreground="gray")
        example_label.pack()
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))
        
        # 确认按钮
        def on_confirm():
            target_path = target_path_var.get().strip()
            if not target_path:
                messagebox.showwarning("输入错误", "请输入设备目标路径")
                return
            
            dialog.destroy()
            self.show_file_selection_dialog(device, target_path)
        
        # 取消按钮
        def on_cancel():
            dialog.destroy()
        
        # Root和Remount按钮
        def on_root_remount():
            self.execute_root_remount(device)
        
        # 绑定回车键
        def on_enter(event):
            on_confirm()
        
        target_path_entry.bind('<Return>', on_enter)
        
        ttk.Button(button_frame, text="adb root&adb remount", command=on_root_remount).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="确认", command=on_confirm).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=on_cancel).pack(side=tk.LEFT)
    
    def show_file_selection_dialog(self, device, target_path):
        """显示文件选择对话框"""
        # 选择文件或文件夹
        selection = filedialog.askopenfilenames(
            title="选择要推送的文件或文件夹",
            filetypes=[("All files", "*.*")]
        )
        
        if selection:
            # 检查是否选择了文件夹（通过检查父目录）
            for file_path in selection:
                if os.path.isdir(file_path):
                    # 推送整个文件夹
                    self.execute_push_folder(device, file_path, target_path)
                else:
                    # 推送单个文件
                    self.execute_push_file(device, file_path, target_path)
        else:
            messagebox.showinfo("提示", "未选择任何文件")
    
    def execute_root_remount(self, device):
        """执行adb root和adb remount命令"""
        self._log_message(f"[APP操作] 执行adb root和adb remount")
        
        # 在后台线程中执行命令
        def run_commands():
            try:
                # 执行adb root
                self._log_message(f"[APP操作] 执行: adb -s {device} root")
                root_process = subprocess.Popen(
                    ["adb", "-s", device, "root"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                root_stdout, root_stderr = root_process.communicate()
                
                # 执行adb remount
                self._log_message(f"[APP操作] 执行: adb -s {device} remount")
                remount_process = subprocess.Popen(
                    ["adb", "-s", device, "remount"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                remount_stdout, remount_stderr = remount_process.communicate()
                
                # 在主线程中更新UI
                self.app.root.after(0, lambda: self.handle_root_remount_result(
                    root_stdout, root_stderr, remount_stdout, remount_stderr
                ))
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self.app.root.after(0, lambda: self.handle_query_error(error_msg))
        
        # 启动后台线程
        thread = threading.Thread(target=run_commands, daemon=True)
        thread.start()
    
    def execute_push_file(self, device, local_file, target_path):
        """执行推送单个文件"""
        cmd = f"adb -s {device} push \"{local_file}\" \"{target_path}\""
        self._log_message(f"[APP操作] 执行命令: {cmd}")
        self._log_message(f"[APP操作] 推送文件: {local_file}")
        
        # 在后台线程中执行命令
        def run_command():
            try:
                # 构建命令参数
                cmd_parts = ["adb", "-s", device, "push", local_file, target_path]
                
                # 执行命令
                process = subprocess.Popen(
                    cmd_parts,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                stdout, stderr = process.communicate()
                
                # 在主线程中更新UI
                self.app.root.after(0, lambda: self.handle_push_result(stdout, stderr, cmd, local_file))
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self.app.root.after(0, lambda: self.handle_query_error(error_msg))
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
    def execute_push_folder(self, device, local_folder, target_path):
        """执行推送整个文件夹"""
        cmd = f"adb -s {device} push \"{local_folder}\" \"{target_path}\""
        self._log_message(f"[APP操作] 执行命令: {cmd}")
        self._log_message(f"[APP操作] 推送文件夹: {local_folder}")
        
        # 在后台线程中执行命令
        def run_command():
            try:
                # 构建命令参数
                cmd_parts = ["adb", "-s", device, "push", local_folder, target_path]
                
                # 执行命令
                process = subprocess.Popen(
                    cmd_parts,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                stdout, stderr = process.communicate()
                
                # 在主线程中更新UI
                self.app.root.after(0, lambda: self.handle_push_result(stdout, stderr, cmd, local_folder))
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self.app.root.after(0, lambda: self.handle_query_error(error_msg))
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
    def handle_root_remount_result(self, root_stdout, root_stderr, remount_stdout, remount_stderr):
        """处理root和remount命令结果"""
        if root_stderr:
            self._log_message(f"[APP操作] Root错误信息: {root_stderr}")
        
        if root_stdout:
            self._log_message(f"[APP操作] Root输出: {root_stdout}")
        
        if remount_stderr:
            self._log_message(f"[APP操作] Remount错误信息: {remount_stderr}")
        
        if remount_stdout:
            self._log_message(f"[APP操作] Remount输出: {remount_stdout}")
        
        # 检查是否成功
        if "restarting" in root_stdout.lower() or "remount succeeded" in remount_stdout.lower():
            self._log_message(f"[APP操作] Root和Remount操作成功!")
            messagebox.showinfo("操作成功", "Root和Remount操作成功!")
        else:
            self._log_message(f"[APP操作] Root和Remount操作完成")
            messagebox.showinfo("操作完成", "Root和Remount操作完成，请查看日志了解详细信息")
    
    def handle_push_result(self, stdout, stderr, cmd, local_path):
        """处理推送结果"""
        if stderr:
            self._log_message(f"[APP操作] 错误信息: {stderr}")
        
        if stdout:
            self._log_message(f"[APP操作] 推送输出: {stdout}")
            
            # 检查推送是否成功
            if "pushed" in stdout.lower() or "success" in stdout.lower():
                self._log_message(f"[APP操作] 文件推送成功!")
                messagebox.showinfo("推送成功", f"文件推送成功!")
            elif "failed" in stdout.lower() or "error" in stdout.lower():
                self._log_message(f"[APP操作] 文件推送失败!")
                messagebox.showerror("推送失败", "文件推送失败!")
            else:
                # 其他情况，显示完整输出
                self._log_message(f"[APP操作] 推送完成，请检查输出信息")
                messagebox.showinfo("推送完成", "文件推送完成，请查看日志了解详细信息")
        else:
            # 没有输出通常表示成功
            self._log_message(f"[APP操作] 文件推送成功!")
            messagebox.showinfo("推送成功", "文件推送成功!")
    
