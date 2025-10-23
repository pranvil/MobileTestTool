#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
输入文本对话框
"""

import subprocess
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextEdit, QPushButton, QMessageBox)
from PyQt5.QtCore import Qt


class InputTextDialog(QDialog):
    """输入文本对话框"""
    
    def __init__(self, device, parent=None):
        super().__init__(parent)
        self.device = device
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle(self.lang_manager.tr("输入文本到设备"))
        self.setFixedSize(500, 400)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel(self.lang_manager.tr("输入文本到Android设备"))
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        main_layout.addWidget(title_label)
        
        # 说明文本
        info_label = QLabel(
            self.lang_manager.tr("请在下方输入框中输入要发送到设备的文本。\n"
            "注意：空格和特殊字符会被正确处理。")
        )
        info_label.setStyleSheet("color: gray;")
        main_layout.addWidget(info_label)
        
        # 文本输入框
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText(self.lang_manager.tr("在此输入要发送到设备的文本..."))
        main_layout.addWidget(self.text_input)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton(self.lang_manager.tr("取消"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        clear_btn = QPushButton(self.lang_manager.tr("清空"))
        clear_btn.clicked.connect(self.text_input.clear)
        button_layout.addWidget(clear_btn)
        
        send_btn = QPushButton(self.lang_manager.tr("发送"))
        send_btn.clicked.connect(self._on_send)
        button_layout.addWidget(send_btn)
        
        main_layout.addLayout(button_layout)
        
        # 设置焦点
        self.text_input.setFocus()
    
    def _on_send(self):
        """发送文本"""
        text_to_send = self.text_input.toPlainText().strip()
        if not text_to_send:
            QMessageBox.warning(self, self.lang_manager.tr("输入错误"), self.lang_manager.tr("请输入要发送的文本"))
            return
        
        # 发送文本
        success = self._send_text_to_device(text_to_send)
        if success:
            # 成功发送，清空输入框，让用户继续输入
            self.text_input.clear()
            self.text_input.setFocus()
        else:
            QMessageBox.critical(self, self.lang_manager.tr("失败"), self.lang_manager.tr("文本发送失败，请检查设备连接"))
    
    def _send_text_to_device(self, text):
        """发送文本到设备"""
        try:
            # 处理特殊字符和空格
            processed_text = self._process_text_for_adb(text)
            
            # 发送文本
            cmd = ["adb", "-s", self.device, "shell", "input", "text", processed_text]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                return True
            else:
                return False
        except Exception as e:
            print(f"{self.lang_manager.tr('发送文本失败')}: {str(e)}")
            return False
    
    def _process_text_for_adb(self, text):
        """处理文本以适配adb命令"""
        # adb shell input text 对某些字符有限制
        # 需要转义特殊字符
        processed = text.replace(' ', '%s')  # 空格
        processed = processed.replace('&', '\\&')
        processed = processed.replace('<', '\\<')
        processed = processed.replace('>', '\\>')
        processed = processed.replace('(', '\\(')
        processed = processed.replace(')', '\\)')
        processed = processed.replace('|', '\\|')
        processed = processed.replace(';', '\\;')
        processed = processed.replace('*', '\\*')
        processed = processed.replace('?', '\\?')
        processed = processed.replace('`', '\\`')
        processed = processed.replace('$', '\\$')
        processed = processed.replace('"', '\\"')
        processed = processed.replace("'", "\\'")
        processed = processed.replace('\\', '\\\\')
        processed = processed.replace('!', '\\!')
        
        return processed

