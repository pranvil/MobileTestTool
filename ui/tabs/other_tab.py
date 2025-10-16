#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
其他 Tab
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QGroupBox, QScrollArea, QLabel, QFrame)
from PyQt5.QtCore import pyqtSignal, Qt
from ui.widgets.shadow_utils import add_card_shadow
from core.debug_logger import logger


class OtherTab(QWidget):
    """其他 Tab"""
    
    # 信号定义
    # 设备信息
    show_device_info_dialog = pyqtSignal()
    set_screen_timeout = pyqtSignal()
    
    # MTKlog操作
    merge_mtklog = pyqtSignal()
    extract_pcap_from_mtklog = pyqtSignal()
    
    # PCAP操作
    merge_pcap = pyqtSignal()
    extract_pcap_from_qualcomm_log = pyqtSignal()
    
    # 赫拉配置
    configure_hera = pyqtSignal()
    configure_collect_data = pyqtSignal()
    
    # 其他操作
    show_input_text_dialog = pyqtSignal()
    
    # 工具配置
    show_tools_config_dialog = pyqtSignal()
    
    # 设置显示行数
    show_display_lines_dialog = pyqtSignal()
    
    def __init__(self, parent=None):
        try:
            logger.debug("OtherTab.__init__ 开始")
            super().__init__(parent)
            logger.debug("OtherTab super().__init__ 完成")
            self.setup_ui()
            logger.debug("OtherTab.setup_ui() 完成")
        except Exception as e:
            logger.exception("OtherTab 初始化失败")
            raise
        
    def setup_ui(self):
        """设置UI"""
        try:
            logger.debug("OtherTab.setup_ui 开始...")
            # 主布局
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(10, 10, 10, 10)
            main_layout.setSpacing(10)
            logger.debug("主布局创建完成")
            
            # 创建滚动区域
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            
            # 滚动内容
            scroll_content = QWidget()
            scroll_layout = QVBoxLayout(scroll_content)
            scroll_layout.setContentsMargins(0, 0, 0, 0)
            scroll_layout.setSpacing(1)
            
            # 1. 设备信息、赫拉配置、其他操作组（同一行）
            first_row_container = QWidget()
            first_row_layout = QHBoxLayout(first_row_container)
            first_row_layout.setContentsMargins(0, 0, 0, 0)
            first_row_layout.setSpacing(10)
            
            device_info_group = self.create_device_info_group()
            first_row_layout.addWidget(device_info_group)
            
            hera_config_group = self.create_hera_config_group()
            first_row_layout.addWidget(hera_config_group)
            
            other_ops_group = self.create_other_ops_group()
            first_row_layout.addWidget(other_ops_group)
            
            scroll_layout.addWidget(first_row_container)
            
            # 2. log操作组（合并PCAP和MTKlog操作）
            log_ops_group = self.create_log_ops_group()
            scroll_layout.addWidget(log_ops_group)
            
            # 添加弹性空间
            scroll_layout.addStretch()
            
            scroll.setWidget(scroll_content)
            main_layout.addWidget(scroll)
            
            logger.debug("OtherTab UI设置完成")
            
        except Exception as e:
            logger.exception("OtherTab.setup_ui 失败")
            raise
        
    def create_device_info_group(self):
        """创建设备信息操作组（现代结构：QLabel + QFrame）"""
        try:
            logger.debug("创建设备信息操作组...")
            # 容器
            container = QWidget()
            v = QVBoxLayout(container)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(4)
            
            # 标题
            title = QLabel("设备信息")
            title.setProperty("class", "section-title")
            v.addWidget(title)
            
            # 卡片
            card = QFrame()
            card.setObjectName("card")
            add_card_shadow(card)
            
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(10, 1, 10, 1)
            card_layout.setSpacing(8)
            
            self.show_device_info_btn = QPushButton("手机信息")
            self.show_device_info_btn.clicked.connect(self.show_device_info_dialog.emit)
            card_layout.addWidget(self.show_device_info_btn)
            
            self.set_screen_timeout_btn = QPushButton("设置灭屏时间")
            self.set_screen_timeout_btn.clicked.connect(self.set_screen_timeout.emit)
            card_layout.addWidget(self.set_screen_timeout_btn)
            
            card_layout.addStretch()
            
            v.addWidget(card)
            
            logger.debug("设备信息操作组创建完成")
            return container
        except Exception as e:
            logger.exception("create_device_info_group 失败")
            raise
        
        
    def create_hera_config_group(self):
        """创建赫拉配置组（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel("赫拉配置")
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        self.configure_hera_btn = QPushButton("赫拉配置")
        self.configure_hera_btn.clicked.connect(self.configure_hera.emit)
        card_layout.addWidget(self.configure_hera_btn)
        
        self.configure_collect_data_btn = QPushButton("赫拉测试数据收集")
        self.configure_collect_data_btn.clicked.connect(self.configure_collect_data.emit)
        card_layout.addWidget(self.configure_collect_data_btn)
        
        card_layout.addStretch()
        
        v.addWidget(card)
        
        return container
        
    def create_other_ops_group(self):
        """创建其他操作组（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel("其他操作")
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        self.show_input_text_btn = QPushButton("输入文本")
        self.show_input_text_btn.clicked.connect(self.show_input_text_dialog.emit)
        card_layout.addWidget(self.show_input_text_btn)
        
        self.show_tools_config_btn = QPushButton("工具配置")
        self.show_tools_config_btn.clicked.connect(self.show_tools_config_dialog.emit)
        card_layout.addWidget(self.show_tools_config_btn)
        
        self.show_display_lines_btn = QPushButton("设置显示行数")
        self.show_display_lines_btn.clicked.connect(self.show_display_lines_dialog.emit)
        card_layout.addWidget(self.show_display_lines_btn)
        
        card_layout.addStretch()
        
        v.addWidget(card)
        
        return container
        
    def create_log_ops_group(self):
        """创建log操作组（合并PCAP和MTKlog操作）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel("log操作")
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        # 第一行：MTKlog操作
        row1_layout = QHBoxLayout()
        
        self.merge_mtklog_btn = QPushButton("合并MTKlog")
        self.merge_mtklog_btn.clicked.connect(self.merge_mtklog.emit)
        row1_layout.addWidget(self.merge_mtklog_btn)
        
        self.extract_pcap_from_mtklog_btn = QPushButton("MTKlog提取pcap")
        self.extract_pcap_from_mtklog_btn.clicked.connect(self.extract_pcap_from_mtklog.emit)
        row1_layout.addWidget(self.extract_pcap_from_mtklog_btn)
              
        self.merge_pcap_btn = QPushButton("合并PCAP")
        self.merge_pcap_btn.clicked.connect(self.merge_pcap.emit)
        row1_layout.addWidget(self.merge_pcap_btn)
        
        self.extract_pcap_from_qualcomm_log_btn = QPushButton("高通log提取pcap")
        self.extract_pcap_from_qualcomm_log_btn.clicked.connect(self.extract_pcap_from_qualcomm_log.emit)
        row1_layout.addWidget(self.extract_pcap_from_qualcomm_log_btn)
        
        row1_layout.addStretch()
        card_layout.addLayout(row1_layout)
        
        v.addWidget(card)
        
        return container

