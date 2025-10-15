#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APP操作管理器 - PyQt5版本
负责Android应用的安装、卸载、查询等操作
完整迁移自App_Operations/app_operations_manager.py
"""

import subprocess
import os
import re
import threading
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QThread, Qt
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QCheckBox, QLineEdit, QGroupBox, 
                             QRadioButton, QFileDialog, QMessageBox, QTextEdit)


class AppOperationsManager(QObject):
    """APP操作管理器 - PyQt5版本"""
    
    # 信号定义
    log_message = pyqtSignal(str)  # 日志消息信号
    
    def __init__(self, device_manager, parent=None):
        """初始化APP操作管理器"""
        super().__init__(parent)
        self.device_manager = device_manager
        
    def query_package(self):
        """查询package信息"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 显示参数选择对话框
        self.show_package_query_dialog(device)
    
    def query_package_name(self):
        """查询包名"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 显示提示对话框
        self.show_package_name_query_dialog(device)
    
    def query_install_path(self):
        """查询安装路径"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 显示包名输入对话框
        self.show_package_name_input_dialog(device)
    
    def pull_apk(self):
        """拉取APK文件"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 显示路径输入对话框
        self.show_pull_apk_dialog(device)
    
    def install_apk(self):
        """安装APK文件"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 显示APK安装参数选择对话框
        self.show_install_apk_dialog(device)
    
    def view_processes(self):
        """查看进程"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 显示进程查看参数选择对话框
        self.show_process_view_dialog(device)
    
    def dump_app(self):
        """Dump应用信息"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 显示dump应用对话框
        self.show_dump_app_dialog(device)
    
    def enable_app(self):
        """启用应用"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 显示包名输入对话框
        self.show_enable_app_dialog(device)
    
    def disable_app(self):
        """禁用应用"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 显示包名输入对话框
        self.show_disable_app_dialog(device)
    
    def push_apk(self):
        """推送文件到设备"""
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 显示推送目标路径对话框
        self.show_push_apk_dialog(device)
    
    def show_package_query_dialog(self, device):
        """显示package查询参数选择对话框"""
        dialog = PackageQueryDialog(device, self)
        dialog.exec_()
    
    def show_package_name_query_dialog(self, device):
        """显示包名查询提示对话框"""
        dialog = PackageNameQueryDialog(device, self)
        dialog.exec_()
    
    def show_package_name_input_dialog(self, device):
        """显示包名输入对话框"""
        dialog = PackageNameInputDialog(device, self)
        dialog.exec_()
    
    def show_pull_apk_dialog(self, device):
        """显示pull APK包名输入对话框"""
        dialog = PullApkDialog(device, self)
        dialog.exec_()
    
    def show_install_apk_dialog(self, device):
        """显示APK安装参数选择对话框"""
        dialog = InstallApkDialog(device, self)
        dialog.exec_()
    
    def show_process_view_dialog(self, device):
        """显示进程查看参数选择对话框"""
        dialog = ProcessViewDialog(device, self)
        dialog.exec_()
    
    def show_dump_app_dialog(self, device):
        """显示dump应用对话框"""
        dialog = DumpAppDialog(device, self)
        dialog.exec_()
    
    def show_enable_app_dialog(self, device):
        """显示启用应用包名输入对话框"""
        dialog = EnableAppDialog(device, self)
        dialog.exec_()
    
    def show_disable_app_dialog(self, device):
        """显示禁用应用包名输入对话框"""
        dialog = DisableAppDialog(device, self)
        dialog.exec_()
    
    def show_push_apk_dialog(self, device):
        """显示推送文件对话框"""
        dialog = PushApkDialog(device, self)
        dialog.exec_()
    
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
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
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
                self._handle_query_result(stdout, stderr, cmd)
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self._handle_query_error(error_msg)
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
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
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                stdout, stderr = process.communicate()
                
                # 在主线程中更新UI
                self._handle_package_name_result(stdout, stderr, cmd)
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self._handle_query_error(error_msg)
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
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
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                stdout, stderr = process.communicate()
                
                # 在主线程中更新UI
                self._handle_install_path_result(stdout, stderr, cmd, package_name)
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self._handle_query_error(error_msg)
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
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
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    error_msg = f"获取APK路径失败: {stderr.strip()}"
                    self._handle_query_error(error_msg)
                    return
                
                # 解析输出获取所有APK路径
                apk_paths = []
                for line in stdout.strip().split('\n'):
                    if line.startswith('package:'):
                        apk_path = line.replace('package:', '').strip()
                        apk_paths.append(apk_path)
                
                if not apk_paths:
                    error_msg = f"未找到包 {package_name} 的APK路径"
                    self._handle_query_error(error_msg)
                    return
                
                self._log_message(f"[APP操作] 找到 {len(apk_paths)} 个APK文件:")
                for i, path in enumerate(apk_paths, 1):
                    filename = os.path.basename(path)
                    self._log_message(f"[APP操作]   {i}. {filename}")
                
                # 第二步：执行pull操作（拉取所有APK文件）
                self._log_message(f"[APP操作] 开始拉取所有APK文件...")
                self.execute_pull_multiple_apks(device, apk_paths, package_name)
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self._handle_query_error(error_msg)
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
    def execute_pull_multiple_apks(self, device, apk_paths, package_name):
        """执行多个APK文件的拉取"""
        # 创建保存目录
        date_str = datetime.now().strftime("%Y%m%d")
        save_dir = f"c:\\log\\{date_str}\\{package_name}"
        
        try:
            os.makedirs(save_dir, exist_ok=True)
        except Exception as e:
            self._log_message(f"[APP操作] 创建保存目录失败: {str(e)}")
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
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
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
            self._handle_multiple_pull_result(success_count, len(apk_paths), failed_files, save_dir)
        
        # 启动后台线程
        thread = threading.Thread(target=run_multiple_pulls, daemon=True)
        thread.start()
    
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
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                stdout, stderr = process.communicate()
                
                # 在主线程中更新UI
                self._handle_install_apk_result(stdout, stderr, cmd, apk_files)
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self._handle_query_error(error_msg)
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
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
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
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
                self._handle_process_view_result(stdout, stderr, cmd)
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self._handle_query_error(error_msg)
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
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
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                stdout, stderr = process.communicate()
                
                # 在主线程中更新UI
                self._handle_enable_app_result(stdout, stderr, cmd, package_name)
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self._handle_query_error(error_msg)
        
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
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                stdout, stderr = process.communicate()
                
                # 在主线程中更新UI
                self._handle_disable_app_result(stdout, stderr, cmd, package_name)
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self._handle_query_error(error_msg)
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
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
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                stdout, stderr = process.communicate()
                
                # 如果有过滤条件，在Python中过滤结果
                if selected_filter and stdout:
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
                self._handle_dump_app_result(stdout, stderr, cmd, package_name)
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self._handle_query_error(error_msg)
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
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
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                root_stdout, root_stderr = root_process.communicate()
                
                # 执行adb remount
                self._log_message(f"[APP操作] 执行: adb -s {device} remount")
                remount_process = subprocess.Popen(
                    ["adb", "-s", device, "remount"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                remount_stdout, remount_stderr = remount_process.communicate()
                
                # 在主线程中更新UI
                self._handle_root_remount_result(root_stdout, root_stderr, remount_stdout, remount_stderr)
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self._handle_query_error(error_msg)
        
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
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                stdout, stderr = process.communicate()
                
                # 在主线程中更新UI
                self._handle_push_result(stdout, stderr, cmd, local_file)
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self._handle_query_error(error_msg)
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
    # ========== 结果处理方法 ==========
    
    def _handle_query_result(self, stdout, stderr, cmd):
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
    
    def _handle_query_error(self, error_msg):
        """处理查询错误"""
        self._log_message(f"[APP操作] {error_msg}")
    
    def _handle_package_name_result(self, stdout, stderr, cmd):
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
    
    def _handle_install_path_result(self, stdout, stderr, cmd, package_name):
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
    
    def _handle_multiple_pull_result(self, success_count, total_count, failed_files, save_dir):
        """处理多个APK拉取结果"""
        if success_count == total_count:
            # 全部成功 - 直接打开文件夹，不显示对话框
            self._log_message(f"[APP操作] 所有APK文件拉取成功！成功拉取: {success_count}/{total_count} 个文件")
            self._log_message(f"[APP操作] 保存位置: {save_dir}")
            self.open_folder_with_selection(save_dir)
        elif success_count > 0:
            # 部分成功 - 直接打开文件夹，不显示对话框
            failed_list = "\n".join(failed_files) if failed_files else "无"
            self._log_message(f"[APP操作] APK文件拉取完成（部分成功）")
            self._log_message(f"[APP操作] 成功: {success_count}/{total_count} 个文件")
            self._log_message(f"[APP操作] 失败: {len(failed_files)} 个文件")
            self._log_message(f"[APP操作] 保存位置: {save_dir}")
            self.open_folder_with_selection(save_dir)
        else:
            # 全部失败 - 只记录日志
            self._log_message(f"[APP操作] 所有APK文件拉取失败！")
            self._log_message(f"[APP操作] 失败的文件数: {total_count}")
            self._log_message(f"[APP操作] 可能的原因: 设备路径不存在、权限不足、网络连接问题")
    
    def open_folder_with_selection(self, folder_path):
        """打开文件夹"""
        try:
            os.startfile(folder_path)
        except Exception as e:
            self._log_message(f"[APP操作] 打开文件夹失败: {str(e)}")
    
    def _handle_install_apk_result(self, stdout, stderr, cmd, apk_files):
        """处理APK安装结果"""
        if stderr:
            self._log_message(f"[APP操作] 错误信息: {stderr}")
        
        if stdout:
            self._log_message(f"[APP操作] 安装输出: {stdout}")
            
            # 检查安装是否成功 - 严格按照"Success"判断
            if "Success" in stdout:
                self._log_message(f"[APP操作] APK安装成功!")
            else:
                # 没有"Success"就判定为安装失败
                self._log_message(f"[APP操作] APK安装失败!")
                self._log_message(f"[APP操作] 输出信息: {stdout}")
                if stderr:
                    self._log_message(f"[APP操作] 错误信息: {stderr}")
        else:
            self._log_message(f"[APP操作] 未获取到输出信息")
    
    def _handle_process_view_result(self, stdout, stderr, cmd):
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
    
    def _handle_enable_app_result(self, stdout, stderr, cmd, package_name):
        """处理启用应用结果"""
        if stderr:
            self._log_message(f"[APP操作] 错误信息: {stderr}")
        
        if stdout:
            self._log_message(f"[APP操作] 启用输出: {stdout}")
            
            # 检查启用是否成功
            if "Success" in stdout or "success" in stdout or "enabled" in stdout.lower():
                self._log_message(f"[APP操作] 应用 {package_name} 启用成功!")
            elif "Failure" in stdout or "failure" in stdout or "Error" in stdout or "error" in stdout:
                self._log_message(f"[APP操作] 应用 {package_name} 启用失败!")
            else:
                # 其他情况，显示完整输出
                self._log_message(f"[APP操作] 启用完成，请检查输出信息")
        else:
            # 没有输出通常表示成功
            self._log_message(f"[APP操作] 应用 {package_name} 启用成功!")
    
    def _handle_disable_app_result(self, stdout, stderr, cmd, package_name):
        """处理禁用应用结果"""
        if stderr:
            self._log_message(f"[APP操作] 错误信息: {stderr}")
        
        if stdout:
            self._log_message(f"[APP操作] 禁用输出: {stdout}")
            
            # 检查禁用是否成功
            if "Success" in stdout or "success" in stdout or "disabled" in stdout.lower():
                self._log_message(f"[APP操作] 应用 {package_name} 禁用成功!")
            elif "Failure" in stdout or "failure" in stdout or "Error" in stdout or "error" in stdout:
                self._log_message(f"[APP操作] 应用 {package_name} 禁用失败!")
            else:
                # 其他情况，显示完整输出
                self._log_message(f"[APP操作] 禁用完成，请检查输出信息")
        else:
            # 没有输出通常表示成功
            self._log_message(f"[APP操作] 应用 {package_name} 禁用成功!")
    
    def _handle_dump_app_result(self, stdout, stderr, cmd, package_name):
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
    
    def _handle_root_remount_result(self, root_stdout, root_stderr, remount_stdout, remount_stderr):
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
        else:
            self._log_message(f"[APP操作] Root和Remount操作完成")
    
    def _handle_push_result(self, stdout, stderr, cmd, local_path):
        """处理推送结果"""
        # 合并stdout和stderr（adb push的成功输出可能在stderr中）
        combined_output = (stdout + stderr).strip()
        
        if combined_output:
            self._log_message(f"[APP操作] 推送输出: {combined_output}")
            
            # 优先检查错误信息（即使有pushed，如果有error/failed也应该判定为失败）
            if "error:" in combined_output.lower() or "failed to copy" in combined_output.lower():
                self._log_message(f"[APP操作] 文件推送失败!")
            elif "pushed" in combined_output.lower() or "success" in combined_output.lower():
                self._log_message(f"[APP操作] 文件推送成功!")
            else:
                # 其他情况，显示完整输出
                self._log_message(f"[APP操作] 推送完成，请检查输出信息")
        else:
            # 没有输出通常表示成功
            self._log_message(f"[APP操作] 文件推送成功!")
    
    def _log_message(self, message):
        """在日志区域显示消息"""
        # 添加时间戳
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        self.log_message.emit(log_message)


# ========== 对话框类定义 ==========

class PackageQueryDialog(QDialog):
    """Package查询参数选择对话框"""
    
    def __init__(self, device, manager, parent=None):
        super().__init__(parent)
        self.device = device
        self.manager = manager
        self.setWindowTitle("查询Package参数选择")
        self.setMinimumSize(500, 500)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("选择查询参数")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)
        
        # 参数选择组
        params_group = QGroupBox("查询参数")
        params_layout = QVBoxLayout()
        
        self.param_checkboxes = {}
        param_options = [
            ("-3", "显示第三方应用"),
            ("-s", "显示系统应用"),
            ("-f", "显示每个包名及其对应的APK文件路径"),
            ("-e", "显示enable的app"),
            ("-d", "显示disable的app"),
            ("-i", "显示app安装源")
        ]
        
        for param, description in param_options:
            cb = QCheckBox(f"{param}: {description}")
            self.param_checkboxes[param] = cb
            params_layout.addWidget(cb)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # 过滤选项组
        filter_group = QGroupBox("过滤选项")
        filter_layout = QVBoxLayout()
        
        self.filter_enabled_cb = QCheckBox("启用过滤")
        filter_layout.addWidget(self.filter_enabled_cb)
        
        filter_input_layout = QHBoxLayout()
        filter_input_layout.addWidget(QLabel("过滤字符:"))
        self.filter_entry = QLineEdit()
        filter_input_layout.addWidget(self.filter_entry)
        
        filter_layout.addLayout(filter_input_layout)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.confirm_btn = QPushButton("确定")
        self.confirm_btn.clicked.connect(self.on_confirm)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.confirm_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
    
    def on_confirm(self):
        # 收集选中的参数
        selected_params = []
        for param, cb in self.param_checkboxes.items():
            if cb.isChecked():
                selected_params.append(param)
        
        # 获取过滤选项
        filter_text = ""
        if self.filter_enabled_cb.isChecked():
            filter_text = self.filter_entry.text().strip()
        
        self.accept()
        
        # 执行查询
        self.manager.execute_package_query(self.device, selected_params, filter_text)


class PackageNameQueryDialog(QDialog):
    """包名查询提示对话框"""
    
    def __init__(self, device, manager, parent=None):
        super().__init__(parent)
        self.device = device
        self.manager = manager
        self.setWindowTitle("查询当前应用包名")
        self.setFixedSize(400, 200)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("查询当前前台应用包名")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)
        
        # 提示信息
        info = QLabel("请先在手机上打开需要查询的应用，\n然后点击确认按钮开始查询。")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.confirm_btn = QPushButton("确认查询")
        self.confirm_btn.clicked.connect(self.on_confirm)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.confirm_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
    
    def on_confirm(self):
        self.accept()
        self.manager.execute_package_name_query(self.device)


