"""
章节编辑器组件
支持动态添加、编辑多个章节和子章节
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QComboBox, QTreeWidget, QTreeWidgetItem,
    QGroupBox, QMessageBox, QDialog, QDialogButtonBox, QSpinBox,
    QFileDialog, QToolBar, QColorDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QListWidget, QListWidgetItem, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCharFormat, QTextCursor, QColor, QFont, QIcon
from typing import Dict, List, Any, Optional
from pathlib import Path
import uuid
import re
import tempfile


class TableInsertDialog(QDialog):
    """插入表格对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("插入表格")
        self.setMinimumWidth(400)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 行数
        rows_layout = QHBoxLayout()
        rows_layout.addWidget(QLabel("行数:"))
        self.rows_spin = QSpinBox()
        self.rows_spin.setMinimum(1)
        self.rows_spin.setMaximum(20)
        self.rows_spin.setValue(3)
        rows_layout.addWidget(self.rows_spin)
        rows_layout.addStretch()
        layout.addLayout(rows_layout)
        
        # 列数
        cols_layout = QHBoxLayout()
        cols_layout.addWidget(QLabel("列数:"))
        self.cols_spin = QSpinBox()
        self.cols_spin.setMinimum(1)
        self.cols_spin.setMaximum(10)
        self.cols_spin.setValue(3)
        self.cols_spin.valueChanged.connect(self.on_cols_changed)
        cols_layout.addWidget(self.cols_spin)
        cols_layout.addStretch()
        layout.addLayout(cols_layout)
        
        # 列名输入（逗号分隔）
        column_names_layout = QHBoxLayout()
        column_names_layout.addWidget(QLabel("列名（逗号分隔）:"))
        self.column_names_input = QLineEdit()
        self.column_names_input.setPlaceholderText("例如: 姓名,年龄,地址（可选，留空使用默认列名）")
        column_names_layout.addWidget(self.column_names_input)
        layout.addLayout(column_names_layout)
        
        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def on_cols_changed(self, value: int):
        """列数改变时的处理"""
        # 如果当前列名数量不匹配，清空列名输入
        column_names_text = self.column_names_input.text().strip()
        if column_names_text:
            names = [n.strip() for n in column_names_text.split(",") if n.strip()]
            if len(names) != value:
                # 列数不匹配，可以清空或保持（由用户决定）
                pass
    
    def validate_and_accept(self):
        """验证并接受"""
        column_names_text = self.column_names_input.text().strip()
        if column_names_text:
            names = [n.strip() for n in column_names_text.split(",") if n.strip()]
            cols = self.cols_spin.value()
            if len(names) != cols:
                QMessageBox.warning(self, "验证错误", f"列名数量（{len(names)}）必须等于列数（{cols}）")
                return
        self.accept()
    
    def get_table_info(self) -> tuple[int, int, List[str]]:
        """获取表格信息"""
        rows = self.rows_spin.value()
        cols = self.cols_spin.value()
        column_names_text = self.column_names_input.text().strip()
        
        if column_names_text:
            column_names = [name.strip() for name in column_names_text.split(",") if name.strip()]
            # 确保列名数量等于列数
            while len(column_names) < cols:
                column_names.append(f"列{len(column_names)+1}")
            column_names = column_names[:cols]
        else:
            column_names = [f"列{i+1}" for i in range(cols)]
        
        return rows, cols, column_names


class ImageInsertDialog(QDialog):
    """插入图片对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("插入图片")
        self.setMinimumWidth(400)
        self.image_path = ""
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 文件选择
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("图片文件:"))
        self.file_label = QLabel("未选择文件")
        self.file_label.setStyleSheet("color: gray;")
        file_layout.addWidget(self.file_label)
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)
        
        # 宽度
        width_layout = QHBoxLayout()
        width_layout.addWidget(QLabel("宽度(px):"))
        self.width_spin = QSpinBox()
        self.width_spin.setMinimum(100)
        self.width_spin.setMaximum(2000)
        self.width_spin.setValue(600)
        width_layout.addWidget(self.width_spin)
        width_layout.addStretch()
        layout.addLayout(width_layout)
        
        # 对齐方式（仅支持居中，避免左对齐导致的换行问题）
        align_layout = QHBoxLayout()
        align_layout.addWidget(QLabel("对齐方式:"))
        self.align_combo = QComboBox()
        self.align_combo.addItems(["居中"])  # 仅支持居中
        self.align_combo.setCurrentIndex(0)  # 默认居中
        self.align_combo.setEnabled(False)  # 禁用选择，固定为居中
        align_layout.addWidget(self.align_combo)
        align_layout.addStretch()
        layout.addLayout(align_layout)
        
        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def browse_file(self):
        """浏览文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        if file_path:
            self.image_path = file_path
            self.file_label.setText(Path(file_path).name)
            self.file_label.setStyleSheet("")
    
    def get_image_info(self) -> Dict:
        """获取图片信息"""
        align_map = {"左对齐": "left", "居中": "center", "右对齐": "right"}
        return {
            "filename": Path(self.image_path).name if self.image_path else "",
            "filepath": self.image_path,
            "width": self.width_spin.value(),
            "align": align_map.get(self.align_combo.currentText(), "center")
        }


