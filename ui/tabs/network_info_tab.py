#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络信息 Tab
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QGroupBox, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QFrame)
from PyQt5.QtCore import pyqtSignal, Qt
from ui.widgets.shadow_utils import add_card_shadow


class NetworkInfoTab(QWidget):
    """网络信息 Tab"""
    
    # 信号定义
    # 网络信息控制
    start_network_info = pyqtSignal()
    stop_network_info = pyqtSignal()
    
    # Ping 控制
    start_ping = pyqtSignal()
    stop_ping = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_network_running = False
        self.is_ping_running = False
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 创建水平布局（控制面板 + 信息显示）
        container_layout = QHBoxLayout()
        
        # 左侧控制面板
        control_panel = self.create_control_panel()
        container_layout.addWidget(control_panel, 0)
        
        # 右侧信息显示区域
        info_panel = self.create_info_panel()
        container_layout.addWidget(info_panel, 1)
        
        main_layout.addLayout(container_layout)
        
    def create_control_panel(self):
        """创建控制面板（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel("控制")
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # 按钮行
        button_layout = QHBoxLayout()
        
        self.network_button = QPushButton("开始")
        self.network_button.clicked.connect(self._on_toggle_network_info)
        button_layout.addWidget(self.network_button)
        
        self.ping_button = QPushButton("Ping")
        self.ping_button.clicked.connect(self._on_toggle_ping)
        button_layout.addWidget(self.ping_button)
        
        layout.addLayout(button_layout)
        
        # 状态标签
        self.network_status_label = QLabel("未启动")
        self.network_status_label.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(self.network_status_label)
        
        self.ping_status_label = QLabel("")
        self.ping_status_label.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(self.ping_status_label)
        
        # 添加弹性空间
        layout.addStretch()
        
        v.addWidget(card)
        
        return container
        
    def create_info_panel(self):
        """创建信息显示面板（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel("网络信息")
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # 创建表格
        self.network_table = QTableWidget()
        self.network_table.setColumnCount(16)
        self.network_table.setHorizontalHeaderLabels([
            "SIM", "CC", "RAT", "BAND", "DL_ARFCN", "UL_ARFCN", 
            "PCI", "RSRP", "RSRQ", "SINR", "RSSI", 
            "BW_DL", "BW_UL", "CA/ENDC", "CQI", "NOTE"
        ])
        
        # 设置表格属性
        self.network_table.setAlternatingRowColors(False)  # 禁用交替行颜色，避免显示问题
        self.network_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.network_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # 设置列调整模式 - 允许手动调整列宽
        self.network_table.horizontalHeader().setStretchLastSection(True)  # 最后一列自动拉伸
        self.network_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)  # 允许手动调整
        
        # 设置初始列宽
        self.network_table.setColumnWidth(0, 50)   # SIM
        self.network_table.setColumnWidth(1, 50)   # CC
        self.network_table.setColumnWidth(2, 50)   # RAT
        self.network_table.setColumnWidth(3, 60)   # BAND
        self.network_table.setColumnWidth(4, 80)   # DL_ARFCN
        self.network_table.setColumnWidth(5, 80)   # UL_ARFCN
        self.network_table.setColumnWidth(6, 50)   # PCI
        self.network_table.setColumnWidth(7, 60)   # RSRP
        self.network_table.setColumnWidth(8, 60)   # RSRQ
        self.network_table.setColumnWidth(9, 60)   # SINR
        self.network_table.setColumnWidth(10, 60)  # RSSI
        self.network_table.setColumnWidth(11, 60)  # BW_DL
        self.network_table.setColumnWidth(12, 60)  # BW_UL
        self.network_table.setColumnWidth(13, 120) # CA/ENDC
        self.network_table.setColumnWidth(14, 50)  # CQI
        self.network_table.setColumnWidth(15, 150) # NOTE (最后一列自动拉伸)
        
        # 设置选中行的样式
        self.network_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #555555;
                background-color: #2b2b2b;
                color: #ffffff;
                alternate-background-color: #2b2b2b;
            }
            QTableCornerButton::section {
                background-color: #2b2b2b;
                border: none;
            }
            QTableWidget::item {
                padding: 2px;
            }
            QTableWidget::item:selected {
                background-color: #0078d4;
                color: #ffffff;
            }
            QTableWidget::item:hover {
                background-color: #4a4a4a;
            }
            QHeaderView::section {
                background-color: #3a3a3a;
                color: #ffffff;
                padding: 4px;
                border: 1px solid #555555;
            }
            QScrollBar:horizontal {
                background-color: white;
                height: 12px;
                border: none;
                margin: 0px;
            }
            QScrollBar::groove:horizontal {
                background-color: white;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #666666;
                min-width: 30px;
                border-radius: 6px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #888888;
            }
            QScrollBar::handle:horizontal:pressed {
                background-color: #aaaaaa;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                height: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background-color: white;
            }
            QScrollBar:vertical {
                background-color: white;
                width: 12px;
                border: none;
                margin: 0px;
            }
            QScrollBar::groove:vertical {
                background-color: white;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #666666;
                min-height: 30px;
                border-radius: 6px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #888888;
            }
            QScrollBar::handle:vertical:pressed {
                background-color: #aaaaaa;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                width: 0px;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background-color: white;
            }
        """)
        
        # 初始提示文本
        self._show_initial_message()
        
        layout.addWidget(self.network_table)
        
        v.addWidget(card)
        
        return container
        
    def _show_initial_message(self):
        """显示初始提示信息"""
        self.network_table.setRowCount(1)
        self.network_table.setColumnCount(1)
        self.network_table.setHorizontalHeaderLabels(["提示"])
        
        item = QTableWidgetItem("点击'开始'按钮获取网络信息")
        item.setTextAlignment(Qt.AlignCenter)
        item.setForeground(Qt.gray)
        self.network_table.setItem(0, 0, item)
        self.network_table.horizontalHeader().setStretchLastSection(True)
        
    def _on_toggle_network_info(self):
        """切换网络信息获取状态"""
        if self.is_network_running:
            # 停止时立即改变状态
            self.stop_network_info.emit()
            self.is_network_running = False
            self.network_button.setText("开始")
            self.network_button.setStyleSheet("")
            self.network_status_label.setText("已停止")
            self.network_status_label.setStyleSheet("color: gray; font-size: 9pt;")
        else:
            # 开始时只发送信号，等待成功回调再改变状态
            self.start_network_info.emit()
            
    def _on_toggle_ping(self):
        """切换 Ping 状态"""
        if self.is_ping_running:
            # 停止时立即改变状态
            self.stop_ping.emit()
            self.is_ping_running = False
            self.ping_button.setText("Ping")
            self.ping_button.setStyleSheet("")
            self.ping_status_label.setText("")
        else:
            # 开始时只发送信号，等待成功回调再改变状态
            self.start_ping.emit()
            
    def set_network_state(self, is_running):
        """设置网络信息状态"""
        self.is_network_running = is_running
        if is_running:
            self.network_button.setText("停止")
            self.network_button.setStyleSheet("background-color: #f44336; color: white;")
            self.network_status_label.setText("运行中...")
            self.network_status_label.setStyleSheet("color: green; font-size: 9pt;")
        else:
            self.network_button.setText("开始")
            self.network_button.setStyleSheet("")
            self.network_status_label.setText("已停止")
            self.network_status_label.setStyleSheet("color: gray; font-size: 9pt;")
            
    def set_ping_state(self, is_running):
        """设置 Ping 状态"""
        self.is_ping_running = is_running
        if is_running:
            self.ping_button.setText("停止")
            self.ping_button.setStyleSheet("background-color: #f44336; color: white;")
            self.ping_status_label.setText("Ping中...")
            self.ping_status_label.setStyleSheet("color: blue; font-size: 9pt;")
        else:
            self.ping_button.setText("Ping")
            self.ping_button.setStyleSheet("")
            self.ping_status_label.setText("")
            
    def update_network_table(self, data):
        """更新网络信息表格
        
        Args:
            data: 网络信息数据列表，每个元素是一个字典
        """
        if not data:
            self._show_initial_message()
            return
            
        # 设置列数和表头
        self.network_table.setColumnCount(16)
        self.network_table.setHorizontalHeaderLabels([
            "SIM", "CC", "RAT", "BAND", "DL_ARFCN", "UL_ARFCN", 
            "PCI", "RSRP", "RSRQ", "SINR", "RSSI", 
            "BW_DL", "BW_UL", "CA/ENDC", "CQI", "NOTE"
        ])
        
        # 设置行数
        self.network_table.setRowCount(len(data))
        
        # 填充数据
        for row, item in enumerate(data):
            self.network_table.setItem(row, 0, QTableWidgetItem(str(item.get('sim', ''))))
            self.network_table.setItem(row, 1, QTableWidgetItem(str(item.get('cc', ''))))
            self.network_table.setItem(row, 2, QTableWidgetItem(str(item.get('rat', ''))))
            self.network_table.setItem(row, 3, QTableWidgetItem(str(item.get('band', ''))))
            self.network_table.setItem(row, 4, QTableWidgetItem(str(item.get('dl_arfcn', ''))))
            self.network_table.setItem(row, 5, QTableWidgetItem(str(item.get('ul_arfcn', ''))))
            self.network_table.setItem(row, 6, QTableWidgetItem(str(item.get('pci', ''))))
            self.network_table.setItem(row, 7, QTableWidgetItem(str(item.get('rsrp', ''))))
            self.network_table.setItem(row, 8, QTableWidgetItem(str(item.get('rsrq', ''))))
            self.network_table.setItem(row, 9, QTableWidgetItem(str(item.get('sinr', ''))))
            self.network_table.setItem(row, 10, QTableWidgetItem(str(item.get('rssi', ''))))
            self.network_table.setItem(row, 11, QTableWidgetItem(str(item.get('bw_dl', ''))))
            self.network_table.setItem(row, 12, QTableWidgetItem(str(item.get('bw_ul', ''))))
            self.network_table.setItem(row, 13, QTableWidgetItem(str(item.get('ca_endc', ''))))
            self.network_table.setItem(row, 14, QTableWidgetItem(str(item.get('cqi', ''))))
            self.network_table.setItem(row, 15, QTableWidgetItem(str(item.get('note', ''))))
            
    def update_ping_status(self, status_text):
        """更新 Ping 状态文本"""
        # 如果收到 ping_stopped 消息，重置 UI 状态
        if status_text == "ping_stopped":
            self.is_ping_running = False
            self.ping_button.setText("Ping")
            self.ping_button.setStyleSheet("")
            self.ping_status_label.setText("")
            return
        
        self.ping_status_label.setText(status_text)
        # 根据状态设置颜色：网络正常=绿色，网络异常=红色
        if status_text == "网络正常":
            self.ping_status_label.setStyleSheet("color: green; font-size: 9pt;")
        elif status_text == "网络异常":
            self.ping_status_label.setStyleSheet("color: red; font-size: 9pt;")
        else:
            self.ping_status_label.setStyleSheet("color: blue; font-size: 9pt;")

