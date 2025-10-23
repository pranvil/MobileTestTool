#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义按钮配置对话框
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QLabel, QLineEdit, QComboBox,
                             QTextEdit, QCheckBox, QFileDialog, QGroupBox,
                             QFormLayout, QScrollArea, QWidget, QTextBrowser)
from PyQt5.QtCore import Qt
from core.debug_logger import logger


class CustomButtonDialog(QDialog):
    """自定义按钮管理对话框"""
    
    def __init__(self, button_manager, parent=None):
        super().__init__(parent)
        self.button_manager = button_manager
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.setWindowTitle(self.tr("自定义按钮管理"))
        self.setModal(True)
        self.resize(900, 600)
        
        self.setup_ui()
        self.load_buttons()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 顶部说明
        info_text = (self.tr("💡 在此配置自定义命令按钮，按钮将显示在指定的Tab和卡片中。") +
                    self.tr("adb命令会自动加上 'adb -s {device}' 前缀。"))
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #17a2b8; padding: 10px; background: #d1ecf1; border-radius: 4px;")
        layout.addWidget(info_label)
        
        # 按钮列表表格
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([self.tr('名称'), self.tr('类型'), self.tr('命令'), self.tr('所在Tab'), self.tr('所在卡片'), self.tr('启用'), self.tr('描述')])
        
        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)
        
        # 底部按钮区
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
        
        self.import_btn = QPushButton("📥 " + self.tr("导入"))
        self.import_btn.clicked.connect(self.import_buttons)
        button_layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("📤 " + self.tr("导出"))
        self.export_btn.clicked.connect(self.export_buttons)
        button_layout.addWidget(self.export_btn)
        
        # 移除重复的备份/恢复按钮，只保留导入/导出
        
        button_layout.addStretch()
        
        self.help_btn = QPushButton("❓ " + self.tr("帮助"))
        self.help_btn.clicked.connect(self.show_help)
        button_layout.addWidget(self.help_btn)
        
        self.close_btn = QPushButton(self.tr("关闭"))
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
            
            self.table.setItem(row, 0, QTableWidgetItem(btn.get('name', '')))
            self.table.setItem(row, 1, QTableWidgetItem(type_display))
            self.table.setItem(row, 2, QTableWidgetItem(btn.get('command', '')))
            self.table.setItem(row, 3, QTableWidgetItem(btn.get('tab', '')))
            self.table.setItem(row, 4, QTableWidgetItem(btn.get('card', '')))
            self.table.setItem(row, 5, QTableWidgetItem('✓' if btn.get('enabled', True) else '✗'))
            self.table.setItem(row, 6, QTableWidgetItem(btn.get('description', '')))
            
            # 存储按钮ID
            self.table.item(row, 0).setData(Qt.UserRole, btn.get('id'))
    
    def add_button(self):
        """添加按钮"""
        dialog = ButtonEditDialog(self.button_manager, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            button_data = dialog.get_button_data()
            if self.button_manager.add_button(button_data):
                self.load_buttons()
                QMessageBox.information(self, self.tr("成功"), self.tr("按钮添加成功！"))
            else:
                QMessageBox.warning(self, self.tr("失败"), self.tr("按钮添加失败，请检查日志"))
    
    def edit_button(self):
        """编辑按钮"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择要编辑的按钮"))
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
                    QMessageBox.information(self, self.tr("成功"), self.tr("按钮更新成功！"))
                else:
                    QMessageBox.warning(self, self.tr("失败"), self.tr("按钮更新失败，请检查日志"))
    
    def delete_button(self):
        """删除按钮"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择要删除的按钮"))
            return
        
        button_name = self.table.item(current_row, 0).text()
        reply = QMessageBox.question(
            self, self.tr("确认删除"),
            f"{self.tr('确定要删除按钮')} '{button_name}' {self.tr('吗？')}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            button_id = self.table.item(current_row, 0).data(Qt.UserRole)
            if self.button_manager.delete_button(button_id):
                self.load_buttons()

            else:
                QMessageBox.warning(self, self.tr("失败"), self.tr("按钮删除失败，请检查日志"))
    
    def import_buttons(self):
        """导入按钮配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("导入按钮配置"), "",
            self.tr("JSON文件 (*.json);;所有文件 (*.*)")
        )
        
        if file_path:
            if self.button_manager.import_buttons(file_path):
                self.load_buttons()
                QMessageBox.information(self, self.tr("成功"), self.tr("按钮配置导入成功！"))
            else:
                QMessageBox.warning(self, self.tr("失败"), self.tr("按钮配置导入失败，请检查文件格式"))
    
    def export_buttons(self):
        """导出按钮配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.tr("导出按钮配置"), "custom_buttons.json",
            self.tr("JSON文件 (*.json);;所有文件 (*.*)")
        )
        
        if file_path:
            if self.button_manager.export_buttons(file_path):
                QMessageBox.information(self, self.tr("导出成功"), f"{self.tr('按钮配置导出成功！')}\n{file_path}")
            else:
                QMessageBox.warning(self, self.tr("导出失败"), self.tr("按钮配置导出失败，请检查日志"))
    
    def show_help(self):
        """显示帮助对话框"""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("📖 " + self.tr("自定义按钮使用帮助"))
        help_dialog.resize(800, 600)
        
        layout = QVBoxLayout(help_dialog)
        
        # 创建文本浏览器
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        
        # 帮助文档内容（与ButtonEditDialog中的相同）
        help_text = """
        <html>
        <head>
            <style>
                body { font-family: "Microsoft YaHei", Arial, sans-serif; line-height: 1.6; }
                h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
                h2 { color: #34495e; margin-top: 20px; }
                h3 { 
                    color: #3498db; 
                    background-color: #2c3e50; 
                    margin-top: 15px; 
                    margin-bottom: 10px;
                    padding: 8px 15px; 
                    border-radius: 5px; 
                    font-weight: bold;
                    font-size: 1.1em;
                }
                .type-section { 
                    background: #ecf0f1; 
                    padding: 15px; 
                    margin: 10px 0; 
                    border-radius: 5px;
                    border-left: 4px solid #3498db;
                }
                .example { 
                    background: #f8f9fa; 
                    color: #2c3e50;
                    padding: 10px; 
                    margin: 10px 0; 
                    border-radius: 3px;
                    border: 1px solid #dee2e6;
                    font-family: "Consolas", monospace;
                    font-weight: normal;
                }
                .warning { 
                    background: #f8d7da; 
                    color: #721c24;
                    padding: 10px; 
                    margin: 10px 0; 
                    border-radius: 3px;
                    border-left: 4px solid #dc3545;
                }
                .tip { 
                    background: #d1ecf1; 
                    color: #0c5460;
                    padding: 10px; 
                    margin: 10px 0; 
                    border-radius: 3px;
                    border-left: 4px solid #17a2b8;
                }
                ul { margin-left: 20px; }
                li { margin: 5px 0; }
            </style>
        </head>
        <body>
            <h1>🔧 自定义按钮使用指南</h1>
            
            <div class="tip">
                <strong>💡 提示：</strong>自定义按钮功能允许您创建各种类型的快捷操作按钮，支持ADB命令、Python脚本、打开文件等多种功能。
            </div>
            
            <h2>📋 按钮类型说明</h2>
            
            <div class="type-section">
                <h3>① ADB命令</h3>
                <p><strong>用途：</strong>执行ADB命令来操作Android设备</p>
                <p><strong>输入格式：</strong>直接输入ADB命令内容，<strong>不需要</strong>加 "adb -s {device}" 前缀</p>
                <p><strong>示例：</strong></p>
                <div class="example">
                    命令/路径: adb reboot<br>
                    说明: 重启设备<br><br>
                    
                    命令/路径: adb shell dumpsys battery<br>
                    说明: 查看电池信息<br><br>
                    
                    命令/路径: logcat -c<br>
                    说明: 清除logcat缓存
                </div>
                <div class="warning">
                    <strong>⚠️ 注意：</strong>某些危险命令（如 push、pull、install、uninstall）被禁止使用，以确保系统安全。
                </div>
            </div>
            
            <div class="type-section">
                <h3>② Python脚本</h3>
                <p><strong>用途：</strong>执行自定义Python代码片段</p>
                <p><strong>输入格式：</strong></p>
                <ul>
                    <li><strong>命令/路径：</strong>可选，用于描述脚本功能</li>
                    <li><strong>Python脚本区域：</strong>必填，输入要执行的Python代码</li>
                </ul>
                <p><strong>可用模块：</strong>datetime、platform、os、json、math、random、time</p>
                <p><strong>示例：</strong></p>
                <div class="example">
                    # 获取系统信息<br>
                    import platform<br>
                    print(f"系统: {platform.system()}")<br>
                    print(f"版本: {platform.version()}")<br><br>
                    
                    # 生成随机数<br>
                    import random<br>
                    print(f"随机数: {random.randint(1, 100)}")<br><br>
                    
                    # 获取当前时间<br>
                    import datetime<br>
                    print(f"当前时间: {datetime.datetime.now()}")
                </div>
                <div class="tip">
                    <strong>💡 提示：</strong>Python脚本在沙箱环境中执行，输出会显示在日志区域。
                </div>
            </div>
            
            <div class="type-section">
                <h3>③ 打开文件</h3>
                <p><strong>用途：</strong>使用默认程序打开指定文件或文件夹</p>
                <p><strong>输入格式：</strong>输入完整的文件路径，或点击self.tr("浏览文件")按钮选择</p>
                <p><strong>示例：</strong></p>
                <div class="example">
                    C:\\Users\\用户名\\Desktop\\测试报告.docx<br>
                    C:\\Users\\用户名\\Documents\\项目文档.pdf<br>
                    D:\\工作文件夹
                </div>
            </div>
            
            <div class="type-section">
                <h3>④ 运行程序</h3>
                <p><strong>用途：</strong>启动指定的可执行程序</p>
                <p><strong>输入格式：</strong>输入完整的程序路径，或点击self.tr("浏览文件")按钮选择</p>
                <p><strong>示例：</strong></p>
                <div class="example">
                    C:\\Program Files\\Notepad++\\notepad++.exe<br>
                    C:\\Windows\\System32\\calc.exe<br>
                    D:\\Tools\\adb工具\\adb.exe
                </div>
            </div>
            
            <div class="type-section">
                <h3>⑤ 系统命令</h3>
                <p><strong>用途：</strong>执行Windows/Linux/Mac系统命令</p>
                <p><strong>输入格式：</strong>直接输入系统命令</p>
                <p><strong>示例：</strong></p>
                <div class="example">
                    ipconfig /all<br>
                    dir C:\\<br>
                    ping 8.8.8.8 -n 4
                </div>
                <div class="warning">
                    <strong>⚠️ 注意：</strong>系统命令会在30秒后超时，请避免使用长时间运行的命令。
                </div>
            </div>
            
            <h2>🎯 按钮配置说明</h2>
            
            <ul>
                <li><strong>按钮名称：</strong>显示在界面上的按钮文字（必填）</li>
                <li><strong>按钮类型：</strong>选择按钮执行的操作类型（必选）</li>
                <li><strong>命令/路径：</strong>根据按钮类型填写相应内容（部分类型必填）</li>
                <li><strong>描述：</strong>按钮的详细说明，鼠标悬停时显示（可选）</li>
                <li><strong>所在Tab：</strong>按钮将显示在哪个选项卡（必选）</li>
                <li><strong>所在卡片：</strong>按钮将显示在哪个功能卡片中（必选）</li>
                <li><strong>启用此按钮：</strong>是否立即启用该按钮（可选）</li>
            </ul>
            
            <h2>✨ 使用技巧</h2>
            
            <ul>
                <li>为按钮起一个简洁明了的名称，方便快速识别</li>
                <li>合理使用描述字段，提供更多操作说明</li>
                <li>将相关功能的按钮放在同一个卡片中，便于管理</li>
                <li>对于常用操作，可以创建多个快捷按钮</li>
                <li>使用self.tr("导出")功能可以备份您的按钮配置</li>
                <li>使用self.tr("导入")功能可以在不同设备间共享配置</li>
            </ul>
            
            <div class="tip">
                <strong>💡 小贴士：</strong>如果不确定按钮是否正确配置，可以先测试一次，查看日志区域的输出结果。
            </div>
            
        </body>
        </html>
        """
        
        browser.setHtml(help_text)
        layout.addWidget(browser)
        
        # 关闭按钮
        close_btn = QPushButton(self.tr("关闭"))
        close_btn.clicked.connect(help_dialog.accept)
        layout.addWidget(close_btn)
        
        help_dialog.exec_()


