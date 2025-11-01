#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一管理对话框
整合Tab管理和按钮管理功能，并提供配置导出/导入功能
"""

import os
import json
import datetime
from PyQt5.QtWidgets import (QDialog, QTabWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QMessageBox, QFileDialog, QGroupBox,
                             QListWidget, QListWidgetItem, QCheckBox, QScrollArea, QWidget,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QFormLayout, QLineEdit, QTextEdit, QComboBox,
                             QLabel, QSplitter, QFrame, QAbstractItemView)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from core.debug_logger import logger


class DragDropButtonTable(QTableWidget):
    """支持拖拽排序的按钮表格"""

    rows_reordered = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragDropOverwriteMode(False)
        self.setDefaultDropAction(Qt.MoveAction)
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

        if target_row > source_row:
            target_row -= 1

        if target_row == source_row or target_row < 0:
            event.ignore()
            return

        if target_row > self.rowCount():
            target_row = self.rowCount()

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


class UnifiedManagerDialog(QDialog):
    """统一管理对话框"""
    
    def __init__(self, tab_config_manager, custom_button_manager, parent=None):
        super().__init__(parent)
        self.tab_config_manager = tab_config_manager
        self.custom_button_manager = custom_button_manager
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        
        self.setWindowTitle(self.tr("自定义界面管理"))
        self.setModal(True)
        self.resize(1000, 700)
        self.setMinimumSize(800, 500)  # 设置最小尺寸，允许调整高度和宽度
        
        # 存储控件引用
        self.visibility_widgets = {}
        self.custom_tab_list = None
        self.custom_card_list = None
        self.button_table = None
        
        self.setup_ui()
        self.load_all_configs()

        self.custom_button_manager.buttons_updated.connect(self.load_buttons)
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # 左侧：Tab管理
        left_widget = self.create_tab_management_widget()
        splitter.addWidget(left_widget)
        
        # 右侧：按钮管理
        right_widget = self.create_button_management_widget()
        splitter.addWidget(right_widget)
        
        # 设置分割器比例
        splitter.setSizes([400, 600])
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.export_btn = QPushButton("📤 " + self.tr("导出配置"))
        self.export_btn.clicked.connect(self.export_config)
        button_layout.addWidget(self.export_btn)
        
        self.import_btn = QPushButton("📥 " + self.tr("导入配置"))
        self.import_btn.clicked.connect(self.import_config)
        button_layout.addWidget(self.import_btn)
        
        self.reset_btn = QPushButton("🔄 " + self.tr("重置为默认"))
        self.reset_btn.clicked.connect(self.reset_to_default)
        self.reset_btn.setStyleSheet("QPushButton { background-color: #dc3545; color: white; }")
        button_layout.addWidget(self.reset_btn)
        
        self.close_btn = QPushButton("❌ " + self.tr("关闭"))
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def create_tab_management_widget(self):
        """创建Tab管理控件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Tab显示控制
        visibility_group = QGroupBox(self.tr("Tab显示控制"))
        visibility_main_layout = QHBoxLayout(visibility_group)
        
        # 左侧：滚动区域
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        self.visibility_scroll_layout = scroll_layout
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(200)
        scroll_area.setMaximumHeight(300)
        visibility_main_layout.addWidget(scroll_area)
        
        # 右侧：应用按钮
        apply_layout = QVBoxLayout()
        apply_layout.addStretch()
        
        self.apply_btn = QPushButton("✅ " + self.tr("应用"))
        self.apply_btn.clicked.connect(self.apply_tab_visibility)
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        apply_layout.addWidget(self.apply_btn)
        
        visibility_main_layout.addLayout(apply_layout)
        layout.addWidget(visibility_group)
        
        # 自定义Tab管理
        custom_tab_group = QGroupBox(self.tr("自定义Tab管理"))
        custom_tab_main_layout = QHBoxLayout(custom_tab_group)
        
        # 左侧：Tab列表
        self.custom_tab_list = QListWidget()
        self.custom_tab_list.setMaximumHeight(120)
        custom_tab_main_layout.addWidget(self.custom_tab_list)
        
        # 右侧：Tab按钮（垂直排列）
        custom_tab_btn_layout = QVBoxLayout()
        self.add_tab_btn = QPushButton("➕ " + self.tr("添加Tab"))
        self.add_tab_btn.clicked.connect(self.show_add_tab_dialog)
        custom_tab_btn_layout.addWidget(self.add_tab_btn)
        
        self.edit_tab_btn = QPushButton("✏️ " + self.tr("编辑Tab"))
        self.edit_tab_btn.clicked.connect(self.edit_custom_tab)
        custom_tab_btn_layout.addWidget(self.edit_tab_btn)
        
        self.delete_tab_btn = QPushButton("🗑️ " + self.tr("删除Tab"))
        self.delete_tab_btn.clicked.connect(self.delete_custom_tab)
        custom_tab_btn_layout.addWidget(self.delete_tab_btn)
        
        custom_tab_main_layout.addLayout(custom_tab_btn_layout)
        layout.addWidget(custom_tab_group)
        
        # 自定义Card管理
        custom_card_group = QGroupBox(self.tr("自定义Card管理"))
        custom_card_main_layout = QHBoxLayout(custom_card_group)
        
        # 左侧：Card列表区域
        card_left_layout = QVBoxLayout()
        
        self.custom_card_list = QListWidget()
        self.custom_card_list.setMaximumHeight(120)
        card_left_layout.addWidget(self.custom_card_list)
        
        custom_card_main_layout.addLayout(card_left_layout)
        
        # 右侧：Card按钮（垂直排列）
        custom_card_btn_layout = QVBoxLayout()
        self.add_card_btn = QPushButton("➕ " + self.tr("添加Card"))
        self.add_card_btn.clicked.connect(self.show_add_card_dialog)
        custom_card_btn_layout.addWidget(self.add_card_btn)
        
        self.edit_card_btn = QPushButton("✏️ " + self.tr("编辑Card"))
        self.edit_card_btn.clicked.connect(self.edit_custom_card)
        custom_card_btn_layout.addWidget(self.edit_card_btn)
        
        self.delete_card_btn = QPushButton("🗑️ " + self.tr("删除Card"))
        self.delete_card_btn.clicked.connect(self.delete_custom_card)
        custom_card_btn_layout.addWidget(self.delete_card_btn)

        self.card_up_btn = QPushButton("⬆️ " + self.tr("上移"))
        self.card_up_btn.clicked.connect(lambda: self.move_custom_card(-1))
        custom_card_btn_layout.addWidget(self.card_up_btn)

        self.card_down_btn = QPushButton("⬇️ " + self.tr("下移"))
        self.card_down_btn.clicked.connect(lambda: self.move_custom_card(1))
        custom_card_btn_layout.addWidget(self.card_down_btn)
        
        custom_card_main_layout.addLayout(custom_card_btn_layout)
        layout.addWidget(custom_card_group)
        
        return widget
    
    def create_button_management_widget(self):
        """创建按钮管理控件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 顶部说明
        info_text = (self.tr("💡 在此配置自定义命令按钮，按钮将显示在指定的Tab和卡片中。") +
                    self.tr("adb命令会自动加上 'adb -s {device}' 前缀。"))
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #17a2b8; padding: 10px; background: #d1ecf1; border-radius: 4px;")
        layout.addWidget(info_label)
        
        # 按钮列表表格
        self.button_table = DragDropButtonTable()
        self.button_table.setColumnCount(7)
        self.button_table.setHorizontalHeaderLabels([
            self.tr('名称'), self.tr('类型'), self.tr('命令'), 
            self.tr('所在Tab'), self.tr('所在卡片'), self.tr('启用'), self.tr('描述')
        ])
        
        # 设置列宽
        header = self.button_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        
        self.button_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.button_table.setSelectionMode(QTableWidget.SingleSelection)
        self.button_table.rows_reordered.connect(self.on_button_rows_reordered)
        layout.addWidget(self.button_table)
        
        # 按钮操作
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ " + self.tr("添加"))
        self.add_btn.clicked.connect(self.add_button)
        button_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("✏️ " + self.tr("编辑"))
        self.edit_btn.clicked.connect(self.edit_button)
        button_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️ " + self.tr("删除"))
        self.delete_btn.clicked.connect(self.delete_button)
        button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 " + self.tr("刷新"))
        self.refresh_btn.clicked.connect(self.load_buttons)
        button_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(button_layout)
        
        return widget
    
    
    def load_all_configs(self):
        """加载所有配置"""
        self.load_tab_config()
        self.load_custom_tabs()
        self.load_custom_cards()
        self.load_buttons()
    
    def load_tab_config(self):
        """加载Tab配置"""
        try:
            # 加载Tab显示控制
            self.visibility_widgets.clear()
            
            # 清除现有控件
            for i in reversed(range(self.visibility_scroll_layout.count())):
                child = self.visibility_scroll_layout.itemAt(i).widget()
                if child:
                    child.setParent(None)
            
            # 获取所有Tab
            all_tabs = self.tab_config_manager.get_all_tabs()
            
            for tab in all_tabs:
                checkbox = QCheckBox(tab['name'])
                checkbox.setChecked(tab.get('visible', True))
                checkbox.setProperty('tab_id', tab['id'])
                
                # 检查Tab是否可以隐藏
                if not self.tab_config_manager.can_hide_tab(tab['id']):
                    checkbox.setEnabled(False)
                    checkbox.setToolTip(self.tr("此Tab不能隐藏"))
                
                self.visibility_widgets[tab['id']] = checkbox
                self.visibility_scroll_layout.addWidget(checkbox)
            
        except Exception as e:
            logger.exception(f"{self.tr('加载Tab配置失败:')} {e}")
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('加载Tab配置失败:')} {str(e)}")
    
    def load_custom_tabs(self):
        """加载自定义Tab列表"""
        try:
            self.custom_tab_list.clear()
            for tab in self.tab_config_manager.custom_tabs:
                item = QListWidgetItem(tab['name'])
                item.setData(Qt.UserRole, tab['id'])
                self.custom_tab_list.addItem(item)
        except Exception as e:
            logger.exception(f"{self.tr('加载自定义Tab失败:')} {e}")
    
    def load_custom_cards(self):
        """加载自定义Card列表"""
        try:
            self.custom_card_list.clear()
            for card in self.tab_config_manager.custom_cards:
                # 获取Card所属的Tab名称
                tab_name = "未知Tab"
                for tab in self.tab_config_manager.custom_tabs:
                    if tab['id'] == card.get('tab_id'):
                        tab_name = tab['name']
                        break
                
                item_text = f"{card['name']} ({tab_name})"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, card['id'])
                self.custom_card_list.addItem(item)
        except Exception as e:
            logger.exception(f"{self.tr('加载自定义Card失败:')} {e}")
    
    def load_buttons(self):
        """加载按钮到表格"""
        try:
            self.button_table.setSortingEnabled(False)
            self.button_table.setRowCount(0)
            buttons = self.custom_button_manager.get_all_buttons()
            
            for btn in buttons:
                row = self.button_table.rowCount()
                self.button_table.insertRow(row)
                
                # 获取按钮类型显示名称
                button_type = btn.get('type', 'adb')
                type_map = {
                    'adb': self.tr('ADB命令'),
                    'python': self.tr('Python脚本'),
                    'file': self.tr('打开文件'),
                    'program': self.tr('运行程序'),
                    'system': self.tr('系统命令')
                }
                type_display = type_map.get(button_type, self.tr('ADB命令'))
                
                self.button_table.setItem(row, 0, QTableWidgetItem(btn.get('name', '')))
                self.button_table.setItem(row, 1, QTableWidgetItem(type_display))
                self.button_table.setItem(row, 2, QTableWidgetItem(btn.get('command', '')))
                self.button_table.setItem(row, 3, QTableWidgetItem(btn.get('tab', '')))
                self.button_table.setItem(row, 4, QTableWidgetItem(btn.get('card', '')))
                self.button_table.setItem(row, 5, QTableWidgetItem('✓' if btn.get('enabled', True) else '✗'))
                self.button_table.setItem(row, 6, QTableWidgetItem(btn.get('description', '')))
                
                # 存储按钮ID
                self.button_table.item(row, 0).setData(Qt.UserRole, btn.get('id'))

            self.button_table.resizeRowsToContents()
        except Exception as e:
            logger.exception(f"{self.tr('加载按钮失败:')} {e}")
    
    def apply_tab_visibility(self):
        """应用Tab显示设置"""
        try:
            # 保存Tab可见性配置
            self.save_config()
            
            # 通知父窗口重新加载Tab
            if self.parent() and hasattr(self.parent(), 'reload_tabs'):
                self.parent().reload_tabs()
                QMessageBox.information(self, self.tr("成功"), self.tr("Tab显示设置已应用"))
            else:
                QMessageBox.warning(self, self.tr("警告"), self.tr("无法通知主窗口更新Tab"))
                
        except Exception as e:
            logger.exception(f"{self.tr('应用Tab显示设置失败:')} {e}")
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('应用Tab显示设置失败:')} {str(e)}")
    
    def save_config(self):
        """保存配置"""
        try:
            # 保存Tab可见性
            for tab_id, checkbox in self.visibility_widgets.items():
                self.tab_config_manager.tab_visibility[tab_id] = checkbox.isChecked()
            
            self.tab_config_manager.save_config()
            
        except Exception as e:
            logger.exception(f"{self.tr('保存配置失败:')} {e}")
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('保存失败:')} {str(e)}")
    
    def export_config(self):
        """导出配置"""
        try:
            # 选择导出文件
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                self.tr("导出配置"), 
                f"MobileTestTool_Config_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON文件 (*.json)"
            )
            
            if file_path:
                # 收集所有配置
                config_data = {
                    'export_time': datetime.datetime.now().isoformat(),
                    'version': '1.0',
                    'tab_config': {
                        'tab_order': self.tab_config_manager.tab_order,
                        'tab_visibility': self.tab_config_manager.tab_visibility,
                        'custom_tabs': self.tab_config_manager.custom_tabs,
                        'custom_cards': self.tab_config_manager.custom_cards
                    },
                    'button_config': {
                        'custom_buttons': self.custom_button_manager.get_all_buttons()
                    }
                }
                
                # 保存到文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
                
                QMessageBox.information(self, self.tr("成功"), f"{self.tr('配置已导出到:')} {file_path}")
                logger.info(f"{self.tr('配置已导出到:')} {file_path}")
                
        except Exception as e:
            logger.exception(f"{self.tr('导出配置失败:')} {e}")
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('导出配置失败:')} {str(e)}")
    
    def import_config(self):
        """导入配置"""
        try:
            # 选择导入文件
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                self.tr("导入配置"), 
                "", 
                "JSON文件 (*.json)"
            )
            
            if file_path:
                # 确认导入
                reply = QMessageBox.question(
                    self,
                    self.tr("确认导入配置"),
                    (self.tr("⚠️ 导入配置将完全覆盖当前所有设置！\n\n") +
                     self.tr("• 所有自定义Tab将被替换\n") +
                     self.tr("• 所有自定义Card将被替换\n") +
                     self.tr("• 所有自定义Button将被替换\n") +
                     self.tr("• 当前配置将永久丢失\n\n") +
                     self.tr("确定要继续导入吗？")),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    # 读取配置文件
                    with open(file_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    
                    # 验证配置格式
                    if 'tab_config' not in config_data or 'button_config' not in config_data:
                        QMessageBox.warning(self, self.tr("错误"), self.tr("配置文件格式不正确"))
                        return
                    
                    # 导入Tab配置
                    tab_config = config_data['tab_config']
                    self.tab_config_manager.tab_visibility = tab_config.get('tab_visibility', {})
                    self.tab_config_manager.custom_tabs = tab_config.get('custom_tabs', [])
                    self.tab_config_manager.custom_cards = tab_config.get('custom_cards', [])
                    
                    # 处理tab_order，如果配置文件中没有则使用默认顺序
                    if 'tab_order' in tab_config:
                        self.tab_config_manager.tab_order = tab_config['tab_order']
                    else:
                        # 如果没有tab_order，创建默认顺序（包含自定义tab）
                        default_order = [tab['id'] for tab in self.tab_config_manager.default_tabs]
                        custom_tab_ids = [tab['id'] for tab in self.tab_config_manager.custom_tabs]
                        self.tab_config_manager.tab_order = default_order + custom_tab_ids
                    
                    self.tab_config_manager.save_config()
                    
                    # 导入按钮配置
                    button_config = config_data['button_config']
                    self.custom_button_manager.buttons = button_config.get('custom_buttons', [])
                    
                    # 验证并修复Button的Tab名称引用
                    self._validate_and_fix_button_tab_references()
                    
                    self.custom_button_manager.save_buttons()
                    
                    # 重新加载所有配置
                    self.load_all_configs()
                    
                    # 通知主窗口重新加载Tab
                    if self.parent() and hasattr(self.parent(), 'reload_tabs'):
                        self.parent().reload_tabs()
                        logger.info(self.tr("已通知主窗口重新加载Tab"))
                    
                    # 统计导入的内容
                    tab_count = len(self.tab_config_manager.custom_tabs)
                    card_count = len(self.tab_config_manager.custom_cards)
                    button_count = len(self.custom_button_manager.buttons)
                    
                    success_msg = (self.tr("✅ 配置导入成功！\n\n") +
                                 f"{self.tr('导入内容:')}\n" +
                                 f"• {self.tr('自定义Tab')}: {tab_count} {self.tr('个')}\n" +
                                 f"• {self.tr('自定义Card')}: {card_count} {self.tr('个')}\n" +
                                 f"• {self.tr('自定义Button')}: {button_count} {self.tr('个')}\n\n" +
                                 f"{self.tr('文件来源:')} {file_path}")
                    
                    QMessageBox.information(self, self.tr("导入成功"), success_msg)
                    logger.info(f"{self.tr('配置已从文件导入:')} {file_path}")
                    
        except Exception as e:
            logger.exception(f"{self.tr('导入配置失败:')} {e}")
            QMessageBox.critical(self, self.tr("错误"), f"{self.tr('导入配置失败:')} {str(e)}")
    
    def _validate_and_fix_button_tab_references(self):
        """验证并修复Button的Tab名称引用"""
        try:
            # 获取所有有效的Tab名称
            valid_tab_names = set()
            
            # 添加默认Tab名称
            for tab in self.tab_config_manager.default_tabs:
                valid_tab_names.add(tab['name'])
            
            # 添加自定义Tab名称
            for tab in self.tab_config_manager.custom_tabs:
                valid_tab_names.add(tab['name'])
            
            # 检查并修复Button的Tab引用
            fixed_count = 0
            for button in self.custom_button_manager.buttons:
                button_tab = button.get('tab', '')
                if button_tab and button_tab not in valid_tab_names:
                    # 尝试找到对应的Tab（通过ID或其他方式）
                    # 这里可以根据需要添加更复杂的匹配逻辑
                    logger.warning(f"{self.tr('Button')} '{button.get('name', '')}' {self.tr('引用了不存在的Tab:')} '{button_tab}'")
                    # 可以选择设置为空或使用默认值
                    button['tab'] = ''
                    fixed_count += 1
            
            if fixed_count > 0:
                logger.info(f"{self.tr('已修复')} {fixed_count} {self.tr('个Button的Tab引用')}")
                
        except Exception as e:
            logger.exception(f"{self.tr('验证Button Tab引用失败:')} {e}")
    
    def reset_to_default(self):
        """重置为默认配置"""
        reply = QMessageBox.question(
            self,
            self.tr("确认重置"),
            self.tr("确定要重置为默认配置吗？这将删除所有自定义Tab、Card和按钮。"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 重置Tab配置
                self.tab_config_manager.reset_to_default()
                
                # 重置按钮配置
                self.custom_button_manager.buttons = self.custom_button_manager._create_default_buttons()
                self.custom_button_manager.save_buttons()
                
                # 重新加载所有配置
                self.load_all_configs()
                
                # 通知主窗口重新加载Tab
                if self.parent() and hasattr(self.parent(), 'reload_tabs'):
                    self.parent().reload_tabs()
                    logger.info(self.tr("已通知主窗口重新加载Tab"))
                
                QMessageBox.information(self, self.tr("成功"), self.tr("已重置为默认配置"))
                logger.info(self.tr("配置已重置为默认"))
                
            except Exception as e:
                logger.exception(f"{self.tr('重置配置失败:')} {e}")
                QMessageBox.critical(self, self.tr("错误"), f"{self.tr('重置配置失败:')} {str(e)}")
    
    # Tab管理相关方法
    def show_add_tab_dialog(self):
        """显示添加Tab对话框"""
        from ui.tab_manager_dialog import CustomTabDialog
        dialog = CustomTabDialog(self.tab_config_manager, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_custom_tabs()
            self.load_tab_config()
    
    def edit_custom_tab(self):
        """编辑自定义Tab"""
        current_item = self.custom_tab_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, self.tr("警告"), self.tr("请选择要编辑的Tab"))
            return
        
        tab_id = current_item.data(Qt.UserRole)
        from ui.tab_manager_dialog import CustomTabDialog
        dialog = CustomTabDialog(self.tab_config_manager, tab_id=tab_id, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_custom_tabs()
            self.load_tab_config()
    
    def delete_custom_tab(self):
        """删除自定义Tab"""
        current_item = self.custom_tab_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, self.tr("警告"), self.tr("请选择要删除的Tab"))
            return
        
        tab_name = current_item.text()
        reply = QMessageBox.question(
            self, self.tr("确认删除"),
            f"{self.tr('确定要删除Tab')} '{tab_name}' {self.tr('吗？这将同时删除该Tab下的所有Card。')}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            tab_id = current_item.data(Qt.UserRole)
            if self.tab_config_manager.delete_custom_tab(tab_id):
                self.load_custom_tabs()
                self.load_custom_cards()
                self.load_tab_config()
                QMessageBox.information(self, self.tr("成功"), self.tr("Tab已删除"))
    
    def show_add_card_dialog(self):
        """显示添加Card对话框"""
        # 检查是否有自定义Tab
        if not self.tab_config_manager.custom_tabs:
            QMessageBox.information(
                self, 
                self.tr("提示"), 
                self.tr("请先创建自定义Tab，Card只能添加到自定义Tab中")
            )
            return
        
        from ui.tab_manager_dialog import CustomCardDialog
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
        from ui.tab_manager_dialog import CustomCardDialog
        dialog = CustomCardDialog(self.tab_config_manager, card_id=card_id, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_custom_cards()
    
    def delete_custom_card(self):
        """删除自定义Card"""
        current_item = self.custom_card_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, self.tr("警告"), self.tr("请选择要删除的Card"))
            return
        
        card_name = current_item.text()
        reply = QMessageBox.question(
            self, self.tr("确认删除"),
            f"{self.tr('确定要删除Card')} '{card_name}' {self.tr('吗？')}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            card_id = current_item.data(Qt.UserRole)
            if self.tab_config_manager.delete_custom_card(card_id):
                self.load_custom_cards()
                QMessageBox.information(self, self.tr("成功"), self.tr("Card已删除"))

    def move_custom_card(self, step):
        """调整自定义Card的顺序"""
        count = self.custom_card_list.count()
        if count == 0:
            return

        current_row = self.custom_card_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择要移动的Card"))
            return

        new_row = current_row + step
        if new_row < 0 or new_row >= count:
            return

        item = self.custom_card_list.takeItem(current_row)
        self.custom_card_list.insertItem(new_row, item)
        self.custom_card_list.setCurrentRow(new_row)

        ordered_ids = []
        for idx in range(self.custom_card_list.count()):
            ordered_ids.append(self.custom_card_list.item(idx).data(Qt.UserRole))

        if not self.tab_config_manager.reorder_custom_cards(ordered_ids):
            QMessageBox.warning(self, self.tr("失败"), self.tr("Card排序保存失败，请检查日志"))
        else:
            logger.info(self.tr("自定义Card顺序已更新"))
    
    # 按钮管理相关方法
    def add_button(self):
        """添加按钮"""
        from ui.custom_button_dialog import ButtonEditDialog
        dialog = ButtonEditDialog(self.custom_button_manager, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            button_data = dialog.get_button_data()
            if self.custom_button_manager.add_button(button_data):
                self.load_buttons()
                QMessageBox.information(self, self.tr("成功"), self.tr("按钮添加成功！"))
            else:
                QMessageBox.warning(self, self.tr("失败"), self.tr("按钮添加失败，请检查日志"))
    
    def edit_button(self):
        """编辑按钮"""
        current_row = self.button_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择要编辑的按钮"))
            return
        
        button_id = self.button_table.item(current_row, 0).data(Qt.UserRole)
        buttons = self.custom_button_manager.get_all_buttons()
        button_data = next((btn for btn in buttons if btn['id'] == button_id), None)
        
        if button_data:
            from ui.custom_button_dialog import ButtonEditDialog
            dialog = ButtonEditDialog(self.custom_button_manager, button_data=button_data, parent=self)
            if dialog.exec_() == QDialog.Accepted:
                updated_data = dialog.get_button_data()
                if self.custom_button_manager.update_button(button_id, updated_data):
                    self.load_buttons()
                    QMessageBox.information(self, self.tr("成功"), self.tr("按钮更新成功！"))
                else:
                    QMessageBox.warning(self, self.tr("失败"), self.tr("按钮更新失败，请检查日志"))
    
    def delete_button(self):
        """删除按钮"""
        current_row = self.button_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择要删除的按钮"))
            return
        
        button_name = self.button_table.item(current_row, 0).text()
        reply = QMessageBox.question(
            self, self.tr("确认删除"),
            f"{self.tr('确定要删除按钮')} '{button_name}' {self.tr('吗？')}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            button_id = self.button_table.item(current_row, 0).data(Qt.UserRole)
            if self.custom_button_manager.delete_button(button_id):
                self.load_buttons()
                QMessageBox.information(self, self.tr("成功"), self.tr("按钮删除成功！"))
            else:
                QMessageBox.warning(self, self.tr("失败"), self.tr("按钮删除失败，请检查日志"))
    
    def on_button_rows_reordered(self, ordered_ids):
        """处理按钮拖拽排序"""
        if not ordered_ids:
            return

        if not self.custom_button_manager.reorder_buttons(ordered_ids):
            QMessageBox.warning(self, self.tr("失败"), self.tr("按钮排序保存失败，请检查日志"))
        else:
            # 重新加载以确保显示与数据一致
            self.load_buttons()

    def closeEvent(self, event):
        """关闭事件"""
        try:
            # 保存当前配置
            self.save_config()
            event.accept()
        except Exception as e:
            logger.exception(f"{self.tr('保存配置失败:')} {e}")
            event.accept()
