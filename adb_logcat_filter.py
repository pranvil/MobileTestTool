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
import sys
from datetime import datetime
import queue

class LogcatFilterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ADB Logcat 关键字过滤工具")
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
        self.queue_size_threshold = 100  # 队列大小阈值
        
        # 自适应处理参数
        self.adaptive_params = {
            'base_batch_size': 50,      # 基础批次大小
            'max_batch_size': 200,      # 最大批次大小
            'base_interval': 50,         # 基础处理间隔(ms)
            'min_interval': 10,          # 最小处理间隔(ms)
            'high_load_threshold': 100,  # 高负荷阈值
            'medium_load_threshold': 50, # 中等负荷阈值
            'max_display_lines': 1000,   # 最大显示行数
            'trim_threshold': 1200       # 裁剪触发阈值
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
        
        # 设置默认值
        self.use_regex.set(True)
        self.case_sensitive.set(False)
        self.color_highlight.set(True)
        
        self.setup_ui()
        self.setup_log_display()
        self.setup_menu()
        
        # 启动日志队列处理
        self.process_log_queue()
    
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
        
        # 关键字输入
        ttk.Label(control_frame, text="关键字:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        keyword_entry = ttk.Entry(control_frame, textvariable=self.filter_keyword, width=30)
        keyword_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        keyword_entry.bind('<Return>', lambda e: self.start_filtering())
        
        # 选项复选框
        options_frame = ttk.Frame(control_frame)
        options_frame.grid(row=0, column=2, sticky=tk.W)
        
        ttk.Checkbutton(options_frame, text="正则表达式", variable=self.use_regex).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(options_frame, text="区分大小写", variable=self.case_sensitive).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(options_frame, text="彩色高亮", variable=self.color_highlight).pack(side=tk.LEFT)
        
        # 按钮
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=0, column=3, sticky=tk.E)
        
        self.start_button = ttk.Button(button_frame, text="开始过滤", command=self.start_filtering)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(button_frame, text="停止", command=self.stop_filtering, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(button_frame, text="清空日志", command=self.clear_logs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="清除缓存", command=self.clear_device_logs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="保存日志", command=self.save_logs).pack(side=tk.LEFT)
        
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
        tools_menu.add_command(label="清除设备缓存", command=self.clear_device_logs)
        tools_menu.add_command(label="保存日志", command=self.save_logs)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)
    
    def show_about(self):
        """显示关于对话框"""
        messagebox.showinfo("关于", 
            "ADB Logcat 关键字过滤工具\n\n"
            "版本: 1.0\n"
            "功能: 实时过滤Android设备日志\n\n"
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
        
        if self.is_running:
            messagebox.showinfo("提示", "过滤已在运行中")
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
            # 构建adb logcat命令
            cmd = ["adb", "logcat", "-v", "time"]
            
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
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            full_line = f"[{timestamp}] {line.rstrip()}\n"
            
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
        """高效的行数裁剪机制 - 第三阶段优化"""
        # 维护行计数器
        if not hasattr(self, '_line_count'):
            self._line_count = 0
        
        self._line_count += added_lines
        
        # 使用更高的阈值触发裁剪，减少频繁操作
        if self._line_count > self.adaptive_params['trim_threshold']:
            # 使用高效的文本索引删除，避免get().split()统计
            try:
                # 获取当前总行数（使用index方法更高效）
                current_lines = int(self.log_text.index('end-1c').split('.')[0])
                
                if current_lines > self.adaptive_params['max_display_lines']:
                    # 计算需要删除的行数
                    lines_to_delete = current_lines - self.adaptive_params['max_display_lines']
                    
                    # 使用文本索引一次性删除超出的行
                    # 删除从第1行到第(lines_to_delete)行
                    self.log_text.delete("1.0", f"{lines_to_delete + 1}.0")
                    
                    # 更新缓存
                    self.performance_cache['last_line_count'] = self.adaptive_params['max_display_lines']
                    
                    # 重置计数器
                    self._line_count = 0
                    
            except Exception as e:
                # 如果出现异常，回退到原来的方法
                lines_count = len(self.log_text.get("1.0", tk.END).split('\n'))
                if lines_count > self.adaptive_params['max_display_lines']:
                    self.log_text.delete("1.0", f"{lines_count - self.adaptive_params['max_display_lines']}.0")
                self._line_count = 0
                self.performance_cache['last_line_count'] = self.adaptive_params['max_display_lines']
    
    def add_log_line(self, line):
        """添加日志行到显示区域"""
        self.log_text.config(state=tk.NORMAL)
        
        # 移动到末尾
        self.log_text.see(tk.END)
        
        # 添加时间戳
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        full_line = f"[{timestamp}] {line.rstrip()}"
        
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
        # 更新缓存计数器
        self.performance_cache['last_memory_check'] += 1
        
        # 只在达到缓存更新间隔时才重新计算
        if self.performance_cache['last_memory_check'] >= self.performance_cache['cache_update_interval']:
            try:
                # 计算当前显示的行数
                current_display_lines = int(self.log_text.index('end-1c').split('.')[0])
                
                # 计算内存使用情况（估算）
                text_content_length = len(self.log_text.get("1.0", tk.END))
                memory_mb = text_content_length / (1024 * 1024)  # 转换为MB
                
                # 更新缓存
                self.performance_cache['last_line_count'] = current_display_lines
                self.performance_cache['last_memory_mb'] = memory_mb
                self.performance_cache['last_memory_check'] = 0
                
                return current_display_lines, memory_mb
                
            except Exception:
                # 如果出现异常，返回缓存值
                return self.performance_cache['last_line_count'], self.performance_cache['last_memory_mb']
        else:
            # 使用缓存值
            return self.performance_cache['last_line_count'], self.performance_cache['last_memory_mb']
    
    def stop_filtering(self):
        """停止过滤"""
        self.is_running = False
        if self.log_process:
            self.log_process.terminate()
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
