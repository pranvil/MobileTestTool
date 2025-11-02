#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
菜单栏
"""

from PyQt5.QtWidgets import (QMenuBar, QAction, QDialog, QVBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QButtonGroup,
                             QRadioButton, QHBoxLayout, QMessageBox,
                             QWidget, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
import os
from ui.widgets.shadow_utils import add_card_shadow


class MenuBar(QMenuBar):
    """菜单栏"""
    
    # 信号定义
    show_display_lines_dialog = None  # 将在外部设置
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.setup_menu()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_menu(self):
        """设置菜单"""
        # 工具菜单
        tools_menu = self.addMenu(self.tr("工具"))
        
        # 设置显示行数
        display_lines_action = QAction(self.tr("设置显示行数"), self)
        tools_menu.addAction(display_lines_action)
        
        # 连接信号（将在外部设置）
        self.display_lines_action = display_lines_action


class DisplayLinesDialog(QDialog):
    """设置显示行数对话框"""
    
    def __init__(self, current_lines=5000, parent=None):
        super().__init__(parent)
        self.current_lines = current_lines
        self.result_lines = current_lines
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle(self.lang_manager.tr("设置最大显示行数"))
        self.setFixedSize(450, 450)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel(self.lang_manager.tr("设置最大显示行数"))
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        main_layout.addWidget(title_label)
        
        # 当前设置显示
        current_label = QLabel(f"{self.lang_manager.tr('当前设置:')} {self.current_lines} {self.lang_manager.tr('行')}")
        main_layout.addWidget(current_label)
        
        # 输入框
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel(self.lang_manager.tr("最大显示行数:")))
        self.lines_edit = QLineEdit(str(self.current_lines))
        self.lines_edit.setFixedWidth(150)
        input_layout.addWidget(self.lines_edit)
        input_layout.addStretch()
        main_layout.addLayout(input_layout)
        
        # 预设选项组（使用与Tab界面一致的样式：QLabel + QFrame）
        presets_container = QWidget()
        presets_container_layout = QVBoxLayout(presets_container)
        presets_container_layout.setContentsMargins(0, 0, 0, 0)
        presets_container_layout.setSpacing(4)
        
        presets_title = QLabel(self.lang_manager.tr("快速选择"))
        presets_title.setProperty("class", "section-title")
        presets_container_layout.addWidget(presets_title)
        
        presets_card = QFrame()
        presets_card.setObjectName("card")
        add_card_shadow(presets_card)
        presets_layout = QVBoxLayout(presets_card)
        presets_layout.setContentsMargins(10, 1, 10, 1)
        presets_layout.setSpacing(8)
        
        self.presets_group = QButtonGroup()
        presets = [
            (self.lang_manager.tr("1000行 (轻量)"), 1000),
            (self.lang_manager.tr("2000行 (标准)"), 2000),
            (self.lang_manager.tr("5000行 (推荐)"), 5000),
            (self.lang_manager.tr("10000行 (大量)"), 10000),
            (self.lang_manager.tr("20000行 (超大)"), 20000)
        ]
        
        for text, value in presets:
            radio = QRadioButton(text)
            if value == self.current_lines:
                radio.setChecked(True)
            self.presets_group.addButton(radio, value)
            presets_layout.addWidget(radio)
            radio.toggled.connect(lambda checked, v=value: self._on_preset_selected(v) if checked else None)
        
        presets_container_layout.addWidget(presets_card)
        main_layout.addWidget(presets_container)
        
        # 说明文本
        info_label = QLabel(self.lang_manager.tr("设置说明: 行数越多显示更多历史日志，建议范围: 1000-20000 行"))
        info_label.setStyleSheet("color: gray;")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_btn = QPushButton(self.lang_manager.tr("确定"))
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton(self.lang_manager.tr("取消"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(button_layout)
    
    def _on_preset_selected(self, value):
        """预设选项被选中"""
        self.lines_edit.setText(str(value))
    
    def get_lines(self):
        """获取设置的行数"""
        try:
            lines = int(self.lines_edit.text())
            if lines < 100:
                QMessageBox.warning(self, self.lang_manager.tr("错误"), "行数不能少于100行")
                return None
            if lines > 100000:
                QMessageBox.warning(self, self.lang_manager.tr("错误"), "行数不能超过100000行")
                return None
            return lines
        except ValueError:
            QMessageBox.warning(self, self.lang_manager.tr("错误"), "请输入有效的数字")
            return None
    
    def accept(self):
        """确定按钮"""
        lines = self.get_lines()
        if lines is not None:
            self.result_lines = lines
            super().accept()


# ToolsConfigDialog 已移动到 ui/tools_config_dialog.py

