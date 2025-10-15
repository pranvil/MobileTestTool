#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
其他 Tab
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QGroupBox, QScrollArea)
from PyQt5.QtCore import pyqtSignal, Qt


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
        
        # 1. 设备信息操作组
        device_info_group = self.create_device_info_group()
        scroll_layout.addWidget(device_info_group)
        
        # 2. MTKlog操作组
        mtklog_ops_group = self.create_mtklog_ops_group()
        scroll_layout.addWidget(mtklog_ops_group)
        
        # 3. PCAP操作组
        pcap_ops_group = self.create_pcap_ops_group()
        scroll_layout.addWidget(pcap_ops_group)
        
        # 4. 赫拉配置组
        hera_config_group = self.create_hera_config_group()
        scroll_layout.addWidget(hera_config_group)
        
        # 5. 其他操作组
        other_ops_group = self.create_other_ops_group()
        scroll_layout.addWidget(other_ops_group)
        
        # 添加弹性空间
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
    def create_device_info_group(self):
        """创建设备信息操作组"""
        group = QGroupBox("设备信息")
        layout = QHBoxLayout(group)
        
        self.show_device_info_btn = QPushButton("手机信息")
        self.show_device_info_btn.clicked.connect(self.show_device_info_dialog.emit)
        layout.addWidget(self.show_device_info_btn)
        
        self.set_screen_timeout_btn = QPushButton("设置灭屏时间")
        self.set_screen_timeout_btn.clicked.connect(self.set_screen_timeout.emit)
        layout.addWidget(self.set_screen_timeout_btn)
        
        layout.addStretch()
        
        return group
        
    def create_mtklog_ops_group(self):
        """创建MTKlog操作组"""
        group = QGroupBox("MTKlog操作")
        layout = QHBoxLayout(group)
        
        self.merge_mtklog_btn = QPushButton("合并MTKlog")
        self.merge_mtklog_btn.clicked.connect(self.merge_mtklog.emit)
        layout.addWidget(self.merge_mtklog_btn)
        
        self.extract_pcap_from_mtklog_btn = QPushButton("MTKlog提取pcap")
        self.extract_pcap_from_mtklog_btn.clicked.connect(self.extract_pcap_from_mtklog.emit)
        layout.addWidget(self.extract_pcap_from_mtklog_btn)
        
        layout.addStretch()
        
        return group
        
    def create_pcap_ops_group(self):
        """创建PCAP操作组"""
        group = QGroupBox("PCAP操作")
        layout = QHBoxLayout(group)
        
        self.merge_pcap_btn = QPushButton("合并PCAP")
        self.merge_pcap_btn.clicked.connect(self.merge_pcap.emit)
        layout.addWidget(self.merge_pcap_btn)
        
        self.extract_pcap_from_qualcomm_log_btn = QPushButton("高通log提取pcap")
        self.extract_pcap_from_qualcomm_log_btn.clicked.connect(self.extract_pcap_from_qualcomm_log.emit)
        layout.addWidget(self.extract_pcap_from_qualcomm_log_btn)
        
        layout.addStretch()
        
        return group
        
    def create_hera_config_group(self):
        """创建赫拉配置组"""
        group = QGroupBox("赫拉配置")
        layout = QHBoxLayout(group)
        
        self.configure_hera_btn = QPushButton("赫拉配置")
        self.configure_hera_btn.clicked.connect(self.configure_hera.emit)
        layout.addWidget(self.configure_hera_btn)
        
        self.configure_collect_data_btn = QPushButton("赫拉测试数据收集")
        self.configure_collect_data_btn.clicked.connect(self.configure_collect_data.emit)
        layout.addWidget(self.configure_collect_data_btn)
        
        layout.addStretch()
        
        return group
        
    def create_other_ops_group(self):
        """创建其他操作组"""
        group = QGroupBox("其他操作")
        layout = QHBoxLayout(group)
        
        self.show_input_text_btn = QPushButton("输入文本")
        self.show_input_text_btn.clicked.connect(self.show_input_text_dialog.emit)
        layout.addWidget(self.show_input_text_btn)
        
        self.show_tools_config_btn = QPushButton("工具配置")
        self.show_tools_config_btn.clicked.connect(self.show_tools_config_dialog.emit)
        layout.addWidget(self.show_tools_config_btn)
        
        self.show_display_lines_btn = QPushButton("设置显示行数")
        self.show_display_lines_btn.clicked.connect(self.show_display_lines_dialog.emit)
        layout.addWidget(self.show_display_lines_btn)
        
        layout.addStretch()
        
        return group

