#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支持拖拽排序的表格组件
"""

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractItemView


class DragDropButtonTable(QTableWidget):
    """支持拖拽排序的按钮表格"""

    rows_reordered = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragDropOverwriteMode(False)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def dragEnterEvent(self, event):
        if event.source() == self:
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.source() == self:
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.source() != self:
            super().dropEvent(event)
            return

        source_row = self.currentRow()
        if source_row < 0:
            event.ignore()
            return

        target_index = self.indexAt(event.pos())
        if target_index.isValid():
            target_row = target_index.row()
            indicator = self.dropIndicatorPosition()
            if indicator == QAbstractItemView.BelowItem:
                target_row += 1
        else:
            target_row = self.rowCount()

        # 调整目标行，考虑源行删除后的偏移
        if target_row > source_row:
            target_row -= 1

        if target_row == source_row or target_row < 0:
            event.ignore()
            return

        if target_row > self.rowCount():
            target_row = self.rowCount()

        # 复制源行数据
        row_items = []
        for col in range(self.columnCount()):
            item = self.item(source_row, col)
            row_items.append(item.clone() if item else QTableWidgetItem())

        self.removeRow(source_row)

        if target_row < 0:
            target_row = 0

        self.insertRow(target_row)
        for col, item in enumerate(row_items):
            self.setItem(target_row, col, item)

        self.selectRow(target_row)
        self.resizeRowsToContents()
        event.acceptProposedAction()

        ordered_ids = []
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item:
                ordered_ids.append(item.data(Qt.UserRole))

        if ordered_ids:
            self.rows_reordered.emit(ordered_ids)

