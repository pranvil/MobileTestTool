"""
高级富文本编辑器组件
支持图片和表格插入、编辑，支持从剪贴板粘贴
参考chapter_editor的实现方式
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QMessageBox, QFileDialog, QDialog, QDialogButtonBox,
    QTabWidget, QListWidget, QListWidgetItem, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QColorDialog, QSpinBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor, QTextCharFormat, QFont, QColor
from PySide6.QtWidgets import QApplication
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid
import re
import tempfile
import shutil

# 复用chapter_editor中的对话框和编辑功能
from Jira_tool.ui.chapter_editor import TableInsertDialog, ImageInsertDialog


class RichTextEditor(QWidget):
    """高级富文本编辑器（参考chapter_editor的实现）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tables: List[Dict] = []  # 存储表格数据
        self.images: List[Dict] = []  # 存储图片数据
        self.image_files: List[str] = []  # 存储图片文件路径（用于上传）
        self.init_ui()
        self._load_from_content()  # 从现有内容加载表格和图片
    
    def init_ui(self):
        """初始化UI（参考chapter_editor）"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建选项卡
        self.tabs = QTabWidget()
        
        # 正文编辑选项卡
        content_tab = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 富文本工具栏（参考chapter_editor）
        toolbar = QHBoxLayout()
        toolbar.setSpacing(5)
        
        # 格式化按钮
        self.bold_btn = QPushButton("粗体")
        self.bold_btn.setCheckable(True)
        self.bold_btn.clicked.connect(self.toggle_bold)
        toolbar.addWidget(self.bold_btn)
        
        self.italic_btn = QPushButton("斜体")
        self.italic_btn.setCheckable(True)
        self.italic_btn.clicked.connect(self.toggle_italic)
        toolbar.addWidget(self.italic_btn)
        
        self.underline_btn = QPushButton("下划线")
        self.underline_btn.setCheckable(True)
        self.underline_btn.clicked.connect(self.toggle_underline)
        toolbar.addWidget(self.underline_btn)
        
        toolbar.addWidget(QLabel("|"))
        
        # 颜色按钮
        color_btn = QPushButton("颜色")
        color_btn.clicked.connect(self.choose_color)
        toolbar.addWidget(color_btn)
        
        toolbar.addStretch()
        
        # 插入按钮
        insert_table_btn = QPushButton("插入表格")
        insert_table_btn.clicked.connect(self.insert_table)
        toolbar.addWidget(insert_table_btn)
        
        insert_image_btn = QPushButton("插入图片")
        insert_image_btn.clicked.connect(self.insert_image)
        toolbar.addWidget(insert_image_btn)
        
        content_layout.addLayout(toolbar)
        
        # 内容输入框（扩大一倍）
        self.content_input = QTextEdit()
        self.content_input.setAcceptRichText(True)
        self.content_input.setPlaceholderText("请输入测试说明...\n\n提示：可以直接从剪贴板粘贴图片和表格（Ctrl+V）")
        self.content_input.setMinimumHeight(400)  # 扩大一倍（原来可能是200左右）
        self.content_input.textChanged.connect(self._on_content_changed)
        # 安装事件过滤器以拦截粘贴事件
        self.content_input.installEventFilter(self)
        content_layout.addWidget(self.content_input)
        
        content_tab.setLayout(content_layout)
        self.tabs.addTab(content_tab, "正文")
        
        # 编辑选项卡（表格和图片列表，参考chapter_editor）
        edit_tab = QWidget()
        edit_layout = QVBoxLayout()
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.setSpacing(6)

        # 用垂直分割器把“表格列表/图片列表”分成两个独立区域，避免互相挤压/覆盖
        from PySide6.QtWidgets import QSplitter
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        section_title_style = "font-weight: bold; font-size: 12px; padding: 4px 0px;"

        # --- 上半区：表格列表 ---
        tables_panel = QWidget()
        tables_panel_layout = QVBoxLayout()
        tables_panel_layout.setContentsMargins(0, 0, 0, 0)
        tables_panel_layout.setSpacing(6)

        tables_label = QLabel("表格列表")
        tables_label.setStyleSheet(section_title_style)
        tables_panel_layout.addWidget(tables_label)

        tables_row = QHBoxLayout()
        tables_row.setSpacing(10)
        self.tables_list = QListWidget()
        self.tables_list.itemDoubleClicked.connect(self.on_table_item_double_clicked)
        tables_row.addWidget(self.tables_list, stretch=1)

        tables_btn_col = QVBoxLayout()
        tables_btn_col.setSpacing(6)
        edit_table_btn = QPushButton("编辑")
        edit_table_btn.clicked.connect(self.on_edit_table_clicked)
        tables_btn_col.addWidget(edit_table_btn)
        delete_table_btn = QPushButton("删除")
        delete_table_btn.clicked.connect(self.on_delete_table_clicked)
        tables_btn_col.addWidget(delete_table_btn)
        tables_btn_col.addStretch()
        tables_row.addLayout(tables_btn_col)

        tables_panel_layout.addLayout(tables_row, stretch=1)
        tables_panel.setLayout(tables_panel_layout)

        # --- 下半区：图片列表 ---
        images_panel = QWidget()
        images_panel_layout = QVBoxLayout()
        images_panel_layout.setContentsMargins(0, 0, 0, 0)
        images_panel_layout.setSpacing(6)

        images_label = QLabel("图片列表")
        images_label.setStyleSheet(section_title_style)
        images_panel_layout.addWidget(images_label)

        images_row = QHBoxLayout()
        images_row.setSpacing(10)
        self.images_list = QListWidget()
        self.images_list.itemDoubleClicked.connect(self.on_image_item_double_clicked)
        images_row.addWidget(self.images_list, stretch=1)

        images_btn_col = QVBoxLayout()
        images_btn_col.setSpacing(6)
        edit_image_btn = QPushButton("编辑")
        edit_image_btn.clicked.connect(self.on_edit_image_clicked)
        images_btn_col.addWidget(edit_image_btn)
        delete_image_btn = QPushButton("删除")
        delete_image_btn.clicked.connect(self.on_delete_image_clicked)
        images_btn_col.addWidget(delete_image_btn)
        images_btn_col.addStretch()
        images_row.addLayout(images_btn_col)

        images_panel_layout.addLayout(images_row, stretch=1)
        images_panel.setLayout(images_panel_layout)

        splitter.addWidget(tables_panel)
        splitter.addWidget(images_panel)
        splitter.setSizes([1, 1])  # 初始均分

        edit_layout.addWidget(splitter)
        edit_tab.setLayout(edit_layout)
        self.tabs.addTab(edit_tab, "编辑")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)
    
    def toggle_bold(self):
        """切换粗体（参考chapter_editor）"""
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Bold if self.bold_btn.isChecked() else QFont.Weight.Normal)
        self._merge_format(fmt)
    
    def toggle_italic(self):
        """切换斜体（参考chapter_editor）"""
        fmt = QTextCharFormat()
        fmt.setFontItalic(self.italic_btn.isChecked())
        self._merge_format(fmt)
    
    def toggle_underline(self):
        """切换下划线（参考chapter_editor）"""
        fmt = QTextCharFormat()
        fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline if self.underline_btn.isChecked() else QTextCharFormat.UnderlineStyle.NoUnderline)
        self._merge_format(fmt)
    
    def _merge_format(self, fmt: QTextCharFormat):
        """合并格式（参考chapter_editor）"""
        cursor = self.content_input.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(fmt)
        self.content_input.mergeCurrentCharFormat(fmt)
    
    def choose_color(self):
        """选择颜色（参考chapter_editor）"""
        color = QColorDialog.getColor(QColor(0, 0, 0), self, "选择颜色")
        if color.isValid():
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            self._merge_format(fmt)
    
    def insert_table(self):
        """插入表格（参考chapter_editor）"""
        dialog = TableInsertDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            rows, cols, column_names = dialog.get_table_info()
            
            # 生成UUID
            table_id = str(uuid.uuid4())
            
            # 创建表格数据（参考chapter_editor）
            table_data = {
                "id": table_id,
                "headers": [{"text": name, "background_color": "#e3fcef"} for name in column_names],
                "rows": [[{"text": "", "rowspan": 1, "colspan": 1} for _ in range(cols)] for _ in range(rows)]
            }
            
            # 添加到列表
            self.tables.append(table_data)
            
            # 在光标位置插入表格占位符（参考chapter_editor）
            cursor = self.content_input.textCursor()
            table_text = f"\n[表格:table_{table_id}]\n"
            cursor.insertText(table_text)
            self.content_input.setTextCursor(cursor)
            
            # 刷新表格列表
            self.refresh_tables_list()
    
    def insert_image(self):
        """插入图片（参考chapter_editor）"""
        dialog = ImageInsertDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            image_info = dialog.get_image_info()
            if image_info["filepath"]:
                # 生成UUID
                image_id = str(uuid.uuid4())
                
                # 添加id到图片信息
                image_info["id"] = image_id
                
                # 将图片复制到临时目录
                file_path = image_info["filepath"]
                file_ext = Path(file_path).suffix
                unique_filename = f"image_{uuid.uuid4().hex[:8]}{file_ext}"
                temp_dir = Path(tempfile.gettempdir()) / "confluence_images"
                temp_dir.mkdir(exist_ok=True)
                temp_path = temp_dir / unique_filename
                shutil.copy2(file_path, temp_path)
                
                # 更新filename为唯一文件名
                image_info["filename"] = unique_filename
                image_info["temp_path"] = str(temp_path)
                
                # 添加到列表
                self.images.append(image_info)
                self.image_files.append(str(temp_path))
                
                # 在光标位置插入图片占位符（参考chapter_editor）
                cursor = self.content_input.textCursor()
                image_text = f"\n[图片:image_{image_id}]\n"
                cursor.insertText(image_text)
                self.content_input.setTextCursor(cursor)
                
            # 刷新图片列表
            self.refresh_images_list()
    
    def _escape_html(self, text: str) -> str:
        """转义HTML特殊字符"""
        return (
            text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;')
        )
    
    def paste_image_from_clipboard(self):
        """从剪贴板粘贴图片（修复粘贴功能）"""
        clipboard = QApplication.clipboard()
        image = clipboard.image()
        
        if image.isNull():
            # 如果没有图片，尝试从HTML中提取
            mime_data = clipboard.mimeData()
            if mime_data.hasHtml():
                html = mime_data.html()
                # 这里可以尝试从HTML中提取图片，但通常剪贴板的图片会直接提供image对象
                return
            QMessageBox.information(self, "提示", "剪贴板中没有图片")
            return
        
        # 保存图片到临时文件
        temp_dir = Path(tempfile.gettempdir()) / "confluence_images"
        temp_dir.mkdir(exist_ok=True)
        unique_filename = f"image_{uuid.uuid4().hex[:8]}.png"
        temp_path = temp_dir / unique_filename
        image.save(str(temp_path), "PNG")
        
        # 生成UUID
        image_id = str(uuid.uuid4())
        
        # 创建图片信息
        image_info = {
            "id": image_id,
            "filename": unique_filename,
            "filepath": str(temp_path),
            "temp_path": str(temp_path),
            "width": 600,
            "align": "center"
        }
        
        # 添加到列表
        self.images.append(image_info)
        self.image_files.append(str(temp_path))
        
        # 在光标位置插入图片占位符
        cursor = self.content_input.textCursor()
        image_text = f"\n[图片:image_{image_id}]\n"
        cursor.insertText(image_text)
        self.content_input.setTextCursor(cursor)
        
        # 刷新图片列表
        self.refresh_images_list()
    
    def eventFilter(self, obj, event):
        """事件过滤器，用于拦截粘贴事件（修复粘贴图片功能）"""
        if obj == self.content_input and event.type() == event.Type.KeyPress:
            if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_V:
                clipboard = QApplication.clipboard()
                mime_data = clipboard.mimeData()
                
                # 优先检查图片
                if mime_data.hasImage():
                    event.accept()  # 接受事件，阻止默认粘贴
                    self.paste_image_from_clipboard()
                    return True
                # 检查HTML内容（可能包含表格）
                elif mime_data.hasHtml():
                    html = mime_data.html()
                    # 如果包含表格，直接插入
                    if '<table' in html.lower():
                        event.accept()  # 接受事件，阻止默认粘贴
                        cursor = self.content_input.textCursor()
                        # 清理HTML（移除可能导致问题的标签）
                        cleaned_html = self._clean_pasted_html(html)
                        cursor.insertHtml(cleaned_html)
                        self.content_input.setTextCursor(cursor)
                        return True
        
        return super().eventFilter(obj, event)
    
    def _clean_pasted_html(self, html: str) -> str:
        """清理粘贴的HTML内容"""
        # 移除可能导致问题的标签
        html = re.sub(r'<!DOCTYPE[^>]*>', '', html, flags=re.IGNORECASE)
        html = re.sub(r'<\?xml[^>]*\?>', '', html, flags=re.IGNORECASE)
        html = re.sub(r'</?html[^>]*>', '', html, flags=re.IGNORECASE)
        html = re.sub(r'</?head[^>]*>', '', html, flags=re.IGNORECASE)
        html = re.sub(r'</?body[^>]*>', '', html, flags=re.IGNORECASE)
        html = re.sub(r'<meta[^>]*>', '', html, flags=re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.IGNORECASE | re.DOTALL)
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
        return html.strip()
    
    def refresh_tables_list(self):
        """刷新表格列表（参考chapter_editor）"""
        self.tables_list.clear()
        for i, table in enumerate(self.tables):
            headers = table.get("headers", [])
            header_texts = [h.get("text", "") if isinstance(h, dict) else str(h) for h in headers]
            header_str = ", ".join(header_texts) if header_texts else "无标题"
            item_text = f"表格 {i+1}: {header_str}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, i)  # 存储索引
            self.tables_list.addItem(item)
    
    def refresh_images_list(self):
        """刷新图片列表（参考chapter_editor）"""
        self.images_list.clear()
        for i, image in enumerate(self.images):
            filename = image.get("filename", "未命名")
            width = image.get("width", 600)
            align = image.get("align", "center")
            item_text = f"图片 {i+1}: {filename} ({width}px, 居中)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, i)  # 存储索引
            self.images_list.addItem(item)
    
    def on_table_item_double_clicked(self, item: QListWidgetItem):
        """表格项双击事件"""
        self.on_edit_table_clicked()
    
    def on_edit_table_clicked(self):
        """编辑选中的表格（参考chapter_editor）"""
        current_item = self.tables_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择一个表格")
            return
        
        index = current_item.data(Qt.ItemDataRole.UserRole)
        if 0 <= index < len(self.tables):
            self._edit_table_dialog(self.tables[index], index)
            self.refresh_tables_list()
    
    def on_delete_table_clicked(self):
        """删除选中的表格（参考chapter_editor）"""
        current_item = self.tables_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择一个表格")
            return
        
        index = current_item.data(Qt.ItemDataRole.UserRole)
        if 0 <= index < len(self.tables):
            table = self.tables[index]
            table_id = table.get("id")
            
            # 从内容中删除占位符
            if table_id:
                content = self.content_input.toPlainText()
                pattern = rf'\[表格:table_{re.escape(table_id)}\]'
                content = re.sub(pattern, '', content)
                self.content_input.setPlainText(content)
            
            # 从列表中删除
            self.tables.pop(index)
            self.refresh_tables_list()
            QMessageBox.information(self, "提示", "表格已删除")
    
    def on_image_item_double_clicked(self, item: QListWidgetItem):
        """图片项双击事件"""
        self.on_edit_image_clicked()
    
    def on_edit_image_clicked(self):
        """编辑选中的图片（参考chapter_editor）"""
        current_item = self.images_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择一张图片")
            return
        
        index = current_item.data(Qt.ItemDataRole.UserRole)
        if 0 <= index < len(self.images):
            self._edit_image_dialog(self.images[index], index)
            self.refresh_images_list()
    
    def on_delete_image_clicked(self):
        """删除选中的图片（参考chapter_editor）"""
        current_item = self.images_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择一张图片")
            return
        
        index = current_item.data(Qt.ItemDataRole.UserRole)
        if 0 <= index < len(self.images):
            image = self.images[index]
            image_id = image.get("id")
            
            # 从内容中删除占位符
            if image_id:
                content = self.content_input.toPlainText()
                pattern = rf'\[图片:image_{re.escape(image_id)}\]'
                content = re.sub(pattern, '', content)
                self.content_input.setPlainText(content)
            
            # 从图片文件列表中删除
            temp_path = image.get("temp_path")
            if temp_path and temp_path in self.image_files:
                self.image_files.remove(temp_path)
            
            # 从列表中删除
            self.images.pop(index)
            self.refresh_images_list()
            QMessageBox.information(self, "提示", "图片已删除")
    
    def _edit_table_dialog(self, table_data: Dict, index: int):
        """编辑表格对话框（复用chapter_editor的实现）"""
        # 导入chapter_editor的编辑表格对话框方法
        from Jira_tool.ui.chapter_editor import ChapterEditDialog
        # 创建一个临时章节数据来使用编辑功能
        temp_chapter = {"tables": [table_data], "images": []}
        temp_dialog = ChapterEditDialog(temp_chapter, self)
        # 这里需要直接调用chapter_editor的_edit_table_dialog方法
        # 但由于是私有方法，我们需要复制实现或创建一个公共接口
        # 为了简化，我们直接在这里实现编辑功能
        
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑表格")
        dialog.setMinimumWidth(800)
        dialog.setMinimumHeight(500)
        
        layout = QVBoxLayout()
        
        # 提示标签
        hint_label = QLabel("提示：第一行为标题行（绿色背景），可以编辑、合并和拆分")
        hint_label.setStyleSheet("color: #666; font-size: 12px; padding: 5px;")
        layout.addWidget(hint_label)
        
        # 工具栏
        toolbar = QHBoxLayout()
        merge_btn = QPushButton("合并单元格")
        split_btn = QPushButton("拆分单元格")
        toolbar.addWidget(merge_btn)
        toolbar.addWidget(split_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # 表格（参考chapter_editor的实现）
        table = QTableWidget()
        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])
        
        if headers:
            # 计算标题行的实际列数（考虑合并单元格的colspan）
            num_cols = sum(header.get("colspan", 1) if isinstance(header, dict) else 1 for header in headers)
            table.setColumnCount(num_cols)
            table.setRowCount(1 + len(rows))
            table.horizontalHeader().setVisible(False)
            table.verticalHeader().setVisible(False)
            
            # 加载标题行和数据行（参考chapter_editor的实现）
            # 这里简化实现，完整实现可以参考chapter_editor的_edit_table_dialog方法
            # 为了节省代码，我们使用一个简化版本
            self._load_table_to_widget(table, headers, rows)
        
        layout.addWidget(table)
        
        # 合并和拆分功能（参考chapter_editor）
        def merge_cells():
            selected_ranges = table.selectedRanges()
            if not selected_ranges:
                QMessageBox.warning(dialog, "提示", "请先选择要合并的单元格")
                return
            
            selection_range = selected_ranges[0]
            top_row = selection_range.topRow()
            bottom_row = selection_range.bottomRow()
            left_col = selection_range.leftColumn()
            right_col = selection_range.rightColumn()
            
            if top_row == bottom_row and left_col == right_col:
                QMessageBox.warning(dialog, "提示", "请选择多个单元格")
                return
            
            # 合并单元格
            rowspan = bottom_row - top_row + 1
            colspan = right_col - left_col + 1
            table.setSpan(top_row, left_col, rowspan, colspan)
            
            # 如果是标题行，保持标题样式
            if top_row == 0:
                first_item = table.item(top_row, left_col)
                if first_item:
                    first_item.setBackground(QColor("#e3fcef"))
                    first_item.setFont(QFont("", -1, QFont.Weight.Bold))
        
        def split_cell():
            selected_ranges = table.selectedRanges()
            if not selected_ranges:
                QMessageBox.warning(dialog, "提示", "请先选择要拆分的单元格")
                return
            
            selection_range = selected_ranges[0]
            row = selection_range.topRow()
            col = selection_range.leftColumn()
            
            if table.rowSpan(row, col) > 1 or table.columnSpan(row, col) > 1:
                table.setSpan(row, col, 1, 1)
            else:
                QMessageBox.warning(dialog, "提示", "选中的单元格不是合并单元格")
        
        merge_btn.clicked.connect(merge_cells)
        split_btn.clicked.connect(split_cell)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        
        def save_table():
            # 保存表格数据（参考chapter_editor的实现）
            max_rows = table.rowCount()
            max_cols = table.columnCount()
            
            if max_rows == 0 or max_cols == 0:
                return
            
            # 保存标题行
            processed_header = [False] * max_cols
            new_headers = []
            
            for j in range(max_cols):
                if processed_header[j]:
                    continue
                
                item = table.item(0, j)
                rowspan = table.rowSpan(0, j)
                colspan = table.columnSpan(0, j)
                
                for c in range(j, min(j + colspan, max_cols)):
                    processed_header[c] = True
                
                header_data = {
                    "text": item.text() if item else "",
                    "background_color": "#e3fcef",
                    "rowspan": rowspan,
                    "colspan": colspan
                }
                new_headers.append(header_data)
            
            # 保存数据行
            processed = [[False for _ in range(max_cols)] for _ in range(max_rows - 1)]
            new_rows = []
            
            for i in range(1, max_rows):
                row = []
                for j in range(max_cols):
                    if processed[i - 1][j]:
                        continue
                    
                    item = table.item(i, j)
                    rowspan = table.rowSpan(i, j)
                    colspan = table.columnSpan(i, j)
                    
                    for r in range(i, min(i + rowspan, max_rows)):
                        for c in range(j, min(j + colspan, max_cols)):
                            if r > 0:
                                processed[r - 1][c] = True
                    
                    cell_data = {
                        "text": item.text() if item else "",
                        "rowspan": rowspan,
                        "colspan": colspan
                    }
                    row.append(cell_data)
                
                new_rows.append(row)
            
            # 更新表格数据
            table_data["headers"] = new_headers
            table_data["rows"] = new_rows
            self.tables[index] = table_data
            
            dialog.accept()
        
        buttons.accepted.connect(save_table)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def _load_table_to_widget(self, table: QTableWidget, headers: List, rows: List):
        """加载表格数据到QTableWidget（简化版本）"""
        if not headers:
            return
        
        num_cols = sum(header.get("colspan", 1) if isinstance(header, dict) else 1 for header in headers)
        table.setColumnCount(num_cols)
        table.setRowCount(1 + len(rows))
        
        # 加载标题行
        col_idx = 0
        for header in headers:
            while col_idx < num_cols and table.item(0, col_idx) is not None:
                col_idx += 1
            if col_idx >= num_cols:
                break
            
            header_text = header.get("text", "") if isinstance(header, dict) else str(header)
            item = QTableWidgetItem(header_text)
            item.setBackground(QColor("#e3fcef"))
            item.setFont(QFont("", -1, QFont.Weight.Bold))
            table.setItem(0, col_idx, item)
            
            rowspan = header.get("rowspan", 1) if isinstance(header, dict) else 1
            colspan = header.get("colspan", 1) if isinstance(header, dict) else 1
            if rowspan > 1 or colspan > 1:
                table.setSpan(0, col_idx, rowspan, colspan)
            
            col_idx += colspan
        
        # 加载数据行
        for i, row in enumerate(rows):
            row_index = i + 1
            col_idx = 0
            for cell_data in row:
                while col_idx < num_cols and table.item(row_index, col_idx) is not None:
                    col_idx += 1
                if col_idx >= num_cols:
                    break
                
                if isinstance(cell_data, dict):
                    cell_text = cell_data.get("text", "")
                    rowspan = cell_data.get("rowspan", 1)
                    colspan = cell_data.get("colspan", 1)
                else:
                    cell_text = str(cell_data) if cell_data else ""
                    rowspan = 1
                    colspan = 1
                
                item = QTableWidgetItem(cell_text)
                table.setItem(row_index, col_idx, item)
                
                if rowspan > 1 or colspan > 1:
                    table.setSpan(row_index, col_idx, rowspan, colspan)
                
                col_idx += colspan
    
    def _edit_image_dialog(self, image_data: Dict, index: int):
        """编辑图片对话框（参考chapter_editor）"""
        dialog = ImageInsertDialog(self)
        
        # 加载现有数据
        if image_data.get("filepath"):
            dialog.image_path = image_data["filepath"]
            dialog.file_label.setText(Path(image_data["filepath"]).name)
            dialog.file_label.setStyleSheet("")
        
        if "width" in image_data:
            dialog.width_spin.setValue(image_data["width"])
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            image_info = dialog.get_image_info()
            if image_info["filepath"]:
                # 更新图片信息
                image_data.update(image_info)
                # 如果文件路径改变，更新临时文件
                if image_info["filepath"] != image_data.get("filepath"):
                    file_ext = Path(image_info["filepath"]).suffix
                    unique_filename = f"image_{uuid.uuid4().hex[:8]}{file_ext}"
                    temp_dir = Path(tempfile.gettempdir()) / "confluence_images"
                    temp_dir.mkdir(exist_ok=True)
                    temp_path = temp_dir / unique_filename
                    shutil.copy2(image_info["filepath"], temp_path)
                    image_data["filename"] = unique_filename
                    image_data["temp_path"] = str(temp_path)
                    # 更新图片文件列表
                    old_path = image_data.get("temp_path")
                    if old_path and old_path in self.image_files:
                        self.image_files.remove(old_path)
                    self.image_files.append(str(temp_path))
                self.images[index] = image_data
                self.refresh_images_list()
    
    def _load_from_content(self):
        """从现有内容中加载表格和图片（解析占位符）"""
        # 这个方法在设置内容后调用，用于从HTML中提取已存在的表格和图片
        # 由于我们使用占位符，这里暂时不需要实现
        # 如果需要支持编辑已有内容，可以在这里解析占位符
        pass
    
    def _on_content_changed(self):
        """内容改变时的处理"""
        # 可以在这里更新按钮状态等
        pass
    
    def set_content(self, content: str):
        """设置内容"""
        if content:
            self.content_input.setHtml(content)
            # 尝试从HTML中提取占位符，重建表格和图片列表
            self._parse_content_for_placeholders(content)
        else:
            self.content_input.clear()
            self.tables.clear()
            self.images.clear()
            self.image_files.clear()
            self.refresh_tables_list()
            self.refresh_images_list()
    
    def _parse_content_for_placeholders(self, content: str):
        """从HTML内容中解析占位符（用于加载已有内容）"""
        # 从纯文本中提取占位符
        plain_text = self.content_input.toPlainText()
        
        # 提取表格占位符
        table_pattern = r'\[表格:table_([a-f0-9\-]+)\]'
        for match in re.finditer(table_pattern, plain_text):
            table_id = match.group(1)
            # 检查是否已存在
            if not any(t.get("id") == table_id for t in self.tables):
                # 创建默认表格数据
                table_data = {
                    "id": table_id,
                    "headers": [{"text": "列1", "background_color": "#e3fcef"}],
                    "rows": [[{"text": "", "rowspan": 1, "colspan": 1}]]
                }
                self.tables.append(table_data)
        
        # 提取图片占位符
        image_pattern = r'\[图片:image_([a-f0-9\-]+)\]'
        for match in re.finditer(image_pattern, plain_text):
            image_id = match.group(1)
            # 检查是否已存在
            if not any(img.get("id") == image_id for img in self.images):
                # 创建默认图片数据
                image_data = {
                    "id": image_id,
                    "filename": "未命名",
                    "width": 600,
                    "align": "center"
                }
                self.images.append(image_data)
        
        self.refresh_tables_list()
        self.refresh_images_list()
    
    def get_content(self) -> str:
        """获取内容（HTML格式，将占位符替换为实际HTML）"""
        # 生成最终的HTML内容（将占位符替换为实际HTML）
        return self._generate_final_html()
    
    def get_image_files(self) -> List[str]:
        """获取图片文件列表"""
        return self.image_files.copy()
    
    def _generate_final_html(self) -> str:
        """生成最终的HTML内容（将占位符替换为实际HTML，保留原有格式）"""
        # 获取HTML内容（保留格式）
        html_content = self.content_input.toHtml()
        
        # 清理HTML（移除QTextEdit添加的额外标签，但保留用户的内容格式）
        html_content = self._clean_html_content(html_content)
        
        # 替换表格占位符（使用更安全的匹配方式）
        for table in self.tables:
            table_id = table.get("id")
            if table_id:
                placeholder = f'[表格:table_{table_id}]'
                table_html = self._generate_table_html(table)
                # 转义占位符用于HTML
                escaped_html_placeholder = self._escape_html(placeholder)
                # 转义占位符用于正则表达式（转义方括号）
                escaped_placeholder_re = placeholder.replace('[', '\\[').replace(']', '\\]')
                escaped_html_placeholder_re = escaped_html_placeholder.replace('[', '\\[').replace(']', '\\]')
                
                # 使用正则表达式匹配（更灵活，可以处理带属性的标签）
                # 匹配 <p> 或 <p ...> 标签中的占位符
                patterns = [
                    # 占位符在<p>标签中（可能带属性）
                    (rf'<p[^>]*>\s*{escaped_placeholder_re}\s*</p>', table_html),
                    (rf'<p[^>]*>\s*{escaped_placeholder_re}\s*<br\s*/?>\s*</p>', table_html),
                    (rf'<p[^>]*>\s*{escaped_html_placeholder_re}\s*</p>', table_html),
                    (rf'<p[^>]*>\s*{escaped_html_placeholder_re}\s*<br\s*/?>\s*</p>', table_html),
                    # 占位符单独存在（不在标签中）
                    (escaped_placeholder_re, table_html),
                    (escaped_html_placeholder_re, table_html),
                ]
                for pattern, replacement in patterns:
                    html_content = re.sub(pattern, replacement, html_content, flags=re.IGNORECASE)
        
        # 替换图片占位符
        for image in self.images:
            image_id = image.get("id")
            if image_id:
                placeholder = f'[图片:image_{image_id}]'
                filename = image.get("filename", "")
                width = image.get("width", 600)
                align = image.get("align", "center")
                image_html = f'<p><ac:image ac:align="{align}" ac:width="{width}"><ri:attachment ri:filename="{filename}" /></ac:image></p>'
                # 转义占位符
                escaped_html_placeholder = self._escape_html(placeholder)
                escaped_placeholder_re = placeholder.replace('[', '\\[').replace(']', '\\]')
                escaped_html_placeholder_re = escaped_html_placeholder.replace('[', '\\[').replace(']', '\\]')
                
                # 使用正则表达式匹配
                patterns = [
                    (rf'<p[^>]*>\s*{escaped_placeholder_re}\s*</p>', image_html),
                    (rf'<p[^>]*>\s*{escaped_placeholder_re}\s*<br\s*/?>\s*</p>', image_html),
                    (rf'<p[^>]*>\s*{escaped_html_placeholder_re}\s*</p>', image_html),
                    (rf'<p[^>]*>\s*{escaped_html_placeholder_re}\s*<br\s*/?>\s*</p>', image_html),
                    (escaped_placeholder_re, image_html),
                    (escaped_html_placeholder_re, image_html),
                ]
                for pattern, replacement in patterns:
                    html_content = re.sub(pattern, replacement, html_content, flags=re.IGNORECASE)
        
        return html_content
    
    def _clean_html_content(self, html: str) -> str:
        """清理HTML内容（移除QTextEdit添加的额外标签，保留用户格式）"""
        # 移除可能导致问题的标签
        html = re.sub(r'<!DOCTYPE[^>]*>', '', html, flags=re.IGNORECASE)
        html = re.sub(r'<\?xml[^>]*\?>', '', html, flags=re.IGNORECASE)
        html = re.sub(r'</?html[^>]*>', '', html, flags=re.IGNORECASE)
        html = re.sub(r'</?head[^>]*>', '', html, flags=re.IGNORECASE)
        html = re.sub(r'</?body[^>]*>', '', html, flags=re.IGNORECASE)
        html = re.sub(r'<meta[^>]*>', '', html, flags=re.IGNORECASE)
        
        # 移除style标签（但保留内联样式）
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.IGNORECASE | re.DOTALL)
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
        
        # 提取body标签内的内容（如果有）
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.IGNORECASE | re.DOTALL)
        if body_match:
            html = body_match.group(1)
        
        # 解码HTML实体（如果被转义了）
        # 从Word复制的内容可能包含被转义的HTML标签（如 &lt;br /&gt;）
        # 使用正则表达式匹配并解码所有被转义的HTML标签
        # 匹配模式：&lt;标签名[属性]> 或 &lt;/标签名>
        def decode_escaped_tags(text: str) -> str:
            """解码被转义的HTML标签"""
            # 匹配被转义的HTML标签：&lt;...&gt;
            def replace_tag(match):
                tag_content = match.group(1)
                # 解码：&lt; -> <, &gt; -> >
                decoded = tag_content.replace('&lt;', '<').replace('&gt;', '>')
                return decoded
            
            # 匹配 &lt;...&gt; 模式（包括自闭合标签）
            pattern = r'&lt;([^&]+)&gt;'
            result = re.sub(pattern, replace_tag, text)
            return result
        
        # 检查是否有被转义的HTML标签
        if '&lt;' in html and '&gt;' in html:
            html = decode_escaped_tags(html)
        
        return html.strip()
    
    def _generate_table_html(self, table_data: Dict) -> str:
        """生成表格HTML（使用local_templates的实现）"""
        from Jira_tool.modules.local_templates import _generate_table_html
        return _generate_table_html(table_data)
