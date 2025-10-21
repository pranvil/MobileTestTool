#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Log过滤 Tab
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QCheckBox, QPushButton, QGroupBox,
                             QScrollArea, QFrame)
from PyQt5.QtCore import pyqtSignal, Qt
from ui.widgets.shadow_utils import add_card_shadow


class LogFilterTab(QWidget):
    """Log过滤 Tab"""
    
    # 信号定义
    # 过滤控制
    start_filtering = pyqtSignal()
    stop_filtering = pyqtSignal()
    
    # 常用操作
    manage_log_keywords = pyqtSignal()  # 打开关键字管理对话框
    clear_logs = pyqtSignal()
    clear_device_logs = pyqtSignal()
    show_display_lines_dialog = pyqtSignal()
    save_logs = pyqtSignal()
    
    # 选项变化
    keyword_changed = pyqtSignal(str)
    use_regex_changed = pyqtSignal(bool)
    case_sensitive_changed = pyqtSignal(bool)
    color_highlight_changed = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_filtering = False
        # 从父窗口获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            # 如果没有父窗口或语言管理器，创建一个默认的
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager()
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
        
        # 1. 过滤控制组
        filter_control_group = self.create_filter_control_group()
        scroll_layout.addWidget(filter_control_group)
        
        
        # 添加弹性空间
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
    def create_filter_control_group(self):
        """创建过滤控制组（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel(self.lang_manager.tr("过滤控制"))
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        # 使用垂直布局作为主布局，但按钮区域使用水平布局
        main_layout = QVBoxLayout(card)
        main_layout.setContentsMargins(10, 1, 10, 1)
        main_layout.setSpacing(8)
        
        # 第一行：关键字输入和选项在同一行
        first_row_layout = QHBoxLayout()
        
        # 关键字输入（占三分之一宽度）
        keyword_label = QLabel(self.lang_manager.tr("关键字:"))
        first_row_layout.addWidget(keyword_label)
        
        self.keyword_entry = QLineEdit()
        self.keyword_entry.setPlaceholderText(self.lang_manager.tr("输入过滤关键字"))
        self.keyword_entry.setFixedWidth(400)
        self.keyword_entry.returnPressed.connect(self._on_start_stop_filtering)
        self.keyword_entry.textChanged.connect(self.keyword_changed.emit)
        first_row_layout.addWidget(self.keyword_entry)
  
        # 选项复选框（放在输入框右侧）
        self.use_regex_check = QCheckBox(self.lang_manager.tr("正则表达式"))
        self.use_regex_check.setChecked(True)
        self.use_regex_check.toggled.connect(self.use_regex_changed.emit)
        first_row_layout.addWidget(self.use_regex_check)
        
        self.case_sensitive_check = QCheckBox(self.lang_manager.tr("区分大小写"))
        self.case_sensitive_check.setChecked(False)
        self.case_sensitive_check.toggled.connect(self.case_sensitive_changed.emit)
        first_row_layout.addWidget(self.case_sensitive_check)
        
        self.color_highlight_check = QCheckBox(self.lang_manager.tr("彩色高亮"))
        self.color_highlight_check.setChecked(True)
        self.color_highlight_check.toggled.connect(self.color_highlight_changed.emit)
        first_row_layout.addWidget(self.color_highlight_check)
        
        first_row_layout.addStretch()
        
        main_layout.addLayout(first_row_layout)
        
        # 第二行：开始/停止按钮和其他操作按钮
        button_layout = QHBoxLayout()
        
        self.filter_button = QPushButton(self.lang_manager.tr("开始过滤"))
        self.filter_button.clicked.connect(self._on_start_stop_filtering)
        button_layout.addWidget(self.filter_button)
        
        # 添加其他操作按钮
        self.manage_keywords_btn = QPushButton(self.lang_manager.tr("管理log关键字"))
        self.manage_keywords_btn.clicked.connect(self.manage_log_keywords.emit)
        button_layout.addWidget(self.manage_keywords_btn)
        
        self.set_lines_btn = QPushButton(self.lang_manager.tr("设置行数"))
        self.set_lines_btn.clicked.connect(self.show_display_lines_dialog.emit)
        button_layout.addWidget(self.set_lines_btn)
        
        self.save_logs_btn = QPushButton(self.lang_manager.tr("保存日志"))
        self.save_logs_btn.clicked.connect(self.save_logs.emit)
        button_layout.addWidget(self.save_logs_btn)
        
        self.clear_cache_btn = QPushButton(self.lang_manager.tr("清除缓存"))
        self.clear_cache_btn.clicked.connect(self.clear_device_logs.emit)
        button_layout.addWidget(self.clear_cache_btn)
        
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
        
        v.addWidget(card)
        
        return container
        
        
    def _on_start_stop_filtering(self):
        """开始/停止过滤"""
        if self.is_filtering:
            self.stop_filtering.emit()
            # 停止过滤的状态更新将由信号处理
        else:
            self.start_filtering.emit()
            # 开始过滤的状态更新将由信号处理
            
    def set_filtering_state(self, is_filtering):
        """设置过滤状态"""
        self.is_filtering = is_filtering
        if is_filtering:
            self.filter_button.setText(self.lang_manager.tr("停止过滤"))
            self.filter_button.setStyleSheet("background-color: #f44336; color: white;")
            # 过滤时禁用输入框和相关控件
            self.keyword_entry.setEnabled(False)
            self.use_regex_check.setEnabled(False)
            self.case_sensitive_check.setEnabled(False)
            self.color_highlight_check.setEnabled(False)
        else:
            self.filter_button.setText(self.lang_manager.tr("开始过滤"))
            self.filter_button.setStyleSheet("")
            # 停止过滤时启用输入框和相关控件
            self.keyword_entry.setEnabled(True)
            self.use_regex_check.setEnabled(True)
            self.case_sensitive_check.setEnabled(True)
            self.color_highlight_check.setEnabled(True)
            
    def get_keyword(self):
        """获取关键字"""
        return self.keyword_entry.text()
        
    def set_keyword(self, keyword):
        """设置关键字"""
        self.keyword_entry.setText(keyword)
        
    def is_use_regex(self):
        """是否使用正则表达式"""
        return self.use_regex_check.isChecked()
        
    def is_case_sensitive(self):
        """是否区分大小写"""
        return self.case_sensitive_check.isChecked()
        
    def is_color_highlight(self):
        """是否彩色高亮"""
        return self.color_highlight_check.isChecked()
    
    def refresh_texts(self, lang_manager=None):
        """刷新所有文本（用于语言切换）"""
        if lang_manager:
            self.lang_manager = lang_manager
        
        if not self.lang_manager:
            return
        
        # 刷新按钮文本
        if hasattr(self, 'start_filter_btn'):
            self.start_filter_btn.setText(self.lang_manager.tr("开始过滤"))
        if hasattr(self, 'stop_filter_btn'):
            self.stop_filter_btn.setText(self.lang_manager.tr("停止过滤"))
        if hasattr(self, 'manage_keywords_btn'):
            self.manage_keywords_btn.setText(self.lang_manager.tr("管理log关键字"))
        if hasattr(self, 'set_lines_btn'):
            self.set_lines_btn.setText(self.lang_manager.tr("设置行数"))
        if hasattr(self, 'save_logs_btn'):
            self.save_logs_btn.setText(self.lang_manager.tr("保存日志"))
        if hasattr(self, 'clear_cache_btn'):
            self.clear_cache_btn.setText(self.lang_manager.tr("清除缓存"))
        
        # 刷新标签文本
        if hasattr(self, 'keyword_label'):
            self.keyword_label.setText(self.lang_manager.tr("关键字:"))
        if hasattr(self, 'use_regex_check'):
            self.use_regex_check.setText(self.lang_manager.tr("正则表达式"))
        if hasattr(self, 'case_sensitive_check'):
            self.case_sensitive_check.setText(self.lang_manager.tr("区分大小写"))
        if hasattr(self, 'color_highlight_check'):
            self.color_highlight_check.setText(self.lang_manager.tr("彩色高亮"))
        
        # 刷新输入框占位符
        if hasattr(self, 'keyword_entry'):
            self.keyword_entry.setPlaceholderText(self.lang_manager.tr("输入过滤关键字..."))
        
        # 刷新组标题标签
        self._refresh_section_titles()
    
    def _refresh_section_titles(self):
        """刷新组标题标签"""
        # 查找所有QLabel并刷新标题
        for label in self.findChildren(QLabel):
            current_text = label.text()
            # 根据当前文本匹配对应的翻译
            if current_text in ["过滤控制", "Filter Control"]:
                label.setText(self.lang_manager.tr("过滤控制"))
            elif current_text in ["关键字:", "Keywords:"]:
                label.setText(self.lang_manager.tr("关键字:"))

