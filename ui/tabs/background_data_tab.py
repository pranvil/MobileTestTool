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
    export_background_logs = pyqtSignal()
    analyze_logs = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
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
        title = QLabel("24小时背景数据操作")
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        self.configure_phone_btn = QPushButton("配置手机")
        self.configure_phone_btn.clicked.connect(self.configure_phone.emit)
        card_layout.addWidget(self.configure_phone_btn)
        
        self.export_logs_btn = QPushButton("导出log")
        self.export_logs_btn.clicked.connect(self.export_background_logs.emit)
        card_layout.addWidget(self.export_logs_btn)
        
        self.analyze_logs_btn = QPushButton("分析log")
        self.analyze_logs_btn.clicked.connect(self.analyze_logs.emit)
        card_layout.addWidget(self.analyze_logs_btn)
        
        card_layout.addStretch()
        
        v.addWidget(card)
        
        return container

