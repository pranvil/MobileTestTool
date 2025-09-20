#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI管理模块
负责用户界面的创建和管理
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import subprocess
import os
import json

class UIManager:
    def __init__(self, root, app_instance):
        self.root = root
        self.app = app_instance
        
        
        self.setup_ui()
        self.setup_log_display()
        self.setup_menu()
        self.setup_window_management()
    
    def _ui_state_path(self):
        """获取UI状态文件路径"""
        base = os.path.expanduser("~/.netui")
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, "ui_state.json")
    
    def load_ui_state(self):
        """加载UI状态"""
        p = self._ui_state_path()
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    
    def save_ui_state(self, state):
        """保存UI状态"""
        p = self._ui_state_path()
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def restore_sash_position(self):
        """恢复分割条位置"""
        try:
            state = self.load_ui_state()
            if "sashpos_main" in state:
                self.main_paned.sash_place(0, 0, state["sashpos_main"])
            else:
                # 默认位置
                self.main_paned.sash_place(0, 0, 140)
        except Exception as e:
            print(f"恢复分割条位置失败: {e}")
            # 使用默认位置
            try:
                self.main_paned.sash_place(0, 0, 140)
            except:
                pass
    
    def save_sash_position(self):
        """保存分割条位置"""
        try:
            state = self.load_ui_state()
            x, y = self.main_paned.sash_coord(0)
            state["sashpos_main"] = y
            self.save_ui_state(state)
        except Exception as e:
            print(f"保存分割条位置失败: {e}")
    
    def reset_sash_position(self, event=None):
        """重置分割条位置到默认值"""
        try:
            self.main_paned.sash_place(0, 0, 140)
        except Exception as e:
            print(f"重置分割条位置失败: {e}")
    
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=1)
        
        # 创建可分割的主面板 - 使用tk.PanedWindow支持minsize
        self.main_paned = tk.PanedWindow(self.main_frame, orient=tk.VERTICAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建Tab控件容器
        self.tab_container = ttk.Frame(self.main_paned)
        self.main_paned.add(self.tab_container, minsize=72)
        
        # 创建Tab控件
        self.notebook = ttk.Notebook(self.tab_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 绑定Tab切换事件
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # 绑定窗口大小变化事件
        self.root.bind("<Configure>", self.on_window_configure)
        
        # 创建各个Tab页面
        self.setup_device_control_tab()
        self.setup_log_filter_tab()
        self.setup_network_info_tab()
        self.setup_tmo_cc_tab()
        self.setup_tmo_echolocate_tab()
        
        # 创建日志显示容器作为第二个面板
        self.log_container = ttk.Frame(self.main_paned)
        self.main_paned.add(self.log_container, minsize=120)
        
        # 配置日志容器
        self.log_container.grid_rowconfigure(0, weight=1)
        self.log_container.grid_columnconfigure(0, weight=1)
        
        # 初始化时检查第一个Tab的滚动条
        self.root.after(200, self.check_current_tab_scrollbar)
        
        # 恢复分割条位置
        self.root.after_idle(self.restore_sash_position)
        
        # 绑定双击重置分割条位置
        self.main_paned.bind("<Double-Button-1>", self.reset_sash_position)
    
    def setup_device_control_tab(self):
        """设置设备控制Tab页面"""
        # 创建设备控制Tab
        device_tab = ttk.Frame(self.notebook)
        self.notebook.add(device_tab, text="设备控制")
        
        # 创建滚动容器
        device_container = ttk.Frame(device_tab)
        device_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        device_container.columnconfigure(0, weight=1)
        
        # 创建水平滚动的Canvas
        canvas = tk.Canvas(device_container, height=30, highlightthickness=0)
        scrollbar = ttk.Scrollbar(device_container, orient="horizontal", command=canvas.xview)
        scrollable_frame = ttk.Frame(canvas)
        
        # 配置滚动
        def update_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # 检查是否需要滚动条
            self.update_scrollbar_visibility(canvas, scrollbar, scrollable_frame)
        
        scrollable_frame.bind("<Configure>", update_scroll_region)
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(xscrollcommand=scrollbar.set)
        
        # 布局Canvas和Scrollbar
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 0), pady=(2, 0))
        scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 0), pady=(1, 2))
        
        # 绑定鼠标滚轮事件
        canvas.bind("<MouseWheel>", lambda e: canvas.xview_scroll(int(-1 * (e.delta / 120)), "units"))
        
        # 设备控制行
        device_row = scrollable_frame
        
        # 设备选择
        ttk.Label(device_row, text="设备:").pack(side=tk.LEFT, padx=(0, 5))
        self.device_combo = ttk.Combobox(device_row, textvariable=self.app.selected_device, width=18, state="readonly")
        self.device_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(device_row, text="刷新设备", command=self.app.refresh_devices).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(device_row, text="截图", command=self.app.take_screenshot).pack(side=tk.LEFT, padx=(0, 5))
        
        # 录制按钮
        self.record_button = ttk.Button(device_row, text="开始录制", command=self.app.toggle_recording)
        self.record_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # MTKLOG控制
        ttk.Label(device_row, text="MTKLOG:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.start_mtklog_button = ttk.Button(device_row, text="开启", command=self.app.start_mtklog)
        self.start_mtklog_button.pack(side=tk.LEFT, padx=(0, 3))
        
        self.stop_export_mtklog_button = ttk.Button(device_row, text="停止&导出", command=self.app.stop_and_export_mtklog)
        self.stop_export_mtklog_button.pack(side=tk.LEFT, padx=(0, 3))
        
        self.delete_mtklog_button = ttk.Button(device_row, text="删除", command=self.app.delete_mtklog)
        self.delete_mtklog_button.pack(side=tk.LEFT, padx=(0, 3))
        
        self.sd_mode_button = ttk.Button(device_row, text="SD模式", command=self.app.set_sd_mode)
        self.sd_mode_button.pack(side=tk.LEFT, padx=(0, 3))
        
        self.usb_mode_button = ttk.Button(device_row, text="USB模式", command=self.app.set_usb_mode)
        self.usb_mode_button.pack(side=tk.LEFT, padx=(0, 10))
        
        
        # Telephony控制
        ttk.Button(device_row, text="Telephony", command=self.app.enable_telephony).pack(side=tk.LEFT)
        
        # 存储Canvas和滚动条引用，用于后续检查
        self.device_canvas = canvas
        self.device_scrollbar = scrollbar
        self.device_scrollable_frame = scrollable_frame
    
    def setup_log_filter_tab(self):
        """设置日志过滤Tab页面"""
        # 创建日志过滤Tab
        filter_tab = ttk.Frame(self.notebook)
        self.notebook.add(filter_tab, text="Log过滤")
        
        # 创建滚动容器
        filter_container = ttk.Frame(filter_tab)
        filter_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        filter_container.columnconfigure(0, weight=1)
        
        # 创建水平滚动的Canvas
        canvas = tk.Canvas(filter_container, height=30, highlightthickness=0)
        scrollbar = ttk.Scrollbar(filter_container, orient="horizontal", command=canvas.xview)
        scrollable_frame = ttk.Frame(canvas)
        
        # 配置滚动
        def update_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # 检查是否需要滚动条
            self.update_scrollbar_visibility(canvas, scrollbar, scrollable_frame)
        
        scrollable_frame.bind("<Configure>", update_scroll_region)
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(xscrollcommand=scrollbar.set)
        
        # 布局Canvas和Scrollbar
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 0), pady=(2, 0))
        scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 0), pady=(1, 2))
        
        # 绑定鼠标滚轮事件
        canvas.bind("<MouseWheel>", lambda e: canvas.xview_scroll(int(-1 * (e.delta / 120)), "units"))
        
        # 日志过滤行
        filter_row = scrollable_frame
        
        # 关键字输入
        ttk.Label(filter_row, text="关键字:").pack(side=tk.LEFT, padx=(0, 5))
        keyword_entry = ttk.Entry(filter_row, textvariable=self.app.filter_keyword, width=20)
        keyword_entry.pack(side=tk.LEFT, padx=(0, 10))
        keyword_entry.bind('<Return>', lambda e: self.app.start_filtering())
        
        # 选项复选框
        ttk.Checkbutton(filter_row, text="正则表达式", variable=self.app.use_regex).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Checkbutton(filter_row, text="区分大小写", variable=self.app.case_sensitive).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Checkbutton(filter_row, text="彩色高亮", variable=self.app.color_highlight).pack(side=tk.LEFT, padx=(0, 10))
        
        # 主要操作按钮（动态按钮）
        self.filter_button = ttk.Button(filter_row, text="开始过滤", command=self.toggle_filtering)
        self.filter_button.pack(side=tk.LEFT, padx=(0, 10))

        
        # 常用操作按钮
        ttk.Button(filter_row, text="加载log关键字", command=self.load_log_keywords).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(filter_row, text="清空日志", command=self.app.clear_logs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(filter_row, text="清除缓存", command=self.app.clear_device_logs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(filter_row, text="设置行数", command=self.app.show_display_lines_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(filter_row, text="保存日志", command=self.app.save_logs).pack(side=tk.LEFT)
        
        # ADB Log控制
        ttk.Label(filter_row, text="ADB Log:").pack(side=tk.LEFT, padx=(10, 5))
        
        self.start_adblog_button = ttk.Button(filter_row, text="开启", command=self.app.start_adblog)
        self.start_adblog_button.pack(side=tk.LEFT, padx=(0, 3))
        
        self.export_adblog_button = ttk.Button(filter_row, text="导出", command=self.app.export_adblog)
        self.export_adblog_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Google日志控制
        ttk.Label(filter_row, text="Google日志:").pack(side=tk.LEFT, padx=(10, 5))
        
        self.google_log_button = ttk.Button(filter_row, text="Google日志", command=self.toggle_google_log)
        self.google_log_button.pack(side=tk.LEFT, padx=(0, 10))
                
        # 存储Canvas和滚动条引用，用于后续检查
        self.filter_canvas = canvas
        self.filter_scrollbar = scrollbar
        self.filter_scrollable_frame = scrollable_frame
    
    def setup_network_info_tab(self):
        """设置网络信息Tab页面"""
        # 创建网络信息Tab
        network_tab = ttk.Frame(self.notebook)
        self.notebook.add(network_tab, text="网络信息")
        
        # 创建主容器
        network_container = ttk.Frame(network_tab)
        network_container.pack(fill=tk.X, expand=False, padx=5, pady=3)
        network_container.columnconfigure(1, weight=1)
        network_container.rowconfigure(0, weight=0)
        
        # 左侧控制面板 - 更紧凑
        control_frame = ttk.LabelFrame(network_container, text="控制", padding="5")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        control_frame.columnconfigure(0, weight=1)
        
        # 开始按钮
        self.network_start_button = ttk.Button(control_frame, text="开始", command=self.toggle_network_info)
        self.network_start_button.pack(fill=tk.X, pady=(0, 5))
        
        # 状态标签
        self.network_status_label = ttk.Label(control_frame, text="未启动", foreground="gray", font=('Arial', 9))
        self.network_status_label.pack()
        
        # 右侧信息显示区域 - 更紧凑
        info_frame = ttk.LabelFrame(network_container, text="网络信息", padding="1")
        info_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        info_frame.columnconfigure(0, weight=1)
        
        # 网络信息显示框架
        self.network_info_frame = ttk.Frame(info_frame)
        self.network_info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.network_info_frame.columnconfigure(0, weight=1)
        
        # 初始显示提示信息
        initial_label = ttk.Label(self.network_info_frame, text="点击'开始'按钮获取网络信息", 
                                 font=('Arial', 10), foreground="gray")
        initial_label.pack(expand=True)
    
    def setup_tmo_cc_tab(self):
        """设置TMO CC Tab页面"""
        # 创建TMO CC Tab
        tmo_cc_tab = ttk.Frame(self.notebook)
        self.notebook.add(tmo_cc_tab, text="TMO CC")
        
        # 创建滚动容器
        tmo_container = ttk.Frame(tmo_cc_tab)
        tmo_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        tmo_container.columnconfigure(0, weight=1)
        
        # 创建水平滚动的Canvas
        canvas = tk.Canvas(tmo_container, height=30, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tmo_container, orient="horizontal", command=canvas.xview)
        scrollable_frame = ttk.Frame(canvas)
        
        # 配置滚动
        def update_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # 检查是否需要滚动条
            self.update_scrollbar_visibility(canvas, scrollbar, scrollable_frame)
        
        scrollable_frame.bind("<Configure>", update_scroll_region)
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(xscrollcommand=scrollbar.set)
        
        # 布局Canvas和Scrollbar
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 0), pady=(2, 0))
        scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 0), pady=(1, 2))
        
        # 绑定鼠标滚轮事件
        canvas.bind("<MouseWheel>", lambda e: canvas.xview_scroll(int(-1 * (e.delta / 120)), "units"))
        
        # TMO CC控制行
        tmo_row = scrollable_frame
        
        # TMO CC按钮
        ttk.Button(tmo_row, text="推CC文件", command=self.push_cc_file).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(tmo_row, text="拉CC文件", command=self.pull_cc_file).pack(side=tk.LEFT, padx=(0, 10))
        
        # 过滤按钮（动态按钮）
        self.simple_filter_button = ttk.Button(tmo_row, text="简单过滤", command=self.simple_filter)
        self.simple_filter_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.complete_filter_button = ttk.Button(tmo_row, text="完全过滤", command=self.complete_filter)
        self.complete_filter_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 清空日志按钮
        ttk.Button(tmo_row, text="清空日志", command=self.app.clear_logs).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(tmo_row, text="PROD服务器", command=self.prod_server).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(tmo_row, text="STG服务器", command=self.stg_server).pack(side=tk.LEFT)
        
        # 存储Canvas和滚动条引用，用于后续检查
        self.tmo_canvas = canvas
        self.tmo_scrollbar = scrollbar
        self.tmo_scrollable_frame = scrollable_frame
    
    def setup_tmo_echolocate_tab(self):
        """设置TMO Echolocate Tab页面"""
        # 创建TMO Echolocate Tab
        tmo_echolocate_tab = ttk.Frame(self.notebook)
        self.notebook.add(tmo_echolocate_tab, text="TMO Echolocate")
        
        # 创建滚动容器
        echolocate_container = ttk.Frame(tmo_echolocate_tab)
        echolocate_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        echolocate_container.columnconfigure(0, weight=1)
        
        # 创建水平滚动的Canvas
        canvas = tk.Canvas(echolocate_container, height=30, highlightthickness=0)
        scrollbar = ttk.Scrollbar(echolocate_container, orient="horizontal", command=canvas.xview)
        scrollable_frame = ttk.Frame(canvas)
        
        # 配置滚动
        def update_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # 检查是否需要滚动条
            self.update_scrollbar_visibility(canvas, scrollbar, scrollable_frame)
        
        scrollable_frame.bind("<Configure>", update_scroll_region)
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(xscrollcommand=scrollbar.set)
        
        # 布局Canvas和Scrollbar
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 0), pady=(2, 0))
        scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 0), pady=(1, 2))
        
        # 绑定鼠标滚轮事件
        canvas.bind("<MouseWheel>", lambda e: canvas.xview_scroll(int(-1 * (e.delta / 120)), "units"))
        
        # TMO Echolocate控制行
        echolocate_row = scrollable_frame
        
        # TMO Echolocate按钮
        ttk.Button(echolocate_row, text="安装", command=self.install_echolocate).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(echolocate_row, text="Trigger", command=self.trigger_echolocate).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(echolocate_row, text="Pull file", command=self.pull_echolocate_file).pack(side=tk.LEFT, padx=(0, 10))
        
        # 过滤标签和按钮
        ttk.Label(echolocate_row, text="filter:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(echolocate_row, text="CallState", command=self.filter_callstate).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(echolocate_row, text="UICallState", command=self.filter_uicallstate).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(echolocate_row, text="AllCallState", command=self.filter_allcallstate).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(echolocate_row, text="IMSSignallingMessageLine1", command=self.filter_ims_signalling).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(echolocate_row, text="AllCallFlow", command=self.filter_allcallflow).pack(side=tk.LEFT)
        
        # 存储Canvas和滚动条引用，用于后续检查
        self.echolocate_canvas = canvas
        self.echolocate_scrollbar = scrollbar
        self.echolocate_scrollable_frame = scrollable_frame
    
    def setup_log_display(self):
        """设置日志显示区域"""
        # 日志显示框架
        log_frame = ttk.LabelFrame(self.log_container, text="日志内容", padding="5")
        log_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 状态栏
        status_frame = ttk.Frame(self.log_container)
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        status_frame.columnconfigure(0, weight=1)
        
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        # 性能显示标签
        self.performance_var = tk.StringVar()
        self.performance_var.set("性能: 等待中...")
        self.performance_label = ttk.Label(status_frame, textvariable=self.performance_var, relief=tk.SUNKEN)
        self.performance_label.grid(row=0, column=1, sticky=tk.W)
        
        # 创建文本框和滚动条
        text_frame = ttk.Frame(log_frame)
        text_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        self.log_text = tk.Text(text_frame, wrap=tk.NONE, font=('Cascadia Mono', 12), 
                               bg='#0C0C0C', fg='#FFFFFF', insertbackground='white')
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 垂直滚动条
        v_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text.configure(yscrollcommand=v_scrollbar.set)
        
        # 水平滚动条
        h_scrollbar = ttk.Scrollbar(log_frame, orient=tk.HORIZONTAL, command=self.log_text.xview)
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.log_text.configure(xscrollcommand=h_scrollbar.set)
        
        # 配置文本标签用于高亮
        self.log_text.tag_configure("highlight", foreground="#FF4444", background="")
        self.log_text.tag_configure("normal", foreground="#FFFFFF")
        self.log_text.tag_configure("search_highlight", foreground="#00FF00", background="#333333")
        
        # 绑定鼠标滚轮事件
        self.log_text.bind("<MouseWheel>", self.on_mousewheel)
        self.log_text.bind("<Button-4>", self.on_mousewheel)
        self.log_text.bind("<Button-5>", self.on_mousewheel)
        
        # 绑定搜索快捷键
        self.root.bind_all("<Control-f>", self.show_search_dialog)
        self.root.bind_all("<Control-F>", self.show_search_dialog)
        self.root.bind_all("<F3>", self.find_next)
        self.root.bind_all("<Shift-F3>", self.find_previous)
        self.root.bind_all("<Control-g>", self.find_next)
        
        # 确保主窗口能接收键盘事件
        self.root.focus_set()
    
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
        edit_menu.add_command(label="清空日志", command=self.app.clear_logs)
        
        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="显示窗口", command=self.bring_to_front)
        tools_menu.add_separator()
        tools_menu.add_command(label="刷新设备列表", command=self.app.refresh_devices)
        tools_menu.add_command(label="设置显示行数", command=self.app.show_display_lines_dialog)
        tools_menu.add_command(label="清除设备缓存", command=self.app.clear_device_logs)
        tools_menu.add_command(label="保存日志", command=self.app.save_logs)
        tools_menu.add_separator()
        tools_menu.add_command(label="安装MTKLOGGER", command=self.app.install_mtklogger)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)
    
    def setup_window_management(self):
        """设置窗口管理功能"""
        # 绑定窗口状态变化事件
        self.root.bind("<Map>", self.on_window_map)
        self.root.bind("<Unmap>", self.on_window_unmap)
        self.root.bind("<FocusIn>", self.on_window_focus)
        self.root.bind("<FocusOut>", self.on_window_focus_out)
        
        # 绑定Alt+Tab快捷键
        self.root.bind("<Alt-Tab>", self.on_alt_tab)
        
        # 设置窗口属性
        self.root.attributes('-topmost', False)
        self.root.lift()
        
        # 设置任务栏图标和窗口属性
        try:
            self.root.iconbitmap(default="")
        except:
            pass
        
        # 设置窗口最小化行为
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 添加全局快捷键支持
        self.root.bind_all("<Control-Shift-L>", lambda e: self.bring_to_front())
    
    def on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        if event.delta:
            self.log_text.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif event.num == 4:
            self.log_text.yview_scroll(-1, "units")
        elif event.num == 5:
            self.log_text.yview_scroll(1, "units")
        return "break"
    
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
        return "break"
    
    def bring_to_front(self):
        """将窗口带到最前面"""
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after(100, lambda: self.root.attributes('-topmost', False))
        self.root.focus_force()
    
    def toggle_filtering(self):
        """切换过滤状态"""
        if self.app.is_running:
            self.app.stop_filtering()
        else:
            self.app.start_filtering()
        self.update_filter_button()
    
    def update_filter_button(self):
        """更新过滤按钮的文本"""
        if self.app.is_running:
            self.filter_button.config(text="停止过滤")
        else:
            self.filter_button.config(text="开始过滤")
        
        # 同时更新TMO CC tab的按钮状态
        self.update_tmo_filter_buttons()
    
    def update_tmo_filter_buttons(self):
        """更新TMO CC tab的过滤按钮状态"""
        if not hasattr(self, 'simple_filter_button') or not hasattr(self, 'complete_filter_button'):
            return
        
        if self.app.is_running:
            # 正在过滤中，根据当前过滤类型显示停止按钮
            current_keywords = self.app.filter_keyword.get()
            
            # 判断当前是简单过滤还是完全过滤
            simple_keywords = "new cc version|old cc version|doDeviceActivation:Successful|mDeviceGroup|getUserAgent"
            complete_keywords = "EntitlementServerApi|new cc version|old cc version|doDeviceActivation:Successful|mDeviceGroup|Entitlement-EapAka|EntitlementHandling|UpdateProvider|EntitlementService"
            
            if current_keywords == simple_keywords:
                # 当前是简单过滤
                self.simple_filter_button.config(text="停止log过滤")
                self.complete_filter_button.config(text="完全过滤")
            elif current_keywords == complete_keywords:
                # 当前是完全过滤
                self.simple_filter_button.config(text="简单过滤")
                self.complete_filter_button.config(text="停止log过滤")
            else:
                # 其他过滤类型，默认简单过滤按钮显示停止
                self.simple_filter_button.config(text="停止log过滤")
                self.complete_filter_button.config(text="完全过滤")
        else:
            # 没有过滤，恢复原始状态
            self.simple_filter_button.config(text="简单过滤")
            self.complete_filter_button.config(text="完全过滤")
    
    def on_tab_changed(self, event):
        """Tab切换时的处理"""
        # 延迟检查当前Tab的滚动条
        self.root.after(100, self.check_current_tab_scrollbar)
    
    def on_window_configure(self, event):
        """窗口大小变化时的处理"""
        # 只处理主窗口的大小变化，忽略子控件的Configure事件
        if event.widget == self.root:
            # 延迟检查当前Tab的滚动条，避免频繁检查
            if hasattr(self, '_configure_timer'):
                self.root.after_cancel(self._configure_timer)
            self._configure_timer = self.root.after(200, self.check_current_tab_scrollbar)
    
    def check_current_tab_scrollbar(self):
        """检查当前Tab的滚动条"""
        try:
            current_tab = self.notebook.select()
            tab_text = self.notebook.tab(current_tab, "text")
            
            if tab_text == "设备控制" and hasattr(self, 'device_canvas'):
                self.update_scrollbar_visibility(self.device_canvas, self.device_scrollbar, self.device_scrollable_frame)
            elif tab_text == "Log过滤" and hasattr(self, 'filter_canvas'):
                self.update_scrollbar_visibility(self.filter_canvas, self.filter_scrollbar, self.filter_scrollable_frame)
            elif tab_text == "网络信息":
                # 网络信息tab不需要滚动条检查
                pass
            elif tab_text == "TMO CC" and hasattr(self, 'tmo_canvas'):
                self.update_scrollbar_visibility(self.tmo_canvas, self.tmo_scrollbar, self.tmo_scrollable_frame)
            elif tab_text == "TMO Echolocate" and hasattr(self, 'echolocate_canvas'):
                self.update_scrollbar_visibility(self.echolocate_canvas, self.echolocate_scrollbar, self.echolocate_scrollable_frame)
        except Exception as e:
            pass  # 静默处理错误
    
    def update_scrollbar_visibility(self, canvas, scrollbar, scrollable_frame):
        """动态控制滚动条的显示/隐藏"""
        try:
            # 获取Canvas和内容的大小
            canvas_width = canvas.winfo_width()
            content_width = scrollable_frame.winfo_reqwidth()
            
            # 如果内容宽度小于等于Canvas宽度，隐藏滚动条
            if content_width <= canvas_width:
                scrollbar.grid_remove()
            else:
                scrollbar.grid()
        except Exception as e:
            # 如果获取尺寸失败，默认显示滚动条
            scrollbar.grid()
    
    def on_closing(self):
        """窗口关闭时的处理"""
        if self.app.is_running:
            self.app.stop_filtering()
        # 保存分割条位置
        self.save_sash_position()
        self.root.destroy()
    
    def show_about(self):
        """显示关于对话框"""
        messagebox.showinfo("关于", 
            "手机测试辅助工具\n\n"
            "版本: 2.1\n"
            "功能: Android设备日志管理和MTKLOG操作\n\n"
            "主要功能:\n"
            "• 实时过滤Android设备日志\n"
            "• MTKLOG开启/停止/导出/删除\n"
            "• ADB Log开启/导出\n"
            "• 设备模式切换(SD/USB)\n"
            "• 截图和视频录制\n"
            "• TMO CC文件操作\n"
            "• 多设备支持\n"
            "• 性能监控和优化\n\n"
            "快捷键:\n"
            "Ctrl+F - 搜索\n"
            "F3 - 查找下一个\n"
            "Shift+F3 - 查找上一个\n"
            "Ctrl+Shift+L - 显示窗口\n"
            "Escape - 关闭搜索对话框\n\n"
            "Tab页面:\n"
            "• 设备控制 - 设备管理、MTKLOG\n"
            "• Log过滤 - 关键字过滤、ADB Log、日志管理\n"
            "• TMO CC - CC文件操作、服务器选择")
    
    # TMO CC相关方法（占位符，待实现）
    def push_cc_file(self):
        """推CC文件"""
        self.app.push_cc_manager.push_cc_file()
    
    def pull_cc_file(self):
        """拉CC文件"""
        self.app.tmo_cc_manager.pull_cc_file()
    
    def simple_filter(self):
        """简单过滤"""
        # 如果正在过滤中，则停止过滤
        if self.app.is_running:
            self.app.stop_filtering()
            self.update_tmo_filter_buttons()
            return
        
        # 设置预定义的关键字（使用正则表达式）
        keywords = "new cc version|old cc version|doDeviceActivation:Successful|mDeviceGroup|getUserAgent"
        
        # 设置关键字到输入框
        self.app.filter_keyword.set(keywords)
        
        # 启用正则表达式模式
        self.app.use_regex.set(True)
        
        # 直接开始过滤
        self.app.start_filtering()
        
        # 更新按钮状态
        self.update_tmo_filter_buttons()
    
    def complete_filter(self):
        """完全过滤"""
        # 如果正在过滤中，则停止过滤
        if self.app.is_running:
            self.app.stop_filtering()
            self.update_tmo_filter_buttons()
            return
        
        # 设置预定义的关键字（使用正则表达式）
        keywords = "EntitlementServerApi|new cc version|old cc version|doDeviceActivation:Successful|mDeviceGroup|Entitlement-EapAka|EntitlementHandling|UpdateProvider|EntitlementService"
        
        # 设置关键字到输入框
        self.app.filter_keyword.set(keywords)
        
        # 启用正则表达式模式
        self.app.use_regex.set(True)
        
        # 直接开始过滤
        self.app.start_filtering()
        
        # 更新按钮状态
        self.update_tmo_filter_buttons()
    
    def prod_server(self):
        """PROD服务器"""
        self.app.server_manager.prod_server()
    
    def stg_server(self):
        """STG服务器"""
        self.app.server_manager.stg_server()
    
    # TMO Echolocate相关方法
    def install_echolocate(self):
        """安装Echolocate"""
        messagebox.showinfo("TMO Echolocate", "安装Echolocate功能待实现")
    
    def trigger_echolocate(self):
        """触发Echolocate"""
        messagebox.showinfo("TMO Echolocate", "触发Echolocate功能待实现")
    
    def pull_echolocate_file(self):
        """拉取Echolocate文件"""
        messagebox.showinfo("TMO Echolocate", "拉取Echolocate文件功能待实现")
    
    def filter_callstate(self):
        """过滤CallState"""
        if self.app.is_running:
            self.app.stop_filtering()
        
        # 设置CallState关键字
        keywords = "CallState"
        self.app.filter_keyword.set(keywords)
        self.app.use_regex.set(True)
        self.app.start_filtering()
    
    def filter_uicallstate(self):
        """过滤UICallState"""
        if self.app.is_running:
            self.app.stop_filtering()
        
        # 设置UICallState关键字
        keywords = "UICallState"
        self.app.filter_keyword.set(keywords)
        self.app.use_regex.set(True)
        self.app.start_filtering()
    
    def filter_allcallstate(self):
        """过滤AllCallState"""
        if self.app.is_running:
            self.app.stop_filtering()
        
        # 设置AllCallState关键字
        keywords = "AllCallState"
        self.app.filter_keyword.set(keywords)
        self.app.use_regex.set(True)
        self.app.start_filtering()
    
    def filter_ims_signalling(self):
        """过滤IMSSignallingMessageLine1"""
        if self.app.is_running:
            self.app.stop_filtering()
        
        # 设置IMSSignallingMessageLine1关键字
        keywords = "IMSSignallingMessageLine1"
        self.app.filter_keyword.set(keywords)
        self.app.use_regex.set(True)
        self.app.start_filtering()
    
    def filter_allcallflow(self):
        """过滤AllCallFlow"""
        if self.app.is_running:
            self.app.stop_filtering()
        
        # 设置AllCallFlow关键字
        keywords = "AllCallFlow"
        self.app.filter_keyword.set(keywords)
        self.app.use_regex.set(True)
        self.app.start_filtering()
    
    def load_log_keywords(self):
        """加载log关键字文件"""
        from tkinter import filedialog, messagebox
        
        # 显示文件选择对话框
        file_path = filedialog.askopenfilename(
            title="选择log关键字文件",
            filetypes=[
                ("文本文件", "*.txt"),
                ("所有文件", "*.*")
            ],
            parent=self.root
        )
        
        if not file_path:
            print(f"[DEBUG] 用户取消文件选择")
            return
        
        try:
            print(f"[DEBUG] 加载log关键字文件: {file_path}")
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                messagebox.showwarning("警告", "文件内容为空")
                return
            
            print(f"[DEBUG] 文件内容: {content}")
            
            # 设置关键字到输入框
            self.app.filter_keyword.set(content)
            
            # 自动启用正则表达式模式（因为文件内容是按正则表达式方式书写的）
            self.app.use_regex.set(True)
            
            # 自动开始过滤
            self.app.start_filtering()
            
        except UnicodeDecodeError:
            messagebox.showerror("错误", "文件编码错误，请确保文件是UTF-8编码")
        except Exception as e:
            print(f"[DEBUG] 加载文件失败: {str(e)}")
            messagebox.showerror("错误", f"加载文件失败:\n{str(e)}")
    
    # 搜索相关方法（委托给search_manager）
    def show_search_dialog(self, event=None):
        """显示搜索对话框"""
        self.app.search_manager.show_search_dialog(event)
    
    def find_next(self, event=None):
        """查找下一个匹配项"""
        self.app.search_manager.find_next(event)
    
    def find_previous(self, event=None):
        """查找上一个匹配项"""
        self.app.search_manager.find_previous(event)
    
    # 模态执行器相关方法
    def run_with_modal(self, title, worker_fn, on_done=None, on_error=None):
        """通用的模态执行器：后台线程执行 + 局部遮罩拦截点击"""
        
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
        try:
            # 检查对话框是否仍然存在
            if not progress_dialog.winfo_exists():
                return
            
            # 更新进度条到100%
            if '!frame' in progress_dialog.children:
                frame = progress_dialog.children['!frame']
                if '!progressbar' in frame.children:
                    progress_var = frame.children['!progressbar'].cget('variable')
                    if hasattr(progress_var, 'set'):
                        progress_var.set(100)
            
            # 更新状态
            if '!frame' in progress_dialog.children:
                frame = progress_dialog.children['!frame']
                if '!label' in frame.children:
                    status_label = frame.children['!label']
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
        except Exception as e:
            # 如果出现任何错误，直接清理资源
            try:
                mask_frame.destroy()
                self._enable_all_widgets(self.root)
                progress_dialog.destroy()
                if callback:
                    callback(result)
            except:
                pass
    
    def toggle_google_log(self):
        """切换Google日志状态"""
        if self.app.google_log_manager.is_running():
            self.stop_google_log()
        else:
            self.show_google_log_options()
    
    def start_google_log(self):
        """开始Google日志收集"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 调用GoogleLogManager启动完整的Google日志收集
        self.app.google_log_manager.start_google_log(device, self)
    
    def show_google_log_options(self):
        """显示Google日志选项对话框"""
        # 创建设备选择对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("Google日志收集选项")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()  # 模态对话框
        
        # 居中显示
        dialog.geometry("+%d+%d" % (
            self.root.winfo_rootx() + (self.root.winfo_width() - 400) // 2,
            self.root.winfo_rooty() + (self.root.winfo_height() - 200) // 2
        ))
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="选择Google日志收集模式", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 选项框架
        options_frame = ttk.Frame(main_frame)
        options_frame.pack(pady=(0, 20))

        # 同一行里放两个按钮
        btn1 = ttk.Button(options_frame, text="仅bugreport",
                        command=lambda: self.start_bugreport_only(dialog))
        btn1.pack(side=tk.LEFT, padx=5)

        btn2 = ttk.Button(options_frame, text="全部log+video",
                        command=lambda: self.start_full_google_log(dialog))
        btn2.pack(side=tk.LEFT, padx=5)
        
        # 取消按钮
        ttk.Button(main_frame, text="取消", command=dialog.destroy).pack()
    
    def start_bugreport_only(self, dialog):
        """仅执行bugreport"""
        dialog.destroy()  # 关闭选择对话框
        
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 调用GoogleLogManager执行仅bugreport
        self.app.google_log_manager.start_bugreport_only(device, self)
    
    def start_full_google_log(self, dialog):
        """启动完整的Google日志收集"""
        dialog.destroy()  # 关闭选择对话框
        self.start_google_log()
    
    def stop_google_log(self):
        """停止Google日志收集"""
        device = self.app.device_manager.validate_device_selection()
        if not device:
            return
        
        # 调用GoogleLogManager停止Google日志收集
        self.app.google_log_manager.stop_google_log(device, self)
    
    def toggle_network_info(self):
        """切换网络信息获取状态"""
        if self.app.network_info_manager.is_running:
            self.app.network_info_manager.stop_network_info()
            self.network_status_label.config(text="已停止", foreground="red")
        else:
            self.app.network_info_manager.start_network_info()
            self.network_status_label.config(text="运行中", foreground="green")