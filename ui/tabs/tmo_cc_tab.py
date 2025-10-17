#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TMO CC Tab
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QGroupBox, QScrollArea, QLabel, QFrame)
from PyQt5.QtCore import pyqtSignal, Qt
from ui.widgets.shadow_utils import add_card_shadow


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
    clear_device_logs = pyqtSignal()
    delete_cc_file = pyqtSignal()
    clear_entitlement = pyqtSignal()
    
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
        scroll_layout.setSpacing(1)
        
        # 1. CC 文件操作组
        cc_ops_group = self.create_cc_ops_group()
        scroll_layout.addWidget(cc_ops_group)
        
        # 2. 过滤操作组
        filter_ops_group = self.create_filter_ops_group()
        scroll_layout.addWidget(filter_ops_group)
        
        # 添加弹性空间
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
    def create_cc_ops_group(self):
        """创建CC文件操作组（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel("CC配置")
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        self.push_cc_btn = QPushButton("推CC文件")
        self.push_cc_btn.clicked.connect(self.push_cc_file.emit)
        card_layout.addWidget(self.push_cc_btn)
        
        self.pull_cc_btn = QPushButton("拉CC文件")
        self.pull_cc_btn.clicked.connect(self.pull_cc_file.emit)
        card_layout.addWidget(self.pull_cc_btn)
        
        self.prod_server_btn = QPushButton("PROD服务器")
        self.prod_server_btn.clicked.connect(self.prod_server.emit)
        card_layout.addWidget(self.prod_server_btn)
        
        self.stg_server_btn = QPushButton("STG服务器")
        self.stg_server_btn.clicked.connect(self.stg_server.emit)
        card_layout.addWidget(self.stg_server_btn)
        
        self.delete_cc_file_btn = QPushButton("删除 CC 文件")
        self.delete_cc_file_btn.clicked.connect(self.delete_cc_file.emit)
        card_layout.addWidget(self.delete_cc_file_btn)
        
        self.clear_entitlement_btn = QPushButton("清除 Entitlement")
        self.clear_entitlement_btn.clicked.connect(self.clear_entitlement.emit)
        card_layout.addWidget(self.clear_entitlement_btn)
        
        card_layout.addStretch()
        
        v.addWidget(card)
        
        return container
        
    def create_filter_ops_group(self):
        """创建过滤操作组（现代结构：QLabel + QFrame）"""
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
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        self.simple_filter_btn = QPushButton("简单过滤")
        self.simple_filter_btn.clicked.connect(self.simple_filter.emit)
        card_layout.addWidget(self.simple_filter_btn)
        
        self.complete_filter_btn = QPushButton("完全过滤")
        self.complete_filter_btn.clicked.connect(self.complete_filter.emit)
        card_layout.addWidget(self.complete_filter_btn)
        
        self.clear_device_logs_btn = QPushButton("清除手机缓存日志")
        self.clear_device_logs_btn.clicked.connect(self.clear_device_logs.emit)
        card_layout.addWidget(self.clear_device_logs_btn)
        
        card_layout.addStretch()
        
        v.addWidget(card)
        
        return container
        
    def update_filter_buttons(self, is_running, current_keyword=""):
        """更新过滤按钮状态
        
        Args:
            is_running: 是否正在过滤
            current_keyword: 当前使用的过滤关键字
        """
        # 定义关键字
        simple_keywords = "new cc version|old cc version|doDeviceActivation:Successful|mDeviceGroup|getUserAgent"
        complete_keywords = "EntitlementServerApi|new cc version|old cc version|doDeviceActivation:Successful|mDeviceGroup|Entitlement-EapAka|EntitlementHandling|UpdateProvider|EntitlementService"
        
        if is_running:
            # 正在过滤中，根据当前过滤类型显示停止按钮
            if current_keyword == simple_keywords:
                # 当前是简单过滤
                self.simple_filter_btn.setText("停止log过滤")
                self.complete_filter_btn.setText("完全过滤")
            elif current_keyword == complete_keywords:
                # 当前是完全过滤
                self.simple_filter_btn.setText("简单过滤")
                self.complete_filter_btn.setText("停止log过滤")
            else:
                # 其他过滤类型，默认简单过滤按钮显示停止
                self.simple_filter_btn.setText("停止log过滤")
                self.complete_filter_btn.setText("完全过滤")
        else:
            # 没有过滤，恢复原始状态
            self.simple_filter_btn.setText("简单过滤")
            self.complete_filter_btn.setText("完全过滤")

