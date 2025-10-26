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
    
    # AT工具
    show_at_tool_dialog = pyqtSignal()
    
    # 自定义界面管理
    show_unified_manager = pyqtSignal()
    
    # 暗码管理
    show_secret_code_dialog = pyqtSignal()
    
    # 高通lock cell
    show_lock_cell_dialog = pyqtSignal()
    
    def __init__(self, parent=None):
        try:
            super().__init__(parent)
            # 从父窗口获取语言管理器
            if parent and hasattr(parent, 'lang_manager'):
                self.lang_manager = parent.lang_manager
            else:
                # 如果没有父窗口或语言管理器，使用单例
                from core.language_manager import LanguageManager
                self.lang_manager = LanguageManager.get_instance()
            self.setup_ui()
        except Exception as e:
            logger.exception(self.lang_manager.tr("OtherTab 初始化失败"))
            raise
        
    def setup_ui(self):
        """设置UI"""
        try:
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
            
            # 1. 设备信息、赫拉配置、其他操作组（同一行）
            first_row_container = QWidget()
            first_row_layout = QHBoxLayout(first_row_container)
            first_row_layout.setContentsMargins(0, 0, 0, 0)
            first_row_layout.setSpacing(10)
            
            device_info_group = self.create_device_info_group()
            first_row_layout.addWidget(device_info_group)
            
            hera_config_group = self.create_hera_config_group()
            first_row_layout.addWidget(hera_config_group)
            
            log_ops_group = self.create_log_ops_group()
            first_row_layout.addWidget(log_ops_group)
            
            scroll_layout.addWidget(first_row_container)
            
            # 2. log操作组（合并PCAP和MTKlog操作）


            other_ops_group = self.create_other_ops_group()
            scroll_layout.addWidget(other_ops_group)            
            # 添加弹性空间
            scroll_layout.addStretch()
            
            scroll.setWidget(scroll_content)
            main_layout.addWidget(scroll)
            
            logger.debug(self.lang_manager.tr("OtherTab UI设置完成"))
            
        except Exception as e:
            logger.exception(self.lang_manager.tr("OtherTab.setup_ui 失败"))
            raise
        
    def create_device_info_group(self):
        """创建设备信息操作组（现代结构：QLabel + QFrame）"""
        try:
            # 容器
            container = QWidget()
            v = QVBoxLayout(container)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(4)
            
            # 标题
            title = QLabel(self.lang_manager.tr("设备信息"))
            title.setProperty("class", "section-title")
            v.addWidget(title)
            
            # 卡片
            card = QFrame()
            card.setObjectName("card")
            add_card_shadow(card)
            
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(10, 1, 10, 1)
            card_layout.setSpacing(8)
            
            self.show_device_info_btn = QPushButton(self.lang_manager.tr("手机信息"))
            self.show_device_info_btn.clicked.connect(self.show_device_info_dialog.emit)
            card_layout.addWidget(self.show_device_info_btn)
            
            self.set_screen_timeout_btn = QPushButton(self.lang_manager.tr("设置灭屏时间"))
            self.set_screen_timeout_btn.clicked.connect(self.set_screen_timeout.emit)
            card_layout.addWidget(self.set_screen_timeout_btn)

            self.secret_code_btn = QPushButton("🔑 " + self.lang_manager.tr("暗码"))
            self.secret_code_btn.clicked.connect(self.show_secret_code_dialog.emit)
            card_layout.addWidget(self.secret_code_btn)
            
            self.lock_cell_btn = QPushButton("📱 " + self.lang_manager.tr("高通lock cell"))
            self.lock_cell_btn.clicked.connect(self.show_lock_cell_dialog.emit)
            card_layout.addWidget(self.lock_cell_btn)
                     
            card_layout.addStretch()
            
            v.addWidget(card)
            
            return container
        except Exception as e:
            logger.exception(self.lang_manager.tr("create_device_info_group 失败"))
            raise
        
        
    def create_hera_config_group(self):
        """创建赫拉配置组（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel(self.lang_manager.tr("赫拉配置"))
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        self.configure_hera_btn = QPushButton(self.lang_manager.tr("赫拉配置"))
        self.configure_hera_btn.clicked.connect(self.configure_hera.emit)
        card_layout.addWidget(self.configure_hera_btn)
        
        self.configure_collect_data_btn = QPushButton(self.lang_manager.tr("赫拉测试数据收集"))
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
        title = QLabel(self.lang_manager.tr("其他操作"))
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        self.show_input_text_btn = QPushButton(self.lang_manager.tr("输入文本"))
        self.show_input_text_btn.clicked.connect(self.show_input_text_dialog.emit)
        card_layout.addWidget(self.show_input_text_btn)
        
        self.show_tools_config_btn = QPushButton(self.lang_manager.tr("工具配置"))
        self.show_tools_config_btn.clicked.connect(self.show_tools_config_dialog.emit)
        card_layout.addWidget(self.show_tools_config_btn)
        
        self.show_display_lines_btn = QPushButton(self.lang_manager.tr("设置显示行数"))
        self.show_display_lines_btn.clicked.connect(self.show_display_lines_dialog.emit)
        card_layout.addWidget(self.show_display_lines_btn)
        
        self.show_at_tool_btn = QPushButton("📡 " + self.lang_manager.tr("AT工具"))
        self.show_at_tool_btn.clicked.connect(self.show_at_tool_dialog.emit)
        card_layout.addWidget(self.show_at_tool_btn)
        
        self.unified_manager_btn = QPushButton("⚙️ " + self.lang_manager.tr("自定义界面管理"))
        self.unified_manager_btn.clicked.connect(self.show_unified_manager.emit)
        self.unified_manager_btn.setStyleSheet("""
            QPushButton {
                background-color: #6f42c1;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a32a3;
            }
        """)
        card_layout.addWidget(self.unified_manager_btn)
        

        
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
        title = QLabel(self.lang_manager.tr("log操作"))
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
        
        self.merge_mtklog_btn = QPushButton(self.lang_manager.tr("合并MTKlog"))
        self.merge_mtklog_btn.clicked.connect(self.merge_mtklog.emit)
        row1_layout.addWidget(self.merge_mtklog_btn)
        
        self.extract_pcap_from_mtklog_btn = QPushButton(self.lang_manager.tr("MTKlog提取pcap"))
        self.extract_pcap_from_mtklog_btn.clicked.connect(self.extract_pcap_from_mtklog.emit)
        row1_layout.addWidget(self.extract_pcap_from_mtklog_btn)
              
        self.merge_pcap_btn = QPushButton(self.lang_manager.tr("合并PCAP"))
        self.merge_pcap_btn.clicked.connect(self.merge_pcap.emit)
        row1_layout.addWidget(self.merge_pcap_btn)
        
        self.extract_pcap_from_qualcomm_log_btn = QPushButton(self.lang_manager.tr("高通log提取pcap"))
        self.extract_pcap_from_qualcomm_log_btn.clicked.connect(self.extract_pcap_from_qualcomm_log.emit)
        row1_layout.addWidget(self.extract_pcap_from_qualcomm_log_btn)
        
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
        
        # 刷新设备信息组按钮
        if hasattr(self, 'show_device_info_btn'):
            self.show_device_info_btn.setText(self.lang_manager.tr("手机信息"))
        if hasattr(self, 'set_screen_timeout_btn'):
            self.set_screen_timeout_btn.setText(self.lang_manager.tr("设置灭屏时间"))
        
        # 刷新赫拉配置组按钮
        if hasattr(self, 'configure_hera_btn'):
            self.configure_hera_btn.setText(self.lang_manager.tr("赫拉配置"))
        if hasattr(self, 'configure_collect_data_btn'):
            self.configure_collect_data_btn.setText(self.lang_manager.tr("赫拉测试数据收集"))
        
        # 刷新其他操作组按钮
        if hasattr(self, 'show_input_text_btn'):
            self.show_input_text_btn.setText(self.lang_manager.tr("输入文本"))
        if hasattr(self, 'show_tools_config_btn'):
            self.show_tools_config_btn.setText(self.lang_manager.tr("工具配置"))
        if hasattr(self, 'show_display_lines_btn'):
            self.show_display_lines_btn.setText(self.lang_manager.tr("设置显示行数"))
        if hasattr(self, 'show_at_tool_btn'):
            self.show_at_tool_btn.setText("📡 " + self.lang_manager.tr("AT工具"))
        if hasattr(self, 'custom_button_manager_btn'):
            self.custom_button_manager_btn.setText("🔧 " + self.lang_manager.tr("管理自定义按钮"))
        if hasattr(self, 'tab_manager_btn'):
            self.tab_manager_btn.setText("📋 " + self.lang_manager.tr("Tab管理"))
        if hasattr(self, 'secret_code_btn'):
            self.secret_code_btn.setText("🔑 " + self.lang_manager.tr("暗码"))
        if hasattr(self, 'lock_cell_btn'):
            self.lock_cell_btn.setText("📱 " + self.lang_manager.tr("高通lock cell"))

        # 刷新log操作组按钮
        if hasattr(self, 'merge_mtklog_btn'):
            self.merge_mtklog_btn.setText(self.lang_manager.tr("合并MTKlog"))
        if hasattr(self, 'extract_pcap_from_mtklog_btn'):
            self.extract_pcap_from_mtklog_btn.setText(self.lang_manager.tr("MTKlog提取pcap"))
        if hasattr(self, 'merge_pcap_btn'):
            self.merge_pcap_btn.setText(self.lang_manager.tr("合并PCAP"))
        if hasattr(self, 'extract_pcap_from_qualcomm_log_btn'):
            self.extract_pcap_from_qualcomm_log_btn.setText(self.lang_manager.tr("高通log提取pcap"))
    
    def _refresh_section_titles(self):
        """刷新组标题标签"""
        # 查找所有QLabel并刷新标题
        for label in self.findChildren(QLabel):
            current_text = label.text()
            # 根据当前文本匹配对应的翻译
            if current_text in ["设备信息", "Device Information"]:
                label.setText(self.lang_manager.tr("设备信息"))
            elif current_text in ["赫拉配置", "Hera Configuration"]:
                label.setText(self.lang_manager.tr("赫拉配置"))
            elif current_text in ["其他操作", "Other Operations"]:
                label.setText(self.lang_manager.tr("其他操作"))
            elif current_text in ["log操作", "Log Operations"]:
                label.setText(self.lang_manager.tr("log操作"))