class PackageNameInputDialog(QDialog):
    """包名输入对话框"""
    
    def __init__(self, device, manager, parent=None):
        super().__init__(parent)
        self.device = device
        self.manager = manager
        self.setWindowTitle("查询应用安装路径")
        self.setFixedSize(450, 250)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("查询应用安装路径")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)
        
        # 说明信息
        info = QLabel("请输入要查询的应用包名：")
        layout.addWidget(info)
        
        # 包名输入框
        self.package_entry = QLineEdit()
        self.package_entry.setPlaceholderText("例如: com.google.android.apps.messaging")
        layout.addWidget(self.package_entry)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.confirm_btn = QPushButton("查询")
        self.confirm_btn.clicked.connect(self.on_confirm)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.confirm_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
    
    def on_confirm(self):
        package_name = self.package_entry.text().strip()
        if not package_name:
            QMessageBox.warning(self, "输入错误", "请输入应用包名")
            return
        
        self.accept()
        self.manager.execute_install_path_query(self.device, package_name)


class PullApkDialog(QDialog):
    """Pull APK对话框"""
    
    def __init__(self, device, manager, parent=None):
        super().__init__(parent)
        self.device = device
        self.manager = manager
        self.setWindowTitle("拉取APK文件")
        self.setFixedSize(500, 300)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("拉取APK文件")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)
        
        # 说明信息
        info = QLabel("请输入应用包名：")
        layout.addWidget(info)
        
        # 包名输入框
        self.package_entry = QLineEdit()
        self.package_entry.setPlaceholderText("例如: com.example.app")
        layout.addWidget(self.package_entry)
        
        # 保存路径信息
        save_info = QLabel("文件将保存到: c:\\log\\yyyymmdd\\<包名>")
        save_info.setStyleSheet("color: blue;")
        layout.addWidget(save_info)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.confirm_btn = QPushButton("开始拉取")
        self.confirm_btn.clicked.connect(self.on_confirm)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.confirm_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
    
    def on_confirm(self):
        package_name = self.package_entry.text().strip()
        if not package_name:
            QMessageBox.warning(self, "输入错误", "请输入应用包名")
            return
        
        self.accept()
        self.manager.execute_pull_apk_by_package(self.device, package_name)


