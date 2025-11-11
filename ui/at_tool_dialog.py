#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AT命令工具对话框
"""

import json
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTextEdit, QTableWidget, QTableWidgetItem, 
                             QLineEdit, QComboBox, QMenu, QMessageBox,
                             QFileDialog, QHeaderView, QLabel, QSplitter, QWidget,
                             QFormLayout, QAbstractItemView)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDateTime, QTimer
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor, QFont
from core.debug_logger import logger


class DraggableCommandsTable(QTableWidget):
    """支持拖动排序的命令表格"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_dialog = parent
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragDropOverwriteMode(False)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        
        # 性能优化：使用像素级滚动，更流畅
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        
        # 性能优化：禁用交替行颜色，减少重绘开销
        self.setAlternatingRowColors(False)
        
        # 性能优化：禁用自动调整行高
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
    
    def dragEnterEvent(self, event):
        """处理拖入事件"""
        if event.source() == self:
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)
    
    def dragMoveEvent(self, event):
        """处理拖动移动事件"""
        if event.source() == self:
            # 快速接受事件，不做额外处理，提高拖动流畅度
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)
    
    def dropEvent(self, event):
        """处理拖放事件"""
        # 只处理来自自身的拖放事件
        if event.source() != self:
            super().dropEvent(event)
            return
        
        # 获取源行（拖动开始时的选中行）
        selected_items = self.selectedItems()
        if not selected_items:
            event.ignore()
            return
        
        source_row = selected_items[0].row()
        if source_row < 0 or source_row >= self.rowCount():
            event.ignore()
            return
        
        # 获取目标位置
        target_index = self.indexAt(event.pos())
        if target_index.isValid():
            target_row = target_index.row()
            # 获取拖放指示器位置（AboveItem或BelowItem）
            indicator = self.dropIndicatorPosition()
            if indicator == QAbstractItemView.BelowItem:
                target_row += 1
        else:
            # 如果拖到表格外，放到最后
            target_row = self.rowCount()
        
        # 调整目标行，考虑源行删除后的偏移
        if target_row > source_row:
            target_row -= 1
        
        # 如果目标位置和源位置相同，忽略
        if target_row == source_row or target_row < 0:
            event.ignore()
            return
        
        if target_row > self.rowCount():
            target_row = self.rowCount()
        
        # 直接操作数据列表，然后刷新表格
        if self.parent_dialog and hasattr(self.parent_dialog, 'at_commands'):
            # 获取要移动的命令
            if source_row < len(self.parent_dialog.at_commands):
                moved_command = self.parent_dialog.at_commands[source_row]
                
                # 从列表中删除
                self.parent_dialog.at_commands.pop(source_row)
                
                # 插入到目标位置
                self.parent_dialog.at_commands.insert(target_row, moved_command)
                
                # 保存
                self.parent_dialog.save_commands()
                
                # 使用QTimer延迟刷新，确保拖放事件完全处理完成
                QTimer.singleShot(0, lambda: self._refresh_after_drop(target_row))
        
        event.acceptProposedAction()
    
    def _refresh_after_drop(self, target_row):
        """拖放完成后刷新表格"""
        if self.parent_dialog and hasattr(self.parent_dialog, 'refresh_commands_table'):
            # 设置强制刷新标志，绕过更新检查
            self.parent_dialog._force_refresh = True
            
            # 刷新表格
            self.parent_dialog.refresh_commands_table()
            
            # 选中移动后的行
            if target_row < self.rowCount():
                self.selectRow(target_row)