class ChapterEditDialog(QDialog):
    """章节编辑对话框"""
    
    def __init__(self, chapter_data: Optional[Dict] = None, parent=None, parent_level: Optional[int] = None):
        super().__init__(parent)
        self.chapter_data = chapter_data or {}
        self.parent_level = parent_level  # 父章节的级别，None 表示顶级章节
        self.setWindowTitle("编辑章节" if chapter_data else "添加章节")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 标题
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("标题:"))
        self.title_input = QLineEdit()
        title_layout.addWidget(self.title_input)
        layout.addLayout(title_layout)
        
        # 级别
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("级别:"))
        self.level_combo = QComboBox()
        # 初始添加所有选项，后面会根据 parent_level 进行过滤
        self.level_combo.addItems(["H1 (一级标题)", "H2 (二级标题)", "H3 (三级标题)", "H4 (四级标题)", "H5 (五级标题)", "H6 (六级标题)"])
        level_layout.addWidget(self.level_combo)
        layout.addLayout(level_layout)
        
        # 创建选项卡
        self.tabs = QTabWidget()
        
        # 正文编辑选项卡
        content_tab = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 富文本工具栏
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
        self.color_btn = QPushButton("颜色")
        self.color_btn.clicked.connect(self.choose_color)
        toolbar.addWidget(self.color_btn)
        
        toolbar.addStretch()
        
        # 插入按钮
        insert_table_btn = QPushButton("插入表格")
        insert_table_btn.clicked.connect(self.insert_table)
        toolbar.addWidget(insert_table_btn)
        
        insert_image_btn = QPushButton("插入图片")
        insert_image_btn.clicked.connect(self.insert_image)
        toolbar.addWidget(insert_image_btn)
        
        # 全屏按钮
        self.fullscreen_btn = QPushButton("全屏")
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        toolbar.addWidget(self.fullscreen_btn)
        
        content_layout.addLayout(toolbar)
        
        # 内容输入框（扩大一倍）
        self.content_input = QTextEdit()
        self.content_input.setMinimumHeight(400)  # 扩大一倍（从200改为400）
        self.content_input.textChanged.connect(self.update_word_count)
        # 安装事件过滤器以支持粘贴图片和表格
        self.content_input.installEventFilter(self)
        content_layout.addWidget(self.content_input)
        
        # 字数统计
        self.word_count_label = QLabel("字数: 0")
        self.word_count_label.setStyleSheet("color: gray; font-size: 11px;")
        content_layout.addWidget(self.word_count_label)
        
        content_tab.setLayout(content_layout)
        self.tabs.addTab(content_tab, "正文")
        
        # 编辑选项卡（表格和图片列表）
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
        
        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def toggle_bold(self):
        """切换粗体"""
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Bold if self.bold_btn.isChecked() else QFont.Weight.Normal)
        self._merge_format(fmt)
    
    def toggle_italic(self):
        """切换斜体"""
        fmt = QTextCharFormat()
        fmt.setFontItalic(self.italic_btn.isChecked())
        self._merge_format(fmt)
    
    def toggle_underline(self):
        """切换下划线"""
        fmt = QTextCharFormat()
        fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline if self.underline_btn.isChecked() else QTextCharFormat.UnderlineStyle.NoUnderline)
        self._merge_format(fmt)
    
    def _merge_format(self, fmt: QTextCharFormat):
        """合并格式"""
        cursor = self.content_input.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(fmt)
        self.content_input.mergeCurrentCharFormat(fmt)
    
    def choose_color(self):
        """选择颜色"""
        color = QColorDialog.getColor(QColor(0, 0, 0), self, "选择颜色")
        if color.isValid():
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            self._merge_format(fmt)
    
    def toggle_fullscreen(self):
        """切换全屏模式"""
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_btn.setText("全屏")
        else:
            self.showFullScreen()
            self.fullscreen_btn.setText("退出全屏")
    
    def keyPressEvent(self, event):
        """处理键盘事件"""
        # ESC键退出全屏
        if event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.toggle_fullscreen()
        else:
            super().keyPressEvent(event)
    
    def insert_table(self):
        """插入表格到正文"""
        dialog = TableInsertDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            rows, cols, column_names = dialog.get_table_info()
            
            # 生成UUID
            table_id = str(uuid.uuid4())
            
            # 创建表格数据
            table_data = {
                "id": table_id,
                "headers": [{"text": name, "background_color": "#e3fcef"} for name in column_names],
                "rows": [[{"text": "", "rowspan": 1, "colspan": 1} for _ in range(cols)] for _ in range(rows)]
            }
            
            # 确保tables列表存在
            if "tables" not in self.chapter_data:
                self.chapter_data["tables"] = []
            self.chapter_data["tables"].append(table_data)
            
            # 在光标位置插入表格占位符
            cursor = self.content_input.textCursor()
            table_text = f"\n[表格:table_{table_id}]\n"
            cursor.insertText(table_text)
            self.content_input.setTextCursor(cursor)
            
            # 刷新表格列表
            self.refresh_tables_list()
    
    def insert_image(self):
        """插入图片到正文"""
        dialog = ImageInsertDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            image_info = dialog.get_image_info()
            if image_info["filename"]:
                # 生成UUID
                image_id = str(uuid.uuid4())
                
                # 添加id到图片信息
                image_info["id"] = image_id
                
                # 确保images列表存在
                if "images" not in self.chapter_data:
                    self.chapter_data["images"] = []
                self.chapter_data["images"].append(image_info)
                
                # 在光标位置插入图片占位符
                cursor = self.content_input.textCursor()
                image_text = f"\n[图片:image_{image_id}]\n"
                cursor.insertText(image_text)
                self.content_input.setTextCursor(cursor)
                
                # 刷新图片列表
                self.refresh_images_list()
    
    def paste_image_from_clipboard(self):
        """从剪贴板粘贴图片"""
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
        
        # 确保images列表存在
        if "images" not in self.chapter_data:
            self.chapter_data["images"] = []
        self.chapter_data["images"].append(image_info)
        
        # 在光标位置插入图片占位符
        cursor = self.content_input.textCursor()
        image_text = f"\n[图片:image_{image_id}]\n"
        cursor.insertText(image_text)
        self.content_input.setTextCursor(cursor)
        
        # 刷新图片列表
        self.refresh_images_list()
    
    def eventFilter(self, obj, event):
        """事件过滤器，用于拦截粘贴事件（支持粘贴图片和表格）"""
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
    
    def _edit_table_dialog(self, table_data: Dict, index: int):
        """编辑表格对话框（支持合并/拆分单元格，包括标题行）"""
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
        
        # 表格
        table = QTableWidget()
        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])
        
        if headers:
            # 计算标题行的实际列数（考虑合并单元格的colspan）
            num_cols = sum(header.get("colspan", 1) if isinstance(header, dict) else 1 for header in headers)
            table.setColumnCount(num_cols)
            
            # 将标题行作为第一行，数据行从第二行开始
            # 总行数 = 1（标题行）+ 数据行数
            table.setRowCount(1 + len(rows))
            
            # 隐藏默认的表头
            table.horizontalHeader().setVisible(False)
            table.verticalHeader().setVisible(False)
            
            # 加载标题行（作为第一行，row 0）
            # 将headers转换为与rows相同的格式，以便支持合并
            header_row = []
            for j, header in enumerate(headers):
                header_text = header.get("text", "") if isinstance(header, dict) else str(header)
                # 检查headers是否已经有rowspan/colspan信息
                if isinstance(header, dict):
                    rowspan = header.get("rowspan", 1)
                    colspan = header.get("colspan", 1)
                else:
                    rowspan = 1
                    colspan = 1
                header_row.append({
                    "text": header_text,
                    "rowspan": rowspan,
                    "colspan": colspan
                })
            
            # 处理标题行的合并单元格
            col_idx = 0
            for j, header_cell in enumerate(header_row):
                # 跳过被合并的列
                while col_idx < num_cols and table.item(0, col_idx) is not None:
                    col_idx += 1
                if col_idx >= num_cols:
                    break
                
                item = QTableWidgetItem(header_cell.get("text", ""))
                # 设置标题行样式（绿色背景，粗体）
                item.setBackground(QColor("#e3fcef"))
                item.setFont(QFont("", -1, QFont.Weight.Bold))
                table.setItem(0, col_idx, item)
                
                rowspan = header_cell.get("rowspan", 1)
                colspan = header_cell.get("colspan", 1)
                if rowspan > 1 or colspan > 1:
                    table.setSpan(0, col_idx, rowspan, colspan)
                
                col_idx += colspan
            
            # 加载数据行（从第二行开始，row 1）
            for i, row in enumerate(rows):
                row_index = i + 1  # 数据行从索引1开始
                col_idx = 0
                for cell_data in row:
                    # 跳过被合并的列
                    while col_idx < num_cols and table.item(row_index, col_idx) is not None:
                        col_idx += 1
                    if col_idx >= num_cols:
                        break
                    
                    # 支持新的单元格数据结构（字典，包含text、rowspan、colspan）
                    if isinstance(cell_data, dict):
                        cell_text = cell_data.get("text", "")
                        rowspan = cell_data.get("rowspan", 1)
                        colspan = cell_data.get("colspan", 1)
                    else:
                        # 兼容旧格式（纯文本）
                        cell_text = str(cell_data) if cell_data else ""
                        rowspan = 1
                        colspan = 1
                    
                    item = QTableWidgetItem(cell_text)
                    table.setItem(row_index, col_idx, item)
                    if rowspan > 1 or colspan > 1:
                        table.setSpan(row_index, col_idx, rowspan, colspan)
                    
                    col_idx += colspan
        
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        layout.addWidget(table)
        
        def merge_cells():
            """合并选中的单元格（包括标题行）"""
            selected_ranges = table.selectedRanges()
            if not selected_ranges:
                QMessageBox.warning(dialog, "提示", "请先选择要合并的单元格")
                return
            
            selection_range = selected_ranges[0]
            top_row = selection_range.topRow()
            left_col = selection_range.leftColumn()
            bottom_row = selection_range.bottomRow()
            right_col = selection_range.rightColumn()
            
            if top_row == bottom_row and left_col == right_col:
                QMessageBox.warning(dialog, "提示", "请选择多个单元格")
                return
            
            # 获取第一个单元格的内容和样式
            first_item = table.item(top_row, left_col)
            content = first_item.text() if first_item else ""
            is_header = (top_row == 0)  # 判断是否在标题行
            # 保存标题行的样式
            header_bg = first_item.background() if first_item else QColor("#e3fcef")
            header_font = first_item.font() if first_item else QFont("", -1, QFont.Weight.Bold)
            
            # 清空被合并的单元格
            for i in range(top_row, bottom_row + 1):
                for j in range(left_col, right_col + 1):
                    if i != top_row or j != left_col:
                        item = table.item(i, j)
                        if item:
                            item.setText("")
                            table.removeCellWidget(i, j)
            
            # 合并单元格
            rowspan = bottom_row - top_row + 1
            colspan = right_col - left_col + 1
            table.setSpan(top_row, left_col, rowspan, colspan)
            
            # 如果是标题行，保持标题样式
            if is_header and first_item:
                first_item.setBackground(QColor("#e3fcef"))
                first_item.setFont(QFont("", -1, QFont.Weight.Bold))
        
        def split_cell():
            """拆分选中的单元格"""
            selected_ranges = table.selectedRanges()
            if not selected_ranges:
                QMessageBox.warning(dialog, "提示", "请先选择要拆分的单元格")
                return
            
            selection_range = selected_ranges[0]
            row = selection_range.topRow()
            col = selection_range.leftColumn()
            
            # 检查是否是合并的单元格
            if table.rowSpan(row, col) > 1 or table.columnSpan(row, col) > 1:
                table.setSpan(row, col, 1, 1)
            else:
                QMessageBox.warning(dialog, "提示", "选中的单元格不是合并单元格")
        
        merge_btn.clicked.connect(merge_cells)
        split_btn.clicked.connect(split_cell)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 保存表格数据（包含合并单元格信息）
            # 第一行（row 0）是标题行，需要单独保存为headers
            # 从第二行（row 1）开始是数据行，保存为rows
            max_rows = table.rowCount()
            max_cols = table.columnCount()
            
            if max_rows == 0 or max_cols == 0:
                return
            
            # 保存标题行（第一行，row 0）
            # 计算标题行的实际列数（考虑合并）
            processed_header = [False] * max_cols
            new_headers = []
            actual_header_cols = 0  # 标题行的实际列数（用于验证数据行）
            
            for j in range(max_cols):
                if processed_header[j]:
                    continue
                
                item = table.item(0, j)
                rowspan = table.rowSpan(0, j)
                colspan = table.columnSpan(0, j)
                actual_header_cols += colspan  # 累加实际列数
                
                # 标记被合并的列
                for c in range(j, min(j + colspan, max_cols)):
                    processed_header[c] = True
                
                header_data = {
                    "text": item.text() if item else "",
                    "background_color": "#e3fcef",
                    "rowspan": rowspan,
                    "colspan": colspan
                }
                new_headers.append(header_data)
            
            # 保存数据行（从第二行开始，row 1及以后）
            processed = [[False for _ in range(max_cols)] for _ in range(max_rows - 1)]
            new_rows = []
            
            for i in range(1, max_rows):  # 从第2行开始（索引1）
                row = []
                for j in range(max_cols):
                    if processed[i - 1][j]:  # 注意索引偏移
                        continue  # 跳过被合并的单元格
                    
                    item = table.item(i, j)
                    rowspan = table.rowSpan(i, j)
                    colspan = table.columnSpan(i, j)
                    
                    # 标记被合并的单元格为已处理
                    for r in range(i, min(i + rowspan, max_rows)):
                        for c in range(j, min(j + colspan, max_cols)):
                            if r > 0:  # 只处理数据行
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
            self.chapter_data["tables"][index] = table_data
            self.refresh_tables_list()  # 刷新列表
    
    def _edit_image_dialog(self, image_data: Dict, index: int):
        """编辑图片对话框"""
        dialog = ImageInsertDialog(self)
        
        # 加载现有图片信息
        if image_data.get("filepath"):
            dialog.image_path = image_data["filepath"]
            dialog.file_label.setText(Path(image_data["filepath"]).name)
            dialog.file_label.setStyleSheet("")
        dialog.width_spin.setValue(image_data.get("width", 600))
        # 对齐方式固定为居中，不需要设置
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_info = dialog.get_image_info()
            new_info["id"] = image_data.get("id")  # 保留原有ID
            self.chapter_data["images"][index] = new_info
            self.refresh_images_list()  # 刷新列表
    
    def update_word_count(self):
        """更新字数统计"""
        text = self.content_input.toPlainText()
        char_count = len(text)
        word_count = len(text.split())
        self.word_count_label.setText(f"字数: {char_count} 字符, {word_count} 词")
    
    def setup_level_combo(self):
        """根据父章节级别设置可选的级别选项和默认值"""
        # 计算可选的级别范围
        if self.parent_level is None:
            # 顶级章节：推荐使用 H1 或 H2，默认 H2
            min_level = 1
            max_level = 6
            default_index = 1  # H2
        else:
            # 子章节：级别应该 >= 父章节级别（不允许降级）
            min_level = self.parent_level
            max_level = 6
            # 默认使用父级别+1，但如果父级别已经是6，则使用6
            default_level = min(self.parent_level + 1, 6)
            default_index = default_level - min_level
        
        # 清空并重新添加可选项
        self.level_combo.clear()
        level_names = ["H1 (一级标题)", "H2 (二级标题)", "H3 (三级标题)", "H4 (四级标题)", "H5 (五级标题)", "H6 (六级标题)"]
        for i in range(min_level - 1, max_level):
            self.level_combo.addItem(level_names[i])
        
        # 设置默认值（如果是编辑模式，使用原有级别；否则使用计算出的默认值）
        if self.chapter_data and "level" in self.chapter_data:
            # 编辑模式：使用原有级别
            original_level = self.chapter_data.get("level", 2)
            # 确保原有级别在可选范围内
            if min_level <= original_level <= max_level:
                combo_index = original_level - min_level
                self.level_combo.setCurrentIndex(combo_index)
            else:
                # 如果原有级别不在可选范围内，使用默认值
                self.level_combo.setCurrentIndex(default_index)
        else:
            # 新建模式：使用计算的默认值
            self.level_combo.setCurrentIndex(default_index)
    
    def load_data(self):
        """加载章节数据（包含数据兼容性处理）"""
        # 先设置级别下拉框（需要根据 parent_level 过滤选项）
        self.setup_level_combo()
        
        if self.chapter_data:
            self.title_input.setText(self.chapter_data.get("title", ""))
            # 加载富文本内容
            content = self.chapter_data.get("content", "")
            self.content_input.setPlainText(content)
            self.update_word_count()
            
            # 数据兼容性：为旧数据（没有ID的表格和图片）生成ID
            tables = self.chapter_data.get("tables", [])
            for table in tables:
                if "id" not in table:
                    table["id"] = str(uuid.uuid4())
                # 兼容旧格式的rows（纯文本列表）
                rows = table.get("rows", [])
                if rows and isinstance(rows[0], list) and len(rows[0]) > 0:
                    if isinstance(rows[0][0], str) or not isinstance(rows[0][0], dict):
                        # 旧格式：转换为新格式
                        new_rows = []
                        for row in rows:
                            new_row = []
                            for cell in row:
                                if isinstance(cell, dict):
                                    new_row.append(cell)
                                else:
                                    new_row.append({"text": str(cell) if cell else "", "rowspan": 1, "colspan": 1})
                            new_rows.append(new_row)
                        table["rows"] = new_rows
            
            images = self.chapter_data.get("images", [])
            for image in images:
                if "id" not in image:
                    image["id"] = str(uuid.uuid4())
            
            # 刷新列表显示
            self.refresh_tables_list()
            self.refresh_images_list()
    
    def refresh_tables_list(self):
        """刷新表格列表"""
        self.tables_list.clear()
        tables = self.chapter_data.get("tables", [])
        for i, table in enumerate(tables):
            headers = table.get("headers", [])
            header_texts = [h.get("text", "") if isinstance(h, dict) else str(h) for h in headers]
            header_str = ", ".join(header_texts) if header_texts else "无标题"
            item_text = f"表格 {i+1}: {header_str}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, i)  # 存储索引
            self.tables_list.addItem(item)
    
    def refresh_images_list(self):
        """刷新图片列表"""
        self.images_list.clear()
        images = self.chapter_data.get("images", [])
        for i, image in enumerate(images):
            filename = image.get("filename", "未命名")
            width = image.get("width", 600)
            align = image.get("align", "center")
            # 对齐方式固定为居中
            item_text = f"图片 {i+1}: {filename} ({width}px, 居中)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, i)  # 存储索引
            self.images_list.addItem(item)
    
    def on_table_item_double_clicked(self, item: QListWidgetItem):
        """表格项双击事件"""
        self.on_edit_table_clicked()
    
    def on_edit_table_clicked(self):
        """编辑选中的表格"""
        current_item = self.tables_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择一个表格")
            return
        
        index = current_item.data(Qt.ItemDataRole.UserRole)
        tables = self.chapter_data.get("tables", [])
        if 0 <= index < len(tables):
            self._edit_table_dialog(tables[index], index)
            self.refresh_tables_list()  # 刷新列表
    
    def on_delete_table_clicked(self):
        """删除选中的表格"""
        current_item = self.tables_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择一个表格")
            return
        
        index = current_item.data(Qt.ItemDataRole.UserRole)
        tables = self.chapter_data.get("tables", [])
        if 0 <= index < len(tables):
            table = tables[index]
            table_id = table.get("id")
            
            # 从内容中删除占位符
            if table_id:
                content = self.content_input.toPlainText()
                pattern = rf'\[表格:table_{re.escape(table_id)}\]'
                content = re.sub(pattern, '', content)
                self.content_input.setPlainText(content)
            
            # 从列表中删除
            tables.pop(index)
            self.refresh_tables_list()
            QMessageBox.information(self, "提示", "表格已删除")
    
    def on_image_item_double_clicked(self, item: QListWidgetItem):
        """图片项双击事件"""
        self.on_edit_image_clicked()
    
    def on_edit_image_clicked(self):
        """编辑选中的图片"""
        current_item = self.images_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择一张图片")
            return
        
        index = current_item.data(Qt.ItemDataRole.UserRole)
        images = self.chapter_data.get("images", [])
        if 0 <= index < len(images):
            self._edit_image_dialog(images[index], index)
            self.refresh_images_list()  # 刷新列表
    
    def on_delete_image_clicked(self):
        """删除选中的图片"""
        current_item = self.images_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择一张图片")
            return
        
        index = current_item.data(Qt.ItemDataRole.UserRole)
        images = self.chapter_data.get("images", [])
        if 0 <= index < len(images):
            image = images[index]
            image_id = image.get("id")
            
            # 从内容中删除占位符
            if image_id:
                content = self.content_input.toPlainText()
                pattern = rf'\[图片:image_{re.escape(image_id)}\]'
                content = re.sub(pattern, '', content)
                self.content_input.setPlainText(content)
            
            # 从列表中删除
            images.pop(index)
            self.refresh_images_list()
            QMessageBox.information(self, "提示", "图片已删除")
    
    def get_data(self) -> Dict:
        """获取章节数据"""
        # 获取选中的级别（需要考虑下拉框的偏移）
        selected_combo_index = self.level_combo.currentIndex()
        # 计算实际的级别：如果 parent_level 是 None，则从 H1 开始（索引0对应H1）
        # 如果 parent_level 不是 None，则从 parent_level 开始
        if self.parent_level is None:
            actual_level = selected_combo_index + 1
        else:
            # 找到第一个可用选项对应的级别
            min_level = self.parent_level
            actual_level = min_level + selected_combo_index
        
        # 验证级别（确保 >= parent_level）
        if self.parent_level is not None and actual_level < self.parent_level:
            # 这理论上不应该发生，因为下拉框已经过滤了，但为了安全起见还是验证一下
            actual_level = self.parent_level
        
        return {
            "title": self.title_input.text().strip(),
            "level": actual_level,
            "content": self.content_input.toPlainText().strip(),  # 保存为纯文本
            "sections": self.chapter_data.get("sections", []),
            "tables": self.chapter_data.get("tables", []),
            "images": self.chapter_data.get("images", [])
        }