class InstallApkDialog(QDialog):
    """APK安装参数选择对话框"""
    
    def __init__(self, device, manager, parent=None):
        super().__init__(parent)
        self.device = device
        self.manager = manager
        self.setWindowTitle("安装APK文件")
        self.setMinimumSize(600, 500)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("安装APK文件")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)
        
        # 参数选择组
        params_group = QGroupBox("安装参数（可选）")
        params_layout = QVBoxLayout()
        
        self.param_checkboxes = {}
        param_options = [
            ("-r", "覆盖安装，保留用户数据"),
            ("-d", "允许降级安装"),
            ("-t", "安装测试版，即便签名不同"),
            ("-g", "自动授予运行时权限"),
            ("--bypass-low-target-sdk-block", "忽略低 targetSdk 限制"),
            ("install-multiple", "安装多个APK文件，针对 split APK")
        ]
        
        for param, description in param_options:
            cb = QCheckBox(f"{param}: {description}")
            self.param_checkboxes[param] = cb
            params_layout.addWidget(cb)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.next_btn = QPushButton("下一步")
        self.next_btn.clicked.connect(self.on_next)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.next_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
    
    def on_next(self):
        # 收集选中的参数
        selected_params = []
        for param, cb in self.param_checkboxes.items():
            if cb.isChecked():
                selected_params.append(param)
        
        self.accept()
        
        # 显示文件选择对话框
        self.manager.show_apk_selection_dialog(self.device, selected_params)


