#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI管理模块
负责界面布局、控件管理和用户交互
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import threading

class UIManager:
    def __init__(self, root, app_instance):
        self.root = root
        self.app = app_instance
        self.setup_ui()
        self.setup_log_display()
        self.setup_menu()
        self.setup_window_management()
    
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)
        
        # 创建Tab控件
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 创建各个Tab页面
        self.setup_device_control_tab()
        self.setup_log_filter_tab()
        self.setup_tmo_cc_tab()
        
        # 第一行 - 设备控制 + MTKLOG + ADB log操作 (可滚动)
        first_row_container = ttk.Frame(control_frame)
        first_row_container.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        first_row_container.columnconfigure(0, weight=1)
        
        # 创建Canvas和Scrollbar用于水平滚动
        self.first_row_canvas = tk.Canvas(first_row_container, height=40, highlightthickness=0)
        self.first_row_scrollbar = ttk.Scrollbar(first_row_container, orient="horizontal", command=self.first_row_canvas.xview)
        self.first_row_scrollable_frame = ttk.Frame(self.first_row_canvas)
        
        # 配置滚动
        self.first_row_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.first_row_canvas.configure(scrollregion=self.first_row_canvas.bbox("all"))
        )
        
        self.first_row_canvas.create_window((0, 0), window=self.first_row_scrollable_frame, anchor="nw")
        self.first_row_canvas.configure(xscrollcommand=self.first_row_scrollbar.set)
        
        # 布局Canvas和Scrollbar
        self.first_row_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.first_row_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # 绑定鼠标滚轮事件到第一行Canvas
        self.first_row_canvas.bind("<MouseWheel>", self.on_first_row_scroll)
        
        first_row_frame = self.first_row_scrollable_frame
        
        # 设备选择
        ttk.Label(first_row_frame, text="设备:").pack(side=tk.LEFT, padx=(0, 5))
        self.device_combo = ttk.Combobox(first_row_frame, textvariable=self.app.selected_device, width=18, state="readonly")
        self.device_combo.pack(side=tk.LEFT, padx=(0, 5))
        
        # 刷新设备按钮
        ttk.Button(first_row_frame, text="刷新设备", command=self.app.refresh_devices).pack(side=tk.LEFT, padx=(0, 5))
        
        # MTKLOG按钮组
        mtklog_label = ttk.Label(first_row_frame, text="MTKLOG:")
        mtklog_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.start_mtklog_button = ttk.Button(first_row_frame, text="开启", command=self.app.start_mtklog)
        self.start_mtklog_button.pack(side=tk.LEFT, padx=(0, 2))
        
        self.stop_export_mtklog_button = ttk.Button(first_row_frame, text="停止&导出", command=self.app.stop_and_export_mtklog)
        self.stop_export_mtklog_button.pack(side=tk.LEFT, padx=(0, 2))
        
        self.delete_mtklog_button = ttk.Button(first_row_frame, text="删除", command=self.app.delete_mtklog)
        self.delete_mtklog_button.pack(side=tk.LEFT, padx=(0, 2))
        
        self.sd_mode_button = ttk.Button(first_row_frame, text="SD模式", command=self.app.set_sd_mode)
        self.sd_mode_button.pack(side=tk.LEFT, padx=(0, 2))
        
        self.usb_mode_button = ttk.Button(first_row_frame, text="USB模式", command=self.app.set_usb_mode)
        self.usb_mode_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # ADB log按钮组
        adblog_label = ttk.Label(first_row_frame, text="ADB Log:")
        adblog_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.start_adblog_button = ttk.Button(first_row_frame, text="开启", command=self.app.start_adblog)
        self.start_adblog_button.pack(side=tk.LEFT, padx=(0, 2))
        
        self.export_adblog_button = ttk.Button(first_row_frame, text="导出", command=self.app.export_adblog)
        self.export_adblog_button.pack(side=tk.LEFT, padx=(0, 2))
        
        # 第二行 - 过滤控制 + 常用操作 (可滚动)
        second_row_container = ttk.Frame(control_frame)
        second_row_container.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        second_row_container.columnconfigure(0, weight=1)
        
        # 创建Canvas和Scrollbar用于水平滚动
        self.second_row_canvas = tk.Canvas(second_row_container, height=40, highlightthickness=0)
        self.second_row_scrollbar = ttk.Scrollbar(second_row_container, orient="horizontal", command=self.second_row_canvas.xview)
        self.second_row_scrollable_frame = ttk.Frame(self.second_row_canvas)
        
        # 配置滚动
        self.second_row_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.second_row_canvas.configure(scrollregion=self.second_row_canvas.bbox("all"))
        )
        
        self.second_row_canvas.create_window((0, 0), window=self.second_row_scrollable_frame, anchor="nw")
        self.second_row_canvas.configure(xscrollcommand=self.second_row_scrollbar.set)
        
        # 布局Canvas和Scrollbar
        self.second_row_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.second_row_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # 绑定鼠标滚轮事件到第二行Canvas
        self.second_row_canvas.bind("<MouseWheel>", self.on_second_row_scroll)
        
        second_row_frame = self.second_row_scrollable_frame
        
        # 关键字输入
        ttk.Label(second_row_frame, text="关键字:").pack(side=tk.LEFT, padx=(0, 5))
        keyword_entry = ttk.Entry(second_row_frame, textvariable=self.app.filter_keyword, width=20)
        keyword_entry.pack(side=tk.LEFT, padx=(0, 10))
        keyword_entry.bind('<Return>', lambda e: self.app.start_filtering())
        
        # 选项复选框
        ttk.Checkbutton(second_row_frame, text="正则表达式", variable=self.app.use_regex).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Checkbutton(second_row_frame, text="区分大小写", variable=self.app.case_sensitive).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Checkbutton(second_row_frame, text="彩色高亮", variable=self.app.color_highlight).pack(side=tk.LEFT, padx=(0, 10))
        
        # 主要操作按钮（动态按钮）
        self.filter_button = ttk.Button(second_row_frame, text="开始过滤", command=self.toggle_filtering)
        self.filter_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # 常用按钮
        ttk.Button(second_row_frame, text="清空日志", command=self.app.clear_logs).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(second_row_frame, text="清除缓存", command=self.app.clear_device_logs).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(second_row_frame, text="设置行数", command=self.app.show_display_lines_dialog).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(second_row_frame, text="截图", command=self.app.take_screenshot).pack(side=tk.LEFT, padx=(0, 3))
        
        # 录制按钮
        self.record_button = ttk.Button(second_row_frame, text="开始录制", command=self.app.toggle_recording)
        self.record_button.pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(second_row_frame, text="保存日志", command=self.app.save_logs).pack(side=tk.LEFT)
        
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
        
        # 绑定搜索快捷键
        self.root.bind_all("<Control-f>", self.app.show_search_dialog)
        self.root.bind_all("<Control-F>", self.app.show_search_dialog)
        self.root.bind_all("<F3>", self.app.find_next)
        self.root.bind_all("<Shift-F3>", self.app.find_previous)
        self.root.bind_all("<Control-g>", self.app.find_next)
        
        # 确保主窗口能接收键盘事件
        self.root.focus_set()
    
    def setup_menu(self):
        """设置菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 编辑菜单
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="搜索 (Ctrl+F)", command=self.app.show_search_dialog)
        edit_menu.add_command(label="查找下一个 (F3)", command=self.app.find_next)
        edit_menu.add_command(label="查找上一个 (Shift+F3)", command=self.app.find_previous)
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
    
    def on_first_row_scroll(self, event):
        """处理第一行按钮的水平滚动"""
        if event.delta:
            self.first_row_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"
    
    def on_second_row_scroll(self, event):
        """处理第二行按钮的水平滚动"""
        if event.delta:
            self.second_row_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
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
    
    def update_filter_button(self):
        """更新过滤按钮状态"""
        if self.app.is_running:
            self.filter_button.config(text="停止过滤")
        else:
            self.filter_button.config(text="开始过滤")
    
    def on_closing(self):
        """窗口关闭时的处理"""
        if self.app.is_running:
            self.app.stop_filtering()
        self.root.destroy()
    
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
    
    def run_with_modal(self, title, worker_fn, on_done=None, on_error=None):
        """通用的模态执行器：后台线程执行 + 局部遮罩拦截点击"""
        # 禁用主窗口所有控件
        self._disable_all_widgets(self.root)
        
        # 创建局部遮罩层（仅在主窗口内部）
        mask_frame = ttk.Frame(self.root)
        mask_frame.place(x=0, y=0, relwidth=1, relheight=1)
        
        # 设置遮罩样式（半透明效果）
        try:
            style = ttk.Style()
            style.configure("Mask.TFrame", background="gray")
            mask_frame.configure(style="Mask.TFrame")
        except:
            # 如果样式设置失败，使用默认样式
            pass
        
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
