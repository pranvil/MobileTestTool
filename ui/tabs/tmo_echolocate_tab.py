#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TMO Echolocate Tab
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QGroupBox, QScrollArea, QLabel, QFrame)
from PyQt5.QtCore import pyqtSignal, Qt
from ui.widgets.shadow_utils import add_card_shadow


class TMOEcholocateTab(QWidget):
    """TMO Echolocate Tab"""
    
    # 信号定义
    # Echolocate 操作
    install_echolocate = pyqtSignal()
    trigger_echolocate = pyqtSignal()
    pull_echolocate_file = pyqtSignal()
    delete_echolocate_file = pyqtSignal()
    get_echolocate_version = pyqtSignal()
    install_gslice1 = pyqtSignal()
    install_gslice2 = pyqtSignal()
    
    # 过滤操作
    filter_callid = pyqtSignal()
    filter_callstate = pyqtSignal()
    filter_uicallstate = pyqtSignal()
    filter_allcallstate = pyqtSignal()
    filter_ims_signalling = pyqtSignal()
    filter_allcallflow = pyqtSignal()
    filter_voice_intent = pyqtSignal()
    
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
        title = QLabel("Echolocate 操作")
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        self.install_btn = QPushButton("安装DiagTrace")
        self.install_btn.clicked.connect(self.install_echolocate.emit)
        card_layout.addWidget(self.install_btn)
        
        self.trigger_btn = QPushButton("Trigger")
        self.trigger_btn.clicked.connect(self.trigger_echolocate.emit)
        card_layout.addWidget(self.trigger_btn)
        
        self.pull_file_btn = QPushButton("Pull file")
        self.pull_file_btn.clicked.connect(self.pull_echolocate_file.emit)
        card_layout.addWidget(self.pull_file_btn)
        
        self.delete_file_btn = QPushButton("删除手机文件")
        self.delete_file_btn.clicked.connect(self.delete_echolocate_file.emit)
        card_layout.addWidget(self.delete_file_btn)
        
        self.version_btn = QPushButton("EchoVersion")
        self.version_btn.clicked.connect(self.get_echolocate_version.emit)
        card_layout.addWidget(self.version_btn)
        
        self.gslice1_btn = QPushButton("安装Gslice1")
        self.gslice1_btn.clicked.connect(self.install_gslice1.emit)
        card_layout.addWidget(self.gslice1_btn)
        
        self.gslice2_btn = QPushButton("安装Gslice2")
        self.gslice2_btn.clicked.connect(self.install_gslice2.emit)
        card_layout.addWidget(self.gslice2_btn)
        
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
        
        self.filter_voice_intent_btn = QPushButton("voice_intent测试")
        self.filter_voice_intent_btn.clicked.connect(self.filter_voice_intent.emit)
        row1_layout.addWidget(self.filter_voice_intent_btn)
        
        row1_layout.addStretch()
        
        card_layout.addLayout(row1_layout)
        
        v.addWidget(card)
        
        return container