class ProcessViewDialog(QDialog):
    """进程查看参数选择对话框"""
    
    def __init__(self, device, manager, parent=None):
        super().__init__(parent)
        self.device = device
        self.manager = manager
        self.setWindowTitle("查看进程")
        self.setMinimumSize(500, 400)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("查看进程参数选择")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)
        
        # 参数选择组
        params_group = QGroupBox("查看参数")
        params_layout = QVBoxLayout()
        
        self.param_checkboxes = {}
        param_options = [
            ("-A", "显示所有进程"),
            ("-T", "显示线程"),
            ("-f", "显示完整格式")
        ]
        
        for param, description in param_options:
            cb = QCheckBox(f"{param}: {description}")
            if param == "-A":  # 默认勾选-A
                cb.setChecked(True)
            self.param_checkboxes[param] = cb
            params_layout.addWidget(cb)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # 过滤选项组
        filter_group = QGroupBox("过滤选项")
        filter_layout = QVBoxLayout()
        
        self.filter_enabled_cb = QCheckBox("启用过滤")
        filter_layout.addWidget(self.filter_enabled_cb)
        
        filter_input_layout = QHBoxLayout()
        filter_input_layout.addWidget(QLabel("过滤字符:"))
        self.filter_entry = QLineEdit()
        filter_input_layout.addWidget(self.filter_entry)
        
        filter_layout.addLayout(filter_input_layout)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.confirm_btn = QPushButton("确定")
        self.confirm_btn.clicked.connect(self.on_confirm)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.confirm_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
    
    def on_confirm(self):
        # 收集选中的参数
        selected_params = []
        for param, cb in self.param_checkboxes.items():
            if cb.isChecked():
                selected_params.append(param)
        
        # 获取过滤选项
        filter_text = ""
        if self.filter_enabled_cb.isChecked():
            filter_text = self.filter_entry.text().strip()
        
        self.accept()
        
        # 执行进程查看
        self.manager.execute_process_view(self.device, selected_params, filter_text)


