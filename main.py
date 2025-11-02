#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手机测试辅助工具 - PyQt5 版本
主程序入口
"""

import sys
import os

# 在打包环境中，提前导入必要的模块以确保PyInstaller包含它们
try:
    import serial
    import serial.tools.list_ports
    from concurrent.futures import ThreadPoolExecutor  # sim_reader需要
except ImportError:
    pass  # 如果未安装相关模块，继续运行（某些功能可能不可用）

# 检测是否在PyInstaller打包环境中运行
def is_pyinstaller():
    """检测是否在PyInstaller打包环境中运行"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# 设置控制台编码（解决Windows下中文乱码问题）
if sys.platform == 'win32':
    import io
    
    # 设置控制台代码页为UTF-8
    try:
        os.system('chcp 65001 >nul 2>&1')
    except:
        pass
    
    # 设置环境变量
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # 重新配置标准输出流（兼容PyInstaller打包）
    if not is_pyinstaller():
        # 只在非PyInstaller环境中重新配置输出流
        try:
            if hasattr(sys.stdout, 'buffer') and sys.stdout.buffer is not None:
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            if hasattr(sys.stderr, 'buffer') and sys.stderr.buffer is not None:
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        except (AttributeError, OSError):
            pass

# 必须在导入PyQt5之前设置高DPI支持
os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
os.environ['QT_SCALE_FACTOR_ROUNDING_POLICY'] = 'PassThrough'
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

# 导入日志系统（尽早初始化）
from core.debug_logger import logger, setup_exception_hook

# 设置全局异常捕获
setup_exception_hook()

# 重定向所有控制台输出到日志文件，避免乱码
def redirect_stdout_to_log():
    """将标准输出重定向到日志文件"""
    # 检测是否是 CLI 模式，CLI 模式下不重定向输出
    if len(sys.argv) > 1:
        cli_flags = ['-w', '-p', '--help', '-h']
        if any(arg in cli_flags for arg in sys.argv):
            # CLI 模式下不重定向输出，保持控制台输出
            return
    
    try:
        # 创建一个自定义的输出类
        class LogRedirector:
            def __init__(self, log_file_path):
                self.log_file_path = log_file_path
                self.original_stdout = sys.stdout
                self.original_stderr = sys.stderr
            
            def write(self, text):
                # 将输出写入日志文件而不是控制台
                try:
                    if self.log_file_path and text.strip():
                        with open(self.log_file_path, 'a', encoding='utf-8') as f:
                            f.write(f"[CONSOLE] {text}")
                except:
                    pass  # 静默处理写入错误
            
            def flush(self):
                pass  # 不需要刷新
            
            def __getattr__(self, name):
                return getattr(self.original_stdout, name)
        
        # 重定向标准输出和错误输出
        if logger.get_log_file_path():
            redirector = LogRedirector(logger.get_log_file_path())
            sys.stdout = redirector
            sys.stderr = redirector
            logger.info("控制台输出已重定向到日志文件")
    except Exception as e:
        # 静默处理重定向错误
        pass

# 执行输出重定向
redirect_stdout_to_log()


def main():
    """主入口 - 根据参数路由到 GUI 或 CLI"""
    try:
        logger.info("=" * 60)
        logger.info("程序启动")
        logger.info("=" * 60)
        
        # 检测是否有 CLI 参数
        if len(sys.argv) > 1:
            cli_flags = ['-w', '-p', '--help', '-h']
            if any(arg in cli_flags for arg in sys.argv):
                logger.info("检测到 CLI 参数，进入 CLI 模式")
                from cli_main import main as cli_main
                cli_main()
                return
        
        # 默认启动 GUI
        logger.info("进入 GUI 模式")
        from gui_main import main as gui_main
        gui_main()
        
    except Exception as e:
        logger.exception("程序启动失败")
        sys.exit(1)


if __name__ == "__main__":
    main()

