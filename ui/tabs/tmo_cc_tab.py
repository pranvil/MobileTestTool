#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TMO CC Tab
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QScrollArea, QLabel, QFrame)
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
    clear_logs = pyqtSignal()
    clear_device_logs = pyqtSignal()
    
    def __init__(self, parent=None):
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
                    # ui/tabs/tmo_cc_tab.py -> ui/tabs -> ui -> 项目根目录
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
                    if project_root not in sys.path:
                        sys.path.insert(0, project_root)
                # 重试导入
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
        title = QLabel(self.lang_manager.tr("CC配置"))
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        self.push_cc_btn = QPushButton(self.lang_manager.tr("推CC文件"))
        self.push_cc_btn.clicked.connect(self.push_cc_file.emit)
        card_layout.addWidget(self.push_cc_btn)
        
        self.pull_cc_btn = QPushButton(self.lang_manager.tr("拉CC文件"))
        self.pull_cc_btn.clicked.connect(self.pull_cc_file.emit)
        card_layout.addWidget(self.pull_cc_btn)
        
        self.prod_server_btn = QPushButton(self.lang_manager.tr("PROD服务器"))
        self.prod_server_btn.clicked.connect(self.prod_server.emit)
        card_layout.addWidget(self.prod_server_btn)
        
        self.stg_server_btn = QPushButton(self.lang_manager.tr("STG服务器"))
        self.stg_server_btn.clicked.connect(self.stg_server.emit)
        card_layout.addWidget(self.stg_server_btn)
        
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
        title = QLabel(self.lang_manager.tr("过滤操作"))
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        self.simple_filter_btn = QPushButton(self.lang_manager.tr("简单过滤"))
        self.simple_filter_btn.clicked.connect(self.simple_filter.emit)
        card_layout.addWidget(self.simple_filter_btn)
        
        self.complete_filter_btn = QPushButton(self.lang_manager.tr("完全过滤"))
        self.complete_filter_btn.clicked.connect(self.complete_filter.emit)
        card_layout.addWidget(self.complete_filter_btn)
        
        self.clear_logs_btn = QPushButton(self.lang_manager.tr("清空日志"))
        self.clear_logs_btn.clicked.connect(self.clear_logs.emit)
        card_layout.addWidget(self.clear_logs_btn)
        
        self.clear_device_logs_btn = QPushButton(self.lang_manager.tr("清除手机缓存日志"))
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
                self.simple_filter_btn.setText(self.lang_manager.tr("停止log过滤"))
                self.complete_filter_btn.setText(self.lang_manager.tr("完全过滤"))
            elif current_keyword == complete_keywords:
                # 当前是完全过滤
                self.simple_filter_btn.setText(self.lang_manager.tr("简单过滤"))
                self.complete_filter_btn.setText(self.lang_manager.tr("停止log过滤"))
            else:
                # 其他过滤类型，默认简单过滤按钮显示停止
                self.simple_filter_btn.setText(self.lang_manager.tr("停止log过滤"))
                self.complete_filter_btn.setText(self.lang_manager.tr("完全过滤"))
        else:
            # 没有过滤，恢复原始状态
            self.simple_filter_btn.setText(self.lang_manager.tr("简单过滤"))
            self.complete_filter_btn.setText(self.lang_manager.tr("完全过滤"))

    def refresh_texts(self, lang_manager=None):
        """刷新所有文本（用于语言切换）"""
        if lang_manager:
            self.lang_manager = lang_manager
        
        if not self.lang_manager:
            return
        
        # 刷新组标题标签
        self._refresh_section_titles()
        
        # 刷新CC文件操作组按钮
        if hasattr(self, 'push_cc_btn'):
            self.push_cc_btn.setText(self.lang_manager.tr("推CC文件"))
        if hasattr(self, 'pull_cc_btn'):
            self.pull_cc_btn.setText(self.lang_manager.tr("拉CC文件"))
        if hasattr(self, 'prod_server_btn'):
            self.prod_server_btn.setText(self.lang_manager.tr("PROD服务器"))
        if hasattr(self, 'stg_server_btn'):
            self.stg_server_btn.setText(self.lang_manager.tr("STG服务器"))
        
        # 刷新日志过滤组按钮
        if hasattr(self, 'simple_filter_btn'):
            self.simple_filter_btn.setText(self.lang_manager.tr("简单过滤"))
        if hasattr(self, 'complete_filter_btn'):
            self.complete_filter_btn.setText(self.lang_manager.tr("完全过滤"))
        if hasattr(self, 'clear_logs_btn'):
            self.clear_logs_btn.setText(self.lang_manager.tr("清空日志"))
        if hasattr(self, 'clear_device_logs_btn'):
            self.clear_device_logs_btn.setText(self.lang_manager.tr("清除手机缓存日志"))
    
    def _refresh_section_titles(self):
        """刷新组标题标签"""
        # 查找所有QLabel并刷新标题
        for label in self.findChildren(QLabel):
            current_text = label.text()
            # 根据当前文本匹配对应的翻译
            if current_text in ["CC配置", "CC Configuration"]:
                label.setText(self.lang_manager.tr("CC配置"))
            elif current_text in ["过滤操作", "Filter Operations"]:
                label.setText(self.lang_manager.tr("过滤操作"))
