#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APP操作 Tab
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QGroupBox, QScrollArea, QLabel, QFrame)
from PyQt5.QtCore import pyqtSignal, Qt
from ui.widgets.shadow_utils import add_card_shadow


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
        # 从父窗口获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            # 如果没有父窗口或语言管理器，使用单例
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager.get_instance()
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
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel(self.lang_manager.tr("查询操作"))
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        self.query_package_btn = QPushButton(self.lang_manager.tr("查询package"))
        self.query_package_btn.clicked.connect(self.query_package.emit)
        card_layout.addWidget(self.query_package_btn)
        
        self.query_package_name_btn = QPushButton(self.lang_manager.tr("查询包名"))
        self.query_package_name_btn.clicked.connect(self.query_package_name.emit)
        card_layout.addWidget(self.query_package_name_btn)
        
        self.query_install_path_btn = QPushButton(self.lang_manager.tr("查询安装路径"))
        self.query_install_path_btn.clicked.connect(self.query_install_path.emit)
        card_layout.addWidget(self.query_install_path_btn)
        
        card_layout.addStretch()
        
        v.addWidget(card)
        
        return container
        
    def create_apk_ops_group(self):
        """创建APK操作组（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel(self.lang_manager.tr("APK操作"))
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
        
        self.push_apk_btn = QPushButton(self.lang_manager.tr("push 文件"))
        self.push_apk_btn.clicked.connect(self.push_apk.emit)
        card_layout.addWidget(self.push_apk_btn)
        
        self.install_apk_btn = QPushButton(self.lang_manager.tr("安装APK"))
        self.install_apk_btn.clicked.connect(self.install_apk.emit)
        card_layout.addWidget(self.install_apk_btn)
        
        card_layout.addStretch()
        
        v.addWidget(card)
        
        return container
        
    def create_process_ops_group(self):
        """创建进程操作组（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel(self.lang_manager.tr("进程操作"))
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        self.view_processes_btn = QPushButton(self.lang_manager.tr("查看进程"))
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
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel(self.lang_manager.tr("APP状态操作"))
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 1, 10)
        card_layout.setSpacing(8)
        
        self.enable_app_btn = QPushButton(self.lang_manager.tr("启用app"))
        self.enable_app_btn.clicked.connect(self.enable_app.emit)
        card_layout.addWidget(self.enable_app_btn)
        
        self.disable_app_btn = QPushButton(self.lang_manager.tr("禁用app"))
        self.disable_app_btn.clicked.connect(self.disable_app.emit)
        card_layout.addWidget(self.disable_app_btn)
        
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
        
        # 刷新查询操作组按钮
        if hasattr(self, 'query_package_btn'):
            self.query_package_btn.setText(self.lang_manager.tr("查询package"))
        if hasattr(self, 'query_package_name_btn'):
            self.query_package_name_btn.setText(self.lang_manager.tr("查询包名"))
        if hasattr(self, 'query_install_path_btn'):
            self.query_install_path_btn.setText(self.lang_manager.tr("查询安装路径"))
        
        # 刷新APK操作组按钮
        if hasattr(self, 'push_apk_btn'):
            self.push_apk_btn.setText(self.lang_manager.tr("push 文件"))
        if hasattr(self, 'install_apk_btn'):
            self.install_apk_btn.setText(self.lang_manager.tr("安装APK"))
        
        # 刷新进程管理组按钮
        if hasattr(self, 'view_processes_btn'):
            self.view_processes_btn.setText(self.lang_manager.tr("查看进程"))
        
        # 刷新应用控制组按钮
        if hasattr(self, 'enable_app_btn'):
            self.enable_app_btn.setText(self.lang_manager.tr("启用app"))
        if hasattr(self, 'disable_app_btn'):
            self.disable_app_btn.setText(self.lang_manager.tr("禁用app"))
    
    def _refresh_section_titles(self):
        """刷新组标题标签"""
        # 查找所有QLabel并刷新标题
        for label in self.findChildren(QLabel):
            current_text = label.text()
            # 根据当前文本匹配对应的翻译
            if current_text in ["查询操作", "Query Operations"]:
                label.setText(self.lang_manager.tr("查询操作"))
            elif current_text in ["APK操作", "APK Operations"]:
                label.setText(self.lang_manager.tr("APK操作"))
            elif current_text in ["进程操作", "Process Operations"]:
                label.setText(self.lang_manager.tr("进程操作"))
            elif current_text in ["APP状态操作", "APP Status Operations"]:
                label.setText(self.lang_manager.tr("APP状态操作"))
