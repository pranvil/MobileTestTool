#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5 搜索管理模块
负责日志搜索、高亮和导航功能
"""

import re
from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QCheckBox, QPushButton, QTextEdit,
                             QMessageBox, QFileDialog, QTextCursor, QFrame)
from PyQt5.QtGui import QTextCharFormat, QColor, QFont


class SearchDialog(QDialog):
    """搜索对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("搜索")
        self.setModal(True)
        self.resize(450, 200)
        
        # 搜索相关变量
        self.search_keyword = ""
        self.search_case_sensitive = False
        self.search_use_regex = False
        self.search_results = []
        self.current_result_index = 0
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 搜索关键字
        keyword_layout = QHBoxLayout()
        keyword_layout.addWidget(QLabel("搜索关键字:"))
        
        self.keyword_entry = QLineEdit()
        self.keyword_entry.setPlaceholderText("输入搜索关键字")
        self.keyword_entry.returnPressed.connect(self.perform_search)
        keyword_layout.addWidget(self.keyword_entry)
        
        layout.addLayout(keyword_layout)
        
        # 搜索选项
        options_layout = QHBoxLayout()
        
        self.case_sensitive_check = QCheckBox("区分大小写")
        self.case_sensitive_check.setChecked(False)
        options_layout.addWidget(self.case_sensitive_check)
        
        self.use_regex_check = QCheckBox("正则表达式")
        self.use_regex_check.setChecked(False)
        options_layout.addWidget(self.use_regex_check)
        
        options_layout.addStretch()
        
        layout.addLayout(options_layout)
        
        # 搜索状态显示
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: blue;")
        layout.addWidget(self.status_label)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.search_btn = QPushButton("搜索")
        self.search_btn.clicked.connect(self.perform_search)
        button_layout.addWidget(self.search_btn)
        
        self.next_btn = QPushButton("下一个")
        self.next_btn.clicked.connect(self.find_next)
        button_layout.addWidget(self.next_btn)
        
        self.prev_btn = QPushButton("上一个")
        self.prev_btn.clicked.connect(self.find_previous)
        button_layout.addWidget(self.prev_btn)
        
        self.all_btn = QPushButton("查找所有")
        self.all_btn.clicked.connect(self.show_all_results)
        button_layout.addWidget(self.all_btn)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
        # 设置焦点
        self.keyword_entry.setFocus()
    
    def perform_search(self):
        """执行搜索"""
        keyword = self.keyword_entry.text().strip()
        if not keyword:
            QMessageBox.warning(self, "警告", "请输入搜索关键字")
            return
        
        # 保存搜索参数
        self.search_keyword = keyword
        self.search_case_sensitive = self.case_sensitive_check.isChecked()
        self.search_use_regex = self.use_regex_check.isChecked()
        
        # 验证正则表达式
        if self.search_use_regex:
            try:
                re.compile(keyword)
            except re.error as e:
                QMessageBox.critical(self, "错误", f"正则表达式无效: {e}")
                return
        
        # 发送搜索信号
        self.search_requested.emit(keyword, self.search_case_sensitive, self.search_use_regex)
    
    def find_next(self):
        """查找下一个"""
        if not self.search_results:
            self.perform_search()
        else:
            self.next_requested.emit()
    
    def find_previous(self):
        """查找上一个"""
        if not self.search_results:
            self.perform_search()
        else:
            self.prev_requested.emit()
    
    def show_all_results(self):
        """显示所有结果"""
        if not self.search_keyword:
            QMessageBox.warning(self, "警告", "请输入搜索关键字")
            return
        
        self.show_all_requested.emit()
    
    def update_status(self, message):
        """更新状态显示"""
        self.status_label.setText(message)
    
    # 信号定义
    search_requested = pyqtSignal(str, bool, bool)  # keyword, case_sensitive, use_regex
    next_requested = pyqtSignal()
    prev_requested = pyqtSignal()
    show_all_requested = pyqtSignal()


