#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Log关键字配置对话框
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QLabel, QLineEdit, QTextEdit,
                             QFileDialog, QFormLayout, QWidget, QFrame)
from PySide6.QtCore import Qt
from core.debug_logger import logger
from ui.widgets.shadow_utils import add_card_shadow


class LogKeywordDialog(QDialog):
    """Log关键字管理对话框"""
    
    def __init__(self, keyword_manager, parent=None):
        super().__init__(parent)
        self.keyword_manager = keyword_manager
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.setWindowTitle(self.tr("Log关键字管理") if self.lang_manager else "Log关键字管理")
        self.setModal(True)
        self.resize(900, 600)
        
        self.setup_ui()
        self.load_keywords()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 顶部说明
        info_label = QLabel(
            self.tr("💡 在此配置log过滤关键字，可以使用正则表达式。支持导入/导出JSON配置文件。")
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #17a2b8; padding: 10px; background: #d1ecf1; border-radius: 4px;")
        layout.addWidget(info_label)
        
        # 关键字列表表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([self.tr('名称'), self.tr('关键字'), self.tr('描述')])
        
        # 设置列宽（允许手动调整）
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 150)  # 名称列初始宽度
        self.table.setColumnWidth(1, 200)  # 关键字列初始宽度
        self.table.setColumnWidth(2, 300)  # 描述列初始宽度
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self.on_double_click)
        layout.addWidget(self.table)
        
        # 底部按钮区
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ " + self.tr("添加"))
        self.add_btn.clicked.connect(self.add_keyword)
        button_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("✏️ " + self.tr("编辑"))
        self.edit_btn.clicked.connect(self.edit_keyword)
        button_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️ " + self.tr("删除"))
        self.delete_btn.clicked.connect(self.delete_keyword)
        button_layout.addWidget(self.delete_btn)
        
        self.load_btn = QPushButton("📋 " + self.tr("加载到过滤"))
        self.load_btn.clicked.connect(self.load_to_filter)
        button_layout.addWidget(self.load_btn)
        
        button_layout.addStretch()
        
        self.import_btn = QPushButton("📥 " + self.tr("导入"))
        self.import_btn.clicked.connect(self.import_keywords)
        button_layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("📤 " + self.tr("导出"))
        self.export_btn.clicked.connect(self.export_keywords)
        button_layout.addWidget(self.export_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("❌ " + self.tr("关闭"))
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def load_keywords(self):
        """加载关键字到表格"""
        self.table.setRowCount(0)
        keywords = self.keyword_manager.get_all_keywords()
        
        for kw in keywords:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(kw.get('name', '')))
            self.table.setItem(row, 1, QTableWidgetItem(kw.get('keyword', '')))
            self.table.setItem(row, 2, QTableWidgetItem(kw.get('description', '')))
            
            # 存储关键字ID
            self.table.item(row, 0).setData(Qt.UserRole, kw.get('id'))
    
    def on_double_click(self):
        """双击加载关键字并开始过滤"""
        self.load_to_filter()
    
    def add_keyword(self):
        """添加关键字"""
        dialog = KeywordEditDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            keyword_data = dialog.get_keyword_data()
            if self.keyword_manager.add_keyword(keyword_data):
                self.load_keywords()
                QMessageBox.information(self, self.tr("成功"), "关键字添加成功！")
            else:
                QMessageBox.warning(self, self.tr("失败"), "关键字添加失败，请检查日志")
    
    def edit_keyword(self):
        """编辑关键字"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, self.tr("提示"), "请先选择要编辑的关键字")
            return
        
        keyword_id = self.table.item(current_row, 0).data(Qt.UserRole)
        keyword_data = self.keyword_manager.get_keyword_by_id(keyword_id)
        
        if keyword_data:
            dialog = KeywordEditDialog(keyword_data=keyword_data, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                updated_data = dialog.get_keyword_data()
                if self.keyword_manager.update_keyword(keyword_id, updated_data):
                    self.load_keywords()
                    QMessageBox.information(self, self.tr("成功"), "关键字更新成功！")
                else:
                    QMessageBox.warning(self, self.tr("失败"), "关键字更新失败，请检查日志")
    
    def delete_keyword(self):
        """删除关键字"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, self.tr("提示"), "请先选择要删除的关键字")
            return
        
        keyword_name = self.table.item(current_row, 0).text()
        reply = QMessageBox.question(
            self, self.tr("确认删除"),
            f"{self.tr('确定要删除关键字')} '{keyword_name}' {self.tr('吗？')}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            keyword_id = self.table.item(current_row, 0).data(Qt.UserRole)
            if self.keyword_manager.delete_keyword(keyword_id):
                self.load_keywords()
                QMessageBox.information(self, self.tr("成功"), "关键字删除成功！")
            else:
                QMessageBox.warning(self, self.tr("失败"), "关键字删除失败，请检查日志")
    
    def load_to_filter(self):
        """加载选中的关键字到过滤框"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, self.tr("提示"), "请先选择要加载的关键字")
            return
        
        keyword_text = self.table.item(current_row, 1).text()
        # 返回选中的关键字
        self.selected_keyword = keyword_text
        self.accept()
    
    def import_keywords(self):
        """导入关键字配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("导入关键字配置"), "",
            self.tr("JSON文件 (*.json);;所有文件 (*.*)")
        )
        
        if file_path:
            if self.keyword_manager.import_keywords(file_path):
                self.load_keywords()
                QMessageBox.information(self, self.tr("成功"), "关键字配置导入成功！")
            else:
                QMessageBox.warning(self, self.tr("失败"), "关键字配置导入失败，请检查文件格式")
    
    def export_keywords(self):
        """导出关键字配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.tr("导出关键字配置"), "log_keywords.json",
            self.tr("JSON文件 (*.json);;所有文件 (*.*)")
        )
        
        if file_path:
            if self.keyword_manager.export_keywords(file_path):
                QMessageBox.information(self, self.tr("导出成功"), f"关键字配置导出成功！\n{file_path}")
            else:
                QMessageBox.warning(self, self.tr("导出失败"), "关键字配置导出失败，请检查日志")
    
    def get_selected_keyword(self):
        """获取选中的关键字"""
        return getattr(self, 'selected_keyword', None)


class KeywordEditDialog(QDialog):
    """关键字编辑对话框"""
    
    def __init__(self, keyword_data=None, parent=None):
        super().__init__(parent)
        self.keyword_data = keyword_data or {}
        self.is_edit = keyword_data is not None
        
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.setWindowTitle(self.tr("编辑关键字") if self.is_edit else "添加关键字")
        self.setModal(True)
        self.resize(600, 400)
        
        self.setup_ui()
        
        if self.is_edit:
            self.load_data()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 基本信息组（使用与Tab界面一致的样式：QLabel + QFrame）
        basic_container = QWidget()
        basic_container_layout = QVBoxLayout(basic_container)
        basic_container_layout.setContentsMargins(0, 0, 0, 0)
        basic_container_layout.setSpacing(4)
        
        basic_title = QLabel(self.tr("关键字信息"))
        basic_title.setProperty("class", "section-title")
        basic_container_layout.addWidget(basic_title)
        
        basic_card = QFrame()
        basic_card.setObjectName("card")
        add_card_shadow(basic_card)
        basic_layout = QFormLayout(basic_card)
        basic_layout.setContentsMargins(10, 1, 10, 1)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(self.tr("例如：错误日志"))
        basic_layout.addRow(self.tr("名称*:"), self.name_edit)
        
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText(self.tr("例如：Error|Exception|FATAL"))
        basic_layout.addRow(self.tr("关键字*:"), self.keyword_edit)
        
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText(self.tr("描述关键字的用途..."))
        self.description_edit.setMaximumHeight(100)
        basic_layout.addRow(self.tr("描述:"), self.description_edit)
        
        basic_container_layout.addWidget(basic_card)
        layout.addWidget(basic_container)
        
        # 提示信息
        tip_label = QLabel(
            self.tr("提示：\n") +
            self.tr("• 可以使用正则表达式，例如：Error|Exception 表示匹配Error或Exception\n") +
            self.tr("• 使用 | 分隔多个关键字表示或关系\n") +
            self.tr("• 使用 .* 表示任意字符\n") +
            self.tr("• 更多正则表达式语法请参考Python正则表达式文档")
        )
        tip_label.setWordWrap(True)
        tip_label.setStyleSheet(
            "color: #856404; padding: 10px; background: #fff3cd; "
            "border: 1px solid #ffeeba; border-radius: 4px; margin: 10px 0;"
        )
        layout.addWidget(tip_label)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_btn = QPushButton(self.tr("保存"))
        self.save_btn.clicked.connect(self.save)
        button_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton(self.tr("取消"))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def load_data(self):
        """加载关键字数据"""
        self.name_edit.setText(self.keyword_data.get('name', ''))
        self.keyword_edit.setText(self.keyword_data.get('keyword', ''))
        self.description_edit.setPlainText(self.keyword_data.get('description', ''))
    
    def save(self):
        """保存关键字"""
        name = self.name_edit.text().strip()
        keyword = self.keyword_edit.text().strip()
        
        if not name:
            QMessageBox.warning(self, self.tr("验证失败"), "请输入关键字名称")
            return
        
        if not keyword:
            QMessageBox.warning(self, self.tr("验证失败"), "请输入关键字内容")
            return
        
        self.accept()
    
    def get_keyword_data(self):
        """获取关键字数据"""
        return {
            'name': self.name_edit.text().strip(),
            'keyword': self.keyword_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip()
        }

