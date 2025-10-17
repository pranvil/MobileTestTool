#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义按钮配置对话框
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QLabel, QLineEdit, QComboBox,
                             QTextEdit, QCheckBox, QFileDialog, QGroupBox,
                             QFormLayout)
from PyQt5.QtCore import Qt
from core.debug_logger import logger


class CustomButtonDialog(QDialog):
    """自定义按钮管理对话框"""
    
    def __init__(self, button_manager, parent=None):
        super().__init__(parent)
        self.button_manager = button_manager
        self.setWindowTitle("自定义按钮管理")
        self.setModal(True)
        self.resize(900, 600)
        
        self.setup_ui()
        self.load_buttons()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 顶部说明
        info_label = QLabel(
            "💡 在此配置自定义ADB命令按钮，按钮将显示在指定的Tab和卡片中。"
            "命令会自动加上 'adb -s {device}' 前缀。"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #17a2b8; padding: 10px; background: #d1ecf1; border-radius: 4px;")
        layout.addWidget(info_label)
        
        # 按钮列表表格
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['名称', '命令', '所在Tab', '所在卡片', '启用', '描述'])
        
        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)
        
        # 底部按钮区
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ 添加")
        self.add_btn.clicked.connect(self.add_button)
        button_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("✏️ 编辑")
        self.edit_btn.clicked.connect(self.edit_button)
        button_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️ 删除")
        self.delete_btn.clicked.connect(self.delete_button)
        button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        
        self.import_btn = QPushButton("📥 导入")
        self.import_btn.clicked.connect(self.import_buttons)
        button_layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("📤 导出")
        self.export_btn.clicked.connect(self.export_buttons)
        button_layout.addWidget(self.export_btn)
        
        # 移除重复的备份/恢复按钮，只保留导入/导出
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def load_buttons(self):
        """加载按钮到表格"""
        self.table.setRowCount(0)
        buttons = self.button_manager.get_all_buttons()
        
        for btn in buttons:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(btn.get('name', '')))
            self.table.setItem(row, 1, QTableWidgetItem(btn.get('command', '')))
            self.table.setItem(row, 2, QTableWidgetItem(btn.get('tab', '')))
            self.table.setItem(row, 3, QTableWidgetItem(btn.get('card', '')))
            self.table.setItem(row, 4, QTableWidgetItem('✓' if btn.get('enabled', True) else '✗'))
            self.table.setItem(row, 5, QTableWidgetItem(btn.get('description', '')))
            
            # 存储按钮ID
            self.table.item(row, 0).setData(Qt.UserRole, btn.get('id'))
    
    def add_button(self):
        """添加按钮"""
        dialog = ButtonEditDialog(self.button_manager, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            button_data = dialog.get_button_data()
            if self.button_manager.add_button(button_data):
                self.load_buttons()
                QMessageBox.information(self, "成功", "按钮添加成功！")
            else:
                QMessageBox.warning(self, "失败", "按钮添加失败，请检查日志")
    
    def edit_button(self):
        """编辑按钮"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择要编辑的按钮")
            return
        
        button_id = self.table.item(current_row, 0).data(Qt.UserRole)
        buttons = self.button_manager.get_all_buttons()
        button_data = next((btn for btn in buttons if btn['id'] == button_id), None)
        
        if button_data:
            dialog = ButtonEditDialog(self.button_manager, button_data=button_data, parent=self)
            if dialog.exec_() == QDialog.Accepted:
                updated_data = dialog.get_button_data()
                if self.button_manager.update_button(button_id, updated_data):
                    self.load_buttons()
                    QMessageBox.information(self, "成功", "按钮更新成功！")
                else:
                    QMessageBox.warning(self, "失败", "按钮更新失败，请检查日志")
    
    def delete_button(self):
        """删除按钮"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择要删除的按钮")
            return
        
        button_name = self.table.item(current_row, 0).text()
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除按钮 '{button_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            button_id = self.table.item(current_row, 0).data(Qt.UserRole)
            if self.button_manager.delete_button(button_id):
                self.load_buttons()
                QMessageBox.information(self, "成功", "按钮删除成功！")
            else:
                QMessageBox.warning(self, "失败", "按钮删除失败，请检查日志")
    
    def import_buttons(self):
        """导入按钮配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入按钮配置", "",
            "JSON文件 (*.json);;所有文件 (*.*)"
        )
        
        if file_path:
            if self.button_manager.import_buttons(file_path):
                self.load_buttons()
                QMessageBox.information(self, "成功", "按钮配置导入成功！")
            else:
                QMessageBox.warning(self, "失败", "按钮配置导入失败，请检查文件格式")
    
    def export_buttons(self):
        """导出按钮配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出按钮配置", "custom_buttons.json",
            "JSON文件 (*.json);;所有文件 (*.*)"
        )
        
        if file_path:
            if self.button_manager.export_buttons(file_path):
                QMessageBox.information(self, "导出成功", f"按钮配置导出成功！\n{file_path}")
            else:
                QMessageBox.warning(self, "导出失败", "按钮配置导出失败，请检查日志")
    


