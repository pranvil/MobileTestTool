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
                             QFormLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDateTime
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor, QFont
from core.debug_logger import logger


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
        
        # AT命令列表（名称 -> 命令）
        self.at_commands = {}
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
        
        self.commands_table = QTableWidget()
        self.commands_table.setColumnCount(2)
        self.commands_table.setHorizontalHeaderLabels([
            self.lang_manager.tr("命令名称"), 
            self.lang_manager.tr("AT命令")
        ])
        self.commands_table.horizontalHeader().setStretchLastSection(True)
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
        splitter.setSizes([500, 400])
        
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
        command_item = self.commands_table.item(row, 1)
        if command_item:
            command = command_item.text()
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
        
        menu.exec_(self.commands_table.viewport().mapToGlobal(position))
    
    def add_command(self):
        """添加AT命令"""
        dialog = AddEditCommandDialog(self, is_edit=False)
        if dialog.exec_() == QDialog.Accepted:
            name, command = dialog.get_data()
            if name and command:
                self.at_commands[name] = command
                self.save_commands()
                self.refresh_commands_table()
    
    def edit_command(self):
        """编辑AT命令"""
        selected_row = self.commands_table.currentRow()
        if selected_row < 0:
            return
        
        name_item = self.commands_table.item(selected_row, 0)
        if not name_item:
            return
        
        name = name_item.text()
        if name not in self.at_commands:
            return
        
        command = self.at_commands[name]
        dialog = AddEditCommandDialog(self, is_edit=True, name=name, command=command)
        if dialog.exec_() == QDialog.Accepted:
            new_name, new_command = dialog.get_data()
            if new_name and new_command:
                # 删除旧命令
                if name in self.at_commands:
                    del self.at_commands[name]
                # 添加新命令
                self.at_commands[new_name] = new_command
                self.save_commands()
                self.refresh_commands_table()
    
    def delete_command(self):
        """删除AT命令"""
        selected_row = self.commands_table.currentRow()
        if selected_row < 0:
            return
        
        name_item = self.commands_table.item(selected_row, 0)
        if not name_item:
            return
        
        name = name_item.text()
        
        reply = QMessageBox.question(
            self,
            self.lang_manager.tr("确认删除"),
            self.lang_manager.tr(f"确定要删除命令 '{name}' 吗？"),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if name in self.at_commands:
                del self.at_commands[name]
                self.save_commands()
                self.refresh_commands_table()
    
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
                    imported_commands = json.load(f)
                    self.at_commands.update(imported_commands)
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
    
    def refresh_commands_table(self):
        """刷新命令列表"""
        self.commands_table.setRowCount(0)
        
        for name, command in self.at_commands.items():
            row = self.commands_table.rowCount()
            self.commands_table.insertRow(row)
            
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)  # 禁止编辑
            self.commands_table.setItem(row, 0, name_item)
            
            command_item = QTableWidgetItem(command)
            command_item.setFlags(command_item.flags() & ~Qt.ItemIsEditable)  # 禁止编辑
            self.commands_table.setItem(row, 1, command_item)
    
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
                    self.at_commands = json.load(f)
            except Exception as e:
                logger.exception(self.lang_manager.tr("加载AT命令失败"))
                self.at_commands = {}


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
            
            # 打开串口，使用较短的超时时间以提高响应速度
            ser = serial.Serial(self.port, 115200, timeout=0.5)
            
            # 清空输入缓冲区
            ser.reset_input_buffer()
            
            # 发送命令
            ser.write(f"{self.command}\r\n".encode())
            
            # 等待一小段时间让设备处理命令（通常AT响应很快）
            time.sleep(0.05)
            
            # 读取所有可用的响应数据
            response = ""
            start_time = time.time()
            max_wait_time = 2.0  # 最多等待2秒
            
            while time.time() - start_time < max_wait_time:
                if ser.in_waiting:
                    # 读取所有可用的数据
                    data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                    if data:
                        response += data
                else:
                    # 如果没有数据，检查是否已经有响应（AT通常响应很快）
                    if response:
                        # 如果有部分响应，再等待一小段时间看是否有更多数据
                        time.sleep(0.05)
                        if not ser.in_waiting:
                            break  # 没有更多数据了
                    else:
                        time.sleep(0.01)  # 如果还没有响应，稍微等待一下
            
            # 再读取一次确保所有数据都被读取
            if ser.in_waiting:
                response += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            
            ser.close()
            
            # 清理响应文本
            response = response.strip()
            
            if not response:
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

