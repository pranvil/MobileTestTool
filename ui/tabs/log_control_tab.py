#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Log控制 Tab
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QToolButton, QLabel, QScrollArea, QFrame, QMenu)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QAction
from ui.widgets.shadow_utils import add_card_shadow


class LogControlTab(QWidget):
    """Log控制 Tab"""
    
    # 信号定义
    # MTKLOG 相关
    mtklog_start = Signal()
    mtklog_stop_export = Signal()
    mtklog_delete = Signal()
    mtklog_set_log_size = Signal()
    mtklog_sd_mode = Signal()
    mtklog_usb_mode = Signal()
    mtklog_install = Signal()
    
    # ADB Log 相关
    adblog_start = Signal()  # 保留原有信号，用于离线log
    adblog_online_start = Signal()  # 新增连线log信号
    adblog_export = Signal()
    
    # Telephony 相关
    telephony_enable = Signal()
    
    # Google 日志相关
    google_log_toggle = Signal()
    
    # Bugreport 相关
    bugreport_generate = Signal()
    bugreport_pull = Signal()
    bugreport_delete = Signal()
    
    # AEE log 相关
    aee_log_start = Signal()
    
    # TCPDUMP 相关
    tcpdump_show_dialog = Signal()
    
    # Log操作相关
    merge_mtklog = Signal()
    extract_pcap_from_mtklog = Signal()
    merge_pcap = Signal()
    extract_pcap_from_qualcomm_log = Signal()
    mtk_sip_decode = Signal()
    
    # Qualcomm工具相关
    show_lock_cell_dialog = Signal()
    show_qc_nv_dialog = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 从父窗口获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            # 如果没有父窗口或语言管理器，使用单例
            import sys
            import os
            import importlib
            try:
                from core.language_manager import LanguageManager
                self.lang_manager = LanguageManager.get_instance()
            except ModuleNotFoundError:
                # 如果导入失败，确保正确的路径在 sys.path 中
                # 支持 PyInstaller 打包环境
                if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                    # PyInstaller 环境：使用 sys._MEIPASS
                    base_path = sys._MEIPASS
                    # 置顶 base_path，避免同名包被更前的路径抢占
                    try:
                        if base_path in sys.path:
                            sys.path.remove(base_path)
                    except ValueError:
                        pass
                    sys.path.insert(0, base_path)
                else:
                    # 开发环境：使用 __file__ 计算项目根目录
                    current_file = os.path.abspath(__file__)
                    # ui/tabs/log_control_tab.py -> ui/tabs -> ui -> 项目根目录
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
                    # 置顶 project_root，避免同名包被更前的路径抢占
                    try:
                        if project_root in sys.path:
                            sys.path.remove(project_root)
                    except ValueError:
                        pass
                    sys.path.insert(0, project_root)

                # 关键：如果 core 已被其它同名包污染（例如 sim_reader/core），需要清掉缓存后再导入
                try:
                    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                        root = sys._MEIPASS
                    else:
                        root = project_root
                    expected_core_init = os.path.normpath(os.path.join(root, "core", "__init__.py"))
                    sim_reader_root = os.path.normpath(os.path.join(root, "sim_reader"))

                    core_pkg = sys.modules.get("core")
                    if core_pkg is not None:
                        core_file = getattr(core_pkg, "__file__", None) or ""
                        normalized_core_file = os.path.normpath(os.path.abspath(core_file)) if core_file else ""
                        is_wrong = (
                            (not core_file) or
                            (sim_reader_root in normalized_core_file) or
                            (expected_core_init and normalized_core_file != expected_core_init) or
                            (core_file and not os.path.exists(core_file))
                        )
                        if is_wrong:
                            for name in list(sys.modules.keys()):
                                if name == "core" or name.startswith("core."):
                                    sys.modules.pop(name, None)
                            importlib.invalidate_caches()
                except Exception:
                    # 兜底：不阻止后续重试导入
                    pass

                # 重试导入
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
        
        # 1. LOG控制组
        mtklog_group = self.create_mtklog_group()
        scroll_layout.addWidget(mtklog_group)
        
        # 2. ADB Log 控制组（包含 ADB Log 和 Google 日志相关功能）
        adblog_group = self.create_adblog_group()
        scroll_layout.addWidget(adblog_group)
        
        # 添加弹性空间
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
    def create_mtklog_group(self):
        """创建 LOG控制组（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)  # 紧凑的标题和卡片之间的间距
        
        # 标题
        title = QLabel(self.lang_manager.tr("LOG控制"))
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        # 第一行：MTK操作（合并了原来的第一行和第二行）
        row1 = QHBoxLayout()
        mtk_label = QLabel("MTK:")
        mtk_label.setFixedWidth(90)  # 固定宽度，确保与Qualcomm标签对齐
        row1.addWidget(mtk_label)
        
        self.mtklog_start_btn = QPushButton(self.lang_manager.tr("开启"))
        self.mtklog_start_btn.clicked.connect(self.mtklog_start.emit)
        row1.addWidget(self.mtklog_start_btn)
        
        self.mtklog_stop_export_btn = QPushButton(self.lang_manager.tr("停止&导出"))
        self.mtklog_stop_export_btn.clicked.connect(self.mtklog_stop_export.emit)
        row1.addWidget(self.mtklog_stop_export_btn)
        
        self.mtklog_delete_btn = QPushButton(self.lang_manager.tr("删除"))
        self.mtklog_delete_btn.clicked.connect(self.mtklog_delete.emit)
        row1.addWidget(self.mtklog_delete_btn)
        
        # Logger设置按钮（下拉菜单）
        self.mtklog_mode_btn = QToolButton()
        self.mtklog_mode_btn.setText(self.lang_manager.tr("Logger设置"))
        self.mtklog_mode_btn.setPopupMode(QToolButton.InstantPopup)
        
        # 创建下拉菜单
        mode_menu = QMenu(self.mtklog_mode_btn)
        
        # 设置log size
        set_log_size_action = QAction(self.lang_manager.tr("设置log size"), self)
        set_log_size_action.triggered.connect(self.mtklog_set_log_size.emit)
        mode_menu.addAction(set_log_size_action)
        
        mode_menu.addSeparator()
        
        # SD模式
        sd_mode_action = QAction(self.lang_manager.tr("SD模式"), self)
        sd_mode_action.triggered.connect(self.mtklog_sd_mode.emit)
        mode_menu.addAction(sd_mode_action)
        
        # USB模式
        usb_mode_action = QAction(self.lang_manager.tr("USB模式"), self)
        usb_mode_action.triggered.connect(self.mtklog_usb_mode.emit)
        mode_menu.addAction(usb_mode_action)
        
        self.mtklog_mode_btn.setMenu(mode_menu)
        self.mtklog_mode_menu = mode_menu  # 保存引用以便后续更新文本
        row1.addWidget(self.mtklog_mode_btn)
        
        # self.mtklog_install_btn = QPushButton(self.lang_manager.tr("安装MTKLOGGER"))
        # self.mtklog_install_btn.clicked.connect(self.mtklog_install.emit)
        # row1.addWidget(self.mtklog_install_btn)
        
        self.telephony_btn = QPushButton(self.lang_manager.tr("启用Telephony日志"))
        self.telephony_btn.clicked.connect(self.telephony_enable.emit)
        row1.addWidget(self.telephony_btn)
        
        # 合并原来的第二行按钮
        self.merge_mtklog_btn = QPushButton(self.lang_manager.tr("合并MTKlog"))
        self.merge_mtklog_btn.clicked.connect(self.merge_mtklog.emit)
        row1.addWidget(self.merge_mtklog_btn)
        
        self.extract_pcap_from_mtklog_btn = QPushButton(self.lang_manager.tr("MTKlog提取pcap"))
        self.extract_pcap_from_mtklog_btn.clicked.connect(self.extract_pcap_from_mtklog.emit)
        row1.addWidget(self.extract_pcap_from_mtklog_btn)
        
        self.merge_pcap_btn = QPushButton(self.lang_manager.tr("合并PCAP"))
        self.merge_pcap_btn.clicked.connect(self.merge_pcap.emit)
        row1.addWidget(self.merge_pcap_btn)
        
        self.mtk_sip_decode_btn = QPushButton(self.lang_manager.tr("MTK SIP DECODE"))
        self.mtk_sip_decode_btn.clicked.connect(self.mtk_sip_decode.emit)
        row1.addWidget(self.mtk_sip_decode_btn)
        
        row1.addStretch()
        card_layout.addLayout(row1)
        
        # 第二行：高通工具
        row2 = QHBoxLayout()
        qualcomm_label = QLabel(self.lang_manager.tr("Qualcomm:"))
        qualcomm_label.setFixedWidth(90)  # 固定宽度，与MTK标签对齐
        row2.addWidget(qualcomm_label)
        
        self.extract_pcap_from_qualcomm_log_btn = QPushButton(self.lang_manager.tr("高通log提取pcap"))
        self.extract_pcap_from_qualcomm_log_btn.clicked.connect(self.extract_pcap_from_qualcomm_log.emit)
        row2.addWidget(self.extract_pcap_from_qualcomm_log_btn)
        
        self.lock_cell_btn = QPushButton("📱 " + self.lang_manager.tr("高通lock cell"))
        self.lock_cell_btn.setToolTip(self.lang_manager.tr("高通lock cell - 锁定高通设备到指定的小区"))
        self.lock_cell_btn.clicked.connect(self.show_lock_cell_dialog.emit)
        row2.addWidget(self.lock_cell_btn)
        
        self.qc_nv_btn = QPushButton("📊 " + self.lang_manager.tr("高通NV"))
        self.qc_nv_btn.clicked.connect(self.show_qc_nv_dialog.emit)
        row2.addWidget(self.qc_nv_btn)
        
        row2.addStretch()
        card_layout.addLayout(row2)
        
        v.addWidget(card)
        
        return container
        
    def create_adblog_group(self):
        """创建 ADB Log 控制组（现代结构：QLabel + QFrame）"""
        # 容器
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        
        # 标题
        title = QLabel(self.lang_manager.tr("ADB Log 控制"))
        title.setProperty("class", "section-title")
        v.addWidget(title)
        
        # 卡片
        card = QFrame()
        card.setObjectName("card")
        add_card_shadow(card)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 1, 10, 1)
        card_layout.setSpacing(8)
        
        # 第一行：ADB Log
        row1 = QHBoxLayout()
        adb_log_label = QLabel("ADB Log:")
        adb_log_label.setFixedWidth(90)  # 固定宽度，确保与Google日志标签对齐
        row1.addWidget(adb_log_label)
        
        self.adblog_online_btn = QPushButton(self.lang_manager.tr("连线log"))
        self.adblog_online_btn.clicked.connect(self.adblog_online_start.emit)
        row1.addWidget(self.adblog_online_btn)
        
        self.adblog_offline_btn = QPushButton(self.lang_manager.tr("离线log"))
        self.adblog_offline_btn.clicked.connect(self.adblog_start.emit)
        row1.addWidget(self.adblog_offline_btn)
        
        self.adblog_export_btn = QPushButton(self.lang_manager.tr("导出"))
        self.adblog_export_btn.clicked.connect(self.adblog_export.emit)
        row1.addWidget(self.adblog_export_btn)
        
        self.tcpdump_btn = QPushButton("TCPDUMP")
        self.tcpdump_btn.clicked.connect(self.tcpdump_show_dialog.emit)
        row1.addWidget(self.tcpdump_btn)
        
        row1.addStretch()
        card_layout.addLayout(row1)
        
        # 第二行：Google 日志
        row2 = QHBoxLayout()
        google_log_label = QLabel(self.lang_manager.tr("Google日志:"))
        google_log_label.setFixedWidth(90)  # 固定宽度，与ADB Log标签对齐
        row2.addWidget(google_log_label)
        
        self.google_log_btn = QPushButton(self.lang_manager.tr("Google 日志"))
        self.google_log_btn.clicked.connect(self.google_log_toggle.emit)
        row2.addWidget(self.google_log_btn)
        
        self.aee_log_btn = QPushButton("AEE Log")
        self.aee_log_btn.clicked.connect(self.aee_log_start.emit)
        row2.addWidget(self.aee_log_btn)
        
        self.bugreport_generate_btn = QPushButton(self.lang_manager.tr("生成 Bugreport"))
        self.bugreport_generate_btn.clicked.connect(self.bugreport_generate.emit)
        row2.addWidget(self.bugreport_generate_btn)
        
        self.bugreport_pull_btn = QPushButton("Pull Bugreport")
        self.bugreport_pull_btn.clicked.connect(self.bugreport_pull.emit)
        row2.addWidget(self.bugreport_pull_btn)
        
        self.bugreport_delete_btn = QPushButton(self.lang_manager.tr("删除 Bugreport"))
        self.bugreport_delete_btn.clicked.connect(self.bugreport_delete.emit)
        row2.addWidget(self.bugreport_delete_btn)
        
        row2.addStretch()
        card_layout.addLayout(row2)
        
        v.addWidget(card)
        
        return container
    
    def set_online_mode_started(self):
        """连线模式已启动，改变按钮状态"""
        stop_text = self.lang_manager.tr("停止")
        print(f"{self.tr('设置连线log按钮文本为: ')}'{stop_text}'")
        self.adblog_online_btn.setText(stop_text)
        self.adblog_online_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 5px 15px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
    
    def set_online_mode_stopped(self):
        """连线模式已停止，恢复按钮状态"""
        self.adblog_online_btn.setText(self.lang_manager.tr("连线log"))
        self.adblog_online_btn.setStyleSheet("")
    
    def refresh_texts(self, lang_manager=None):
        """刷新所有文本（用于语言切换）"""
        if lang_manager:
            self.lang_manager = lang_manager
        
        if not self.lang_manager:
            return
        
        # 刷新MTKLOG控制按钮
        if hasattr(self, 'mtklog_start_btn'):
            self.mtklog_start_btn.setText(self.lang_manager.tr("开启"))
        if hasattr(self, 'mtklog_stop_export_btn'):
            self.mtklog_stop_export_btn.setText(self.lang_manager.tr("停止&导出"))
        if hasattr(self, 'mtklog_delete_btn'):
            self.mtklog_delete_btn.setText(self.lang_manager.tr("删除"))
        if hasattr(self, 'mtklog_mode_btn'):
            self.mtklog_mode_btn.setText(self.lang_manager.tr("Logger设置"))
        if hasattr(self, 'mtklog_mode_menu'):
            # 更新菜单项文本
            for action in self.mtklog_mode_menu.actions():
                if "设置log size" in action.text() or "Set log size" in action.text():
                    action.setText(self.lang_manager.tr("设置log size"))
                elif "SD模式" in action.text() or "SD Mode" in action.text():
                    action.setText(self.lang_manager.tr("SD模式"))
                elif "USB模式" in action.text() or "USB Mode" in action.text():
                    action.setText(self.lang_manager.tr("USB模式"))
        # if hasattr(self, 'mtklog_install_btn'):
        #     self.mtklog_install_btn.setText(self.lang_manager.tr("安装MTKLOGGER"))
        
        # 刷新ADB Log控制按钮
        if hasattr(self, 'adblog_online_btn'):
            if self.adblog_online_btn.text() in ["连线log", "Online Log"]:
                self.adblog_online_btn.setText(self.lang_manager.tr("连线log"))
            elif self.adblog_online_btn.text() in ["停止", "Stop"]:
                self.adblog_online_btn.setText(self.lang_manager.tr("停止"))
        if hasattr(self, 'adblog_offline_btn'):
            self.adblog_offline_btn.setText(self.lang_manager.tr("离线log"))
        if hasattr(self, 'adblog_export_btn'):
            self.adblog_export_btn.setText(self.lang_manager.tr("导出"))
        
        # 刷新其他按钮
        if hasattr(self, 'telephony_btn'):
            self.telephony_btn.setText(self.lang_manager.tr("启用Telephony日志"))
        if hasattr(self, 'google_log_btn'):
            if "Google" in self.google_log_btn.text():
                self.google_log_btn.setText(self.lang_manager.tr("Google 日志"))
            elif "停止" in self.google_log_btn.text():
                self.google_log_btn.setText(self.lang_manager.tr("停止 Google 日志"))
        if hasattr(self, 'bugreport_generate_btn'):
            self.bugreport_generate_btn.setText(self.lang_manager.tr("生成 Bugreport"))
        if hasattr(self, 'bugreport_pull_btn'):
            self.bugreport_pull_btn.setText(self.lang_manager.tr("拉取 Bugreport"))
        if hasattr(self, 'bugreport_delete_btn'):
            self.bugreport_delete_btn.setText(self.lang_manager.tr("删除 Bugreport"))
        if hasattr(self, 'aee_log_start_btn'):
            self.aee_log_start_btn.setText(self.lang_manager.tr("AEE日志"))
        if hasattr(self, 'tcpdump_btn'):
            self.tcpdump_btn.setText(self.lang_manager.tr("TCPDUMP"))
        
        # 刷新log操作按钮
        if hasattr(self, 'merge_mtklog_btn'):
            self.merge_mtklog_btn.setText(self.lang_manager.tr("合并MTKlog"))
        if hasattr(self, 'extract_pcap_from_mtklog_btn'):
            self.extract_pcap_from_mtklog_btn.setText(self.lang_manager.tr("MTKlog提取pcap"))
        if hasattr(self, 'merge_pcap_btn'):
            self.merge_pcap_btn.setText(self.lang_manager.tr("合并PCAP"))
        if hasattr(self, 'mtk_sip_decode_btn'):
            self.mtk_sip_decode_btn.setText(self.lang_manager.tr("MTK SIP DECODE"))
        
        # 刷新Qualcomm组按钮
        if hasattr(self, 'extract_pcap_from_qualcomm_log_btn'):
            self.extract_pcap_from_qualcomm_log_btn.setText(self.lang_manager.tr("高通log提取pcap"))
        if hasattr(self, 'lock_cell_btn'):
            self.lock_cell_btn.setText("📱 " + self.lang_manager.tr("高通lock cell"))
        if hasattr(self, 'qc_nv_btn'):
            self.qc_nv_btn.setText("📊 " + self.lang_manager.tr("高通NV"))
        
        # 刷新组标题标签
        self._refresh_section_titles()
    
    def _refresh_section_titles(self):
        """刷新组标题标签"""
        # 查找所有QLabel并刷新标题
        for label in self.findChildren(QLabel):
            current_text = label.text()
            # 根据当前文本匹配对应的翻译
            if current_text in ["LOG控制", "MTKLOG Control"]:
                label.setText(self.lang_manager.tr("LOG控制"))
            elif current_text in ["ADB Log 控制", "ADB Log Control"]:
                label.setText(self.lang_manager.tr("ADB Log 控制"))
            elif current_text in ["模式:", "Mode:"]:
                label.setText(self.lang_manager.tr("模式:"))
            elif current_text in ["Google日志:", "Google Log:"]:
                label.setText(self.lang_manager.tr("Google日志:"))
            elif current_text in ["Qualcomm工具:", "Qualcomm Tools:"]:
                label.setText(self.lang_manager.tr("Qualcomm工具:"))

