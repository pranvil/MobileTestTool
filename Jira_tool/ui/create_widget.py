"""
创建Test Progress功能界面
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QCheckBox, QProgressBar,
    QTextEdit, QMessageBox, QFileDialog, QGroupBox, QScrollArea, QSizePolicy,
    QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from pathlib import Path
import pandas as pd
from Jira_tool.modules.test_progress_creator import (
    validate_file_structure, validate_rows, create_issues_from_excel
)
from core.debug_logger import logger
from Jira_tool.core.exceptions import ValidationError, FileError


class CreateIssuesThread(QThread):
    """创建Issue线程"""
    finished = Signal(dict)  # 结果字典
    progress = Signal(int)  # 进度百分比
    
    def __init__(self, excel_path: str, skip_errors: bool):
        super().__init__()
        self.excel_path = excel_path
        self.skip_errors = skip_errors
    
    def run(self):
        """执行创建"""
        try:
            result = create_issues_from_excel(self.excel_path, self.skip_errors)
            self.finished.emit(result)
        except Exception as e:
            logger.exception(f"创建Issue线程异常: {e}")
            self.finished.emit({
                'success': False,
                'error': str(e)
            })


class CreateWidget(QWidget):
    """创建Test Progress界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_excel_path = None
        self.df = None
        self.create_thread = None
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        # 整页需要可滚动：窗口尺寸不足时避免内容“溢出显示框”
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(10)
        
        # 标题
        title = QLabel("批量创建Test Progress")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # 顶部区域：把“选择文件 / 创建模板 / 创建选项”放到同一个 card 里
        top_card = QGroupBox("文件选择")
        top_row_layout = QHBoxLayout()
        top_row_layout.setSpacing(10)

        # 选择文件（左侧）
        self.file_label = QLabel("未选择文件")
        self.select_file_button = QPushButton("选择Excel文件")
        self.select_file_button.clicked.connect(self.select_file)
        top_row_layout.addWidget(self.file_label, 1)
        top_row_layout.addWidget(self.select_file_button)

        # 创建模板（中间）
        self.create_template_button = QPushButton("创建模板")
        self.create_template_button.setToolTip("生成Excel模板并打开")
        self.create_template_button.clicked.connect(self.create_template)
        top_row_layout.addWidget(self.create_template_button)

        # 创建选项（右侧）
        self.skip_errors_checkbox = QCheckBox("跳过错误行继续创建")
        self.skip_errors_checkbox.setChecked(True)
        top_row_layout.addWidget(self.skip_errors_checkbox)

        top_card.setLayout(top_row_layout)
        layout.addWidget(top_card)
        
        # 表格预览
        preview_group = QGroupBox("数据预览")
        preview_layout = QVBoxLayout()
        
        self.preview_table = QTableWidget()
        self.preview_table.setObjectName("jiraTestProgressPreviewTable")
        # 增大预览区默认高度，让数据预览更充裕
        self.preview_table.setMinimumHeight(260)
        self.preview_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.preview_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.preview_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.preview_table.setWordWrap(True)
        self.preview_table.setTextElideMode(Qt.TextElideMode.ElideRight)
        header = self.preview_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        preview_layout.addWidget(self.preview_table)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # 校验结果
        validation_group = QGroupBox("校验结果")
        validation_layout = QVBoxLayout()
        
        self.validation_text = QTextEdit()
        self.validation_text.setReadOnly(True)
        # 压缩校验结果显示区域（约一行高），需要时仍可滚动查看详情
        self.validation_text.setMinimumHeight(42)
        self.validation_text.setMaximumHeight(42)
        validation_layout.addWidget(self.validation_text)
        
        validation_group.setLayout(validation_layout)
        layout.addWidget(validation_group)
        
        # 按钮和进度条
        button_layout = QHBoxLayout()
        
        self.validate_button = QPushButton("校验文件")
        self.validate_button.clicked.connect(self.validate_file)
        self.validate_button.setEnabled(False)
        button_layout.addWidget(self.validate_button)
        
        self.create_button = QPushButton("开始创建")
        self.create_button.clicked.connect(self.start_create)
        self.create_button.setEnabled(False)
        button_layout.addWidget(self.create_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 结果显示
        result_group = QGroupBox("创建结果")
        result_layout = QVBoxLayout()
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(150)
        result_layout.addWidget(self.result_text)
        
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        layout.addStretch()

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)
        self.setLayout(outer_layout)
    
    def create_template(self):
        """创建Excel模板并打开"""
        default_name = "TestProgress_Template.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存Excel模板",
            default_name,
            "Excel Files (*.xlsx)"
        )

        if not file_path:
            return

        # 确保后缀
        if not file_path.lower().endswith(".xlsx"):
            file_path = file_path + ".xlsx"

        try:
            df = pd.DataFrame(columns=["Project", "Summary", "StartDate", "FinishDate", "Amount - Function"])
            df.to_excel(file_path, index=False)

            # 直接打开
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
            QMessageBox.information(self, "完成", f"模板已生成并打开：\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成模板失败：\n{str(e)}")

    def select_file(self):
        """选择Excel文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择Excel文件",
            "",
            "Excel Files (*.xlsx *.xls)"
        )
        
        if file_path:
            self.current_excel_path = file_path
            self.file_label.setText(Path(file_path).name)
            self.validate_button.setEnabled(True)
            self.create_button.setEnabled(False)
            self.preview_table.clear()
            self.validation_text.clear()
            self.result_text.clear()
            
            # 尝试读取并预览
            try:
                self.df = pd.read_excel(file_path)
                self.preview_data()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"读取Excel文件失败:\n{str(e)}")
    
    def preview_data(self):
        """预览数据"""
        if self.df is None:
            return
        
        # 显示前10行
        preview_df = self.df.head(10)
        
        self.preview_table.setRowCount(len(preview_df))
        self.preview_table.setColumnCount(len(preview_df.columns))
        self.preview_table.setHorizontalHeaderLabels(preview_df.columns.tolist())
        
        for i, row in preview_df.iterrows():
            for j, value in enumerate(row):
                item = QTableWidgetItem(str(value) if pd.notna(value) else "")
                # 鼠标悬停可看完整内容
                item.setToolTip(item.text())
                self.preview_table.setItem(i, j, item)

        # 尽量自适应列宽；超出时靠水平滚动条查看
        try:
            self.preview_table.resizeColumnsToContents()
        except Exception:
            pass
    
    def validate_file(self):
        """校验文件"""
        if self.df is None:
            QMessageBox.warning(self, "警告", "请先选择Excel文件")
            return
        
        self.validation_text.clear()
        
        # 文件级校验
        is_valid, missing_columns = validate_file_structure(self.df)
        
        if not is_valid:
            self.validation_text.append("❌ 文件级校验失败")
            self.validation_text.append(f"缺失列: {', '.join(missing_columns)}")
            self.create_button.setEnabled(False)
            return
        
        self.validation_text.append("✅ 文件级校验通过")
        
        # 行级校验
        errors = validate_rows(self.df)
        
        if errors:
            self.validation_text.append(f"\n⚠️ 行级校验发现 {len(errors)} 个错误:")
            for err in errors[:20]:  # 只显示前20个错误
                self.validation_text.append(
                    f"第{err['row_number']}行: {err['error_message']}"
                )
            if len(errors) > 20:
                self.validation_text.append(f"... 还有 {len(errors) - 20} 个错误")
        else:
            self.validation_text.append("✅ 行级校验通过，所有数据有效")
        
        # 如果校验通过或选择跳过错误，启用创建按钮
        if is_valid:
            self.create_button.setEnabled(True)
    
    def start_create(self):
        """开始创建"""
        if not self.current_excel_path:
            QMessageBox.warning(self, "警告", "请先选择Excel文件")
            return
        
        skip_errors = self.skip_errors_checkbox.isChecked()
        
        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认",
            f"确定要开始创建吗？\n"
            f"文件: {Path(self.current_excel_path).name}\n"
            f"总行数: {len(self.df)}\n"
            f"跳过错误行: {'是' if skip_errors else '否'}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 禁用按钮
        self.create_button.setEnabled(False)
        self.validate_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        self.result_text.clear()
        self.result_text.append("正在创建...")
        
        # 创建并启动线程
        self.create_thread = CreateIssuesThread(self.current_excel_path, skip_errors)
        self.create_thread.finished.connect(self.on_create_finished)
        self.create_thread.start()
    
    def on_create_finished(self, result: dict):
        """创建完成回调"""
        self.create_button.setEnabled(True)
        self.validate_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if result.get('success', False):
            total = result.get('total', 0)
            success_count = result.get('success_count', 0)
            fail_count = result.get('fail_count', 0)
            validation_errors = result.get('validation_errors', [])
            log_path = result.get('log_path', '')
            
            self.result_text.clear()
            self.result_text.append("✅ 创建完成！")
            self.result_text.append(f"总数: {total}")
            self.result_text.append(f"成功: {success_count}")
            self.result_text.append(f"失败: {fail_count}")
            
            if validation_errors:
                self.result_text.append(f"\n校验错误: {len(validation_errors)} 个")
            
            if log_path:
                self.result_text.append(f"\n日志文件: {log_path}")
            
            QMessageBox.information(
                self,
                "完成",
                f"创建完成！\n成功: {success_count}\n失败: {fail_count}"
            )
        else:
            error = result.get('error', '未知错误')
            self.result_text.clear()
            self.result_text.append(f"❌ 创建失败: {error}")
            QMessageBox.critical(self, "错误", f"创建失败:\n{error}")

