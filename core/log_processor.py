#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5 Log过滤管理器
完整实现原Tkinter版本的Log过滤功能
"""

import subprocess
import threading
import re
import os
import queue
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QMutex
from PyQt5.QtWidgets import QMessageBox, QFileDialog


class LogFilterWorker(threading.Thread):
    """Log过滤工作线程"""
    
    def __init__(self, device, keyword, use_regex, case_sensitive, callback, stop_event):
        super().__init__()
        self.device = device
        self.keyword = keyword
        self.use_regex = use_regex
        self.case_sensitive = case_sensitive
        self.callback = callback
        self.stop_event = stop_event
        self.process = None
        
        # 编译正则表达式
        if self.use_regex:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            try:
                self.pattern = re.compile(self.keyword, flags)
            except re.error:
                self.pattern = None
        else:
            self.pattern = None
    
    def run(self):
        """运行logcat过滤"""
        while not self.stop_event.is_set():
            try:
                # 检查设备选择
                if not self.device or self.device in ["无设备", "检测失败", "检测超时", "adb未安装", "检测错误"]:
                    self.callback("ERROR: 请先选择有效的设备\n")
                    return
                
                # 构建adb logcat命令，添加-b all参数确保完全输出
                cmd = ["adb", "-s", self.device, "logcat", "-b", "all", "-v", "time"]
                
                # 启动进程
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    bufsize=1,
                    universal_newlines=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                # 读取输出
                line_count = 0
                waiting_for_device = False
                
                for line in iter(self.process.stdout.readline, ''):
                    if self.stop_event.is_set():
                        break
                    
                    line_count += 1
                    
                    # 检查是否是"waiting for device"状态
                    if "waiting for device" in line.lower():
                        if not waiting_for_device:
                            waiting_for_device = True
                            self.callback("STATUS: ADB断开，等待重连...\n")
                        continue
                    
                    # 如果之前是waiting状态，现在收到正常日志，说明重连成功
                    if waiting_for_device:
                        waiting_for_device = False
                        self.callback("STATUS: ADB重连成功，恢复正常过滤\n")
                    
                    # 过滤日志
                    if self._should_show(line):
                        self.callback(line)
                
                # 如果用户没有主动停止，说明连接断开，重新启动
                if not self.stop_event.is_set():
                    self.callback("STATUS: ADB断开，等待重连...\n")
                    
                    # 清理当前进程
                    if self.process:
                        try:
                            self.process.terminate()
                            self.process.wait(timeout=2)
                        except:
                            pass
                        self.process = None
                    
                    # 短暂等待后重新启动
                    import time
                    time.sleep(1)
                else:
                    break
                    
            except FileNotFoundError:
                self.callback("ERROR: 未找到adb命令，请确保Android SDK已安装并配置PATH\n")
                break
            except Exception as e:
                self.callback(f"STATUS: ADB连接异常，等待重连...\n")
                
                # 清理当前进程
                if self.process:
                    try:
                        self.process.terminate()
                        self.process.wait(timeout=2)
                    except:
                        pass
                    self.process = None
                
                # 等待后重新尝试
                import time
                time.sleep(2)
                
                if self.stop_event.is_set():
                    break
        
        # 清理资源
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                pass
            self.process = None
    
    def _should_show(self, line):
        """判断是否应该显示这行日志"""
        if not self.keyword:
            return True
        
        if self.use_regex:
            if self.pattern:
                return bool(self.pattern.search(line))
            else:
                return False
        else:
            if self.case_sensitive:
                return self.keyword in line
            else:
                return self.keyword.lower() in line.lower()
    
    def stop(self):
        """停止logcat"""
        self.stop_event.set()
        if self.process:
            self.process.terminate()


class PyQtLogProcessor(QObject):
    """PyQt5 Log过滤管理器 - 完整功能版本"""
    
    # 信号定义
    filtering_started = pyqtSignal()
    filtering_stopped = pyqtSignal()
    log_received = pyqtSignal(str)  # log_line
    status_message = pyqtSignal(str)
    performance_update = pyqtSignal(str)  # 性能统计更新
    keyword_loaded = pyqtSignal(str)  # 关键字已加载
    
    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self.worker = None
        self.stop_event = None
        self.is_running = False
        self.log_viewer = None
        self.log_queue = queue.Queue()
        
        # 性能监控变量
        self.performance_stats = {
            'processed_lines': 0,
            'start_time': None,
            'last_update_time': None,
            'processing_rate': 0.0
        }
        
        # 自适应处理参数（与原始版本保持一致）
        self.adaptive_params = {
            'base_batch_size': 50,      # 基础批次大小
            'max_batch_size': 200,      # 最大批次大小
            'base_interval': 50,         # 基础处理间隔(ms)
            'min_interval': 10,          # 最小处理间隔(ms)
            'high_load_threshold': 1000,  # 高负荷阈值（提高以避免采样模式）
            'medium_load_threshold': 50, # 中等负荷阈值
            'max_display_lines': 5000,   # 最大显示行数（默认5000）
            'trim_threshold': 250        # 裁剪触发阈值（max_display_lines的5%）
        }
        
        # 性能缓存
        self.performance_cache = {
            'last_line_count': 0,
            'last_memory_mb': 0.0,
            'last_memory_check': 0,
            'cache_update_interval': 20
        }
        
        # 行计数器
        self._line_count = 0
        
        # 启动日志队列处理定时器
        self.queue_timer = QTimer()
        self.queue_timer.timeout.connect(self.process_log_queue)
        self.queue_timer.start(50)  # 默认50ms
        
        # 性能更新定时器
        self.performance_timer = QTimer()
        self.performance_timer.timeout.connect(self.update_performance_display)
        self.performance_timer.start(1000)  # 每秒更新一次
        
    def start_filtering(self, keyword, use_regex, case_sensitive, color_highlight):
        """开始过滤日志"""
        if not keyword.strip():
            self.status_message.emit("请输入过滤关键字")
            return
        
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        if self.is_running:
            self.status_message.emit("日志过滤已经在运行中")
            return
        
        # 验证正则表达式
        if use_regex:
            try:
                re.compile(keyword)
            except re.error as e:
                QMessageBox.critical(None, "错误", f"正则表达式无效: {e}")
                return
        
        try:
            # 保存过滤参数
            self.filter_keyword = keyword
            self.use_regex = use_regex
            self.case_sensitive = case_sensitive
            self.color_highlight = color_highlight
            
            # 创建停止事件
            self.stop_event = threading.Event()
            
            # 创建工作线程
            self.worker = LogFilterWorker(
                device, keyword, use_regex, case_sensitive,
                self._on_log_received, self.stop_event
            )
            self.worker.start()
            
            self.is_running = True
            
            # 初始化性能统计
            self.performance_stats['start_time'] = datetime.now()
            self.performance_stats['last_update_time'] = datetime.now()
            self.performance_stats['processed_lines'] = 0
            self.performance_stats['processing_rate'] = 0.0
            
            self.filtering_started.emit()
            self.status_message.emit("日志过滤已启动")
            
        except Exception as e:
            self.status_message.emit(f"启动日志过滤失败: {str(e)}")
    
    def stop_filtering(self):
        """停止过滤日志"""
        if not self.is_running:
            self.status_message.emit("日志过滤未运行")
            return
        
        try:
            # 停止worker
            if self.worker:
                self.worker.stop()
                self.worker.join(timeout=5)
            
            self.is_running = False
            self.filtering_stopped.emit()
            self.status_message.emit("日志过滤已停止")
            
            # 重置性能统计
            self.performance_update.emit("")
            
        except Exception as e:
            self.status_message.emit(f"停止日志过滤失败: {str(e)}")
    
    def clear_device_logs(self):
        """清除设备日志缓存"""
        from core.utilities import DeviceUtilities
        device_utilities = DeviceUtilities(self.device_manager)
        device_utilities.status_message.connect(self.status_message.emit)
        device_utilities.clear_device_logs()
    
    def set_log_viewer(self, log_viewer):
        """设置日志查看器引用"""
        self.log_viewer = log_viewer
    
    def save_logs(self):
        """保存日志到文件"""
        if not self.log_viewer:
            self.status_message.emit("日志查看器未初始化")
            return
        
        # 获取日志内容
        log_content = self.log_viewer.text_edit.toPlainText()
        
        if not log_content.strip():
            QMessageBox.warning(None, "警告", "没有日志内容可保存")
            return
        
        # 选择保存位置
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "保存日志文件",
            f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "文本文件 (*.txt);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                QMessageBox.information(None, "成功", f"日志已保存到: {file_path}")
                self.status_message.emit(f"日志已保存到: {file_path}")
            except Exception as e:
                QMessageBox.critical(None, "错误", f"保存失败: {e}")
    
    def clear_logs(self):
        """清空日志显示"""
        if not self.log_viewer:
            self.status_message.emit("日志查看器未初始化")
            return
        
        reply = QMessageBox.question(
            None,
            "确认",
            "确定要清空所有日志吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.log_viewer.text_edit.clear()
            self._line_count = 0
            self.status_message.emit("日志已清空")
            
            # 重置性能统计
            if self.is_running:
                self.performance_stats['processed_lines'] = 0
                self.performance_stats['start_time'] = datetime.now()
                self.performance_stats['processing_rate'] = 0.0
                self.update_performance_display()
    
    def show_display_lines_dialog(self):
        """显示设置最大显示行数的对话框"""
        from PyQt5.QtWidgets import QInputDialog
        
        current_lines = self.adaptive_params['max_display_lines']
        
        lines, ok = QInputDialog.getInt(
            None,
            "设置最大显示行数",
            f"当前设置: {current_lines} 行\n\n请输入新的最大显示行数 (100-100000):",
            current_lines,
            100,
            100000,
            100
        )
        
        if ok:
            self.adaptive_params['max_display_lines'] = lines
            self.adaptive_params['trim_threshold'] = int(lines * 0.05)
            self.status_message.emit(f"最大显示行数已设置为: {lines} 行")
            QMessageBox.information(
                None,
                "成功",
                f"设置已应用!\n最大显示行数: {lines}\ntrim_threshold: {self.adaptive_params['trim_threshold']}"
            )
    
    def simple_filter(self):
        """简单过滤 - TMO CC"""
        keyword = "new cc version|old cc version|doDeviceActivation:Successful|mDeviceGroup|getUserAgent"
        self.start_filtering(keyword, True, False, True)
        self.status_message.emit("已启动简单过滤")
    
    def complete_filter(self):
        """完全过滤 - TMO CC"""
        keyword = "EntitlementServerApi|new cc version|old cc version|doDeviceActivation:Successful|mDeviceGroup|Entitlement-EapAka|EntitlementHandling|UpdateProvider|EntitlementService"
        self.start_filtering(keyword, True, False, True)
        self.status_message.emit("已启动完全过滤")
    
    def load_log_keywords(self):
        """加载log关键字文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "选择log关键字文件",
            "",
            "文本文件 (*.txt);;所有文件 (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                keyword = f.read().strip()
            
            if not keyword:
                QMessageBox.warning(None, "警告", "文件内容为空")
                return
            
            # 发出关键字加载信号，让UI更新输入框
            self.keyword_loaded.emit(keyword)
            self.status_message.emit(f"已加载关键字文件: {file_path}")
            
            # 自动开始过滤
            self.start_filtering(keyword, True, False, True)
            
        except UnicodeDecodeError:
            QMessageBox.critical(None, "错误", "文件编码错误，请确保文件是UTF-8编码")
        except Exception as e:
            QMessageBox.critical(None, "错误", f"加载文件失败:\n{str(e)}")
    
    def _on_log_received(self, log_line):
        """接收日志行 - 添加到队列"""
        self.log_queue.put(log_line)
    
    def process_log_queue(self):
        """处理日志队列 - 自适应批次大小"""
        if not self.is_running or not self.log_viewer:
            return
        
        batch_lines = []
        queue_size = self.log_queue.qsize()
        
        # 根据队列大小动态调整批次大小
        if queue_size > self.adaptive_params['high_load_threshold']:
            # 高负荷：大批次，快速处理
            batch_size = self.adaptive_params['max_batch_size']
        elif queue_size > self.adaptive_params['medium_load_threshold']:
            # 中等负荷：中等批次
            batch_size = int(self.adaptive_params['base_batch_size'] * 1.5)
        else:
            # 低负荷：基础批次
            batch_size = self.adaptive_params['base_batch_size']
        
        try:
            # 批量处理，减少UI更新次数
            # 注意：已禁用采样模式以避免日志丢失
            # 正常处理所有日志行
            while len(batch_lines) < batch_size:
                line = self.log_queue.get_nowait()
                batch_lines.append(line)
        except queue.Empty:
            pass
        
        # 批量添加日志行
        if batch_lines:
            self.add_log_lines_batch(batch_lines)
    
    def add_log_lines_batch(self, lines):
        """批量添加日志行，提高性能"""
        text_edit = self.log_viewer.text_edit
        
        # 移动到末尾
        cursor = text_edit.textCursor()
        cursor.movePosition(cursor.End)
        
        # 批量处理所有行
        for line in lines:
            # 直接使用设备log输出的时间，不添加额外时间戳
            full_line = line.rstrip() + "\n"
            
            # 高亮关键字（如果启用）
            if self.color_highlight and self.filter_keyword:
                self.add_highlighted_line(full_line, cursor)
            else:
                cursor.insertText(full_line)
        
        # 更新性能统计
        self.performance_stats['processed_lines'] += len(lines)
        
        # 高效的行数裁剪机制
        self.trim_log_lines_if_needed(len(lines))
        
        # 滚动到底部
        text_edit.setTextCursor(cursor)
        text_edit.ensureCursorVisible()
    
    def add_highlighted_line(self, line, cursor):
        """添加高亮显示的日志行"""
        keyword = self.filter_keyword
        if not keyword:
            cursor.insertText(line)
            return
        
        # 检查队列负荷，决定高亮策略
        queue_size = self.log_queue.qsize()
        
        # 准备搜索模式
        if self.use_regex:
            try:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                pattern = keyword
            except re.error:
                pattern = re.escape(keyword)
                flags = 0 if self.case_sensitive else re.IGNORECASE
        else:
            pattern = re.escape(keyword)
            flags = 0 if self.case_sensitive else re.IGNORECASE
        
        # 查找匹配
        matches = list(re.finditer(pattern, line, flags))
        
        if not matches:
            cursor.insertText(line)
            return
        
        # 高亮所有匹配（已移除采样模式以避免日志丢失）
        last_end = 0
        for match in matches:
            # 插入普通文本（使用默认格式）
            if match.start() > last_end:
                cursor.setCharFormat(self.log_viewer.default_format)
                cursor.insertText(line[last_end:match.start()])
            
            # 插入高亮文本
            cursor.insertText(match.group(), self.log_viewer.highlight_format)
            last_end = match.end()
        
        # 插入剩余文本（使用默认格式）
        if last_end < len(line):
            cursor.setCharFormat(self.log_viewer.default_format)
            cursor.insertText(line[last_end:])
    
    def trim_log_lines_if_needed(self, added_lines):
        """高效的行数裁剪机制 - 使用trim_threshold避免频繁操作"""
        # 维护行计数器
        self._line_count += added_lines
        
        # 使用统一的trim_threshold值
        trim_threshold = self.adaptive_params['trim_threshold']
        
        # 只有当累计新增行数超过trim_threshold时才检查并裁剪
        if self._line_count > trim_threshold:
            try:
                # 获取当前总行数
                text_edit = self.log_viewer.text_edit
                current_lines = text_edit.document().blockCount()
                
                if current_lines > self.adaptive_params['max_display_lines']:
                    # 计算需要删除的行数
                    lines_to_delete = current_lines - self.adaptive_params['max_display_lines']
                    
                    # 使用文本光标一次性删除超出的行
                    cursor = text_edit.textCursor()
                    cursor.movePosition(cursor.Start)
                    cursor.movePosition(cursor.Down, cursor.MoveAnchor, lines_to_delete)
                    cursor.movePosition(cursor.StartOfLine)
                    cursor.movePosition(cursor.Start, cursor.KeepAnchor)
                    cursor.removeSelectedText()
                    
                    # 更新缓存
                    self.performance_cache['last_line_count'] = self.adaptive_params['max_display_lines']
                    
                    # 重置计数器
                    self._line_count = 0
                    
                    # 输出调试信息
                    print(f"裁剪日志: 删除了 {lines_to_delete} 行，当前行数: {self.adaptive_params['max_display_lines']} (trim_threshold: {trim_threshold})")
                    
            except Exception as e:
                print(f"裁剪日志失败: {e}")
                # 重置计数器
                self._line_count = 0
    
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
        
        # 根据队列大小改变状态
        if queue_size > self.adaptive_params['high_load_threshold']:
            performance_text += " (高负荷)"
        elif queue_size > self.adaptive_params['medium_load_threshold']:
            performance_text += " (中负荷)"
        else:
            performance_text += " (正常)"
        
        self.performance_update.emit(performance_text)
    
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
        try:
            # 计算当前显示的行数（实时计算）
            if self.log_viewer:
                current_display_lines = self.log_viewer.text_edit.document().blockCount()
                
                # 检查是否需要更新内存缓存（基于时间间隔）
                current_time = datetime.now()
                if not hasattr(self, '_last_memory_update') or \
                   (current_time - self._last_memory_update).total_seconds() > 2.0:
                    
                    # 计算内存使用情况（更准确的估算）
                    try:
                        # 获取文本内容长度
                        text_content = self.log_viewer.text_edit.toPlainText()
                        text_length = len(text_content)
                        
                        # 估算内存使用（包括Qt内部开销）
                        # 每个字符大约2-4字节（UTF-8编码 + Qt内部结构）
                        estimated_memory_bytes = text_length * 3
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
            else:
                return 0, 0.0
                
        except Exception:
            # 如果出现异常，返回缓存值
            return self.performance_cache['last_line_count'], self.performance_cache['last_memory_mb']
