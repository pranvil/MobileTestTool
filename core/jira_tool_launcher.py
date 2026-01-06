#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JIRA工具启动器
负责检查配置、启动JIRA工具窗口
"""

from PySide6.QtWidgets import QMessageBox, QWidget
from PySide6.QtCore import QThread, Signal, QObject, Qt
from core.debug_logger import logger
from core.jira_config_manager import get_token


class JiraToolLauncherWorker(QThread):
    """JIRA工具启动工作线程"""
    
    finished = Signal(bool, str)  # 成功标志, 错误消息
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.jira_window = None
    
    def run(self):
        """在工作线程中运行"""
        try:
            # 以包方式导入，避免与主工程 `ui.main_window` 冲突
            from Jira_tool.ui.main_window import MainWindow as JiraMainWindow
            
            # 创建JIRA主窗口
            # 注意：Qt窗口必须在主线程创建，所以我们使用信号通知主线程
            self.jira_window = JiraMainWindow
            self.finished.emit(True, "")
            
        except Exception as e:
            error_msg = str(e)
            logger.exception(f"启动JIRA工具失败: {error_msg}")
            self.finished.emit(False, error_msg)


def launch_jira_tool(parent_window):
    """
    启动JIRA工具
    
    Args:
        parent_window: 父窗口对象（用于显示消息框）
    
    Returns:
        bool: 是否成功启动
    """
    try:
        # 检查token配置
        token = get_token()
        if not token or not token.strip():
            # Token未配置，显示提示
            lang_manager = None
            if parent_window and hasattr(parent_window, 'lang_manager'):
                lang_manager = parent_window.lang_manager
            
            tr = lambda text: lang_manager.tr(text) if lang_manager else text
            
            msg_box = QMessageBox(parent_window)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle(tr("配置缺失"))
            msg_box.setText(tr("JIRA API Token未配置"))
            msg_box.setInformativeText(
                tr("请先配置JIRA API Token才能使用JIRA工具。\n\n")
                + tr("获取Token方法：\n")
                + tr("1. 登录JIRA Profile\n")
                + tr("2. 在左侧菜单点击 Personal Access Tokens\n")
                + tr("3. 点击 Create token，设置名称和过期时间\n")
                + tr("4. 复制生成的Token\n\n")
                + tr("配置方法：请在工具配置中设置JIRA相关配置。")
            )
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
            return False
        
        # Token已配置，启动JIRA工具窗口
        # 注意：Qt窗口必须在主线程创建
        from Jira_tool.ui.main_window import MainWindow as JiraMainWindow
        
        # 创建JIRA主窗口（在主线程中创建）
        jira_window = JiraMainWindow(parent_window)
        jira_window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        jira_window.show()
        
        logger.info("JIRA工具窗口已启动")
        return True
        
    except Exception as e:
        error_msg = str(e)
        logger.exception(f"启动JIRA工具失败: {error_msg}")
        
        # 显示错误消息
        lang_manager = None
        if parent_window and hasattr(parent_window, 'lang_manager'):
            lang_manager = parent_window.lang_manager
        
        tr = lambda text: lang_manager.tr(text) if lang_manager else text
        
        msg_box = QMessageBox(parent_window)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(tr("错误"))
        msg_box.setText(tr("启动JIRA工具失败"))
        msg_box.setInformativeText(tr(f"错误信息：{error_msg}"))
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
        
        return False
