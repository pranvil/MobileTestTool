#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
暗码管理对话框
管理设备暗码（secret codes）的存储、编辑、删除、导入、导出和搜索
"""

import os
import json
import sys
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QLineEdit, QMessageBox, QFileDialog, QSplitter,
                             QWidget, QLabel, QGroupBox, QMenu)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QTimer
from core.debug_logger import logger


class SecretCodeDialog(QDialog):
    """暗码管理对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager.get_instance()
        
        self.setWindowTitle(self.tr("暗码管理"))
        self.setModal(True)
        self.resize(900, 600)
        
        # 数据存储
        self.secret_codes = {}
        self.categories = []  # 存储分类列表
        self.current_category = None
        self.config_file = self._get_config_file_path()
        
        # 控件引用
        self.category_table = None
        self.code_table = None
        self.search_input = None
        
        self.setup_ui()
        self.load_data()
    
    def _get_config_file_path(self):
        """获取配置文件路径，兼容exe和开发环境"""
        # 统一保存到 ~/.netui/ 目录，与其他配置保持一致
        user_config_dir = os.path.expanduser('~/.netui')
        os.makedirs(user_config_dir, exist_ok=True)
        return os.path.join(user_config_dir, 'secret_codes.json')
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # 左侧：分类列表
        left_widget = self.create_category_widget()
        splitter.addWidget(left_widget)
        
        # 右侧：暗码列表
        right_widget = self.create_code_widget()
        splitter.addWidget(right_widget)
        
        # 设置分割器比例
        splitter.setSizes([200, 700])
        
        # 底部按钮（导出和导入）
        button_layout = QHBoxLayout()
        
        button_layout.addStretch()
        
        self.export_btn = QPushButton("📤 " + self.tr("导出"))
        self.export_btn.clicked.connect(self.export_data)
        button_layout.addWidget(self.export_btn)
        
        self.import_btn = QPushButton("📥 " + self.tr("导入"))
        self.import_btn.clicked.connect(self.import_data)
        button_layout.addWidget(self.import_btn)
        
        layout.addLayout(button_layout)
    
    def create_category_widget(self):
        """创建分类控件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 标题行
        title_layout = QHBoxLayout()
        title = QLabel(self.tr("分类"))
        title.setProperty("class", "section-title")
        title_layout.addWidget(title)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # 创建分类表格
        self.category_table = QTableWidget()
        self.category_table.setColumnCount(1)
        self.category_table.setHorizontalHeaderLabels([self.tr("分类名称")])
        self.category_table.horizontalHeader().setStretchLastSection(True)
        self.category_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.category_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.category_table.setSelectionMode(QTableWidget.SingleSelection)
        self.category_table.itemSelectionChanged.connect(self.on_category_selected)
        
        # 启用右键菜单
        self.category_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.category_table.customContextMenuRequested.connect(self.show_category_context_menu)
        
        layout.addWidget(self.category_table)
        
        return widget
    
    def create_code_widget(self):
        """创建暗码控件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 搜索区域
        search_group = QGroupBox(self.tr("搜索"))
        search_layout = QHBoxLayout(search_group)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("输入搜索关键字..."))
        search_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("🔍 " + self.tr("搜索"))
        search_btn.clicked.connect(self.search_codes)
        search_layout.addWidget(search_btn)
        
        clear_search_btn = QPushButton("🗑️ " + self.tr("清除搜索"))
        clear_search_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(clear_search_btn)
        
        layout.addWidget(search_group)
        
        # 创建暗码表格
        self.code_table = QTableWidget()
        self.code_table.setColumnCount(2)
        self.code_table.setHorizontalHeaderLabels([self.tr("Code"), self.tr("描述")])
        self.code_table.horizontalHeader().setStretchLastSection(True)
        self.code_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.code_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.code_table.setSelectionMode(QTableWidget.SingleSelection)
        
        # 双击事件
        self.code_table.itemDoubleClicked.connect(self.on_code_double_clicked)
        
        header = self.code_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        
        layout.addWidget(self.code_table)
        
        # 操作按钮区域
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ " + self.tr("新增"))
        self.add_btn.clicked.connect(self.add_code)
        button_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("✏️ " + self.tr("编辑"))
        self.edit_btn.clicked.connect(self.edit_code)
        button_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️ " + self.tr("删除"))
        self.delete_btn.clicked.connect(self.delete_code)
        button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        return widget
    
    def load_data(self):
        """加载数据"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.secret_codes = data.get('codes', {})
                    self.categories = data.get('categories', ["TCL", "Samsung", "Others"])
                    logger.debug(f"加载暗码数据: {len(self.secret_codes)} 个分类")
            else:
                # 创建默认数据
                self.secret_codes = {}
                self.categories = ["TCL", "Samsung", "Others"]
                self.save_data()
                logger.debug("创建默认暗码数据")
        except Exception as e:
            logger.exception(f"加载暗码数据失败: {e}")
            self.secret_codes = {}
            self.categories = ["TCL", "Samsung", "Others"]
        
        # 刷新分类列表
        self.refresh_category_table()
    
    def save_data(self):
        """保存数据"""
        try:
            data = {
                'categories': self.categories,
                'codes': self.secret_codes
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                logger.debug("保存暗码数据成功")
        except Exception as e:
            logger.exception(f"保存暗码数据失败: {e}")
    
    def refresh_category_table(self):
        """刷新分类表格"""
        self.category_table.setRowCount(0)
        
        for category in self.categories:
            row = self.category_table.rowCount()
            self.category_table.insertRow(row)
            item = QTableWidgetItem(category)
            self.category_table.setItem(row, 0, item)
    
    def on_category_selected(self):
        """分类选择事件"""
        selected_items = self.category_table.selectedItems()
        if selected_items:
            category = selected_items[0].text()
            self.current_category = category
            self.refresh_code_table()
    
    def refresh_code_table(self):
        """刷新暗码表格"""
        self.code_table.setRowCount(0)
        
        if not self.current_category:
            return
        
        # 获取当前分类的暗码
        codes = self.secret_codes.get(self.current_category, [])
        
        for code_data in codes:
            row = self.code_table.rowCount()
            self.code_table.insertRow(row)
            
            code = code_data.get('code', '')
            description = code_data.get('description', '')
            
            self.code_table.setItem(row, 0, QTableWidgetItem(code))
            self.code_table.setItem(row, 1, QTableWidgetItem(description))
            
            self.code_table.item(row, 0).setFlags(self.code_table.item(row, 0).flags() & ~Qt.ItemIsEditable)
            self.code_table.item(row, 1).setFlags(self.code_table.item(row, 1).flags() & ~Qt.ItemIsEditable)
    
    def search_codes(self):
        """搜索暗码"""
        search_text = self.search_input.text().strip()
        
        if not search_text:
            self.refresh_code_table()
            return
        
        self.code_table.setRowCount(0)
        
        if not self.current_category:
            return
        
        codes = self.secret_codes.get(self.current_category, [])
        
        # 过滤匹配的暗码
        filtered_codes = []
        for code_data in codes:
            code = code_data.get('code', '')
            description = code_data.get('description', '')
            
            if search_text.lower() in code.lower() or search_text.lower() in description.lower():
                filtered_codes.append(code_data)
        
        for code_data in filtered_codes:
            row = self.code_table.rowCount()
            self.code_table.insertRow(row)
            
            code = code_data.get('code', '')
            description = code_data.get('description', '')
            
            self.code_table.setItem(row, 0, QTableWidgetItem(code))
            self.code_table.setItem(row, 1, QTableWidgetItem(description))
    
    def clear_search(self):
        """清除搜索"""
        self.search_input.clear()
        self.refresh_code_table()
    
    def add_code(self):
        """新增暗码"""
        if not self.current_category:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择一个分类"))
            return
        
        dialog = SecretCodeEditDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            code = dialog.get_code()
            description = dialog.get_description()
            
            if code:
                if self.current_category not in self.secret_codes:
                    self.secret_codes[self.current_category] = []
                
                self.secret_codes[self.current_category].append({
                    'code': code,
                    'description': description
                })
                
                self.save_data()
                self.refresh_code_table()
                QMessageBox.information(self, self.tr("成功"), self.tr("暗码添加成功！"))
    
    def edit_code(self):
        """编辑暗码"""
        if not self.current_category:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择一个分类"))
            return
        
        selected_items = self.code_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择要编辑的暗码"))
            return
        
        row = selected_items[0].row()
        
        current_code = self.code_table.item(row, 0).text()
        current_description = self.code_table.item(row, 1).text()
        
        dialog = SecretCodeEditDialog(self, code=current_code, description=current_description)
        if dialog.exec_() == QDialog.Accepted:
            new_code = dialog.get_code()
            new_description = dialog.get_description()
            
            if new_code:
                # 更新数据
                codes = self.secret_codes.get(self.current_category, [])
                for code_data in codes:
                    if code_data.get('code') == current_code:
                        code_data['code'] = new_code
                        code_data['description'] = new_description
                        break
                
                self.save_data()
                self.refresh_code_table()
                QMessageBox.information(self, self.tr("成功"), self.tr("暗码更新成功！"))
    
    def delete_code(self):
        """删除暗码"""
        if not self.current_category:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择一个分类"))
            return
        
        selected_items = self.code_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择要删除的暗码"))
            return
        
        reply = QMessageBox.question(
            self, 
            self.tr("确认删除"),
            self.tr("确定要删除这个暗码吗？"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            row = selected_items[0].row()
            code_to_delete = self.code_table.item(row, 0).text()
            
            # 从数据中删除
            codes = self.secret_codes.get(self.current_category, [])
            self.secret_codes[self.current_category] = [
                code_data for code_data in codes 
                if code_data.get('code') != code_to_delete
            ]
            
            self.save_data()
            self.refresh_code_table()
            QMessageBox.information(self, self.tr("成功"), self.tr("暗码删除成功！"))
    
    def export_data(self):
        """导出数据"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                self.tr("导出暗码数据"),
                "secret_codes.json",
                "JSON files (*.json)"
            )
            
            if file_path:
                data = {
                    'categories': self.categories,
                    'codes': self.secret_codes
                }
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                QMessageBox.information(
                    self, 
                    self.tr("成功"),
                    self.tr(f"暗码数据已导出到: {file_path}")
                )
        except Exception as e:
            logger.exception(f"导出暗码数据失败: {e}")
            QMessageBox.critical(
                self,
                self.tr("失败"),
                self.tr(f"导出暗码数据失败: {e}")
            )
    
    def import_data(self):
        """导入数据"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                self.tr("导入暗码数据"),
                "",
                "JSON files (*.json)"
            )
            
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_data = json.load(f)
                
                # 兼容旧格式（直接是codes字典）和新格式（包含categories和codes）
                if isinstance(imported_data, dict):
                    if 'categories' in imported_data and 'codes' in imported_data:
                        # 新格式
                        for category in imported_data.get('categories', []):
                            if category not in self.categories:
                                self.categories.append(category)
                        
                        for category, codes in imported_data.get('codes', {}).items():
                            if category not in self.secret_codes:
                                self.secret_codes[category] = []
                            self.secret_codes[category].extend(codes)
                    else:
                        # 旧格式（直接是codes字典）
                        for category, codes in imported_data.items():
                            if category not in self.secret_codes:
                                self.secret_codes[category] = []
                            self.secret_codes[category].extend(codes)
                
                self.save_data()
                self.refresh_code_table()
                QMessageBox.information(
                    self,
                    self.tr("成功"),
                    self.tr(f"暗码数据已导入: {file_path}")
                )
        except Exception as e:
            logger.exception(f"导入暗码数据失败: {e}")
            QMessageBox.critical(
                self,
                self.tr("失败"),
                self.tr(f"导入暗码数据失败: {e}")
            )
    
    def on_code_double_clicked(self, item):
        """双击code事件"""
        # 占位函数，后续实现功能
        logger.debug(f"双击暗码: {item.text()}")
        pass
    
    def add_category(self):
        """新增分类"""
        dialog = CategoryEditDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            new_category = dialog.get_category_name()
            if new_category and new_category not in self.categories:
                self.categories.append(new_category)
                self.save_data()
                self.refresh_category_table()
                QMessageBox.information(self, self.tr("成功"), self.tr("分类添加成功！"))
            elif new_category in self.categories:
                QMessageBox.warning(self, self.tr("提示"), self.tr("分类已存在！"))
    
    def edit_category(self):
        """编辑分类"""
        selected_items = self.category_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择要编辑的分类"))
            return
        
        old_category = selected_items[0].text()
        
        dialog = CategoryEditDialog(parent=self, category_name=old_category)
        if dialog.exec_() == QDialog.Accepted:
            new_category = dialog.get_category_name()
            if new_category and new_category != old_category:
                if new_category not in self.categories:
                    # 更新分类列表
                    index = self.categories.index(old_category)
                    self.categories[index] = new_category
                    
                    # 更新数据中的分类键
                    if old_category in self.secret_codes:
                        codes = self.secret_codes.pop(old_category)
                        self.secret_codes[new_category] = codes
                    
                    self.save_data()
                    self.refresh_category_table()
                    
                    # 如果当前正在编辑这个分类，更新当前分类
                    if self.current_category == old_category:
                        self.current_category = new_category
                    
                    self.refresh_code_table()
                    QMessageBox.information(self, self.tr("成功"), self.tr("分类更新成功！"))
                else:
                    QMessageBox.warning(self, self.tr("提示"), self.tr("新分类名已存在！"))
    
    def delete_category(self):
        """删除分类"""
        selected_items = self.category_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择要删除的分类"))
            return
        
        category_to_delete = selected_items[0].text()
        
        reply = QMessageBox.question(
            self,
            self.tr("确认删除"),
            self.tr(f"确定要删除分类'{category_to_delete}'吗？\n删除分类会同时删除该分类下的所有暗码。"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 从分类列表中删除
            self.categories.remove(category_to_delete)
            
            # 从数据中删除分类及其所有暗码
            if category_to_delete in self.secret_codes:
                del self.secret_codes[category_to_delete]
            
            # 如果当前正在编辑这个分类，清空选择
            if self.current_category == category_to_delete:
                self.current_category = None
                self.code_table.setRowCount(0)
            
            self.save_data()
            self.refresh_category_table()
            QMessageBox.information(self, self.tr("成功"), self.tr("分类删除成功！"))
    
    def show_category_context_menu(self, position: QPoint):
        """显示分类右键菜单"""
        menu = QMenu(self)
        
        # 检查是否有选中的项
        item = self.category_table.itemAt(position)
        
        if item is None:
            # 没有选中任何项，只显示新增
            add_action = menu.addAction("➕ " + self.tr("新增分类"))
            add_action.triggered.connect(self.add_category)
        else:
            # 有选中项，显示全部选项
            add_action = menu.addAction("➕ " + self.tr("新增分类"))
            add_action.triggered.connect(self.add_category)
            menu.addSeparator()
            
            edit_action = menu.addAction("✏️ " + self.tr("编辑分类"))
            edit_action.triggered.connect(self.edit_category)
            
            menu.addSeparator()
            
            # 上移和下移选项
            row = self.category_table.row(item)
            move_up_action = menu.addAction("⬆️ " + self.tr("上移"))
            move_up_action.triggered.connect(lambda: self.move_category_up(row))
            
            move_down_action = menu.addAction("⬇️ " + self.tr("下移"))
            move_down_action.triggered.connect(lambda: self.move_category_down(row))
            
            menu.addSeparator()
            
            delete_action = menu.addAction("🗑️ " + self.tr("删除分类"))
            delete_action.triggered.connect(self.delete_category)
        
        # 显示菜单
        menu.exec_(self.category_table.viewport().mapToGlobal(position))
    
    def move_category_up(self, row):
        """上移分类"""
        if row > 0:
            # 交换categories列表中的位置
            self.categories[row], self.categories[row - 1] = self.categories[row - 1], self.categories[row]
            
            # 刷新表格
            self.refresh_category_table()
            
            # 选中移动后的行
            self.category_table.selectRow(row - 1)
            
            # 保存数据
            self.save_data()
            logger.debug(f"[move_category_up] 分类已上移，从行{row}移动到行{row-1}")
    
    def move_category_down(self, row):
        """下移分类"""
        if row < len(self.categories) - 1:
            # 交换categories列表中的位置
            self.categories[row], self.categories[row + 1] = self.categories[row + 1], self.categories[row]
            
            # 刷新表格
            self.refresh_category_table()
            
            # 选中移动后的行
            self.category_table.selectRow(row + 1)
            
            # 保存数据
            self.save_data()
            logger.debug(f"[move_category_down] 分类已下移，从行{row}移动到行{row+1}")


class SecretCodeEditDialog(QDialog):
    """暗码编辑对话框"""
    
    def __init__(self, parent=None, code="", description=""):
        super().__init__(parent)
        
        # 获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager.get_instance()
        
        self.setWindowTitle(self.tr("编辑暗码"))
        self.setModal(True)
        self.resize(400, 200)
        
        self.code = code
        self.description = description
        
        self.setup_ui()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        from PyQt5.QtWidgets import QFormLayout, QDialogButtonBox
        
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.code_input = QLineEdit()
        self.code_input.setText(self.code)
        form_layout.addRow(self.tr("Code*:"), self.code_input)
        
        self.description_input = QLineEdit()
        self.description_input.setText(self.description)
        form_layout.addRow(self.tr("描述:"), self.description_input)
        
        layout.addLayout(form_layout)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_code(self):
        """获取Code"""
        return self.code_input.text().strip()
    
    def get_description(self):
        """获取描述"""
        return self.description_input.text().strip()


class CategoryEditDialog(QDialog):
    """分类编辑对话框"""
    
    def __init__(self, parent=None, category_name=""):
        super().__init__(parent)
        
        # 获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager.get_instance()
        
        self.setWindowTitle(self.tr("编辑分类"))
        self.setModal(True)
        self.resize(400, 150)
        
        self.category_name = category_name
        
        self.setup_ui()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        from PyQt5.QtWidgets import QFormLayout, QDialogButtonBox
        
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.category_input = QLineEdit()
        self.category_input.setText(self.category_name)
        form_layout.addRow(self.tr("分类名称*:"), self.category_input)
        
        layout.addLayout(form_layout)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_category_name(self):
        """获取分类名称"""
        return self.category_input.text().strip()

