#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络信息 Tab
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QFrame, QLineEdit, QScrollArea)
from PyQt5.QtCore import pyqtSignal, Qt, QObject
from ui.widgets.shadow_utils import add_card_shadow
from core.debug_logger import logger


class NetworkInfoTab(QWidget):
    """网络信息 Tab"""
    
    # 信号定义
    # 网络信息控制
    start_network_info = pyqtSignal()
    stop_network_info = pyqtSignal()
    
    # Ping 控制
    start_ping = pyqtSignal(str)  # 传递 ping_target 参数
    stop_ping = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_network_running = False
        self.is_ping_running = False
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
        scroll_layout = QHBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(10)
        
        # 左侧控制面板
        control_panel = self.create_control_panel()
        scroll_layout.addWidget(control_panel, 0)
        
        # 右侧信息显示区域
        info_panel = self.create_info_panel()
        scroll_layout.addWidget(info_panel, 1)
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
    def create_control_panel(self):
        """创建控制面板（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel(self.lang_manager.tr("控制"))
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # 按钮行
        button_layout = QHBoxLayout()
        
        self.network_button = QPushButton(self.lang_manager.tr("开始"))
        self.network_button.clicked.connect(self._on_toggle_network_info)
        button_layout.addWidget(self.network_button)
        
        self.ping_button = QPushButton("Ping")
        self.ping_button.clicked.connect(self._on_toggle_ping)
        button_layout.addWidget(self.ping_button)
        
        layout.addLayout(button_layout)
        
        # 状态标签
        self.network_status_label = QLabel(self.lang_manager.tr("未启动"))
        self.network_status_label.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(self.network_status_label)
        
        self.ping_status_label = QLabel("")
        self.ping_status_label.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(self.ping_status_label)
        
        # Ping目标输入框（标签和输入框在同一行）
        ping_target_layout = QHBoxLayout()
        ping_target_label = QLabel(self.lang_manager.tr("Ping目标:"))
        ping_target_label.setStyleSheet("font-size: 9pt;")
        ping_target_layout.addWidget(ping_target_label)
        
        self.ping_target_input = QLineEdit()
        self.ping_target_input.setPlaceholderText("www.google.com")
        self.ping_target_input.setMaximumWidth(200)  # 限制输入框宽度
        # 从配置加载 ping_target，如果没有则使用默认值
        self._load_ping_target()
        # 连接输入框文本改变信号，保存配置
        self.ping_target_input.textChanged.connect(self._on_ping_target_changed)
        ping_target_layout.addWidget(self.ping_target_input)
        ping_target_layout.addStretch()  # 添加弹性空间，让输入框靠左
        layout.addLayout(ping_target_layout)
        
        # 添加弹性空间
        layout.addStretch()
        
        v.addWidget(card)
        
        return container
        
    def create_info_panel(self):
        """创建信息显示面板（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel(self.lang_manager.tr("网络信息"))
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # 创建表格
        self.network_table = QTableWidget()
        self.network_table.setColumnCount(16)
        self.network_table.setHorizontalHeaderLabels([
            "SIM", "CC", "RAT", "BAND", "DL_ARFCN", "UL_ARFCN", 
            "PCI", "RSRP", "RSRQ", "SINR", "RSSI", 
            "BW_DL", "BW_UL", "CA/ENDC", "CQI", "NOTE"
        ])
        
        # 设置表格属性
        self.network_table.setAlternatingRowColors(False)  # 禁用交替行颜色，避免显示问题
        self.network_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.network_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # 设置列调整模式 - 允许手动调整所有列的列宽
        header = self.network_table.horizontalHeader()
        header.setStretchLastSection(False)  # 禁用自动拉伸，允许手动调整
        # 设置所有列为可手动调整
        for i in range(16):
            header.setSectionResizeMode(i, QHeaderView.Interactive)
        
        # 设置初始列宽
        self.network_table.setColumnWidth(0, 50)   # SIM
        self.network_table.setColumnWidth(1, 50)   # CC
        self.network_table.setColumnWidth(2, 50)   # RAT
        self.network_table.setColumnWidth(3, 60)   # BAND
        self.network_table.setColumnWidth(4, 80)   # DL_ARFCN
        self.network_table.setColumnWidth(5, 80)   # UL_ARFCN
        self.network_table.setColumnWidth(6, 50)   # PCI
        self.network_table.setColumnWidth(7, 60)   # RSRP
        self.network_table.setColumnWidth(8, 60)   # RSRQ
        self.network_table.setColumnWidth(9, 60)   # SINR
        self.network_table.setColumnWidth(10, 60)  # RSSI
        self.network_table.setColumnWidth(11, 60)  # BW_DL
        self.network_table.setColumnWidth(12, 60)  # BW_UL
        self.network_table.setColumnWidth(13, 120) # CA/ENDC
        self.network_table.setColumnWidth(14, 50)  # CQI
        self.network_table.setColumnWidth(15, 150) # NOTE (最后一列自动拉伸)
        
        # 设置对象名称以便在主题中识别
        self.network_table.setObjectName("networkInfoTable")
        # 移除硬编码样式，使用主题样式
        
        # 初始提示文本
        self._show_initial_message()
        
        layout.addWidget(self.network_table)
        
        v.addWidget(card)
        
        return container
        
    def _show_initial_message(self):
        """显示初始提示信息"""
        self.network_table.setRowCount(1)
        self.network_table.setColumnCount(1)
        self.network_table.setHorizontalHeaderLabels([self.lang_manager.tr("提示")])
        
        item = QTableWidgetItem(self.lang_manager.tr("点击") + self.lang_manager.tr("开始") + self.lang_manager.tr("按钮获取网络信息"))
        item.setTextAlignment(Qt.AlignCenter)
        item.setForeground(Qt.gray)
        self.network_table.setItem(0, 0, item)
        self.network_table.horizontalHeader().setStretchLastSection(True)
        
    def _on_toggle_network_info(self):
        """切换网络信息获取状态"""
        logger.debug("=" * 60)
        logger.debug(f"按钮点击事件触发")
        logger.debug(f"Tab: NetworkInfoTab")
        logger.debug(f"按钮名称: network_button")
        logger.debug(f"当前状态: {'运行中' if self.is_network_running else '已停止'}")
        
        try:
            if self.is_network_running:
                # 停止时立即改变状态
                # 检查信号连接状态
                try:
                    receivers = QObject.receivers(self, self.stop_network_info)
                    logger.debug(f"信号对象: stop_network_info")
                    logger.debug(f"信号接收器数量: {receivers}")
                    if receivers == 0:
                        logger.error(f"⚠️ 警告：信号 stop_network_info 没有接收者！信号连接可能失败！")
                    else:
                        logger.debug(f"✓ 信号 stop_network_info 有 {receivers} 个接收者")
                except Exception as check_error:
                    logger.warning(f"无法检查信号 stop_network_info 的接收器数量: {check_error}")
                
                logger.debug(f"准备发送信号: stop_network_info")
                self.stop_network_info.emit()
                logger.debug(f"信号发送成功: stop_network_info")
                self.is_network_running = False
                self.network_button.setText(self.lang_manager.tr("开始"))
                self.network_button.setStyleSheet("")
                self.network_status_label.setText(self.lang_manager.tr("已停止"))
                self.network_status_label.setStyleSheet("color: gray; font-size: 9pt;")
            else:
                # 开始时只发送信号，等待成功回调再改变状态
                # 检查信号连接状态
                try:
                    receivers = QObject.receivers(self, self.start_network_info)
                    logger.debug(f"信号对象: start_network_info")
                    logger.debug(f"信号接收器数量: {receivers}")
                    if receivers == 0:
                        logger.error(f"⚠️ 警告：信号 start_network_info 没有接收者！信号连接可能失败！")
                    else:
                        logger.debug(f"✓ 信号 start_network_info 有 {receivers} 个接收者")
                except Exception as check_error:
                    logger.warning(f"无法检查信号 start_network_info 的接收器数量: {check_error}")
                
                logger.debug(f"准备发送信号: start_network_info")
                self.start_network_info.emit()
                logger.debug(f"信号发送成功: start_network_info")
        except Exception as e:
            logger.error(f"按钮点击处理失败:\n  按钮名称: network_button\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
        finally:
            logger.debug("=" * 60)
            
    def _on_toggle_ping(self):
        """切换 Ping 状态"""
        logger.debug("=" * 60)
        logger.debug(f"按钮点击事件触发")
        logger.debug(f"Tab: NetworkInfoTab")
        logger.debug(f"按钮名称: ping_button")
        logger.debug(f"当前状态: {'运行中' if self.is_ping_running else '已停止'}")
        
        try:
            if self.is_ping_running:
                # 停止时立即改变状态
                # 检查信号连接状态
                try:
                    receivers = QObject.receivers(self, self.stop_ping)
                    logger.debug(f"信号对象: stop_ping")
                    logger.debug(f"信号接收器数量: {receivers}")
                    if receivers == 0:
                        logger.error(f"⚠️ 警告：信号 stop_ping 没有接收者！信号连接可能失败！")
                    else:
                        logger.debug(f"✓ 信号 stop_ping 有 {receivers} 个接收者")
                except Exception as check_error:
                    logger.warning(f"无法检查信号 stop_ping 的接收器数量: {check_error}")
                
                logger.debug(f"准备发送信号: stop_ping")
                self.stop_ping.emit()
                logger.debug(f"信号发送成功: stop_ping")
                self.is_ping_running = False
                self.ping_button.setText("Ping")
                self.ping_button.setStyleSheet("")
                self.ping_status_label.setText("")
            else:
                # 开始时只发送信号，等待成功回调再改变状态
                # 从输入框获取 ping 目标，如果为空则使用默认值
                ping_target = self.ping_target_input.text().strip()
                if not ping_target:
                    ping_target = "www.google.com"
                
                # 检查信号连接状态
                try:
                    receivers = QObject.receivers(self, self.start_ping)
                    logger.debug(f"信号对象: start_ping")
                    logger.debug(f"信号接收器数量: {receivers}")
                    logger.debug(f"Ping目标: {ping_target}")
                    if receivers == 0:
                        logger.error(f"⚠️ 警告：信号 start_ping 没有接收者！信号连接可能失败！")
                    else:
                        logger.debug(f"✓ 信号 start_ping 有 {receivers} 个接收者")
                except Exception as check_error:
                    logger.warning(f"无法检查信号 start_ping 的接收器数量: {check_error}")
                
                logger.debug(f"准备发送信号: start_ping (target: {ping_target})")
                self.start_ping.emit(ping_target)
                logger.debug(f"信号发送成功: start_ping")
        except Exception as e:
            logger.error(f"按钮点击处理失败:\n  按钮名称: ping_button\n  错误类型: {type(e).__name__}\n  错误信息: {str(e)}")
            logger.exception("异常详情")
        finally:
            logger.debug("=" * 60)
            
    def set_network_state(self, is_running):
        """设置网络信息状态"""
        self.is_network_running = is_running
        if is_running:
            self.network_button.setText(self.lang_manager.tr("停止"))
            self.network_button.setStyleSheet("background-color: #f44336; color: white;")
            self.network_status_label.setText(self.lang_manager.tr("运行中..."))
            self.network_status_label.setStyleSheet("color: green; font-size: 9pt;")
        else:
            self.network_button.setText(self.lang_manager.tr("开始"))
            self.network_button.setStyleSheet("")
            self.network_status_label.setText(self.lang_manager.tr("已停止"))
            self.network_status_label.setStyleSheet("color: gray; font-size: 9pt;")
            
    def set_ping_state(self, is_running):
        """设置 Ping 状态"""
        self.is_ping_running = is_running
        if is_running:
            self.ping_button.setText(self.lang_manager.tr("停止"))
            self.ping_button.setStyleSheet("background-color: #f44336; color: white;")
            self.ping_status_label.setText(self.lang_manager.tr("Ping中..."))
            self.ping_status_label.setStyleSheet("color: blue; font-size: 9pt;")
        else:
            self.ping_button.setText("Ping")
            self.ping_button.setStyleSheet("")
            self.ping_status_label.setText("")
            
    def update_network_table(self, data):
        """更新网络信息表格
        
        Args:
            data: 网络信息数据列表，每个元素是一个字典
        """
        if not data:
            self._show_initial_message()
            return
            
        # 设置列数和表头
        self.network_table.setColumnCount(16)
        self.network_table.setHorizontalHeaderLabels([
            "SIM", "CC", "RAT", "BAND", "DL_ARFCN", "UL_ARFCN", 
            "PCI", "RSRP", "RSRQ", "SINR", "RSSI", 
            "BW_DL", "BW_UL", "CA/ENDC", "CQI", "NOTE"
        ])
        
        # 设置行数
        self.network_table.setRowCount(len(data))
        
        # 填充数据
        for row, item in enumerate(data):
            self.network_table.setItem(row, 0, QTableWidgetItem(str(item.get('sim', ''))))
            self.network_table.setItem(row, 1, QTableWidgetItem(str(item.get('cc', ''))))
            self.network_table.setItem(row, 2, QTableWidgetItem(str(item.get('rat', ''))))
            self.network_table.setItem(row, 3, QTableWidgetItem(str(item.get('band', ''))))
            self.network_table.setItem(row, 4, QTableWidgetItem(str(item.get('dl_arfcn', ''))))
            self.network_table.setItem(row, 5, QTableWidgetItem(str(item.get('ul_arfcn', ''))))
            self.network_table.setItem(row, 6, QTableWidgetItem(str(item.get('pci', ''))))
            self.network_table.setItem(row, 7, QTableWidgetItem(str(item.get('rsrp', ''))))
            self.network_table.setItem(row, 8, QTableWidgetItem(str(item.get('rsrq', ''))))
            self.network_table.setItem(row, 9, QTableWidgetItem(str(item.get('sinr', ''))))
            self.network_table.setItem(row, 10, QTableWidgetItem(str(item.get('rssi', ''))))
            self.network_table.setItem(row, 11, QTableWidgetItem(str(item.get('bw_dl', ''))))
            self.network_table.setItem(row, 12, QTableWidgetItem(str(item.get('bw_ul', ''))))
            self.network_table.setItem(row, 13, QTableWidgetItem(str(item.get('ca_endc', ''))))
            self.network_table.setItem(row, 14, QTableWidgetItem(str(item.get('cqi', ''))))
            self.network_table.setItem(row, 15, QTableWidgetItem(str(item.get('note', ''))))
            
    def update_ping_status(self, status_text):
        """更新 Ping 状态文本"""
        # 如果收到 ping_stopped 消息，重置 UI 状态
        if status_text == "ping_stopped":
            self.is_ping_running = False
            self.ping_button.setText("Ping")
            self.ping_button.setStyleSheet("")
            self.ping_status_label.setText("")
            return
        
        self.ping_status_label.setText(status_text)
        # 根据状态设置颜色：网络正常=绿色，网络异常=红色
        if status_text == self.lang_manager.tr("网络正常"):
            self.ping_status_label.setStyleSheet("color: green; font-size: 9pt;")
        elif status_text == self.lang_manager.tr("网络异常"):
            self.ping_status_label.setStyleSheet("color: red; font-size: 9pt;")  
        else:
            self.ping_status_label.setStyleSheet("color: blue; font-size: 9pt;")
    
    def refresh_texts(self, lang_manager=None):
        """刷新所有文本（用于语言切换）"""
        if lang_manager:
            self.lang_manager = lang_manager
        
        if not self.lang_manager:
            return
        
        # 刷新按钮文本
        if hasattr(self, 'network_button'):
            if self.network_button.text() in ["开始", "Start"]:
                self.network_button.setText(self.lang_manager.tr("开始"))
            elif self.network_button.text() in ["停止", "Stop"]:
                self.network_button.setText(self.lang_manager.tr("停止"))
        if hasattr(self, 'ping_button'):
            if self.ping_button.text() in ["Ping", "开始"]:
                self.ping_button.setText(self.lang_manager.tr("Ping"))
            elif self.ping_button.text() in ["停止", "Stop"]:
                self.ping_button.setText(self.lang_manager.tr("停止"))
        
        # 刷新状态标签
        if hasattr(self, 'network_status_label'):
            current_text = self.network_status_label.text()
            if current_text in ["未启动", "Not Started"]:
                self.network_status_label.setText(self.lang_manager.tr("未启动"))
            elif current_text in ["已停止", "Stopped"]:
                self.network_status_label.setText(self.lang_manager.tr("已停止"))
            elif current_text in ["运行中...", "Running..."]:
                self.network_status_label.setText(self.lang_manager.tr("运行中..."))
        
        if hasattr(self, 'ping_status_label'):
            current_text = self.ping_status_label.text()
            if current_text in ["Ping中...", "Pinging..."]:
                self.ping_status_label.setText(self.lang_manager.tr("Ping中..."))
        
        # 刷新表格标题
        if hasattr(self, 'network_table'):
            self.network_table.setHorizontalHeaderLabels([self.lang_manager.tr("提示")])
        
        # 刷新表格内容
        if hasattr(self, 'network_table') and self.network_table.rowCount() > 0:
            item = self.network_table.item(0, 0)
            if item and "点击" in item.text():
                item.setText(self.lang_manager.tr("点击") + self.lang_manager.tr("开始") + self.lang_manager.tr("按钮获取网络信息"))
        
        # 刷新组标题标签
        self._refresh_section_titles()
    
    def _refresh_section_titles(self):
        """刷新组标题标签"""
        # 查找所有QLabel并刷新标题
        for label in self.findChildren(QLabel):
            current_text = label.text()
            # 根据当前文本匹配对应的翻译
            if current_text in ["控制", "Control"]:
                label.setText(self.lang_manager.tr("控制"))
            elif current_text in ["网络信息", "Network Info"]:
                label.setText(self.lang_manager.tr("网络信息"))
    
    def _load_ping_target(self):
        """从配置加载 ping 目标"""
        try:
            # 从父窗口获取 network_info_manager
            if self.parent() and hasattr(self.parent(), 'network_info_manager'):
                network_info_manager = self.parent().network_info_manager
                ping_target = network_info_manager.get_ping_target()
                self.ping_target_input.setText(ping_target)
            else:
                # 如果没有父窗口，使用默认值
                self.ping_target_input.setText("www.google.com")
        except Exception:
            # 加载失败，使用默认值
            self.ping_target_input.setText("www.google.com")
    
    def _on_ping_target_changed(self, text):
        """当 ping 目标输入框内容改变时，保存配置"""
        try:
            # 从父窗口获取 network_info_manager
            if self.parent() and hasattr(self.parent(), 'network_info_manager'):
                network_info_manager = self.parent().network_info_manager
                ping_target = text.strip()
                if ping_target:  # 只有当输入不为空时才保存
                    network_info_manager.save_ping_target(ping_target)
        except Exception:
            # 保存失败不影响功能，静默处理
            pass