class ButtonEditDialog(QDialog):
    """按钮编辑对话框"""
    
    def __init__(self, button_manager, button_data=None, parent=None):
        super().__init__(parent)
        self.button_manager = button_manager
        self.button_data = button_data or {}
        self.is_edit = button_data is not None
        
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        
        self.setWindowTitle(self.tr("编辑按钮") if self.is_edit else self.tr("添加按钮"))
        self.setModal(True)
        self.resize(700, 600)  # 增加宽度和高度
        
        # 设置窗口标志，显示帮助按钮
        self.setWindowFlags(self.windowFlags() | Qt.WindowContextHelpButtonHint)
        
        self.setup_ui()
        
        if self.is_edit:
            self.load_data()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def event(self, event):
        """处理事件，包括帮助按钮点击"""
        if event.type() == event.EnterWhatsThisMode:
            # 点击帮助按钮时显示帮助对话框
            self.show_help_dialog()
            return True
        return super().event(event)
    
    def show_help_dialog(self):
        """显示帮助对话框"""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("📖 " + self.tr("自定义按钮使用帮助"))
        help_dialog.resize(800, 600)
        
        layout = QVBoxLayout(help_dialog)
        
        # 创建文本浏览器
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        
        # 帮助文档内容
        help_text = """
        <html>
        <head>
            <style>
                body { font-family: "Microsoft YaHei", Arial, sans-serif; line-height: 1.6; }
                h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
                h2 { color: #34495e; margin-top: 20px; }
                h3 { 
                    color: #3498db; 
                    background-color: #2c3e50; 
                    margin-top: 15px; 
                    margin-bottom: 10px;
                    padding: 8px 15px; 
                    border-radius: 5px; 
                    font-weight: bold;
                    font-size: 1.1em;
                }
                .type-section { 
                    background: #ecf0f1; 
                    padding: 15px; 
                    margin: 10px 0; 
                    border-radius: 5px;
                    border-left: 4px solid #3498db;
                }
                .example { 
                    background: #f8f9fa; 
                    color: #2c3e50;
                    padding: 10px; 
                    margin: 10px 0; 
                    border-radius: 3px;
                    border: 1px solid #dee2e6;
                    font-family: "Consolas", monospace;
                    font-weight: normal;
                }
                .warning { 
                    background: #f8d7da; 
                    color: #721c24;
                    padding: 10px; 
                    margin: 10px 0; 
                    border-radius: 3px;
                    border-left: 4px solid #dc3545;
                }
                .tip { 
                    background: #d1ecf1; 
                    color: #0c5460;
                    padding: 10px; 
                    margin: 10px 0; 
                    border-radius: 3px;
                    border-left: 4px solid #17a2b8;
                }
                ul { margin-left: 20px; }
                li { margin: 5px 0; }
            </style>
        </head>
        <body>
            <h1>🔧 自定义按钮使用指南</h1>
            
            <div class="tip">
                <strong>💡 提示：</strong>自定义按钮功能允许您创建各种类型的快捷操作按钮，支持ADB命令、Python脚本、打开文件等多种功能。
            </div>
            
            <h2>📋 按钮类型说明</h2>
            
            <div class="type-section">
                <h3>① ADB命令</h3>
                <p><strong>用途：</strong>执行ADB命令来操作Android设备</p>
                <p><strong>输入格式：</strong>直接输入ADB命令内容，<strong>不需要</strong>加 "adb -s {device}" 前缀</p>
                <p><strong>示例：</strong></p>
                <div class="example">
                    命令/路径: adb reboot<br>
                    说明: 重启设备<br><br>
                    
                    命令/路径: shell dumpsys battery<br>
                    说明: 查看电池信息<br><br>
                    
                    命令/路径: logcat -c<br>
                    说明: 清除logcat缓存
                </div>
                <div class="warning">
                    <strong>⚠️ 注意：</strong>某些危险命令（如 push、pull、install、uninstall）被禁止使用，以确保系统安全。
                </div>
            </div>
            
            <div class="type-section">
                <h3>② Python脚本</h3>
                <p><strong>用途：</strong>执行自定义Python代码片段</p>
                <p><strong>输入格式：</strong></p>
                <ul>
                    <li><strong>命令/路径：</strong>可选，用于描述脚本功能</li>
                    <li><strong>Python脚本区域：</strong>必填，输入要执行的Python代码</li>
                </ul>
                <p><strong>可用模块：</strong>datetime、platform、os、json、math、random、time</p>
                <p><strong>示例：</strong></p>
                <div class="example">
                    # 获取系统信息<br>
                    import platform<br>
                    print(f"系统: {platform.system()}")<br>
                    print(f"版本: {platform.version()}")<br><br>
                    
                    # 生成随机数<br>
                    import random<br>
                    print(f"随机数: {random.randint(1, 100)}")<br><br>
                    
                    # 获取当前时间<br>
                    import datetime<br>
                    print(f"当前时间: {datetime.datetime.now()}")
                </div>
                <div class="tip">
                    <strong>💡 提示：</strong>Python脚本在沙箱环境中执行，输出会显示在日志区域。
                </div>
            </div>
            
            <div class="type-section">
                <h3>③ 打开文件</h3>
                <p><strong>用途：</strong>使用默认程序打开指定文件或文件夹</p>
                <p><strong>输入格式：</strong>输入完整的文件路径，或点击self.tr("浏览文件")按钮选择</p>
                <p><strong>示例：</strong></p>
                <div class="example">
                    C:\\Users\\用户名\\Desktop\\测试报告.docx<br>
                    C:\\Users\\用户名\\Documents\\项目文档.pdf<br>
                    D:\\工作文件夹
                </div>
            </div>
            
            <div class="type-section">
                <h3>④ 运行程序</h3>
                <p><strong>用途：</strong>启动指定的可执行程序</p>
                <p><strong>输入格式：</strong>输入完整的程序路径，或点击self.tr("浏览文件")按钮选择</p>
                <p><strong>示例：</strong></p>
                <div class="example">
                    C:\\Program Files\\Notepad++\\notepad++.exe<br>
                    C:\\Windows\\System32\\calc.exe<br>
                    D:\\Tools\\adb工具\\adb.exe
                </div>
            </div>
            
            <div class="type-section">
                <h3>⑤ 系统命令</h3>
                <p><strong>用途：</strong>执行Windows/Linux/Mac系统命令</p>
                <p><strong>输入格式：</strong>直接输入系统命令</p>
                <p><strong>示例：</strong></p>
                <div class="example">
                    ipconfig /all<br>
                    dir C:\\<br>
                    ping 8.8.8.8 -n 4
                </div>
                <div class="warning">
                    <strong>⚠️ 注意：</strong>系统命令会在30秒后超时，请避免使用长时间运行的命令。
                </div>
            </div>
            
            <h2>🎯 按钮配置说明</h2>
            
            <ul>
                <li><strong>按钮名称：</strong>显示在界面上的按钮文字（必填）</li>
                <li><strong>按钮类型：</strong>选择按钮执行的操作类型（必选）</li>
                <li><strong>命令/路径：</strong>根据按钮类型填写相应内容（部分类型必填）</li>
                <li><strong>描述：</strong>按钮的详细说明，鼠标悬停时显示（可选）</li>
                <li><strong>所在Tab：</strong>按钮将显示在哪个选项卡（必选）</li>
                <li><strong>所在卡片：</strong>按钮将显示在哪个功能卡片中（必选）</li>
                <li><strong>启用此按钮：</strong>是否立即启用该按钮（可选）</li>
            </ul>
            
            <h2>✨ 使用技巧</h2>
            
            <ul>
                <li>为按钮起一个简洁明了的名称，方便快速识别</li>
                <li>合理使用描述字段，提供更多操作说明</li>
                <li>将相关功能的按钮放在同一个卡片中，便于管理</li>
                <li>对于常用操作，可以创建多个快捷按钮</li>
                <li>使用self.tr("导出")功能可以备份您的按钮配置</li>
                <li>使用self.tr("导入")功能可以在不同设备间共享配置</li>
            </ul>
            
            <div class="tip">
                <strong>💡 小贴士：</strong>如果不确定按钮是否正确配置，可以先测试一次，查看日志区域的输出结果。
            </div>
            
        </body>
        </html>
        """
        
        browser.setHtml(help_text)
        layout.addWidget(browser)
        
        # 关闭按钮
        close_btn = QPushButton(self.tr("关闭"))
        close_btn.clicked.connect(help_dialog.accept)
        layout.addWidget(close_btn)
        
        help_dialog.exec_()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 创建滚动内容容器
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(5, 5, 5, 5)
        
        # 基本信息组
        basic_group = QGroupBox(self.tr("基本信息"))
        basic_layout = QFormLayout(basic_group)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(self.tr("例如：重启设备"))
        basic_layout.addRow(self.tr("按钮名称*:"), self.name_edit)
        
        # 按钮类型选择
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            self.tr("ADB命令"), self.tr("Python脚本"), self.tr("打开文件"), self.tr("运行程序"), self.tr("系统命令")
        ])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        basic_layout.addRow(self.tr("按钮类型*:"), self.type_combo)
        
        self.command_edit = QLineEdit()
        self.command_edit.setPlaceholderText(self.tr("adb reboot"))
        basic_layout.addRow(self.tr("命令/路径*:"), self.command_edit)
        
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText(self.tr("描述按钮的功能..."))
        self.description_edit.setMaximumHeight(80)
        basic_layout.addRow(self.tr("描述:"), self.description_edit)
        
        scroll_layout.addWidget(basic_group)
        
        # 高级设置组（用于Python脚本等）
        self.advanced_group = QGroupBox(self.tr("高级设置"))
        advanced_layout = QVBoxLayout(self.advanced_group)
        
        self.script_edit = QTextEdit()
        self.script_edit.setPlaceholderText(self.tr("输入Python脚本代码..."))
        self.script_edit.setMaximumHeight(200)  # 增加高度
        self.script_edit.setVisible(False)
        self.script_edit.textChanged.connect(self.update_preview)
        advanced_layout.addWidget(self.script_edit)
        
        self.file_browse_btn = QPushButton(self.tr("浏览文件"))
        self.file_browse_btn.clicked.connect(self.browse_file)
        self.file_browse_btn.setVisible(False)
        advanced_layout.addWidget(self.file_browse_btn)
        
        scroll_layout.addWidget(self.advanced_group)
        
        # 位置设置组
        position_group = QGroupBox(self.tr("显示位置"))
        position_layout = QFormLayout(position_group)
        
        self.tab_combo = QComboBox()
        self.tab_combo.addItems(self.button_manager.get_available_tabs())
        self.tab_combo.currentTextChanged.connect(self.on_tab_changed)
        position_layout.addRow(self.tr("所在Tab*:"), self.tab_combo)
        
        self.card_combo = QComboBox()
        position_layout.addRow(self.tr("所在卡片*:"), self.card_combo)
        
        self.enabled_check = QCheckBox(self.tr("启用此按钮"))
        self.enabled_check.setChecked(True)
        position_layout.addRow("", self.enabled_check)
        
        scroll_layout.addWidget(position_group)
        
        # 命令预览
        preview_group = QGroupBox(self.tr("命令预览"))
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
        
        scroll_layout.addWidget(preview_group)
        
        # 设置滚动区域的内容
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # 初始化Card列表
        self.on_tab_changed(self.tab_combo.currentText())
        
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
        
        # 初始预览
        self.update_preview()
    
    def on_tab_changed(self, tab_name):
        """Tab改变时更新Card列表"""
        self.card_combo.clear()
        cards = self.button_manager.get_available_cards(tab_name)
        self.card_combo.addItems(cards)
    
    def on_type_changed(self, type_text):
        """按钮类型改变时的处理"""
        type_map = {
            self.tr("ADB命令"): "adb",
            self.tr("Python脚本"): "python", 
            self.tr("打开文件"): "file",
            self.tr("运行程序"): "program",
            self.tr("系统命令"): "system"
        }
        
        button_type = type_map.get(type_text, "adb")
        
        # 更新输入框的占位符
        placeholders = {
            "adb": self.tr("adb reboot（不需要加 'adb -s {device}'）"),
            "python": self.tr("可选：脚本描述或文件名（如：系统信息收集）"),
            "file": self.tr("例如：C:\\Users\\用户名\\Desktop\\文件.txt"),
            "program": self.tr("例如：C:\\Program Files\\Notepad++\\notepad++.exe"),
            "system": self.tr("例如：dir 或 ls")
        }
        
        self.command_edit.setPlaceholderText(placeholders.get(button_type, ""))
        
        # 显示/隐藏高级设置
        if button_type == "python":
            self.script_edit.setVisible(True)
            self.script_edit.setMaximumHeight(300)  # 增加Python脚本编辑区域高度
            self.file_browse_btn.setVisible(False)
            self.advanced_group.setTitle(self.tr("Python脚本"))
            self.advanced_group.setVisible(True)
        elif button_type in ["file", "program"]:
            self.script_edit.setVisible(False)
            self.file_browse_btn.setVisible(True)
            self.advanced_group.setTitle(self.tr("文件选择"))
            self.advanced_group.setVisible(True)
        else:
            self.script_edit.setVisible(False)
            self.file_browse_btn.setVisible(False)
            self.advanced_group.setVisible(False)
    
    def browse_file(self):
        """浏览文件"""
        from PyQt5.QtWidgets import QFileDialog
        
        type_text = self.type_combo.currentText()
        
        if type_text == self.tr("打开文件"):
            file_path, _ = QFileDialog.getOpenFileName(
                self, self.tr("选择要打开的文件"), "",
                self.tr("所有文件 (*.*)")
            )
        elif type_text == self.tr("运行程序"):
            file_path, _ = QFileDialog.getOpenFileName(
                self, self.tr("选择要运行的程序"), "",
                self.tr("可执行文件 (*.exe);;所有文件 (*.*)")
            )
        else:
            file_path, _ = QFileDialog.getOpenFileName(
                self, self.tr("选择文件"), "",
                self.tr("所有文件 (*.*)")
            )
        
        if file_path:
            self.command_edit.setText(file_path)
    
    def update_preview(self):
        """更新命令预览"""
        command = self.command_edit.text().strip()
        button_type = self.type_combo.currentText()
        
        if command:
            if button_type == self.tr("ADB命令"):
                # ADB命令预览
                clean_command = command
                if clean_command.lower().startswith('adb '):
                    clean_command = clean_command[4:].strip()
                
                preview = f"{self.tr('adb -s {{设备ID}}')} {clean_command}"
                self.preview_label.setText(preview)
                
                # 检查ADB命令是否被阻止
                if not self.button_manager.validate_command(command):
                    reason = self.button_manager.get_blocked_reason(command)
                    if reason:
                        self.preview_label.setStyleSheet(
                            "background: #f8d7da; padding: 10px; "
                            "border: 1px solid #f5c6cb; border-radius: 4px; "
                            "color: #721c24; font-family: 'Consolas', 'Monaco', monospace;"
                        )
                        self.preview_label.setText(f"{self.tr('⚠️ 不支持的命令')}\n{reason}")
                        return
                    else:
                        self.preview_label.setStyleSheet(
                            "background: #f8d7da; padding: 10px; "
                            "border: 1px solid #f5c6cb; border-radius: 4px; "
                            "color: #721c24; font-family: 'Consolas', 'Monaco', monospace;"
                        )
                        self.preview_label.setText(f"{self.tr('⚠️ 命令验证失败')}")
                        return
            elif button_type == self.tr("Python脚本"):
                # Python脚本预览
                script = self.script_edit.toPlainText().strip()
                if script:
                    preview = f"{self.tr('执行Python脚本:')}\n{script[:100]}{'...' if len(script) > 100 else ''}"
                else:
                    preview = self.tr("Python脚本为空")
            elif button_type == self.tr("打开文件"):
                # 文件预览
                import os
                if os.path.exists(command):
                    preview = f"✅ {self.tr('将打开文件:')}\n{command}"
                else:
                    preview = f"⚠️ {self.tr('文件不存在:')}\n{command}"
            elif button_type == self.tr("运行程序"):
                # 程序预览
                import os
                if os.path.exists(command):
                    preview = f"✅ {self.tr('将运行程序:')}\n{command}"
                else:
                    preview = f"⚠️ {self.tr('程序不存在:')}\n{command}"
            elif button_type == self.tr("系统命令"):
                # 系统命令预览
                preview = f"{self.tr('将执行系统命令:')}\n{command}"
            
            # 设置正常样式
            self.preview_label.setStyleSheet(
                "background: #f8f9fa; padding: 10px; "
                "border: 1px solid #dee2e6; border-radius: 4px; "
                "font-family: 'Consolas', 'Monaco', monospace;"
            )
            self.preview_label.setText(preview)
        else:
            self.preview_label.setText(f"{self.tr('请输入')}{button_type}{self.tr('内容...')}")
    
    def load_data(self):
        """加载按钮数据"""
        self.name_edit.setText(self.button_data.get('name', ''))
        self.command_edit.setText(self.button_data.get('command', ''))
        self.description_edit.setPlainText(self.button_data.get('description', ''))
        
        # 加载按钮类型
        button_type = self.button_data.get('type', 'adb')
        type_map = {
            'adb': self.tr('ADB命令'),
            'python': self.tr('Python脚本'),
            'file': self.tr('打开文件'),
            'program': self.tr('运行程序'),
            'system': self.tr('系统命令')
        }
        type_text = type_map.get(button_type, self.tr('ADB命令'))
        index = self.type_combo.findText(type_text)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)
        
        # 加载Python脚本
        if button_type == 'python':
            script = self.button_data.get('script', '')
            self.script_edit.setPlainText(script)
        
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
        button_type = self.type_combo.currentText()
        
        if not name:
            QMessageBox.warning(self, self.tr("验证失败"), "请输入按钮名称")
            return
        
        # 对于Python脚本，命令/路径字段是可选的（用作描述）
        if button_type != self.tr("Python脚本") and not command:
            QMessageBox.warning(self, self.tr("验证失败"), f"请输入{button_type}内容")
            return
        
        # 根据按钮类型进行不同的验证
        if button_type == self.tr("ADB命令"):
            # 验证ADB命令
            if not self.button_manager.validate_command(command):
                reason = self.button_manager.get_blocked_reason(command)
                QMessageBox.warning(
                    self, self.tr("验证失败"),
                    f"{self.tr('ADB命令验证失败')}\n{reason if reason else self.tr('请检查命令是否正确')}"
                )
                return
        elif button_type == self.tr("Python脚本"):
            # 验证Python脚本 - 主要检查脚本区域，命令/路径作为描述
            script = self.script_edit.toPlainText().strip()
            if not script:
                QMessageBox.warning(self, self.tr("验证失败"), "请在Python脚本区域输入代码")
                return
            # 命令/路径字段可以为空或用作描述
        elif button_type in [self.tr("打开文件"), self.tr("运行程序")]:
            # 验证文件路径
            import os
            if not os.path.exists(command):
                QMessageBox.warning(
                    self, self.tr("验证失败"), 
                    f"{self.tr('文件/程序不存在:')}\n{command}\n\n{self.tr('请检查路径是否正确')}"
                )
                return
        
        self.accept()
    
    def get_button_data(self):
        """获取按钮数据"""
        # 获取按钮类型
        type_map = {
            self.tr("ADB命令"): "adb",
            self.tr("Python脚本"): "python", 
            self.tr("打开文件"): "file",
            self.tr("运行程序"): "program",
            self.tr("系统命令"): "system"
        }
        button_type = type_map.get(self.type_combo.currentText(), "adb")
        
        data = {
            'name': self.name_edit.text().strip(),
            'type': button_type,
            'command': self.command_edit.text().strip(),
            'tab': self.tab_combo.currentText(),
            'card': self.card_combo.currentText(),
            'enabled': self.enabled_check.isChecked(),
            'description': self.description_edit.toPlainText().strip()
        }
        
        # 如果是Python脚本，添加脚本内容
        if button_type == 'python':
            data['script'] = self.script_edit.toPlainText().strip()
        
        return data