class AddEditCommandDialog(QDialog):
    """添加/编辑AT命令对话框"""
    
    def __init__(self, parent=None, is_edit=False, name="", command=""):
        super().__init__(parent)
        
        # 从父窗口获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager.get_instance()
        
        self.is_edit = is_edit
        self.setup_ui(name, command)
    
    def setup_ui(self, name, command):
        """设置UI"""
        self.setWindowTitle(self.lang_manager.tr("编辑AT命令") if self.is_edit else self.lang_manager.tr("添加AT命令"))
        self.setFixedSize(500, 200)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 表单布局
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setText(name)
        self.name_input.setPlaceholderText(self.lang_manager.tr("例如：查询信号强度"))
        form_layout.addRow(self.lang_manager.tr("命令名称:"), self.name_input)
        
        self.command_input = QLineEdit()
        self.command_input.setText(command)
        self.command_input.setPlaceholderText(self.lang_manager.tr("例如：AT+CSQ"))
        form_layout.addRow(self.lang_manager.tr("AT命令:"), self.command_input)
        
        main_layout.addLayout(form_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton(self.lang_manager.tr("取消"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton(self.lang_manager.tr("确定"))
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        main_layout.addLayout(button_layout)
        
        # 设置焦点
        if self.is_edit:
            self.name_input.selectAll()
        else:
            self.name_input.setFocus()
    
    def get_data(self):
        """获取输入的数据"""
        return self.name_input.text().strip(), self.command_input.text().strip()


class ATCommandDialog(QDialog):
    """AT命令工具对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AT工具")
        self.setMinimumSize(800, 600)
        
        # 从父窗口获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager.get_instance()
        
        # AT命令列表（有序列表，每个元素为 {"name": "...", "command": "..."}）
        self.at_commands = []
        self.load_commands()
        
        # 当前选中的端口
        self.selected_port = None
        
        self.setup_ui()
    
    def keyPressEvent(self, event):
        """处理键盘事件，防止回车键清空显示区域"""
        # 如果焦点在输入框，回车应该发送命令而不是关闭对话框
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # 获取当前焦点控件
            focus_widget = self.focusWidget()
            # 如果焦点在输入框，让输入框处理回车，而不是关闭对话框
            if hasattr(self, 'command_input') and focus_widget == self.command_input:
                # 不调用父类的方法，让returnPressed信号处理
                # 只是阻止回车键的默认行为（关闭对话框）
                event.accept()
                return
        # 其他情况调用父类方法
        super().keyPressEvent(event)
    
    def setup_ui(self):
        """设置UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建分割器（改为左右布局）
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧：AT命令输入输出显示区域
        output_container = QVBoxLayout()
        output_widget = QWidget()
        output_widget.setLayout(output_container)
        
        # 标题行（包含标题和清除按钮）
        title_layout = QHBoxLayout()
        output_label = QLabel(self.lang_manager.tr("AT命令输出:"))
        title_layout.addWidget(output_label)
        title_layout.addStretch()
        
        self.clear_btn = QPushButton(self.lang_manager.tr("清除"))
        self.clear_btn.clicked.connect(self.clear_output)
        title_layout.addWidget(self.clear_btn)
        
        output_container.addLayout(title_layout)
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText(self.lang_manager.tr("AT命令输出将显示在这里..."))
        
        # 确保output_text不会响应回车键
        self.output_text.setFocusPolicy(Qt.NoFocus)
        
        # 设置字体为等宽字体，更适合显示AT命令
        font = QFont("Consolas", 9)
        font.setStyleHint(QFont.TypeWriter)
        self.output_text.setFont(font)
        
        output_container.addWidget(self.output_text)
        
        splitter.addWidget(output_widget)
        
        # 右侧：保存的命令列表
        commands_container = QVBoxLayout()
        commands_widget = QWidget()
        commands_widget.setLayout(commands_container)
        
        commands_label = QLabel(self.lang_manager.tr("保存的AT命令:"))
        commands_container.addWidget(commands_label)
        
        self.commands_table = DraggableCommandsTable(self)
        self.commands_table.setColumnCount(2)
        self.commands_table.setHorizontalHeaderLabels([
            self.lang_manager.tr("命令名称"), 
            self.lang_manager.tr("AT命令")
        ])
        # 允许手动调整列宽
        header = self.commands_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        self.commands_table.setColumnWidth(0, 150)  # 命令名称列初始宽度
        self.commands_table.setColumnWidth(1, 300)  # AT命令列初始宽度
        self.commands_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.commands_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.commands_table.customContextMenuRequested.connect(self.show_context_menu)
        self.commands_table.cellDoubleClicked.connect(self.on_command_double_clicked)
        self.commands_table.verticalHeader().setVisible(False)
        commands_container.addWidget(self.commands_table)
        
        # 在命令列表下方添加输入框和发送按钮
        input_layout = QHBoxLayout()
        input_layout.setSpacing(5)
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText(self.lang_manager.tr("输入AT命令..."))
        self.command_input.returnPressed.connect(self.send_command)
        self.command_input.setFocus()  # 设置焦点以便可以使用回车键发送
        input_layout.addWidget(self.command_input)
        
        self.send_btn = QPushButton(self.lang_manager.tr("发送"))
        self.send_btn.clicked.connect(self.send_command)
        input_layout.addWidget(self.send_btn)
        
        commands_container.addLayout(input_layout)
        
        splitter.addWidget(commands_widget)
        
        # 设置分割器比例（左右各占50%）
        splitter.setSizes([400, 500])
        
        # 刷新命令列表
        self.refresh_commands_table()
        
        # 最下面一行：控制按钮
        control_layout = QHBoxLayout()
        control_layout.setSpacing(5)
        
        # 端口下拉菜单
        port_label = QLabel(self.lang_manager.tr("端口:"))
        control_layout.addWidget(port_label)
        
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(120)
        self.refresh_ports()
        control_layout.addWidget(self.port_combo)
        
        # 刷新端口按钮
        self.refresh_port_btn = QPushButton(self.lang_manager.tr("刷新"))
        self.refresh_port_btn.clicked.connect(self.refresh_ports)
        control_layout.addWidget(self.refresh_port_btn)
        
        # 添加弹性空间
        control_layout.addStretch()
        
        # 导入按钮
        self.import_btn = QPushButton(self.lang_manager.tr("导入"))
        self.import_btn.clicked.connect(self.import_commands)
        control_layout.addWidget(self.import_btn)
        
        # 导出按钮
        self.export_btn = QPushButton(self.lang_manager.tr("导出"))
        self.export_btn.clicked.connect(self.export_commands)
        control_layout.addWidget(self.export_btn)
        
        main_layout.addLayout(control_layout)
    
    def refresh_ports(self):
        """刷新端口列表"""
        try:
            import serial.tools.list_ports
            self.port_combo.clear()
            ports = serial.tools.list_ports.comports()
            
            ports_list = list(ports)
            if not ports_list:
                self.port_combo.addItem("未检测到端口", None)
                logger.warning("未检测到任何串口")
            else:
                for port, desc, hwid in sorted(ports_list):
                    self.port_combo.addItem(f"{port} - {desc}", port)
                logger.debug(f"找到 {len(ports_list)} 个端口")
                
        except ImportError:
            QMessageBox.critical(self, self.lang_manager.tr("错误"), 
                              "需要安装pyserial库\npip install pyserial")
            self.port_combo.clear()
            self.port_combo.addItem("请先安装pyserial", None)
            logger.error("需要安装pyserial库")
        except Exception as e:
            logger.exception("刷新端口失败")
            self.port_combo.clear()
            self.port_combo.addItem(f"刷新失败: {str(e)}", None)
    
    def send_command(self):
        """发送AT命令"""
        command = self.command_input.text().strip()
        if not command:
            return
        
        # 发送命令
        self.send_at_command_directly(command)
        
        # 清空输入框
        self.command_input.clear()
        
        # 确保焦点回到输入框，方便连续输入
        self.command_input.setFocus()
    
    def send_at_command_directly(self, command):
        """直接发送AT命令"""
        port = self.port_combo.currentData()
        if not port:
            QMessageBox.warning(self, self.lang_manager.tr("警告"), 
                              self.lang_manager.tr("请先选择端口"))
            return
        
        # 添加到输出
        self.append_output(f">>> {command}")
        
        # 在后台线程中执行命令
        worker = ATCommandWorker(port, command, parent=self)
        worker.output.connect(self.append_output)
        worker.start()
    
    def on_command_double_clicked(self, row, column):
        """双击命令时直接发送"""
        if row < 0 or row >= len(self.at_commands):
            return
        
        command = self.at_commands[row]["command"]
        self.send_at_command_directly(command)
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu(self)
        
        add_action = menu.addAction(self.lang_manager.tr("添加"))
        add_action.triggered.connect(self.add_command)
        
        # 检查是否有选中的行
        if self.commands_table.selectedItems():
            edit_action = menu.addAction(self.lang_manager.tr("编辑"))
            edit_action.triggered.connect(self.edit_command)
            
            delete_action = menu.addAction(self.lang_manager.tr("删除"))
            delete_action.triggered.connect(self.delete_command)
            
            menu.addSeparator()
            
            # 上移/下移选项
            selected_row = self.commands_table.currentRow()
            if selected_row > 0:
                move_up_action = menu.addAction(self.lang_manager.tr("上移"))
                move_up_action.triggered.connect(self.move_command_up)
            
            if selected_row < self.commands_table.rowCount() - 1:
                move_down_action = menu.addAction(self.lang_manager.tr("下移"))
                move_down_action.triggered.connect(self.move_command_down)
        
        menu.exec_(self.commands_table.viewport().mapToGlobal(position))
    
    def add_command(self):
        """添加AT命令"""
        dialog = AddEditCommandDialog(self, is_edit=False)
        if dialog.exec_() == QDialog.Accepted:
            name, command = dialog.get_data()
            if name and command:
                # 检查名称是否已存在
                if any(cmd["name"] == name for cmd in self.at_commands):
                    QMessageBox.warning(self, self.lang_manager.tr("警告"), 
                                      self.lang_manager.tr(f"命令名称 '{name}' 已存在"))
                    return
                self.at_commands.append({"name": name, "command": command})
                self.save_commands()
                self.refresh_commands_table()
    
    def edit_command(self):
        """编辑AT命令"""
        selected_row = self.commands_table.currentRow()
        if selected_row < 0 or selected_row >= len(self.at_commands):
            return
        
        cmd = self.at_commands[selected_row]
        name = cmd["name"]
        command = cmd["command"]
        
        dialog = AddEditCommandDialog(self, is_edit=True, name=name, command=command)
        if dialog.exec_() == QDialog.Accepted:
            new_name, new_command = dialog.get_data()
            if new_name and new_command:
                # 检查新名称是否与其他命令冲突
                if new_name != name and any(cmd["name"] == new_name for cmd in self.at_commands):
                    QMessageBox.warning(self, self.lang_manager.tr("警告"), 
                                      self.lang_manager.tr(f"命令名称 '{new_name}' 已存在"))
                    return
                # 更新命令
                self.at_commands[selected_row] = {"name": new_name, "command": new_command}
                self.save_commands()
                self.refresh_commands_table()
    
    def delete_command(self):
        """删除AT命令"""
        selected_row = self.commands_table.currentRow()
        if selected_row < 0 or selected_row >= len(self.at_commands):
            return
        
        cmd = self.at_commands[selected_row]
        name = cmd["name"]
        
        reply = QMessageBox.question(
            self,
            self.lang_manager.tr("确认删除"),
            self.lang_manager.tr(f"确定要删除命令 '{name}' 吗？"),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.at_commands.pop(selected_row)
            self.save_commands()
            self.refresh_commands_table()
    
    def move_command_up(self):
        """上移命令"""
        selected_row = self.commands_table.currentRow()
        if selected_row <= 0 or selected_row >= len(self.at_commands):
            return
        
        # 交换位置
        self.at_commands[selected_row], self.at_commands[selected_row - 1] = \
            self.at_commands[selected_row - 1], self.at_commands[selected_row]
        
        self.save_commands()
        self.refresh_commands_table()
        
        # 保持选中状态
        self.commands_table.selectRow(selected_row - 1)
    
    def move_command_down(self):
        """下移命令"""
        selected_row = self.commands_table.currentRow()
        if selected_row < 0 or selected_row >= len(self.at_commands) - 1:
            return
        
        # 交换位置
        self.at_commands[selected_row], self.at_commands[selected_row + 1] = \
            self.at_commands[selected_row + 1], self.at_commands[selected_row]
        
        self.save_commands()
        self.refresh_commands_table()
        
        # 保持选中状态
        self.commands_table.selectRow(selected_row + 1)
    
    def refresh_commands_table(self):
        """刷新命令列表"""
        # 如果正在更新顺序，不执行刷新（但允许强制刷新）
        if hasattr(self, '_updating_order') and self._updating_order:
            # 检查是否是强制刷新（通过临时设置标志来绕过检查）
            if not getattr(self, '_force_refresh', False):
                return
        
        try:
            # 清除强制刷新标志
            self._force_refresh = False
            
            # 清空表格
            self.commands_table.setRowCount(0)
            
            # 重新填充表格
            for cmd in self.at_commands:
                row = self.commands_table.rowCount()
                self.commands_table.insertRow(row)
                
                name_item = QTableWidgetItem(cmd["name"])
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)  # 禁止编辑
                self.commands_table.setItem(row, 0, name_item)
                
                command_item = QTableWidgetItem(cmd["command"])
                command_item.setFlags(command_item.flags() & ~Qt.ItemIsEditable)  # 禁止编辑
                self.commands_table.setItem(row, 1, command_item)
        except Exception as e:
            logger.exception(f"刷新命令表格失败: {e}")
    
    def _sync_data_from_table(self):
        """根据表格当前顺序同步数据列表"""
        # 防止递归调用
        if hasattr(self, '_updating_order') and self._updating_order:
            return
            
        self._updating_order = True
        try:
            # 根据表格行的顺序重新排列数据
            new_commands = []
            used_indices = set()  # 记录已使用的索引，避免重复
            
            for row in range(self.commands_table.rowCount()):
                name_item = self.commands_table.item(row, 0)
                command_item = self.commands_table.item(row, 1)
                if name_item and command_item:
                    name = name_item.text()
                    command = command_item.text()
                    
                    # 在原始列表中查找对应的命令（使用索引避免重复）
                    found = False
                    for idx, cmd in enumerate(self.at_commands):
                        if idx not in used_indices and cmd["name"] == name and cmd["command"] == command:
                            new_commands.append(cmd)
                            used_indices.add(idx)
                            found = True
                            break
                    
                    # 如果没找到，创建一个新的（防止数据丢失）
                    if not found:
                        logger.warning(f"未找到匹配的命令: {name} - {command}")
                        new_commands.append({"name": name, "command": command})
            
            # 更新数据列表
            if len(new_commands) > 0:
                self.at_commands = new_commands
                self.save_commands()
                logger.debug(f"数据同步成功，共 {len(new_commands)} 条命令")
        except Exception as e:
            logger.exception(f"同步数据失败: {e}")
        finally:
            self._updating_order = False
    
    def import_commands(self):
        """导入AT命令列表"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.lang_manager.tr("导入AT命令"),
            "",
            self.lang_manager.tr("JSON文件 (*.json)")
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_data = json.load(f)
                    
                    # 兼容旧格式（字典）和新格式（列表）
                    if isinstance(imported_data, dict):
                        # 旧格式：转换为新格式
                        imported_commands = [{"name": name, "command": cmd} 
                                           for name, cmd in imported_data.items()]
                    elif isinstance(imported_data, list):
                        # 新格式：直接使用
                        imported_commands = imported_data
                    else:
                        raise ValueError("不支持的JSON格式")
                    
                    # 合并到现有列表（追加到末尾）
                    self.at_commands.extend(imported_commands)
                    self.save_commands()
                    self.refresh_commands_table()
                    QMessageBox.information(self, self.lang_manager.tr("成功"), 
                                          self.lang_manager.tr("导入成功"))
            except Exception as e:
                QMessageBox.critical(self, self.lang_manager.tr("错误"), 
                                    self.lang_manager.tr(f"导入失败: {str(e)}"))
                logger.exception(self.lang_manager.tr("导入AT命令失败"))
    
    def export_commands(self):
        """导出AT命令列表"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.lang_manager.tr("导出AT命令"),
            "at_commands.json",
            self.lang_manager.tr("JSON文件 (*.json)")
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.at_commands, f, ensure_ascii=False, indent=2)
                    QMessageBox.information(self, self.lang_manager.tr("成功"), 
                                          self.lang_manager.tr("导出成功"))
            except Exception as e:
                QMessageBox.critical(self, self.lang_manager.tr("错误"), 
                                    self.lang_manager.tr(f"导出失败: {str(e)}"))
                logger.exception(self.lang_manager.tr("导出AT命令失败"))
    
    def append_output(self, text):
        """追加输出文本，使用颜色区分输入和输出"""
        cursor = self.output_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.output_text.setTextCursor(cursor)
        
        # 根据文本前缀设置颜色
        format = QTextCharFormat()
        
        if text.startswith(">>>"):
            # 发送的命令 - 使用蓝色
            format.setForeground(QColor("#4A9EFF"))  # 亮蓝色
            format.setFontWeight(600)  # 半粗体
        elif text.startswith("<<<"):
            # 接收的响应 - 使用绿色
            format.setForeground(QColor("#52C41A"))  # 亮绿色
        elif "错误" in text or text.startswith("错误"):
            # 错误信息 - 使用红色
            format.setForeground(QColor("#FF4D4F"))  # 红色
        else:
            # 其他信息 - 使用默认颜色
            format.setForeground(QColor("#8C8C8C"))  # 灰色
        
        # 应用格式
        cursor.setCharFormat(format)
        
        # 插入文本
        cursor.insertText(text + "\n")
        
        # 重置光标位置
        cursor.movePosition(QTextCursor.End)
        self.output_text.setTextCursor(cursor)
    
    def clear_output(self):
        """清除输出区域"""
        self.output_text.clear()
    
    def _get_config_file_path(self):
        """获取配置文件路径，兼容exe和开发环境"""
        # 统一保存到 ~/.netui/ 目录，与其他配置保持一致
        user_config_dir = os.path.expanduser('~/.netui')
        os.makedirs(user_config_dir, exist_ok=True)
        return os.path.join(user_config_dir, 'at_commands.json')
    
    def save_commands(self):
        """保存AT命令列表"""
        file_path = self._get_config_file_path()
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.at_commands, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.exception(self.lang_manager.tr("保存AT命令失败"))
    
    def load_commands(self):
        """加载AT命令列表"""
        file_path = self._get_config_file_path()
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 兼容旧格式（字典）和新格式（列表）
                    if isinstance(data, dict):
                        # 旧格式：转换为新格式（有序列表）
                        self.at_commands = [{"name": name, "command": cmd} 
                                           for name, cmd in data.items()]
                        # 保存为新格式以便后续使用
                        self.save_commands()
                    elif isinstance(data, list):
                        # 新格式：直接使用
                        self.at_commands = data
                    else:
                        logger.warning("AT命令文件格式不正确，使用空列表")
                        self.at_commands = []
            except Exception as e:
                logger.exception(self.lang_manager.tr("加载AT命令失败"))
                self.at_commands = []
        else:
            self.at_commands = []


class ATCommandWorker(QThread):
    """AT命令工作线程"""
    
    output = pyqtSignal(str)
    
    def __init__(self, port, command, parent=None):
        super().__init__(parent)
        self.port = port
        self.command = command
        
        # 从父窗口获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager.get_instance()
    
    def run(self):
        """执行AT命令"""
        try:
            import serial
            import time
            
            # 判断命令类型，设置不同的超时时间
            command_upper = self.command.upper().strip()
            is_query_command = command_upper.endswith('=?') or command_upper.endswith('?')
            is_cops_query = command_upper == 'AT+COPS=?' or command_upper == '+COPS=?'
            
            # 查询命令（如 AT+COPS=?）需要更长的超时时间，因为可能需要扫描网络
            if is_query_command:
                max_wait_time = 60.0  # 查询命令最多等待60秒
                read_timeout = 1.0    # 串口读取超时1秒
            else:
                max_wait_time = 10.0  # 普通命令最多等待10秒
                read_timeout = 0.5    # 串口读取超时0.5秒
            
            # AT+COPS=? 特殊处理：60秒内没有新数据也认为响应完成
            if is_cops_query:
                no_data_timeout = 60.0  # 60秒内没有新数据，认为响应完成
            else:
                no_data_timeout = 2.0   # 其他命令：2秒内没有新数据，认为响应完成
            
            # 打开串口
            ser = serial.Serial(self.port, 115200, timeout=read_timeout)
            
            # 清空输入缓冲区
            ser.reset_input_buffer()
            
            # 发送命令
            ser.write(f"{self.command}\r\n".encode())
            
            # 等待一小段时间让设备处理命令
            time.sleep(0.1)
            
            # 读取响应数据
            response = ""
            start_time = time.time()
            last_data_time = start_time
            
            while time.time() - start_time < max_wait_time:
                if ser.in_waiting:
                    # 读取所有可用的数据
                    data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                    if data:
                        response += data
                        last_data_time = time.time()
                        
                        # 检查是否收到完整的响应（通常以OK或ERROR结尾）
                        response_upper = response.upper()
                        if 'OK' in response_upper or 'ERROR' in response_upper:
                            # 再等待一小段时间，确保所有数据都已接收
                            time.sleep(0.2)
                            if ser.in_waiting:
                                response += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                            break
                else:
                    # 如果没有数据，检查是否已经有响应
                    if response:
                        # 如果已经有响应且超过指定时间没有新数据，认为响应完成
                        if time.time() - last_data_time > no_data_timeout:
                            break
                    time.sleep(0.1)  # 等待一下再检查
            
            # 最后再读取一次确保所有数据都被读取
            if ser.in_waiting:
                response += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            
            ser.close()
            
            # 清理响应文本
            response = response.strip()
            
            if not response:
                if time.time() - start_time >= max_wait_time:
                    response = f"(超时：等待超过{int(max_wait_time)}秒无响应)"
                else:
                    response = "(无响应)"
            
            # 发送响应信号
            self.output.emit(f"<<< {response}")
            
        except ImportError:
            self.output.emit("错误: 需要安装pyserial库，请运行: pip install pyserial")
            logger.exception("pyserial未安装")
        except Exception as e:
            error_msg = f"执行AT命令失败: {str(e)}"
            self.output.emit(error_msg)
            logger.exception(error_msg)

