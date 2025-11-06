#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3GPP RRC/NAS/SMS 消息解码对话框（支持多条消息）
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QComboBox, QLineEdit, QTextEdit, QPushButton, 
                              QDialogButtonBox, QMessageBox, QScrollArea, 
                              QWidget, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontMetrics


# 协议列表（根据技术类型）
PROTOCOLS = {
    'SMS': ['MO SMS', 'MT SMS'],
    'LTE': [
        'NAS-EPS',
        'NAS-EPS_plain',
        'LTE-RRC.BCCH.BCH',
        'LTE-RRC.BCCH.DL.SCH',
        'LTE-RRC.BCCH.DL.SCH.BR',
        'LTE-RRC.DL.CCCH',
        'LTE-RRC.DL.DCCH',
        'LTE-RRC.PCCH',
        'LTE-RRC.RRCConnectionReconfiguration',
        'LTE-RRC.SC.MCCH',
        'LTE-RRC.UE-EUTRA-Capability',
        'LTE-RRC.UECapabilityInformation',
        'LTE-RRC.UL.CCCH',
        'LTE-RRC.UL.DCCH',
    ],
    '5G': [
        'NAS-5GS',
        'NR-RRC.BCCH.BCH',
        'NR-RRC.BCCH.DL.SCH',
        'NR-RRC.DL.CCCH',
        'NR-RRC.DL.DCCH',
        'NR-RRC.PCCH',
        'NR-RRC.UL.CCCH',
        'NR-RRC.UL.DCCH',
        'NR-RRC.CellGroupConfig',
        'NR-RRC.HandoverCommand',
        'NR-RRC.HandoverPreparationInformation',
        'NR-RRC.MeasConfig',
        'NR-RRC.MeasGapConfig',
    ]
}


class RRC3GPPMessageWidget(QFrame):
    """单条3GPP消息输入组件"""
    
    def __init__(self, index, lang_manager, parent=None):
        super().__init__(parent)
        self.index = index
        self.lang_manager = lang_manager
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("QFrame { border: 1px solid #ccc; border-radius: 4px; padding: 5px; }")
        self.setup_ui()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # 标题栏（显示序号和删除按钮）
        header_layout = QHBoxLayout()
        title_label = QLabel(self.tr("消息 #{}").format(self.index + 1))
        title_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        self.delete_btn = QPushButton("✖ " + self.tr("删除"))
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 4px 12px;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        header_layout.addWidget(self.delete_btn)
        layout.addLayout(header_layout)
        
        # 技术类型选择
        tech_layout = QHBoxLayout()
        tech_layout.addWidget(QLabel(self.tr("技术类型:")))
        self.technology_combo = QComboBox()
        self.technology_combo.addItems(['SMS', 'LTE', '5G'])
        self.technology_combo.currentTextChanged.connect(self.on_technology_changed)
        tech_layout.addWidget(self.technology_combo)
        tech_layout.addStretch()
        layout.addLayout(tech_layout)
        
        # 协议选择
        protocol_layout = QHBoxLayout()
        protocol_layout.addWidget(QLabel(self.tr("协议:")))
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(PROTOCOLS['SMS'])  # 默认SMS
        # 设置下拉菜单自动调整宽度
        self.protocol_combo.setSizeAdjustPolicy(QComboBox.AdjustToContentsOnFirstShow)
        # 重写 showPopup 方法以动态调整下拉列表宽度
        original_show_popup = self.protocol_combo.showPopup
        def adjusted_show_popup():
            original_show_popup()
            # 计算所有选项的最大宽度
            font_metrics = QFontMetrics(self.protocol_combo.font())
            max_width = 0
            for i in range(self.protocol_combo.count()):
                text = self.protocol_combo.itemText(i)
                # 使用 horizontalAdvance 方法（PyQt5 推荐），如果不存在则使用 width
                if hasattr(font_metrics, 'horizontalAdvance'):
                    width = font_metrics.horizontalAdvance(text)
                else:
                    width = font_metrics.width(text)
                max_width = max(max_width, width)
            # 设置下拉列表的最小宽度（加上一些边距和滚动条宽度）
            view = self.protocol_combo.view()
            if view:
                min_width = max_width + 50  # 50像素用于边距和滚动条
                view.setMinimumWidth(min_width)
        self.protocol_combo.showPopup = adjusted_show_popup
        protocol_layout.addWidget(self.protocol_combo)
        protocol_layout.addStretch()
        layout.addLayout(protocol_layout)
        
        # 数据长度输入（仅SMS显示）
        self.length_layout = QHBoxLayout()
        self.length_label = QLabel(self.tr("数据长度:"))
        self.length_edit = QLineEdit()
        self.length_edit.setPlaceholderText(self.tr("请输入数据长度（十进制）"))
        self.length_layout.addWidget(self.length_label)
        self.length_layout.addWidget(self.length_edit)
        self.length_layout.addStretch()
        layout.addLayout(self.length_layout)
        
        # 十六进制数据输入
        data_label = QLabel(self.tr("16进制数据:"))
        layout.addWidget(data_label)
        
        self.hex_data_edit = QTextEdit()
        self.hex_data_edit.setPlaceholderText(self.tr("请输入16进制数据（可以包含空格、制表符、换行符）"))
        self.hex_data_edit.setMinimumHeight(120)
        layout.addWidget(self.hex_data_edit)
    
    def on_technology_changed(self, technology):
        """技术类型改变时更新协议列表"""
        self.protocol_combo.clear()
        if technology in PROTOCOLS:
            self.protocol_combo.addItems(PROTOCOLS[technology])
        
        # 显示/隐藏长度输入框（仅SMS需要）
        if technology == 'SMS':
            self.length_label.setVisible(True)
            self.length_edit.setVisible(True)
        else:
            self.length_label.setVisible(False)
            self.length_edit.setVisible(False)
    
    def get_inputs(self):
        """获取用户输入"""
        technology = self.technology_combo.currentText()
        protocol = self.protocol_combo.currentText()
        hex_data = self.hex_data_edit.toPlainText()
        
        result = {
            'technology': technology,
            'protocol': protocol,
            'hex_data': hex_data
        }
        
        # 只有SMS才需要length
        if technology == 'SMS':
            length_str = self.length_edit.text().strip()
            result['length'] = int(length_str) if length_str else None
        else:
            result['length'] = None
        
        return result
    
    def validate(self):
        """验证输入"""
        technology = self.technology_combo.currentText()
        protocol = self.protocol_combo.currentText()
        
        # 验证十六进制数据
        hex_data = self.hex_data_edit.toPlainText().strip()
        if not hex_data:
            return False, self.tr("请输入16进制数据")
        
        # 验证是否为有效的十六进制
        compact = "".join(hex_data.split())
        try:
            int(compact, 16)
        except ValueError:
            return False, self.tr("输入的16进制数据格式不正确")
        
        # SMS需要验证数据长度
        if technology == 'SMS':
            try:
                length = int(self.length_edit.text().strip())
                if length <= 0:
                    return False, self.tr("数据长度必须大于0")
            except ValueError:
                return False, self.tr("请输入有效的数字作为数据长度")
        
        return True, None


