#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TMO CC Tab
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QGroupBox, QScrollArea, QLabel, QFrame)
from PyQt5.QtCore import pyqtSignal, Qt


class TMOCCTab(QWidget):
    """TMO CC Tab"""
    
    # 信号定义
    # CC 文件操作
    push_cc_file = pyqtSignal()
    pull_cc_file = pyqtSignal()
    
    # 过滤操作
    simple_filter = pyqtSignal()
    complete_filter = pyqtSignal()
    
    # 服务器选择
    prod_server = pyqtSignal()
    stg_server = pyqtSignal()
    
    # 其他操作
    clear_logs = pyqtSignal()
    
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
        
        # 1. CC 文件操作组
        cc_ops_group = self.create_cc_ops_group()
        scroll_layout.addWidget(cc_ops_group)
        
        # 2. 过滤操作组
        filter_ops_group = self.create_filter_ops_group()
        scroll_layout.addWidget(filter_ops_group)
        
        # 3. 服务器选择组
        server_group = self.create_server_group()
        scroll_layout.addWidget(server_group)
        
        # 添加弹性空间
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
    def create_cc_ops_group(self):
        """创建CC文件操作组（现代结构：QLabel + QFrame）"""
        from ui.widgets.shadow_utils import add_card_shadow
        
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel("CC 文件操作")
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(8)
        
        self.push_cc_btn = QPushButton("推CC文件")
        self.push_cc_btn.clicked.connect(self.push_cc_file.emit)
        card_layout.addWidget(self.push_cc_btn)
        
        self.pull_cc_btn = QPushButton("拉CC文件")
        self.pull_cc_btn.clicked.connect(self.pull_cc_file.emit)
        card_layout.addWidget(self.pull_cc_btn)
        
        card_layout.addStretch()
        
        v.addWidget(card)
        
        return container
        
    def create_filter_ops_group(self):
        """创建过滤操作组（现代结构：QLabel + QFrame）"""
        from ui.widgets.shadow_utils import add_card_shadow
        
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel("过滤操作")
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(8)
        
        self.simple_filter_btn = QPushButton("简单过滤")
        self.simple_filter_btn.clicked.connect(self.simple_filter.emit)
        card_layout.addWidget(self.simple_filter_btn)
        
        self.complete_filter_btn = QPushButton("完全过滤")
        self.complete_filter_btn.clicked.connect(self.complete_filter.emit)
        card_layout.addWidget(self.complete_filter_btn)
        
        self.clear_logs_btn = QPushButton("清空日志")
        self.clear_logs_btn.clicked.connect(self.clear_logs.emit)
        card_layout.addWidget(self.clear_logs_btn)
        
        card_layout.addStretch()
        
        v.addWidget(card)
        
        return container
        
    def create_server_group(self):
        """创建服务器选择组（现代结构：QLabel + QFrame）"""
        from ui.widgets.shadow_utils import add_card_shadow
        
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel("服务器选择")
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(8)
        
        self.prod_server_btn = QPushButton("PROD服务器")
        self.prod_server_btn.clicked.connect(self.prod_server.emit)
        card_layout.addWidget(self.prod_server_btn)
        
        self.stg_server_btn = QPushButton("STG服务器")
        self.stg_server_btn.clicked.connect(self.stg_server.emit)
        card_layout.addWidget(self.stg_server_btn)
        
        card_layout.addStretch()
        
        v.addWidget(card)
        
        return container

