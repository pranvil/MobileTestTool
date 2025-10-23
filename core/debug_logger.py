#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试日志模块
用于记录程序运行时的详细信息，方便排查问题
"""

import os
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path


class DebugLogger:
    """调试日志记录器"""
    
    _instance = None
    _log_file = None
    
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
        """初始化日志文件"""
        try:
            # 获取程序运行目录
            if getattr(sys, 'frozen', False):
                # 打包后的exe运行目录
                app_dir = os.path.dirname(sys.executable)
            else:
                # 开发环境
                app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # 创建logs目录
            log_dir = os.path.join(app_dir, 'logs')
            os.makedirs(log_dir, exist_ok=True)
            
            # 清理7天前的旧日志
            self._cleanup_old_logs(log_dir)
            
            # 生成日志文件名（带时间戳）
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_filename = f'debug_{timestamp}.txt'
            self._log_file = os.path.join(log_dir, log_filename)
            
            # 写入初始信息
            self._write_header()
            
        except Exception as e:
            # 静默处理日志系统初始化错误，避免控制台乱码
            self._log_file = None
    
    def _cleanup_old_logs(self, log_dir, days=7):
        """
        清理指定天数前的旧日志文件
        
        Args:
            log_dir: 日志目录路径
            days: 保留的天数，默认7天
        """
        try:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(days=days)
            
            # 遍历日志目录中的所有文件
            for filename in os.listdir(log_dir):
                if filename.startswith('debug_') and filename.endswith('.txt'):
                    file_path = os.path.join(log_dir, filename)
                    
                    # 获取文件的修改时间
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    # 如果文件超过保留天数，删除它
                    if file_mtime < cutoff_time:
                        os.remove(file_path)
                        # 静默删除旧日志文件，避免控制台乱码
        
        except Exception as e:
            # 静默处理清理旧日志错误，避免控制台乱码
            pass
    
    def _write_header(self):
        """写入日志文件头部信息"""
        try:
            with open(self._log_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("MobileTestTool Debug Log\n")
                f.write(self._tr("启动时间:") + " " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n")
                f.write(self._tr("Python版本:") + " " + sys.version + "\n")
                f.write(self._tr("运行目录:") + " " + os.getcwd() + "\n")
                if getattr(sys, 'frozen', False):
                    f.write(self._tr("可执行文件:") + " " + sys.executable + "\n")
                    f.write(self._tr("运行模式:") + " " + self._tr("打包EXE模式") + "\n")
                else:
                    f.write(self._tr("运行模式:") + " " + self._tr("开发模式") + "\n")
                f.write("=" * 80 + "\n\n")
        except Exception as e:
            # 静默处理写入日志头部错误，避免控制台乱码
            pass
    
    def log(self, message, level="INFO"):
        """
        记录日志
        
        Args:
            message: 日志消息
            level: 日志级别 (INFO, WARNING, ERROR, DEBUG)
        """
        if not self._log_file:
            return
        
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            log_line = f"[{timestamp}] [{level}] {message}\n"
            
            with open(self._log_file, 'a', encoding='utf-8') as f:
                f.write(log_line)
            
            # 不再打印到控制台，避免乱码问题
            # 所有日志信息都保存在文件中，用户可以通过日志文件查看详细信息
            
        except Exception as e:
            # 静默处理日志写入错误，避免控制台乱码
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
        if not self._log_file:
            return
        
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            exc_info = traceback.format_exc()
            
            log_content = f"[{timestamp}] [EXCEPTION] {message}\n"
            log_content += "-" * 80 + "\n"
            log_content += exc_info
            log_content += "-" * 80 + "\n\n"
            
            with open(self._log_file, 'a', encoding='utf-8') as f:
                f.write(log_content)
            
            # 不再打印到控制台，避免乱码问题
            # 异常信息已保存到日志文件中
            
        except Exception as e:
            # 静默处理异常记录错误，避免控制台乱码
            pass
    
    def separator(self):
        """写入分隔线"""
        self.log("=" * 60, "")
    
    def get_log_file_path(self):
        """获取日志文件路径"""
        return self._log_file


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
            msg.setInformativeText(logger._tr("详细信息请查看日志文件：") + "\n" + logger.get_log_file_path())
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
        except:
            pass
        
        # 调用默认的异常处理
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    sys.excepthook = exception_hook
    logger.info("全局异常捕获已启用")