class SearchResultsWindow(QDialog):
    """搜索结果窗口"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("搜索结果")
        self.setModal(True)
        self.resize(1000, 600)
        
        self.search_keyword = ""
        self.search_case_sensitive = False
        self.search_use_regex = False
        self.matching_lines = []
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题和统计信息
        title_layout = QHBoxLayout()
        
        title_label = QLabel(f"搜索关键字: {self.search_keyword}")
        title_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        title_layout.addWidget(title_label)
        
        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: blue;")
        title_layout.addWidget(self.count_label)
        
        title_layout.addStretch()
        
        # 按钮
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.select_all)
        title_layout.addWidget(self.select_all_btn)
        
        self.copy_btn = QPushButton("复制")
        self.copy_btn.clicked.connect(self.copy_results)
        title_layout.addWidget(self.copy_btn)
        
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_results)
        title_layout.addWidget(self.save_btn)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        title_layout.addWidget(self.close_btn)
        
        layout.addLayout(title_layout)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # 文本显示区域
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Cascadia Mono", 10))
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #0C0C0C;
                color: #FFFFFF;
                selection-background-color: #444444;
            }
        """)
        
        layout.addWidget(self.text_edit)
    
    def set_search_params(self, keyword, case_sensitive, use_regex):
        """设置搜索参数"""
        self.search_keyword = keyword
        self.search_case_sensitive = case_sensitive
        self.search_use_regex = use_regex
    
    def set_matching_lines(self, lines):
        """设置匹配的行"""
        self.matching_lines = lines
        self.count_label.setText(f"找到 {len(lines)} 个匹配项")
        self.fill_results()
    
    def fill_results(self):
        """填充搜索结果"""
        self.text_edit.clear()
        
        # 准备搜索模式
        if self.search_use_regex:
            try:
                flags = 0 if self.search_case_sensitive else re.IGNORECASE
                pattern = self.search_keyword
            except re.error:
                pattern = re.escape(self.search_keyword)
                flags = 0 if self.search_case_sensitive else re.IGNORECASE
        else:
            pattern = re.escape(self.search_keyword)
            flags = 0 if self.search_case_sensitive else re.IGNORECASE
        
        # 配置高亮格式
        highlight_format = QTextCharFormat()
        highlight_format.setForeground(QColor("#FF4444"))
        
        # 显示匹配的行
        for line_num, line in self.matching_lines:
            # 添加行号
            cursor = self.text_edit.textCursor()
            cursor.movePosition(cursor.End)
            cursor.insertText(f"[{line_num:4d}] ")
            
            # 添加高亮文本
            self.add_highlighted_line(cursor, line, pattern, flags, highlight_format)
            cursor.insertText("\n")
        
        # 移动到顶部
        self.text_edit.moveCursor(QTextCursor.Start)
    
    def add_highlighted_line(self, cursor, line, pattern, flags, highlight_format):
        """向文本光标添加高亮行"""
        matches = list(re.finditer(pattern, line, flags))
        
        if not matches:
            cursor.insertText(line)
            return
        
        # 插入高亮文本
        last_end = 0
        for match in matches:
            # 插入普通文本
            if match.start() > last_end:
                cursor.insertText(line[last_end:match.start()])
            
            # 插入高亮文本
            cursor.insertText(match.group(), highlight_format)
            last_end = match.end()
        
        # 插入剩余文本
        if last_end < len(line):
            cursor.insertText(line[last_end:])
    
    def select_all(self):
        """全选"""
        self.text_edit.selectAll()
        self.text_edit.setFocus()
    
    def copy_results(self):
        """复制搜索结果"""
        # 检查是否有选中文本
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
        else:
            # 如果没有选中文本，复制全部内容
            selected_text = self.text_edit.toPlainText()
        
        self.text_edit.copy()
        QMessageBox.information(self, "成功", "搜索结果已复制到剪贴板")
    
    def save_results(self):
        """保存搜索结果到文件"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存搜索结果",
                f"搜索结果_{self.search_keyword}.txt",
                "文本文件 (*.txt);;所有文件 (*.*)"
            )
            
            if file_path:
                # 获取文本内容
                content = self.text_edit.toPlainText()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                QMessageBox.information(self, "成功", f"搜索结果已保存到: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")


class PyQtSearchManager(QObject):
    """PyQt5 搜索管理器"""
    
    # 信号定义
    status_message = pyqtSignal(str)
    
    def __init__(self, log_viewer, parent=None):
        super().__init__(parent)
        self.log_viewer = log_viewer
        self.search_dialog = None
        self.results_window = None
        
        # 搜索相关变量
        self.search_keyword = ""
        self.search_case_sensitive = False
        self.search_use_regex = False
        self.search_results = []
        self.current_result_index = 0
        
        # 高亮格式
        self.highlight_format = QTextCharFormat()
        self.highlight_format.setBackground(QColor("#FFFF00"))
        self.highlight_format.setForeground(QColor("#000000"))
    
    def show_search_dialog(self):
        """显示搜索对话框"""
        if not self.search_dialog:
            self.search_dialog = SearchDialog()
            self.search_dialog.search_requested.connect(self.perform_search)
            self.search_dialog.next_requested.connect(self.find_next)
            self.search_dialog.prev_requested.connect(self.find_previous)
            self.search_dialog.show_all_requested.connect(self.show_all_results)
        
        self.search_dialog.show()
        self.search_dialog.raise_()
        self.search_dialog.activateWindow()
        self.search_dialog.keyword_entry.setFocus()
    
    def perform_search(self, keyword, case_sensitive, use_regex):
        """执行搜索"""
        if not keyword:
            QMessageBox.warning(None, "警告", "请输入搜索关键字")
            return
        
        # 保存搜索参数
        self.search_keyword = keyword
        self.search_case_sensitive = case_sensitive
        self.search_use_regex = use_regex
        
        # 验证正则表达式
        if self.search_use_regex:
            try:
                re.compile(keyword)
            except re.error as e:
                QMessageBox.critical(None, "错误", f"正则表达式无效: {e}")
                return
        
        # 获取文本内容
        text_content = self.log_viewer.text_edit.toPlainText()
        
        # 如果文本为空，提示用户
        if not text_content.strip():
            QMessageBox.information(None, "提示", "没有日志内容可搜索")
            return
        
        # 清除之前的高亮
        self.clear_search_highlight()
        
        # 执行搜索
        self.search_results = []
        self.current_result_index = 0
        
        # 准备搜索模式
        if self.search_use_regex:
            try:
                flags = 0 if self.search_case_sensitive else re.IGNORECASE
                pattern = keyword
            except re.error:
                pattern = re.escape(keyword)
                flags = 0 if self.search_case_sensitive else re.IGNORECASE
        else:
            pattern = re.escape(keyword)
            flags = 0 if self.search_case_sensitive else re.IGNORECASE
        
        # 查找所有匹配
        for match in re.finditer(pattern, text_content, flags):
            start_pos = match.start()
            end_pos = match.end()
            self.search_results.append((start_pos, end_pos))
        
        if self.search_results:
            # 高亮所有匹配
            cursor = self.log_viewer.text_edit.textCursor()
            for start_pos, end_pos in self.search_results:
                cursor.setPosition(start_pos)
                cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
                cursor.setCharFormat(self.highlight_format)
            
            # 跳转到第一个匹配
            self.current_result_index = 0
            self.jump_to_search_result()
            
            # 更新状态显示
            self.status_message.emit(f"找到 {len(self.search_results)} 个匹配项")
            if self.search_dialog:
                self.search_dialog.update_status(f"找到 {len(self.search_results)} 个匹配项，当前第 {self.current_result_index + 1} 个")
        else:
            QMessageBox.information(None, "搜索结果", "未找到匹配项")
    
    def find_next(self):
        """查找下一个匹配项"""
        if not self.search_results:
            # 如果没有搜索结果，先尝试执行搜索
            if self.search_dialog:
                keyword = self.search_dialog.keyword_entry.text().strip()
                if keyword:
                    self.perform_search(
                        keyword,
                        self.search_dialog.case_sensitive_check.isChecked(),
                        self.search_dialog.use_regex_check.isChecked()
                    )
                    if self.search_results:
                        self.jump_to_search_result()
                        if self.search_dialog:
                            self.search_dialog.update_status(f"找到 {len(self.search_results)} 个匹配项，当前第 {self.current_result_index + 1} 个")
                else:
                    QMessageBox.information(None, "提示", "请先输入搜索关键字")
            return
        
        if self.current_result_index < len(self.search_results) - 1:
            self.current_result_index += 1
        else:
            self.current_result_index = 0  # 循环到第一个
        
        self.jump_to_search_result()
        
        # 更新搜索状态显示
        if self.search_dialog:
            self.search_dialog.update_status(f"找到 {len(self.search_results)} 个匹配项，当前第 {self.current_result_index + 1} 个")
    
    def find_previous(self):
        """查找上一个匹配项"""
        if not self.search_results:
            # 如果没有搜索结果，先尝试执行搜索
            if self.search_dialog:
                keyword = self.search_dialog.keyword_entry.text().strip()
                if keyword:
                    self.perform_search(
                        keyword,
                        self.search_dialog.case_sensitive_check.isChecked(),
                        self.search_dialog.use_regex_check.isChecked()
                    )
                    if self.search_results:
                        # 跳转到最后一个结果
                        self.current_result_index = len(self.search_results) - 1
                        self.jump_to_search_result()
                        if self.search_dialog:
                            self.search_dialog.update_status(f"找到 {len(self.search_results)} 个匹配项，当前第 {self.current_result_index + 1} 个")
                else:
                    QMessageBox.information(None, "提示", "请先输入搜索关键字")
            return
        
        if self.current_result_index > 0:
            self.current_result_index -= 1
        else:
            self.current_result_index = len(self.search_results) - 1  # 循环到最后一个
        
        self.jump_to_search_result()
        
        # 更新搜索状态显示
        if self.search_dialog:
            self.search_dialog.update_status(f"找到 {len(self.search_results)} 个匹配项，当前第 {self.current_result_index + 1} 个")
    
    def jump_to_search_result(self):
        """跳转到当前搜索结果"""
        if not self.search_results:
            return
        
        start_pos, end_pos = self.search_results[self.current_result_index]
        
        # 跳转到匹配位置
        cursor = self.log_viewer.text_edit.textCursor()
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
        self.log_viewer.text_edit.setTextCursor(cursor)
        self.log_viewer.text_edit.ensureCursorVisible()
        
        # 更新状态
        self.status_message.emit(f"找到 {len(self.search_results)} 个匹配项，当前第 {self.current_result_index + 1} 个")
    
    def clear_search_highlight(self):
        """清除搜索高亮"""
        # 重新设置字符格式为默认格式
        cursor = self.log_viewer.text_edit.textCursor()
        cursor.select(QTextCursor.Document)
        default_format = QTextCharFormat()
        cursor.setCharFormat(default_format)
        cursor.clearSelection()
        self.log_viewer.text_edit.setTextCursor(cursor)
    
    def show_all_results(self):
        """显示所有搜索结果"""
        if not self.search_keyword:
            QMessageBox.warning(None, "警告", "请输入搜索关键字")
            return
        
        # 如果没有搜索结果，先执行搜索
        if not self.search_results:
            if self.search_dialog:
                keyword = self.search_dialog.keyword_entry.text().strip()
                if keyword:
                    self.perform_search(
                        keyword,
                        self.search_dialog.case_sensitive_check.isChecked(),
                        self.search_dialog.use_regex_check.isChecked()
                    )
                    if not self.search_results:
                        return
                else:
                    QMessageBox.warning(None, "警告", "请输入搜索关键字")
                    return
            else:
                return
        
        # 创建结果显示窗口
        if not self.results_window:
            self.results_window = SearchResultsWindow()
        
        self.results_window.set_search_params(
            self.search_keyword,
            self.search_case_sensitive,
            self.search_use_regex
        )
        
        # 获取匹配的行
        text_content = self.log_viewer.text_edit.toPlainText()
        lines = text_content.split('\n')
        
        # 准备搜索模式
        if self.search_use_regex:
            try:
                flags = 0 if self.search_case_sensitive else re.IGNORECASE
                pattern = self.search_keyword
            except re.error:
                pattern = re.escape(self.search_keyword)
                flags = 0 if self.search_case_sensitive else re.IGNORECASE
        else:
            pattern = re.escape(self.search_keyword)
            flags = 0 if self.search_case_sensitive else re.IGNORECASE
        
        # 查找包含关键字的行
        matching_lines = []
        for i, line in enumerate(lines):
            if re.search(pattern, line, flags):
                matching_lines.append((i + 1, line))  # 行号从1开始
        
        self.results_window.set_matching_lines(matching_lines)
        self.results_window.show()
        self.results_window.raise_()
        self.results_window.activateWindow()

