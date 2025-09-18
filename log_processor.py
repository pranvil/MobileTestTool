#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志处理模块
负责日志过滤、搜索、保存和性能优化
"""

import subprocess
import threading
import re
import os
import queue
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

class LogProcessor:
    def __init__(self, app_instance):
        self.app = app_instance
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
        
        
        # 启动日志队列处理
        self.process_log_queue()
    
    def start_filtering(self):
        """开始过滤日志"""
        keyword = self.app.filter_keyword.get().strip()
        if not keyword:
            messagebox.showwarning("警告", "请输入过滤关键字")
            return
        
        if self.app.is_running:
            messagebox.showinfo("提示", "过滤已在运行中")
            return
        
        # 检查设备选择
        device = self.app.selected_device.get().strip()
        
        # 如果有多个设备但未选择，提示用户选择
        if len(self.app.available_devices) > 1 and device == "":
            messagebox.showwarning("警告", f"检测到多个设备，请选择要抓取日志的设备:\n{', '.join(self.app.available_devices)}")
            return
        
        bad_devices = {"无设备", "检测失败", "检测超时", "adb未安装", "检测错误"}
        if device == "" or device in bad_devices:
            messagebox.showwarning("警告", "请先选择有效的设备")
            return
        
        try:
            # 验证正则表达式
            if self.app.use_regex.get():
                re.compile(keyword)
        except re.error as e:
            messagebox.showerror("错误", f"正则表达式无效: {e}")
            return
        
        self.app.is_running = True
        self.app.ui.update_filter_button()
        self.app.ui.status_var.set("正在过滤...")
        
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
            device = self.app.selected_device.get().strip()
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
                if not self.app.is_running:
                    break
                
                # 过滤日志
                if self.filter_line(line):
                    self.log_queue.put(line)
            
        except FileNotFoundError:
            self.log_queue.put("ERROR: 未找到adb命令，请确保Android SDK已安装并配置PATH")
        except Exception as e:
            self.log_queue.put(f"ERROR: {e}")
        finally:
            self.app.is_running = False
            self.app.root.after(0, self.filtering_stopped)
    
    def filter_line(self, line):
        """过滤日志行"""
        keyword = self.app.filter_keyword.get()
        
        if self.app.use_regex.get():
            try:
                flags = 0 if self.app.case_sensitive.get() else re.IGNORECASE
                return bool(re.search(keyword, line, flags))
            except re.error:
                return False
        else:
            if self.app.case_sensitive.get():
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
        self.app.root.after(interval, self.process_log_queue)
    
    def add_log_lines_batch(self, lines):
        """批量添加日志行，提高性能"""
        self.app.ui.log_text.config(state=tk.NORMAL)
        
        # 移动到末尾
        self.app.ui.log_text.see(tk.END)
        
        # 批量处理所有行
        for line in lines:
            # 直接使用设备log输出的时间，不添加额外时间戳
            full_line = line.rstrip() + "\n"
            
            # 高亮关键字（如果启用）- 支持自适应高亮策略
            if self.app.color_highlight.get() and self.app.filter_keyword.get():
                self.add_highlighted_line_batch(full_line)
            else:
                self.app.ui.log_text.insert(tk.END, full_line)
        
        # 更新性能统计
        self.performance_stats['processed_lines'] += len(lines)
        self.update_performance_display()
        
        # 高效的行数裁剪机制
        self.trim_log_lines_if_needed(len(lines))
        
        self.app.ui.log_text.config(state=tk.DISABLED)
        self.app.ui.log_text.see(tk.END)
    
    def add_highlighted_line_batch(self, line):
        """批量添加高亮显示的日志行，支持自适应高亮策略"""
        keyword = self.app.filter_keyword.get()
        if not keyword:
            self.app.ui.log_text.insert(tk.END, line)
            return
        
        # 检查队列负荷，决定高亮策略
        queue_size = self.log_queue.qsize()
        
        # 准备搜索模式
        if self.app.use_regex.get():
            try:
                flags = 0 if self.app.case_sensitive.get() else re.IGNORECASE
                pattern = keyword
            except re.error:
                pattern = re.escape(keyword)
                flags = 0 if self.app.case_sensitive.get() else re.IGNORECASE
        else:
            pattern = re.escape(keyword)
            flags = 0 if self.app.case_sensitive.get() else re.IGNORECASE
        
        # 查找匹配
        matches = list(re.finditer(pattern, line, flags))
        
        if not matches:
            self.app.ui.log_text.insert(tk.END, line)
            return
        
        # 自适应高亮策略：高负荷时只高亮第一个匹配
        if queue_size > self.adaptive_params['high_load_threshold']:
            # 高负荷：只高亮第一个匹配，提升性能
            match = matches[0]
            # 插入匹配前的文本
            if match.start() > 0:
                self.app.ui.log_text.insert(tk.END, line[:match.start()])
            # 插入高亮文本
            self.app.ui.log_text.insert(tk.END, match.group(), "highlight")
            # 插入匹配后的文本
            if match.end() < len(line):
                self.app.ui.log_text.insert(tk.END, line[match.end():])
        else:
            # 正常负荷：高亮所有匹配
            last_end = 0
            for match in matches:
                # 插入普通文本
                if match.start() > last_end:
                    self.app.ui.log_text.insert(tk.END, line[last_end:match.start()])
                
                # 插入高亮文本
                self.app.ui.log_text.insert(tk.END, match.group(), "highlight")
                last_end = match.end()
            
            # 插入剩余文本
            if last_end < len(line):
                self.app.ui.log_text.insert(tk.END, line[last_end:])
    
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
                current_lines = int(self.app.ui.log_text.index('end-1c').split('.')[0])
                
                if current_lines > self.adaptive_params['max_display_lines']:
                    # 计算需要删除的行数
                    lines_to_delete = current_lines - self.adaptive_params['max_display_lines']
                    
                    # 使用文本索引一次性删除超出的行
                    self.app.ui.log_text.delete("1.0", f"{lines_to_delete + 1}.0")
                    
                    # 更新缓存
                    self.performance_cache['last_line_count'] = self.adaptive_params['max_display_lines']
                    
                    # 重置计数器
                    self._line_count = 0
                    
                    # 输出调试信息
                    print(f"裁剪日志: 删除了 {lines_to_delete} 行，当前行数: {self.adaptive_params['max_display_lines']} (trim_threshold: {trim_threshold})")
                    
            except Exception as e:
                # 如果出现异常，回退到原来的方法
                try:
                    lines_count = len(self.app.ui.log_text.get("1.0", tk.END).split('\n'))
                    if lines_count > self.adaptive_params['max_display_lines']:
                        lines_to_delete = lines_count - self.adaptive_params['max_display_lines']
                        self.app.ui.log_text.delete("1.0", f"{lines_to_delete + 1}.0")
                        self.performance_cache['last_line_count'] = self.adaptive_params['max_display_lines']
                        print(f"裁剪日志(备用方法): 删除了 {lines_to_delete} 行")
                except Exception as e2:
                    print(f"裁剪日志失败: {e2}")
                
                # 重置计数器
                self._line_count = 0
    
    def stop_filtering(self):
        """停止过滤"""
        self.app.is_running = False
        if self.log_process:
            self.log_process.terminate()
            self.log_process.wait()  # 等待进程结束，避免僵尸进程
            self.log_process = None
    
    def filtering_stopped(self):
        """过滤停止后的处理"""
        self.app.ui.update_filter_button()
        self.app.ui.status_var.set("已停止")
        
        # 重置性能统计
        self.app.ui.performance_var.set("")
    
    def clear_logs(self):
        """清空日志"""
        self.app.ui.log_text.config(state=tk.NORMAL)
        self.app.ui.log_text.delete("1.0", tk.END)
        self.app.ui.log_text.config(state=tk.DISABLED)
        self._line_count = 0  # 重置行计数器
        
        # 重置性能统计
        if self.app.is_running:
            self.performance_stats['processed_lines'] = 0
            self.performance_stats['start_time'] = datetime.now()
            self.performance_stats['processing_rate'] = 0.0
            self.update_performance_display()
        
        self.app.ui.status_var.set("日志已清空")
    
    def save_logs(self):
        """保存日志到文件"""
        if not self.app.ui.log_text.get("1.0", tk.END).strip():
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
                    f.write(self.app.ui.log_text.get("1.0", tk.END))
                messagebox.showinfo("成功", f"日志已保存到: {filename}")
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
                self.app.ui.status_var.set("设备日志缓存已清除")
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                messagebox.showerror("错误", f"清除设备日志缓存失败:\n{error_msg}")
                self.app.ui.status_var.set("清除设备日志缓存失败")
                
        except subprocess.TimeoutExpired:
            messagebox.showerror("错误", "清除设备日志缓存超时，请检查设备连接")
            self.app.ui.status_var.set("清除设备日志缓存超时")
        except FileNotFoundError:
            messagebox.showerror("错误", "未找到adb命令，请确保Android SDK已安装并配置PATH")
            self.app.ui.status_var.set("未找到adb命令")
        except Exception as e:
            messagebox.showerror("错误", f"清除设备日志缓存时发生错误: {e}")
            self.app.ui.status_var.set("清除设备日志缓存失败")
    
    def show_display_lines_dialog(self):
        """显示设置最大显示行数的对话框"""
        # 创建设置对话框
        dialog = tk.Toplevel(self.app.root)
        dialog.title("设置最大显示行数")
        dialog.geometry("450x450")
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
                self.app.ui.status_var.set(f"最大显示行数已设置为: {new_lines} 行")
                
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
    
    def update_performance_display(self):
        """更新性能显示"""
        if not self.app.is_running:
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
        
        self.app.ui.performance_var.set(performance_text)
        
        # 更新性能栏颜色
        for child in self.app.ui.main_frame.winfo_children():
            if isinstance(child, ttk.Frame):
                for grandchild in child.winfo_children():
                    if isinstance(grandchild, ttk.Label) and grandchild.cget('textvariable') == str(self.app.ui.performance_var):
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
            current_display_lines = int(self.app.ui.log_text.index('end-1c').split('.')[0])
            
            # 检查是否需要更新内存缓存（基于时间间隔）
            current_time = datetime.now()
            if not hasattr(self, '_last_memory_update') or \
               (current_time - self._last_memory_update).total_seconds() > 2.0:  # 每2秒更新一次
                
                # 计算内存使用情况（更准确的估算）
                try:
                    # 获取文本内容长度
                    text_content = self.app.ui.log_text.get("1.0", tk.END)
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
