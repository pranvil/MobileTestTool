#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tab管理对话框
支持tab排序、显示/隐藏、自定义tab和card管理
"""

import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, 
                             QCheckBox, QGroupBox, QTabWidget, QWidget,
                             QLineEdit, QTextEdit, QMessageBox, QComboBox,
                             QSpinBox, QFormLayout, QScrollArea, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from core.debug_logger import logger


class TabManagerDialog(QDialog):
    """Tab管理对话框"""
    
    def __init__(self, tab_config_manager, parent=None):
        super().__init__(parent)
        self.tab_config_manager = tab_config_manager
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        
        self.setWindowTitle(self.tr("Tab管理"))
        self.setModal(True)
        self.resize(800, 600)
        
        self.setup_ui()
        self.load_tab_config()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 创建Tab控件
        self.tab_widget = QTabWidget()
        
        # Tab排序和显示管理
        self.setup_tab_order_ui()
        
        # 自定义Tab管理
        self.setup_custom_tab_ui()
        
        # 自定义Card管理
        self.setup_custom_card_ui()
        
        layout.addWidget(self.tab_widget)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.reset_btn = QPushButton(self.tr("重置为默认"))
        self.reset_btn.clicked.connect(self.reset_to_default)
        button_layout.addWidget(self.reset_btn)
        
        self.cancel_btn = QPushButton(self.tr("取消"))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton(self.tr("保存"))
        self.save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def setup_tab_order_ui(self):
        """设置Tab排序和显示管理UI"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Tab排序
        order_group = QGroupBox(self.tr("Tab排序"))
        order_layout = QVBoxLayout(order_group)
        
        order_layout.addWidget(QLabel(self.tr("拖拽调整Tab顺序:")))
        
        self.tab_order_list = QListWidget()
        self.tab_order_list.setDragDropMode(QListWidget.InternalMove)
        order_layout.addWidget(self.tab_order_list)
        
        layout.addWidget(order_group)
        
        # Tab显示控制
        visibility_group = QGroupBox(self.tr("Tab显示控制"))
        visibility_layout = QVBoxLayout(visibility_group)
        
        self.visibility_widgets = {}
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # 这里会在load_tab_config中动态添加checkbox
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(200)
        
        visibility_layout.addWidget(scroll_area)
        layout.addWidget(visibility_group)
        
        self.tab_widget.addTab(widget, self.tr("Tab排序和显示"))
    
    def setup_custom_tab_ui(self):
        """设置自定义Tab管理UI"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 自定义Tab列表
        list_group = QGroupBox(self.tr("自定义Tab列表"))
        list_layout = QVBoxLayout(list_group)
        
        self.custom_tab_list = QListWidget()
        list_layout.addWidget(self.custom_tab_list)
        
        # 按钮
        btn_layout = QHBoxLayout()
        self.add_tab_btn = QPushButton(self.tr("添加Tab"))
        self.add_tab_btn.clicked.connect(self.show_add_tab_dialog)
        btn_layout.addWidget(self.add_tab_btn)
        
        self.edit_tab_btn = QPushButton(self.tr("编辑Tab"))
        self.edit_tab_btn.clicked.connect(self.edit_custom_tab)
        btn_layout.addWidget(self.edit_tab_btn)
        
        self.delete_tab_btn = QPushButton(self.tr("删除Tab"))
        self.delete_tab_btn.clicked.connect(self.delete_custom_tab)
        btn_layout.addWidget(self.delete_tab_btn)
        
        list_layout.addLayout(btn_layout)
        layout.addWidget(list_group)
        
        self.tab_widget.addTab(widget, self.tr("自定义Tab"))
    
    def setup_custom_card_ui(self):
        """设置自定义Card管理UI"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Card列表
        list_group = QGroupBox(self.tr("自定义Card列表"))
        list_layout = QVBoxLayout(list_group)
        
        self.custom_card_list = QListWidget()
        list_layout.addWidget(self.custom_card_list)
        
        # 按钮
        btn_layout = QHBoxLayout()
        self.add_card_btn = QPushButton(self.tr("添加Card"))
        self.add_card_btn.clicked.connect(self.show_add_card_dialog)
        btn_layout.addWidget(self.add_card_btn)
        
        self.edit_card_btn = QPushButton(self.tr("编辑Card"))
        self.edit_card_btn.clicked.connect(self.edit_custom_card)
        btn_layout.addWidget(self.edit_card_btn)
        
        self.delete_card_btn = QPushButton(self.tr("删除Card"))
        self.delete_card_btn.clicked.connect(self.delete_custom_card)
        btn_layout.addWidget(self.delete_card_btn)
        
        list_layout.addLayout(btn_layout)
        layout.addWidget(list_group)
        
        self.tab_widget.addTab(widget, self.tr("自定义Card"))
    
    def load_tab_config(self):
        """加载Tab配置"""
        try:
            # 加载Tab顺序
            self.tab_order_list.clear()
            tab_order = self.tab_config_manager.get_tab_order()
            tab_visibility = self.tab_config_manager.get_tab_visibility()
            all_tabs = self.tab_config_manager.get_all_tabs()
            
            # 创建tab名称映射
            tab_name_map = {tab['id']: tab['name'] for tab in all_tabs}
            
            for tab_id in tab_order:
                if tab_id in tab_name_map:
                    item = QListWidgetItem(tab_name_map[tab_id])
                    item.setData(Qt.UserRole, tab_id)
                    self.tab_order_list.addItem(item)
            
            # 加载Tab显示控制
            self.visibility_widgets.clear()
            scroll_widget = self.tab_order_list.parent().parent().findChild(QScrollArea).widget()
            scroll_layout = scroll_widget.layout()
            
            # 清除现有控件
            for i in reversed(range(scroll_layout.count())):
                child = scroll_layout.itemAt(i).widget()
                if child:
                    child.setParent(None)
            
            for tab in all_tabs:
                checkbox = QCheckBox(tab['name'])
                checkbox.setChecked(tab.get('visible', True))
                checkbox.setProperty('tab_id', tab['id'])
                
                # 检查Tab是否可以隐藏
                if not self.tab_config_manager.can_hide_tab(tab['id']):
                    checkbox.setEnabled(False)
                    checkbox.setToolTip(self.tr("此Tab不能隐藏"))
                
                self.visibility_widgets[tab['id']] = checkbox
                scroll_layout.addWidget(checkbox)
            
            # 加载自定义Tab
            self.load_custom_tabs()
            
            # 加载自定义Card
            self.load_custom_cards()
            
        except Exception as e:
            logger.exception(f"{self.tr('加载Tab配置失败:')} {e}")
    
    def load_custom_tabs(self):
        """加载自定义Tab列表"""
        self.custom_tab_list.clear()
        for tab in self.tab_config_manager.custom_tabs:
            item = QListWidgetItem(f"{tab['name']} ({tab['id']})")
            item.setData(Qt.UserRole, tab['id'])
            self.custom_tab_list.addItem(item)
    
    def load_custom_cards(self):
        """加载自定义Card列表"""
        self.custom_card_list.clear()
        for card in self.tab_config_manager.custom_cards:
            item = QListWidgetItem(f"{card['name']} -> {card.get('tab_id', 'Unknown')}")
            item.setData(Qt.UserRole, card['id'])
            self.custom_card_list.addItem(item)
    
    def save_config(self):
        """保存配置"""
        try:
            # 保存Tab顺序
            new_order = []
            for i in range(self.tab_order_list.count()):
                item = self.tab_order_list.item(i)
                tab_id = item.data(Qt.UserRole)
                new_order.append(tab_id)
            
            self.tab_config_manager.set_tab_order(new_order)
            
            # 保存Tab显示状态
            for tab_id, checkbox in self.visibility_widgets.items():
                self.tab_config_manager.set_tab_visibility(tab_id, checkbox.isChecked())
            
            QMessageBox.information(self, self.tr("成功"), self.tr("Tab配置已保存"))
            self.accept()
            
        except Exception as e:
            logger.exception(f"{self.tr('保存Tab配置失败:')} {e}")
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('保存失败:')} {str(e)}")
    
    def reset_to_default(self):
        """重置为默认配置"""
        reply = QMessageBox.question(
            self,
            self.tr("确认重置"),
            self.tr("确定要重置为默认Tab配置吗？这将删除所有自定义Tab和Card。"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.tab_config_manager.reset_to_default()
            self.load_tab_config()
            QMessageBox.information(self, self.tr("成功"), self.tr("已重置为默认配置"))
    
    def show_add_tab_dialog(self):
        """显示添加Tab对话框"""
        dialog = CustomTabDialog(self.tab_config_manager, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_custom_tabs()
    
    def edit_custom_tab(self):
        """编辑自定义Tab"""
        current_item = self.custom_tab_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, self.tr("警告"), self.tr("请选择要编辑的Tab"))
            return
        
        tab_id = current_item.data(Qt.UserRole)
        dialog = CustomTabDialog(self.tab_config_manager, tab_id=tab_id, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_custom_tabs()
    
    def delete_custom_tab(self):
        """删除自定义Tab"""
        current_item = self.custom_tab_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, self.tr("警告"), self.tr("请选择要删除的Tab"))
            return
        
        tab_id = current_item.data(Qt.UserRole)
        tab_name = current_item.text()
        
        reply = QMessageBox.question(
            self,
            self.tr("确认删除"),
            f"{self.tr('确定要删除Tab')} '{tab_name}' {self.tr('吗？')}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.tab_config_manager.delete_custom_tab(tab_id):
                self.load_custom_tabs()
                QMessageBox.information(self, self.tr("成功"), self.tr("Tab已删除"))
    
    def show_add_card_dialog(self):
        """显示添加Card对话框"""
        dialog = CustomCardDialog(self.tab_config_manager, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_custom_cards()
    
    def edit_custom_card(self):
        """编辑自定义Card"""
        current_item = self.custom_card_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, self.tr("警告"), self.tr("请选择要编辑的Card"))
            return
        
        card_id = current_item.data(Qt.UserRole)
        dialog = CustomCardDialog(self.tab_config_manager, card_id=card_id, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_custom_cards()
    
    def delete_custom_card(self):
        """删除自定义Card"""
        current_item = self.custom_card_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, self.tr("警告"), self.tr("请选择要删除的Card"))
            return
        
        card_id = current_item.data(Qt.UserRole)
        card_name = current_item.text()
        
        reply = QMessageBox.question(
            self,
            self.tr("确认删除"),
            f"{self.tr('确定要删除Card')} '{card_name}' {self.tr('吗？')}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.tab_config_manager.delete_custom_card(card_id):
                self.load_custom_cards()
                QMessageBox.information(self, self.tr("成功"), self.tr("Card已删除"))


class CustomTabDialog(QDialog):
    """自定义Tab对话框"""
    
    def __init__(self, tab_config_manager, tab_id=None, parent=None):
        super().__init__(parent)
        self.tab_config_manager = tab_config_manager
        self.tab_id = tab_id
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        
        self.setWindowTitle(self.tr("自定义Tab") if not tab_id else self.tr("编辑Tab"))
        self.setModal(True)
        self.resize(500, 400)
        
        self.setup_ui()
        if tab_id:
            self.load_tab_data()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # Tab基本信息
        info_group = QGroupBox(self.tr("Tab信息"))
        info_layout = QFormLayout(info_group)
        
        self.name_edit = QLineEdit()
        info_layout.addRow(self.tr("Tab名称:"), self.name_edit)
        
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        info_layout.addRow(self.tr("描述:"), self.description_edit)
        
        layout.addWidget(info_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton(self.tr("取消"))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton(self.tr("保存"))
        self.save_btn.clicked.connect(self.save_tab)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def load_tab_data(self):
        """加载Tab数据"""
        if not self.tab_id:
            return
        
        for tab in self.tab_config_manager.custom_tabs:
            if tab['id'] == self.tab_id:
                self.name_edit.setText(tab.get('name', ''))
                self.description_edit.setPlainText(tab.get('description', ''))
                break
    
    def save_tab(self):
        """保存Tab"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, self.tr("警告"), self.tr("Tab名称不能为空"))
            return
        
        tab_data = {
            'name': name,
            'description': self.description_edit.toPlainText().strip()
        }
        
        if self.tab_id:
            # 更新现有Tab
            if self.tab_config_manager.update_custom_tab(self.tab_id, tab_data):
                QMessageBox.information(self, self.tr("成功"), self.tr("Tab已更新"))
                self.accept()
        else:
            # 创建新Tab
            tab_id = self.tab_config_manager.create_custom_tab(tab_data)
            if tab_id:
                QMessageBox.information(self, self.tr("成功"), self.tr("Tab已创建"))
                self.accept()


class CustomCardDialog(QDialog):
    """自定义Card对话框"""
    
    def __init__(self, tab_config_manager, card_id=None, parent=None):
        super().__init__(parent)
        self.tab_config_manager = tab_config_manager
        self.card_id = card_id
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        
        self.setWindowTitle(self.tr("自定义Card") if not card_id else self.tr("编辑Card"))
        self.setModal(True)
        self.resize(400, 300)
        
        self.setup_ui()
        if card_id:
            self.load_card_data()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # Card基本信息
        info_group = QGroupBox(self.tr("Card信息"))
        info_layout = QFormLayout(info_group)
        
        self.name_edit = QLineEdit()
        info_layout.addRow(self.tr("Card名称:"), self.name_edit)
        
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        info_layout.addRow(self.tr("描述:"), self.description_edit)
        
        # Tab选择
        self.tab_combo = QComboBox()
        self.load_tab_options()
        info_layout.addRow(self.tr("所属Tab:"), self.tab_combo)
        
        layout.addWidget(info_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton(self.tr("取消"))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton(self.tr("保存"))
        self.save_btn.clicked.connect(self.save_card)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def load_tab_options(self):
        """加载Tab选项"""
        self.tab_combo.clear()
        all_tabs = self.tab_config_manager.get_all_tabs()
        
        for tab in all_tabs:
            self.tab_combo.addItem(tab['name'], tab['id'])
    
    def load_card_data(self):
        """加载Card数据"""
        if not self.card_id:
            return
        
        for card in self.tab_config_manager.custom_cards:
            if card['id'] == self.card_id:
                self.name_edit.setText(card.get('name', ''))
                self.description_edit.setPlainText(card.get('description', ''))
                
                # 设置Tab选择
                tab_id = card.get('tab_id', '')
                for i in range(self.tab_combo.count()):
                    if self.tab_combo.itemData(i) == tab_id:
                        self.tab_combo.setCurrentIndex(i)
                        break
                break
    
    def save_card(self):
        """保存Card"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, self.tr("警告"), self.tr("Card名称不能为空"))
            return
        
        tab_id = self.tab_combo.currentData()
        if not tab_id:
            QMessageBox.warning(self, self.tr("警告"), self.tr("请选择所属Tab"))
            return
        
        card_data = {
            'name': name,
            'description': self.description_edit.toPlainText().strip(),
            'tab_id': tab_id,
            'buttons': []  # 暂时为空，后续可以扩展
        }
        
        if self.card_id:
            # 更新现有Card
            for i, card in enumerate(self.tab_config_manager.custom_cards):
                if card['id'] == self.card_id:
                    self.tab_config_manager.custom_cards[i].update(card_data)
                    self.tab_config_manager.save_config()
                    QMessageBox.information(self, self.tr("成功"), self.tr("Card已更新"))
                    self.accept()
                    return
        else:
            # 创建新Card
            card_id = self.tab_config_manager.create_custom_card(card_data)
            if card_id:
                QMessageBox.information(self, self.tr("成功"), self.tr("Card已创建"))
                self.accept()
    
    def get_card_data(self):
        """获取Card数据"""
        return {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'tab_id': self.tab_combo.currentData(),
            'buttons': []
        }
