#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Android ADB Logcat 关键字过滤工具
支持正则表达式、大小写敏感、彩色显示和保存功能
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import subprocess
import threading
import re
import os
from datetime import datetime
import queue

class LogcatFilterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("手机日志辅助工具 v2.0")
        self.root.geometry("1000x700")
        
        # 变量
        self.filter_keyword = tk.StringVar()
        self.use_regex = tk.BooleanVar()
        self.case_sensitive = tk.BooleanVar()
        self.color_highlight = tk.BooleanVar()
        self.is_running = False
        self.log_process = None
        self.log_queue = queue.Queue()
        
        # 性能监控变量
        self.performance_stats = {
            'processed_lines': 0,
            'start_time': None,
            'last_update_time': None,
            'processing_rate': 0.0
        }
        
        # 自适应处理参数
        self.adaptive_params = {
            'base_batch_size': 50,      # 基础批次大小
            'max_batch_size': 200,      # 最大批次大小
            'base_interval': 50,         # 基础处理间隔(ms)
            'min_interval': 10,          # 最小处理间隔(ms)
            'high_load_threshold': 100,  # 高负荷阈值
            'medium_load_threshold': 50, # 中等负荷阈值
            'max_display_lines': 5000,   # 最大显示行数（默认5000）
            'trim_threshold': 250        # 裁剪触发阈值（max_display_lines的5%）
        }
        
        # 性能缓存
        self.performance_cache = {
            'last_line_count': 0,
            'last_memory_mb': 0.0,
            'last_memory_check': 0,
            'cache_update_interval': 20   # 每20次更新才重新计算
        }
        
        # 搜索相关变量
        self.search_keyword = tk.StringVar()
        self.search_case_sensitive = tk.BooleanVar()
        self.search_use_regex = tk.BooleanVar()
        self.current_search_pos = "1.0"
        self.search_results = []
        self.current_result_index = 0
        
        # 设备选择相关变量
        self.selected_device = tk.StringVar()
        self.available_devices = []
        self.device_combo = None
        
        # 设置默认值
        self.use_regex.set(True)
        self.case_sensitive.set(False)
        self.color_highlight.set(True)
        
        self.setup_ui()
        self.setup_log_display()
        self.setup_menu()
        
        # 启动日志队列处理
        self.process_log_queue()
        
        # 初始化设备列表
        self.refresh_devices()
    
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(2, weight=1)
        
        # 控制面板
        control_frame = ttk.LabelFrame(self.main_frame, text="过滤控制", padding="5")
        control_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 第一行 - 设备控制 + MTKLOG + ADB log操作
        first_row_frame = ttk.Frame(control_frame)
        first_row_frame.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 设备选择
        ttk.Label(first_row_frame, text="设备:").pack(side=tk.LEFT, padx=(0, 5))
        self.device_combo = ttk.Combobox(first_row_frame, textvariable=self.selected_device, width=18, state="readonly")
        self.device_combo.pack(side=tk.LEFT, padx=(0, 5))
        
        # 刷新设备按钮
        ttk.Button(first_row_frame, text="刷新设备", command=self.refresh_devices).pack(side=tk.LEFT, padx=(0, 5))
        
        # MTKLOG按钮组
        mtklog_label = ttk.Label(first_row_frame, text="MTKLOG:")
        mtklog_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.start_mtklog_button = ttk.Button(first_row_frame, text="开启", command=self.start_mtklog)
        self.start_mtklog_button.pack(side=tk.LEFT, padx=(0, 2))
        
        self.stop_export_mtklog_button = ttk.Button(first_row_frame, text="停止&导出", command=self.stop_and_export_mtklog)
        self.stop_export_mtklog_button.pack(side=tk.LEFT, padx=(0, 2))
        
        self.delete_mtklog_button = ttk.Button(first_row_frame, text="删除", command=self.delete_mtklog)
        self.delete_mtklog_button.pack(side=tk.LEFT, padx=(0, 2))
        
        self.sd_mode_button = ttk.Button(first_row_frame, text="SD模式", command=self.set_sd_mode)
        self.sd_mode_button.pack(side=tk.LEFT, padx=(0, 2))
        
        self.usb_mode_button = ttk.Button(first_row_frame, text="USB模式", command=self.set_usb_mode)
        self.usb_mode_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # ADB log按钮组
        adblog_label = ttk.Label(first_row_frame, text="ADB Log:")
        adblog_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.start_adblog_button = ttk.Button(first_row_frame, text="开启", command=self.start_adblog)
        self.start_adblog_button.pack(side=tk.LEFT, padx=(0, 2))
        
        self.export_adblog_button = ttk.Button(first_row_frame, text="导出", command=self.export_adblog)
        self.export_adblog_button.pack(side=tk.LEFT)
        
        # 第二行 - 过滤控制 + 常用操作
        second_row_frame = ttk.Frame(control_frame)
        second_row_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 关键字输入
        ttk.Label(second_row_frame, text="关键字:").pack(side=tk.LEFT, padx=(0, 5))
        keyword_entry = ttk.Entry(second_row_frame, textvariable=self.filter_keyword, width=20)
        keyword_entry.pack(side=tk.LEFT, padx=(0, 10))
        keyword_entry.bind('<Return>', lambda e: self.start_filtering())
        
        # 选项复选框
        ttk.Checkbutton(second_row_frame, text="正则表达式", variable=self.use_regex).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Checkbutton(second_row_frame, text="区分大小写", variable=self.case_sensitive).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Checkbutton(second_row_frame, text="彩色高亮", variable=self.color_highlight).pack(side=tk.LEFT, padx=(0, 10))
        
        # 主要操作按钮
        self.start_button = ttk.Button(second_row_frame, text="开始过滤", command=self.start_filtering)
        self.start_button.pack(side=tk.LEFT, padx=(0, 3))
        
        self.stop_button = ttk.Button(second_row_frame, text="停止", command=self.stop_filtering, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # 常用按钮
        ttk.Button(second_row_frame, text="清空日志", command=self.clear_logs).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(second_row_frame, text="清除缓存", command=self.clear_device_logs).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(second_row_frame, text="设置行数", command=self.show_display_lines_dialog).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(second_row_frame, text="保存日志", command=self.save_logs).pack(side=tk.LEFT)
        
        
        # 状态栏框架
        status_frame = ttk.Frame(self.main_frame)
        status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(0, weight=1)
        
        # 主状态
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        # 性能指标
        self.performance_var = tk.StringVar()
        self.performance_var.set("")
        performance_bar = ttk.Label(status_frame, textvariable=self.performance_var, relief=tk.SUNKEN, foreground="blue")
        performance_bar.grid(row=0, column=1, sticky=tk.E)
    
    def setup_log_display(self):
        """设置日志显示区域"""
        # 日志显示框架
        log_frame = ttk.LabelFrame(self.main_frame, text="日志内容", padding="5")
        log_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 创建文本框和滚动条
        text_frame = ttk.Frame(log_frame)
        text_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        self.log_text = tk.Text(text_frame, wrap=tk.WORD, font=('Cascadia Mono', 12), 
                               bg='#0C0C0C', fg='#FFFFFF', insertbackground='white')
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 滚动条
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # 配置文本标签用于高亮
        self.log_text.tag_configure("highlight", foreground="#FF4444", background="")
        self.log_text.tag_configure("normal", foreground="#FFFFFF")
        self.log_text.tag_configure("search_highlight", foreground="#00FF00", background="#333333")
        
        # 绑定鼠标滚轮事件
        self.log_text.bind("<MouseWheel>", self.on_mousewheel)
        self.log_text.bind("<Button-4>", self.on_mousewheel)
        self.log_text.bind("<Button-5>", self.on_mousewheel)
        
        # 绑定搜索快捷键 - 只绑定一次，避免重复触发
        self.root.bind_all("<Control-f>", self.show_search_dialog)
        self.root.bind_all("<Control-F>", self.show_search_dialog)
        self.root.bind_all("<F3>", self.find_next)
        self.root.bind_all("<Shift-F3>", self.find_previous)
        self.root.bind_all("<Control-g>", self.find_next)
        
        # 确保主窗口能接收键盘事件
        self.root.focus_set()
        
        # 添加窗口状态管理
        self.setup_window_management()
    
    def setup_window_management(self):
        """设置窗口管理功能"""
        # 绑定窗口状态变化事件
        self.root.bind("<Map>", self.on_window_map)
        self.root.bind("<Unmap>", self.on_window_unmap)
        self.root.bind("<FocusIn>", self.on_window_focus)
        self.root.bind("<FocusOut>", self.on_window_focus_out)
        
        # 绑定Alt+Tab快捷键，确保程序能通过Alt+Tab切换回来
        self.root.bind("<Alt-Tab>", self.on_alt_tab)
        
        # 设置窗口属性
        self.root.attributes('-topmost', False)  # 不总是置顶
        self.root.lift()  # 提升窗口到最前
        
        # 设置任务栏图标和窗口属性
        try:
            self.root.iconbitmap(default="")  # 使用默认图标
        except:
            pass  # 如果没有图标文件，忽略错误
        
        # 设置窗口最小化行为
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 添加全局快捷键支持
        self.root.bind_all("<Control-Shift-L>", lambda e: self.bring_to_front())
    
    def on_window_map(self, event):
        """窗口显示时调用"""
        self.root.lift()
        self.root.focus_force()
    
    def on_window_unmap(self, event):
        """窗口隐藏时调用"""
        pass
    
    def on_window_focus(self, event):
        """窗口获得焦点时调用"""
        self.root.lift()
    
    def on_window_focus_out(self, event):
        """窗口失去焦点时调用"""
        pass
    
    def on_alt_tab(self, event):
        """Alt+Tab时调用"""
        self.root.lift()
        self.root.focus_force()
        return "break"  # 阻止默认行为
    
    def bring_to_front(self):
        """将窗口带到最前面"""
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after(100, lambda: self.root.attributes('-topmost', False))
        self.root.focus_force()
    
    def on_closing(self):
        """窗口关闭时的处理"""
        if self.is_running:
            self.stop_filtering()
        self.root.destroy()
    
    def setup_menu(self):
        """设置菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 编辑菜单
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="搜索 (Ctrl+F)", command=self.show_search_dialog)
        edit_menu.add_command(label="查找下一个 (F3)", command=self.find_next)
        edit_menu.add_command(label="查找上一个 (Shift+F3)", command=self.find_previous)
        edit_menu.add_separator()
        edit_menu.add_command(label="清空日志", command=self.clear_logs)
        
        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="显示窗口", command=self.bring_to_front)
        tools_menu.add_separator()
        tools_menu.add_command(label="刷新设备列表", command=self.refresh_devices)
        tools_menu.add_command(label="设置显示行数", command=self.show_display_lines_dialog)
        tools_menu.add_command(label="清除设备缓存", command=self.clear_device_logs)
        tools_menu.add_command(label="保存日志", command=self.save_logs)
        tools_menu.add_separator()
        tools_menu.add_command(label="安装MTKLOGGER", command=self.install_mtklogger)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)
    
    def show_about(self):
        """显示关于对话框"""
        messagebox.showinfo("关于", 
            "手机log辅助工具\n\n"
            "版本: 2.0\n"
            "功能: Android设备日志管理和MTKLOG操作\n\n"
            "主要功能:\n"
            "• 实时过滤Android设备日志\n"
            "• MTKLOG开启/停止/导出/删除\n"
            "• ADB Log开启/导出\n"
            "• 设备模式切换(SD/USB)\n"
            "• 多设备支持\n"
            "• 性能监控和优化\n\n"
            "快捷键:\n"
            "Ctrl+F - 搜索\n"
            "F3 - 查找下一个\n"
            "Shift+F3 - 查找上一个\n"
            "Ctrl+Shift+L - 显示窗口\n"
            "Escape - 关闭搜索对话框\n\n"
            "窗口管理:\n"
            "使用 Alt+Tab 切换窗口\n"
            "使用任务栏图标访问程序\n"
            "菜单: 工具 → 显示窗口")
    
    def on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        if event.delta:
            self.log_text.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif event.num == 4:
            self.log_text.yview_scroll(-1, "units")
        elif event.num == 5:
            self.log_text.yview_scroll(1, "units")
        return "break"
    
    def start_filtering(self):
        """开始过滤日志"""
        keyword = self.filter_keyword.get().strip()
        if not keyword:
            messagebox.showwarning("警告", "请输入过滤关键字")
            return
        
        # if self.is_running:
        #     messagebox.showinfo("提示", "过滤已在运行中")
        #     return
        
        # 检查设备选择
        device = self.selected_device.get().strip()
        
        # 如果有多个设备但未选择，提示用户选择
        if len(self.available_devices) > 1 and device == "":
            messagebox.showwarning("警告", f"检测到多个设备，请选择要抓取日志的设备:\n{', '.join(self.available_devices)}")
            return
        
        bad_devices = {"无设备", "检测失败", "检测超时", "adb未安装", "检测错误"}
        if device == "" or device in bad_devices:
            messagebox.showwarning("警告", "请先选择有效的设备")
            return
        
        try:
            # 验证正则表达式
            if self.use_regex.get():
                re.compile(keyword)
        except re.error as e:
            messagebox.showerror("错误", f"正则表达式无效: {e}")
            return
        
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_var.set("正在过滤...")
        
        # 初始化性能统计
        self.performance_stats['start_time'] = datetime.now()
        self.performance_stats['last_update_time'] = datetime.now()
        self.performance_stats['processed_lines'] = 0
        self.performance_stats['processing_rate'] = 0.0
        self.update_performance_display()
        
        # 在新线程中启动logcat
        threading.Thread(target=self.run_logcat, daemon=True).start()
    
    def run_logcat(self):
        """运行adb logcat命令"""
        try:
            # 检查设备选择
            device = self.selected_device.get().strip()
            if not device or device in ["无设备", "检测失败", "检测超时", "adb未安装", "检测错误"]:
                self.log_queue.put("ERROR: 请先选择有效的设备")
                return
            
            # 构建adb logcat命令，添加-b all参数确保完全输出
            cmd = ["adb", "-s", device, "logcat", "-b", "all", "-v", "time"]
            
            # 启动进程
            self.log_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',  # 遇到无法解码的字符时用替换字符代替
                bufsize=1,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # 读取输出
            for line in iter(self.log_process.stdout.readline, ''):
                if not self.is_running:
                    break
                
                # 过滤日志
                if self.filter_line(line):
                    self.log_queue.put(line)
            
        except FileNotFoundError:
            self.log_queue.put("ERROR: 未找到adb命令，请确保Android SDK已安装并配置PATH")
        except Exception as e:
            self.log_queue.put(f"ERROR: {e}")
        finally:
            self.is_running = False
            self.root.after(0, self.filtering_stopped)
    
    def filter_line(self, line):
        """过滤日志行"""
        keyword = self.filter_keyword.get()
        
        if self.use_regex.get():
            try:
                flags = 0 if self.case_sensitive.get() else re.IGNORECASE
                return bool(re.search(keyword, line, flags))
            except re.error:
                return False
        else:
            if self.case_sensitive.get():
                return keyword in line
            else:
                return keyword.lower() in line.lower()
    
    def process_log_queue(self):
        """处理日志队列 - 自适应批次大小"""
        batch_lines = []
        queue_size = self.log_queue.qsize()
        
        # 根据队列大小动态调整批次大小和处理策略
        if queue_size > self.adaptive_params['high_load_threshold']:
            # 高负荷：大批次，快速处理，启用采样
            batch_size = self.adaptive_params['max_batch_size']
            interval = self.adaptive_params['min_interval']
            use_sampling = True
        elif queue_size > self.adaptive_params['medium_load_threshold']:
            # 中等负荷：中等批次
            batch_size = int(self.adaptive_params['base_batch_size'] * 1.5)
            interval = int(self.adaptive_params['base_interval'] * 0.7)
            use_sampling = False
        else:
            # 低负荷：基础批次
            batch_size = self.adaptive_params['base_batch_size']
            interval = self.adaptive_params['base_interval']
            use_sampling = False
        
        try:
            # 批量处理，减少UI更新次数
            if use_sampling:
                # 高负荷时使用采样：每3行取1行
                sampled_count = 0
                while len(batch_lines) < batch_size:
                    line = self.log_queue.get_nowait()
                    sampled_count += 1
                    if sampled_count % 3 == 1:  # 每3行取第1行
                        batch_lines.append(line)
            else:
                # 正常处理
                while len(batch_lines) < batch_size:
                    line = self.log_queue.get_nowait()
                    batch_lines.append(line)
        except queue.Empty:
            pass
        
        # 批量添加日志行
        if batch_lines:
            self.add_log_lines_batch(batch_lines)
        
        # 动态调整处理间隔
        self.root.after(interval, self.process_log_queue)
    
    def add_log_lines_batch(self, lines):
        """批量添加日志行，提高性能"""
        self.log_text.config(state=tk.NORMAL)
        
        # 移动到末尾
        self.log_text.see(tk.END)
        
        # 批量处理所有行
        for line in lines:
            # 直接使用设备log输出的时间，不添加额外时间戳
            full_line = line.rstrip() + "\n"
            
            # 高亮关键字（如果启用）- 支持自适应高亮策略
            if self.color_highlight.get() and self.filter_keyword.get():
                self.add_highlighted_line_batch(full_line)
            else:
                self.log_text.insert(tk.END, full_line)
        
        # 更新性能统计
        self.performance_stats['processed_lines'] += len(lines)
        self.update_performance_display()
        
        # 高效的行数裁剪机制
        self.trim_log_lines_if_needed(len(lines))
        
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)
    
    def add_highlighted_line_batch(self, line):
        """批量添加高亮显示的日志行，支持自适应高亮策略"""
        keyword = self.filter_keyword.get()
        if not keyword:
            self.log_text.insert(tk.END, line)
            return
        
        # 检查队列负荷，决定高亮策略
        queue_size = self.log_queue.qsize()
        
        # 准备搜索模式
        if self.use_regex.get():
            try:
                flags = 0 if self.case_sensitive.get() else re.IGNORECASE
                pattern = keyword
            except re.error:
                pattern = re.escape(keyword)
                flags = 0 if self.case_sensitive.get() else re.IGNORECASE
        else:
            pattern = re.escape(keyword)
            flags = 0 if self.case_sensitive.get() else re.IGNORECASE
        
        # 查找匹配
        matches = list(re.finditer(pattern, line, flags))
        
        if not matches:
            self.log_text.insert(tk.END, line)
            return
        
        # 自适应高亮策略：高负荷时只高亮第一个匹配
        if queue_size > self.adaptive_params['high_load_threshold']:
            # 高负荷：只高亮第一个匹配，提升性能
            match = matches[0]
            # 插入匹配前的文本
            if match.start() > 0:
                self.log_text.insert(tk.END, line[:match.start()])
        # 插入高亮文本
            self.log_text.insert(tk.END, match.group(), "highlight")
            # 插入匹配后的文本
            if match.end() < len(line):
                self.log_text.insert(tk.END, line[match.end():])
        else:
            # 正常负荷：高亮所有匹配
            last_end = 0
            for match in matches:
                # 插入普通文本
                if match.start() > last_end:
                    self.log_text.insert(tk.END, line[last_end:match.start()])
                
                # 插入高亮文本
                self.log_text.insert(tk.END, match.group(), "highlight")
                last_end = match.end()
        
        # 插入剩余文本
        if last_end < len(line):
            self.log_text.insert(tk.END, line[last_end:])
    
    def trim_log_lines_if_needed(self, added_lines):
        """高效的行数裁剪机制 - 使用trim_threshold避免频繁操作"""
        # 维护行计数器
        if not hasattr(self, '_line_count'):
            self._line_count = 0
        
        self._line_count += added_lines
        
        # 使用统一的trim_threshold值
        trim_threshold = self.adaptive_params['trim_threshold']
        
        # 只有当累计新增行数超过trim_threshold时才检查并裁剪
        if self._line_count > trim_threshold:
            try:
                # 获取当前总行数
                current_lines = int(self.log_text.index('end-1c').split('.')[0])
                
                if current_lines > self.adaptive_params['max_display_lines']:
                    # 计算需要删除的行数
                    lines_to_delete = current_lines - self.adaptive_params['max_display_lines']
                    
                    # 使用文本索引一次性删除超出的行
                    self.log_text.delete("1.0", f"{lines_to_delete + 1}.0")
                    
                    # 更新缓存
                    self.performance_cache['last_line_count'] = self.adaptive_params['max_display_lines']
                    
                    # 重置计数器
                    self._line_count = 0
                    
                    # 输出调试信息
                    print(f"裁剪日志: 删除了 {lines_to_delete} 行，当前行数: {self.adaptive_params['max_display_lines']} (trim_threshold: {trim_threshold})")
                    
            except Exception as e:
                # 如果出现异常，回退到原来的方法
                try:
                    lines_count = len(self.log_text.get("1.0", tk.END).split('\n'))
                    if lines_count > self.adaptive_params['max_display_lines']:
                        lines_to_delete = lines_count - self.adaptive_params['max_display_lines']
                        self.log_text.delete("1.0", f"{lines_to_delete + 1}.0")
                        self.performance_cache['last_line_count'] = self.adaptive_params['max_display_lines']
                        print(f"裁剪日志(备用方法): 删除了 {lines_to_delete} 行")
                except Exception as e2:
                    print(f"裁剪日志失败: {e2}")
                
                # 重置计数器
                self._line_count = 0
    
    def add_log_line(self, line):
        """添加日志行到显示区域"""
        self.log_text.config(state=tk.NORMAL)
        
        # 移动到末尾
        self.log_text.see(tk.END)
        
        # 直接使用设备log输出的时间，不添加额外时间戳
        full_line = line.rstrip()
        
        # 高亮关键字
        if self.color_highlight.get() and self.filter_keyword.get():
            self.add_highlighted_line(full_line)
        else:
            self.log_text.insert(tk.END, full_line + "\n")
        
        # 高效的行数裁剪机制
        self.trim_log_lines_if_needed(1)
        
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)
    
    def add_highlighted_line(self, line):
        """添加高亮显示的日志行"""
        keyword = self.filter_keyword.get()
        if not keyword:
            self.log_text.insert(tk.END, line + "\n")
            return
        
        # 准备搜索模式
        if self.use_regex.get():
            try:
                flags = 0 if self.case_sensitive.get() else re.IGNORECASE
                pattern = keyword
            except re.error:
                pattern = re.escape(keyword)
                flags = 0 if self.case_sensitive.get() else re.IGNORECASE
        else:
            pattern = re.escape(keyword)
            flags = 0 if self.case_sensitive.get() else re.IGNORECASE
        
        # 查找匹配
        matches = list(re.finditer(pattern, line, flags))
        
        if not matches:
            self.log_text.insert(tk.END, line + "\n")
            return
        
        # 插入高亮文本
        last_end = 0
        for match in matches:
            # 插入普通文本
            if match.start() > last_end:
                self.log_text.insert(tk.END, line[last_end:match.start()])
            
            # 插入高亮文本
            self.log_text.insert(tk.END, match.group(), "highlight")
            last_end = match.end()
        
        # 插入剩余文本
        if last_end < len(line):
            self.log_text.insert(tk.END, line[last_end:])
        
        self.log_text.insert(tk.END, "\n")
    
    def update_performance_display(self):
        """更新性能显示"""
        if not self.is_running:
            return
        
        current_time = datetime.now()
        queue_size = self.log_queue.qsize()
        
        # 计算处理速率（每秒处理的行数）
        if self.performance_stats['start_time']:
            elapsed_time = (current_time - self.performance_stats['start_time']).total_seconds()
            if elapsed_time > 0:
                self.performance_stats['processing_rate'] = self.performance_stats['processed_lines'] / elapsed_time
        
        # 获取当前自适应参数
        current_batch_size = self.get_current_batch_size(queue_size)
        current_interval = self.get_current_interval(queue_size)
        
        # 更新性能显示
        rate_text = f"{self.performance_stats['processing_rate']:.1f}" if self.performance_stats['processing_rate'] > 0 else "0.0"
        
        # 使用缓存机制计算当前显示的行数和内存使用
        current_display_lines, memory_mb = self.get_cached_performance_metrics()
        
        performance_text = f"队列: {queue_size} | 速率: {rate_text} 行/秒 | 批次: {current_batch_size} | 间隔: {current_interval}ms | 显示: {current_display_lines}行 | 内存: {memory_mb:.1f}MB"
        
        # 根据队列大小改变颜色和状态
        if queue_size > self.adaptive_params['high_load_threshold']:
            performance_text += " (高负荷-采样模式)"
            color = "red"
        elif queue_size > self.adaptive_params['medium_load_threshold']:
            performance_text += " (中负荷-优化)"
            color = "orange"
        else:
            performance_text += " (正常)"
            color = "blue"
        
        self.performance_var.set(performance_text)
        
        # 更新性能栏颜色
        for child in self.main_frame.winfo_children():
            if isinstance(child, ttk.Frame):
                for grandchild in child.winfo_children():
                    if isinstance(grandchild, ttk.Label) and grandchild.cget('textvariable') == str(self.performance_var):
                        grandchild.configure(foreground=color)
                        break
    
    def get_current_batch_size(self, queue_size):
        """获取当前批次大小"""
        if queue_size > self.adaptive_params['high_load_threshold']:
            return self.adaptive_params['max_batch_size']
        elif queue_size > self.adaptive_params['medium_load_threshold']:
            return int(self.adaptive_params['base_batch_size'] * 1.5)
        else:
            return self.adaptive_params['base_batch_size']
    
    def get_current_interval(self, queue_size):
        """获取当前处理间隔"""
        if queue_size > self.adaptive_params['high_load_threshold']:
            return self.adaptive_params['min_interval']
        elif queue_size > self.adaptive_params['medium_load_threshold']:
            return int(self.adaptive_params['base_interval'] * 0.7)
        else:
            return self.adaptive_params['base_interval']
    
    def get_cached_performance_metrics(self):
        """使用缓存机制获取性能指标，减少计算开销"""
        # 行数总是实时计算
        try:
            # 计算当前显示的行数（实时计算）
            current_display_lines = int(self.log_text.index('end-1c').split('.')[0])
            
            # 检查是否需要更新内存缓存（基于时间间隔）
            current_time = datetime.now()
            if not hasattr(self, '_last_memory_update') or \
               (current_time - self._last_memory_update).total_seconds() > 2.0:  # 每2秒更新一次
                
                # 计算内存使用情况（更准确的估算）
                try:
                    # 获取文本内容长度
                    text_content = self.log_text.get("1.0", tk.END)
                    text_length = len(text_content)
                    
                    # 估算内存使用（包括Tkinter内部开销）
                    # 每个字符大约2-4字节（UTF-8编码 + Tkinter内部结构）
                    estimated_memory_bytes = text_length * 3  # 使用3字节作为平均值
                    memory_mb = estimated_memory_bytes / (1024 * 1024)
                    
                    # 更新缓存
                    self.performance_cache['last_memory_mb'] = memory_mb
                    self._last_memory_update = current_time
                    
                except Exception:
                    # 如果计算失败，使用缓存值
                    memory_mb = self.performance_cache['last_memory_mb']
            else:
                # 使用缓存的内存值
                memory_mb = self.performance_cache['last_memory_mb']
            
            return current_display_lines, memory_mb
                
        except Exception:
            # 如果出现异常，返回缓存值
            return self.performance_cache['last_line_count'], self.performance_cache['last_memory_mb']
    
    def refresh_devices(self):
        """刷新可用设备列表"""
        try:
            # 执行adb devices命令
            result = subprocess.run(
                ["adb", "devices"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                # 解析设备列表
                lines = result.stdout.strip().split('\n')[1:]  # 跳过第一行标题
                self.available_devices = []
                
                for line in lines:
                    if line.strip() and '\tdevice' in line:
                        device_id = line.split('\t')[0].strip()
                        self.available_devices.append(device_id)
                
                # 更新下拉框
                if self.device_combo:
                    self.device_combo['values'] = self.available_devices
                    
                    # 如果只有一个设备，自动选择
                    if len(self.available_devices) == 1:
                        self.selected_device.set(self.available_devices[0])
                    elif len(self.available_devices) > 1:
                        # 多个设备时，清空选择
                        self.selected_device.set("")
                    else:
                        # 没有设备
                        self.selected_device.set("无设备")
                        
                self.status_var.set(f"检测到 {len(self.available_devices)} 个设备")
                
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                self.status_var.set(f"设备检测失败: {error_msg}")
                if self.device_combo:
                    self.device_combo['values'] = ["检测失败"]
                    self.selected_device.set("检测失败")
                
        except subprocess.TimeoutExpired:
            self.status_var.set("设备检测超时")
            if self.device_combo:
                self.device_combo['values'] = ["检测超时"]
                self.selected_device.set("检测超时")
        except FileNotFoundError:
            self.status_var.set("未找到adb命令")
            if self.device_combo:
                self.device_combo['values'] = ["adb未安装"]
                self.selected_device.set("adb未安装")
        except Exception as e:
            self.status_var.set(f"设备检测错误: {e}")
            if self.device_combo:
                self.device_combo['values'] = ["检测错误"]
                self.selected_device.set("检测错误")
    
    def show_display_lines_dialog(self):
        """显示设置最大显示行数的对话框"""
        # 创建设置对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("设置最大显示行数")
        dialog.geometry("450x450")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 居中显示
        dialog.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 50,
            self.root.winfo_rooty() + 50
        ))
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="设置最大显示行数", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 当前设置显示
        current_label = ttk.Label(main_frame, text=f"当前设置: {self.adaptive_params['max_display_lines']} 行")
        current_label.pack(pady=(0, 10))
        
        # 输入框
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(pady=(0, 20))
        
        ttk.Label(input_frame, text="最大显示行数:").pack(side=tk.LEFT, padx=(0, 10))
        lines_var = tk.StringVar(value=str(self.adaptive_params['max_display_lines']))
        lines_entry = ttk.Entry(input_frame, textvariable=lines_var, width=15)
        lines_entry.pack(side=tk.LEFT)
        lines_entry.focus()
        
        # 预设选项
        presets_frame = ttk.LabelFrame(main_frame, text="快速选择", padding="10")
        presets_frame.pack(fill=tk.X, pady=(0, 15))
        
        presets = [
            ("1000行 (轻量)", 1000),
            ("2000行 (标准)", 2000),
            ("5000行 (推荐)", 5000),
            ("10000行 (大量)", 10000),
            ("20000行 (超大)", 20000)
        ]
        
        # 使用垂直布局，避免重叠
        for text, value in presets:
            btn = ttk.Button(presets_frame, text=text, 
                           command=lambda v=value: lines_var.set(str(v)))
            btn.pack(fill=tk.X, padx=5, pady=2)
        
        # 说明文本
        info_text = "设置说明: 行数越多显示更多历史日志，建议范围: 1000-20000 行"
        
        info_label = ttk.Label(main_frame, text=info_text, justify=tk.LEFT, foreground="gray")
        info_label.pack(pady=(0, 10))
        
        def apply_settings():
            try:
                new_lines = int(lines_var.get())
                if new_lines < 100:
                    messagebox.showerror("错误", "行数不能少于100行")
                    return
                if new_lines > 100000:
                    messagebox.showerror("错误", "行数不能超过100000行")
                    return
                
                # 更新设置
                self.adaptive_params['max_display_lines'] = new_lines
                self.adaptive_params['trim_threshold'] = int(new_lines * 0.05)  # 5%的缓冲行数
                
                # 更新状态显示
                self.status_var.set(f"最大显示行数已设置为: {new_lines} 行")
                
                messagebox.showinfo("成功", f"设置已应用!\n最大显示行数: {new_lines}\ntrim_threshold: {self.adaptive_params['trim_threshold']}")
                dialog.destroy()
                
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字")
        
        # 按钮 - 使用更简单的布局
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 20))
        
        # 应用按钮
        apply_btn = ttk.Button(button_frame, text="确定", command=apply_settings)
        apply_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 取消按钮
        cancel_btn = ttk.Button(button_frame, text="取消", command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT)
        
        # 绑定回车键
        lines_entry.bind('<Return>', lambda e: apply_settings())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def stop_filtering(self):
        """停止过滤"""
        self.is_running = False
        if self.log_process:
            self.log_process.terminate()
            self.log_process.wait()  # 等待进程结束，避免僵尸进程
            self.log_process = None
    
    def filtering_stopped(self):
        """过滤停止后的处理"""
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("已停止")
        
        # 重置性能统计
        self.performance_var.set("")
    
    def clear_logs(self):
        """清空日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)
        self._line_count = 0  # 重置行计数器
        
        # 重置性能统计
        if self.is_running:
            self.performance_stats['processed_lines'] = 0
            self.performance_stats['start_time'] = datetime.now()
            self.performance_stats['processing_rate'] = 0.0
            self.update_performance_display()
        
        self.status_var.set("日志已清空")
    
    def save_logs(self):
        """保存日志到文件"""
        if not self.log_text.get("1.0", tk.END).strip():
            messagebox.showwarning("警告", "没有日志内容可保存")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            title="保存日志文件"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get("1.0", tk.END))
                messagebox.showinfo("成功", f"日志已保存到: {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")
    
    def show_search_dialog(self, event=None):
        """显示搜索对话框"""
        # 调试信息
        print(f"搜索对话框被触发，事件: {event}")
        
        # 创建搜索对话框
        search_dialog = tk.Toplevel(self.root)
        search_dialog.title("搜索")
        search_dialog.geometry("400x200")
        search_dialog.resizable(False, False)
        search_dialog.transient(self.root)
        search_dialog.grab_set()
        
        # 居中显示
        search_dialog.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 50,
            self.root.winfo_rooty() + 50
        ))
        
        # 确保对话框获得焦点
        search_dialog.focus_set()
        
        # 初始化搜索状态（如果还没有搜索结果）
        if not hasattr(self, 'search_results') or not self.search_results:
            self.search_results = []
            self.current_result_index = 0
        
        # 主框架
        main_frame = ttk.Frame(search_dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 搜索关键字
        ttk.Label(main_frame, text="搜索关键字:").grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        search_entry = ttk.Entry(main_frame, textvariable=self.search_keyword, width=30)
        search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 10), padx=(10, 0))
        search_entry.focus()
        search_entry.bind('<Return>', lambda e: self.perform_search(search_dialog))
        search_entry.bind('<Escape>', lambda e: search_dialog.destroy())
        
        # 延迟设置焦点，确保对话框完全显示后再设置
        search_dialog.after(100, lambda: search_entry.focus_set())
        
        # 搜索选项
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Checkbutton(options_frame, text="区分大小写", variable=self.search_case_sensitive).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Checkbutton(options_frame, text="正则表达式", variable=self.search_use_regex).pack(side=tk.LEFT)
        
        # 搜索状态显示
        self.search_status_var = tk.StringVar()
        self.search_status_var.set("")
        status_label = ttk.Label(main_frame, textvariable=self.search_status_var, foreground="blue")
        status_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        # 按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, sticky=tk.E, pady=(10, 0))
        
        ttk.Button(button_frame, text="搜索", command=lambda: self.perform_search(search_dialog)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="下一个", command=self.find_next_with_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="上一个", command=self.find_previous_with_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="查找所有", command=self.show_all_results).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="关闭", command=search_dialog.destroy).pack(side=tk.LEFT)
        
        # 配置网格权重
        main_frame.columnconfigure(1, weight=1)
    
    def perform_search(self, dialog=None):
        """执行搜索"""
        keyword = self.search_keyword.get().strip()
        if not keyword:
            messagebox.showwarning("警告", "请输入搜索关键字")
            return
        
        # 验证正则表达式
        if self.search_use_regex.get():
            try:
                re.compile(keyword)
            except re.error as e:
                messagebox.showerror("错误", f"正则表达式无效: {e}")
                return
        
        # 清除之前的高亮
        self.clear_search_highlight()
        
        # 执行搜索
        self.search_results = []
        self.current_result_index = 0
        
        # 获取文本内容
        text_content = self.log_text.get("1.0", tk.END)
        
        # 如果文本为空，提示用户
        if not text_content.strip():
            messagebox.showinfo("提示", "没有日志内容可搜索")
            if dialog:
                dialog.destroy()
            return
        
        # 准备搜索模式
        if self.search_use_regex.get():
            try:
                flags = 0 if self.search_case_sensitive.get() else re.IGNORECASE
                pattern = keyword
            except re.error:
                pattern = re.escape(keyword)
                flags = 0 if self.search_case_sensitive.get() else re.IGNORECASE
        else:
            pattern = re.escape(keyword)
            flags = 0 if self.search_case_sensitive.get() else re.IGNORECASE
        
        # 查找所有匹配
        for match in re.finditer(pattern, text_content, flags):
            start_pos = f"1.0+{match.start()}c"
            end_pos = f"1.0+{match.end()}c"
            self.search_results.append((start_pos, end_pos))
        
        if self.search_results:
            # 高亮所有匹配
            for start_pos, end_pos in self.search_results:
                self.log_text.tag_add("search_highlight", start_pos, end_pos)
            
            # 跳转到第一个匹配
            self.current_result_index = 0
            self.jump_to_search_result()
            
            # 不关闭对话框，让用户可以继续使用下一个/上一个按钮
            if dialog:
                # 更新状态显示
                self.status_var.set(f"找到 {len(self.search_results)} 个匹配项")
                self.search_status_var.set(f"找到 {len(self.search_results)} 个匹配项，当前第 {self.current_result_index + 1} 个")
        else:
            messagebox.showinfo("搜索结果", "未找到匹配项")
    
    def find_next(self, event=None):
        """查找下一个匹配项"""
        if not self.search_results:
            self.show_search_dialog()
            return
        
        if self.current_result_index < len(self.search_results) - 1:
            self.current_result_index += 1
        else:
            self.current_result_index = 0  # 循环到第一个
        
        self.jump_to_search_result()
    
    def find_next_with_dialog(self):
        """查找下一个匹配项（保持对话框打开）"""
        if not self.search_results:
            # 如果没有搜索结果，先尝试执行搜索
            keyword = self.search_keyword.get().strip()
            if keyword:
                self.perform_search(None)  # 不关闭对话框
                if self.search_results:
                    self.jump_to_search_result()
                    if hasattr(self, 'search_status_var'):
                        self.search_status_var.set(f"找到 {len(self.search_results)} 个匹配项，当前第 {self.current_result_index + 1} 个")
                else:
                    messagebox.showinfo("提示", "未找到匹配项")
            else:
                messagebox.showinfo("提示", "请先输入搜索关键字")
            return
        
        if self.current_result_index < len(self.search_results) - 1:
            self.current_result_index += 1
        else:
            self.current_result_index = 0  # 循环到第一个
        
        self.jump_to_search_result()
        # 更新搜索状态显示
        if hasattr(self, 'search_status_var'):
            self.search_status_var.set(f"找到 {len(self.search_results)} 个匹配项，当前第 {self.current_result_index + 1} 个")
    
    def find_previous(self, event=None):
        """查找上一个匹配项"""
        if not self.search_results:
            self.show_search_dialog()
            return
        
        if self.current_result_index > 0:
            self.current_result_index -= 1
        else:
            self.current_result_index = len(self.search_results) - 1  # 循环到最后一个
        
        self.jump_to_search_result()
    
    def find_previous_with_dialog(self):
        """查找上一个匹配项（保持对话框打开）"""
        if not self.search_results:
            # 如果没有搜索结果，先尝试执行搜索
            keyword = self.search_keyword.get().strip()
            if keyword:
                self.perform_search(None)  # 不关闭对话框
                if self.search_results:
                    # 跳转到最后一个结果
                    self.current_result_index = len(self.search_results) - 1
                    self.jump_to_search_result()
                    if hasattr(self, 'search_status_var'):
                        self.search_status_var.set(f"找到 {len(self.search_results)} 个匹配项，当前第 {self.current_result_index + 1} 个")
                else:
                    messagebox.showinfo("提示", "未找到匹配项")
            else:
                messagebox.showinfo("提示", "请先输入搜索关键字")
            return
        
        if self.current_result_index > 0:
            self.current_result_index -= 1
        else:
            self.current_result_index = len(self.search_results) - 1  # 循环到最后一个
        
        self.jump_to_search_result()
        # 更新搜索状态显示
        if hasattr(self, 'search_status_var'):
            self.search_status_var.set(f"找到 {len(self.search_results)} 个匹配项，当前第 {self.current_result_index + 1} 个")
    
    def jump_to_search_result(self):
        """跳转到当前搜索结果"""
        if not self.search_results:
            return
        
        start_pos, end_pos = self.search_results[self.current_result_index]
        
        # 跳转到匹配位置
        self.log_text.see(start_pos)
        
        # 选中匹配文本
        self.log_text.tag_remove(tk.SEL, "1.0", tk.END)
        self.log_text.tag_add(tk.SEL, start_pos, end_pos)
        
        # 更新状态
        self.status_var.set(f"找到 {len(self.search_results)} 个匹配项，当前第 {self.current_result_index + 1} 个")
    
    def clear_search_highlight(self):
        """清除搜索高亮"""
        self.log_text.tag_remove("search_highlight", "1.0", tk.END)
        self.log_text.tag_remove(tk.SEL, "1.0", tk.END)
    
    def show_all_results(self):
        """显示所有搜索结果"""
        keyword = self.search_keyword.get().strip()
        if not keyword:
            messagebox.showwarning("警告", "请输入搜索关键字")
            return
        
        # 如果没有搜索结果，先执行搜索
        if not self.search_results:
            self.perform_search(None)
            if not self.search_results:
                return
        
        # 创建结果显示窗口
        results_window = tk.Toplevel(self.root)
        results_window.title(f"搜索结果 - 找到 {len(self.search_results)} 个匹配项")
        results_window.geometry("1000x600")
        results_window.transient(self.root)
        
        # 居中显示
        results_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 50,
            self.root.winfo_rooty() + 50
        ))
        
        # 确保窗口获得焦点
        results_window.focus_set()
        results_window.grab_set()
        
        # 主框架
        main_frame = ttk.Frame(results_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 标题和统计信息
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        title_frame.columnconfigure(1, weight=1)
        
        ttk.Label(title_frame, text=f"搜索关键字: {keyword}", font=('Arial', 12, 'bold')).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(title_frame, text=f"找到 {len(self.search_results)} 个匹配项", foreground="blue").grid(row=0, column=1, sticky=tk.E)
        
        # 按钮框架
        button_frame = ttk.Frame(title_frame)
        button_frame.grid(row=0, column=2, sticky=tk.E, padx=(10, 0))
        
        ttk.Button(button_frame, text="全选", command=lambda: self.select_all_results(results_text)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="复制", command=lambda: self.copy_results(results_text)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="保存", command=lambda: self.save_results(results_text, keyword)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="关闭", command=results_window.destroy).pack(side=tk.LEFT)
        
        # 文本显示区域
        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        results_text = tk.Text(text_frame, wrap=tk.WORD, font=('Cascadia Mono', 10), 
                              bg='#0C0C0C', fg='#FFFFFF', insertbackground='white',
                              state=tk.NORMAL, selectbackground='#444444')
        results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 滚动条
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=results_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        results_text.configure(yscrollcommand=scrollbar.set)
        
        # 配置文本标签用于高亮
        results_text.tag_configure("highlight", foreground="#FF4444", background="")
        results_text.tag_configure("normal", foreground="#FFFFFF")
        
        # 填充搜索结果
        self.fill_search_results(results_text, keyword)
        
        # 绑定快捷键
        results_text.bind("<Control-a>", lambda e: self.select_all_results(results_text))
        results_text.bind("<Control-c>", lambda e: self.copy_results(results_text))
        results_text.bind("<Control-s>", lambda e: self.save_results(results_text, keyword))
        
        # 绑定窗口关闭事件
        def on_closing():
            results_window.grab_release()
            results_window.destroy()
        
        results_window.protocol("WM_DELETE_WINDOW", on_closing)
    
    def fill_search_results(self, text_widget, keyword):
        """填充搜索结果到文本控件"""
        text_widget.config(state=tk.NORMAL)
        text_widget.delete("1.0", tk.END)  # 清空内容
        
        # 获取原始文本内容
        original_text = self.log_text.get("1.0", tk.END)
        lines = original_text.split('\n')
        
        # 准备搜索模式
        if self.search_use_regex.get():
            try:
                flags = 0 if self.search_case_sensitive.get() else re.IGNORECASE
                pattern = keyword
            except re.error:
                pattern = re.escape(keyword)
                flags = 0 if self.search_case_sensitive.get() else re.IGNORECASE
        else:
            pattern = re.escape(keyword)
            flags = 0 if self.search_case_sensitive.get() else re.IGNORECASE
        
        # 查找包含关键字的行
        matching_lines = []
        for i, line in enumerate(lines):
            if re.search(pattern, line, flags):
                matching_lines.append((i + 1, line))  # 行号从1开始
        
        # 显示匹配的行
        for line_num, line in matching_lines:
            # 添加行号
            text_widget.insert(tk.END, f"[{line_num:4d}] ", "normal")
            
            # 添加高亮文本
            self.add_highlighted_line_to_widget(text_widget, line, keyword, pattern, flags)
            text_widget.insert(tk.END, "\n")
        
        # 保持文本控件可编辑状态，以便选择和复制
        text_widget.config(state=tk.NORMAL)
    
    def add_highlighted_line_to_widget(self, text_widget, line, keyword, pattern, flags):
        """向文本控件添加高亮行"""
        matches = list(re.finditer(pattern, line, flags))
        
        if not matches:
            text_widget.insert(tk.END, line)
            return
        
        # 插入高亮文本
        last_end = 0
        for match in matches:
            # 插入普通文本
            if match.start() > last_end:
                text_widget.insert(tk.END, line[last_end:match.start()])
            
            # 插入高亮文本
            text_widget.insert(tk.END, match.group(), "highlight")
            last_end = match.end()
        
        # 插入剩余文本
        if last_end < len(line):
            text_widget.insert(tk.END, line[last_end:])
    
    def select_all_results(self, text_widget):
        """全选搜索结果"""
        text_widget.config(state=tk.NORMAL)
        text_widget.tag_add(tk.SEL, "1.0", tk.END)
        text_widget.mark_set(tk.INSERT, "1.0")
        text_widget.see(tk.INSERT)
        text_widget.focus_set()
    
    def copy_results(self, text_widget):
        """复制搜索结果"""
        try:
            # 检查是否有选中文本
            if text_widget.tag_ranges(tk.SEL):
                selected_text = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            else:
                # 如果没有选中文本，复制全部内容
                selected_text = text_widget.get("1.0", tk.END)
            
            text_widget.clipboard_clear()
            text_widget.clipboard_append(selected_text)
            messagebox.showinfo("成功", "搜索结果已复制到剪贴板")
        except Exception as e:
            messagebox.showerror("错误", f"复制失败: {e}")
    
    def save_results(self, text_widget, keyword):
        """保存搜索结果到文件"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
                title="保存搜索结果",
                initialfile=f"搜索结果_{keyword}.txt"
            )
            
            if filename:
                # 获取文本内容
                content = text_widget.get("1.0", tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("成功", f"搜索结果已保存到: {filename}")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")
    
    def clear_device_logs(self):
        """清除设备日志缓存"""
        # 确认对话框
        result = messagebox.askyesno("确认", "确定要清除设备上的日志缓存吗？\n\n这将执行 'adb logcat -c' 命令")
        if not result:
            return
        
        try:
            # 执行adb logcat -c命令
            result = subprocess.run(
                ["adb", "logcat", "-c"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',  # 遇到无法解码的字符时用替换字符代替
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                messagebox.showinfo("成功", "设备日志缓存已清除")
                self.status_var.set("设备日志缓存已清除")
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                messagebox.showerror("错误", f"清除设备日志缓存失败:\n{error_msg}")
                self.status_var.set("清除设备日志缓存失败")
                
        except subprocess.TimeoutExpired:
            messagebox.showerror("错误", "清除设备日志缓存超时，请检查设备连接")
            self.status_var.set("清除设备日志缓存超时")
        except FileNotFoundError:
            messagebox.showerror("错误", "未找到adb命令，请确保Android SDK已安装并配置PATH")
            self.status_var.set("未找到adb命令")
        except Exception as e:
            messagebox.showerror("错误", f"清除设备日志缓存时发生错误: {e}")
            self.status_var.set("清除设备日志缓存失败")
    
    def start_mtklog(self):
        """开启MTKLOG"""
        device = self.selected_device.get()
        if not device:
            messagebox.showerror("错误", "请先选择设备")
            return
        
        # 先检查设备连接状态
        try:
            devices_cmd = ["adb", "devices"]
            result = subprocess.run(devices_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                messagebox.showerror("错误", "检查设备连接失败")
                self.status_var.set("检查设备连接失败")
                return
            
            # 检查设备是否在列表中
            if device not in result.stdout:
                messagebox.showerror("错误", f"设备 {device} 未连接")
                self.status_var.set(f"设备 {device} 未连接")
                return
            
            # 设备连接正常，继续检查MTKlogger
            self.status_var.set(f"设备 {device} 连接正常，检查MTKlogger...")
                
        except Exception as e:
            messagebox.showerror("错误", f"检查设备连接时发生错误: {e}")
            self.status_var.set("检查设备连接失败")
            return
        
        # 检查MTKlogger是否存在
        try:
            check_cmd = ["adb", "-s", device, "shell", "am", "start", "-n", "com.debug.loggerui/.MainActivity"]
            result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0 or "Error type 3" in result.stderr or "does not exist" in result.stderr:
                messagebox.showerror("错误", 
                    f"MTKlogger不存在，需要安装\n\n"
                    f"设备: {device}\n"
                    f"错误信息: {result.stderr.strip() if result.stderr else 'MTKlogger未安装'}\n\n"
                    f"请先安装MTKlogger工具后再使用此功能")
                self.status_var.set("MTKlogger不存在，需要安装")
                return
            
            # MTKlogger存在，继续执行
            self.status_var.set("MTKlogger检查通过，开始开启MTKLOG")
                
        except Exception as e:
            messagebox.showerror("错误", f"检查MTKlogger时发生错误: {e}")
            self.status_var.set("检查MTKlogger失败")
            return
        
        # 创建进度条弹框
        progress_dialog = tk.Toplevel(self.root)
        progress_dialog.title("开启MTKLOG")
        progress_dialog.geometry("400x200")
        progress_dialog.resizable(False, False)
        progress_dialog.transient(self.root)
        progress_dialog.grab_set()
        
        # 居中显示
        progress_dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        # 进度条框架
        progress_frame = ttk.Frame(progress_dialog, padding="20")
        progress_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(progress_frame, text="正在开启MTKLOG...", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # 进度条
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100, length=300)
        progress_bar.pack(pady=(0, 10))
        
        # 状态标签
        status_label = ttk.Label(progress_frame, text="准备中...", font=('Arial', 10))
        status_label.pack(pady=(0, 10))
        
        # 设备信息
        device_label = ttk.Label(progress_frame, text=f"设备: {device}", font=('Arial', 9), foreground="gray")
        device_label.pack()
        
        # 按钮框架
        button_frame = ttk.Frame(progress_frame)
        button_frame.pack(pady=(10, 0))
        
        # 确认按钮（初始状态为禁用）
        confirm_button = ttk.Button(button_frame, text="确认", state=tk.DISABLED, command=lambda: self.close_progress_dialog(progress_dialog, None, device))
        confirm_button.pack()
        
        # 更新进度条
        progress_dialog.update()
        
        try:
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
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
                if result.returncode != 0:
                    error_msg = result.stderr.strip() if result.stderr else "未知错误"
                    progress_dialog.destroy()
                    messagebox.showerror("错误", f"开启MTKLOG失败 (步骤{i}):\n{error_msg}")
                    self.status_var.set(f"开启MTKLOG失败 - 步骤{i}")
                    return
                
                # 更新进度
                progress_var.set(i * 25)
                progress_dialog.update()
                
                # 添加时间保护
                if i == 1:  # 停止logger后等待5秒
                    status_label.config(text="等待5秒...")
                    progress_dialog.update()
                    import time
                    time.sleep(5)
                elif i == 2:  # 清除日志后等待2秒
                    status_label.config(text="等待2秒...")
                    progress_dialog.update()
                    import time
                    time.sleep(2)
                elif i == 3:  # 设置缓存大小后等待1秒
                    status_label.config(text="等待1秒...")
                    progress_dialog.update()
                    import time
                    time.sleep(1)
            
            # 完成
            status_label.config(text="完成!")
            progress_var.set(100)
            progress_dialog.update()
            
            # 启用确认按钮
            confirm_button.config(state=tk.NORMAL)
            progress_dialog.update()
            
            # 保存结果信息供确认按钮使用
            progress_dialog.device = device
                
        except subprocess.TimeoutExpired:
            progress_dialog.destroy()
            messagebox.showerror("错误", "开启MTKLOG超时，请检查设备连接")
            self.status_var.set("开启MTKLOG超时")
        except FileNotFoundError:
            progress_dialog.destroy()
            messagebox.showerror("错误", "未找到adb命令，请确保Android SDK已安装并配置PATH")
            self.status_var.set("未找到adb命令")
        except Exception as e:
            progress_dialog.destroy()
            messagebox.showerror("错误", f"开启MTKLOG时发生错误: {e}")
            self.status_var.set("开启MTKLOG失败")
    
    def stop_and_export_mtklog(self):
        """停止并导出MTKLOG"""
        device = self.selected_device.get()
        if not device:
            messagebox.showerror("错误", "请先选择设备")
            return
        
        # 先检查设备连接状态
        try:
            devices_cmd = ["adb", "devices"]
            result = subprocess.run(devices_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                messagebox.showerror("错误", "检查设备连接失败")
                self.status_var.set("检查设备连接失败")
                return
            
            # 检查设备是否在列表中
            if device not in result.stdout:
                messagebox.showerror("错误", f"设备 {device} 未连接")
                self.status_var.set(f"设备 {device} 未连接")
                return
            
            # 设备连接正常，继续检查MTKlogger
            self.status_var.set(f"设备 {device} 连接正常，检查MTKlogger...")
                
        except Exception as e:
            messagebox.showerror("错误", f"检查设备连接时发生错误: {e}")
            self.status_var.set("检查设备连接失败")
            return
        
        # 检查MTKlogger是否存在
        try:
            check_cmd = ["adb", "-s", device, "shell", "am", "start", "-n", "com.debug.loggerui/.MainActivity"]
            result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0 or "Error type 3" in result.stderr or "does not exist" in result.stderr:
                messagebox.showerror("错误", 
                    f"MTKlogger不存在，需要安装\n\n"
                    f"设备: {device}\n"
                    f"错误信息: {result.stderr.strip() if result.stderr else 'MTKlogger未安装'}\n\n"
                    f"请先安装MTKlogger工具后再使用此功能")
                self.status_var.set("MTKlogger不存在，需要安装")
                return
            
            # MTKlogger存在，继续执行
            self.status_var.set("MTKlogger检查通过，开始停止并导出MTKLOG")
                
        except Exception as e:
            messagebox.showerror("错误", f"检查MTKlogger时发生错误: {e}")
            self.status_var.set("检查MTKlogger失败")
            return
        
        # 获取日志名称
        log_name = tk.simpledialog.askstring("输入日志名称", "请输入日志名称:", parent=self.root)
        if not log_name:
            return
        
        # 定义后台工作函数
        def mtklog_worker(progress_var, status_label, progress_dialog):
            import os
            import datetime
            import time
            
            # 1. 停止logger命令,加5s时间保护
            status_label.config(text="停止logger...")
            progress_var.set(20)
            progress_dialog.update()
            
            stop_cmd = ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                       "-e", "cmd_name", "stop", "--ei", "cmd_target", "-1", "-n", "com.debug.loggerui/.framework.LogReceiver"]
            
            result = subprocess.run(stop_cmd, capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                raise Exception(f"停止logger失败: {result.stderr.strip()}")
            
            # 添加5秒时间保护
            status_label.config(text="等待5秒保护时间...")
            progress_dialog.update()
            time.sleep(5)  # 在后台线程中sleep，不会阻塞UI
            
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
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
                
                if result.returncode != 0:
                    print(f"警告: {folder_name} 导出失败: {result.stderr.strip()}")
            
            # 4. 完成
            status_label.config(text="完成!")
            progress_var.set(100)
            progress_dialog.update()
            
            return {"log_folder": log_folder, "device": device}
        
        # 定义完成回调
        def on_mtklog_done(result):
            import os
            # 打开日志文件夹
            if result["log_folder"]:
                os.startfile(result["log_folder"])
            # 更新状态
            self.status_var.set(f"MTKLOG已停止并导出 - {result['device']}")
        
        # 定义错误回调
        def on_mtklog_error(error):
            messagebox.showerror("错误", f"停止并导出MTKLOG时发生错误: {error}")
            self.status_var.set("停止并导出MTKLOG失败")
        
        # 使用模态执行器
        self.run_with_modal("停止并导出MTKLOG", mtklog_worker, on_mtklog_done, on_mtklog_error)
    
    def run_with_modal(self, title, worker_fn, on_done=None, on_error=None):
        """通用的模态执行器：后台线程执行 + 局部遮罩拦截点击"""
        import threading
        
        # 禁用主窗口所有控件
        self._disable_all_widgets(self.root)
        
        # 创建局部遮罩层（仅在主窗口内部）
        mask_frame = ttk.Frame(self.root)
        mask_frame.place(x=0, y=0, relwidth=1, relheight=1)  # 覆盖整个主窗口
        mask_frame.configure(style="Mask.TFrame")  # 使用自定义样式
        
        # 创建进度对话框
        progress_dialog = tk.Toplevel(self.root)
        progress_dialog.title(title)
        progress_dialog.geometry("400x200")
        progress_dialog.resizable(False, False)
        progress_dialog.transient(self.root)
        
        # 居中显示
        progress_dialog.geometry("+%d+%d" % (
            self.root.winfo_rootx() + (self.root.winfo_width() - 400) // 2,
            self.root.winfo_rooty() + (self.root.winfo_height() - 200) // 2
        ))
        
        # 进度条框架
        progress_frame = ttk.Frame(progress_dialog, padding="20")
        progress_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(progress_frame, text=f"正在{title}...", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # 进度条
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100, length=300)
        progress_bar.pack(pady=(0, 10))
        
        # 状态标签
        status_label = ttk.Label(progress_frame, text="准备中...", font=('Arial', 10))
        status_label.pack(pady=(0, 10))
        
        # 按钮框架
        button_frame = ttk.Frame(progress_frame)
        button_frame.pack(pady=(10, 0))
        
        # 确认按钮（初始状态为禁用）
        confirm_button = ttk.Button(button_frame, text="确认", state=tk.DISABLED)
        confirm_button.pack()
        
        # 遮罩点击处理
        def on_mask_click(event):
            messagebox.showinfo("正在处理", "后台正在执行操作，请稍候...\n\n请不要关闭窗口，操作完成后会自动提示。")
        
        mask_frame.bind("<Button-1>", on_mask_click)
        
        # 更新进度条
        progress_dialog.update()
        
        # 后台线程执行
        def background_worker():
            try:
                result = worker_fn(progress_var, status_label, progress_dialog)
                # 执行成功，回到主线程
                self.root.after(0, lambda: self._finish_modal_execution(
                    mask_frame, progress_dialog, confirm_button, result, on_done, True
                ))
            except Exception as error:
                # 执行失败，回到主线程
                self.root.after(0, lambda err=error: self._finish_modal_execution(
                    mask_frame, progress_dialog, confirm_button, err, on_error, False
                ))
        
        # 启动后台线程
        thread = threading.Thread(target=background_worker, daemon=True)
        thread.start()
        
        return mask_frame, progress_dialog, confirm_button
    
    def _disable_all_widgets(self, parent):
        """禁用所有控件，并保存原始状态"""
        if not hasattr(self, '_original_widget_states'):
            self._original_widget_states = {}
        
        for child in parent.winfo_children():
            try:
                if isinstance(child, (ttk.Button, ttk.Entry, ttk.Combobox)):
                    # 保存原始状态
                    self._original_widget_states[child] = child.cget('state')
                    child.config(state=tk.DISABLED)
                elif isinstance(child, tk.Text):
                    # 保存原始状态
                    self._original_widget_states[child] = child.cget('state')
                    child.config(state=tk.DISABLED)
                # 递归处理子控件
                self._disable_all_widgets(child)
            except:
                pass
    
    def _enable_all_widgets(self, parent):
        """恢复所有控件的原始状态"""
        if not hasattr(self, '_original_widget_states'):
            return
            
        for child in parent.winfo_children():
            try:
                if isinstance(child, (ttk.Button, ttk.Entry, ttk.Combobox, tk.Text)):
                    # 恢复原始状态
                    if child in self._original_widget_states:
                        original_state = self._original_widget_states[child]
                        child.config(state=original_state)
                        del self._original_widget_states[child]
                # 递归处理子控件
                self._enable_all_widgets(child)
            except:
                pass
    
    def _finish_modal_execution(self, mask_frame, progress_dialog, confirm_button, result, callback, success):
        """完成模态执行"""
        # 更新进度条到100%
        progress_var = progress_dialog.children['!frame'].children['!progressbar'].cget('variable')
        if hasattr(progress_var, 'set'):
            progress_var.set(100)
        
        # 更新状态
        status_label = progress_dialog.children['!frame'].children['!label']
        if hasattr(status_label, 'config'):
            status_label.config(text="完成!" if success else "失败!")
        
        # 启用确认按钮
        confirm_button.config(state=tk.NORMAL)
        
        # 设置确认按钮的回调
        def on_confirm():
            # 移除遮罩
            mask_frame.destroy()
            # 重新启用所有控件
            self._enable_all_widgets(self.root)
            # 关闭进度对话框
            progress_dialog.destroy()
            # 执行回调
            if callback:
                callback(result)
        
        confirm_button.config(command=on_confirm)
    
    def close_progress_dialog(self, dialog, log_folder, device):
        """关闭进度弹框并执行后续操作"""
        import os
        # 从dialog对象中获取log_folder（如果参数为None）
        if log_folder is None and hasattr(dialog, 'log_folder'):
            log_folder = dialog.log_folder
        if device is None and hasattr(dialog, 'device'):
            device = dialog.device
            
        # 打开日志文件夹
        if log_folder:
            os.startfile(log_folder)
        # 关闭弹框
        dialog.destroy()
        # 更新状态
        if device:
            # 根据操作类型设置不同的状态信息
            if hasattr(dialog, 'operation_type') and dialog.operation_type == "adb_export":
                # ADB log导出操作
                self.status_var.set(f"ADB log已导出 - {device}")
            elif hasattr(dialog, 'log_folder'):
                # MTKLOG操作
                self.status_var.set(f"MTKLOG已停止并导出 - {device}")
            else:
                # ADB log开启操作
                self.status_var.set(f"ADB log已开启 - {device}")
    
    def delete_mtklog(self):
        """删除MTKLOG"""
        device = self.selected_device.get()
        if not device:
            messagebox.showerror("错误", "请先选择设备")
            return
        
        # 先检查设备连接状态
        try:
            devices_cmd = ["adb", "devices"]
            result = subprocess.run(devices_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                messagebox.showerror("错误", "检查设备连接失败")
                self.status_var.set("检查设备连接失败")
                return
            
            # 检查设备是否在列表中
            if device not in result.stdout:
                messagebox.showerror("错误", f"设备 {device} 未连接")
                self.status_var.set(f"设备 {device} 未连接")
                return
            
            # 设备连接正常，继续检查MTKlogger
            self.status_var.set(f"设备 {device} 连接正常，检查MTKlogger...")
                
        except Exception as e:
            messagebox.showerror("错误", f"检查设备连接时发生错误: {e}")
            self.status_var.set("检查设备连接失败")
            return
        
        # 检查MTKlogger是否存在
        try:
            check_cmd = ["adb", "-s", device, "shell", "am", "start", "-n", "com.debug.loggerui/.MainActivity"]
            result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0 or "Error type 3" in result.stderr or "does not exist" in result.stderr:
                messagebox.showerror("错误", 
                    f"MTKlogger不存在，需要安装\n\n"
                    f"设备: {device}\n"
                    f"错误信息: {result.stderr.strip() if result.stderr else 'MTKlogger未安装'}\n\n"
                    f"请先安装MTKlogger工具后再使用此功能")
                self.status_var.set("MTKlogger不存在，需要安装")
                return
            
            # MTKlogger存在，继续执行
            self.status_var.set("MTKlogger检查通过，开始删除MTKLOG")
                
        except Exception as e:
            messagebox.showerror("错误", f"检查MTKlogger时发生错误: {e}")
            self.status_var.set("检查MTKlogger失败")
            return
        
        # 创建进度条弹框
        progress_dialog = tk.Toplevel(self.root)
        progress_dialog.title("删除MTKLOG")
        progress_dialog.geometry("350x170")
        progress_dialog.resizable(False, False)
        progress_dialog.transient(self.root)
        progress_dialog.grab_set()
        
        # 居中显示
        progress_dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 75, self.root.winfo_rooty() + 75))
        
        # 进度框架
        progress_frame = ttk.Frame(progress_dialog, padding="20")
        progress_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(progress_frame, text="正在删除MTKLOG...", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # 状态标签
        status_label = ttk.Label(progress_frame, text="执行删除命令...", font=('Arial', 10))
        status_label.pack(pady=(0, 5))
        
        # 设备信息
        device_label = ttk.Label(progress_frame, text=f"设备: {device}", font=('Arial', 9), foreground="gray")
        device_label.pack()
        
        # 按钮框架
        button_frame = ttk.Frame(progress_frame)
        button_frame.pack(pady=(10, 0))
        
        # 确认按钮（初始状态为禁用）
        confirm_button = ttk.Button(button_frame, text="确认", state=tk.DISABLED, command=lambda: self.close_progress_dialog(progress_dialog, None, device))
        confirm_button.pack()
        
        progress_dialog.update()
        
        try:
            # 删除logger命令
            cmd = ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                   "-e", "cmd_name", "clear_logs_all", "--ei", "cmd_target", "0", "-n", "com.debug.loggerui/.framework.LogReceiver"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                # 更新状态
                status_label.config(text="删除完成!")
                progress_dialog.update()
                
                # 等待一下让用户看到完成状态
                import time
                time.sleep(1)
                
                # 启用确认按钮
                confirm_button.config(state=tk.NORMAL)
                progress_dialog.update()
                
                # 保存结果信息供确认按钮使用
                progress_dialog.device = device
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                progress_dialog.destroy()
                messagebox.showerror("错误", f"删除MTKLOG失败:\n{error_msg}")
                self.status_var.set("删除MTKLOG失败")
                
        except subprocess.TimeoutExpired:
            progress_dialog.destroy()
            messagebox.showerror("错误", "删除MTKLOG超时，请检查设备连接")
            self.status_var.set("删除MTKLOG超时")
        except FileNotFoundError:
            progress_dialog.destroy()
            messagebox.showerror("错误", "未找到adb命令，请确保Android SDK已安装并配置PATH")
            self.status_var.set("未找到adb命令")
        except Exception as e:
            progress_dialog.destroy()
            messagebox.showerror("错误", f"删除MTKLOG时发生错误: {e}")
            self.status_var.set("删除MTKLOG失败")
    
    def set_sd_mode(self):
        """设置SD模式"""
        device = self.selected_device.get()
        if not device:
            messagebox.showerror("错误", "请先选择设备")
            return
        
        # 先检查设备连接状态
        try:
            devices_cmd = ["adb", "devices"]
            result = subprocess.run(devices_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                messagebox.showerror("错误", "检查设备连接失败")
                self.status_var.set("检查设备连接失败")
                return
            
            # 检查设备是否在列表中
            if device not in result.stdout:
                messagebox.showerror("错误", f"设备 {device} 未连接")
                self.status_var.set(f"设备 {device} 未连接")
                return
            
            # 设备连接正常，继续检查MTKlogger
            self.status_var.set(f"设备 {device} 连接正常，检查MTKlogger...")
                
        except Exception as e:
            messagebox.showerror("错误", f"检查设备连接时发生错误: {e}")
            self.status_var.set("检查设备连接失败")
            return
        
        # 检查MTKlogger是否存在
        try:
            check_cmd = ["adb", "-s", device, "shell", "am", "start", "-n", "com.debug.loggerui/.MainActivity"]
            result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0 or "Error type 3" in result.stderr or "does not exist" in result.stderr:
                messagebox.showerror("错误", 
                    f"MTKlogger不存在，需要安装\n\n"
                    f"设备: {device}\n"
                    f"错误信息: {result.stderr.strip() if result.stderr else 'MTKlogger未安装'}\n\n"
                    f"请先安装MTKlogger工具后再使用此功能")
                self.status_var.set("MTKlogger不存在，需要安装")
                return
            
            # MTKlogger存在，继续执行
            self.status_var.set("MTKlogger检查通过，开始设置SD模式")
                
        except Exception as e:
            messagebox.showerror("错误", f"检查MTKlogger时发生错误: {e}")
            self.status_var.set("检查MTKlogger失败")
            return
        
        try:
            cmd = ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                   "-e", "cmd_name", "switch_modem_log_mode_2", "--ei", "cmd_target", "1", "-n", "com.debug.loggerui/.framework.LogReceiver"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                messagebox.showinfo("成功", f"已设置为SD模式 \n(设备: {device})")
                self.status_var.set(f"已设置为SD模式 - {device}")
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                messagebox.showerror("错误", f"设置SD模式失败:\n{error_msg}")
                self.status_var.set("设置SD模式失败")
                
        except subprocess.TimeoutExpired:
            messagebox.showerror("错误", "设置SD模式超时，请检查设备连接")
            self.status_var.set("设置SD模式超时")
        except FileNotFoundError:
            messagebox.showerror("错误", "未找到adb命令，请确保Android SDK已安装并配置PATH")
            self.status_var.set("未找到adb命令")
        except Exception as e:
            messagebox.showerror("错误", f"设置SD模式时发生错误: {e}")
            self.status_var.set("设置SD模式失败")
    
    def set_usb_mode(self):
        """设置USB模式"""
        device = self.selected_device.get()
        if not device:
            messagebox.showerror("错误", "请先选择设备")
            return
        
        # 先检查设备连接状态
        try:
            devices_cmd = ["adb", "devices"]
            result = subprocess.run(devices_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                messagebox.showerror("错误", "检查设备连接失败")
                self.status_var.set("检查设备连接失败")
                return
            
            # 检查设备是否在列表中
            if device not in result.stdout:
                messagebox.showerror("错误", f"设备 {device} 未连接")
                self.status_var.set(f"设备 {device} 未连接")
                return
            
            # 设备连接正常，继续检查MTKlogger
            self.status_var.set(f"设备 {device} 连接正常，检查MTKlogger...")
                
        except Exception as e:
            messagebox.showerror("错误", f"检查设备连接时发生错误: {e}")
            self.status_var.set("检查设备连接失败")
            return
        
        # 检查MTKlogger是否存在
        try:
            check_cmd = ["adb", "-s", device, "shell", "am", "start", "-n", "com.debug.loggerui/.MainActivity"]
            result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0 or "Error type 3" in result.stderr or "does not exist" in result.stderr:
                messagebox.showerror("错误", 
                    f"MTKlogger不存在，需要安装\n\n"
                    f"设备: {device}\n"
                    f"错误信息: {result.stderr.strip() if result.stderr else 'MTKlogger未安装'}\n\n"
                    f"请先安装MTKlogger工具后再使用此功能")
                self.status_var.set("MTKlogger不存在，需要安装")
                return
            
            # MTKlogger存在，继续执行
            self.status_var.set("MTKlogger检查通过，开始设置USB模式")
                
        except Exception as e:
            messagebox.showerror("错误", f"检查MTKlogger时发生错误: {e}")
            self.status_var.set("检查MTKlogger失败")
            return
        
        try:
            cmd = ["adb", "-s", device, "shell", "am", "broadcast", "-a", "com.debug.loggerui.ADB_CMD", 
                   "-e", "cmd_name", "switch_modem_log_mode_1", "--ei", "cmd_target", "1", "-n", "com.debug.loggerui/.framework.LogReceiver"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                messagebox.showinfo("成功", f"已设置为USB模式 \n(设备: {device})")
                self.status_var.set(f"已设置为USB模式 - {device}")
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                messagebox.showerror("错误", f"设置USB模式失败:\n{error_msg}")
                self.status_var.set("设置USB模式失败")
                
        except subprocess.TimeoutExpired:
            messagebox.showerror("错误", "设置USB模式超时，请检查设备连接")
            self.status_var.set("设置USB模式超时")
        except FileNotFoundError:
            messagebox.showerror("错误", "未找到adb命令，请确保Android SDK已安装并配置PATH")
            self.status_var.set("未找到adb命令")
        except Exception as e:
            messagebox.showerror("错误", f"设置USB模式时发生错误: {e}")
            self.status_var.set("设置USB模式失败")
    
    def start_adblog(self):
        """开启adb log"""
        device = self.selected_device.get()
        if not device:
            messagebox.showerror("错误", "请先选择设备")
            return
        
        # 先检查设备连接状态
        try:
            devices_cmd = ["adb", "devices"]
            result = subprocess.run(devices_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                messagebox.showerror("错误", "检查设备连接失败")
                self.status_var.set("检查设备连接失败")
                return
            
            # 检查设备是否在列表中
            if device not in result.stdout:
                messagebox.showerror("错误", f"设备 {device} 未连接")
                self.status_var.set(f"设备 {device} 未连接")
                return
            
            # 设备连接正常
            self.status_var.set(f"设备 {device} 连接正常，准备开启ADB log")
                
        except Exception as e:
            messagebox.showerror("错误", f"检查设备连接时发生错误: {e}")
            self.status_var.set("检查设备连接失败")
            return
        
        # 检查/data/local/tmp是否有txt文件
        try:
            ls_cmd = ["adb", "-s", device, "shell", "ls", "/data/local/tmp/*.txt"]
            result = subprocess.run(ls_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0 and result.stdout.strip():
                # 有txt文件，询问用户是否清除
                txt_files = result.stdout.strip().split('\n')
                file_count = len([f for f in txt_files if f.strip()])
                
                # 显示文件名列表（最多显示5个）
                file_list = [os.path.basename(f.strip()) for f in txt_files if f.strip()][:5]
                file_display = '\n'.join(file_list)
                if file_count > 5:
                    file_display += '\n...'
                
                response = messagebox.askyesno("发现旧log文件", 
                    f"在设备 {device} 的 /data/local/tmp 目录中发现 {file_count} 个txt文件:\n\n"
                    f"{file_display}\n\n"
                    "是否清除这些旧log文件？\n\n"
                    "选择'是'：清除所有旧文件，然后输入新文件名\n"
                    "选择'否'：保留旧文件，然后输入新文件名")
                
                if response:
                    # 用户选择清除，只删除txt文件
                    self.status_var.set(f"正在清除设备 {device} 的旧log文件...")
                    
                    # 只删除txt文件，不影响其他文件
                    rm_cmd = ["adb", "-s", device, "shell", "rm", "-f", "/data/local/tmp/*.txt"]
                    result = subprocess.run(rm_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
                    
                    if result.returncode == 0:
                        self.status_var.set(f"已清除设备 {device} 的旧log文件")
                    else:
                        print(f"警告: 清除旧文件失败: {result.stderr.strip()}")
                else:
                    # 用户选择保留
                    self.status_var.set(f"保留设备 {device} 的旧log文件")
                    
        except Exception as e:
            print(f"检查旧log文件时发生错误: {e}")
            # 继续执行，不中断流程
        
        # 获取log名称
        log_name = tk.simpledialog.askstring("输入log名称", 
            "请输入log名称:\n\n注意: 名称中不能包含空格，空格将被替换为下划线", 
            parent=self.root)
        if not log_name:
            return
        
        # 处理log名称：替换空格为下划线
        log_name = log_name.replace(" ", "_")
        
        # 定义后台工作函数
        def adblog_start_worker(progress_var, status_label, progress_dialog):
            import time
            import datetime
            
            # 1. 生成带时间的log文件名
            status_label.config(text="生成log文件名...")
            progress_var.set(20)
            progress_dialog.update()
            
            current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"{log_name}_{current_time}.txt"
            log_path = f"/data/local/tmp/{log_filename}"
            
            # 2. 启动logcat进程
            status_label.config(text="启动logcat进程...")
            progress_var.set(50)
            progress_dialog.update()
            
            cmd = ["adb", "-s", device, "shell", "nohup", "logcat", "-v", "time", "-b", "all", "-f", log_path, ">", "/dev/null", "2>&1", "&"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                raise Exception(f"启动logcat失败: {result.stderr.strip()}")
            
            # 3. 检查logcat进程是否存在
            status_label.config(text="检查logcat进程...")
            progress_var.set(80)
            progress_dialog.update()
            
            cmd3 = ["adb", "-s", device, "shell", "ps", "-A"]
            result = subprocess.run(cmd3, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                raise Exception(f"检查进程失败: {result.stderr.strip()}")
            
            # 检查输出中是否包含logcat
            if "logcat" not in result.stdout:
                raise Exception("logcat进程不存在，启动失败")
            
            # 完成
            status_label.config(text="完成!")
            progress_var.set(100)
            progress_dialog.update()
            
            return {"device": device, "log_filename": log_filename, "log_path": log_path}
        
        # 定义完成回调
        def on_adblog_start_done(result):
            # 更新状态
            self.status_var.set(f"ADB log已开启 - {result['device']} - {result['log_filename']}")
        
        # 定义错误回调
        def on_adblog_start_error(error):
            messagebox.showerror("错误", f"开启ADB log时发生错误: {error}")
            self.status_var.set("开启ADB log失败")
        
        # 使用模态执行器
        self.run_with_modal("开启ADB Log", adblog_start_worker, on_adblog_start_done, on_adblog_start_error)
    
    def export_adblog(self):
        """停止adb log并导出"""
        device = self.selected_device.get()
        if not device:
            messagebox.showerror("错误", "请先选择设备")
            return
        
        # 先检查设备连接状态
        try:
            devices_cmd = ["adb", "devices"]
            result = subprocess.run(devices_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                messagebox.showerror("错误", "检查设备连接失败")
                self.status_var.set("检查设备连接失败")
                return
            
            # 检查设备是否在列表中
            if device not in result.stdout:
                messagebox.showerror("错误", f"设备 {device} 未连接")
                self.status_var.set(f"设备 {device} 未连接")
                return
            
            # 设备连接正常，继续执行导出流程
            self.status_var.set(f"设备 {device} 连接正常，开始导出ADB log...")
                
        except Exception as e:
            messagebox.showerror("错误", f"检查设备连接时发生错误: {e}")
            self.status_var.set("检查设备连接失败")
            return
        
        # 定义后台工作函数
        def adblog_worker(progress_var, status_label, progress_dialog):
            import os
            import datetime
            import time
            
            # 1. 检查设备连接状态
            status_label.config(text="检查设备连接状态...")
            progress_var.set(10)
            progress_dialog.update()
            
            devices_cmd = ["adb", "devices"]
            result = subprocess.run(devices_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                raise Exception("检查设备连接失败")
            
            # 检查设备是否在列表中
            if device not in result.stdout:
                raise Exception(f"设备 {device} 未连接")
            
            # 2. 检查logcat进程是否存在
            status_label.config(text="检查logcat进程...")
            progress_var.set(25)
            progress_dialog.update()
            
            ps_cmd = ["adb", "-s", device, "shell", "ps", "-A"]
            result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                raise Exception(f"检查进程失败: {result.stderr.strip()}")
            
            # 检查输出中是否包含logcat
            if "logcat" not in result.stdout:
                raise Exception("logcat进程不存在，log抓取异常")
            
            # 3. 精确杀掉nohup启动的logcat进程
            status_label.config(text="停止nohup logcat进程...")
            progress_var.set(40)
            progress_dialog.update()
            
            # 查找nohup启动的logcat进程
            ps_cmd = ["adb", "-s", device, "shell", "ps", "-ef"]
            result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                # 解析进程列表，找到包含/data/local/tmp/的logcat进程
                lines = result.stdout.strip().split('\n')
                nohup_pids = []
                
                for line in lines:
                    if 'logcat' in line and '/data/local/tmp/' in line:
                        # 提取PID（第二列）
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                pid = int(parts[1])
                                nohup_pids.append(pid)
                                print(f"找到nohup logcat进程 PID: {pid}")
                            except ValueError:
                                continue
                
                # 杀掉找到的nohup logcat进程
                if nohup_pids:
                    for pid in nohup_pids:
                        kill_cmd = ["adb", "-s", device, "shell", "kill", str(pid)]
                        kill_result = subprocess.run(kill_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
                        if kill_result.returncode == 0:
                            print(f"成功停止nohup logcat进程 PID: {pid}")
                        else:
                            print(f"停止进程 PID {pid} 失败: {kill_result.stderr.strip()}")
                else:
                    print("未找到nohup启动的logcat进程")
            else:
                print(f"获取进程列表失败: {result.stderr.strip()}")
            
            # 4. 创建日志目录
            status_label.config(text="创建日志目录...")
            progress_var.set(50)
            progress_dialog.update()
            
            curredate = datetime.datetime.now().strftime("%Y%m%d")
            log_dir = f"c:\\log\\{curredate}"
            
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # 5. 导出log文件
            status_label.config(text="导出log文件...")
            progress_var.set(70)
            progress_dialog.update()
            
            # 创建logcat目录
            logcat_dir = os.path.join(log_dir, "logcat")
            if not os.path.exists(logcat_dir):
                os.makedirs(logcat_dir)
            
            # 先获取设备上的所有txt文件列表
            ls_cmd = ["adb", "-s", device, "shell", "ls", "/data/local/tmp/*.txt"]
            result = subprocess.run(ls_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0 and result.stdout.strip():
                # 有txt文件，逐个导出
                txt_files = result.stdout.strip().split('\n')
                exported_count = 0
                for txt_file in txt_files:
                    if txt_file.strip():
                        filename = os.path.basename(txt_file.strip())
                        pull_cmd = ["adb", "-s", device, "pull", txt_file.strip(), os.path.join(logcat_dir, filename)]
                        result = subprocess.run(pull_cmd, capture_output=True, text=True, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
                        
                        if result.returncode == 0:
                            exported_count += 1
                            print(f"成功导出: {filename}")
                        else:
                            print(f"警告: {filename} 导出失败: {result.stderr.strip()}")
                
                if exported_count == 0:
                    raise Exception("没有成功导出任何log文件")
            else:
                # 没有找到txt文件，尝试导出整个tmp目录
                status_label.config(text="未找到txt文件，导出整个tmp目录...")
                progress_dialog.update()
                
                pull_cmd = ["adb", "-s", device, "pull", "/data/local/tmp/", logcat_dir]
                result = subprocess.run(pull_cmd, capture_output=True, text=True, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
                
                if result.returncode != 0:
                    raise Exception(f"导出tmp目录失败: {result.stderr.strip()}")
            
            # 6. 完成
            status_label.config(text="完成!")
            progress_var.set(100)
            progress_dialog.update()
            
            return {"log_folder": logcat_dir, "device": device, "operation_type": "adb_export"}
        
        # 定义完成回调
        def on_adblog_done(result):
            import os
            # 打开日志文件夹
            if result["log_folder"]:
                os.startfile(result["log_folder"])
            # 更新状态
            self.status_var.set(f"ADB log已导出 - {result['device']}")
        
        # 定义错误回调
        def on_adblog_error(error):
            if "logcat进程不存在" in str(error):
                messagebox.showerror("错误", "logcat进程不存在，log抓取异常")
                self.status_var.set("logcat进程不存在")
            else:
                messagebox.showerror("错误", f"停止并导出ADB log时发生错误: {error}")
                self.status_var.set("停止并导出ADB log失败")
        
        # 使用模态执行器
        self.run_with_modal("停止并导出ADB Log", adblog_worker, on_adblog_done, on_adblog_error)
    
    def install_mtklogger(self):
        """安装MTKLOGGER"""
        # 检查是否有设备连接
        device = self.selected_device.get()
        if not device or device in ["无设备", "检测失败", "检测超时", "adb未安装", "检测错误"]:
            messagebox.showerror("错误", "请先连接设备并选择有效设备")
            return
        
        # 检查设备连接状态
        try:
            devices_cmd = ["adb", "devices"]
            result = subprocess.run(devices_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                messagebox.showerror("错误", "检查设备连接失败")
                return
            
            # 检查设备是否在列表中
            if device not in result.stdout:
                messagebox.showerror("错误", f"设备 {device} 未连接")
                return
            
            # 设备连接正常
            self.status_var.set(f"设备 {device} 连接正常，准备安装MTKLOGGER")
                
        except Exception as e:
            messagebox.showerror("错误", f"检查设备连接时发生错误: {e}")
            return
        
        # 选择APK文件
        apk_file = filedialog.askopenfilename(
            title="选择MTKLOGGER APK文件",
            filetypes=[("APK文件", "*.apk"), ("所有文件", "*.*")],
            parent=self.root
        )
        
        if not apk_file:
            return
        
        # 定义后台工作函数
        def install_worker(progress_var, status_label, progress_dialog):
            import time
            
            # 1. 卸载旧版本（如果存在）
            status_label.config(text="检查并卸载旧版本...")
            progress_var.set(20)
            progress_dialog.update()
            
            uninstall_cmd = ["adb", "-s", device, "uninstall", "com.debug.loggerui"]
            subprocess.run(uninstall_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            
            # 2. 安装新版本
            status_label.config(text="安装MTKLOGGER...")
            progress_var.set(50)
            progress_dialog.update()
            
            install_cmd = ["adb", "-s", device, "install", apk_file]
            result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                raise Exception(f"安装失败: {error_msg}")
            
            # 检查安装结果
            if "Success" not in result.stdout and "success" not in result.stdout.lower():
                raise Exception(f"安装可能失败: {result.stdout.strip()}")
            
            # 3. 启动MTKLOGGER
            status_label.config(text="启动MTKLOGGER...")
            progress_var.set(80)
            progress_dialog.update()
            
            start_cmd = ["adb", "-s", device, "shell", "am", "start", "-n", "com.debug.loggerui/.MainActivity"]
            result = subprocess.run(start_cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            
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
            self.status_var.set(f"MTKLOGGER安装成功 - {result['device']}")
        
        # 定义错误回调
        def on_install_error(error):
            messagebox.showerror("错误", f"安装MTKLOGGER时发生错误: {error}")
            self.status_var.set("安装MTKLOGGER失败")
        
        # 使用模态执行器
        self.run_with_modal("安装MTKLOGGER", install_worker, on_install_done, on_install_error)

def main():
    """主函数"""
    root = tk.Tk()
    app = LogcatFilterApp(root)
    
    # 设置窗口关闭事件
    def on_closing():
        if app.is_running:
            app.stop_filtering()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
