#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
办公工具 Tab
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QScrollArea, QLabel, QFrame)
from PySide6.QtCore import Signal, Qt, QObject
from ui.widgets.shadow_utils import add_card_shadow
from core.debug_logger import logger


class OfficeToolTab(QWidget):
    """办公工具 Tab"""
    
    # 信号定义
    # JIRA工具
    show_jira_tool = Signal()
    
    def __init__(self, parent=None):
        try:
            super().__init__(parent)
            # 从父窗口获取语言管理器
            if parent and hasattr(parent, 'lang_manager'):
                self.lang_manager = parent.lang_manager
            else:
                # 如果没有父窗口或语言管理器，使用单例
                import sys
                import os
                try:
                    from core.language_manager import LanguageManager
                    self.lang_manager = LanguageManager.get_instance()
                except ModuleNotFoundError:
                    # 如果导入失败，确保正确的路径在 sys.path 中
                    # 支持 PyInstaller 打包环境
                    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                        # PyInstaller 环境：使用 sys._MEIPASS
                        base_path = sys._MEIPASS
                        if base_path not in sys.path:
                            sys.path.insert(0, base_path)
                    else:
                        # 开发环境：使用 __file__ 计算项目根目录
                        current_file = os.path.abspath(__file__)
                        # ui/tabs/office_tool_tab.py -> ui/tabs -> ui -> 项目根目录
                        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
                        if project_root not in sys.path:
                            sys.path.insert(0, project_root)
                    # 重试导入
                    from core.language_manager import LanguageManager
                    self.lang_manager = LanguageManager.get_instance()
            self.setup_ui()
        except Exception as e:
            logger.exception(self.lang_manager.tr("OfficeToolTab 初始化失败"))
            raise
        
    def setup_ui(self):
        """设置UI"""
        try:
            # 主布局
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(10, 10, 10, 10)
            main_layout.setSpacing(10)
            
            # 创建滚动区域
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            
            # 滚动内容
            scroll_content = QWidget()
            scroll_layout = QVBoxLayout(scroll_content)
            scroll_layout.setContentsMargins(0, 0, 0, 0)
            scroll_layout.setSpacing(1)
            
            # JIRA&Confluence 卡片组
            jira_confluence_group = self.create_jira_confluence_group()
            scroll_layout.addWidget(jira_confluence_group)
            
            # 添加弹性空间
            scroll_layout.addStretch()
            
            scroll.setWidget(scroll_content)
            main_layout.addWidget(scroll)
            
            logger.debug(self.lang_manager.tr("OfficeToolTab UI设置完成"))
            
        except Exception as e:
            logger.exception(self.lang_manager.tr("OfficeToolTab.setup_ui 失败"))
            raise
        
    def create_jira_confluence_group(self):
        """创建JIRA&Confluence操作组（现代结构：QLabel + QFrame）"""
        try:
            # 容器
            container = QWidget()
            v = QVBoxLayout(container)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(4)
            
            # 标题
            title = QLabel(self.lang_manager.tr("JIRA&Confluence"))
            title.setProperty("class", "section-title")
            v.addWidget(title)
            
            # 卡片
            card = QFrame()
            card.setObjectName("card")
            add_card_shadow(card)
            
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(10, 1, 10, 1)
            card_layout.setSpacing(8)
            
            self.show_jira_tool_btn = QPushButton(self.lang_manager.tr("JIRA工具"))
            self.show_jira_tool_btn.clicked.connect(lambda: self._on_button_clicked("show_jira_tool_btn", self.show_jira_tool.emit))
            card_layout.addWidget(self.show_jira_tool_btn)
            
            card_layout.addStretch()
            
            v.addWidget(card)
            
            return container
        except Exception as e:
            logger.exception(self.lang_manager.tr("create_jira_confluence_group 失败"))
            raise
    
    def _on_button_clicked(self, button_name, emit_func):
        """按钮点击统一处理函数，添加日志"""
        logger.debug("=" * 60)
        logger.debug(f"按钮点击事件触发")
        logger.debug(f"Tab: OfficeToolTab")
        logger.debug(f"按钮名称: {button_name}")
        logger.debug(f"按钮对象: {getattr(self, button_name, None)}")
        try:
            # 检查信号连接状态
            signal_name = None
            base_name = button_name.replace("_btn", "")
            if hasattr(self, base_name):
                signal_name = base_name
            elif hasattr(self, "show_" + base_name):
                signal_name = "show_" + base_name
            
            if signal_name:
                signal_obj = getattr(self, signal_name)
                try:
                    receivers = QObject.receivers(self, signal_obj)
                    logger.debug(f"信号对象: {signal_name}")
                    logger.debug(f"信号接收器数量: {receivers}")
                    if receivers == 0:
                        logger.error(f"⚠️ 警告：信号 {signal_name} 没有接收者！信号连接可能失败！")
                    else:
                        logger.debug(f"✓ 信号 {signal_name} 有 {receivers} 个接收者")
                except Exception as check_error:
                    logger.warning(f"无法检查信号 {signal_name} 的接收器数量: {check_error}")
            else:
                logger.warning(f"⚠️ 无法找到按钮 {button_name} 对应的信号对象")
            
            logger.debug(f"准备发送信号: {button_name}")
            emit_func()
            logger.debug(f"信号发送成功: {button_name}")
        except Exception as e:
            logger.error(f"按钮点击处理失败:\n  按钮名称: {button_name}\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
        finally:
            logger.debug("=" * 60)
    
    def refresh_texts(self, lang_manager=None):
        """刷新所有文本（用于语言切换）"""
        if lang_manager:
            self.lang_manager = lang_manager
        
        if not self.lang_manager:
            return
        
        # 刷新组标题标签
        self._refresh_section_titles()
        
        # 刷新JIRA&Confluence组按钮
        if hasattr(self, 'show_jira_tool_btn'):
            self.show_jira_tool_btn.setText(self.lang_manager.tr("JIRA工具"))
    
    def _refresh_section_titles(self):
        """刷新组标题标签"""
        # 查找所有QLabel并刷新标题
        for label in self.findChildren(QLabel):
            current_text = label.text()
            # 根据当前文本匹配对应的翻译
            if current_text in ["JIRA&Confluence", "JIRA&Confluence"]:
                label.setText(self.lang_manager.tr("JIRA&Confluence"))
