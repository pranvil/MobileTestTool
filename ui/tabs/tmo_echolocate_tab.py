#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TMO Echolocate Tab
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QScrollArea, QLabel, QFrame)
from PySide6.QtCore import Signal, Qt
from ui.widgets.shadow_utils import add_card_shadow


class TMOEcholocateTab(QWidget):
    """TMO Echolocate Tab"""
    
    # 信号定义
    # Echolocate 操作
    install_echolocate = Signal()
    trigger_echolocate = Signal()
    pull_echolocate_file = Signal()
    delete_echolocate_file = Signal()
    get_echolocate_version = Signal()
    
    # 过滤操作
    filter_callid = Signal()
    filter_callstate = Signal()
    filter_uicallstate = Signal()
    filter_allcallstate = Signal()
    filter_ims_signalling = Signal()
    filter_allcallflow = Signal()
    filter_voice_intent = Signal()
    
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
                    # ui/tabs/tmo_echolocate_tab.py -> ui/tabs -> ui -> 项目根目录
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
        
        # 1. Echolocate 操作组
        echolocate_ops_group = self.create_echolocate_ops_group()
        scroll_layout.addWidget(echolocate_ops_group)
        
        # 2. 过滤操作组
        filter_ops_group = self.create_filter_ops_group()
        scroll_layout.addWidget(filter_ops_group)
        
        # 添加弹性空间
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
    def create_echolocate_ops_group(self):
        """创建Echolocate操作组（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel(self.lang_manager.tr("Echolocate 操作"))
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        self.install_btn = QPushButton(self.lang_manager.tr("安装"))
        self.install_btn.clicked.connect(self.install_echolocate.emit)
        card_layout.addWidget(self.install_btn)
        
        self.trigger_btn = QPushButton("Trigger")
        self.trigger_btn.clicked.connect(self.trigger_echolocate.emit)
        card_layout.addWidget(self.trigger_btn)
        
        self.pull_file_btn = QPushButton("Pull file")
        self.pull_file_btn.clicked.connect(self.pull_echolocate_file.emit)
        card_layout.addWidget(self.pull_file_btn)
        
        self.delete_file_btn = QPushButton(self.lang_manager.tr("删除手机文件"))
        self.delete_file_btn.clicked.connect(self.delete_echolocate_file.emit)
        card_layout.addWidget(self.delete_file_btn)
        
        self.version_btn = QPushButton("EchoVersion")
        self.version_btn.clicked.connect(self.get_echolocate_version.emit)
        card_layout.addWidget(self.version_btn)
        
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
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        # 第一行
        row1_layout = QHBoxLayout()
        row1_layout.addWidget(QLabel("filter:"))
        
        self.filter_callid_btn = QPushButton("CallID")
        self.filter_callid_btn.clicked.connect(self.filter_callid.emit)
        row1_layout.addWidget(self.filter_callid_btn)
        
        self.filter_callstate_btn = QPushButton("CallState")
        self.filter_callstate_btn.clicked.connect(self.filter_callstate.emit)
        row1_layout.addWidget(self.filter_callstate_btn)
        
        self.filter_uicallstate_btn = QPushButton("UICallState")
        self.filter_uicallstate_btn.clicked.connect(self.filter_uicallstate.emit)
        row1_layout.addWidget(self.filter_uicallstate_btn)
        
        self.filter_allcallstate_btn = QPushButton("AllCallState")
        self.filter_allcallstate_btn.clicked.connect(self.filter_allcallstate.emit)
        row1_layout.addWidget(self.filter_allcallstate_btn)      
        
        self.filter_ims_signalling_btn = QPushButton("IMSSignallingMessageLine1")
        self.filter_ims_signalling_btn.clicked.connect(self.filter_ims_signalling.emit)
        row1_layout.addWidget(self.filter_ims_signalling_btn)
        
        self.filter_allcallflow_btn = QPushButton("AllCallFlow")
        self.filter_allcallflow_btn.clicked.connect(self.filter_allcallflow.emit)
        row1_layout.addWidget(self.filter_allcallflow_btn)
        
        self.filter_voice_intent_btn = QPushButton(self.lang_manager.tr("voice_intent测试"))
        self.filter_voice_intent_btn.clicked.connect(self.filter_voice_intent.emit)
        row1_layout.addWidget(self.filter_voice_intent_btn)
        
        row1_layout.addStretch()
        
        card_layout.addLayout(row1_layout)
        
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
        
        # 刷新Echolocate操作组按钮
        if hasattr(self, 'install_btn'):
            self.install_btn.setText(self.lang_manager.tr("安装"))
        if hasattr(self, 'delete_file_btn'):
            self.delete_file_btn.setText(self.lang_manager.tr("删除手机文件"))
        if hasattr(self, 'filter_voice_intent_btn'):
            self.filter_voice_intent_btn.setText(self.lang_manager.tr("voice_intent测试"))
    
    def _refresh_section_titles(self):
        """刷新组标题标签"""
        # 查找所有QLabel并刷新标题
        for label in self.findChildren(QLabel):
            current_text = label.text()
            # 根据当前文本匹配对应的翻译
            if current_text in ["Echolocate 操作", "Echolocate Operations"]:
                label.setText(self.lang_manager.tr("Echolocate 操作"))
            elif current_text in ["过滤操作", "Filter Operations"]:
                label.setText(self.lang_manager.tr("过滤操作"))
