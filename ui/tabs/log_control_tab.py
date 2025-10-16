#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Log控制 Tab
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                              QPushButton, QLabel, QScrollArea, QFrame)
from PyQt5.QtCore import pyqtSignal, Qt
from ui.widgets.shadow_utils import add_card_shadow


class LogControlTab(QWidget):
    """Log控制 Tab"""
    
    # 信号定义
    # MTKLOG 相关
    mtklog_start = pyqtSignal()
    mtklog_stop_export = pyqtSignal()
    mtklog_delete = pyqtSignal()
    mtklog_set_log_size = pyqtSignal()
    mtklog_sd_mode = pyqtSignal()
    mtklog_usb_mode = pyqtSignal()
    mtklog_install = pyqtSignal()
    
    # ADB Log 相关
    adblog_start = pyqtSignal()
    adblog_export = pyqtSignal()
    
    # Telephony 相关
    telephony_enable = pyqtSignal()
    
    # Google 日志相关
    google_log_toggle = pyqtSignal()
    
    # Bugreport 相关
    bugreport_generate = pyqtSignal()
    bugreport_pull = pyqtSignal()
    bugreport_delete = pyqtSignal()
    
    # AEE log 相关
    aee_log_start = pyqtSignal()
    
    # TCPDUMP 相关
    tcpdump_show_dialog = pyqtSignal()
    
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
        
        # 1. MTKLOG 控制组
        mtklog_group = self.create_mtklog_group()
        scroll_layout.addWidget(mtklog_group)
        
        # 2. ADB Log 控制组（包含 ADB Log 和 Google 日志相关功能）
        adblog_group = self.create_adblog_group()
        scroll_layout.addWidget(adblog_group)
        
        # 添加弹性空间
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
    def create_mtklog_group(self):
        """创建 MTKLOG 控制组（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)  # 紧凑的标题和卡片之间的间距
        
        # 标题
        title = QLabel("MTKLOG 控制")
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        # 第一行：主要操作
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("MTKLOG:"))
        
        self.mtklog_start_btn = QPushButton("开启")
        self.mtklog_start_btn.clicked.connect(self.mtklog_start.emit)
        row1.addWidget(self.mtklog_start_btn)
        
        self.mtklog_stop_export_btn = QPushButton("停止&导出")
        self.mtklog_stop_export_btn.clicked.connect(self.mtklog_stop_export.emit)
        row1.addWidget(self.mtklog_stop_export_btn)
        
        self.mtklog_delete_btn = QPushButton("删除")
        self.mtklog_delete_btn.clicked.connect(self.mtklog_delete.emit)
        row1.addWidget(self.mtklog_delete_btn)
        
        self.mtklog_set_log_size_btn = QPushButton("设置log size")
        self.mtklog_set_log_size_btn.clicked.connect(self.mtklog_set_log_size.emit)
        row1.addWidget(self.mtklog_set_log_size_btn)
        
        row1.addStretch()
        card_layout.addLayout(row1)
        
        # 第二行：模式切换
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("模式:"))
        
        self.mtklog_sd_mode_btn = QPushButton("SD模式")
        self.mtklog_sd_mode_btn.clicked.connect(self.mtklog_sd_mode.emit)
        row2.addWidget(self.mtklog_sd_mode_btn)
        
        self.mtklog_usb_mode_btn = QPushButton("USB模式")
        self.mtklog_usb_mode_btn.clicked.connect(self.mtklog_usb_mode.emit)
        row2.addWidget(self.mtklog_usb_mode_btn)
        
        self.mtklog_install_btn = QPushButton("安装MTKLOGGER")
        self.mtklog_install_btn.clicked.connect(self.mtklog_install.emit)
        row2.addWidget(self.mtklog_install_btn)
        
        self.telephony_btn = QPushButton("启用 Telephony 日志")
        self.telephony_btn.clicked.connect(self.telephony_enable.emit)
        row2.addWidget(self.telephony_btn)
        
        row2.addStretch()
        card_layout.addLayout(row2)
        
        v.addWidget(card)
        
        return container
        
    def create_adblog_group(self):
        """创建 ADB Log 控制组（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel("ADB Log 控制")
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        # 第一行：ADB Log
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("ADB Log:"))
        
        self.adblog_start_btn = QPushButton("开启")
        self.adblog_start_btn.clicked.connect(self.adblog_start.emit)
        row1.addWidget(self.adblog_start_btn)
        
        self.adblog_export_btn = QPushButton("导出")
        self.adblog_export_btn.clicked.connect(self.adblog_export.emit)
        row1.addWidget(self.adblog_export_btn)
        
        self.tcpdump_btn = QPushButton("TCPDUMP")
        self.tcpdump_btn.clicked.connect(self.tcpdump_show_dialog.emit)
        row1.addWidget(self.tcpdump_btn)
        
        row1.addStretch()
        card_layout.addLayout(row1)
        
        # 第二行：Google 日志
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Google日志:"))
        
        self.google_log_btn = QPushButton("Google 日志")
        self.google_log_btn.clicked.connect(self.google_log_toggle.emit)
        row2.addWidget(self.google_log_btn)
        
        self.aee_log_btn = QPushButton("AEE Log")
        self.aee_log_btn.clicked.connect(self.aee_log_start.emit)
        row2.addWidget(self.aee_log_btn)
        
        self.bugreport_generate_btn = QPushButton("生成 Bugreport")
        self.bugreport_generate_btn.clicked.connect(self.bugreport_generate.emit)
        row2.addWidget(self.bugreport_generate_btn)
        
        self.bugreport_pull_btn = QPushButton("Pull Bugreport")
        self.bugreport_pull_btn.clicked.connect(self.bugreport_pull.emit)
        row2.addWidget(self.bugreport_pull_btn)
        
        self.bugreport_delete_btn = QPushButton("删除 Bugreport")
        self.bugreport_delete_btn.clicked.connect(self.bugreport_delete.emit)
        row2.addWidget(self.bugreport_delete_btn)
        
        row2.addStretch()
        card_layout.addLayout(row2)
        
        v.addWidget(card)
        
        return container
    
    def set_online_mode_started(self):
        """连线模式已启动，改变按钮状态"""
        self.adblog_start_btn.setText("停止")
        self.adblog_start_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 5px 15px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
    
    def set_online_mode_stopped(self):
        """连线模式已停止，恢复按钮状态"""
        self.adblog_start_btn.setText("开启")
        self.adblog_start_btn.setStyleSheet("")

