#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志查看器
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QLabel,
                             QHBoxLayout, QPushButton, QLineEdit, QCheckBox,
                             QSizePolicy, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QTextCharFormat, QColor, QTextCursor, QFont, QTextDocument


class LogViewer(QWidget):
    """日志查看器控件"""
    
    # 信号定义
    search_requested = pyqtSignal(str, bool)  # keyword, case_sensitive
    adb_command_executed = pyqtSignal(str)  # 执行adb命令
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 从父窗口获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            # 如果没有父窗口或语言管理器，创建一个默认的
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager()
        
        # 搜索相关
        self.search_keyword = ""
        self.search_case_sensitive = False
        self.search_results = []
        self.current_search_index = -1
        
        self.setup_ui()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 标题行：日志内容标签 + 搜索工具栏
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(5, 5, 5, 5)
        
        # 日志显示标签（左侧）
        label = QLabel(self.lang_manager.tr("日志内容"))
        label.setStyleSheet("font-weight: bold;")
        label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        title_layout.addWidget(label)
        
        # 搜索工具栏（右侧）
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(5)
        
        search_label = QLabel(self.lang_manager.tr("搜索:"))
        search_layout.addWidget(search_label)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self.lang_manager.tr("输入搜索关键字..."))
        self.search_edit.returnPressed.connect(self.on_return_pressed)
        search_layout.addWidget(self.search_edit)
        
        self.search_btn = QPushButton(self.lang_manager.tr("搜索"))
        self.search_btn.clicked.connect(self.on_search)
        search_layout.addWidget(self.search_btn)
        
        self.search_all_btn = QPushButton(self.lang_manager.tr("搜索全部"))
        self.search_all_btn.clicked.connect(self.show_all_results)
        search_layout.addWidget(self.search_all_btn)
        
        self.case_check = QCheckBox(self.lang_manager.tr("区分大小写"))
        search_layout.addWidget(self.case_check)
        
        self.prev_btn = QPushButton(self.lang_manager.tr("上一个"))
        self.prev_btn.clicked.connect(self.find_previous)
        search_layout.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton(self.lang_manager.tr("下一个"))
        self.next_btn.clicked.connect(self.find_next)
        search_layout.addWidget(self.next_btn)
        
        self.clear_btn = QPushButton(self.lang_manager.tr("清空日志"))
        self.clear_btn.clicked.connect(self.clear_logs)
        search_layout.addWidget(self.clear_btn)
        
        # 在"日志内容"和搜索工具栏之间添加小间距
        title_layout.addSpacing(10)
        title_layout.addLayout(search_layout)
        
        # 添加弹性空间将搜索工具栏推到右侧
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # 日志文本编辑框
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Cascadia Mono", 10))
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
        """)
        
        # 配置文本格式
        self.default_format = QTextCharFormat()
        self.default_format.setForeground(QColor("#ffffff"))
        
        # 关键字高亮格式（用于过滤时的高亮）
        self.highlight_format = QTextCharFormat()
        self.highlight_format.setForeground(QColor("#FF4444"))
        self.highlight_format.setFontWeight(700)  # 加粗
        
        # 搜索高亮格式（用于搜索时的高亮）
        self.search_highlight_format = QTextCharFormat()
        self.search_highlight_format.setForeground(QColor("#00FF00"))  # 绿色字体
        
        layout.addWidget(self.text_edit)
        
        # ADB命令输入区域（日志显示区域下方）
        adb_frame = QFrame()
        adb_frame.setStyleSheet("background-color: #2a2a2a; padding: 5px;")
        adb_layout_h = QHBoxLayout(adb_frame)
        adb_layout_h.setContentsMargins(5, 5, 5, 5)
        adb_layout_h.setSpacing(5)
        
        adb_label = QLabel(self.lang_manager.tr("ADB命令:"))
        adb_layout_h.addWidget(adb_label)
        
        self.adb_input = QLineEdit()
        self.adb_input.setPlaceholderText(self.lang_manager.tr("快速执行adb命令（如: adb devices, adb shell getprop）"))
        self.adb_input.setMinimumWidth(300)
        self.adb_input.setToolTip(
            self.lang_manager.tr("支持快速执行一次性ADB命令\n") +
            self.lang_manager.tr("例如: adb devices, adb shell pm list packages 等\n") +
            self.lang_manager.tr("不支持持续输出命令（logcat、top等），请使用对应功能")
        )
        self.adb_input.returnPressed.connect(self._on_adb_command_entered)
        adb_layout_h.addWidget(self.adb_input)
        
        # 发送按钮
        self.adb_send_btn = QPushButton(self.lang_manager.tr("发送"))
        self.adb_send_btn.clicked.connect(self._on_adb_command_entered)
        adb_layout_h.addWidget(self.adb_send_btn)
        
        layout.addWidget(adb_frame)
        
    def _on_adb_command_entered(self):
        """处理ADB命令输入"""
        command = self.adb_input.text().strip()
        if command:
            self.adb_command_executed.emit(command)
            self.adb_input.clear()
        
    def append_log(self, text, color=None):
        """追加日志"""
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # 设置文本格式
        if color:
            format = QTextCharFormat()
            format.setForeground(QColor(color))
            cursor.setCharFormat(format)
        else:
            cursor.setCharFormat(self.default_format)
        
        # 添加文本
        cursor.insertText(text)
        
        # 自动滚动到底部
        self.text_edit.setTextCursor(cursor)
        
    def append_log_with_highlight(self, text, keyword, color="#FF4444"):
        """追加日志并高亮关键字"""
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # 添加文本
        cursor.setCharFormat(self.default_format)
        cursor.insertText(text)
        
        # 高亮关键字
        if keyword:
            self.highlight_keyword_in_text(keyword, color)
        
        # 自动滚动到底部
        self.text_edit.setTextCursor(cursor)
        
    def highlight_keyword_in_text(self, keyword, color="#FF4444"):
        """高亮文本中的关键字"""
        format = QTextCharFormat()
        format.setForeground(QColor(color))
        
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # 查找并高亮所有匹配项
        text = self.text_edit.toPlainText()
        index = 0
        while True:
            index = text.find(keyword, index)
            if index == -1:
                break
            
            cursor.setPosition(index)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(keyword))
            cursor.setCharFormat(format)
            
            index += len(keyword)
            
        self.text_edit.setTextCursor(cursor)
    
    def on_return_pressed(self):
        """回车键处理"""
        keyword = self.search_edit.text()
        if not keyword:
            return
        
        # 如果已经有搜索结果且搜索关键字相同，跳转到下一个
        if (self.search_results and 
            self.search_keyword == keyword and 
            self.search_case_sensitive == self.case_check.isChecked()):
            self.find_next()
        else:
            # 否则执行新的搜索
            self.on_search()
        
    def on_search(self):
        """搜索"""
        keyword = self.search_edit.text()
        if not keyword:
            return
            
        self.search_keyword = keyword
        self.search_case_sensitive = self.case_check.isChecked()
        
        # 清除之前的搜索高亮
        self.clear_search_highlight()
        
        # 搜索所有匹配项的位置
        self.search_results = []
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.Start)
        self.text_edit.setTextCursor(cursor)
        
        flags = QTextDocument.FindFlags()
        if self.search_case_sensitive:
            flags |= QTextDocument.FindCaseSensitively
            
        while True:
            found = self.text_edit.find(keyword, flags)
            if not found:
                break
            # 获取当前光标位置（匹配开始的位置）
            cursor = self.text_edit.textCursor()
            self.search_results.append(cursor.position() - len(keyword))
            
        # 高亮第一个搜索结果
        if self.search_results:
            self.current_search_index = 0
            self.highlight_search_results()
            self.status_message.emit(f"{self.tr('找到 ')}{len(self.search_results)}{self.tr(' 个匹配项，当前第 1 个')}")
        else:
            self.status_message.emit(self.lang_manager.tr("未找到匹配项"))
            
    def clear_search_highlight(self):
        """清除搜索高亮"""
        cursor = self.text_edit.textCursor()
        cursor.select(QTextCursor.Document)
        cursor.setCharFormat(self.default_format)
        self.text_edit.setTextCursor(cursor)
        
    def highlight_search_results(self):
        """高亮搜索结果"""
        if not self.search_results:
            return
        
        # 清除之前的搜索高亮
        self.clear_search_highlight()
            
        # 只高亮当前匹配项
        if self.current_search_index >= 0 and self.current_search_index < len(self.search_results):
            cursor = self.text_edit.textCursor()
            
            # 设置光标到匹配位置
            cursor.setPosition(self.search_results[self.current_search_index])
            
            # 选中当前匹配的关键字
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(self.search_keyword))
            
            # 应用高亮格式
            cursor.mergeCharFormat(self.search_highlight_format)
            
            # 设置光标到匹配位置（不选中文本）
            cursor.setPosition(self.search_results[self.current_search_index])
            self.text_edit.setTextCursor(cursor)
            self.text_edit.ensureCursorVisible()
            
    def find_next(self):
        """查找下一个"""
        if not self.search_results:
            return
            
        self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
        self.highlight_search_results()
        self.status_message.emit(f"{self.tr('找到 ')}{len(self.search_results)}{self.tr(' 个匹配项，当前第 ')}{self.current_search_index + 1}{self.tr(' 个')}")
        
    def find_previous(self):
        """查找上一个"""
        if not self.search_results:
            return
            
        self.current_search_index = (self.current_search_index - 1) % len(self.search_results)
        self.highlight_search_results()
        self.status_message.emit(f"{self.tr('找到 ')}{len(self.search_results)}{self.tr(' 个匹配项，当前第 ')}{self.current_search_index + 1}{self.tr(' 个')}")
        
    def clear_logs(self):
        """清空日志"""
        self.text_edit.clear()
        self.search_results = []
        self.current_search_index = -1
    
    def show_all_results(self):
        """显示所有搜索结果"""
        keyword = self.search_edit.text()
        if not keyword:
            self.status_message.emit(self.lang_manager.tr("请输入搜索关键字"))
            return
        
        # 获取文本内容
        text_content = self.text_edit.toPlainText()
        
        if not text_content.strip():
            self.status_message.emit(self.lang_manager.tr("没有日志内容可搜索"))
            return
        
        # 搜索所有匹配的行
        lines = text_content.split('\n')
        matching_lines = []
        
        import re
        pattern = re.escape(keyword)
        flags_re = 0 if self.search_case_sensitive else re.IGNORECASE
        
        for i, line in enumerate(lines):
            if re.search(pattern, line, flags_re):
                matching_lines.append((i + 1, line))
        
        if not matching_lines:
            self.status_message.emit(self.lang_manager.tr("未找到匹配项"))
            return
        
        # 创建结果显示窗口
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QFrame
        from PyQt5.QtGui import QTextCharFormat, QColor
        from PyQt5.QtWidgets import QMessageBox
        
        results_window = QDialog(self)
        results_window.setWindowTitle(f"{self.tr('搜索结果 - 找到 ')}{len(matching_lines)}{self.tr(' 个匹配项')}")
        results_window.resize(1000, 600)
        
        # 主布局
        main_layout = QVBoxLayout(results_window)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 标题和统计信息
        title_layout = QHBoxLayout()
        
        title_label = QLabel(f"{self.lang_manager.tr('搜索关键字:')} {keyword}")
        title_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        title_layout.addWidget(title_label)
        
        count_label = QLabel(f"{self.lang_manager.tr('找到')} {len(matching_lines)} {self.lang_manager.tr('个匹配项')}")
        count_label.setStyleSheet("color: blue;")
        title_layout.addWidget(count_label)
        
        title_layout.addStretch()
        
        # 按钮
        select_all_btn = QPushButton(self.lang_manager.tr("全选"))
        title_layout.addWidget(select_all_btn)
        
        copy_btn = QPushButton(self.lang_manager.tr("复制"))
        title_layout.addWidget(copy_btn)
        
        close_btn = QPushButton(self.lang_manager.tr("关闭"))
        title_layout.addWidget(close_btn)
        
        main_layout.addLayout(title_layout)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        
        # 文本显示区域
        results_text = QTextEdit()
        results_text.setReadOnly(True)
        results_text.setFont(QFont("Cascadia Mono", 10))
        results_text.setStyleSheet("""
            QTextEdit {
                background-color: #0C0C0C;
                color: #FFFFFF;
                selection-background-color: #444444;
            }
        """)
        
        main_layout.addWidget(results_text)
        
        # 配置高亮格式
        highlight_format = QTextCharFormat()
        highlight_format.setForeground(QColor("#FF4444"))
        
        # 配置默认格式（白色字体）
        default_format = QTextCharFormat()
        default_format.setForeground(QColor("#FFFFFF"))
        
        # 填充搜索结果
        for line_num, line in matching_lines:
            # 添加行号
            cursor = results_text.textCursor()
            cursor.movePosition(cursor.End)
            cursor.setCharFormat(default_format)
            cursor.insertText(f"[{line_num:4d}] ")
            
            # 高亮关键字
            import re
            pattern = re.escape(keyword)
            flags_re = 0 if self.search_case_sensitive else re.IGNORECASE
            
            matches = list(re.finditer(pattern, line, flags_re))
            last_end = 0
            
            for match in matches:
                # 插入普通文本（使用默认格式）
                if match.start() > last_end:
                    cursor.setCharFormat(default_format)
                    cursor.insertText(line[last_end:match.start()])
                
                # 插入高亮文本
                cursor.insertText(match.group(), highlight_format)
                last_end = match.end()
            
            # 插入剩余文本（使用默认格式）
            if last_end < len(line):
                cursor.setCharFormat(default_format)
                cursor.insertText(line[last_end:])
            
            cursor.setCharFormat(default_format)
            cursor.insertText("\n")
        
        # 移动到顶部
        results_text.moveCursor(QTextCursor.Start)
        
        # 连接按钮事件
        def select_all():
            results_text.selectAll()
            results_text.setFocus()
        
        def copy_results():
            results_text.copy()
            QMessageBox.information(results_window, self.lang_manager.tr("成功"), "搜索结果已复制到剪贴板")
        
        def close_window():
            results_window.accept()
        
        select_all_btn.clicked.connect(select_all)
        copy_btn.clicked.connect(copy_results)
        close_btn.clicked.connect(close_window)
        
        # 显示窗口
        results_window.exec_()
        self.status_message.emit(f"{self.tr('显示 ')}{len(matching_lines)}{self.tr(' 个匹配项')}")
        
    # 信号定义（用于发送状态消息）
    status_message = pyqtSignal(str)

