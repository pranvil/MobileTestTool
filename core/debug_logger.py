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
        # 日志级别映射（与LogConfig保持一致）
        LEVELS = {
            'DEBUG': 0,
            'INFO': 1,
            'WARNING': 2,
            'ERROR': 3,
            'EXCEPTION': 3  # EXCEPTION级别等同于ERROR
        }
        
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
            """判断指定级别的日志是否应该记录（与LogConfig实现一致）"""
            if not self.get('enabled', True):
                return False
            
            current_level = self.LEVELS.get(self.get('log_level', 'DEBUG'), 1)
            log_level = self.LEVELS.get(level, 1)
            
            return log_level >= current_level
    
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
            # 日志系统初始化错误，记录到stderr
            try:
                sys.stderr.write(f"[DebugLogger] Failed to initialize logger: {e}\n")
            except:
                pass
            self._log_file = None
    
    def _get_log_file_path(self, log_dir):
        """获取日志文件路径，支持按日期轮转"""
        try:
            current_date = datetime.now().date()
            date_str = current_date.strftime('%Y%m%d')
            
            # 检查是否启用日志轮转
            enable_rotation = config.get('enable_rotation', True)
            
            # 检查是否需要按日期轮转
            needs_date_rotation = False
            if enable_rotation and config.get('rotation_by_date', True) and self._current_date and self._current_date != current_date:
                # 日期已变化，需要轮转
                needs_date_rotation = True
            
            # 查找今天的日志文件
            log_filename = f'debug_{date_str}.log'
            log_file_path = os.path.join(log_dir, log_filename)
            
            # 如果需要按日期轮转，返回新日期的文件路径（文件可能不存在）
            if needs_date_rotation:
                self._current_date = current_date
                self._current_file_size = 0
                return log_file_path
            
            # 如果文件存在，检查大小
            if os.path.exists(log_file_path):
                file_size = os.path.getsize(log_file_path)
                max_size = config.get('max_file_size_mb', 10) * 1024 * 1024
                
                # 如果文件超过大小限制，需要轮转
                if enable_rotation and config.get('rotation_by_size', True) and file_size >= max_size:
                    log_file_path = self._rotate_log_file(log_dir, date_str)
            else:
                # 文件不存在，创建新文件
                self._current_file_size = 0
            
            self._current_date = current_date
            return log_file_path
            
        except (OSError, IOError) as e:
            # 文件操作错误，记录到stderr并使用时间戳文件名
            try:
                sys.stderr.write(f"[DebugLogger] Failed to get log file path: {e}\n")
            except:
                pass
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return os.path.join(log_dir, f'debug_{timestamp}.log')
        except Exception as e:
            # 其他错误，记录到stderr并使用时间戳文件名
            try:
                sys.stderr.write(f"[DebugLogger] Unexpected error in _get_log_file_path: {e}\n")
            except:
                pass
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
            
        except (OSError, IOError) as e:
            # 文件操作错误，记录到stderr并使用时间戳文件名
            try:
                sys.stderr.write(f"[DebugLogger] Failed to rotate log file: {e}\n")
            except:
                pass
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return os.path.join(log_dir, f'debug_{timestamp}.log')
        except Exception as e:
            # 其他错误，记录到stderr并使用时间戳文件名
            try:
                sys.stderr.write(f"[DebugLogger] Unexpected error in _rotate_log_file: {e}\n")
            except:
                pass
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
                            try:
                                os.remove(file_path)
                            except (OSError, IOError) as e:
                                # 删除文件失败，记录到stderr（但不影响主流程）
                                try:
                                    sys.stderr.write(f"[DebugLogger] Failed to remove old log file {filename}: {e}\n")
                                except:
                                    pass
                    except (OSError, IOError) as e:
                        # 获取文件修改时间失败，记录到stderr（但不影响主流程）
                        try:
                            sys.stderr.write(f"[DebugLogger] Failed to get mtime for {filename}: {e}\n")
                        except:
                            pass
        except (OSError, IOError) as e:
            # 文件操作错误，记录到stderr
            try:
                sys.stderr.write(f"[DebugLogger] Failed to cleanup old logs: {e}\n")
            except:
                pass
        except Exception as e:
            # 其他错误，记录到stderr
            try:
                sys.stderr.write(f"[DebugLogger] Unexpected error in _cleanup_old_logs: {e}\n")
            except:
                pass
    
    def _write_header(self):
        """写入日志文件头部信息（仅在文件不存在或为空时写入，避免覆盖已有日志）"""
        if not self._log_file:
            return
        
        try:
            # 检查文件是否存在且不为空
            file_exists = os.path.exists(self._log_file)
            file_is_empty = False
            
            if file_exists:
                try:
                    file_is_empty = os.path.getsize(self._log_file) == 0
                except (OSError, IOError):
                    # 如果无法获取文件大小，假设文件不为空，跳过头部写入
                    return
            
            # 只在文件不存在或为空时写入头部
            if not file_exists or file_is_empty:
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
                
                # 使用追加模式写入（如果文件存在但为空）或创建模式（如果文件不存在）
                mode = 'a' if file_exists else 'w'
                with open(self._log_file, mode, encoding='utf-8') as f:
                    f.write(header_content)
                
                if not file_exists:
                    self._current_file_size = len(header_content.encode('utf-8'))
                else:
                    # 如果文件已存在但为空，更新文件大小
                    self._current_file_size = len(header_content.encode('utf-8'))
            
        except (OSError, IOError) as e:
            # 文件操作错误，记录到stderr
            try:
                sys.stderr.write(f"[DebugLogger] Failed to write header: {e}\n")
            except:
                pass
        except Exception as e:
            # 其他错误，记录到stderr
            try:
                sys.stderr.write(f"[DebugLogger] Unexpected error in _write_header: {e}\n")
            except:
                pass
    
    def _get_caller_info(self):
        """获取调用者信息（模块名、函数名、行号）
        
        注意：此方法仅在DEBUG级别或配置启用时调用，以避免性能开销。
        inspect.stack() 是一个相对昂贵的操作，应该谨慎使用。
        """
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
        except Exception:
            # 获取调用者信息失败时静默处理（避免影响日志记录）
            pass
        
        return None, None, None
    
    def _format_log_message(self, message, level):
        """格式化日志消息（支持多行输出）
        
        性能优化：仅在DEBUG级别获取调用者信息，其他级别跳过inspect.stack()调用
        以提升性能。如需在其他级别启用调用者信息，可通过配置控制。
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # 构建日志行头部
        log_parts = [f"[{timestamp}]", f"[{level}]"]
        
        # 仅在DEBUG级别获取调用者信息（性能优化：避免频繁调用inspect.stack()）
        # 或者根据配置决定是否包含调用者信息
        should_include_caller = (level == 'DEBUG') or (
            config.get('include_module', True) or 
            config.get('include_function', True) or 
            config.get('include_line', True)
        )
        
        if should_include_caller:
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
        
        header = " ".join(log_parts)
        message_str = str(message)
        
        # 支持多行消息：每行都添加头部信息
        lines = message_str.split('\n')
        if len(lines) == 1:
            # 单行消息，直接返回
            return f"{header} {message_str}\n"
        else:
            # 多行消息，第一行有完整头部，后续行只有缩进
            result = []
            for i, line in enumerate(lines):
                if i == 0:
                    result.append(f"{header} {line}")
                else:
                    # 后续行使用缩进，保持对齐
                    indent = " " * len(header) + " "
                    result.append(f"{indent}{line}")
            return "\n".join(result) + "\n"
    
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
                
            except Exception as e:
                # 后台写入线程错误，记录到stderr
                try:
                    sys.stderr.write(f"[DebugLogger] Error in write worker thread: {e}\n")
                except:
                    pass
    
    def _flush_buffer(self):
        """刷新缓冲区，将日志写入文件"""
        if not self._buffer or not self._log_file:
            return
        
        try:
            with self._lock:
                # 检查是否启用日志轮转
                enable_rotation = config.get('enable_rotation', True)
                
                # 检查是否需要按日期轮转
                current_date = datetime.now().date()
                if enable_rotation and config.get('rotation_by_date', True) and self._current_date and self._current_date != current_date:
                    log_dir = os.path.dirname(self._log_file)
                    # 获取新日期的日志文件路径
                    self._log_file = self._get_log_file_path(log_dir)
                    # 为新文件写入头部信息
                    self._write_header()
                    self._current_date = current_date
                    self._current_file_size = len("".join(self._buffer).encode('utf-8'))
                
                # 检查文件是否需要按大小轮转
                if os.path.exists(self._log_file):
                    file_size = os.path.getsize(self._log_file)
                    max_size = config.get('max_file_size_mb', 10) * 1024 * 1024
                    
                    if enable_rotation and config.get('rotation_by_size', True) and file_size >= max_size:
                        log_dir = os.path.dirname(self._log_file)
                        date_str = datetime.now().date().strftime('%Y%m%d')
                        self._log_file = self._rotate_log_file(log_dir, date_str)
                        # 为轮转后的新文件写入头部信息
                        self._write_header()
                        self._current_file_size = 0
                
                # 批量写入日志
                log_content = "".join(self._buffer)
                
                with open(self._log_file, 'a', encoding='utf-8') as f:
                    f.write(log_content)
                
                self._current_file_size += len(log_content.encode('utf-8'))
                self._buffer.clear()
                self._last_flush_time = time.time()
                
        except (OSError, IOError) as e:
            # 文件操作错误，记录到stderr
            try:
                sys.stderr.write(f"[DebugLogger] Failed to flush buffer: {e}\n")
            except:
                pass
        except Exception as e:
            # 其他错误，记录到stderr
            try:
                sys.stderr.write(f"[DebugLogger] Unexpected error in _flush_buffer: {e}\n")
            except:
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
                # 队列已满，直接写入文件（设计策略：确保重要日志不丢失）
                # 注意：这会绕过缓冲区机制，但可以保证在队列满载时日志仍能记录
                # 这是有意设计的行为，用于处理突发大量日志的场景
                try:
                    with self._lock:
                        with open(self._log_file, 'a', encoding='utf-8') as f:
                            f.write(log_line)
                except (OSError, IOError) as e:
                    # 文件写入错误，记录到stderr
                    try:
                        sys.stderr.write(f"[DebugLogger] Failed to write log directly: {e}\n")
                    except:
                        pass
                except Exception as e:
                    # 其他错误，记录到stderr
                    try:
                        sys.stderr.write(f"[DebugLogger] Unexpected error writing log directly: {e}\n")
                    except:
                        pass
        
        except Exception as e:
            # 记录日志时出错，记录到stderr（避免日志系统自身错误影响程序）
            try:
                sys.stderr.write(f"[DebugLogger] Failed to log message: {e}\n")
            except:
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
                # 队列已满，直接写入文件（设计策略：确保重要日志不丢失）
                # 注意：这会绕过缓冲区机制，但可以保证异常信息在队列满载时仍能记录
                # 这是有意设计的行为，用于处理突发大量日志的场景
                try:
                    with self._lock:
                        with open(self._log_file, 'a', encoding='utf-8') as f:
                            f.write(log_content)
                except (OSError, IOError) as e:
                    # 文件写入错误，记录到stderr
                    try:
                        sys.stderr.write(f"[DebugLogger] Failed to write exception log directly: {e}\n")
                    except:
                        pass
                except Exception as e:
                    # 其他错误，记录到stderr
                    try:
                        sys.stderr.write(f"[DebugLogger] Unexpected error writing exception log directly: {e}\n")
                    except:
                        pass
        
        except Exception as e:
            # 记录异常时出错，记录到stderr
            try:
                sys.stderr.write(f"[DebugLogger] Failed to log exception: {e}\n")
            except:
                pass
    
    def separator(self):
        """写入分隔线"""
        self.log("=" * 60, "INFO")
    
    def get_log_file_path(self):
        """获取日志文件路径"""
        return self._log_file
    
    def flush(self):
        """立即刷新所有待写入的日志（使用线程安全的队列操作）"""
        try:
            # 使用非阻塞获取方式处理队列中的所有消息（线程安全）
            # 避免使用empty()检查，因为它在多线程环境中不可靠
            while True:
                try:
                    log_entry = self._log_queue.get_nowait()
                    self._buffer.append(log_entry)
                except queue.Empty:
                    # 队列为空，退出循环
                    break
            
            # 刷新缓冲区
            self._flush_buffer()
        except Exception as e:
            # 记录刷新错误到stderr
            try:
                sys.stderr.write(f"[DebugLogger] Failed to flush logs: {e}\n")
            except:
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
        
        except Exception as e:
            # 关闭日志系统时出错，记录到stderr
            try:
                sys.stderr.write(f"[DebugLogger] Failed to shutdown logger: {e}\n")
            except:
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
