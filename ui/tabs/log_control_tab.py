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
    adblog_start = pyqtSignal()  # 保留原有信号，用于离线log
    adblog_online_start = pyqtSignal()  # 新增连线log信号
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
    
    # Log操作相关
    merge_mtklog = pyqtSignal()
    extract_pcap_from_mtklog = pyqtSignal()
    merge_pcap = pyqtSignal()
    extract_pcap_from_qualcomm_log = pyqtSignal()
    
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
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
        
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
        title = QLabel(self.lang_manager.tr("MTKLOG 控制"))
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
        
        self.mtklog_start_btn = QPushButton(self.lang_manager.tr("开启"))
        self.mtklog_start_btn.clicked.connect(self.mtklog_start.emit)
        row1.addWidget(self.mtklog_start_btn)
        
        self.mtklog_stop_export_btn = QPushButton(self.lang_manager.tr("停止&导出"))
        self.mtklog_stop_export_btn.clicked.connect(self.mtklog_stop_export.emit)
        row1.addWidget(self.mtklog_stop_export_btn)
        
        self.mtklog_delete_btn = QPushButton(self.lang_manager.tr("删除"))
        self.mtklog_delete_btn.clicked.connect(self.mtklog_delete.emit)
        row1.addWidget(self.mtklog_delete_btn)
        
        self.mtklog_set_log_size_btn = QPushButton(self.lang_manager.tr("设置log size"))
        self.mtklog_set_log_size_btn.clicked.connect(self.mtklog_set_log_size.emit)
        row1.addWidget(self.mtklog_set_log_size_btn)
        
        # 在第一行添加模式相关的按钮（不要模式标签）
        self.mtklog_sd_mode_btn = QPushButton(self.lang_manager.tr("SD模式"))
        self.mtklog_sd_mode_btn.clicked.connect(self.mtklog_sd_mode.emit)
        row1.addWidget(self.mtklog_sd_mode_btn)
        
        self.mtklog_usb_mode_btn = QPushButton(self.lang_manager.tr("USB模式"))
        self.mtklog_usb_mode_btn.clicked.connect(self.mtklog_usb_mode.emit)
        row1.addWidget(self.mtklog_usb_mode_btn)
        
        self.mtklog_install_btn = QPushButton(self.lang_manager.tr("安装MTKLOGGER"))
        self.mtklog_install_btn.clicked.connect(self.mtklog_install.emit)
        row1.addWidget(self.mtklog_install_btn)
        
        self.telephony_btn = QPushButton(self.lang_manager.tr("启用Telephony日志"))
        self.telephony_btn.clicked.connect(self.telephony_enable.emit)
        row1.addWidget(self.telephony_btn)
        
        row1.addStretch()
        card_layout.addLayout(row1)
        
        # 第二行：log操作
        row2 = QHBoxLayout()
        row2.addWidget(QLabel(self.lang_manager.tr("log操作:")))
        
        self.merge_mtklog_btn = QPushButton(self.lang_manager.tr("合并MTKlog"))
        self.merge_mtklog_btn.clicked.connect(self.merge_mtklog.emit)
        row2.addWidget(self.merge_mtklog_btn)
        
        self.extract_pcap_from_mtklog_btn = QPushButton(self.lang_manager.tr("MTKlog提取pcap"))
        self.extract_pcap_from_mtklog_btn.clicked.connect(self.extract_pcap_from_mtklog.emit)
        row2.addWidget(self.extract_pcap_from_mtklog_btn)
        
        self.merge_pcap_btn = QPushButton(self.lang_manager.tr("合并PCAP"))
        self.merge_pcap_btn.clicked.connect(self.merge_pcap.emit)
        row2.addWidget(self.merge_pcap_btn)
        
        self.extract_pcap_from_qualcomm_log_btn = QPushButton(self.lang_manager.tr("高通log提取pcap"))
        self.extract_pcap_from_qualcomm_log_btn.clicked.connect(self.extract_pcap_from_qualcomm_log.emit)
        row2.addWidget(self.extract_pcap_from_qualcomm_log_btn)
        
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
        title = QLabel(self.lang_manager.tr("ADB Log 控制"))
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
        
        self.adblog_online_btn = QPushButton(self.lang_manager.tr("连线log"))
        self.adblog_online_btn.clicked.connect(self.adblog_online_start.emit)
        row1.addWidget(self.adblog_online_btn)
        
        self.adblog_offline_btn = QPushButton(self.lang_manager.tr("离线log"))
        self.adblog_offline_btn.clicked.connect(self.adblog_start.emit)
        row1.addWidget(self.adblog_offline_btn)
        
        self.adblog_export_btn = QPushButton(self.lang_manager.tr("导出"))
        self.adblog_export_btn.clicked.connect(self.adblog_export.emit)
        row1.addWidget(self.adblog_export_btn)
        
        self.tcpdump_btn = QPushButton("TCPDUMP")
        self.tcpdump_btn.clicked.connect(self.tcpdump_show_dialog.emit)
        row1.addWidget(self.tcpdump_btn)
        
        row1.addStretch()
        card_layout.addLayout(row1)
        
        # 第二行：Google 日志
        row2 = QHBoxLayout()
        row2.addWidget(QLabel(self.lang_manager.tr("Google日志:")))
        
        self.google_log_btn = QPushButton(self.lang_manager.tr("Google 日志"))
        self.google_log_btn.clicked.connect(self.google_log_toggle.emit)
        row2.addWidget(self.google_log_btn)
        
        self.aee_log_btn = QPushButton("AEE Log")
        self.aee_log_btn.clicked.connect(self.aee_log_start.emit)
        row2.addWidget(self.aee_log_btn)
        
        self.bugreport_generate_btn = QPushButton(self.lang_manager.tr("生成 Bugreport"))
        self.bugreport_generate_btn.clicked.connect(self.bugreport_generate.emit)
        row2.addWidget(self.bugreport_generate_btn)
        
        self.bugreport_pull_btn = QPushButton("Pull Bugreport")
        self.bugreport_pull_btn.clicked.connect(self.bugreport_pull.emit)
        row2.addWidget(self.bugreport_pull_btn)
        
        self.bugreport_delete_btn = QPushButton(self.lang_manager.tr("删除 Bugreport"))
        self.bugreport_delete_btn.clicked.connect(self.bugreport_delete.emit)
        row2.addWidget(self.bugreport_delete_btn)
        
        row2.addStretch()
        card_layout.addLayout(row2)
        
        v.addWidget(card)
        
        return container
    
    def set_online_mode_started(self):
        """连线模式已启动，改变按钮状态"""
        stop_text = self.lang_manager.tr("停止")
        print(f"{self.tr('设置连线log按钮文本为: ')}'{stop_text}'")
        self.adblog_online_btn.setText(stop_text)
        self.adblog_online_btn.setStyleSheet("""
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
        self.adblog_online_btn.setText(self.lang_manager.tr("连线log"))
        self.adblog_online_btn.setStyleSheet("")
    
    def refresh_texts(self, lang_manager=None):
        """刷新所有文本（用于语言切换）"""
        if lang_manager:
            self.lang_manager = lang_manager
        
        if not self.lang_manager:
            return
        
        # 刷新MTKLOG控制按钮
        if hasattr(self, 'mtklog_start_btn'):
            self.mtklog_start_btn.setText(self.lang_manager.tr("开启"))
        if hasattr(self, 'mtklog_stop_export_btn'):
            self.mtklog_stop_export_btn.setText(self.lang_manager.tr("停止&导出"))
        if hasattr(self, 'mtklog_delete_btn'):
            self.mtklog_delete_btn.setText(self.lang_manager.tr("删除"))
        if hasattr(self, 'mtklog_set_log_size_btn'):
            self.mtklog_set_log_size_btn.setText(self.lang_manager.tr("设置log size"))
        if hasattr(self, 'mtklog_sd_mode_btn'):
            self.mtklog_sd_mode_btn.setText(self.lang_manager.tr("SD模式"))
        if hasattr(self, 'mtklog_usb_mode_btn'):
            self.mtklog_usb_mode_btn.setText(self.lang_manager.tr("USB模式"))
        if hasattr(self, 'mtklog_install_btn'):
            self.mtklog_install_btn.setText(self.lang_manager.tr("安装MTKLOGGER"))
        
        # 刷新ADB Log控制按钮
        if hasattr(self, 'adblog_online_btn'):
            if self.adblog_online_btn.text() in ["连线log", "Online Log"]:
                self.adblog_online_btn.setText(self.lang_manager.tr("连线log"))
            elif self.adblog_online_btn.text() in ["停止", "Stop"]:
                self.adblog_online_btn.setText(self.lang_manager.tr("停止"))
        if hasattr(self, 'adblog_offline_btn'):
            self.adblog_offline_btn.setText(self.lang_manager.tr("离线log"))
        if hasattr(self, 'adblog_export_btn'):
            self.adblog_export_btn.setText(self.lang_manager.tr("导出"))
        
        # 刷新其他按钮
        if hasattr(self, 'telephony_btn'):
            self.telephony_btn.setText(self.lang_manager.tr("启用Telephony日志"))
        if hasattr(self, 'google_log_btn'):
            if "Google" in self.google_log_btn.text():
                self.google_log_btn.setText(self.lang_manager.tr("Google 日志"))
            elif "停止" in self.google_log_btn.text():
                self.google_log_btn.setText(self.lang_manager.tr("停止 Google 日志"))
        if hasattr(self, 'bugreport_generate_btn'):
            self.bugreport_generate_btn.setText(self.lang_manager.tr("生成 Bugreport"))
        if hasattr(self, 'bugreport_pull_btn'):
            self.bugreport_pull_btn.setText(self.lang_manager.tr("拉取 Bugreport"))
        if hasattr(self, 'bugreport_delete_btn'):
            self.bugreport_delete_btn.setText(self.lang_manager.tr("删除 Bugreport"))
        if hasattr(self, 'aee_log_start_btn'):
            self.aee_log_start_btn.setText(self.lang_manager.tr("AEE日志"))
        if hasattr(self, 'tcpdump_btn'):
            self.tcpdump_btn.setText(self.lang_manager.tr("TCPDUMP"))
        
        # 刷新组标题标签
        self._refresh_section_titles()
    
    def _refresh_section_titles(self):
        """刷新组标题标签"""
        # 查找所有QLabel并刷新标题
        for label in self.findChildren(QLabel):
            current_text = label.text()
            # 根据当前文本匹配对应的翻译
            if current_text in ["MTKLOG 控制", "MTKLOG Control"]:
                label.setText(self.lang_manager.tr("MTKLOG 控制"))
            elif current_text in ["ADB Log 控制", "ADB Log Control"]:
                label.setText(self.lang_manager.tr("ADB Log 控制"))
            elif current_text in ["模式:", "Mode:"]:
                label.setText(self.lang_manager.tr("模式:"))
            elif current_text in ["Google日志:", "Google Log:"]:
                label.setText(self.lang_manager.tr("Google日志:"))

