#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试日志模块
用于记录程序运行时的详细信息，方便排查问题
改进版本：支持日志级别控制、线程安全、缓冲机制、日志轮转等
"""

import os
import sys
import traceback
import threading
import queue
import time
import inspect
from datetime import datetime, timedelta
from pathlib import Path

try:
    from core.log_config import config
except Exception:
    # 如果导入失败，创建一个简单的默认配置对象
    class DefaultConfig:
        def get(self, key, default=None):
            defaults = {
                'enabled': True,
                'log_level': 'DEBUG',
                'max_file_size_mb': 10,
                'max_files': 5,
                'retention_days': 7,
                'buffer_size': 100,
                'flush_interval': 1.0,
                'rotation_by_size': True,
                'rotation_by_date': True,
                'include_module': True,
                'include_function': True,
                'include_line': True
            }
            return defaults.get(key, default)
        
        def should_log(self, level):
            return True
    
    config = DefaultConfig()


class DebugLogger:
    """调试日志记录器 - 改进版本"""
    
    _instance = None
    _log_file = None
    _log_queue = None
    _write_thread = None
    _stop_event = None
    _lock = None
    _buffer = []
    _last_flush_time = None
    _current_file_size = 0
    _current_date = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _tr(self, text):
        """安全地获取翻译文本"""
        if hasattr(self, 'lang_manager') and self.lang_manager:
            return self.lang_manager.tr(text)
        return text
    
    def _initialize(self):
        """初始化日志系统"""
        try:
            # 检查是否启用日志
            if not config.get('enabled', True):
                self._log_file = None
                return
            
            # 获取程序运行目录
            if getattr(sys, 'frozen', False):
                # 打包环境：使用exe所在目录
                app_dir = os.path.dirname(os.path.abspath(sys.executable))
            else:
                # 开发环境：使用项目根目录
                app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # 创建logs目录
            log_dir = os.path.join(app_dir, 'logs')
            os.makedirs(log_dir, exist_ok=True)
            
            # 清理旧日志
            self._cleanup_old_logs(log_dir)
            
            # 初始化线程安全相关
            self._lock = threading.Lock()
            self._log_queue = queue.Queue(maxsize=config.get('buffer_size', 100))
            self._stop_event = threading.Event()
            self._buffer = []
            self._last_flush_time = time.time()
            self._current_file_size = 0
            self._current_date = datetime.now().date()
            
            # 创建或获取日志文件
            self._log_file = self._get_log_file_path(log_dir)
            
            # 写入初始信息
            self._write_header()
            
            # 启动后台写入线程
            self._write_thread = threading.Thread(target=self._write_worker, daemon=True)
            self._write_thread.start()
            
        except Exception as e:
            # 静默处理日志系统初始化错误
            self._log_file = None
    
    def _get_log_file_path(self, log_dir):
        """获取日志文件路径，支持按日期轮转"""
        try:
            current_date = datetime.now().date()
            date_str = current_date.strftime('%Y%m%d')
            
            # 检查是否需要按日期轮转
            if config.get('rotation_by_date', True) and self._current_date and self._current_date != current_date:
                # 日期已变化，需要轮转
                pass
            
            # 查找今天的日志文件
            log_filename = f'debug_{date_str}.log'
            log_file_path = os.path.join(log_dir, log_filename)
            
            # 如果文件存在，检查大小
            if os.path.exists(log_file_path):
                file_size = os.path.getsize(log_file_path)
                max_size = config.get('max_file_size_mb', 10) * 1024 * 1024
                
                # 如果文件超过大小限制，需要轮转
                if config.get('rotation_by_size', True) and file_size >= max_size:
                    log_file_path = self._rotate_log_file(log_dir, date_str)
            else:
                # 文件不存在，创建新文件
                self._current_file_size = 0
            
            self._current_date = current_date
            return log_file_path
            
        except Exception:
            # 如果出错，使用时间戳文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return os.path.join(log_dir, f'debug_{timestamp}.log')
    
    def _rotate_log_file(self, log_dir, date_str):
        """轮转日志文件"""
        try:
            # 查找已存在的轮转文件
            base_name = f'debug_{date_str}'
            existing_files = []
            
            for filename in os.listdir(log_dir):
                if filename.startswith(base_name) and filename.endswith('.log'):
                    existing_files.append(filename)
            
            # 按序号排序
            existing_files.sort()
            
            # 计算下一个序号
            if existing_files:
                last_file = existing_files[-1]
                # 提取序号（格式：debug_20250107_001.log）
                if '_' in last_file:
                    try:
                        parts = last_file.rsplit('_', 1)
                        if len(parts) == 2:
                            seq_num = int(parts[1].replace('.log', ''))
                            next_seq = seq_num + 1
                        else:
                            next_seq = 1
                    except:
                        next_seq = 1
                else:
                    next_seq = 1
            else:
                next_seq = 1
            
            # 重命名当前文件
            old_file = os.path.join(log_dir, f'{base_name}.log')
            if os.path.exists(old_file):
                new_file = os.path.join(log_dir, f'{base_name}_{next_seq:03d}.log')
                os.rename(old_file, new_file)
            
            # 清理旧文件，只保留最近的N个文件
            max_files = config.get('max_files', 5)
            if len(existing_files) >= max_files:
                # 删除最旧的文件
                for i in range(len(existing_files) - max_files + 1):
                    old_file_path = os.path.join(log_dir, existing_files[i])
                    if os.path.exists(old_file_path):
                        try:
                            os.remove(old_file_path)
                        except:
                            pass
            
            # 返回新的日志文件路径
            self._current_file_size = 0
            return os.path.join(log_dir, f'{base_name}.log')
            
        except Exception:
            # 如果轮转失败，使用时间戳
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return os.path.join(log_dir, f'debug_{timestamp}.log')
    
    def _cleanup_old_logs(self, log_dir):
        """清理指定天数前的旧日志文件"""
        try:
            retention_days = config.get('retention_days', 7)
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(days=retention_days)
            
            # 遍历日志目录中的所有文件
            for filename in os.listdir(log_dir):
                if filename.startswith('debug_') and filename.endswith('.log'):
                    file_path = os.path.join(log_dir, filename)
                    
                    try:
                        # 获取文件的修改时间
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        # 如果文件超过保留天数，删除它
                        if file_mtime < cutoff_time:
                            os.remove(file_path)
                    except:
                        pass
        
        except Exception:
            pass
    
    def _write_header(self):
        """写入日志文件头部信息"""
        if not self._log_file:
            return
        
        try:
            header_lines = [
                "=" * 80,
                "MobileTestTool Debug Log",
                f"{self._tr('启动时间:')} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"{self._tr('Python版本:')} {sys.version.split()[0]}",
                f"{self._tr('运行目录:')} {os.getcwd()}",
            ]
            
            if getattr(sys, 'frozen', False):
                header_lines.append(f"{self._tr('可执行文件:')} {sys.executable}")
                header_lines.append(f"{self._tr('运行模式:')} {self._tr('打包EXE模式')}")
            else:
                header_lines.append(f"{self._tr('运行模式:')} {self._tr('开发模式')}")
            
            header_lines.append("=" * 80)
            header_lines.append("")
            
            header_content = "\n".join(header_lines) + "\n"
            
            with open(self._log_file, 'w', encoding='utf-8') as f:
                f.write(header_content)
            
            self._current_file_size = len(header_content.encode('utf-8'))
            
        except Exception:
            pass
    
    def _get_caller_info(self):
        """获取调用者信息（模块名、函数名、行号）"""
        try:
            # 获取调用栈，跳过当前函数和log相关函数
            stack = inspect.stack()
            # 查找真正的调用者（跳过log、info、warning、error、debug、exception等方法）
            skip_functions = ['log', 'info', 'warning', 'error', 'debug', 'exception', '_format_log_message']
            
            for frame_info in stack[2:]:  # 跳过当前函数和_format_log_message
                if frame_info.function not in skip_functions:
                    module_name = frame_info.frame.f_globals.get('__name__', 'unknown')
                    function_name = frame_info.function
                    line_number = frame_info.lineno
                    
                    # 简化模块名（只保留最后一部分）
                    if '.' in module_name:
                        module_name = module_name.split('.')[-1]
                    
                    return module_name, function_name, line_number
        except:
            pass
        
        return None, None, None
    
    def _format_log_message(self, message, level):
        """格式化日志消息"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # 构建日志行
        log_parts = [f"[{timestamp}]", f"[{level}]"]
        
        # 添加调用者信息
        if config.get('include_module', True) or config.get('include_function', True) or config.get('include_line', True):
            module_name, function_name, line_number = self._get_caller_info()
            
            context_parts = []
            if config.get('include_module', True) and module_name:
                context_parts.append(module_name)
            if config.get('include_function', True) and function_name:
                context_parts.append(function_name)
            if config.get('include_line', True) and line_number:
                context_parts.append(f"L{line_number}")
            
            if context_parts:
                log_parts.append(f"[{':'.join(context_parts)}]")
        
        log_parts.append(str(message))
        
        return " ".join(log_parts) + "\n"
    
    def _write_worker(self):
        """后台写入线程工作函数"""
        flush_interval = config.get('flush_interval', 1.0)
        
        while not self._stop_event.is_set():
            try:
                # 从队列获取日志消息
                try:
                    log_entry = self._log_queue.get(timeout=0.5)
                except queue.Empty:
                    # 队列为空，检查是否需要刷新缓冲区
                    current_time = time.time()
                    if self._buffer and (current_time - self._last_flush_time) >= flush_interval:
                        self._flush_buffer()
                    continue
                
                # 添加到缓冲区
                self._buffer.append(log_entry)
                
                # 如果缓冲区达到一定大小，立即刷新
                if len(self._buffer) >= 10:
                    self._flush_buffer()
                else:
                    # 检查是否需要定时刷新
                    current_time = time.time()
                    if (current_time - self._last_flush_time) >= flush_interval:
                        self._flush_buffer()
                
            except Exception:
                pass
    
    def _flush_buffer(self):
        """刷新缓冲区，将日志写入文件"""
        if not self._buffer or not self._log_file:
            return
        
        try:
            with self._lock:
                # 检查是否需要按日期轮转
                current_date = datetime.now().date()
                if config.get('rotation_by_date', True) and self._current_date and self._current_date != current_date:
                    log_dir = os.path.dirname(self._log_file)
                    date_str = current_date.strftime('%Y%m%d')
                    self._log_file = self._get_log_file_path(log_dir)
                    self._current_date = current_date
                    self._current_file_size = 0
                
                # 检查文件是否需要按大小轮转
                if os.path.exists(self._log_file):
                    file_size = os.path.getsize(self._log_file)
                    max_size = config.get('max_file_size_mb', 10) * 1024 * 1024
                    
                    if config.get('rotation_by_size', True) and file_size >= max_size:
                        log_dir = os.path.dirname(self._log_file)
                        date_str = datetime.now().date().strftime('%Y%m%d')
                        self._log_file = self._rotate_log_file(log_dir, date_str)
                        self._current_file_size = 0
                
                # 批量写入日志
                log_content = "".join(self._buffer)
                
                with open(self._log_file, 'a', encoding='utf-8') as f:
                    f.write(log_content)
                
                self._current_file_size += len(log_content.encode('utf-8'))
                self._buffer.clear()
                self._last_flush_time = time.time()
                
        except Exception:
            pass
    
    def log(self, message, level="INFO"):
        """
        记录日志
        
        Args:
            message: 日志消息
            level: 日志级别 (INFO, WARNING, ERROR, DEBUG, EXCEPTION)
        """
        # 检查是否启用日志
        if not self._log_file or not config.should_log(level):
            return
        
        try:
            # 格式化日志消息
            log_line = self._format_log_message(message, level)
            
            # 添加到队列（非阻塞）
            try:
                self._log_queue.put_nowait(log_line)
            except queue.Full:
                # 队列已满，直接写入（避免丢失重要日志）
                try:
                    with self._lock:
                        with open(self._log_file, 'a', encoding='utf-8') as f:
                            f.write(log_line)
                except:
                    pass
        
        except Exception:
            pass
    
    def info(self, message):
        """记录INFO级别日志"""
        self.log(message, "INFO")
    
    def warning(self, message):
        """记录WARNING级别日志"""
        self.log(message, "WARNING")
    
    def error(self, message):
        """记录ERROR级别日志"""
        self.log(message, "ERROR")
    
    def debug(self, message):
        """记录DEBUG级别日志"""
        self.log(message, "DEBUG")
    
    def exception(self, message="发生异常"):
        """
        记录异常信息（包含完整的堆栈跟踪）
        """
        if not self._log_file or not config.should_log("ERROR"):
            return
        
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            exc_info = traceback.format_exc()
            
            # 获取调用者信息
            module_name, function_name, line_number = self._get_caller_info()
            context_info = ""
            if module_name or function_name or line_number:
                context_parts = []
                if module_name:
                    context_parts.append(module_name)
                if function_name:
                    context_parts.append(function_name)
                if line_number:
                    context_parts.append(f"L{line_number}")
                context_info = f" [{':'.join(context_parts)}]"
            
            log_content = f"[{timestamp}] [EXCEPTION]{context_info} {message}\n"
            log_content += "-" * 80 + "\n"
            log_content += exc_info
            log_content += "-" * 80 + "\n\n"
            
            # 添加到队列
            try:
                self._log_queue.put_nowait(log_content)
            except queue.Full:
                # 队列已满，直接写入
                try:
                    with self._lock:
                        with open(self._log_file, 'a', encoding='utf-8') as f:
                            f.write(log_content)
                except:
                    pass
        
        except Exception:
            pass
    
    def separator(self):
        """写入分隔线"""
        self.log("=" * 60, "INFO")
    
    def get_log_file_path(self):
        """获取日志文件路径"""
        return self._log_file
    
    def flush(self):
        """立即刷新所有待写入的日志"""
        try:
            # 等待队列中的所有消息
            while not self._log_queue.empty():
                try:
                    log_entry = self._log_queue.get_nowait()
                    self._buffer.append(log_entry)
                except queue.Empty:
                    break
            
            # 刷新缓冲区
            self._flush_buffer()
        except Exception:
            pass
    
    def shutdown(self):
        """关闭日志系统"""
        try:
            # 停止后台线程
            if self._stop_event:
                self._stop_event.set()
            
            # 刷新所有待写入的日志
            self.flush()
            
            # 等待写入线程结束
            if self._write_thread and self._write_thread.is_alive():
                self._write_thread.join(timeout=2.0)
        
        except Exception:
            pass


