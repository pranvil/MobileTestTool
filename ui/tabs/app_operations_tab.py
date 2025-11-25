#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APP操作 Tab
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QScrollArea, QLabel, QFrame)
from PyQt5.QtCore import pyqtSignal, Qt, QObject
from ui.widgets.shadow_utils import add_card_shadow
from core.debug_logger import logger


class AppOperationsTab(QWidget):
    """APP操作 Tab"""
    
    # 信号定义
    # 查询操作
    query_package = pyqtSignal()
    query_package_name = pyqtSignal()
    query_install_path = pyqtSignal()
    
    # APK操作
    pull_apk = pyqtSignal()
    push_apk = pyqtSignal()
    install_apk = pyqtSignal()
    
    # 进程操作
    view_processes = pyqtSignal()
    dump_app = pyqtSignal()
    
    # APP状态操作
    enable_app = pyqtSignal()
    disable_app = pyqtSignal()
    
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
        
        # 1. 查询操作和APK操作组（同一行）
        query_apk_container = QWidget()
        query_apk_layout = QHBoxLayout(query_apk_container)
        query_apk_layout.setContentsMargins(0, 0, 0, 0)
        query_apk_layout.setSpacing(10)
        
        query_ops_group = self.create_query_ops_group()
        query_apk_layout.addWidget(query_ops_group)
        
        apk_ops_group = self.create_apk_ops_group()
        query_apk_layout.addWidget(apk_ops_group)
        
        scroll_layout.addWidget(query_apk_container)
        
        # 2. 进程操作和APP状态操作组（同一行）
        process_status_container = QWidget()
        process_status_layout = QHBoxLayout(process_status_container)
        process_status_layout.setContentsMargins(0, 0, 0, 0)
        process_status_layout.setSpacing(10)
        
        process_ops_group = self.create_process_ops_group()
        process_status_layout.addWidget(process_ops_group)
        
        app_status_ops_group = self.create_app_status_ops_group()
        process_status_layout.addWidget(app_status_ops_group)
        
        scroll_layout.addWidget(process_status_container)
        
        # 添加弹性空间
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
    def create_query_ops_group(self):
        """创建查询操作组（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel(self.lang_manager.tr("查询操作"))
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        self.query_package_btn = QPushButton(self.lang_manager.tr("查询package"))
        self.query_package_btn.clicked.connect(lambda: self._on_button_clicked("query_package_btn", self.query_package.emit))
        card_layout.addWidget(self.query_package_btn)
        
        self.query_package_name_btn = QPushButton(self.lang_manager.tr("查询包名"))
        self.query_package_name_btn.clicked.connect(lambda: self._on_button_clicked("query_package_name_btn", self.query_package_name.emit))
        card_layout.addWidget(self.query_package_name_btn)
        
        self.query_install_path_btn = QPushButton(self.lang_manager.tr("查询安装路径"))
        self.query_install_path_btn.clicked.connect(lambda: self._on_button_clicked("query_install_path_btn", self.query_install_path.emit))
        card_layout.addWidget(self.query_install_path_btn)
        
        card_layout.addStretch()
        
        v.addWidget(card)
        
        return container
        
    def create_apk_ops_group(self):
        """创建APK操作组（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel(self.lang_manager.tr("APK操作"))
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        self.pull_apk_btn = QPushButton("pull apk")
        self.pull_apk_btn.clicked.connect(lambda: self._on_button_clicked("pull_apk_btn", self.pull_apk.emit))
        card_layout.addWidget(self.pull_apk_btn)
        
        self.push_apk_btn = QPushButton(self.lang_manager.tr("push 文件"))
        self.push_apk_btn.clicked.connect(lambda: self._on_button_clicked("push_apk_btn", self.push_apk.emit))
        card_layout.addWidget(self.push_apk_btn)
        
        self.install_apk_btn = QPushButton(self.lang_manager.tr("安装APK"))
        self.install_apk_btn.clicked.connect(lambda: self._on_button_clicked("install_apk_btn", self.install_apk.emit))
        card_layout.addWidget(self.install_apk_btn)
        
        card_layout.addStretch()
        
        v.addWidget(card)
        
        return container
        
    def create_process_ops_group(self):
        """创建进程操作组（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel(self.lang_manager.tr("进程操作"))
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        self.view_processes_btn = QPushButton(self.lang_manager.tr("查看进程"))
        self.view_processes_btn.clicked.connect(lambda: self._on_button_clicked("view_processes_btn", self.view_processes.emit))
        card_layout.addWidget(self.view_processes_btn)
        
        self.dump_app_btn = QPushButton("dump app")
        self.dump_app_btn.clicked.connect(lambda: self._on_button_clicked("dump_app_btn", self.dump_app.emit))
        card_layout.addWidget(self.dump_app_btn)
        
        card_layout.addStretch()
        
        v.addWidget(card)
        
        return container
        
    def create_app_status_ops_group(self):
        """创建APP状态操作组（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel(self.lang_manager.tr("APP状态操作"))
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        self.enable_app_btn = QPushButton(self.lang_manager.tr("启用app"))
        self.enable_app_btn.clicked.connect(lambda: self._on_button_clicked("enable_app_btn", self.enable_app.emit))
        card_layout.addWidget(self.enable_app_btn)
        
        self.disable_app_btn = QPushButton(self.lang_manager.tr("禁用app"))
        self.disable_app_btn.clicked.connect(lambda: self._on_button_clicked("disable_app_btn", self.disable_app.emit))
        card_layout.addWidget(self.disable_app_btn)
        
        card_layout.addStretch()
        
        v.addWidget(card)
        
        return container

    def _on_button_clicked(self, button_name, emit_func):
        """按钮点击统一处理函数，添加日志"""
        logger.debug("=" * 60)
        logger.debug(f"按钮点击事件触发")
        logger.debug(f"Tab: AppOperationsTab")
        logger.debug(f"按钮名称: {button_name}")
        logger.debug(f"按钮对象: {getattr(self, button_name, None)}")
        try:
            # 检查信号连接状态 - 尝试多种可能的信号名
            signal_name = None
            # 规则1: xxx_btn -> xxx (去掉 _btn 后缀)
            base_name = button_name.replace("_btn", "")
            if hasattr(self, base_name):
                signal_name = base_name
            # 规则2: xxx_btn -> xxx_dialog
            elif hasattr(self, base_name + "_dialog"):
                signal_name = base_name + "_dialog"
            # 规则3: xxx_btn -> show_xxx_dialog
            elif hasattr(self, "show_" + base_name + "_dialog"):
                signal_name = "show_" + base_name + "_dialog"
            
            if signal_name:
                signal_obj = getattr(self, signal_name)
                try:
                    # 使用 QObject.receivers() 静态方法检查信号接收器数量
                    receivers = QObject.receivers(signal_obj)
                    logger.debug(f"信号对象: {signal_name}")
                    logger.debug(f"信号接收器数量: {receivers}")
                    if receivers == 0:
                        logger.error(f"⚠️ 警告：信号 {signal_name} 没有接收者！信号连接可能失败！")
                    else:
                        logger.debug(f"✓ 信号 {signal_name} 有 {receivers} 个接收者")
                except Exception as check_error:
                    logger.warning(f"无法检查信号 {signal_name} 的接收器数量: {check_error}")
            else:
                logger.warning(f"⚠️ 无法找到按钮 {button_name} 对应的信号对象")
            
            logger.debug(f"准备发送信号: {button_name}")
            emit_func()
            logger.debug(f"信号发送成功: {button_name}")
        except Exception as e:
            logger.error(f"按钮点击处理失败:\n  按钮名称: {button_name}\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
        finally:
            logger.debug("=" * 60)
    
    def refresh_texts(self, lang_manager=None):
        """刷新所有文本（用于语言切换）"""
        if lang_manager:
            self.lang_manager = lang_manager
        
        if not self.lang_manager:
            return
        
        # 刷新组标题标签
        self._refresh_section_titles()
        
        # 刷新查询操作组按钮
        if hasattr(self, 'query_package_btn'):
            self.query_package_btn.setText(self.lang_manager.tr("查询package"))
        if hasattr(self, 'query_package_name_btn'):
            self.query_package_name_btn.setText(self.lang_manager.tr("查询包名"))
        if hasattr(self, 'query_install_path_btn'):
            self.query_install_path_btn.setText(self.lang_manager.tr("查询安装路径"))
        
        # 刷新APK操作组按钮
        if hasattr(self, 'push_apk_btn'):
            self.push_apk_btn.setText(self.lang_manager.tr("push 文件"))
        if hasattr(self, 'install_apk_btn'):
            self.install_apk_btn.setText(self.lang_manager.tr("安装APK"))
        
        # 刷新进程管理组按钮
        if hasattr(self, 'view_processes_btn'):
            self.view_processes_btn.setText(self.lang_manager.tr("查看进程"))
        
        # 刷新应用控制组按钮
        if hasattr(self, 'enable_app_btn'):
            self.enable_app_btn.setText(self.lang_manager.tr("启用app"))
        if hasattr(self, 'disable_app_btn'):
            self.disable_app_btn.setText(self.lang_manager.tr("禁用app"))
    
    def _refresh_section_titles(self):
        """刷新组标题标签"""
        # 查找所有QLabel并刷新标题
        for label in self.findChildren(QLabel):
            current_text = label.text()
            # 根据当前文本匹配对应的翻译
            if current_text in ["查询操作", "Query Operations"]:
                label.setText(self.lang_manager.tr("查询操作"))
            elif current_text in ["APK操作", "APK Operations"]:
                label.setText(self.lang_manager.tr("APK操作"))
            elif current_text in ["进程操作", "Process Operations"]:
                label.setText(self.lang_manager.tr("进程操作"))
            elif current_text in ["APP状态操作", "APP Status Operations"]:
                label.setText(self.lang_manager.tr("APP状态操作"))
