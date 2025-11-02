#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手机测试辅助工具 - GUI 入口
纯粹的 GUI 模式启动逻辑
"""

import sys
import os

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon

from ui.main_window import MainWindow
from core.debug_logger import logger


def _set_application_icon(app):
    """设置应用程序图标"""
    try:
        if hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS'):
            # PyInstaller 环境
            icon_path = os.path.join(sys._MEIPASS, 'icon.ico')
        else:
            # 开发环境
            icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
        
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            logger.info(f"应用程序图标已设置: {icon_path}")
        else:
            logger.warning(f"图标文件不存在: {icon_path}")
    except Exception as e:
        logger.warning(f"设置图标失败: {str(e)}")


def main():
    """GUI 入口函数"""
    try:
        logger.info("=" * 60)
        logger.info("程序启动 (GUI 模式)")
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
        
        # 设置应用程序图标
        _set_application_icon(app)
        
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
        logger.exception("GUI 启动失败")
        
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

