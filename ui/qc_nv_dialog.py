#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高通 NV 管理对话框
管理高通NV信息
"""

import os
import json
import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QLineEdit, QMessageBox, QFileDialog, QLabel,
                             QDialogButtonBox, QTextEdit, QGroupBox, QFormLayout,
                             QSplitter, QWidget)
from PyQt5.QtCore import Qt
from core.debug_logger import logger


class QCNVDialog(QDialog):
    """高通 NV 管理对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager.get_instance()
        
        self.setWindowTitle(self.tr("高通NV"))
        self.setModal(True)
        self.resize(1000, 700)
        
        # 数据存储
        self.nv_data = []  # 存储NV信息的列表 [{"nv_value": "...", "description": "..."}]
        self.config_file = self._get_config_file_path()
        self.backup_dir = self._get_backup_dir()
        
        self.setup_ui()
        self.load_data()
    
    def _get_config_file_path(self):
        """获取配置文件路径，兼容exe和开发环境"""
        # 统一保存到 ~/.netui/ 目录，与其他配置保持一致
        user_config_dir = os.path.expanduser('~/.netui')
        os.makedirs(user_config_dir, exist_ok=True)
        return os.path.join(user_config_dir, 'qc_nv.json')
    
    def _get_backup_dir(self):
        """获取备份文件目录"""
        # 备份文件保存到 ~/.netui/backups/ 目录
        backup_dir = os.path.join(os.path.expanduser('~/.netui'), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        return backup_dir
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 创建表格
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels([self.tr("NV值"), self.tr("说明")])
        
        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        
        # 双击事件
        self.table.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        layout.addWidget(self.table)
        
        # 底部按钮区域 - 分两行
        # 第一行：搜索框和搜索按钮
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel(self.tr("搜索:")))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("输入搜索关键字..."))
        self.search_input.returnPressed.connect(self.search_data)
        search_layout.addWidget(self.search_input)
        
        self.search_btn = QPushButton("🔍 " + self.tr("搜索"))
        self.search_btn.clicked.connect(self.search_data)
        search_layout.addWidget(self.search_btn)
        
        layout.addLayout(search_layout)
        
        # 第二行：新增、编辑、删除、导入、导出按钮
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ " + self.tr("新增"))
        self.add_btn.clicked.connect(self.add_nv)
        button_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("✏️ " + self.tr("编辑"))
        self.edit_btn.clicked.connect(self.edit_nv)
        button_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️ " + self.tr("删除"))
        self.delete_btn.clicked.connect(self.delete_nv)
        button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        
        self.import_btn = QPushButton("📥 " + self.tr("导入"))
        self.import_btn.clicked.connect(self.import_data)
        button_layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("📤 " + self.tr("导出"))
        self.export_btn.clicked.connect(self.export_data)
        button_layout.addWidget(self.export_btn)
        
        layout.addLayout(button_layout)
    
    def load_data(self):
        """加载数据"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.nv_data = data.get('nv_list', [])
                    logger.debug(f"加载高通NV数据: {len(self.nv_data)} 条记录")
            else:
                # 创建默认数据
                self.nv_data = []
                logger.debug("创建新的高通NV数据文件")
            
            self.refresh_table()
            
        except Exception as e:
            logger.exception(f"加载高通NV数据失败: {e}")
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('加载数据失败')}: {str(e)}")
    
    def save_data(self):
        """保存数据"""
        try:
            # 先备份现有文件
            if os.path.exists(self.config_file):
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = os.path.join(self.backup_dir, f"qc_nv_backup_{timestamp}.json")
                
                import shutil
                shutil.copy2(self.config_file, backup_file)
                logger.debug(f"备份文件到: {backup_file}")
            
            data = {
                'nv_list': self.nv_data,
                'version': '1.0',
                'update_time': datetime.datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"保存高通NV数据: {len(self.nv_data)} 条记录")
            
        except Exception as e:
            logger.exception(f"保存高通NV数据失败: {e}")
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('保存数据失败')}: {str(e)}")
    
    def refresh_table(self):
        """刷新表格"""
        self.table.setRowCount(0)
        for item in self.nv_data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(item.get('nv_value', '')))
            self.table.setItem(row, 1, QTableWidgetItem(item.get('description', '')))
    
    def add_nv(self):
        """新增NV"""
        dialog = NVEditDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            nv_value, description = dialog.get_data()
            if nv_value:
                self.nv_data.append({
                    'nv_value': nv_value,
                    'description': description
                })
                self.save_data()
                self.refresh_table()
                QMessageBox.information(self, self.tr("成功"), self.tr("新增成功！"))
    
    def edit_nv(self):
        """编辑NV"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择要编辑的项目"))
            return
        
        nv_value = self.table.item(current_row, 0).text()
        description = self.table.item(current_row, 1).text()
        
        dialog = NVEditDialog(nv_value=nv_value, description=description, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            new_nv_value, new_description = dialog.get_data()
            if new_nv_value:
                # 更新数据
                self.nv_data[current_row] = {
                    'nv_value': new_nv_value,
                    'description': new_description
                }
                self.save_data()
                self.refresh_table()
                QMessageBox.information(self, self.tr("成功"), self.tr("编辑成功！"))
    
    def delete_nv(self):
        """删除NV"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择要删除的项目"))
            return
        
        nv_value = self.table.item(current_row, 0).text()
        
        reply = QMessageBox.question(
            self, self.tr("确认删除"),
            f"{self.tr('确定要删除')} '{nv_value}' {self.tr('吗？')}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            del self.nv_data[current_row]
            self.save_data()
            self.refresh_table()
    
    def import_data(self):
        """导入数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("导入NV数据"), "",
            self.tr("JSON文件 (*.json);;所有文件 (*.*)")
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                imported_data = data.get('nv_list', [])
                if not imported_data:
                    QMessageBox.warning(self, self.tr("提示"), self.tr("导入的文件格式不正确或数据为空"))
                    return
                
                # 询问是否覆盖或追加
                reply = QMessageBox.question(
                    self, self.tr("导入方式"),
                    self.tr("请选择导入方式：\n是 = 追加到现有数据\n否 = 覆盖现有数据\n取消 = 取消操作"),
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                )
                
                if reply == QMessageBox.Yes:
                    # 追加
                    self.nv_data.extend(imported_data)
                elif reply == QMessageBox.No:
                    # 覆盖
                    self.nv_data = imported_data
                else:
                    return
                
                self.save_data()
                self.refresh_table()
                QMessageBox.information(self, self.tr("成功"), self.tr("导入成功！"))
                
            except Exception as e:
                logger.exception(f"导入NV数据失败: {e}")
                QMessageBox.critical(self, self.tr("错误"), f"{self.tr('导入失败')}: {str(e)}")
    
    def export_data(self):
        """导出数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.tr("导出NV数据"), "qc_nv_export.json",
            self.tr("JSON文件 (*.json);;所有文件 (*.*)")
        )
        
        if file_path:
            try:
                data = {
                    'nv_list': self.nv_data,
                    'version': '1.0',
                    'export_time': datetime.datetime.now().isoformat(),
                    'export_note': self.tr('高通NV数据导出')
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                QMessageBox.information(self, self.tr("导出成功"), f"{self.tr('数据已导出到')}\n{file_path}")
                
            except Exception as e:
                logger.exception(f"导出NV数据失败: {e}")
                QMessageBox.critical(self, self.tr("错误"), f"{self.tr('导出失败')}: {str(e)}")
    
    def search_data(self):
        """搜索数据"""
        keyword = self.search_input.text().strip().lower()
        
        if not keyword:
            self.refresh_table()
            return
        
        # 过滤数据
        filtered_data = []
        for item in self.nv_data:
            nv_value = item.get('nv_value', '').lower()
            description = item.get('description', '').lower()
            if keyword in nv_value or keyword in description:
                filtered_data.append(item)
        
        # 更新表格
        self.table.setRowCount(0)
        for item in filtered_data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(item.get('nv_value', '')))
            self.table.setItem(row, 1, QTableWidgetItem(item.get('description', '')))
    
    def on_item_double_clicked(self, item):
        """双击打开详细信息"""
        current_row = self.table.currentRow()
        if current_row < 0:
            return
        
        nv_value = self.table.item(current_row, 0).text()
        description = self.table.item(current_row, 1).text()
        
        # 显示详细信息的对话框
        detail_dialog = QDialog(self)
        detail_dialog.setWindowTitle(self.tr("NV详情"))
        detail_dialog.setModal(True)
        detail_dialog.resize(600, 400)
        
        layout = QVBoxLayout(detail_dialog)
        
        # NV值
        nv_label = QLabel(f"<b>{self.tr('NV值')}:</b>")
        layout.addWidget(nv_label)
        
        nv_text = QTextEdit()
        nv_text.setPlainText(nv_value)
        nv_text.setReadOnly(True)
        nv_text.setMaximumHeight(80)
        layout.addWidget(nv_text)
        
        # 说明
        desc_label = QLabel(f"<b>{self.tr('说明')}:</b>")
        layout.addWidget(desc_label)
        
        desc_text = QTextEdit()
        desc_text.setPlainText(description)
        desc_text.setReadOnly(True)
        layout.addWidget(desc_text)
        
        # 关闭按钮
        close_btn = QPushButton(self.tr("关闭"))
        close_btn.clicked.connect(detail_dialog.close)
        layout.addWidget(close_btn)
        
        detail_dialog.exec_()
    
    def closeEvent(self, event):
        """关闭事件"""
        self.save_data()
        super().closeEvent(event)


class NVEditDialog(QDialog):
    """NV编辑对话框"""
    
    def __init__(self, nv_value="", description="", parent=None):
        super().__init__(parent)
        
        # 获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager.get_instance()
        
        self.setWindowTitle(self.tr("编辑NV"))
        self.setModal(True)
        self.resize(500, 200)
        
        self.setup_ui()
        
        # 设置初始值
        self.nv_value_edit.setText(nv_value)
        self.description_edit.setPlainText(description)
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.nv_value_edit = QLineEdit()
        self.nv_value_edit.setPlaceholderText(self.tr("请输入NV值"))
        form_layout.addRow(self.tr("NV值*:"), self.nv_value_edit)
        
        layout.addLayout(form_layout)
        
        desc_label = QLabel(self.tr("说明:"))
        layout.addWidget(desc_label)
        
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText(self.tr("请输入说明（可选）..."))
        self.description_edit.setMaximumHeight(100)
        layout.addWidget(self.description_edit)
        
        layout.addStretch()
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def on_accept(self):
        """验证并接受"""
        nv_value = self.nv_value_edit.text().strip()
        
        if not nv_value:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请输入NV值"))
            return
        
        self.accept()
    
    def get_data(self):
        """获取数据"""
        return (self.nv_value_edit.text().strip(), 
                self.description_edit.toPlainText().strip())
