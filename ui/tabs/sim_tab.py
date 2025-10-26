#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIM Tab - SIM APDU 解析器集成
"""

import sys
import os
import subprocess
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QLabel, QMessageBox, QScrollArea, QFrame)
from PyQt5.QtCore import pyqtSignal, Qt
from ui.widgets.shadow_utils import add_card_shadow

# 添加SIM_APDU_Parser到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))  # ui/tabs目录
ui_dir = os.path.dirname(current_dir)  # ui目录
project_root = os.path.dirname(ui_dir)  # 项目根目录
sim_parser_path = os.path.join(project_root, "SIM_APDU_Parser")
if sim_parser_path not in sys.path:
    sys.path.insert(0, sim_parser_path)
    print(f"[DEBUG] SIM Tab添加SIM_APDU_Parser路径: {sim_parser_path}")

from ui.apdu_parser_dialog import ApduParserDialog

class SimTab(QWidget):
    """SIM APDU 解析器 Tab"""
    
    # 信号定义
    status_message = pyqtSignal(str)
    
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
        sim_group = self.create_sim_group()
        scroll_layout.addWidget(sim_group)
        
        # 添加弹性空间
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
    
    def create_sim_group(self):
        """创建 SIM APDU 解析器控制组（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)  # 紧凑的标题和卡片之间的间距
        
        # 标题
        title = QLabel("SIM APDU 解析器")
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        # 按钮行
        row = QHBoxLayout()
        # row.addWidget(QLabel("APDU解析器:"))
        
        self.launch_btn = QPushButton("启动 APDU 解析器")
        self.launch_btn.clicked.connect(self.launch_apdu_parser)
        row.addWidget(self.launch_btn)
        
        row.addStretch()
        card_layout.addLayout(row)
        
        v.addWidget(card)
        
        return container
    
    def launch_apdu_parser(self):
        """启动 APDU 解析器"""
        try:
            # 打开APDU解析器对话框
            dialog = ApduParserDialog(self)
            dialog.exec_()
            
            self.status_message.emit("APDU 解析器已启动")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动失败：\n{str(e)}")
            self.status_message.emit(f"APDU 解析器启动失败：{str(e)}")
