#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高通SMS解析对话框（支持多条消息）
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QComboBox, QLineEdit, QTextEdit, QPushButton, 
                              QDialogButtonBox, QMessageBox, QScrollArea, 
                              QWidget, QFrame, QGroupBox)
from PyQt5.QtCore import Qt


class SMSMessageWidget(QFrame):
    """单条SMS消息输入组件"""
    
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
        
        # SMS类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel(self.tr("SMS类型:")))
        self.sms_type_combo = QComboBox()
        self.sms_type_combo.addItems(["MO SMS", "MT SMS"])
        type_layout.addWidget(self.sms_type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)
        
        # 数据长度输入
        length_layout = QHBoxLayout()
        length_layout.addWidget(QLabel(self.tr("数据长度:")))
        self.length_edit = QLineEdit()
        self.length_edit.setPlaceholderText(self.tr("请输入数据长度（十进制）"))
        length_layout.addWidget(self.length_edit)
        length_layout.addStretch()
        layout.addLayout(length_layout)
        
        # 十六进制数据输入
        data_label = QLabel(self.tr("SMS 16进制数据:"))
        layout.addWidget(data_label)
        
        self.hex_data_edit = QTextEdit()
        self.hex_data_edit.setPlaceholderText(self.tr("请输入SMS的16进制数据（可以包含空格、制表符、换行符）"))
        self.hex_data_edit.setMinimumHeight(120)
        layout.addWidget(self.hex_data_edit)
    
    def get_inputs(self):
        """获取用户输入"""
        return {
            'sms_type': self.sms_type_combo.currentText(),
            'length': self.length_edit.text().strip(),
            'hex_data': self.hex_data_edit.toPlainText()
        }
    
    def validate(self):
        """验证输入"""
        # 验证数据长度
        try:
            length = int(self.length_edit.text().strip())
            if length <= 0:
                return False, self.tr("数据长度必须大于0")
        except ValueError:
            return False, self.tr("请输入有效的数字作为数据长度")
        
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
        
        return True, None


class SMSParserDialog(QDialog):
    """SMS解析对话框（支持多条消息）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.message_widgets = []
        self.setWindowTitle(self.tr("高通SMS解析"))
        self.setModal(True)
        self.resize(700, 600)
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
        widget = SMSMessageWidget(index, self.lang_manager, self)
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
            messages.append({
                'sms_type': inputs['sms_type'],
                'length': int(inputs['length']),
                'hex_data': inputs['hex_data']
            })
        return messages