class ChapterEditor(QWidget):
    """章节编辑器主组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chapters: List[Dict] = []
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 工具栏
        toolbar = QHBoxLayout()
        add_chapter_btn = QPushButton("添加章节")
        add_chapter_btn.clicked.connect(self.add_chapter)
        toolbar.addWidget(add_chapter_btn)
        add_sub_btn = QPushButton("添加子章节")
        add_sub_btn.clicked.connect(self.add_subchapter)
        toolbar.addWidget(add_sub_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # 章节树
        self.chapter_tree = QTreeWidget()
        self.chapter_tree.setHeaderLabel("章节列表")
        self.chapter_tree.setRootIsDecorated(True)
        self.chapter_tree.itemDoubleClicked.connect(self.edit_chapter)
        layout.addWidget(self.chapter_tree)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(self.edit_selected_chapter)
        delete_btn = QPushButton("删除")
        delete_btn.clicked.connect(self.delete_selected_chapter)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def add_chapter(self):
        """添加章节"""
        # 顶级章节，parent_level 为 None
        dialog = ChapterEditDialog(parent=self, parent_level=None)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            chapter_data = dialog.get_data()
            self.chapters.append(chapter_data)
            self.refresh_tree()
    
    def add_subchapter(self):
        """添加子章节"""
        current_item = self.chapter_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择一个章节")
            return
        
        # 找到对应的章节数据
        chapter_data = self._get_chapter_from_item(current_item)
        if chapter_data is None:
            return
        
        # 获取父章节的级别
        parent_level = chapter_data.get("level", 2)
        dialog = ChapterEditDialog(parent=self, parent_level=parent_level)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            subchapter_data = dialog.get_data()
            
            # 验证子章节级别（确保 >= 父章节级别）
            if subchapter_data.get("level", 1) < parent_level:
                QMessageBox.warning(self, "验证错误", f"子章节的级别不能小于父章节的级别（父章节: H{parent_level}）")
                return
            
            if "sections" not in chapter_data:
                chapter_data["sections"] = []
            chapter_data["sections"].append(subchapter_data)
            self.refresh_tree()
            # 重新查找对应的item并展开（因为refresh_tree会重建树，旧的item引用已无效）
            item = self._find_item_by_chapter(chapter_data)
            if item:
                item.setExpanded(True)
                self.chapter_tree.setCurrentItem(item)
    
    def edit_selected_chapter(self):
        """编辑选中的章节"""
        current_item = self.chapter_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择一个章节")
            return
        
        chapter_data = self._get_chapter_from_item(current_item)
        if chapter_data is None:
            return
        
        # 获取父章节的级别（如果有的话）
        parent_item = current_item.parent()
        parent_level = None
        if parent_item:
            # 如果有父节点，获取父章节数据
            parent_chapter = self._get_chapter_from_item(parent_item)
            if parent_chapter:
                parent_level = parent_chapter.get("level", 1)
        else:
            # 没有父节点，说明是顶级章节
            parent_level = None
        
        dialog = ChapterEditDialog(chapter_data, parent=self, parent_level=parent_level)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_data = dialog.get_data()
            
            # 验证级别（确保 >= 父章节级别）
            if parent_level is not None and new_data.get("level", 1) < parent_level:
                QMessageBox.warning(self, "验证错误", f"章节的级别不能小于父章节的级别（父章节: H{parent_level}）")
                return
            
            # 检查子章节：如果当前章节级别提升，需要验证所有子章节的级别
            old_level = chapter_data.get("level", 2)
            new_level = new_data.get("level", 2)
            if new_level > old_level:
                # 级别提升，检查子章节是否都 >= 新级别
                subchapters = chapter_data.get("sections", [])
                for subchapter in subchapters:
                    sub_level = subchapter.get("level", 1)
                    if sub_level < new_level:
                        QMessageBox.warning(
                            self, 
                            "验证错误", 
                            f"无法将级别提升到 H{new_level}，因为存在级别为 H{sub_level} 的子章节。\n"
                            f"请先修改或删除级别小于 H{new_level} 的子章节。"
                        )
                        return
            
            # 保留原有的子章节、表格、图片
            new_data["sections"] = chapter_data.get("sections", [])
            new_data["tables"] = chapter_data.get("tables", [])
            new_data["images"] = chapter_data.get("images", [])
            chapter_data.update(new_data)
            self.refresh_tree()
    
    def edit_chapter(self, item: QTreeWidgetItem, column: int):
        """双击编辑章节"""
        self.edit_selected_chapter()
    
    def delete_selected_chapter(self):
        """删除选中的章节"""
        current_item = self.chapter_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择一个章节")
            return
        
        reply = QMessageBox.question(
            self, "确认", "确定要删除这个章节吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 找到对应的章节数据并删除
        parent_item = current_item.parent()
        if parent_item:
            # 子章节
            parent_data = self._get_chapter_from_item(parent_item)
            if parent_data and "sections" in parent_data:
                index = parent_item.indexOfChild(current_item)
                if 0 <= index < len(parent_data["sections"]):
                    parent_data["sections"].pop(index)
        else:
            # 顶级章节
            index = self.chapter_tree.indexOfTopLevelItem(current_item)
            if 0 <= index < len(self.chapters):
                self.chapters.pop(index)
        
        self.refresh_tree()
    
    def _get_chapter_from_item(self, item: QTreeWidgetItem) -> Optional[Dict]:
        """从树项获取章节数据"""
        parent_item = item.parent()
        if parent_item:
            # 子章节
            parent_data = self._get_chapter_from_item(parent_item)
            if parent_data and "sections" in parent_data:
                index = parent_item.indexOfChild(item)
                if 0 <= index < len(parent_data["sections"]):
                    return parent_data["sections"][index]
        else:
            # 顶级章节
            index = self.chapter_tree.indexOfTopLevelItem(item)
            if 0 <= index < len(self.chapters):
                return self.chapters[index]
        return None
    
    def refresh_tree(self):
        """刷新章节树"""
        self.chapter_tree.clear()
        
        for chapter in self.chapters:
            item = self._create_tree_item(chapter)
            self.chapter_tree.addTopLevelItem(item)
            # 默认展开第一层级
            item.setExpanded(True)
            # 默认展开第二层级（子章节）
            for i in range(item.childCount()):
                child_item = item.child(i)
                child_item.setExpanded(True)
                # 默认展开第三层级（子章节的子章节）
                for j in range(child_item.childCount()):
                    grandchild_item = child_item.child(j)
                    grandchild_item.setExpanded(True)
    
    def _find_item_by_chapter(self, chapter_data: Dict) -> Optional[QTreeWidgetItem]:
        """根据章节数据查找对应的树项"""
        def search_item(parent_item: Optional[QTreeWidgetItem] = None) -> Optional[QTreeWidgetItem]:
            if parent_item is None:
                # 从顶层开始搜索
                for i in range(self.chapter_tree.topLevelItemCount()):
                    item = self.chapter_tree.topLevelItem(i)
                    item_data = item.data(0, Qt.ItemDataRole.UserRole)
                    if item_data is chapter_data:
                        return item
                    # 递归搜索子项
                    result = search_item(item)
                    if result:
                        return result
            else:
                # 搜索子项
                for i in range(parent_item.childCount()):
                    item = parent_item.child(i)
                    item_data = item.data(0, Qt.ItemDataRole.UserRole)
                    if item_data is chapter_data:
                        return item
                    # 递归搜索子项
                    result = search_item(item)
                    if result:
                        return result
            return None
        
        return search_item()
    
    def _create_tree_item(self, chapter: Dict) -> QTreeWidgetItem:
        """创建树项"""
        title = chapter.get("title", "未命名章节")
        level = chapter.get("level", 2)
        level_text = f"H{level}"
        item_text = f"{level_text}: {title}"
        
        item = QTreeWidgetItem([item_text])
        item.setData(0, Qt.ItemDataRole.UserRole, chapter)
        
        # 添加子章节
        for subchapter in chapter.get("sections", []):
            sub_item = self._create_tree_item(subchapter)
            item.addChild(sub_item)
        
        return item
    
    def get_chapters(self) -> List[Dict]:
        """获取所有章节数据"""
        return self.chapters
    
    def set_chapters(self, chapters: List[Dict]):
        """设置章节数据"""
        self.chapters = chapters
        self.refresh_tree()