# 创建全局日志实例
logger = DebugLogger()


def log_function_call(func):
    """
    装饰器：记录函数调用
    
    使用方法:
        @log_function_call
        def my_function():
            pass
    """
    def wrapper(*args, **kwargs):
        logger.debug(logger._tr("调用函数:") + " " + func.__name__)
        try:
            result = func(*args, **kwargs)
            logger.debug(logger._tr("函数") + " " + func.__name__ + " " + logger._tr("执行成功"))
            return result
        except Exception as e:
            logger.exception(logger._tr("函数") + " " + func.__name__ + " " + logger._tr("执行失败"))
            raise
    return wrapper


def setup_exception_hook():
    """
    设置全局异常捕获钩子
    捕获所有未处理的异常
    """
    def exception_hook(exc_type, exc_value, exc_traceback):
        """异常钩子函数"""
        if issubclass(exc_type, KeyboardInterrupt):
            # 忽略键盘中断
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.error("=" * 80)
        logger.error("捕获到未处理的异常！")
        logger.error(f"{logger._tr('异常类型:')} {exc_type.__name__}")
        logger.error(f"{logger._tr('异常信息:')} {exc_value}")
        logger.error("-" * 80)
        
        # 记录完整的堆栈信息
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        for line in tb_lines:
            logger.log(line.rstrip(), "ERROR")
        
        logger.error("=" * 80)
        
        # 显示错误对话框（如果可能）
        try:
            from PyQt5.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("❌ " + logger._tr("程序错误"))
            msg.setText(logger._tr("程序遇到错误：") + str(exc_value))
            msg.setInformativeText(logger._tr("详细信息请查看日志文件：") + "\n" + (logger.get_log_file_path() or ""))
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
        except:
            pass
        
        # 调用默认的异常处理
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    sys.excepthook = exception_hook
    logger.info("全局异常捕获已启用")
