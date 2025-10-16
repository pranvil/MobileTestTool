#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APP操作 Tab
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QGroupBox, QScrollArea, QLabel, QFrame)
from PyQt5.QtCore import pyqtSignal, Qt


class AppOperationsTab(QWidget):
    """APP操作 Tab"""
    
    # 信号定义
    # 查询操作
    query_package = pyqtSignal()
    query_package_name = pyqtSignal()
    query_install_path = pyqtSignal()
    
    # APK操作
    pull_apk = pyqtSignal()
    push_apk = pyqtSignal()
    install_apk = pyqtSignal()
    
    # 进程操作
    view_processes = pyqtSignal()
    dump_app = pyqtSignal()
    
    # APP状态操作
    enable_app = pyqtSignal()
    disable_app = pyqtSignal()
    
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
        
        # 1. 查询操作和APK操作组（同一行）
        query_apk_container = QWidget()
        query_apk_layout = QHBoxLayout(query_apk_container)
        query_apk_layout.setContentsMargins(0, 0, 0, 0)
        query_apk_layout.setSpacing(10)
        
        query_ops_group = self.create_query_ops_group()
        query_apk_layout.addWidget(query_ops_group)
        
        apk_ops_group = self.create_apk_ops_group()
        query_apk_layout.addWidget(apk_ops_group)
        
        scroll_layout.addWidget(query_apk_container)
        
        # 2. 进程操作和APP状态操作组（同一行）
        process_status_container = QWidget()
        process_status_layout = QHBoxLayout(process_status_container)
        process_status_layout.setContentsMargins(0, 0, 0, 0)
        process_status_layout.setSpacing(10)
        
        process_ops_group = self.create_process_ops_group()
        process_status_layout.addWidget(process_ops_group)
        
        app_status_ops_group = self.create_app_status_ops_group()
        process_status_layout.addWidget(app_status_ops_group)
        
        scroll_layout.addWidget(process_status_container)
        
        # 添加弹性空间
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
    def create_query_ops_group(self):
        """创建查询操作组（现代结构：QLabel + QFrame）"""
        from ui.widgets.shadow_utils import add_card_shadow
        
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel("查询操作")
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        self.query_package_btn = QPushButton("查询package")
        self.query_package_btn.clicked.connect(self.query_package.emit)
        card_layout.addWidget(self.query_package_btn)
        
        self.query_package_name_btn = QPushButton("查询包名")
        self.query_package_name_btn.clicked.connect(self.query_package_name.emit)
        card_layout.addWidget(self.query_package_name_btn)
        
        self.query_install_path_btn = QPushButton("查询安装路径")
        self.query_install_path_btn.clicked.connect(self.query_install_path.emit)
        card_layout.addWidget(self.query_install_path_btn)
        
        card_layout.addStretch()
        
        v.addWidget(card)
        
        return container
        
    def create_apk_ops_group(self):
        """创建APK操作组（现代结构：QLabel + QFrame）"""
        from ui.widgets.shadow_utils import add_card_shadow
        
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel("APK操作")
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        self.pull_apk_btn = QPushButton("pull apk")
        self.pull_apk_btn.clicked.connect(self.pull_apk.emit)
        card_layout.addWidget(self.pull_apk_btn)
        
        self.push_apk_btn = QPushButton("push apk")
        self.push_apk_btn.clicked.connect(self.push_apk.emit)
        card_layout.addWidget(self.push_apk_btn)
        
        self.install_apk_btn = QPushButton("安装APK")
        self.install_apk_btn.clicked.connect(self.install_apk.emit)
        card_layout.addWidget(self.install_apk_btn)
        
        card_layout.addStretch()
        
        v.addWidget(card)
        
        return container
        
    def create_process_ops_group(self):
        """创建进程操作组（现代结构：QLabel + QFrame）"""
        from ui.widgets.shadow_utils import add_card_shadow
        
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel("进程操作")
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        self.view_processes_btn = QPushButton("查看进程")
        self.view_processes_btn.clicked.connect(self.view_processes.emit)
        card_layout.addWidget(self.view_processes_btn)
        
        self.dump_app_btn = QPushButton("dump app")
        self.dump_app_btn.clicked.connect(self.dump_app.emit)
        card_layout.addWidget(self.dump_app_btn)
        
        card_layout.addStretch()
        
        v.addWidget(card)
        
        return container
        
    def create_app_status_ops_group(self):
        """创建APP状态操作组（现代结构：QLabel + QFrame）"""
        from ui.widgets.shadow_utils import add_card_shadow
        
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel("APP状态操作")
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 1, 10)
        card_layout.setSpacing(8)
        
        self.enable_app_btn = QPushButton("启用app")
        self.enable_app_btn.clicked.connect(self.enable_app.emit)
        card_layout.addWidget(self.enable_app_btn)
        
        self.disable_app_btn = QPushButton("禁用app")
        self.disable_app_btn.clicked.connect(self.disable_app.emit)
        card_layout.addWidget(self.disable_app_btn)
        
        card_layout.addStretch()
        
        v.addWidget(card)
        
        return container

