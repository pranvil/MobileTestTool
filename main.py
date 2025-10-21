#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手机测试辅助工具 - PyQt5 版本
主程序入口
"""

import sys
import os

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

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from ui.main_window import MainWindow


def main():
    """主函数"""
    try:
        logger.info("=" * 60)
        logger.info("程序启动")
        logger.info("=" * 60)
        
        # 在创建QApplication之前启用高DPI缩放（Qt 5.6+）
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
        # 创建应用程序
        logger.info("创建QApplication实例...")
        app = QApplication(sys.argv)
        
        # 设置应用程序属性
        app.setApplicationName("手机测试辅助工具")
        app.setApplicationVersion("0.7-PyQt5")
        app.setOrganizationName("MobileTestTool")
        logger.info("应用程序属性设置完成")
        
        # 设置字体渲染质量和大小
        font = app.font()
        font.setHintingPreference(QFont.PreferFullHinting)
        font.setStyleStrategy(QFont.PreferAntialias)
        
        # 智能字体大小补偿 - 解决DPI感知后字体变小的问题
        screen = app.primaryScreen()
        current_dpi = screen.logicalDotsPerInch()
        dpi_scale = current_dpi / 96.0
        
        # 根据DPI缩放智能调整字体大小
        if dpi_scale <= 1.0:
            # 标准DPI (96) 或更小
            font.setPointSize(9)
            logger.info(f"标准DPI ({current_dpi}), 字体大小: 9pt")
        elif dpi_scale <= 1.25:
            # 125% DPI (120)
            font.setPointSize(10)
            logger.info(f"125% DPI ({current_dpi}), 字体大小: 10pt")
        elif dpi_scale <= 1.5:
            # 150% DPI (144)
            font.setPointSize(11)
            logger.info(f"150% DPI ({current_dpi}), 字体大小: 11pt")
        elif dpi_scale <= 2.0:
            # 200% DPI (192)
            font.setPointSize(12)
            logger.info(f"200% DPI ({current_dpi}), 字体大小: 12pt")
        else:
            # 更高DPI
            font.setPointSize(13)
            logger.info(f"超高DPI ({current_dpi}), 字体大小: 13pt")
        
        app.setFont(font)
        logger.info("字体渲染优化已启用")
        
        # 记录DPI信息
        dpi = screen.logicalDotsPerInch()
        scale_factor = screen.devicePixelRatio()
        logger.info(f"显示器DPI: {dpi}, 缩放比例: {scale_factor}")
        logger.info("高DPI支持已启用")
        
        # 创建主窗口
        logger.info("开始创建主窗口...")
        window = MainWindow()
        logger.info("主窗口创建成功")
        
        logger.info("显示主窗口...")
        window.show()
        logger.info("主窗口已显示")
        
        logger.info("进入事件循环...")
        logger.info(f"日志文件位置: {logger.get_log_file_path()}")
        logger.separator()
        
        # 运行应用程序
        exit_code = app.exec_()
        
        logger.info("=" * 60)
        logger.info(f"程序正常退出，退出码: {exit_code}")
        logger.info("=" * 60)
        
        sys.exit(exit_code)
        
    except Exception as e:
        logger.exception("程序启动失败")
        
        # 尝试显示错误对话框
        try:
            from PyQt5.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("启动失败")
            msg.setText(f"程序启动失败: {str(e)}")
            msg.setInformativeText(f"详细信息请查看日志文件：\n{logger.get_log_file_path()}")
            msg.exec_()
        except:
            # 静默处理启动失败错误，避免控制台乱码
            pass
        
        sys.exit(1)


if __name__ == "__main__":
    main()

