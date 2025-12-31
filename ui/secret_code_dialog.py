#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
暗码管理对话框
管理设备暗码（secret codes）的存储、编辑、删除、导入、导出和搜索
"""

import os
import json
import sys
import time
import subprocess
import re
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QLineEdit, QMessageBox, QFileDialog, QSplitter,
                             QWidget, QLabel, QMenu, QFrame)
from PySide6.QtCore import Qt, QPoint, Signal, QTimer
from core.debug_logger import logger
from ui.widgets.shadow_utils import add_card_shadow

# 尝试导入 uiautomator2
try:
    import uiautomator2 as u2
    HAS_UIAUTOMATOR2 = True
except ImportError:
    u2 = None
    HAS_UIAUTOMATOR2 = False


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
        
        # 获取设备管理器
        if parent and hasattr(parent, 'device_manager'):
            self.device_manager = parent.device_manager
        else:
            self.device_manager = None
        
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
        # 允许手动调整列宽
        header = self.category_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        self.category_table.setColumnWidth(0, 200)  # 设置初始宽度
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
        
        # 搜索区域（使用与Tab界面一致的样式：QLabel + QFrame）
        search_container = QWidget()
        search_container_layout = QVBoxLayout(search_container)
        search_container_layout.setContentsMargins(0, 0, 0, 0)
        search_container_layout.setSpacing(4)
        
        search_title = QLabel(self.tr("搜索"))
        search_title.setProperty("class", "section-title")
        search_container_layout.addWidget(search_title)
        
        search_card = QFrame()
        search_card.setObjectName("card")
        add_card_shadow(search_card)
        search_layout = QHBoxLayout(search_card)
        search_layout.setContentsMargins(10, 1, 10, 1)
        search_layout.setSpacing(8)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("输入搜索关键字..."))
        search_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("🔍 " + self.tr("搜索"))
        search_btn.clicked.connect(self.search_codes)
        search_layout.addWidget(search_btn)
        
        clear_search_btn = QPushButton("🗑️ " + self.tr("清除搜索"))
        clear_search_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(clear_search_btn)
        
        search_container_layout.addWidget(search_card)
        layout.addWidget(search_container)
        
        # 创建暗码表格
        self.code_table = QTableWidget()
        self.code_table.setColumnCount(2)
        self.code_table.setHorizontalHeaderLabels([self.tr("Code"), self.tr("描述")])
        self.code_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.code_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.code_table.setSelectionMode(QTableWidget.SingleSelection)
        
        # 双击事件
        self.code_table.itemDoubleClicked.connect(self.on_code_double_clicked)
        
        # 允许手动调整列宽
        header = self.code_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        self.code_table.setColumnWidth(0, 200)  # Code列初始宽度
        self.code_table.setColumnWidth(1, 300)  # 描述列初始宽度
        
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
        if dialog.exec() == QDialog.DialogCode.Accepted:
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
        if dialog.exec() == QDialog.DialogCode.Accepted:
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
                # QMessageBox.information(self, self.tr("成功"), self.tr("暗码更新成功！"))
    
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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
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
        """双击暗码（任意列）事件 - 自动输入暗码"""
        # 获取双击的行
        row = item.row()
        
        # 必须从第0列（code列）获取code文本
        code_item = self.code_table.item(row, 0)
        if not code_item:
            return
        
        code = code_item.text()
        description = self.code_table.item(row, 1).text() if self.code_table.item(row, 1) else ""
        
        logger.debug(f"双击暗码: {code}, 描述: {description}")
        
        # 检查设备管理器是否可用
        if not self.device_manager:
            QMessageBox.warning(self, self.tr("错误"), self.tr("设备管理器未初始化"))
            return
        
        # 验证设备选择
        device = self.device_manager.validate_device_selection()
        if not device:
            return
        
        # 检查UIAutomator2是否可用
        if not HAS_UIAUTOMATOR2:
            QMessageBox.warning(self, self.tr("错误"), self.tr("uiautomator2未安装，无法执行自动输入"))
            return
        
        # 在后台线程执行暗码输入，避免阻塞UI
        import threading
        def run_in_background():
            try:
                self._execute_secret_code(device, code)
                logger.debug(f"暗码输入成功: {code}")
            except Exception as e:
                logger.exception(f"执行暗码输入失败: {e}")
        
        thread = threading.Thread(target=run_in_background, daemon=True)
        thread.start()
        
        # 显示一个简单的提示，用户可以看到正在执行
        QMessageBox.information(self, self.tr("提示"), self.tr(f"暗码已发送\n {code}"))
    
    def _execute_secret_code(self, device, code):
        """执行暗码输入的完整流程"""
        logger.debug(f"开始执行暗码输入流程: {code}")
        
        # 步骤1: 确保屏幕亮屏且解锁
        if not self._ensure_screen_unlocked(device):
            raise Exception(self.tr("无法确保屏幕解锁"))
        
        # 步骤2: 返回桌面
        self._go_home(device)
        time.sleep(1)
        
        # 步骤3: 打开Phone应用
        self._open_phone_app(device)
        time.sleep(2)
        
        # 步骤4: 获取当前包名
        package_name = self._get_current_package_name(device)
        logger.debug(f"检测到Phone app包名: {package_name}")
        
        # 步骤5: 检查并点击拨号盘（打开拨号盘），然后等待拨号盘加载
        if not self._open_dialpad_and_wait(device, package_name):
            raise Exception(self.tr("未找到拨号盘或拨号按钮"))
        
        # 步骤7: 输入暗码（在焦点获取后额外等待一小段时间，确保焦点完全稳定）
        time.sleep(0.3)
        self._input_text(device, code)
        time.sleep(1)
        
        logger.debug("暗码输入流程完成")
    
    def _ensure_screen_unlocked(self, device):
        """确保屏幕亮屏且解锁"""
        try:
            # 检查屏幕是否亮屏
            screen_on = self._check_screen_on(device)
            if not screen_on:
                self._wake_screen(device)
                time.sleep(2)
            
            # 检查屏幕是否解锁
            screen_unlocked = self._check_screen_unlocked(device)
            if not screen_unlocked:
                self._unlock_screen(device)
                time.sleep(1)
            
            return True
        except Exception as e:
            logger.exception(f"检查屏幕状态失败: {e}")
            return False
    
    def _check_screen_on(self, device):
        """检查屏幕是否亮屏"""
        try:
            cmd = ["adb", "-s", device, "shell", "dumpsys", "deviceidle"]
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                errors='replace', 
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'mScreenOn' in line:
                        return 'true' in line.lower()
            return False
        except Exception:
            return False
    
    def _check_screen_unlocked(self, device):
        """检查屏幕是否解锁"""
        try:
            cmd = ["adb", "-s", device, "shell", "dumpsys", "deviceidle"]
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                errors='replace', 
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'mScreenLocked' in line:
                        return 'false' in line.lower()  # false表示解锁状态
            return False
        except Exception:
            return False
    
    def _wake_screen(self, device):
        """点亮屏幕"""
        try:
            cmd = ["adb", "-s", device, "shell", "input", "keyevent", "224"]
            subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                errors='replace', 
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
        except Exception as e:
            logger.exception(f"点亮屏幕失败: {e}")
    
    def _unlock_screen(self, device):
        """解锁屏幕"""
        try:
            cmd = ["adb", "-s", device, "shell", "input", "keyevent", "82"]
            subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                errors='replace', 
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
        except Exception as e:
            logger.exception(f"解锁屏幕失败: {e}")
    
    def _go_home(self, device):
        """返回桌面"""
        try:
            cmd = ["adb", "-s", device, "shell", "input", "keyevent", "KEYCODE_HOME"]
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            logger.debug("已返回桌面")
        except Exception as e:
            logger.exception(f"返回桌面失败: {e}")
    
    def _open_phone_app(self, device):
        """打开Phone应用"""
        try:
            d = u2.connect(device)
            
            # 尝试查找Phone图标
            phone_found = False
            # 方法1: 通过content-desc查找"Phone"
            try:
                phone_elements = d(description="Phone")
                if phone_elements.exists:
                    phone_elements.click()
                    phone_found = True
                    logger.debug("通过content-desc='Phone'找到并点击")
            except Exception:
                pass
            
            # 方法2: 通过content-desc查找"电话"
            if not phone_found:
                try:
                    phone_elements = d(description="电话")
                    if phone_elements.exists:
                        phone_elements.click()
                        phone_found = True
                        logger.debug("通过content-desc='电话'找到并点击")
                except Exception:
                    pass
            
            # 方法3: 通过class name查找所有元素，查找可能的phone图标
            if not phone_found:
                try:
                    # 尝试查找包含phone关键词的元素
                    all_elements = d(className="android.widget.ImageView")
                    for element in all_elements:
                        try:
                            desc = element.info.get('contentDescription', '').lower()
                            if 'phone' in desc or '电话' in desc:
                                element.click()
                                phone_found = True
                                logger.debug(f"通过ImageView找到phone图标: {desc}")
                                break
                        except Exception:
                            continue
                except Exception:
                    pass
            
            if not phone_found:
                raise Exception(self.tr("未找到Phone应用图标"))
            
            logger.debug("已打开Phone应用")
        except Exception as e:
            logger.exception(f"打开Phone应用失败: {e}")
            raise
    
    def _get_current_package_name(self, device):
        """获取当前应用的包名 - 使用 dumpsys window 查找 mCurrentFocus"""
        try:
            cmd = ["adb", "-s", device, "shell", "dumpsys", "window"]
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode != 0:
                logger.error(f"dumpsys window 命令执行失败: {result.stderr}")
                return None
            
            # 查找 mCurrentFocus 行
            # 格式: mCurrentFocus=Window{xxx u0 com.package.name/Activity}
            for line in result.stdout.split('\n'):
                if 'mCurrentFocus' in line:
                    logger.debug(f"找到 mCurrentFocus 行: {line.strip()}")
                    # 解析格式: Window{xxx u0 com.package.name/Activity}
                    # 提取 u0 后面，/ 前面的包名部分
                    if ' u0 ' in line:
                        parts = line.split(' u0 ')
                        if len(parts) > 1:
                            package_part = parts[1].strip()
                            # 提取包名（在第一个/之前的部分）
                            if '/' in package_part:
                                package_name = package_part.split('/')[0].strip()
                            else:
                                # 如果没有/，可能是格式不同，尝试提取包名
                                # 去掉可能的后续字符
                                package_name = package_part.split()[0].strip() if package_part.split() else None
                            
                            if package_name and len(package_name) > 0:
                                logger.info(f"解析到包名: {package_name}")
                                return package_name
            
            logger.warning("未找到 mCurrentFocus 行，无法获取包名")
            return None
            
        except Exception as e:
            logger.exception(f"获取当前包名失败: {e}")
            return None
    
    def _clear_input(self, device):
        """清空输入 - 使用KEYCODE_DEL清空，避免触发UI状态"""
        try:
            # 简单粗暴：直接用DEL键清空，不调用任何可能触发UI状态的操作
            cmd = ["adb", "-s", device, "shell", "input", "keyevent", "KEYCODE_DEL"]
            for _ in range(15):  # 删除15次确保清空
                subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=1,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                time.sleep(0.05)
            logger.debug("使用DEL键清空输入")
        except Exception as e:
            logger.exception(f"清空输入失败: {e}")
    
    def _focus_google_dialer_input(self, d):
        """聚焦Google Dialer输入框的辅助方法 - 通过点击数字2按钮上方位置获取焦点
        
        Args:
            d: uiautomator2设备对象
            
        Returns:
            bool: 成功返回True，失败返回False
        """
        try:
            logger.debug("开始聚焦 Google Dialer 输入框（通过点击数字2按钮上方位置）...")
            
            # 步骤1: 等待并找到数字2按钮
            two_button = d(resourceId="com.google.android.dialer:id/two")
            two_button.wait(timeout=3.0)  # 等待数字2按钮出现
            
            if not two_button.exists:
                logger.error("未找到数字2按钮，焦点获取失败")
                return False
            
            # 步骤2: 获取数字2按钮的坐标信息
            button_info = two_button.info
            if not button_info:
                logger.error("无法获取数字2按钮的坐标信息")
                return False
            
            # 获取按钮的中心坐标和边界
            bounds = button_info.get('bounds', {})
            if not bounds:
                logger.error("无法获取数字2按钮的边界信息")
                return False
            
            # 计算按钮的中心坐标
            center_x = (bounds['left'] + bounds['right']) // 2
            center_y = (bounds['top'] + bounds['bottom']) // 2
            button_height = bounds['bottom'] - bounds['top']
            
            logger.debug(f"数字2按钮位置: center=({center_x}, {center_y}), height={button_height}")
            
            # 步骤3: 计算向上一点的位置（向上移动按钮高度的1.5倍）
            click_y = center_y - int(button_height * 1.5)
            click_x = center_x  # x坐标保持不变
            
            logger.debug(f"点击输入框位置: ({click_x}, {click_y})")
            
            # 步骤4: 点击输入框位置
            d.click(click_x, click_y)
            logger.debug("已点击输入框位置")
            
            # 额外等待，确保焦点完全稳定
            time.sleep(0.5)
            
            logger.debug("Google Dialer 输入框焦点获取成功")
            return True
            
        except Exception as e:
            logger.exception(f"聚焦Google Dialer输入框失败: {e}")
            return False
    
    def _open_dialpad_and_wait(self, device, package_name):
        """检查并点击拨号盘，然后等待拨号盘完全加载"""
        try:
            d = u2.connect(device)
            
            # 根据包名选择对应的resource ID列表
            dial_button_ids = []
            dialpad_button_ids = []
            
            if package_name == "com.google.android.dialer":
                dial_button_ids = ["com.google.android.dialer:id/dialpad_voice_call_button"]
                dialpad_button_ids = [
                    "com.google.android.dialer:id/dialpad_fab",
                    "com.google.android.dialer:id/tab_dialpad"
                ]
            elif package_name == "com.android.dialer":
                dial_button_ids = ["com.android.dialer:id/dialpad_floating_action_button"]
                dialpad_button_ids = ["com.android.dialer:id/fab"]
            elif package_name == "com.samsung.android.dialer":
                dial_button_ids = ["com.samsung.android.dialer:id/dialButton"]
                dialpad_button_ids = ["com.samsung.android.dialer:id/tab_text_container"]
            else:
                # 未知包名，尝试所有可能的ID
                dial_button_ids = [
                    "com.google.android.dialer:id/dialpad_voice_call_button",
                    "com.android.dialer:id/dialpad_floating_action_button",
                    "com.samsung.android.dialer:id/dialButton",
                ]
                dialpad_button_ids = [
                    "com.google.android.dialer:id/dialpad_fab",
                    "com.google.android.dialer:id/tab_dialpad",
                    "com.android.dialer:id/fab",
                    "com.samsung.android.dialer:id/tab_text_container",
                ]
            
            # 先检查是否已经有拨号按钮（说明已经在拨号盘页面）
            for dial_button_id in dial_button_ids:
                button = d(resourceId=dial_button_id)
                if button.exists:
                    logger.debug(f"找到拨号按钮: {dial_button_id}，已位于拨号盘")
                    # 判断是否是Google Dialer：通过resourceId或包名判断
                    is_google_dialer = (package_name == "com.google.android.dialer" or 
                                       dial_button_id == "com.google.android.dialer:id/dialpad_voice_call_button")
                    
                    if is_google_dialer:
                        if not self._focus_google_dialer_input(d):
                            logger.error("聚焦Google Dialer输入框失败")
                            return False
                    return True
            
            # 如果不在拨号盘，尝试点击拨号盘按钮
            logger.debug(f"未在拨号盘，尝试点击拨号盘按钮。包名: {package_name}")
            dialpad_button_found = False
            for dialpad_button_id in dialpad_button_ids:
                button = d(resourceId=dialpad_button_id)
                if button.exists:
                    button.click()
                    logger.debug(f"已点击拨号盘按钮: {dialpad_button_id}")
                    dialpad_button_found = True
                    break
            
            if not dialpad_button_found:
                logger.error(f"未找到拨号盘按钮。包名: {package_name}")
                return False
            
            # 点击后，等待拨号按钮出现（最多2秒）
            logger.debug("等待拨号盘加载...")
            for dial_button_id in dial_button_ids:
                try:
                    button = d(resourceId=dial_button_id)
                    button.wait(timeout=2.0)  # 等待元素出现，最多2秒
                    if button.exists:
                        logger.debug(f"拨号盘已加载，找到拨号按钮: {dial_button_id}")
                        # 判断是否是Google Dialer：通过resourceId或包名判断
                        is_google_dialer = (package_name == "com.google.android.dialer" or 
                                           dial_button_id == "com.google.android.dialer:id/dialpad_voice_call_button")
                        
                        if is_google_dialer:
                            # 额外等待一小段时间，确保拨号盘UI完全稳定
                            time.sleep(0.5)
                            if not self._focus_google_dialer_input(d):
                                logger.error("聚焦Google Dialer输入框失败")
                                return False
                        return True
                except:
                    continue
            
            logger.error("拨号盘加载超时")
            return False
            
        except Exception as e:
            logger.exception(f"打开拨号盘失败: {e}")
            return False
    
    def _input_text(self, device, text):
        """输入文本 - 使用input text，对特殊字符进行转义"""
        try:
            logger.debug(f"输入文本: {text}")
            
            # 转义特殊字符
            # 空格用 %s，其他字符直接传递
            processed_text = text.replace(' ', '%s')
            
            # 使用input text输入
            cmd = ["adb", "-s", device, "shell", "input", "text", processed_text]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode != 0:
                logger.error(f"输入文本失败: {result.stderr}")
                raise Exception(f"输入文本失败: {result.stderr}")
            
            logger.debug(f"已输入文本: {text}")
        except Exception as e:
            logger.exception(f"输入文本失败: {e}")
            raise
    
    def add_category(self):
        """新增分类"""
        dialog = CategoryEditDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
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
        if dialog.exec() == QDialog.DialogCode.Accepted:
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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
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
        menu.exec(self.category_table.viewport().mapToGlobal(position))
    
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
        from PySide6.QtWidgets import QFormLayout, QDialogButtonBox
        
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
        from PySide6.QtWidgets import QFormLayout, QDialogButtonBox
        
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