class DumpAppDialog(QDialog):
    """Dump应用对话框"""
    
    def __init__(self, device, manager, parent=None):
        super().__init__(parent)
        self.device = device
        self.manager = manager
        self.setWindowTitle("Dump应用信息")
        self.setMinimumSize(600, 500)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("Dump应用信息")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)
        
        # 包名输入组
        package_group = QGroupBox("应用包名")
        package_layout = QVBoxLayout()
        
        self.package_entry = QLineEdit()
        self.package_entry.setPlaceholderText("例如: com.google.android.apps.messaging")
        package_layout.addWidget(self.package_entry)
        
        package_group.setLayout(package_layout)
        layout.addWidget(package_group)
        
        # 过滤选项组
        filter_group = QGroupBox("过滤选项（可选）")
        filter_layout = QVBoxLayout()
        
        # 预定义过滤选项（单选）
        predefined_label = QLabel("预定义过滤选项:")
        predefined_label.setStyleSheet("font-weight: bold;")
        filter_layout.addWidget(predefined_label)
        
        self.predefined_group = QRadioButton("permission: 权限")
        self.predefined_group.setProperty("value", "permission")
        filter_layout.addWidget(self.predefined_group)
        
        self.predefined_version = QRadioButton("versionName: 版本号")
        self.predefined_version.setProperty("value", "versionName")
        filter_layout.addWidget(self.predefined_version)
        
        self.predefined_path = QRadioButton("path: 安装路径")
        self.predefined_path.setProperty("value", "path")
        filter_layout.addWidget(self.predefined_path)
        
        # 自定义过滤选项
        custom_filter_layout = QHBoxLayout()
        self.custom_rb = QRadioButton("自定义过滤:")
        self.custom_rb.setProperty("value", "custom")
        custom_filter_layout.addWidget(self.custom_rb)
        
        self.custom_entry = QLineEdit()
        custom_filter_layout.addWidget(self.custom_entry)
        
        self.regex_cb = QCheckBox("启用正则表达式")
        self.regex_cb.setChecked(True)
        custom_filter_layout.addWidget(self.regex_cb)
        
        filter_layout.addLayout(custom_filter_layout)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.confirm_btn = QPushButton("开始Dump")
        self.confirm_btn.clicked.connect(self.on_confirm)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.confirm_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
    
    def on_confirm(self):
        package_name = self.package_entry.text().strip()
        if not package_name:
            QMessageBox.warning(self, "输入错误", "请输入应用包名")
            return
        
        # 收集选中的过滤选项（单选）
        selected_filter = None
        selected_regex_enabled = False
        
        # 检查预定义选项
        if self.predefined_group.isChecked():
            selected_filter = self.predefined_group.property("value")
        elif self.predefined_version.isChecked():
            selected_filter = self.predefined_version.property("value")
        elif self.predefined_path.isChecked():
            selected_filter = self.predefined_path.property("value")
        elif self.custom_rb.isChecked():
            custom_text = self.custom_entry.text().strip()
            if custom_text:
                selected_filter = custom_text
                selected_regex_enabled = self.regex_cb.isChecked()
        
        self.accept()
        
        # 执行dump命令
        self.manager.execute_dump_app(self.device, package_name, selected_filter, selected_regex_enabled)


