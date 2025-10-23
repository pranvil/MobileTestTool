#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
24小时背景数据 Tab
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QGroupBox, QScrollArea, QLabel, QFrame)
from PyQt5.QtCore import pyqtSignal, Qt
from ui.widgets.shadow_utils import add_card_shadow


class BackgroundDataTab(QWidget):
    """24小时背景数据 Tab"""
    
    # 信号定义
    # 背景数据操作
    configure_phone = pyqtSignal()
    analyze_logs = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 从父窗口获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            # 如果没有父窗口或语言管理器，创建一个默认的
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager()
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
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
        scroll_layout.setSpacing(10)
        
        # 背景数据操作组
        bg_ops_group = self.create_bg_ops_group()
        scroll_layout.addWidget(bg_ops_group)
        
        # 添加弹性空间
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
    def create_bg_ops_group(self):
        """创建背景数据操作组（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel(self.lang_manager.tr("24小时背景数据操作"))
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        self.configure_phone_btn = QPushButton(self.lang_manager.tr("配置手机"))
        self.configure_phone_btn.clicked.connect(self.configure_phone.emit)
        card_layout.addWidget(self.configure_phone_btn)
        
        self.analyze_logs_btn = QPushButton(self.lang_manager.tr("分析log"))
        self.analyze_logs_btn.clicked.connect(self.analyze_logs.emit)
        card_layout.addWidget(self.analyze_logs_btn)
        
        card_layout.addStretch()
        
        v.addWidget(card)
        
        return container

    def refresh_texts(self, lang_manager=None):
        """刷新所有文本（用于语言切换）"""
        if lang_manager:
            self.lang_manager = lang_manager
        
        if not self.lang_manager:
            return
        
        # 刷新组标题标签
        self._refresh_section_titles()
        
        # 刷新24小时背景数据操作按钮
        if hasattr(self, 'configure_phone_btn'):
            self.configure_phone_btn.setText(self.lang_manager.tr("配置手机"))
        if hasattr(self, 'analyze_logs_btn'):
            self.analyze_logs_btn.setText(self.lang_manager.tr("分析log"))
    
    def _refresh_section_titles(self):
        """刷新组标题标签"""
        # 查找所有QLabel并刷新标题
        for label in self.findChildren(QLabel):
            current_text = label.text()
            # 根据当前文本匹配对应的翻译
            if current_text in ["24小时背景数据操作", "24h Background Data Operations"]:
                label.setText(self.lang_manager.tr("24小时背景数据操作"))