class ButtonEditDialog(QDialog):
    """按钮编辑对话框"""
    
    def __init__(self, button_manager, button_data=None, parent=None):
        super().__init__(parent)
        self.button_manager = button_manager
        self.button_data = button_data or {}
        self.is_edit = button_data is not None
        
        self.setWindowTitle("编辑按钮" if self.is_edit else "添加按钮")
        self.setModal(True)
        self.resize(600, 500)
        
        self.setup_ui()
        
        if self.is_edit:
            self.load_data()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 基本信息组
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout(basic_group)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：重启ADB")
        basic_layout.addRow("按钮名称*:", self.name_edit)
        
        self.command_edit = QLineEdit()
        self.command_edit.setPlaceholderText("例如：shell reboot（不需要加 'adb -s {device}'）")
        basic_layout.addRow("ADB命令*:", self.command_edit)
        
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("描述按钮的功能...")
        self.description_edit.setMaximumHeight(80)
        basic_layout.addRow("描述:", self.description_edit)
        
        layout.addWidget(basic_group)
        
        # 位置设置组
        position_group = QGroupBox("显示位置")
        position_layout = QFormLayout(position_group)
        
        self.tab_combo = QComboBox()
        self.tab_combo.addItems(self.button_manager.get_available_tabs())
        self.tab_combo.currentTextChanged.connect(self.on_tab_changed)
        position_layout.addRow("所在Tab*:", self.tab_combo)
        
        self.card_combo = QComboBox()
        position_layout.addRow("所在卡片*:", self.card_combo)
        
        self.enabled_check = QCheckBox("启用此按钮")
        self.enabled_check.setChecked(True)
        position_layout.addRow("", self.enabled_check)
        
        layout.addWidget(position_group)
        
        # 命令预览
        preview_group = QGroupBox("命令预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_label = QLabel()
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet(
            "background: #f8f9fa; padding: 10px; "
            "border: 1px solid #dee2e6; border-radius: 4px; "
            "font-family: 'Consolas', 'Monaco', monospace;"
        )
        preview_layout.addWidget(self.preview_label)
        
        self.command_edit.textChanged.connect(self.update_preview)
        
        layout.addWidget(preview_group)
        
        # 初始化Card列表
        self.on_tab_changed(self.tab_combo.currentText())
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save)
        button_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 初始预览
        self.update_preview()
    
    def on_tab_changed(self, tab_name):
        """Tab改变时更新Card列表"""
        self.card_combo.clear()
        cards = self.button_manager.get_available_cards(tab_name)
        self.card_combo.addItems(cards)
    
    def update_preview(self):
        """更新命令预览"""
        command = self.command_edit.text().strip()
        if command:
            # 处理命令格式：如果用户输入了"adb"开头，需要去掉
            clean_command = command
            if clean_command.lower().startswith('adb '):
                clean_command = clean_command[4:].strip()
            
            preview = f"adb -s {{设备ID}} {clean_command}"
            self.preview_label.setText(preview)
            
            # 检查命令是否被阻止
            if not self.button_manager.validate_command(command):
                reason = self.button_manager.get_blocked_reason(command)
                if reason:
                    self.preview_label.setStyleSheet(
                        "background: #f8d7da; padding: 10px; "
                        "border: 1px solid #f5c6cb; border-radius: 4px; "
                        "color: #721c24; font-family: 'Consolas', 'Monaco', monospace;"
                    )
                    self.preview_label.setText(f"⚠️ 不支持的命令\n{reason}")
                else:
                    self.preview_label.setStyleSheet(
                        "background: #f8d7da; padding: 10px; "
                        "border: 1px solid #f5c6cb; border-radius: 4px; "
                        "color: #721c24; font-family: 'Consolas', 'Monaco', monospace;"
                    )
                    self.preview_label.setText(f"⚠️ 命令验证失败")
            else:
                self.preview_label.setStyleSheet(
                    "background: #f8f9fa; padding: 10px; "
                    "border: 1px solid #dee2e6; border-radius: 4px; "
                    "font-family: 'Consolas', 'Monaco', monospace;"
                )
        else:
            self.preview_label.setText("请输入ADB命令...")
    
    def load_data(self):
        """加载按钮数据"""
        self.name_edit.setText(self.button_data.get('name', ''))
        self.command_edit.setText(self.button_data.get('command', ''))
        self.description_edit.setPlainText(self.button_data.get('description', ''))
        
        tab = self.button_data.get('tab', '')
        if tab:
            index = self.tab_combo.findText(tab)
            if index >= 0:
                self.tab_combo.setCurrentIndex(index)
        
        card = self.button_data.get('card', '')
        if card:
            index = self.card_combo.findText(card)
            if index >= 0:
                self.card_combo.setCurrentIndex(index)
        
        self.enabled_check.setChecked(self.button_data.get('enabled', True))
    
    def save(self):
        """保存按钮"""
        name = self.name_edit.text().strip()
        command = self.command_edit.text().strip()
        
        if not name:
            QMessageBox.warning(self, "验证失败", "请输入按钮名称")
            return
        
        if not command:
            QMessageBox.warning(self, "验证失败", "请输入ADB命令")
            return
        
        if not self.button_manager.validate_command(command):
            reason = self.button_manager.get_blocked_reason(command)
            QMessageBox.warning(
                self, "验证失败",
                f"命令验证失败\n{reason if reason else '请检查命令是否正确'}"
            )
            return
        
        self.accept()
    
    def get_button_data(self):
        """获取按钮数据"""
        return {
            'name': self.name_edit.text().strip(),
            'command': self.command_edit.text().strip(),
            'tab': self.tab_combo.currentText(),
            'card': self.card_combo.currentText(),
            'enabled': self.enabled_check.isChecked(),
            'description': self.description_edit.toPlainText().strip()
        }