class EnableAppDialog(QDialog):
    """启用应用对话框"""
    
    def __init__(self, device, manager, parent=None):
        super().__init__(parent)
        self.device = device
        self.manager = manager
        self.setWindowTitle("启用应用")
        self.setFixedSize(450, 250)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("启用应用")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)
        
        # 说明信息
        info = QLabel("请输入要启用的应用包名：")
        layout.addWidget(info)
        
        # 包名输入框
        self.package_entry = QLineEdit()
        self.package_entry.setPlaceholderText("例如: com.google.android.apps.messaging")
        layout.addWidget(self.package_entry)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.confirm_btn = QPushButton("启用")
        self.confirm_btn.clicked.connect(self.on_confirm)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.confirm_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
    
    def on_confirm(self):
        package_name = self.package_entry.text().strip()
        if not package_name:
            QMessageBox.warning(self, "输入错误", "请输入应用包名")
            return
        
        self.accept()
        self.manager.execute_enable_app(self.device, package_name)


class DisableAppDialog(QDialog):
    """禁用应用对话框"""
    
    def __init__(self, device, manager, parent=None):
        super().__init__(parent)
        self.device = device
        self.manager = manager
        self.setWindowTitle("禁用应用")
        self.setFixedSize(450, 250)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("禁用应用")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)
        
        # 说明信息
        info = QLabel("请输入要禁用的应用包名：")
        layout.addWidget(info)
        
        # 包名输入框
        self.package_entry = QLineEdit()
        self.package_entry.setPlaceholderText("例如: com.google.android.apps.messaging")
        layout.addWidget(self.package_entry)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.confirm_btn = QPushButton("禁用")
        self.confirm_btn.clicked.connect(self.on_confirm)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.confirm_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
    
    def on_confirm(self):
        package_name = self.package_entry.text().strip()
        if not package_name:
            QMessageBox.warning(self, "输入错误", "请输入应用包名")
            return
        
        self.accept()
        self.manager.execute_disable_app(self.device, package_name)


