"""
Issue Export（Jira 导出 Excel + 常用 JQL 管理）
"""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QFileDialog,
    QAbstractItemView,
    QHeaderView,
    QInputDialog,
    QSplitter,
    QTextEdit,
)

from Jira_tool.jira_client import JiraClient
from Jira_tool.modules.jql_records import load_records, upsert_record, delete_record
from core.debug_logger import logger


class ExportXlsxThread(QThread):
    finished = Signal(bool, str, str)  # success, message, saved_path

    def __init__(self, jql: str, save_path: str):
        super().__init__()
        self.jql = jql
        self.save_path = save_path

    def run(self):
        try:
            client = JiraClient()
            data = client.download_issue_export_xlsx(self.jql)
            Path(self.save_path).write_bytes(data)
            self.finished.emit(True, "导出成功", self.save_path)
        except Exception as e:
            logger.exception(f"Issue Export 导出线程异常: {e}")
            self.finished.emit(False, f"导出失败: {str(e)}", "")


class IssueExportWidget(QWidget):
    """Issue Export 页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.export_thread: ExportXlsxThread | None = None
        self.init_ui()
        self.reload_table()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        title = QLabel("Issue Export")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 区域 A：操作区
        op_group = QGroupBox("操作区")
        op_layout = QVBoxLayout()
        op_layout.setSpacing(8)

        jql_label = QLabel("JQL:")
        op_layout.addWidget(jql_label)

        self.jql_input = QPlainTextEdit()
        self.jql_input.setObjectName("jiraIssueExportJqlInput")
        self.jql_input.setPlaceholderText("请输入 JQL 语句，例如：assignee = currentUser() AND status = Open")
        self.jql_input.setMinimumHeight(140)
        op_layout.addWidget(self.jql_input, 1)

        btn_row = QHBoxLayout()
        self.export_btn = QPushButton("导出 Excel")
        self.export_btn.clicked.connect(self.export_excel)
        btn_row.addWidget(self.export_btn)

        self.save_jql_btn = QPushButton("添加为常用 JQL")
        self.save_jql_btn.clicked.connect(self.save_current_jql)
        btn_row.addWidget(self.save_jql_btn)

        btn_row.addStretch()
        op_layout.addLayout(btn_row)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(70)
        op_layout.addWidget(self.status_text)

        op_group.setLayout(op_layout)
        splitter.addWidget(op_group)

        # 区域 B：已保存 JQL 列表
        list_group = QGroupBox("已保存 JQL 列表")
        list_layout = QVBoxLayout()
        list_layout.setSpacing(8)

        self.table = QTableWidget()
        self.table.setObjectName("jiraIssueExportTable")
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["名称 (Name)", "JQL 内容 (Content)"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.cellDoubleClicked.connect(lambda _r, _c: self.load_selected_jql())
        list_layout.addWidget(self.table, 1)

        list_btn_row = QHBoxLayout()
        self.load_btn = QPushButton("加载 JQL")
        self.load_btn.clicked.connect(self.load_selected_jql)
        list_btn_row.addWidget(self.load_btn)

        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self.delete_selected_record)
        list_btn_row.addWidget(self.delete_btn)

        list_btn_row.addStretch()
        list_layout.addLayout(list_btn_row)

        list_group.setLayout(list_layout)
        splitter.addWidget(list_group)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        self.setLayout(layout)

    def _set_busy(self, busy: bool):
        self.export_btn.setEnabled(not busy)
        self.save_jql_btn.setEnabled(not busy)
        self.load_btn.setEnabled(not busy)
        self.delete_btn.setEnabled(not busy)
        self.table.setEnabled(not busy)

    def _append_status(self, text: str):
        ts = time.strftime("%H:%M:%S")
        self.status_text.append(f"[{ts}] {text}")

    def reload_table(self):
        records = load_records()
        self.table.setRowCount(len(records))
        for row, r in enumerate(records):
            name_item = QTableWidgetItem(r.get("name", ""))
            jql_item = QTableWidgetItem(r.get("jql", ""))
            # tooltip 便于查看完整内容
            name_item.setToolTip(name_item.text())
            jql_item.setToolTip(jql_item.text())
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, jql_item)
        try:
            self.table.resizeRowsToContents()
        except Exception:
            pass

    def _selected_row(self) -> int:
        items = self.table.selectedItems()
        if not items:
            return -1
        return items[0].row()

    def _selected_record(self) -> tuple[str, str] | None:
        row = self._selected_row()
        if row < 0:
            return None
        name_item = self.table.item(row, 0)
        jql_item = self.table.item(row, 1)
        if not name_item or not jql_item:
            return None
        name = (name_item.text() or "").strip()
        jql = (jql_item.text() or "").strip()
        if not name or not jql:
            return None
        return name, jql

    def load_selected_jql(self):
        rec = self._selected_record()
        if not rec:
            QMessageBox.warning(self, "提示", "请先在列表中选择一条记录")
            return
        _name, jql = rec
        self.jql_input.setPlainText(jql)
        self._append_status("已加载选中的 JQL 到输入框")

    def delete_selected_record(self):
        rec = self._selected_record()
        if not rec:
            QMessageBox.warning(self, "提示", "请先在列表中选择一条记录")
            return
        name, _jql = rec
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除这条常用 JQL 吗？\n\n名称: {name}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        delete_record(name)
        self.reload_table()
        self._append_status(f"已删除常用 JQL：{name}")

    def save_current_jql(self):
        jql = (self.jql_input.toPlainText() or "").strip()
        if not jql:
            QMessageBox.warning(self, "提示", "JQL 不能为空")
            return

        name, ok = QInputDialog.getText(self, "保存常用 JQL", "请输入名称 (Name):")
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            QMessageBox.warning(self, "提示", "名称不能为空")
            return

        existing = {r.get("name"): r.get("jql") for r in load_records()}
        if name in existing:
            reply = QMessageBox.question(
                self,
                "确认覆盖",
                f"已存在同名记录：{name}\n\n是否覆盖？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        replaced, _records = upsert_record(name, jql)
        self.reload_table()
        self._append_status("已更新常用 JQL" if replaced else "已新增常用 JQL")

    def export_excel(self):
        jql = (self.jql_input.toPlainText() or "").strip()
        if not jql:
            QMessageBox.warning(self, "提示", "请先输入 JQL")
            return

        default_name = "Jira_Issue_Export.xlsx"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存导出的 Excel",
            default_name,
            "Excel Files (*.xlsx)",
        )
        if not save_path:
            return
        if not save_path.lower().endswith(".xlsx"):
            save_path += ".xlsx"

        self._set_busy(True)
        self._append_status("开始导出…")

        self.export_thread = ExportXlsxThread(jql=jql, save_path=save_path)
        self.export_thread.finished.connect(self.on_export_finished)
        self.export_thread.start()

    def on_export_finished(self, success: bool, message: str, saved_path: str):
        self._set_busy(False)
        if success:
            self._append_status(f"{message}: {saved_path}")
            QMessageBox.information(self, "完成", f"{message}！\n\n文件已保存到：\n{saved_path}")
        else:
            self._append_status(message)
            QMessageBox.critical(self, "错误", message)