class RRC3GPPDecoderDialog(QDialog):
    """3GPP消息解码对话框（支持多条消息）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.message_widgets = []
        self.setWindowTitle(self.tr("3GPP消息解码器"))
        self.setModal(True)
        self.resize(750, 650)
        self.setup_ui()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # 顶部：消息数量和添加按钮
        top_layout = QHBoxLayout()
        self.count_label = QLabel(self.tr("当前消息数量: 1"))
        top_layout.addWidget(self.count_label)
        top_layout.addStretch()
        
        self.add_message_btn = QPushButton("➕ " + self.tr("添加消息"))
        self.add_message_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 6px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.add_message_btn.clicked.connect(self.add_message)
        top_layout.addWidget(self.add_message_btn)
        layout.addLayout(top_layout)
        
        # 中间：滚动区域，包含所有消息输入组
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(5, 5, 5, 5)
        self.scroll_layout.setSpacing(10)
        
        scroll_area.setWidget(self.scroll_content)
        layout.addWidget(scroll_area)
        
        # 底部：确认/取消按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
        # 添加第一条消息
        self.add_message()
    
    def add_message(self):
        """添加一条消息输入组"""
        index = len(self.message_widgets)
        widget = RRC3GPPMessageWidget(index, self.lang_manager, self)
        widget.delete_btn.clicked.connect(lambda checked, w=widget: self.remove_message(w))
        
        self.message_widgets.append(widget)
        self.scroll_layout.addWidget(widget)
        self.update_count_label()
    
    def remove_message(self, widget):
        """删除一条消息输入组"""
        if len(self.message_widgets) <= 1:
            QMessageBox.warning(self, self.tr("提示"), self.tr("至少需要保留一条消息"))
            return
        
        self.message_widgets.remove(widget)
        self.scroll_layout.removeWidget(widget)
        widget.deleteLater()
        
        # 重新编号
        for i, w in enumerate(self.message_widgets):
            w.index = i
            title_label = w.findChildren(QLabel)[0]  # 第一个QLabel是标题
            if title_label:
                title_label.setText(self.tr("消息 #{}").format(i + 1))
        
        self.update_count_label()
    
    def update_count_label(self):
        """更新消息数量标签"""
        count = len(self.message_widgets)
        self.count_label.setText(self.tr("当前消息数量: {}").format(count))
    
    def validate_and_accept(self):
        """验证所有输入并接受"""
        if not self.message_widgets:
            QMessageBox.warning(self, self.tr("输入错误"), self.tr("至少需要输入一条消息"))
            return
        
        # 验证所有消息
        errors = []
        for i, widget in enumerate(self.message_widgets):
            is_valid, error_msg = widget.validate()
            if not is_valid:
                errors.append(self.tr("消息 #{}: {}").format(i + 1, error_msg))
        
        if errors:
            QMessageBox.warning(self, self.tr("输入错误"), 
                              self.tr("以下消息输入有误:\n\n{}").format("\n".join(errors)))
            return
        
        self.accept()
    
    def get_inputs(self):
        """获取所有用户输入"""
        messages = []
        for widget in self.message_widgets:
            inputs = widget.get_inputs()
            messages.append(inputs)
        return messages