class PushApkDialog(QDialog):
    """推送文件对话框"""
    
    def __init__(self, device, manager, parent=None):
        super().__init__(parent)
        self.device = device
        self.manager = manager
        self.setWindowTitle("推送文件到设备")
        self.setFixedSize(500, 300)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("推送文件到设备")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)
        
        # 目标路径输入组
        path_group = QGroupBox("设备目标路径")
        path_layout = QVBoxLayout()
        
        self.target_path_entry = QLineEdit()
        self.target_path_entry.setPlaceholderText("例如: /system/app/ 或 /data/local/tmp/")
        path_layout.addWidget(self.target_path_entry)
        
        path_group.setLayout(path_layout)
        layout.addWidget(path_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.root_remount_btn = QPushButton("adb root&adb remount")
        self.root_remount_btn.clicked.connect(self.on_root_remount)
        self.confirm_btn = QPushButton("确认")
        self.confirm_btn.clicked.connect(self.on_confirm)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.root_remount_btn)
        button_layout.addWidget(self.confirm_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
    
    def on_root_remount(self):
        self.manager.execute_root_remount(self.device)
    
    def on_confirm(self):
        target_path = self.target_path_entry.text().strip()
        if not target_path:
            QMessageBox.warning(self, "输入错误", "请输入设备目标路径")
            return
        
        self.accept()
        
        # 显示文件选择对话框
        self.manager.show_file_selection_dialog(self.device, target_path)
    
    def show_file_selection_dialog(self, device, target_path):
        """显示文件选择对话框"""
        # 选择文件或文件夹
        files, _ = QFileDialog.getOpenFileNames(
            None,
            "选择要推送的文件或文件夹",
            "",
            "All files (*.*)"
        )
        
        if files:
            # 检查是否选择了文件夹（通过检查父目录）
            for file_path in files:
                if os.path.isdir(file_path):
                    # 推送整个文件夹
                    self.manager.execute_push_folder(device, file_path, target_path)
                else:
                    # 推送单个文件
                    self.manager.execute_push_file(device, file_path, target_path)
        else:
            QMessageBox.information(None, "提示", "未选择任何文件")
    
    def execute_push_folder(self, device, local_folder, target_path):
        """执行推送整个文件夹"""
        cmd = f"adb -s {device} push \"{local_folder}\" \"{target_path}\""
        self.manager._log_message(f"[APP操作] 执行命令: {cmd}")
        self.manager._log_message(f"[APP操作] 推送文件夹: {local_folder}")
        
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
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                stdout, stderr = process.communicate()
                
                # 在主线程中更新UI
                self.manager._handle_push_result(stdout, stderr, cmd, local_folder)
                
            except Exception as e:
                error_msg = f"执行命令失败: {str(e)}"
                self.manager._handle_query_error(error_msg)
        
        # 启动后台线程
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()


# 添加缺少的方法到AppOperationsManager
def show_apk_selection_dialog(self, device, selected_params):
    """显示APK文件选择对话框"""
    # 检查是否选择了install-multiple参数
    is_multiple_install = "install-multiple" in selected_params
    
    # 提示信息
    if is_multiple_install:
        info_text = "选择了 install-multiple 参数，可以选择多个APK文件（split APK）"
        filetypes = "APK files (*.apk);;All files (*.*)"
        selection_mode = "multiple"
    else:
        info_text = "请选择一个APK文件进行安装"
        filetypes = "APK files (*.apk);;All files (*.*)"
        selection_mode = "single"
    
    if is_multiple_install:
        # 多选模式
        files, _ = QFileDialog.getOpenFileNames(
            None,
            "选择APK文件（可多选）",
            "",
            filetypes
        )
    else:
        # 单选模式
        file, _ = QFileDialog.getOpenFileName(
            None,
            "选择APK文件",
            "",
            filetypes
        )
        files = [file] if file else []
    
    if files:
        self.execute_install_apk(device, selected_params, files)


def show_file_selection_dialog(self, device, target_path):
    """显示文件选择对话框"""
    # 选择文件或文件夹
    files, _ = QFileDialog.getOpenFileNames(
        None,
        "选择要推送的文件或文件夹",
        "",
        "All files (*.*)"
    )
    
    if files:
        # 检查是否选择了文件夹（通过检查父目录）
        for file_path in files:
            if os.path.isdir(file_path):
                # 推送整个文件夹
                self.execute_push_folder(device, file_path, target_path)
            else:
                    # 推送单个文件
                    self.execute_push_file(device, file_path, target_path)


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
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            stdout, stderr = process.communicate()
            
            # 在主线程中更新UI
            self._handle_push_result(stdout, stderr, cmd, local_folder)
            
        except Exception as e:
            error_msg = f"执行命令失败: {str(e)}"
            self._handle_query_error(error_msg)
    
    # 启动后台线程
    thread = threading.Thread(target=run_command, daemon=True)
    thread.start()


# 将方法添加到类
AppOperationsManager.show_apk_selection_dialog = show_apk_selection_dialog
AppOperationsManager.show_file_selection_dialog = show_file_selection_dialog
AppOperationsManager.execute_push_folder = execute_push_folder

