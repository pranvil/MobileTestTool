#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIM Tab - SIM APDU 解析器集成
"""

import sys
import os
import subprocess
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QLabel, QMessageBox, QScrollArea, QFrame)
from PySide6.QtCore import Signal, Qt
from ui.widgets.shadow_utils import add_card_shadow

# 添加SIM_APDU_Parser到Python路径
# 在PyInstaller打包环境中，使用sys._MEIPASS获取资源路径
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # PyInstaller打包环境：SIM_APDU_Parser在sys._MEIPASS中
    # 需要将sys._MEIPASS添加到sys.path（父目录），而不是SIM_APDU_Parser本身
    base_path = sys._MEIPASS
    sim_parser_parent_path = base_path
else:
    # 开发环境：使用__file__计算路径
    # 需要将SIM_APDU_Parser的父目录添加到sys.path，而不是SIM_APDU_Parser本身
    current_dir = os.path.dirname(os.path.abspath(__file__))  # ui/tabs目录
    ui_dir = os.path.dirname(current_dir)  # ui目录
    project_root = os.path.dirname(ui_dir)  # 项目根目录
    sim_parser_path = os.path.join(project_root, "SIM_APDU_Parser")
    sim_parser_parent_path = project_root  # 父目录就是项目根目录

if sim_parser_parent_path not in sys.path:
    sys.path.insert(0, sim_parser_parent_path)
    print(f"[DEBUG] SIM Tab添加SIM_APDU_Parser父路径到sys.path: {sim_parser_parent_path}")

from ui.apdu_parser_dialog import ApduParserDialog

class SimTab(QWidget):
    """SIM APDU 解析器 Tab"""
    
    # 信号定义
    status_message = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 从父窗口获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            # 如果没有父窗口或语言管理器，使用单例
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager.get_instance()
        self.setup_ui()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 滚动内容
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(1)
        
        # SIM APDU 解析器控制组
        sim_apdu_group = self.create_sim_apdu_group()
        scroll_layout.addWidget(sim_apdu_group)
        
        # SIM 卡读写工具控制组
        sim_reader_group = self.create_sim_reader_group()
        scroll_layout.addWidget(sim_reader_group)
        
        # 添加弹性空间
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
    
    def create_sim_apdu_group(self):
        """创建 SIM APDU 解析器控制组（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)  # 紧凑的标题和卡片之间的间距
        
        # 标题
        self.sim_apdu_title = QLabel(self.lang_manager.tr("SIM APDU 解析器"))
        self.sim_apdu_title.setProperty("class", "section-title")
        v.addWidget(self.sim_apdu_title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        # 按钮行
        row = QHBoxLayout()
        
        self.launch_apdu_btn = QPushButton(self.lang_manager.tr("启动 APDU 解析器"))
        self.launch_apdu_btn.clicked.connect(self.launch_apdu_parser)
        row.addWidget(self.launch_apdu_btn)
        
        row.addStretch()
        card_layout.addLayout(row)
        
        v.addWidget(card)
        
        return container
    
    def create_sim_reader_group(self):
        """创建 SIM 卡读写工具控制组（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)  # 紧凑的标题和卡片之间的间距
        
        # 标题
        self.sim_reader_title = QLabel(self.lang_manager.tr("SIM 卡读写工具"))
        self.sim_reader_title.setProperty("class", "section-title")
        v.addWidget(self.sim_reader_title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        # 按钮行
        row = QHBoxLayout()
        
        self.launch_reader_btn = QPushButton(self.lang_manager.tr("启动 SIM 卡读写工具"))
        self.launch_reader_btn.clicked.connect(self.launch_sim_reader)
        row.addWidget(self.launch_reader_btn)
        
        row.addStretch()
        card_layout.addLayout(row)
        
        v.addWidget(card)
        
        return container
    
    def launch_apdu_parser(self):
        """启动 APDU 解析器"""
        try:
            # 打开APDU解析器对话框
            dialog = ApduParserDialog(self)
            dialog.exec()
            
            self.status_message.emit("APDU 解析器已启动")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动失败：\n{str(e)}")
            self.status_message.emit(f"APDU 解析器启动失败：{str(e)}")
    
    def launch_sim_reader(self):
        """启动 SIM 卡读写工具"""
        try:
            # 导入并打开SIM卡读写工具对话框
            from ui.sim_reader_dialog import SimReaderDialog
            dialog = SimReaderDialog.get_instance(self)
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
            
            self.status_message.emit("SIM 卡读写工具已启动")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动失败：\n{str(e)}")
            self.status_message.emit(f"SIM 卡读写工具启动失败：{str(e)}")
    
    def refresh_texts(self, lang_manager=None):
        """刷新所有文本（用于语言切换）"""
        if lang_manager:
            self.lang_manager = lang_manager
        
        if not self.lang_manager:
            return
        
        # 刷新标题
        if hasattr(self, 'sim_apdu_title'):
            self.sim_apdu_title.setText(self.lang_manager.tr("SIM APDU 解析器"))
        if hasattr(self, 'sim_reader_title'):
            self.sim_reader_title.setText(self.lang_manager.tr("SIM 卡读写工具"))
        
        # 刷新按钮
        if hasattr(self, 'launch_apdu_btn'):
            self.launch_apdu_btn.setText(self.lang_manager.tr("启动 APDU 解析器"))
        if hasattr(self, 'launch_reader_btn'):
            self.launch_reader_btn.setText(self.lang_manager.tr("启动 SIM 卡读写工具"))
