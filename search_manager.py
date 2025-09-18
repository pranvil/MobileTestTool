#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜索管理模块
负责日志搜索、高亮和导航功能
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import re

class SearchManager:
    def __init__(self, app_instance):
        self.app = app_instance
        
        # 搜索相关变量
        self.search_keyword = tk.StringVar()
        self.search_case_sensitive = tk.BooleanVar()
        self.search_use_regex = tk.BooleanVar()
        self.current_search_pos = "1.0"
        self.search_results = []
        self.current_result_index = 0
    
    def show_search_dialog(self, event=None):
        """显示搜索对话框"""
        # 调试信息
        print(f"搜索对话框被触发，事件: {event}")
        
        # 创建搜索对话框
        search_dialog = tk.Toplevel(self.app.root)
        search_dialog.title("搜索")
        search_dialog.geometry("400x200")
        search_dialog.resizable(False, False)
        search_dialog.transient(self.app.root)
        search_dialog.grab_set()
        
        # 居中显示
        search_dialog.geometry("+%d+%d" % (
            self.app.root.winfo_rootx() + 50,
            self.app.root.winfo_rooty() + 50
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
        text_content = self.app.ui.log_text.get("1.0", tk.END)
        
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
                self.app.ui.log_text.tag_add("search_highlight", start_pos, end_pos)
            
            # 跳转到第一个匹配
            self.current_result_index = 0
            self.jump_to_search_result()
            
            # 不关闭对话框，让用户可以继续使用下一个/上一个按钮
            if dialog:
                # 更新状态显示
                self.app.ui.status_var.set(f"找到 {len(self.search_results)} 个匹配项")
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
        self.app.ui.log_text.see(start_pos)
        
        # 选中匹配文本
        self.app.ui.log_text.tag_remove(tk.SEL, "1.0", tk.END)
        self.app.ui.log_text.tag_add(tk.SEL, start_pos, end_pos)
        
        # 更新状态
        self.app.ui.status_var.set(f"找到 {len(self.search_results)} 个匹配项，当前第 {self.current_result_index + 1} 个")
    
    def clear_search_highlight(self):
        """清除搜索高亮"""
        self.app.ui.log_text.tag_remove("search_highlight", "1.0", tk.END)
        self.app.ui.log_text.tag_remove(tk.SEL, "1.0", tk.END)
    
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
        results_window = tk.Toplevel(self.app.root)
        results_window.title(f"搜索结果 - 找到 {len(self.search_results)} 个匹配项")
        results_window.geometry("1000x600")
        results_window.transient(self.app.root)
        
        # 居中显示
        results_window.geometry("+%d+%d" % (
            self.app.root.winfo_rootx() + 50,
            self.app.root.winfo_rooty() + 50
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
        original_text = self.app.ui.log_text.get("1.0", tk.END)
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
