#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志查看器
"""

import os
import json
import re
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QLabel,
                             QHBoxLayout, QPushButton, QLineEdit, QCheckBox,
                             QSizePolicy, QFrame, QMenu)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor, QFont, QTextDocument, QKeyEvent, QAction


class FileDropLineEdit(QLineEdit):
    """支持拖拽文件路径和历史命令的输入框"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        # 历史命令相关属性
        self.command_history = []  # 命令历史列表
        self.history_index = -1  # 当前历史索引，-1表示不在历史浏览状态
        self.temp_command = ""  # 临时保存当前输入的命令（用于在浏览历史时保存未提交的命令）

    def set_command_history(self, history):
        """设置命令历史列表"""
        self.command_history = history if history else []
        self.history_index = -1

    def add_to_history(self, command):
        """添加命令到历史记录"""
        if not command or not command.strip():
            return
        
        command = command.strip()
        # 避免重复保存相同的连续命令
        if self.command_history and self.command_history[-1] == command:
            return
        
        self.command_history.append(command)
        # 限制历史记录数量（最多100条）
        if len(self.command_history) > 100:
            self.command_history.pop(0)
        self.history_index = -1

    def keyPressEvent(self, event: QKeyEvent):
        """处理键盘事件，实现历史命令导航"""
        if event.key() == Qt.Key_Up:
            # 上键：显示上一个历史命令
            if self.command_history:
                # 如果当前不在浏览历史状态，保存当前输入
                if self.history_index == -1:
                    self.temp_command = self.text()
                
                # 移动到上一个历史命令
                if self.history_index > 0:
                    self.history_index -= 1
                elif self.history_index == -1:
                    self.history_index = len(self.command_history) - 1
                
                # 显示历史命令
                if 0 <= self.history_index < len(self.command_history):
                    self.setText(self.command_history[self.history_index])
            event.accept()
            return
        elif event.key() == Qt.Key_Down:
            # 下键：显示下一个历史命令
            if self.command_history and self.history_index != -1:
                # 移动到下一个历史命令
                if self.history_index < len(self.command_history) - 1:
                    self.history_index += 1
                    self.setText(self.command_history[self.history_index])
                else:
                    # 已经到最新命令，恢复临时保存的命令
                    self.history_index = -1
                    self.setText(self.temp_command)
                    self.temp_command = ""
            event.accept()
            return
        
        # 其他按键正常处理
        super().keyPressEvent(event)
        # 如果用户开始输入新命令，重置历史索引
        if event.key() not in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right, 
                               Qt.Key_Home, Qt.Key_End, Qt.Key_Shift, Qt.Key_Control,
                               Qt.Key_Alt, Qt.Key_Meta):
            if self.history_index != -1:
                self.history_index = -1
                self.temp_command = ""

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                local_path = urls[0].toLocalFile()
                if local_path:
                    # Windows 控制台会自动为含空格的路径加引号，这里保持一致
                    if ' ' in local_path:
                        local_path = f'"{local_path}"'
                    self.insert(local_path)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class LogViewer(QWidget):
    """日志查看器控件"""
    
    # 信号定义
    search_requested = Signal(str, bool)  # keyword, case_sensitive
    adb_command_executed = Signal(str)  # 执行adb命令
    
    # 行首 adb 时间戳匹配：MM-DD HH:mm:ss.SSS
    _ADB_TS_RE = re.compile(r'^\s*\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3}\b')
    
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
        
        # ADB命令历史
        self.adb_command_history = []
        
        # 自动滚动状态（默认开启）
        self.auto_scroll_enabled = True
        
        # 加载历史命令
        self.load_command_history()
        
        self.setup_ui()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def _update_text_colors(self):
        """根据当前主题更新文本颜色"""
        # 获取当前主题
        theme = "dark"  # 默认暗色主题
        
        # 尝试从parent获取主题管理器
        # 注意：LogViewer的parent可能是QSplitter，需要向上查找MainWindow
        widget = self.parent()
        theme_manager = None
        
        # 向上查找MainWindow（最多查找5层）
        for _ in range(5):
            if widget is None:
                break
            if hasattr(widget, 'theme_manager'):
                theme_manager = widget.theme_manager
                break
            widget = widget.parent()
        
        if theme_manager:
            theme = theme_manager.get_current_theme()
        else:
            # 如果无法找到theme_manager，使用默认主题
            pass
        
        # 根据主题设置文本颜色
        if theme == "light":
            # 亮色主题：使用深色文本
            color = QColor("#000000")
            self.default_format.setForeground(color)
        else:
            # 暗色主题：使用浅色文本
            color = QColor("#ffffff")
            self.default_format.setForeground(color)
        
        # 重新格式化所有已存在的文本（除了高亮的部分）
        self._reformat_existing_text()
    
    def _reformat_existing_text(self):
        """重新格式化所有已存在的文本，应用新的默认颜色"""
        if not self.text_edit.document():
            return
        
        # 保存当前光标位置
        cursor = self.text_edit.textCursor()
        original_position = cursor.position()
        
        # 获取所有文本
        full_text = self.text_edit.toPlainText()
        if not full_text:
            return
        
        # 保存搜索高亮信息（如果有）
        search_keyword = self.search_keyword
        search_results = self.search_results.copy() if self.search_results else []
        current_search_index = self.current_search_index
        
        # 保存高亮关键字信息（用于过滤时的高亮）
        # 注意：这里我们无法完全恢复所有高亮，但至少可以恢复搜索高亮
        
        # 重新设置整个文档的格式
        cursor.select(QTextCursor.Document)
        cursor.setCharFormat(self.default_format)
        
        # 恢复搜索高亮（如果有）
        if search_keyword and search_results:
            self.search_keyword = search_keyword
            self.search_results = search_results
            self.current_search_index = current_search_index
            self.highlight_search_results()
        
        # 恢复光标位置
        new_position = min(original_position, len(full_text))
        cursor.setPosition(new_position)
        self.text_edit.setTextCursor(cursor)
        
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
        # 移除硬编码样式，使用主题样式
        # 设置对象名称以便在主题中识别
        self.text_edit.setObjectName("logViewerTextEdit")
        # 设置右键菜单
        self.text_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_edit.customContextMenuRequested.connect(self.show_context_menu)
        
        # 配置文本格式（根据主题动态调整）
        self.default_format = QTextCharFormat()
        self._update_text_colors()
        
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
        adb_frame.setObjectName("adbCommandFrame")
        # 移除硬编码样式，使用主题样式
        adb_layout_h = QHBoxLayout(adb_frame)
        adb_layout_h.setContentsMargins(5, 5, 5, 5)
        adb_layout_h.setSpacing(5)
        
        adb_label = QLabel(self.lang_manager.tr("ADB命令:"))
        adb_layout_h.addWidget(adb_label)
        
        self.adb_input = FileDropLineEdit()
        self.adb_input.setPlaceholderText(self.lang_manager.tr("快速执行adb命令（如: adb devices, adb shell getprop）"))
        self.adb_input.setMinimumWidth(300)
        self.adb_input.setToolTip(
            self.lang_manager.tr("支持快速执行一次性ADB命令\n") +
            self.lang_manager.tr("例如: adb devices, adb shell pm list packages 等\n") +
            self.lang_manager.tr("不支持持续输出命令（logcat、top等），请使用对应功能\n") +
            self.lang_manager.tr("提示: 使用上下键可以浏览历史命令")
        )
        # 设置命令历史
        self.adb_input.set_command_history(self.adb_command_history)
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
            # 添加到历史记录（避免重复保存相同的连续命令）
            if not self.adb_command_history or self.adb_command_history[-1] != command:
                self.adb_command_history.append(command)
                # 限制历史记录数量（最多100条）
                if len(self.adb_command_history) > 100:
                    self.adb_command_history.pop(0)
                # 同步到输入框的历史记录
                self.adb_input.set_command_history(self.adb_command_history)
                # 保存历史命令到文件
                self.save_command_history()
            else:
                # 即使命令相同，也要同步到输入框（确保索引正确）
                self.adb_input.set_command_history(self.adb_command_history)
            
            self.adb_command_executed.emit(command)
            self.adb_input.clear()
    
    def _get_config_file_path(self):
        """获取配置文件路径，兼容exe和开发环境"""
        # 统一保存到 ~/.netui/ 目录，与其他配置保持一致
        user_config_dir = os.path.expanduser('~/.netui')
        os.makedirs(user_config_dir, exist_ok=True)
        return os.path.join(user_config_dir, 'adb_command_history.json')
    
    def save_command_history(self):
        """保存ADB命令历史到文件"""
        file_path = self._get_config_file_path()
        try:
            data = {
                'command_history': self.adb_command_history,
                'version': '1.0'
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # 静默处理错误，不影响主功能
            from core.debug_logger import logger
            logger.exception(f"保存ADB命令历史失败: {e}")
    
    def load_command_history(self):
        """从文件加载ADB命令历史"""
        file_path = self._get_config_file_path()
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 兼容旧格式（直接是列表）和新格式（包含version字段）
                    if isinstance(data, list):
                        self.adb_command_history = data
                    elif isinstance(data, dict) and 'command_history' in data:
                        self.adb_command_history = data.get('command_history', [])
                    else:
                        self.adb_command_history = []
                    
                    # 限制历史记录数量（最多100条）
                    if len(self.adb_command_history) > 100:
                        self.adb_command_history = self.adb_command_history[-100:]
            except Exception as e:
                # 静默处理错误，不影响主功能
                from core.debug_logger import logger
                logger.exception(f"加载ADB命令历史失败: {e}")
                self.adb_command_history = []
        
    def append_log(self, text, color=None):
        """追加日志"""
        # 仅当行首没有 adb 时间戳时，为每一行添加本地时间戳（MM-DD HH:mm:ss.SSS）
        def _ensure_ts(src: str) -> str:
            lines = src.splitlines(keepends=True)
            output_parts = []
            for ln in lines:
                # 空白行保持原样
                if ln.strip() == "":
                    output_parts.append(ln)
                    continue
                if self._ADB_TS_RE.match(ln):
                    output_parts.append(ln)
                else:
                    ts = datetime.now().strftime('%m-%d %H:%M:%S.%f')[:-3]
                    output_parts.append(f"{ts} {ln}")
            return "".join(output_parts)
        
        text = _ensure_ts(text)
        
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # 设置文本格式
        if color:
            format = QTextCharFormat()
            format.setForeground(QColor(color))
            cursor.setCharFormat(format)
        else:
            cursor.setCharFormat(self.default_format)
        
        # 添加文本
        cursor.insertText(text)
        
        # 根据自动滚动状态决定是否滚动到底部
        if self.auto_scroll_enabled:
            self.text_edit.setTextCursor(cursor)
        
    def append_log_with_highlight(self, text, keyword, color="#FF4444"):
        """追加日志并高亮关键字"""
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # 添加文本
        cursor.setCharFormat(self.default_format)
        cursor.insertText(text)
        
        # 高亮关键字
        if keyword:
            self.highlight_keyword_in_text(keyword, color)
        
        # 根据自动滚动状态决定是否滚动到底部
        if self.auto_scroll_enabled:
            self.text_edit.setTextCursor(cursor)
        
    def highlight_keyword_in_text(self, keyword, color="#FF4444"):
        """高亮文本中的关键字"""
        format = QTextCharFormat()
        format.setForeground(QColor(color))
        
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
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
        cursor.movePosition(QTextCursor.MoveOperation.Start)
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
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QFrame
        from PySide6.QtGui import QTextCharFormat, QColor
        from PySide6.QtWidgets import QMessageBox
        
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
        # 移除硬编码样式，使用主题样式
        results_text.setObjectName("searchResultsTextEdit")
        
        main_layout.addWidget(results_text)
        
        # 配置高亮格式
        highlight_format = QTextCharFormat()
        highlight_format.setForeground(QColor("#FF4444"))
        
        # 配置默认格式（根据主题动态调整）
        default_format = QTextCharFormat()
        # 获取当前主题
        theme = "dark"  # 默认暗色主题
        if self.parent() and hasattr(self.parent(), 'theme_manager'):
            theme = self.parent().theme_manager.get_current_theme()
        
        # 根据主题设置文本颜色
        if theme == "light":
            default_format.setForeground(QColor("#000000"))  # 亮色主题：黑色文本
        else:
            default_format.setForeground(QColor("#FFFFFF"))  # 暗色主题：白色文本
        
        # 填充搜索结果
        for line_num, line in matching_lines:
            # 添加行号
            cursor = results_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
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
        results_text.moveCursor(QTextCursor.MoveOperation.Start)
        
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
        results_window.exec()
        self.status_message.emit(f"{self.tr('显示 ')}{len(matching_lines)}{self.tr(' 个匹配项')}")
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu(self.text_edit)
        
        # 添加QTextEdit的标准编辑动作（复制、全选等）
        # 由于text_edit是只读的，只有复制和全选可用
        copy_action = QAction(self.lang_manager.tr("复制"), self.text_edit)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.text_edit.copy)
        menu.addAction(copy_action)
        
        select_all_action = QAction(self.lang_manager.tr("全选"), self.text_edit)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.text_edit.selectAll)
        menu.addAction(select_all_action)
        
        # 添加分隔符
        menu.addSeparator()
        
        # 根据当前自动滚动状态显示不同的菜单文本
        if self.auto_scroll_enabled:
            action_text = self.lang_manager.tr("停止自动滚动")
        else:
            action_text = self.lang_manager.tr("自动滚动")
        
        auto_scroll_action = QAction(action_text, self.text_edit)
        auto_scroll_action.triggered.connect(self.toggle_auto_scroll)
        menu.addAction(auto_scroll_action)
        
        # 添加分隔符
        menu.addSeparator()
        
        # 清空日志
        clear_action = QAction(self.lang_manager.tr("清空日志"), self.text_edit)
        clear_action.triggered.connect(self.clear_logs)
        menu.addAction(clear_action)
        
        # 显示菜单
        menu.exec(self.text_edit.mapToGlobal(position))
    
    def toggle_auto_scroll(self):
        """切换自动滚动状态"""
        self.auto_scroll_enabled = not self.auto_scroll_enabled
        
        # 如果重新启用自动滚动，立即滚动到底部
        if self.auto_scroll_enabled:
            cursor = self.text_edit.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.text_edit.setTextCursor(cursor)
        
    # 信号定义（用于发送状态消息）
    status_message = Signal(str)

