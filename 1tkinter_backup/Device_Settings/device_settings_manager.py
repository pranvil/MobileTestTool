#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备设置管理器
负责设置灭屏时间、合并MTKlog、MTKlog提取pcap等功能
"""

import subprocess
import os
import shutil
import zipfile
import glob
import json
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, filedialog, simpledialog, ttk

class DeviceSettingsManager:
    def __init__(self, app_instance):
        """
        初始化设备设置管理器
        
        Args:
            app_instance: 主应用程序实例
        """
        self.app = app_instance
        self.device_manager = app_instance.device_manager
        self.config_file = os.path.expanduser("~/.netui/tool_config.json")
        self.tool_config = self._load_tool_config()
    
    def _load_tool_config(self):
        """加载工具配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[DEBUG] 加载工具配置失败: {str(e)}")
        
        return {
            "mtk_tools": [],
            "qualcomm_tools": [],
            "wireshark_path": "",
            "last_used_mtk": "",
            "last_used_qualcomm": "",
            "last_used_wireshark": ""
        }
    
    def _save_tool_config(self):
        """保存工具配置"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.tool_config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[DEBUG] 保存工具配置失败: {str(e)}")
            return False
    
    def _log_message(self, message, color_tag="info"):
        """添加日志消息到日志显示区域"""
        try:
            # 获取当前时间
            current_time = datetime.now().strftime("%H:%M:%S")
            log_message = f"[{current_time}] {message}\n"
            
            # 使用after(0)确保立即在主线程中执行
            self.app.root.after(0, lambda: self._update_log_display(log_message, color_tag))
            
        except Exception as e:
            print(f"记录日志消息失败: {e}")
    
    def _update_log_display(self, message, color_tag="info"):
        """更新日志显示"""
        try:
            if hasattr(self.app, 'ui') and hasattr(self.app.ui, 'log_text'):
                # 确保控件可编辑
                self.app.ui.log_text.config(state=tk.NORMAL)
                
                # 插入消息
                start_index = self.app.ui.log_text.index(tk.END + "-1c")
                self.app.ui.log_text.insert(tk.END, message)
                end_index = self.app.ui.log_text.index(tk.END + "-1c")
                
                # 应用颜色标签
                if color_tag == "success":
                    self.app.ui.log_text.tag_add("success", start_index, end_index)
                    self.app.ui.log_text.tag_config("success", foreground="#00AA00")  # 绿色
                elif color_tag == "error":
                    self.app.ui.log_text.tag_add("error", start_index, end_index)
                    self.app.ui.log_text.tag_config("error", foreground="#FF4444")  # 红色
                elif color_tag == "info":
                    self.app.ui.log_text.tag_add("info", start_index, end_index)
                    self.app.ui.log_text.tag_config("info", foreground="#0088FF")  # 蓝色
                
                self.app.ui.log_text.see(tk.END)
                
                # 保持原有状态（如果正在过滤则保持DISABLED）
                if hasattr(self.app, 'is_running') and self.app.is_running:
                    self.app.ui.log_text.config(state=tk.DISABLED)
                else:
                    self.app.ui.log_text.config(state=tk.NORMAL)
                    
        except Exception as e:
            print(f"更新日志显示失败: {e}")
    
    def configure_tools(self):
        """配置MTK工具和Wireshark路径"""
        try:
            # 创建配置对话框
            dialog = tk.Toplevel(self.app.root)
            dialog.title("工具路径配置")
            dialog.geometry("600x600")
            dialog.resizable(False, False)
            dialog.transient(self.app.root)
            # dialog.grab_set()  # 注释掉以允许在程序和桌面之间自由切换
            
            # 居中显示
            dialog.geometry("+%d+%d" % (
                self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 600) // 2,
                self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 600) // 2
            ))
            
            # 主框架
            main_frame = ttk.Frame(dialog, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 标题
            title_label = ttk.Label(main_frame, text="工具路径配置", font=('Arial', 14, 'bold'))
            title_label.pack(pady=(0, 20))
            
            # MTK工具配置框架
            mtk_frame = ttk.LabelFrame(main_frame, text="ELT路径配置", padding="10")
            mtk_frame.pack(fill=tk.X, pady=(0, 15))
            
            # 检测MTK工具按钮
            ttk.Button(mtk_frame, text="自动检测", command=lambda: self._detect_mtk_tools(dialog)).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(mtk_frame, text="手动选择", command=lambda: self._manual_mtk_config(dialog)).pack(side=tk.LEFT)
            
            # MTK工具列表
            mtk_list_frame = ttk.Frame(mtk_frame)
            mtk_list_frame.pack(fill=tk.X, pady=(10, 0))
            
            self.mtk_listbox = tk.Listbox(mtk_list_frame, height=4)
            mtk_scrollbar = ttk.Scrollbar(mtk_list_frame, orient=tk.VERTICAL, command=self.mtk_listbox.yview)
            self.mtk_listbox.configure(yscrollcommand=mtk_scrollbar.set)
            
            self.mtk_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            mtk_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Wireshark配置框架
            wireshark_frame = ttk.LabelFrame(main_frame, text="Wireshark配置", padding="10")
            wireshark_frame.pack(fill=tk.X, pady=(0, 15))
            
            # Wireshark路径输入
            ttk.Label(wireshark_frame, text="Wireshark路径:").pack(anchor=tk.W)
            wireshark_path_frame = ttk.Frame(wireshark_frame)
            wireshark_path_frame.pack(fill=tk.X, pady=(5, 0))
            
            self.wireshark_var = tk.StringVar()
            self.wireshark_entry = ttk.Entry(wireshark_path_frame, textvariable=self.wireshark_var, width=50)
            self.wireshark_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            ttk.Button(wireshark_path_frame, text="手动", command=lambda: self._browse_wireshark()).pack(side=tk.RIGHT, padx=(5, 0))
            ttk.Button(wireshark_path_frame, text="自动检测", command=lambda: self._detect_wireshark()).pack(side=tk.RIGHT, padx=(5, 0))
            
            # 高通工具配置框架
            qualcomm_frame = ttk.LabelFrame(main_frame, text="高通工具配置", padding="10")
            qualcomm_frame.pack(fill=tk.X, pady=(0, 15))
            
            # 检测高通工具按钮
            ttk.Button(qualcomm_frame, text="自动检测", command=lambda: self._detect_qualcomm_tools(dialog)).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(qualcomm_frame, text="手动选择", command=lambda: self._manual_qualcomm_config(dialog)).pack(side=tk.LEFT)
            
            # 高通工具列表
            qualcomm_list_frame = ttk.Frame(qualcomm_frame)
            qualcomm_list_frame.pack(fill=tk.X, pady=(10, 0))
            
            self.qualcomm_listbox = tk.Listbox(qualcomm_list_frame, height=3)
            qualcomm_scrollbar = ttk.Scrollbar(qualcomm_list_frame, orient=tk.VERTICAL, command=self.qualcomm_listbox.yview)
            self.qualcomm_listbox.configure(yscrollcommand=qualcomm_scrollbar.set)
            
            self.qualcomm_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            qualcomm_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 按钮框架
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(20, 0))
            
            ttk.Button(button_frame, text="确定", command=lambda: self._save_tool_config_and_close(dialog)).pack(side=tk.RIGHT, padx=(5, 0))
            ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT)
            
            # 初始化显示
            self._refresh_mtk_list()
            self._refresh_qualcomm_list()
            self.wireshark_var.set(self.tool_config.get("wireshark_path", ""))
            
            return dialog
            
        except Exception as e:
            messagebox.showerror("错误", f"创建配置对话框失败: {str(e)}")
            return None
    
    def _detect_mtk_tools(self, dialog):
        """检测MTK工具"""
        try:
            detected_tools = []
            
            # 常见安装路径
            common_paths = [
                "C:\\Tool\\ELT_*",
                "C:\\Program Files\\ELT_*",
                "C:\\MTK\\ELT_*",
                "D:\\Tool\\ELT_*",
                "D:\\Program Files\\ELT_*"
            ]
            
            for path_pattern in common_paths:
                # 查找匹配的目录
                import glob
                matches = glob.glob(path_pattern)
                for match in matches:
                    if self._validate_mtk_tool(match):
                        tool_info = self._get_mtk_tool_info(match)
                        if tool_info:
                            detected_tools.append(tool_info)
            
            if detected_tools:
                # 添加到配置中
                for tool in detected_tools:
                    # 检查是否已存在
                    exists = any(t["base_path"] == tool["base_path"] for t in self.tool_config["mtk_tools"])
                    if not exists:
                        self.tool_config["mtk_tools"].append(tool)
                
                self._refresh_mtk_list()
                messagebox.showinfo("检测完成", f"检测到 {len(detected_tools)} 个MTK工具")
            else:
                messagebox.showinfo("检测结果", "未检测到MTK工具，请尝试手动输入")
                
        except Exception as e:
            messagebox.showerror("错误", f"检测MTK工具失败: {str(e)}")
    
    def _validate_mtk_tool(self, base_path):
        """验证MTK工具路径"""
        try:
            # 检查必要目录和文件
            elgcap_path = os.path.join(base_path, "System", "External", "elgcap")
            utilities_path = os.path.join(base_path, "Utilities")
            
            if not os.path.exists(elgcap_path):
                return False
            
            if not os.path.exists(utilities_path):
                return False
            
            # 检查main.py
            main_py = os.path.join(elgcap_path, "main.py")
            if not os.path.exists(main_py):
                return False
            
            # 检查Python目录
            python_dirs = ["Python3", "Python", "Python27", "Python2"]
            python_found = False
            
            for python_dir in python_dirs:
                python_path = os.path.join(utilities_path, python_dir)
                embedded_python = os.path.join(python_path, "EmbeddedPython.exe")
                if os.path.exists(embedded_python):
                    python_found = True
                    break
            
            return python_found
            
        except Exception:
            return False
    
    def _get_mtk_tool_info(self, base_path):
        """获取MTK工具信息"""
        try:
            # 获取工具名称
            tool_name = os.path.basename(base_path)
            
            # 查找Python路径
            utilities_path = os.path.join(base_path, "Utilities")
            python_dirs = ["Python3", "Python", "Python27", "Python2"]
            python_path = ""
            python_version = "Unknown"
            
            for python_dir in python_dirs:
                test_python_path = os.path.join(utilities_path, python_dir)
                embedded_python = os.path.join(test_python_path, "EmbeddedPython.exe")
                if os.path.exists(embedded_python):
                    python_path = test_python_path
                    # 尝试检测Python版本
                    try:
                        result = subprocess.run([embedded_python, "--version"], 
                                             capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            python_version = result.stdout.strip()
                    except:
                        # 如果无法检测版本，根据目录名推断
                        if "Python3" in python_dir:
                            python_version = "3.x"
                        elif "Python27" in python_dir:
                            python_version = "2.7"
                        elif "Python2" in python_dir:
                            python_version = "2.x"
                    break
            
            if not python_path:
                return None
            
            return {
                "name": tool_name,
                "base_path": base_path,
                "python_path": python_path,
                "python_version": python_version,
                "elgcap_path": os.path.join(base_path, "System", "External", "elgcap")
            }
            
        except Exception as e:
            print(f"[DEBUG] 获取MTK工具信息失败: {str(e)}")
            return None
    
    def _manual_mtk_config(self, dialog):
        """手动配置MTK工具"""
        try:
            # 获取用户输入的路径
            base_path = filedialog.askdirectory(
                title="选择MTK工具根目录",
                parent=self.app.root
            )
            
            # 恢复主窗口焦点
            self.app.ui.restore_focus_after_dialog()
            
            if not base_path:
                return
            
            # 验证路径
            if not self._validate_mtk_tool(base_path):
                messagebox.showerror("错误", "选择的路径不是有效的MTK工具目录")
                return
            
            # 获取工具信息
            tool_info = self._get_mtk_tool_info(base_path)
            if not tool_info:
                messagebox.showerror("错误", "无法获取MTK工具信息")
                return
            
            # 添加到配置
            exists = any(t["base_path"] == tool_info["base_path"] for t in self.tool_config["mtk_tools"])
            if not exists:
                self.tool_config["mtk_tools"].append(tool_info)
                self._refresh_mtk_list()
                messagebox.showinfo("成功", f"已添加MTK工具: {tool_info['name']}")
            else:
                messagebox.showinfo("提示", "该MTK工具已存在")
                
        except Exception as e:
            messagebox.showerror("错误", f"手动配置失败: {str(e)}")
    
    def _detect_wireshark(self):
        """检测Wireshark"""
        try:
            # 常见Wireshark路径
            common_paths = [
                "C:\\Program Files\\Wireshark",
                "C:\\Program Files (x86)\\Wireshark",
                "D:\\Program Files\\Wireshark",
                "D:\\Program Files (x86)\\Wireshark"
            ]
            
            for path in common_paths:
                mergecap_exe = os.path.join(path, "mergecap.exe")
                if os.path.exists(mergecap_exe):
                    self.wireshark_var.set(path)
                    messagebox.showinfo("检测完成", f"检测到Wireshark: {path}")
                    return
            
            messagebox.showinfo("检测结果", "未检测到Wireshark，请手动选择")
            
        except Exception as e:
            messagebox.showerror("错误", f"检测Wireshark失败: {str(e)}")
    
    def _browse_wireshark(self):
        """浏览选择Wireshark路径"""
        try:
            path = filedialog.askdirectory(
                title="选择Wireshark安装目录"
            )
            
            # 恢复主窗口焦点
            self.app.ui.restore_focus_after_dialog()
            
            if path:
                # 验证mergecap.exe是否存在
                mergecap_exe = os.path.join(path, "mergecap.exe")
                if os.path.exists(mergecap_exe):
                    self.wireshark_var.set(path)
                else:
                    messagebox.showerror("错误", "选择的目录中没有找到mergecap.exe")
                    
        except Exception as e:
            messagebox.showerror("错误", f"选择Wireshark路径失败: {str(e)}")
    
    def _refresh_mtk_list(self):
        """刷新MTK工具列表"""
        try:
            self.mtk_listbox.delete(0, tk.END)
            for tool in self.tool_config["mtk_tools"]:
                display_text = f"{tool['name']} (Python {tool['python_version']}) - {tool['base_path']}"
                self.mtk_listbox.insert(tk.END, display_text)
        except Exception as e:
            print(f"[DEBUG] 刷新MTK工具列表失败: {str(e)}")
    
    def _detect_qualcomm_tools(self, dialog):
        """检测高通工具"""
        try:
            detected_tools = []
            
            # 常见安装路径
            common_paths = [
                "C:\\Program Files (x86)\\Qualcomm\\PCAP_Generator\\PCAP_Gen_2.0\\Release",
                "C:\\Program Files\\Qualcomm\\PCAP_Generator\\PCAP_Gen_2.0\\Release",
                "D:\\Program Files (x86)\\Qualcomm\\PCAP_Generator\\PCAP_Gen_2.0\\Release",
                "D:\\Program Files\\Qualcomm\\PCAP_Generator\\PCAP_Gen_2.0\\Release"
            ]
            
            print(f"[DEBUG] 开始检测高通工具，共 {len(common_paths)} 个路径")
            
            for i, path in enumerate(common_paths):
                print(f"[DEBUG] 检查路径 {i+1}: {path}")
                if self._validate_qualcomm_tool(path):
                    print(f"[DEBUG] 路径验证通过: {path}")
                    tool_info = self._get_qualcomm_tool_info(path)
                    if tool_info:
                        print(f"[DEBUG] 获取工具信息成功: {tool_info}")
                        detected_tools.append(tool_info)
                    else:
                        print(f"[DEBUG] 获取工具信息失败: {path}")
                else:
                    print(f"[DEBUG] 路径验证失败: {path}")
            
            if detected_tools:
                # 确保qualcomm_tools键存在
                if "qualcomm_tools" not in self.tool_config:
                    self.tool_config["qualcomm_tools"] = []
                
                # 添加到配置中
                for tool in detected_tools:
                    # 检查是否已存在
                    exists = any(t["base_path"] == tool["base_path"] for t in self.tool_config["qualcomm_tools"])
                    if not exists:
                        self.tool_config["qualcomm_tools"].append(tool)
                
                self._refresh_qualcomm_list()
                messagebox.showinfo("检测完成", f"检测到 {len(detected_tools)} 个高通工具")
            else:
                messagebox.showinfo("检测结果", "未检测到高通工具，请尝试手动输入。\n\n常见路径:\nC:\\Program Files (x86)\\Qualcomm\\PCAP_Generator\\PCAP_Gen_2.0\\Release\nC:\\Program Files\\Qualcomm\\PCAP_Generator\\PCAP_Gen_2.0\\Release\nD:\\Program Files (x86)\\Qualcomm\\PCAP_Generator\\PCAP_Gen_2.0\\Release\nD:\\Program Files\\Qualcomm\\PCAP_Generator\\PCAP_Gen_2.0\\Release")
                
        except Exception as e:
            messagebox.showerror("错误", f"检测高通工具失败: {str(e)}")
    
    def _validate_qualcomm_tool(self, base_path):
        """验证高通工具路径"""
        try:
            # 检查PCAP_Gen_2.0.exe是否存在
            pcap_gen_exe = os.path.join(base_path, "PCAP_Gen_2.0.exe")
            exists = os.path.exists(pcap_gen_exe)
            print(f"[DEBUG] 验证高通工具: {pcap_gen_exe} -> {exists}")
            return exists
        except Exception as e:
            print(f"[DEBUG] 验证高通工具异常: {str(e)}")
            return False
    
    def _get_qualcomm_tool_info(self, base_path):
        """获取高通工具信息"""
        try:
            # 获取工具名称
            tool_name = os.path.basename(os.path.dirname(base_path))  # PCAP_Gen_2.0
            parent_dir = os.path.basename(os.path.dirname(os.path.dirname(base_path)))  # PCAP_Generator
            
            return {
                "name": f"{parent_dir}_{tool_name}",
                "base_path": base_path,
                "pcap_gen_exe": os.path.join(base_path, "PCAP_Gen_2.0.exe")
            }
            
        except Exception as e:
            print(f"[DEBUG] 获取高通工具信息失败: {str(e)}")
            return None
    
    def _manual_qualcomm_config(self, dialog):
        """手动配置高通工具"""
        try:
            # 获取用户输入的路径
            base_path = filedialog.askdirectory(
                title="选择高通工具目录",
                parent=self.app.root
            )
            
            if not base_path:
                return
            
            # 验证路径
            if not self._validate_qualcomm_tool(base_path):
                messagebox.showerror("错误", "选择的路径不是有效的高通工具目录")
                return
            
            # 获取工具信息
            tool_info = self._get_qualcomm_tool_info(base_path)
            if not tool_info:
                messagebox.showerror("错误", "无法获取高通工具信息")
                return
            
            # 确保qualcomm_tools键存在
            if "qualcomm_tools" not in self.tool_config:
                self.tool_config["qualcomm_tools"] = []
            
            # 添加到配置
            exists = any(t["base_path"] == tool_info["base_path"] for t in self.tool_config["qualcomm_tools"])
            if not exists:
                self.tool_config["qualcomm_tools"].append(tool_info)
                self._refresh_qualcomm_list()
                messagebox.showinfo("成功", f"已添加高通工具: {tool_info['name']}")
            else:
                messagebox.showinfo("提示", "该高通工具已存在")
                
        except Exception as e:
            messagebox.showerror("错误", f"手动配置失败: {str(e)}")
    
    def _refresh_qualcomm_list(self):
        """刷新高通工具列表"""
        try:
            self.qualcomm_listbox.delete(0, tk.END)
            # 确保qualcomm_tools键存在
            if "qualcomm_tools" not in self.tool_config:
                self.tool_config["qualcomm_tools"] = []
            
            for tool in self.tool_config["qualcomm_tools"]:
                display_text = f"{tool['name']} - {tool['base_path']}"
                self.qualcomm_listbox.insert(tk.END, display_text)
        except Exception as e:
            print(f"[DEBUG] 刷新高通工具列表失败: {str(e)}")
    
    def _save_tool_config_and_close(self, dialog):
        """保存配置并关闭对话框"""
        try:
            # 保存Wireshark路径
            wireshark_path = self.wireshark_var.get().strip()
            if wireshark_path:
                mergecap_exe = os.path.join(wireshark_path, "mergecap.exe")
                if not os.path.exists(mergecap_exe):
                    messagebox.showerror("错误", "Wireshark路径无效，找不到mergecap.exe")
                    return
                self.tool_config["wireshark_path"] = wireshark_path
            
            # 保存配置
            if self._save_tool_config():
                messagebox.showinfo("成功", "工具配置已保存")
                # 重新加载配置到内存
                self.tool_config = self._load_tool_config()
                print(f"[DEBUG] 配置保存后重新加载: {self.tool_config}")
                dialog.destroy()
            else:
                messagebox.showerror("错误", "保存配置失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {str(e)}")
        
    def set_screen_timeout(self):
        """设置灭屏时间"""
        try:
            selected_device = self.app.selected_device.get()
            if not selected_device:
                messagebox.showerror("错误", "请先选择设备")
                return False
            
            # 检查设备连接
            if not self.device_manager.check_device_connection(selected_device):
                return False
            
            # 获取用户输入的灭屏时间（秒）
            timeout_seconds = simpledialog.askinteger(
                "设置灭屏时间",
                "请输入灭屏时间（秒）:\n"
                "0 = 永不灭屏",
                parent=self.app.root,
                minvalue=0,
                maxvalue=86400  # 最大24小时
            )
            
            if timeout_seconds is None:
                messagebox.showinfo("取消", "用户取消设置")
                return False
            
            # 转换为毫秒，如果输入0则设置为永不灭屏的值
            if timeout_seconds == 0:
                timeout_ms = 2147483647  # 32位有符号整数最大值，表示永不灭屏
            else:
                timeout_ms = timeout_seconds * 1000
            
            try:
                # 设置屏幕超时时间
                cmd = f"adb -s {selected_device} shell settings put system screen_off_timeout {timeout_ms}"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    if timeout_seconds == 0:
                        messagebox.showinfo("成功", "屏幕超时已设置为永不灭屏")
                    else:
                        # 转换为更友好的显示格式
                        if timeout_seconds < 60:
                            display_text = f"{timeout_seconds} 秒"
                        elif timeout_seconds < 3600:
                            minutes = timeout_seconds // 60
                            seconds = timeout_seconds % 60
                            if seconds > 0:
                                display_text = f"{minutes} 分钟 {seconds} 秒"
                            else:
                                display_text = f"{minutes} 分钟"
                        else:
                            hours = timeout_seconds // 3600
                            minutes = (timeout_seconds % 3600) // 60
                            if minutes > 0:
                                display_text = f"{hours} 小时 {minutes} 分钟"
                            else:
                                display_text = f"{hours} 小时"
                        
                        messagebox.showinfo("成功", f"屏幕超时已设置为 {display_text}")
                    return True
                else:
                    messagebox.showerror("错误", f"设置屏幕超时失败: {result.stderr}")
                    return False
                    
            except subprocess.TimeoutExpired:
                messagebox.showerror("错误", "设置屏幕超时超时")
                return False
            except Exception as e:
                messagebox.showerror("错误", f"设置屏幕超时异常: {str(e)}")
                return False
            
        except Exception as e:
            messagebox.showerror("错误", f"设置灭屏时间失败: {str(e)}")
            return False
    
    def merge_mtklog(self):
        """合并MTKlog文件"""
        try:
            # 检查工具配置
            if not self._check_tool_config():
                return False
            
            # 选择MTKlog文件夹
            log_folder = filedialog.askdirectory(
                title="选择MTKlog文件夹",
                parent=self.app.root
            )
            
            if not log_folder:
                return False
            
            # 检查文件夹中是否有muxz文件
            muxz_files = self._find_muxz_files(log_folder)
            if not muxz_files:
                messagebox.showerror("错误", "选择的文件夹中没有找到muxz文件")
                return False
            
            # 选择MTK工具
            mtk_tool = self._select_mtk_tool()
            if not mtk_tool:
                return False
            
            # 定义后台工作函数
            def mtklog_merge_worker(progress_var, status_label, progress_dialog, stop_flag):
                return self._execute_mtklog_merge_worker(log_folder, muxz_files, mtk_tool, progress_var, status_label, progress_dialog)
            
            # 定义完成回调
            def on_merge_done(result):
                if result and result.get('success', False):
                    merge_file = result.get('merge_file', '')
                    file_count = result.get('file_count', 0)
                    # 显示成功消息到日志区域
                    self._log_message(f"MTKlog合并完成！合并文件: {merge_file}，处理文件: {file_count} 个muxz文件，文件夹已自动打开。", "success")
                else:
                    error_msg = result.get('error', '未知错误') if result else '合并失败'
                    self._log_message(f"MTKlog合并失败: {error_msg}", "error")
            
            # 定义错误回调
            def on_merge_error(error):
                self._log_message(f"执行MTKlog合并时发生错误: {str(error)}", "error")
            
            # 使用模态执行器
            self.app.ui.run_with_modal(
                title="合并MTKlog",
                worker_fn=mtklog_merge_worker,
                on_done=on_merge_done,
                on_error=on_merge_error
            )
            
            return True
            
        except Exception as e:
            messagebox.showerror("错误", f"合并MTKlog失败: {str(e)}")
            return False
    
    def extract_pcap_from_mtklog(self):
        """从MTKlog中提取pcap文件"""
        try:
            # 检查工具配置
            if not self._check_tool_config():
                return False
            
            # 选择MTKlog文件夹
            log_folder = filedialog.askdirectory(
                title="选择MTKlog文件夹",
                parent=self.app.root
            )
            
            if not log_folder:
                return False
            
            # 检查文件夹中是否有muxz文件
            muxz_files = self._find_muxz_files(log_folder)
            if not muxz_files:
                messagebox.showerror("错误", "选择的文件夹中没有找到muxz文件")
                return False
            
            # 选择MTK工具
            mtk_tool = self._select_mtk_tool()
            if not mtk_tool:
                return False
            
            # 定义后台工作函数
            def mtklog_extraction_worker(progress_var, status_label, progress_dialog, stop_flag):
                return self._execute_pcap_extraction_worker(log_folder, muxz_files, mtk_tool, progress_var, status_label, progress_dialog)
            
            # 定义完成回调
            def on_extraction_done(result):
                if result and result.get('success', False):
                    merge_file = result.get('merge_file', '')
                    success_count = result.get('success_count', 0)
                    total_files = result.get('total_files', 0)
                    # 显示成功消息到日志区域
                    self._log_message(f"MTK pcap提取完成！成功提取: {success_count}/{total_files} 个文件，合并文件: {merge_file}，文件已自动打开。", "success")
                else:
                    error_msg = result.get('error', '未知错误') if result else '提取失败'
                    self._log_message(f"MTK pcap提取失败: {error_msg}", "error")
            
            # 定义错误回调
            def on_extraction_error(error):
                self._log_message(f"执行MTK pcap提取时发生错误: {str(error)}", "error")
            
            # 使用模态执行器
            self.app.ui.run_with_modal(
                title="提取MTK pcap",
                worker_fn=mtklog_extraction_worker,
                on_done=on_extraction_done,
                on_error=on_extraction_error
            )
            
            return True
            
        except Exception as e:
            messagebox.showerror("错误", f"提取pcap失败: {str(e)}")
            return False
    
    def _check_tool_config(self, check_mtk=True, check_qualcomm=False, check_wireshark=True):
        """检查工具配置"""
        print(f"[DEBUG] 检查工具配置: MTK={check_mtk}, 高通={check_qualcomm}, Wireshark={check_wireshark}")
        
        if check_mtk and not self.tool_config.get("mtk_tools"):
            print("[DEBUG] MTK工具未配置")
            if messagebox.askyesno("配置缺失", "未配置MTK工具，是否现在配置？"):
                self.configure_tools()
                return bool(self.tool_config.get("mtk_tools"))
            return False
        
        if check_qualcomm and not self.tool_config.get("qualcomm_tools"):
            print("[DEBUG] 高通工具未配置")
            if messagebox.askyesno("配置缺失", "未配置高通工具，是否现在配置？"):
                self.configure_tools()
                # 重新加载配置
                self.tool_config = self._load_tool_config()
                print(f"[DEBUG] 配置完成后重新检查: {bool(self.tool_config.get('qualcomm_tools'))}")
                return bool(self.tool_config.get("qualcomm_tools"))
            return False
        
        if check_wireshark and not self.tool_config.get("wireshark_path"):
            print("[DEBUG] Wireshark未配置")
            if messagebox.askyesno("配置缺失", "未配置Wireshark路径，是否现在配置？"):
                self.configure_tools()
                return bool(self.tool_config.get("wireshark_path"))
            return False
        
        print("[DEBUG] 所有工具配置检查通过")
        return True
    
    def _select_mtk_tool(self):
        """选择MTK工具"""
        try:
            if len(self.tool_config["mtk_tools"]) == 1:
                return self.tool_config["mtk_tools"][0]
            
            # 创建选择对话框
            dialog = tk.Toplevel(self.app.root)
            dialog.title("选择MTK工具")
            dialog.geometry("500x300")
            dialog.resizable(False, False)
            dialog.transient(self.app.root)
            # dialog.grab_set()  # 注释掉以允许在程序和桌面之间自由切换
            
            # 居中显示
            dialog.geometry("+%d+%d" % (
                self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 500) // 2,
                self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 300) // 2
            ))
            
            # 主框架
            main_frame = ttk.Frame(dialog, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 标题
            title_label = ttk.Label(main_frame, text="选择MTK工具", font=('Arial', 12, 'bold'))
            title_label.pack(pady=(0, 15))
            
            # 工具列表
            listbox = tk.Listbox(main_frame, height=8)
            scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=listbox.yview)
            listbox.configure(yscrollcommand=scrollbar.set)
            
            for tool in self.tool_config["mtk_tools"]:
                display_text = f"{tool['name']} (Python {tool['python_version']})"
                listbox.insert(tk.END, display_text)
            
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 按钮框架
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(15, 0))
            
            result = [None]
            
            def on_confirm():
                selection = listbox.curselection()
                if selection:
                    result[0] = self.tool_config["mtk_tools"][selection[0]]
                    dialog.destroy()
                else:
                    messagebox.showwarning("选择错误", "请选择一个MTK工具")
            
            ttk.Button(button_frame, text="确定", command=on_confirm).pack(side=tk.RIGHT, padx=(5, 0))
            ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT)
            
            # 等待对话框关闭
            dialog.wait_window()
            
            return result[0]
            
        except Exception as e:
            print(f"[DEBUG] 选择MTK工具失败: {str(e)}")
            return None
    
    def _select_qualcomm_tool(self):
        """选择高通工具"""
        try:
            # 确保qualcomm_tools键存在
            if "qualcomm_tools" not in self.tool_config:
                self.tool_config["qualcomm_tools"] = []
            
            if len(self.tool_config["qualcomm_tools"]) == 1:
                return self.tool_config["qualcomm_tools"][0]
            
            # 创建选择对话框
            dialog = tk.Toplevel(self.app.root)
            dialog.title("选择高通工具")
            dialog.geometry("500x300")
            dialog.resizable(False, False)
            dialog.transient(self.app.root)
            # dialog.grab_set()  # 注释掉以允许在程序和桌面之间自由切换
            
            # 居中显示
            dialog.geometry("+%d+%d" % (
                self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 500) // 2,
                self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 300) // 2
            ))
            
            # 主框架
            main_frame = ttk.Frame(dialog, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 标题
            title_label = ttk.Label(main_frame, text="选择高通工具", font=('Arial', 12, 'bold'))
            title_label.pack(pady=(0, 15))
            
            # 工具列表
            listbox = tk.Listbox(main_frame, height=8)
            scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=listbox.yview)
            listbox.configure(yscrollcommand=scrollbar.set)
            
            # 确保qualcomm_tools键存在
            if "qualcomm_tools" not in self.tool_config:
                self.tool_config["qualcomm_tools"] = []
            
            for tool in self.tool_config["qualcomm_tools"]:
                display_text = f"{tool['name']}"
                listbox.insert(tk.END, display_text)
            
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 按钮框架
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(15, 0))
            
            result = [None]
            
            def on_confirm():
                selection = listbox.curselection()
                if selection:
                    result[0] = self.tool_config["qualcomm_tools"][selection[0]]
                    dialog.destroy()
                else:
                    messagebox.showwarning("选择错误", "请选择一个高通工具")
            
            ttk.Button(button_frame, text="确定", command=on_confirm).pack(side=tk.RIGHT, padx=(5, 0))
            ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT)
            
            # 等待对话框关闭
            dialog.wait_window()
            
            return result[0]
            
        except Exception as e:
            print(f"[DEBUG] 选择高通工具失败: {str(e)}")
            return None
    
    def _find_muxz_files(self, log_folder):
        """查找muxz文件"""
        try:
            muxz_files = []
            for file in os.listdir(log_folder):
                if file.endswith('.muxz'):
                    muxz_files.append(file)
            return muxz_files
        except Exception as e:
            print(f"[DEBUG] 查找muxz文件失败: {str(e)}")
            return []
    
    def _find_hdf_files(self, log_folder):
        """查找hdf文件"""
        try:
            hdf_files = []
            for file in os.listdir(log_folder):
                if file.endswith('.hdf'):
                    hdf_files.append(file)
            return hdf_files
        except Exception as e:
            print(f"[DEBUG] 查找hdf文件失败: {str(e)}")
            return []
    
    
    
    def _execute_qualcomm_pcap_extraction_worker(self, log_folder, hdf_files, qualcomm_tool, progress_var, status_label, progress_dialog):
        """执行高通pcap提取的后台工作函数"""
        try:
            # 获取PCAP_Gen_2.0.exe路径
            pcap_gen_exe = qualcomm_tool["pcap_gen_exe"]
            
            if not os.path.exists(pcap_gen_exe):
                return {
                    'success': False,
                    'error': f"找不到PCAP_Gen_2.0.exe: {pcap_gen_exe}"
                }
            
            # 更新进度
            status_label.config(text="准备提取环境...")
            progress_var.set(0)
            progress_dialog.update()
            
            # 对每个hdf文件执行提取
            total_files = len(hdf_files)
            success_count = 0
            
            for i, hdf_file in enumerate(hdf_files):
                progress_text = f"正在提取: {hdf_file} ({i+1}/{total_files})"
                progress_value = (i / total_files) * 80
                
                status_label.config(text=progress_text)
                progress_var.set(progress_value)
                progress_dialog.update()
                
                # 执行提取命令
                hdf_path = os.path.join(log_folder, hdf_file)
                cmd = [pcap_gen_exe, hdf_path, log_folder]
                
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                    if result.returncode == 0:
                        success_count += 1
                        print(f"[INFO] 成功提取: {hdf_file}")
                    else:
                        print(f"[WARNING] 提取失败: {hdf_file} - {result.stderr}")
                except subprocess.TimeoutExpired:
                    print(f"[WARNING] 提取超时: {hdf_file}")
                except Exception as e:
                    print(f"[WARNING] 提取异常: {hdf_file} - {str(e)}")
            
            # 合并pcap文件
            status_label.config(text="合并pcap文件...")
            progress_var.set(80)
            progress_dialog.update()
            
            # 使用通用的合并函数
            merge_success = self._execute_pcap_merge(log_folder)
            
            if merge_success:
                merge_file = os.path.join(log_folder, 'merge.pcap')
                status_label.config(text="提取完成!")
                progress_var.set(100)
                progress_dialog.update()
                
                return {
                    'success': True,
                    'merge_file': merge_file,
                    'success_count': success_count,
                    'total_files': total_files
                }
            else:
                return {
                    'success': False,
                    'error': 'pcap文件合并失败'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"执行高通pcap提取失败: {str(e)}"
            }
    
    def _execute_mtklog_merge_worker(self, log_folder, muxz_files, mtk_tool, progress_var, status_label, progress_dialog):
        """执行MTKlog合并的后台工作函数"""
        try:
            # 获取MDLogMan.exe路径
            utilities_path = os.path.join(mtk_tool["base_path"], "Utilities")
            mdlogman_exe = os.path.join(utilities_path, "MDLogMan.exe")
            
            if not os.path.exists(mdlogman_exe):
                return {
                    'success': False,
                    'error': f"找不到MDLogMan.exe: {mdlogman_exe}"
                }
            
            # 更新进度
            status_label.config(text="准备合并环境...")
            progress_var.set(10)
            progress_dialog.update()
            
            # 创建输出文件路径
            merge_elg_path = os.path.join(log_folder, "merge.elg")
            
            # 更新进度
            status_label.config(text=f"正在合并 {len(muxz_files)} 个muxz文件...")
            progress_var.set(50)
            progress_dialog.update()
            
            # 执行合并命令
            # MDLogMan -i *.muxz -o merge.elg
            cmd = [
                mdlogman_exe,
                "-i", "*.muxz",
                "-o", "merge.elg"
            ]
            
            try:
                result = subprocess.run(cmd, cwd=log_folder, capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    # 合并成功
                    status_label.config(text="合并完成!")
                    progress_var.set(100)
                    progress_dialog.update()
                    
                    # 检查输出文件是否存在
                    if os.path.exists(merge_elg_path):
                        # 打开合并后的elg文件所在文件夹
                        os.startfile(log_folder)
                        
                        return {
                            'success': True,
                            'merge_file': merge_elg_path,
                            'file_count': len(muxz_files)
                        }
                    else:
                        return {
                            'success': False,
                            'error': '合并完成但未找到输出文件'
                        }
                else:
                    return {
                        'success': False,
                        'error': f"MDLogMan执行失败: {result.stderr}"
                    }
                    
            except subprocess.TimeoutExpired:
                return {
                    'success': False,
                    'error': 'MDLogMan执行超时'
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': f"MDLogMan执行异常: {str(e)}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"执行MTKlog合并失败: {str(e)}"
            }
    
    
    def _execute_pcap_extraction_worker(self, log_folder, muxz_files, mtk_tool, progress_var, status_label, progress_dialog):
        """执行pcap提取的后台工作函数"""
        try:
            # 切换到elgcap目录
            elgcap_path = mtk_tool["elgcap_path"]
            python_path = mtk_tool["python_path"]
            embedded_python = os.path.join(python_path, "EmbeddedPython.exe")
            
            # 更新进度
            status_label.config(text="准备提取环境...")
            progress_var.set(0)
            progress_dialog.update()
            
            # 对每个muxz文件执行提取
            total_files = len(muxz_files)
            success_count = 0
            
            for i, muxz_file in enumerate(muxz_files):
                progress_text = f"正在提取: {muxz_file} ({i+1}/{total_files})"
                progress_value = (i / total_files) * 80
                
                status_label.config(text=progress_text)
                progress_var.set(progress_value)
                progress_dialog.update()
                
                # 执行提取命令
                muxz_path = os.path.join(log_folder, muxz_file)
                cmd = [
                    embedded_python,
                    "main.py",
                    "-sap", "sap_6291",
                    "-pcapng",
                    "-all_payload",
                    muxz_path
                ]
                
                try:
                    result = subprocess.run(cmd, cwd=elgcap_path, capture_output=True, text=True, timeout=300)
                    if result.returncode == 0:
                        success_count += 1
                        print(f"[INFO] 成功提取: {muxz_file}")
                    else:
                        print(f"[WARNING] 提取失败: {muxz_file} - {result.stderr}")
                except subprocess.TimeoutExpired:
                    print(f"[WARNING] 提取超时: {muxz_file}")
                except Exception as e:
                    print(f"[WARNING] 提取异常: {muxz_file} - {str(e)}")
            
            # 合并pcap文件
            status_label.config(text="合并pcap文件...")
            progress_var.set(80)
            progress_dialog.update()
            
            # 使用通用的合并函数
            merge_success = self._execute_pcap_merge(log_folder)
            
            if merge_success:
                merge_file = os.path.join(log_folder, 'merge.pcap')
                status_label.config(text="提取完成!")
                progress_var.set(100)
                progress_dialog.update()
                
                return {
                    'success': True,
                    'merge_file': merge_file,
                    'success_count': success_count,
                    'total_files': total_files
                }
            else:
                return {
                    'success': False,
                    'error': 'pcap文件合并失败'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"执行pcap提取失败: {str(e)}"
            }
    
    
    
    def merge_pcap(self):
        """合并PCAP文件"""
        try:
            # 检查Wireshark配置
            if not self.tool_config.get("wireshark_path"):
                if messagebox.askyesno("配置缺失", "未配置Wireshark路径，是否现在配置？"):
                    self.configure_tools()
                    if not self.tool_config.get("wireshark_path"):
                        return False
                else:
                    return False
            
            # 循环合并功能
            while True:
                # 获取用户输入的文件夹路径
                folder_path = self._get_folder_path_for_merge()
                if not folder_path:
                    break  # 用户取消
                
                # 执行合并
                success = self._execute_pcap_merge(folder_path)
                
                if success:
                    # 合并成功，直接结束
                    break
                else:
                    # 询问是否重试
                    if not messagebox.askyesno("合并失败", "PCAP合并失败！\n\n是否重试？"):
                        break
            
            return True
            
        except Exception as e:
            messagebox.showerror("错误", f"合并PCAP失败: {str(e)}")
            return False
    
    def _execute_pcap_merge(self, folder_path):
        """执行PCAP合并的通用函数"""
        try:
            # 检查文件夹是否存在
            if not os.path.exists(folder_path):
                messagebox.showerror("错误", f"文件夹不存在: {folder_path}")
                return False
            
            # 查找所有pcap文件
            pcap_files = self._find_pcap_files(folder_path)
            if not pcap_files:
                messagebox.showerror("错误", f"文件夹中没有找到pcap文件: {folder_path}")
                return False
            
            # 检查Wireshark路径
            wireshark_path = self.tool_config["wireshark_path"]
            mergecap_exe = os.path.join(wireshark_path, "mergecap.exe")
            
            if not os.path.exists(mergecap_exe):
                messagebox.showerror("错误", f"找不到mergecap.exe: {mergecap_exe}")
                return False
            
            # 创建输出文件路径
            merge_pcap_path = os.path.join(folder_path, "merge.pcap")
            
            # 显示进度对话框
            progress_dialog = self._show_merge_progress_dialog()
            
            try:
                # 更新进度
                self._update_merge_progress(progress_dialog, f"正在合并 {len(pcap_files)} 个文件...", 50)
                
                # 执行合并命令
                merge_cmd = [mergecap_exe, "-w", merge_pcap_path] + pcap_files
                
                result = subprocess.run(merge_cmd, capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0:
                    # 合并成功
                    self._update_merge_progress(progress_dialog, "合并完成!", 100)
                    progress_dialog.destroy()
                    
                    # 打开合并后的pcap文件
                    os.startfile(merge_pcap_path)
                    
                    print(f"[INFO] 成功合并PCAP文件: {merge_pcap_path}")
                    return True
                else:
                    raise Exception(f"mergecap执行失败: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                progress_dialog.destroy()
                messagebox.showerror("错误", "合并超时，请检查文件大小")
                return False
            except Exception as e:
                progress_dialog.destroy()
                messagebox.showerror("错误", f"合并失败: {str(e)}")
                return False
                
        except Exception as e:
            messagebox.showerror("错误", f"执行PCAP合并失败: {str(e)}")
            return False
    
    def _find_pcap_files(self, folder_path):
        """查找文件夹中的所有pcap文件"""
        try:
            pcap_files = []
            
            # 查找所有pcap相关文件
            for file in os.listdir(folder_path):
                if any(file.lower().endswith(ext) for ext in ['.pcap', '.pcapng', '.cap']):
                    pcap_files.append(os.path.join(folder_path, file))
            
            return pcap_files
            
        except Exception as e:
            print(f"[DEBUG] 查找pcap文件失败: {str(e)}")
            return []
    
    def _get_folder_path_for_merge(self):
        """获取用户输入的文件夹路径"""
        try:
            # 创建输入对话框
            dialog = tk.Toplevel(self.app.root)
            dialog.title("选择PCAP文件夹")
            dialog.geometry("500x200")
            dialog.resizable(False, False)
            dialog.transient(self.app.root)
            # dialog.grab_set()  # 注释掉以允许在程序和桌面之间自由切换
            
            # 居中显示
            dialog.geometry("+%d+%d" % (
                self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 500) // 2,
                self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 200) // 2
            ))
            
            # 主框架
            main_frame = ttk.Frame(dialog, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 标题
            title_label = ttk.Label(main_frame, text="选择包含PCAP文件的文件夹", font=('Arial', 12, 'bold'))
            title_label.pack(pady=(0, 15))
            
            # 路径输入框架
            path_frame = ttk.Frame(main_frame)
            path_frame.pack(fill=tk.X, pady=(0, 15))
            
            # 路径输入框
            path_var = tk.StringVar()
            path_entry = ttk.Entry(path_frame, textvariable=path_var, width=50)
            path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # 浏览按钮
            def browse_folder():
                folder = filedialog.askdirectory(
                    title="选择PCAP文件夹",
                    parent=self.app.root
                )
                if folder:
                    path_var.set(folder)
            
            ttk.Button(path_frame, text="浏览", command=browse_folder).pack(side=tk.RIGHT, padx=(5, 0))
            
            # 按钮框架
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(15, 0))
            
            result = [None]
            
            def on_confirm():
                folder_path = path_var.get().strip()
                if folder_path:
                    if os.path.exists(folder_path):
                        result[0] = folder_path
                        dialog.destroy()
                    else:
                        messagebox.showerror("错误", "文件夹不存在，请重新选择")
                else:
                    messagebox.showwarning("输入错误", "请输入文件夹路径")
            
            def on_cancel():
                dialog.destroy()
            
            ttk.Button(button_frame, text="确定", command=on_confirm).pack(side=tk.RIGHT, padx=(5, 0))
            ttk.Button(button_frame, text="取消", command=on_cancel).pack(side=tk.RIGHT)
            
            # 绑定回车键
            path_entry.bind('<Return>', lambda e: on_confirm())
            path_entry.focus()
            
            # 等待对话框关闭
            dialog.wait_window()
            
            return result[0]
            
        except Exception as e:
            print(f"[DEBUG] 获取文件夹路径失败: {str(e)}")
            return None
    
    def _show_merge_progress_dialog(self, title="正在合并文件"):
        """显示合并进度对话框"""
        try:
            progress_dialog = tk.Toplevel(self.app.root)
            progress_dialog.title(title)
            progress_dialog.geometry("400x150")
            progress_dialog.resizable(False, False)
            progress_dialog.transient(self.app.root)
            # progress_dialog.grab_set()  # 注释掉以允许在程序和桌面之间自由切换
            
            # 居中显示
            progress_dialog.geometry("+%d+%d" % (
                self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 400) // 2,
                self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 150) // 2
            ))
            
            # 主框架
            main_frame = ttk.Frame(progress_dialog, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 标题
            title_label = ttk.Label(main_frame, text=f"{title}...", font=('Arial', 12, 'bold'))
            title_label.pack(pady=(0, 15))
            
            # 进度条
            progress_var = tk.DoubleVar()
            progress_bar = ttk.Progressbar(main_frame, variable=progress_var, maximum=100, length=300)
            progress_bar.pack(pady=(0, 15))
            
            # 状态标签
            status_label = ttk.Label(main_frame, text="准备中...", font=('Arial', 10))
            status_label.pack()
            
            # 存储引用
            progress_dialog.progress_var = progress_var
            progress_dialog.status_label = status_label
            
            progress_dialog.update()
            return progress_dialog
            
        except Exception as e:
            print(f"[DEBUG] 创建合并进度对话框失败: {str(e)}")
            return None
    
    def _update_merge_progress(self, progress_dialog, status_text, progress_value):
        """更新合并进度"""
        try:
            if progress_dialog and progress_dialog.winfo_exists():
                if hasattr(progress_dialog, 'status_label'):
                    progress_dialog.status_label.config(text=status_text)
                if hasattr(progress_dialog, 'progress_var'):
                    progress_dialog.progress_var.set(progress_value)
                progress_dialog.update()
        except Exception as e:
            print(f"[DEBUG] 更新合并进度失败: {str(e)}")
    
    def extract_pcap_from_qualcomm_log(self):
        """从高通log提取pcap文件"""
        try:
            print("[DEBUG] 开始高通pcap提取流程")
            # 检查工具配置
            if not self._check_tool_config(check_mtk=False, check_qualcomm=True, check_wireshark=True):
                print("[DEBUG] 工具配置检查失败，退出")
                return False
            
            print("[DEBUG] 工具配置检查通过，准备选择文件夹")
            
            # 选择高通log文件夹
            log_folder = filedialog.askdirectory(
                title="选择高通log文件夹",
                parent=self.app.root
            )
            
            if not log_folder:
                return False
            
            # 检查文件夹中是否有hdf文件
            hdf_files = self._find_hdf_files(log_folder)
            if not hdf_files:
                messagebox.showerror("错误", "选择的文件夹中没有找到hdf文件")
                return False
            
            # 选择高通工具
            qualcomm_tool = self._select_qualcomm_tool()
            if not qualcomm_tool:
                return False
            
            # 定义后台工作函数
            def qualcomm_extraction_worker(progress_var, status_label, progress_dialog, stop_flag):
                return self._execute_qualcomm_pcap_extraction_worker(log_folder, hdf_files, qualcomm_tool, progress_var, status_label, progress_dialog)
            
            # 定义完成回调
            def on_extraction_done(result):
                if result and result.get('success', False):
                    merge_file = result.get('merge_file', '')
                    success_count = result.get('success_count', 0)
                    total_files = result.get('total_files', 0)
                    # 显示成功消息到日志区域
                    self._log_message(f"高通pcap提取完成！成功提取: {success_count}/{total_files} 个文件，合并文件: {merge_file}，文件已自动打开。", "success")
                else:
                    error_msg = result.get('error', '未知错误') if result else '提取失败'
                    self._log_message(f"高通pcap提取失败: {error_msg}", "error")
            
            # 定义错误回调
            def on_extraction_error(error):
                self._log_message(f"执行高通pcap提取时发生错误: {str(error)}", "error")
            
            # 使用模态执行器
            self.app.ui.run_with_modal(
                title="提取高通pcap",
                worker_fn=qualcomm_extraction_worker,
                on_done=on_extraction_done,
                on_error=on_extraction_error
            )
            
            return True
            
        except Exception as e:
            messagebox.showerror("错误", f"提取高通pcap失败: {str(e)}")
            return False
    
    def _execute_delete_bugreport_worker(self, device, progress_var, status_label, progress_dialog):
        """执行删除bugreport文件的后台工作函数"""
        try:
            bugreport_path = "/data/user_de/0/com.android.shell/files/bugreports"
            
            # 更新进度
            status_label.config(text="检查目标路径...")
            progress_var.set(10)
            progress_dialog.update()
            
            # 首先检查路径是否存在
            check_cmd = f"adb -s {device} shell ls {bugreport_path}"
            check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            if check_result.returncode != 0:
                # 路径不存在或为空
                if "No such file or directory" in check_result.stderr:
                    status_label.config(text="目标路径不存在或为空")
                    progress_var.set(100)
                    progress_dialog.update()
                    return {
                        'success': True,
                        'deleted_count': 0,
                        'message': '目标路径不存在或为空'
                    }
                else:
                    return {
                        'success': False,
                        'error': f"检查路径失败: {check_result.stderr}"
                    }
            
            # 更新进度
            status_label.config(text="正在删除文件...")
            progress_var.set(50)
            progress_dialog.update()
            
            # 删除目录中的所有内容
            delete_cmd = f"adb -s {device} shell rm -rf {bugreport_path}/*"
            delete_result = subprocess.run(delete_cmd, shell=True, capture_output=True, text=True, timeout=60)
            
            if delete_result.returncode == 0:
                # 删除成功，再次检查确认
                status_label.config(text="验证删除结果...")
                progress_var.set(80)
                progress_dialog.update()
                
                verify_cmd = f"adb -s {device} shell ls {bugreport_path}"
                verify_result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True, timeout=30)
                
                if verify_result.returncode != 0 or not verify_result.stdout.strip():
                    # 目录为空，删除成功
                    status_label.config(text="删除完成!")
                    progress_var.set(100)
                    progress_dialog.update()
                    
                    # 统计删除的文件数量（通过原始输出估算）
                    original_files = check_result.stdout.strip().split('\n')
                    deleted_count = len([f for f in original_files if f.strip()])
                    
                    return {
                        'success': True,
                        'deleted_count': deleted_count,
                        'message': '所有文件已成功删除'
                    }
                else:
                    # 还有文件残留
                    remaining_files = verify_result.stdout.strip().split('\n')
                    remaining_count = len([f for f in remaining_files if f.strip()])
                    
                    return {
                        'success': False,
                        'error': f"删除不完整，还有 {remaining_count} 个文件残留"
                    }
            else:
                return {
                    'success': False,
                    'error': f"删除命令执行失败: {delete_result.stderr}"
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': '删除操作超时'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"执行删除bugreport失败: {str(e)}"
            }
    
    def delete_bugreport(self):
        """删除手机中的bugreport文件"""
        try:
            # 获取选中的设备
            device = self.app.device_manager.validate_device_selection()
            if not device:
                return False
            
            # 确认删除操作
            if not messagebox.askyesno("确认删除", 
                "即将删除手机中的bugreport文件！\n\n"
                "目标路径: /data/user_de/0/com.android.shell/files/bugreports\n\n"
                "此操作不可撤销，是否继续？"):
                return False
            
            # 定义后台工作函数
            def delete_bugreport_worker(progress_var, status_label, progress_dialog, stop_flag):
                return self._execute_delete_bugreport_worker(device, progress_var, status_label, progress_dialog)
            
            # 定义完成回调
            def on_delete_done(result):
                if result and result.get('success', False):
                    deleted_count = result.get('deleted_count', 0)
                    # 显示成功消息到日志区域
                    self._log_message(f"bugreport文件删除完成！已删除: {deleted_count} 个文件/文件夹，目标路径: /data/user_de/0/com.android.shell/files/bugreports", "success")
                else:
                    error_msg = result.get('error', '未知错误') if result else '删除失败'
                    self._log_message(f"删除bugreport文件失败: {error_msg}", "error")
            
            # 定义错误回调
            def on_delete_error(error):
                self._log_message(f"执行删除bugreport时发生错误: {str(error)}", "error")
            
            # 使用模态执行器
            self.app.ui.run_with_modal(
                title="删除bugreport",
                worker_fn=delete_bugreport_worker,
                on_done=on_delete_done,
                on_error=on_delete_error
            )
            
            return True
            
        except Exception as e:
            messagebox.showerror("错误", f"删除bugreport失败: {str(e)}")
            return False
    
    def show_input_text_dialog(self):
        """显示输入文本对话框"""
        try:
            # 检查设备连接
            device = self.app.device_manager.validate_device_selection()
            if not device:
                return False
            
            # 创建设备选择对话框
            dialog = tk.Toplevel(self.app.root)
            dialog.title("输入文本到设备")
            dialog.geometry("500x400")
            dialog.resizable(True, True)
            dialog.transient(self.app.root)
            # dialog.grab_set()  # 注释掉以允许在程序和桌面之间自由切换
            
            # 绑定对话框的焦点事件
            dialog.bind("<FocusOut>", lambda e: self._on_dialog_focus_out(dialog))
            dialog.bind("<Map>", lambda e: self._on_dialog_map(dialog))
            
            # 居中显示
            dialog.geometry("+%d+%d" % (
                self.app.root.winfo_rootx() + (self.app.root.winfo_width() - 500) // 2,
                self.app.root.winfo_rooty() + (self.app.root.winfo_height() - 400) // 2
            ))
            
            # 主框架
            main_frame = ttk.Frame(dialog, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 标题
            title_label = ttk.Label(main_frame, text="输入文本到Android设备", font=('Arial', 14, 'bold'))
            title_label.pack(pady=(0, 15))
            
            # 说明文本
            info_label = ttk.Label(main_frame, 
                                 text="请在下方输入框中输入要发送到设备的文本。\n"
                                      "注意：空格和特殊字符会被正确处理。", 
                                 font=('Arial', 10))
            info_label.pack(pady=(0, 15))
            
            # 文本输入框架
            text_frame = ttk.LabelFrame(main_frame, text="输入文本", padding="10")
            text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
            
            # 文本输入框
            text_input = tk.Text(text_frame, height=8, wrap=tk.WORD, font=('Arial', 11))
            scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_input.yview)
            text_input.configure(yscrollcommand=scrollbar.set)
            
            text_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 按钮框架
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(15, 0))
            
            def on_send():
                text_to_send = text_input.get(1.0, tk.END).strip()
                if not text_to_send:
                    messagebox.showwarning("输入错误", "请输入要发送的文本")
                    return
                
                # 发送文本
                success = self._send_text_to_device(device, text_to_send)
                # if success:
                #     # 成功发送，不显示消息框，让用户继续使用
                #     pass
                # else:
                #     messagebox.showerror("失败", "文本发送失败，请检查设备连接")
            
            def on_clear():
                text_input.delete(1.0, tk.END)
            
            def on_cancel():
                dialog.grab_release()  # 释放模态锁定
                dialog.destroy()
                # 恢复主窗口焦点
                self.app.ui.restore_focus_after_dialog()
            
            ttk.Button(button_frame, text="发送", command=on_send).pack(side=tk.RIGHT, padx=(5, 0))
            ttk.Button(button_frame, text="清空", command=on_clear).pack(side=tk.RIGHT, padx=(5, 0))
            ttk.Button(button_frame, text="取消", command=on_cancel).pack(side=tk.RIGHT)
            
            # 绑定快捷键
            text_input.bind('<Control-Return>', lambda e: on_send())
            dialog.bind('<Escape>', lambda e: on_cancel())
            
            # 绑定窗口关闭事件
            dialog.protocol("WM_DELETE_WINDOW", on_cancel)
            
            # 绑定对话框的窗口事件
            dialog.bind("<Unmap>", lambda e: self._on_dialog_unmap(dialog))
            
            # 设置焦点
            text_input.focus()
            
            return True
            
        except Exception as e:
            messagebox.showerror("错误", f"打开输入文本对话框失败: {str(e)}")
            return False
    
    def _send_text_to_device(self, device, text):
        """发送文本到设备"""
        try:
            # 处理特殊字符和空格
            # adb shell input text 对某些字符有限制，需要特殊处理
            processed_text = self._process_text_for_adb(text)
            
            # 构建adb命令
            cmd = f"adb -s {device} shell input text '{processed_text}'"
            
            # 执行命令
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"[DEBUG] 文本发送成功: {text}")
                return True
            else:
                print(f"[DEBUG] 文本发送失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("[DEBUG] 文本发送超时")
            return False
        except Exception as e:
            print(f"[DEBUG] 文本发送异常: {str(e)}")
            return False
    
    def _process_text_for_adb(self, text):
        """处理文本以适配adb input text命令"""
        try:
            # adb shell input text 的限制：
            # 1. 空格需要用%s表示
            # 2. 某些特殊字符需要转义
            # 3. 单引号需要特殊处理
            
            # 替换空格
            processed = text.replace(' ', '%s')
            
            # 处理其他特殊字符
            # 替换常见的需要转义的字符
            char_replacements = {
                '&': '%s&%s',
                '(': '%s(%s',
                ')': '%s)%s',
                ';': '%s;%s',
                '|': '%s|%s',
                '*': '%s*%s',
                '?': '%s?%s',
                '<': '%s<%s',
                '>': '%s>%s',
                '[': '%s[%s',
                ']': '%s]%s',
                '{': '%s{%s',
                '}': '%s}%s',
                '^': '%s^%s',
                '~': '%s~%s',
                '`': '%s`%s',
                '"': '%s"%s',
                "'": "\\'",  # 单引号特殊处理

            }
            
            # 应用字符替换
            for char, replacement in char_replacements.items():
                if char in processed:
                    processed = processed.replace(char, replacement)
            
            # 清理多余的空格标记
            processed = processed.replace('%s%s', '%s')
            
            return processed
            
        except Exception as e:
            print(f"[DEBUG] 文本处理失败: {str(e)}")
            return text  # 如果处理失败，返回原始文本
    
    def _on_dialog_focus_out(self, dialog):
        """对话框失去焦点时的处理"""
        try:
            # 检查对话框是否仍然存在
            if dialog.winfo_exists():
                # 延迟检查，如果对话框仍然可见，尝试重新获得焦点
                dialog.after(100, lambda: self._check_dialog_focus(dialog))
        except Exception as e:
            print(f"对话框焦点处理失败: {e}")
    
    def _on_dialog_map(self, dialog):
        """对话框显示时的处理"""
        try:
            # 确保对话框获得焦点
            dialog.focus_force()
        except Exception as e:
            print(f"对话框显示处理失败: {e}")
    
    def _check_dialog_focus(self, dialog):
        """检查对话框焦点状态"""
        try:
            if dialog.winfo_exists() and dialog.winfo_viewable():
                # 如果对话框可见但没有焦点，尝试重新获得焦点
                if not dialog.focus_get():
                    dialog.focus_force()
        except Exception as e:
            print(f"检查对话框焦点失败: {e}")
    
    def _on_dialog_unmap(self, dialog):
        """对话框隐藏时的处理"""
        try:
            # 释放模态锁定
            dialog.grab_release()
            # 恢复主窗口焦点
            self.app.ui.restore_focus_after_dialog()
        except Exception as e:
            print(f"对话框隐藏处理失败: {e}")