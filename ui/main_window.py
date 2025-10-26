#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口
"""

import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                              QSplitter, QTabWidget, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
from ui.menu_bar import DisplayLinesDialog
from ui.tools_config_dialog import ToolsConfigDialog
from core.debug_logger import logger

from ui.toolbar import DeviceToolBar
from ui.widgets.log_viewer import LogViewer
from ui.tabs.log_control_tab import LogControlTab
from ui.tabs.log_filter_tab import LogFilterTab
from ui.tabs.network_info_tab import NetworkInfoTab
from ui.tabs.tmo_cc_tab import TMOCCTab
from ui.tabs.tmo_echolocate_tab import TMOEcholocateTab
from ui.tabs.background_data_tab import BackgroundDataTab
from ui.tabs.app_operations_tab import AppOperationsTab
from ui.tabs.other_tab import OtherTab
from ui.tabs.sim_tab import SimTab
from core.device_manager import PyQtDeviceManager
from core.mtklog_manager import PyQtMTKLogManager
from core.adblog_manager import PyQtADBLogManager
from core.log_processor import PyQtLogProcessor
from core.network_info_manager import PyQtNetworkInfoManager
from core.screenshot_manager import PyQtScreenshotManager
from core.video_manager import VideoManager
from core.tcpdump_manager import PyQtTCPDumpManager
from core.log_utilities import PyQtBugreportManager
from core.aee_log_manager import PyQtAEELogManager
from core.google_log_manager import PyQtGoogleLogManager
from core.enable_telephony_manager import PyQtTelephonyManager
from core.tmo_cc_manager import PyQtTMOCCManager
from core.echolocate_manager import PyQtEcholocateManager
from core.device_operations import (
    PyQtBackgroundDataManager,
    PyQtAppOperationsManager,
    PyQtDeviceInfoManager,
    PyQtHeraConfigManager,
    PyQtOtherOperationsManager
)
from core.theme_manager import ThemeManager
from core.custom_button_manager import CustomButtonManager
from core.log_keyword_manager import LogKeywordManager
from core.language_manager import LanguageManager
from core.tab_config_manager import TabConfigManager


class MainWindow(QMainWindow):
    """主窗口类"""
    
    # 信号定义
    device_changed = pyqtSignal(str)
    append_log = pyqtSignal(str, str)  # text, color
    update_status = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
        # 初始化变量
        self.selected_device = ""
        
        # 初始化语言管理器
        self.lang_manager = LanguageManager(self)
        
        # 初始化设备管理器
        self.device_manager = PyQtDeviceManager(self)
        
        # 显示友好的加载界面
        self._show_loading_screen()
        
        # 初始化所有管理器
        self._init_managers()
        
        # 设置UI（但不显示主窗口）
        self.setup_ui()
        
        # 加载主题
        self.theme_manager.load_theme("dark")
        
        # 连接信号槽
        self.setup_connections()
        
        # 根据保存的语言设置刷新UI
        self._refresh_all_ui_texts()
        
        # 设置log_processor的log_viewer引用
        self.log_processor.set_log_viewer(self.log_viewer)
        
        # 加载所有Tab的自定义按钮
        self.load_custom_buttons_for_all_tabs()
        
        # 连接自定义按钮管理器信号
        self.custom_button_manager.buttons_updated.connect(self.on_custom_buttons_updated)
        
        # 隐藏加载界面，显示主界面
        self._hide_loading_screen()
        
        # 异步刷新设备列表，避免阻塞UI显示
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self.device_manager.refresh_devices)
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def _set_window_icon(self):
        """设置窗口图标"""
        from PyQt5.QtGui import QIcon
        import sys
        import os
        
        # 尝试设置窗口图标
        if hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS'):
            # PyInstaller 环境
            icon_path = os.path.join(sys._MEIPASS, 'icon.ico')
        else:
            # 开发环境
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'icon.ico')
        
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            logger.info(f"窗口图标已设置: {icon_path}")
        else:
            logger.warning(f"图标文件不存在: {icon_path}")
    
    def _show_loading_screen(self):
        """显示友好的加载界面"""
        from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget, QProgressBar
        from PyQt5.QtCore import Qt, QTimer
        from PyQt5.QtGui import QFont
        
        # 创建加载窗口
        self.loading_window = QWidget()
        self.loading_window.setWindowTitle(self.lang_manager.tr("手机测试辅助工具"))
        self.loading_window.setFixedSize(400, 200)
        self.loading_window.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # 设置窗口居中
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.loading_window.width()) // 2
        y = (screen.height() - self.loading_window.height()) // 2
        self.loading_window.move(x, y)
        
        # 设置样式
        self.loading_window.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                border-radius: 10px;
            }
        """)
        
        # 创建布局
        layout = QVBoxLayout(self.loading_window)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        
        # 应用标题
        title_label = QLabel(self.lang_manager.tr("手机测试辅助工具"))
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #4CAF50; margin-bottom: 10px;")
        
        # 加载提示
        loading_label = QLabel(self.lang_manager.tr("正在初始化..."))
        loading_label.setAlignment(Qt.AlignCenter)
        loading_label.setStyleSheet("color: #cccccc; font-size: 14px;")
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 无限进度条
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555555;
                border-radius: 5px;
                text-align: center;
                background-color: #1e1e1e;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        
        # 版本信息
        version_label = QLabel("v0.92")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #888888; font-size: 12px;")
        
        # 添加到布局
        layout.addWidget(title_label)
        layout.addWidget(loading_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(version_label)
        
        # 显示加载窗口
        self.loading_window.show()
        
        # 强制刷新界面
        QApplication.processEvents()
    
    def _hide_loading_screen(self):
        """隐藏加载界面并显示主窗口"""
        if hasattr(self, 'loading_window'):
            self.loading_window.close()
            self.loading_window = None
        
        # 显示主窗口
        self.showMaximized()
        
    def _init_managers(self):
        """初始化所有管理器"""
        # 初始化设备工具类
        from core.utilities import DeviceUtilities
        self.device_utilities = DeviceUtilities(self.device_manager, self)
        self.device_utilities.status_message.connect(self._on_device_status_message)
        self.device_utilities.reboot_started.connect(self._on_reboot_started)
        self.device_utilities.reboot_finished.connect(self._on_reboot_finished)
        
        # 初始化MTKLOG管理器
        self.mtklog_manager = PyQtMTKLogManager(self.device_manager, self)
        
        # 初始化ADB Log管理器
        self.adblog_manager = PyQtADBLogManager(self.device_manager, self)
        
        # 初始化Log过滤管理器
        self.log_processor = PyQtLogProcessor(self.device_manager, self)
        
        # 初始化网络信息管理器
        self.network_info_manager = PyQtNetworkInfoManager(self.device_manager, self)
        
        # 初始化截图管理器
        self.screenshot_manager = PyQtScreenshotManager(self.device_manager, self)
        
        # 初始化录制管理器
        self.video_manager = VideoManager(self.device_manager, self)
        
        # 初始化其他管理器
        self.tcpdump_manager = PyQtTCPDumpManager(self.device_manager, self)
        self.telephony_manager = PyQtTelephonyManager(self.device_manager, self)
        self.google_log_manager = PyQtGoogleLogManager(
            self.device_manager, 
            parent=self,
            adblog_manager=self.adblog_manager, 
            video_manager=self.video_manager
        )
        self.aee_log_manager = PyQtAEELogManager(self.device_manager, self)
        self.bugreport_manager = PyQtBugreportManager(self.device_manager, self)
        
        # 初始化TMO CC管理器
        self.tmo_cc_manager = PyQtTMOCCManager(self.device_manager, self)
        
        # 初始化Echolocate管理器
        self.echolocate_manager = PyQtEcholocateManager(self.device_manager, self)
        
        # 初始化背景数据管理器
        self.background_data_manager = PyQtBackgroundDataManager(self.device_manager, self)
        
        # 初始化APP操作管理器
        self.app_operations_manager = PyQtAppOperationsManager(self.device_manager, self)
        
        # 初始化设备信息管理器
        self.device_info_manager = PyQtDeviceInfoManager(self.device_manager, self)
        
        # 初始化赫拉配置管理器
        self.hera_config_manager = PyQtHeraConfigManager(self.device_manager, self)
        
        # 初始化其他操作管理器
        self.other_operations_manager = PyQtOtherOperationsManager(self.device_manager, self)
        
        # 添加工具配置属性，供其他管理器访问
        self.tool_config = self.other_operations_manager.tool_config
        
        # 初始化主题管理器
        self.theme_manager = ThemeManager()
        
        # 初始化自定义按钮管理器
        self.custom_button_manager = CustomButtonManager(self)
        
        # 初始化log关键字管理器
        self.log_keyword_manager = LogKeywordManager(self)
        
        # 初始化Tab配置管理器
        self.tab_config_manager = TabConfigManager(self)
        
        # 重新设置CustomButtonManager的tab_config_manager引用
        self.custom_button_manager.tab_config_manager = self.tab_config_manager
        
    def setup_ui(self):
        """设置用户界面"""
        # 设置窗口属性
        self.setWindowTitle(self.lang_manager.tr("手机测试辅助工具 v0.92"))
        self.setGeometry(100, 100, 900, 600)
        
        # 设置窗口图标（任务栏图标）
        self._set_window_icon()
        
        # 不立即显示主窗口，等初始化完成后再显示
        
        # 创建顶部工具栏
        self.toolbar = DeviceToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        
        # 创建中央控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)
        
        # 创建分割器（Tab区域 + 日志区域）
        splitter = QSplitter(Qt.Vertical)
        
        # Tab 区域
        self.tab_widget = QTabWidget()
        
        # 启用Tab拖拽排序
        self.tab_widget.setMovable(True)
        self.tab_widget.tabBar().tabMoved.connect(self._on_tab_moved)
        
        # 添加各个Tab
        self.setup_tabs()
        
        splitter.addWidget(self.tab_widget)
        
        # 日志显示区域
        self.log_viewer = LogViewer()
        splitter.addWidget(self.log_viewer)
        
        # 设置分割比例（Tab区域:日志区域 = 1:2）
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)
        
    def setup_connections(self):
        """连接信号槽"""
        
        # 连接日志追加信号
        self.append_log.connect(self._append_log_handler)
        
        # 连接设备管理器信号
        self.device_manager.devices_updated.connect(self._on_devices_updated)
        self.device_manager.device_selected.connect(self._on_device_selected)
        self.device_manager.status_message.connect(self._on_device_status_message)
        
        # 连接MTKLOG管理器信号
        self.mtklog_manager.mtklog_started.connect(self._on_mtklog_started)
        self.mtklog_manager.mtklog_stopped.connect(self._on_mtklog_stopped)
        self.mtklog_manager.mtklog_deleted.connect(self._on_mtklog_deleted)
        self.mtklog_manager.mtklog_exported.connect(self._on_mtklog_exported)
        self.mtklog_manager.progress_updated.connect(self._on_mtklog_progress)
        self.mtklog_manager.status_message.connect(self._on_mtklog_status)
        
        # 连接ADB Log管理器信号
        self.adblog_manager.adblog_started.connect(self._on_adblog_started)
        self.adblog_manager.adblog_stopped.connect(self._on_adblog_stopped)
        self.adblog_manager.adblog_exported.connect(self._on_adblog_exported)
        self.adblog_manager.status_message.connect(self._on_adblog_status)
        self.adblog_manager.clear_old_logs_required.connect(self._on_clear_old_logs_required)
        self.adblog_manager.online_mode_started.connect(self._on_online_mode_started)
        self.adblog_manager.online_mode_stopped.connect(self._on_online_mode_stopped)
        self.adblog_manager.usb_disconnected.connect(self._on_usb_disconnected)
        self.adblog_manager.usb_reconnected.connect(self._on_usb_reconnected)
        
        # 连接Log过滤管理器信号
        self.log_processor.filtering_started.connect(self._on_filtering_started)
        self.log_processor.filtering_stopped.connect(self._on_filtering_stopped)
        self.log_processor.log_received.connect(self._on_filter_log_received)
        self.log_processor.status_message.connect(self._on_filter_status)
        
        # 连接网络信息管理器信号
        self.network_info_manager.network_info_updated.connect(self._on_network_info_updated)
        self.network_info_manager.ping_result.connect(self._on_ping_result)
        self.network_info_manager.status_message.connect(self._on_network_status)
        self.network_info_manager.network_info_started.connect(self._on_network_info_started)
        self.network_info_manager.network_info_start_failed.connect(self._on_network_info_start_failed)
        self.network_info_manager.ping_started.connect(self._on_ping_started)
        self.network_info_manager.ping_start_failed.connect(self._on_ping_start_failed)
        
        # 连接工具栏信号
        self.toolbar.device_changed.connect(self._on_device_changed)
        self.toolbar.refresh_clicked.connect(self._on_refresh_devices)
        self.toolbar.screenshot_clicked.connect(self._on_screenshot)
        self.toolbar.record_toggled.connect(self._on_record_toggled)
        self.toolbar.reboot_clicked.connect(self._on_reboot_device)
        self.toolbar.root_remount_clicked.connect(self._on_root_remount)
        self.toolbar.theme_toggled.connect(self._on_theme_toggled)
        self.toolbar.adb_command_executed.connect(self._on_adb_command_executed)
        
        # 连接语言管理器信号
        self.lang_manager.language_changed.connect(self._on_language_changed)
        
        # 设置快捷键
        self._setup_shortcuts()
        
        # 连接截图管理器信号
        self.screenshot_manager.screenshot_completed.connect(self._on_screenshot_completed)
        self.screenshot_manager.progress_updated.connect(self._on_screenshot_progress)
        self.screenshot_manager.status_message.connect(self._on_screenshot_status)
        
        # 连接录制管理器信号
        self.video_manager.recording_started.connect(self._on_recording_started)
        self.video_manager.recording_stopped.connect(self._on_recording_stopped)
        self.video_manager.video_saved.connect(self._on_video_saved)
        self.video_manager.status_message.connect(self._on_video_status)
        
        # 连接其他管理器信号
        self.tcpdump_manager.status_message.connect(self._on_tcpdump_status)
        self.telephony_manager.status_message.connect(self._on_telephony_status)
        self.google_log_manager.status_message.connect(self._on_google_log_status)
        self.google_log_manager.google_log_started.connect(self._on_google_log_started)
        self.google_log_manager.google_log_stopped.connect(self._on_google_log_stopped)
        self.aee_log_manager.status_message.connect(self._on_aee_log_status)
        self.bugreport_manager.status_message.connect(self._on_bugreport_status)
        
        # 连接TMO CC管理器信号
        self.tmo_cc_manager.cc_pulled.connect(self._on_cc_pulled)
        self.tmo_cc_manager.cc_pushed.connect(self._on_cc_pushed)
        self.tmo_cc_manager.server_started.connect(self._on_server_started)
        self.tmo_cc_manager.status_message.connect(self._on_tmo_cc_status)
        
        # 连接Echolocate管理器信号
        self.echolocate_manager.echolocate_installed.connect(self._on_echolocate_installed)
        self.echolocate_manager.echolocate_triggered.connect(self._on_echolocate_triggered)
        self.echolocate_manager.file_pulled.connect(self._on_echolocate_file_pulled)
        self.echolocate_manager.file_deleted.connect(self._on_echolocate_file_deleted)
        self.echolocate_manager.status_message.connect(self._on_echolocate_status)
        self.echolocate_manager.log_message.connect(self._on_echolocate_log)
        
        # 连接背景数据管理器信号
        self.background_data_manager.status_message.connect(self._on_background_data_status)
        self.background_data_manager.log_message.connect(self._on_background_data_log)
        
        # 连接APP操作管理器信号
        self.app_operations_manager.status_message.connect(self._on_app_operations_status)
        
        # 连接设备信息管理器信号
        self.device_info_manager.status_message.connect(self._on_device_info_status)
        
        # 连接赫拉配置管理器信号
        self.hera_config_manager.status_message.connect(self._on_hera_config_status)
        
        # 连接其他操作管理器信号
        self.other_operations_manager.status_message.connect(self._on_other_operations_status)
        
        # 连接 SIM Tab 信号
        self.sim_tab.status_message.connect(self._on_sim_status_message)
        
        # 连接 Log控制 Tab 信号
        self.log_control_tab.mtklog_start.connect(self._on_mtklog_start)
        self.log_control_tab.mtklog_stop_export.connect(self._on_mtklog_stop_export)
        self.log_control_tab.mtklog_delete.connect(self._on_mtklog_delete)
        self.log_control_tab.mtklog_set_log_size.connect(self._on_mtklog_set_log_size)
        self.log_control_tab.mtklog_sd_mode.connect(self._on_mtklog_sd_mode)
        self.log_control_tab.mtklog_usb_mode.connect(self._on_mtklog_usb_mode)
        self.log_control_tab.mtklog_install.connect(self._on_mtklog_install)
        self.log_control_tab.adblog_start.connect(self._on_adblog_start)
        self.log_control_tab.adblog_online_start.connect(self._on_adblog_online_start)
        self.log_control_tab.adblog_export.connect(self._on_adblog_export)
        self.log_control_tab.telephony_enable.connect(self._on_telephony_enable)
        self.log_control_tab.google_log_toggle.connect(self._on_google_log_toggle)
        self.log_control_tab.bugreport_generate.connect(self._on_bugreport_generate)
        self.log_control_tab.bugreport_pull.connect(self._on_bugreport_pull)
        self.log_control_tab.bugreport_delete.connect(self._on_bugreport_delete)
        self.log_control_tab.aee_log_start.connect(self._on_aee_log_start)
        self.log_control_tab.tcpdump_show_dialog.connect(self._on_tcpdump_show_dialog)
        
        # 连接 Log过滤 Tab 信号
        self.log_filter_tab.start_filtering.connect(self._on_start_filtering)
        self.log_filter_tab.stop_filtering.connect(self._on_stop_filtering)
        self.log_filter_tab.manage_log_keywords.connect(self._on_manage_log_keywords)
        self.log_filter_tab.clear_logs.connect(self._on_clear_logs)
        self.log_filter_tab.clear_device_logs.connect(self._on_clear_device_logs)
        self.log_filter_tab.show_display_lines_dialog.connect(self._on_show_display_lines_dialog)
        self.log_filter_tab.save_logs.connect(self._on_save_logs)
        
        # Log处理器信号连接
        self.log_processor.keyword_loaded.connect(self._on_keyword_loaded)
        self.log_processor.filter_state_changed.connect(self._on_filter_state_changed)
        
        # 连接 网络信息 Tab 信号
        self.network_info_tab.start_network_info.connect(self._on_start_network_info)
        self.network_info_tab.stop_network_info.connect(self._on_stop_network_info)
        self.network_info_tab.start_ping.connect(self._on_start_ping)
        self.network_info_tab.stop_ping.connect(self._on_stop_ping)
        
        # 连接 TMO CC Tab 信号
        self.tmo_cc_tab.push_cc_file.connect(self._on_push_cc_file)
        self.tmo_cc_tab.pull_cc_file.connect(self._on_pull_cc_file)
        self.tmo_cc_tab.simple_filter.connect(self._on_simple_filter)
        self.tmo_cc_tab.complete_filter.connect(self._on_complete_filter)
        self.tmo_cc_tab.prod_server.connect(self._on_prod_server)
        self.tmo_cc_tab.stg_server.connect(self._on_stg_server)
        self.tmo_cc_tab.clear_logs.connect(self._on_clear_logs)
        self.tmo_cc_tab.clear_device_logs.connect(self._on_clear_device_logs)
        
        # 连接 TMO Echolocate Tab 信号
        self.tmo_echolocate_tab.install_echolocate.connect(self._on_install_echolocate)
        self.tmo_echolocate_tab.trigger_echolocate.connect(self._on_trigger_echolocate)
        self.tmo_echolocate_tab.pull_echolocate_file.connect(self._on_pull_echolocate_file)
        self.tmo_echolocate_tab.delete_echolocate_file.connect(self._on_delete_echolocate_file)
        self.tmo_echolocate_tab.get_echolocate_version.connect(self._on_get_echolocate_version)
        self.tmo_echolocate_tab.filter_callid.connect(self._on_filter_callid)
        self.tmo_echolocate_tab.filter_callstate.connect(self._on_filter_callstate)
        self.tmo_echolocate_tab.filter_uicallstate.connect(self._on_filter_uicallstate)
        self.tmo_echolocate_tab.filter_allcallstate.connect(self._on_filter_allcallstate)
        self.tmo_echolocate_tab.filter_ims_signalling.connect(self._on_filter_ims_signalling)
        self.tmo_echolocate_tab.filter_allcallflow.connect(self._on_filter_allcallflow)
        self.tmo_echolocate_tab.filter_voice_intent.connect(self._on_filter_voice_intent)
        
        # 连接 24小时背景数据 Tab 信号
        self.background_data_tab.configure_phone.connect(self._on_configure_phone)
        self.background_data_tab.analyze_logs.connect(self._on_analyze_logs)
        
        # 连接 APP操作 Tab 信号
        self.app_operations_tab.query_package.connect(self._on_query_package)
        self.app_operations_tab.query_package_name.connect(self._on_query_package_name)
        self.app_operations_tab.query_install_path.connect(self._on_query_install_path)
        self.app_operations_tab.pull_apk.connect(self._on_pull_apk)
        self.app_operations_tab.push_apk.connect(self._on_push_apk)
        self.app_operations_tab.install_apk.connect(self._on_install_apk)
        self.app_operations_tab.view_processes.connect(self._on_view_processes)
        self.app_operations_tab.dump_app.connect(self._on_dump_app)
        self.app_operations_tab.enable_app.connect(self._on_enable_app)
        self.app_operations_tab.disable_app.connect(self._on_disable_app)
        
        # 连接 其他 Tab 信号
        self.other_tab.show_device_info_dialog.connect(self._on_show_device_info_dialog)
        self.other_tab.set_screen_timeout.connect(self._on_set_screen_timeout)
        self.other_tab.merge_mtklog.connect(self._on_merge_mtklog)
        self.other_tab.extract_pcap_from_mtklog.connect(self._on_extract_pcap_from_mtklog)
        self.other_tab.merge_pcap.connect(self._on_merge_pcap)
        self.other_tab.extract_pcap_from_qualcomm_log.connect(self._on_extract_pcap_from_qualcomm_log)
        self.other_tab.configure_hera.connect(self._on_configure_hera)
        self.other_tab.configure_collect_data.connect(self._on_configure_collect_data)
        self.other_tab.show_input_text_dialog.connect(self._on_show_input_text_dialog)
        self.other_tab.show_tools_config_dialog.connect(self._on_show_tools_config_dialog)
        self.other_tab.show_display_lines_dialog.connect(self._on_show_display_lines_dialog)
        self.other_tab.show_unified_manager.connect(self.show_unified_manager_dialog)
        self.other_tab.show_secret_code_dialog.connect(self.show_secret_code_dialog)
        self.other_tab.show_lock_cell_dialog.connect(self.show_lock_cell_dialog)
        
        # 连接Tab配置管理器信号
        self.tab_config_manager.tab_config_updated.connect(self._on_tab_config_updated)
        
    def setup_tabs(self):
        """设置Tab页面"""
        logger.info(self.lang_manager.tr("开始初始化所有Tab页面..."))
        
        try:
            # 获取Tab配置
            tab_order = self.tab_config_manager.get_tab_order()
            tab_visibility = self.tab_config_manager.get_tab_visibility()
            all_tabs = self.tab_config_manager.get_all_tabs()
            
            
            # 创建tab实例映射
            tab_instances = {}
            
            # 初始化所有默认Tab
            
            self.log_control_tab = LogControlTab()
            self.log_control_tab.tab_id = 'log_control'  # 添加tab_id属性
            tab_instances['log_control'] = self.log_control_tab
            
            self.log_filter_tab = LogFilterTab()
            self.log_filter_tab.tab_id = 'log_filter'  # 添加tab_id属性
            tab_instances['log_filter'] = self.log_filter_tab
            
            self.network_info_tab = NetworkInfoTab()
            self.network_info_tab.tab_id = 'network_info'  # 添加tab_id属性
            tab_instances['network_info'] = self.network_info_tab
            
            self.tmo_cc_tab = TMOCCTab()
            self.tmo_cc_tab.tab_id = 'tmo_cc'  # 添加tab_id属性
            tab_instances['tmo_cc'] = self.tmo_cc_tab
            
            self.tmo_echolocate_tab = TMOEcholocateTab()
            self.tmo_echolocate_tab.tab_id = 'tmo_echolocate'  # 添加tab_id属性
            tab_instances['tmo_echolocate'] = self.tmo_echolocate_tab
            
            self.background_data_tab = BackgroundDataTab()
            self.background_data_tab.tab_id = 'background_data'  # 添加tab_id属性
            tab_instances['background_data'] = self.background_data_tab
            
            self.app_operations_tab = AppOperationsTab()
            self.app_operations_tab.tab_id = 'app_operations'  # 添加tab_id属性
            tab_instances['app_operations'] = self.app_operations_tab
            
            self.other_tab = OtherTab()
            self.other_tab.tab_id = 'other'  # 添加tab_id属性
            tab_instances['other'] = self.other_tab
            
            self.sim_tab = SimTab(self)
            self.sim_tab.tab_id = 'sim'  # 添加tab_id属性
            tab_instances['sim'] = self.sim_tab
            
            # 初始化自定义Tab
            for custom_tab in self.tab_config_manager.custom_tabs:
                tab_id = custom_tab['id']
                tab_name = custom_tab['name']
                
                # 创建自定义Tab实例（这里可以扩展为动态创建）
                custom_tab_instance = self._create_custom_tab_instance(custom_tab)
                if custom_tab_instance:
                    tab_instances[tab_id] = custom_tab_instance
            
            # 按照配置的顺序添加Tab
            for tab_id in tab_order:
                if tab_id in tab_instances and tab_visibility.get(tab_id, True):
                    tab_instance = tab_instances[tab_id]
                    tab_name = self._get_tab_name(tab_id, all_tabs)
                    
                    self.tab_widget.addTab(tab_instance, tab_name)
            
            logger.info(self.lang_manager.tr("所有Tab页面初始化完成"))
            
        except Exception as e:
            logger.exception(self.lang_manager.tr("Tab页面初始化失败"))
            raise
    
    def _get_tab_name(self, tab_id, all_tabs):
        """获取Tab名称"""
        # 首先在all_tabs中查找
        for tab in all_tabs:
            if tab['id'] == tab_id:
                return tab['name']
        
        # 如果找不到，使用默认映射（直接使用中文名称，避免翻译失败）
        default_names = {
            'log_control': 'Log控制',
            'log_filter': 'Log过滤',
            'network_info': '网络信息',
            'tmo_cc': 'TMO CC',
            'tmo_echolocate': 'TMO Echolocate',
            'background_data': '24小时背景数据',
            'app_operations': 'APP操作',
            'other': '其他',
            'sim': 'SIM'
        }
        
        result = default_names.get(tab_id, tab_id)
        return result
    
    def _create_custom_tab_instance(self, custom_tab):
        """创建自定义Tab实例"""
        try:
            from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QScrollArea, QFrame
            from PyQt5.QtCore import Qt
            
            widget = QWidget()
            widget.tab_id = custom_tab['id']  # 设置tab_id属性
            layout = QVBoxLayout(widget)
            
            # 添加Tab标题和描述
            title_label = QLabel(f"{self.tr('自定义Tab:')} {custom_tab['name']}")
            title_label.setProperty("class", "section-title")
            title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px 0;")
            layout.addWidget(title_label)
            
            if custom_tab.get('description'):
                desc_label = QLabel(f"{self.tr('描述:')} {custom_tab['description']}")
                desc_label.setWordWrap(True)
                layout.addWidget(desc_label)
            
            # 创建滚动区域
            scroll_area = QScrollArea()
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout(scroll_widget)
            
            # 添加自定义Card
            custom_cards = self.tab_config_manager.get_custom_cards_for_tab(custom_tab['id'])
            for card in custom_cards:
                card_group = self._create_custom_card_group(card)
                if card_group:
                    scroll_layout.addWidget(card_group)
            
            # 如果没有Card，添加提示
            if not custom_cards:
                no_cards_label = QLabel(self.tr("暂无自定义Card，请在Tab管理中创建"))
                no_cards_label.setStyleSheet("color: #666; font-style: italic;")
                scroll_layout.addWidget(no_cards_label)
            
            scroll_layout.addStretch()
            scroll_area.setWidget(scroll_widget)
            scroll_area.setWidgetResizable(True)
            layout.addWidget(scroll_area)
            
            return widget
        except Exception as e:
            logger.exception(f"{self.tr('创建自定义Tab实例失败:')} {e}")
            return None
    
    def _create_custom_card_group(self, card):
        """创建自定义Card组（仅创建结构，按钮由统一方法添加）"""
        try:
            from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel
            from PyQt5.QtCore import Qt
            
            group = QGroupBox(card['name'])
            group.setProperty('custom_card', True)  # 标记为自定义Card
            layout = QVBoxLayout(group)
            
            # 添加Card描述
            if card.get('description'):
                desc_label = QLabel(card['description'])
                desc_label.setWordWrap(True)
                desc_label.setStyleSheet("color: #666; margin-bottom: 10px;")
                layout.addWidget(desc_label)
            
            # 添加空的按钮布局（按钮由load_custom_buttons_for_all_tabs统一添加）
            button_layout = QHBoxLayout()
            button_layout.addStretch()  # 添加stretch，按钮会插入到stretch之前
            layout.addLayout(button_layout)
            
            logger.debug(f"{self.tr('创建自定义Card组:')} '{card['name']}' {self.tr('（按钮稍后添加）')}")
            
            return group
        except Exception as e:
            logger.exception(f"{self.tr('创建自定义Card组失败:')} {e}")
            return None
    
    def _get_tab_name_by_id(self, tab_id):
        """根据Tab ID获取Tab名称"""
        all_tabs = self.tab_config_manager.get_all_tabs()
        for tab in all_tabs:
            if tab['id'] == tab_id:
                return tab['name']
        return tab_id
    
    def _find_custom_card_by_name(self, card_name):
        """根据Card名称查找自定义Card"""
        try:
            for card in self.tab_config_manager.custom_cards:
                if card['name'] == card_name:
                    return card
            return None
        except Exception as e:
            logger.exception(f"{self.tr('查找自定义Card失败:')} {e}")
            return None
    
        
    def _append_log_handler(self, text, color=None):
        """日志追加处理"""
        self.log_viewer.append_log(text, color)
        
    def _on_device_changed(self, device):
        """设备改变处理"""
        self.selected_device = device
        self.device_manager.set_selected_device(device)
        self.append_log.emit(f"{self.lang_manager.tr('切换到设备:')} {device}\n", None)
        
    def _on_refresh_devices(self):
        """刷新设备列表"""
        self.append_log.emit(self.lang_manager.tr("刷新设备列表...") + "\n", None)
        self.device_manager.refresh_devices()
        
    def _on_devices_updated(self, devices):
        """设备列表更新"""
        self.toolbar.set_device_list(devices)
        
    def _on_device_selected(self, device):
        """设备选择"""
        self.selected_device = device
        
    def _on_device_status_message(self, message):
        """设备状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    def _on_sim_status_message(self, message):
        """SIM Tab状态消息"""
        self.append_log.emit(f"[SIM] {message}\n", None)
        
    def _on_screenshot(self):
        """截图处理"""
        self.screenshot_manager.take_screenshot()
        
    def _on_record_toggled(self, is_recording):
        """录制切换处理"""
        # 如果按钮被选中，说明用户想开始录制
        if is_recording:
            self.video_manager.start_recording()
        else:
            # 如果按钮被取消选中，说明用户想停止录制
            self.video_manager.stop_recording()
    
    def _on_reboot_device(self):
        """重启设备处理（异步）"""
        self.device_utilities.reboot_device(self)
    
    def _on_reboot_started(self, device):
        """重启开始回调"""
        self.append_log.emit(f"{self.lang_manager.tr('正在重启设备')} {device}...\n", "#FFA500")
        self.statusBar().showMessage(f"{self.lang_manager.tr('正在重启设备')} {device}...")
    
    def _on_reboot_finished(self, success, message):
        """重启完成回调"""
        if success:
            self.append_log.emit(f"✅ {message}\n", "#00FF00")
            self.statusBar().showMessage(self.lang_manager.tr("设备重启命令已执行"))
        else:
            self.append_log.emit(f"❌ {message}\n", "#FF0000")
            self.statusBar().showMessage(self.lang_manager.tr("设备重启失败"))
    
    def _on_root_remount(self):
        """Root&remount处理"""
        import subprocess
        
        device = self.device_manager.selected_device
        if not device:
            self.append_log.emit(self.lang_manager.tr("未选择设备") + "\n", "#FFA500")
            return
        
        # 步骤1: 执行 adb root
        self.append_log.emit(self.lang_manager.tr("执行 adb root...") + "\n", None)
        try:
            result = subprocess.run(
                ["adb", "-s", device, "root"],
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.stdout:
                self.append_log.emit(result.stdout, None)
            if result.stderr:
                self.append_log.emit(result.stderr, None)
                
        except subprocess.TimeoutExpired:
            self.append_log.emit(f"⚠️ {self.lang_manager.tr('adb root 执行超时')}\n", "#FFA500")
            return
        except Exception as e:
            self.append_log.emit("❌ " + self.tr("执行 adb root 失败: ") + str(e) + "\n", "#FF0000")
            return
        
        # 步骤2: 执行 adb remount
        self.append_log.emit(self.lang_manager.tr("执行 adb remount...") + "\n", None)
        try:
            result = subprocess.run(
                ["adb", "-s", device, "remount"],
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            remount_output = ""
            if result.stdout:
                remount_output += result.stdout
                self.append_log.emit(result.stdout, None)
            if result.stderr:
                remount_output += result.stderr
                self.append_log.emit(result.stderr, None)
            
            # 步骤3: 检查输出是否包含"reboot"
            if "reboot" in remount_output.lower():
                # 弹出提示询问用户是否要重启
                reply = QMessageBox.question(
                    self,
                    self.lang_manager.tr('需要重启设备'),
                    '检测到需要重启设备才能使设置生效。\n\n是否立即重启设备？',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.append_log.emit(f"{self.lang_manager.tr('执行 adb reboot...')}\n", None)
                    try:
                        subprocess.run(
                            ["adb", "-s", device, "reboot"],
                            shell=True,
                            capture_output=True,
                            text=True,
                            encoding='utf-8',
                            errors='replace',
                            timeout=5,
                            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                        )
                        self.append_log.emit(self.tr("设备 ") + device + self.tr(" 重启命令已执行") + "\n", None)
                    except Exception as e:
                        self.append_log.emit("❌ " + self.tr("执行 adb reboot 失败: ") + str(e) + "\n", "#FF0000")
                else:
                    self.append_log.emit(f"{self.lang_manager.tr('用户取消重启')}\n", None)
            # else:
            #     self.append_log.emit(f"{self.lang_manager.tr('Root&remount 完成')}\n", None)
                    
        except subprocess.TimeoutExpired:
            self.append_log.emit(f"⚠️ {self.lang_manager.tr('adb remount 执行超时')}\n", "#FFA500")
        except Exception as e:
            self.append_log.emit("❌ " + self.tr("执行 adb remount 失败: ") + str(e) + "\n", "#FF0000")
    
    def _on_theme_toggled(self):
        """主题切换处理"""
        self.theme_manager.toggle_theme()
        current_theme = self.theme_manager.get_current_theme()
        self.toolbar.update_theme_button(current_theme)
        self.append_log.emit(f"{self.tr('已切换到')}{current_theme}{self.tr('主题')}\n", None)
    
    def _on_language_changed(self, new_lang):
        """语言切换处理"""
        self.append_log.emit(f"{self.tr('语言已切换到:')}{self.tr('英文') if new_lang == 'en' else self.tr('中文')}\n", None)
        # 刷新所有UI文本
        self._refresh_all_ui_texts()
    
    def _refresh_all_ui_texts(self):
        """刷新所有UI文本"""
        try:
            # 刷新窗口标题
            self.setWindowTitle(self.lang_manager.tr("手机测试辅助工具 v0.92"))
            
            # 刷新所有Tab标题和内容
            if hasattr(self, 'tab_widget'):
                # 根据Tab的实际内容来设置标题，而不是硬编码
                for i in range(self.tab_widget.count()):
                    tab_widget = self.tab_widget.widget(i)
                    
                    # 根据Tab实例类型设置正确的标题
                    if hasattr(tab_widget, 'tab_id'):
                        tab_id = tab_widget.tab_id
                        # 使用Tab配置管理器获取正确的标题
                        all_tabs = self.tab_config_manager.get_all_tabs()
                        correct_title = self._get_tab_name(tab_id, all_tabs)
                        self.tab_widget.setTabText(i, correct_title)
                        logger.debug(f"刷新Tab标题: 索引={i}, ID={tab_id}, 标题={correct_title}")
                    
                    # 更新Tab内容
                    if hasattr(tab_widget, 'refresh_texts'):
                        tab_widget.refresh_texts(self.lang_manager)
            
            # 刷新工具栏文本
            if hasattr(self, 'toolbar'):
                self.toolbar.refresh_texts(self.lang_manager)
                
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('刷新UI文本失败:')} {e}")
    
    def _on_adb_command_executed(self, command):
        """执行ADB命令"""
        import subprocess
        
        # 黑名单：不支持的持续输出命令
        BLOCKED_COMMANDS = {
            'logcat': '请使用"Log过滤"功能',
            'tcpdump': '请使用"Log控制"标签页的tcpdump功能',
            'ping': '请使用"Network信息"标签页的ping功能',
            'top': '此命令会持续输出，不支持',
            'getevent': '此命令会持续输出，不支持',
            'monkey': '此命令会持续输出，不支持'
        }
        
        # 检查是否包含黑名单命令
        cmd_lower = command.lower()
        for blocked_cmd, hint in BLOCKED_COMMANDS.items():
            if blocked_cmd in cmd_lower:
                self.append_log.emit(f"{self.tr('⚠️ 不支持命令: ')}{command}\n", "#FFA500")
                self.append_log.emit(f"{self.tr('💡 提示: ')}{hint}\n", "#17a2b8")
                return
        
        # 显示命令
        self.append_log.emit(f"{self.tr('执行命令: ')}{command}\n", None)
        
        try:
            # 执行命令
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # 透传输出内容
            if result.stdout:
                self.append_log.emit(result.stdout, None)
            
            if result.stderr:
                self.append_log.emit(result.stderr, None)
                
        except subprocess.TimeoutExpired:
            self.append_log.emit(f"⚠️ {self.lang_manager.tr('命令执行超时（30秒）')}\n", "#FFA500")
            self.append_log.emit(f"💡 {self.lang_manager.tr('如需长时间运行的命令，请使用对应的专门功能')}\n", "#17a2b8")
        except Exception as e:
            self.append_log.emit(f"{self.tr('执行失败: ')}{str(e)}\n", None)
            
    # Log控制 Tab 信号处理
    def _on_mtklog_start(self):
        """MTKLOG 开启"""
        self.append_log.emit(self.lang_manager.tr("开启 MTKLOG...") + "\n", None)
        self.mtklog_manager.start_mtklog()
        
    def _on_mtklog_stop_export(self):
        """MTKLOG 停止并导出"""
        self.append_log.emit(self.lang_manager.tr("停止并导出 MTKLOG...") + "\n", None)
        self.mtklog_manager.stop_and_export_mtklog()
        
    def _on_mtklog_delete(self):
        """MTKLOG 删除"""
        self.append_log.emit(self.lang_manager.tr("删除 MTKLOG...") + "\n", None)
        self.mtklog_manager.delete_mtklog()
    
    def _on_mtklog_set_log_size(self):
        """设置 MTKLOG 大小"""
        self.append_log.emit(self.lang_manager.tr("设置 MTKLOG 大小...") + "\n", None)
        self.mtklog_manager.set_log_size()
        
    def _on_mtklog_sd_mode(self):
        """MTKLOG SD模式"""
        self.append_log.emit(self.lang_manager.tr("设置 MTKLOG SD模式...") + "\n", None)
        self.mtklog_manager.set_sd_mode()
        
    def _on_mtklog_usb_mode(self):
        """MTKLOG USB模式"""
        self.append_log.emit(self.lang_manager.tr("设置 MTKLOG USB模式...") + "\n", None)
        self.mtklog_manager.set_usb_mode()
        
    def _on_mtklog_install(self):
        """安装 MTKLOGGER"""
        self.append_log.emit(self.lang_manager.tr("安装 MTKLOGGER...") + "\n", None)
        self.mtklog_manager.install_mtklogger()
        
    # MTKLOG管理器信号处理
    def _on_mtklog_started(self):
        """MTKLOG启动完成"""
        self.append_log.emit(self.lang_manager.tr("MTKLOG启动成功") + "\n", None)
        
    def _on_mtklog_stopped(self):
        """MTKLOG停止完成"""
        self.append_log.emit(self.lang_manager.tr("MTKLOG已停止") + "\n", None)
        
    def _on_mtklog_deleted(self):
        """MTKLOG删除完成"""
        self.append_log.emit(self.lang_manager.tr("MTKLOG已删除") + "\n", None)
        
    def _on_mtklog_exported(self, export_path):
        """MTKLOG导出完成"""
        self.append_log.emit(f"{self.tr('MTKLOG已导出到: ')}{export_path}\n", None)
        
    def _on_mtklog_progress(self, progress, status):
        """MTKLOG进度更新"""
        self.append_log.emit(f"[{progress}%] {status}\n", None)
        
    def _on_mtklog_status(self, message):
        """MTKLOG状态消息"""
        self.append_log.emit(f"{message}\n", None)
        
    def _on_adblog_start(self):
        """离线ADB Log 开启"""
        print(f"{self.tr('离线ADB Log按钮被点击，当前is_running状态: ')}{self.adblog_manager.is_running}")
        
        # 检查ADB Log是否正在运行
        if self.adblog_manager.is_running:
            print("ADB Log正在运行，无法启动离线模式")
            self.append_log.emit(self.lang_manager.tr("ADB Log已经在运行中，请先停止当前任务\n"), None)
            return
        
        # 获取log名称
        from PyQt5.QtWidgets import QInputDialog
        log_name, ok = QInputDialog.getText(
            self,
            self.lang_manager.tr('输入log名称'),
            self.lang_manager.tr('请输入log名称:\n\n注意: 名称中不能包含空格，空格将被替换为下划线')
        )
        
        if not ok or not log_name:
            return
        
        # 处理log名称：替换空格为下划线
        log_name = log_name.replace(" ", "_")
        
        # 启动离线ADB Log
        self.append_log.emit(f"{self.lang_manager.tr('开启离线ADB Log...')}\n", None)
        self.adblog_manager.start_adblog("offline", log_name)
    
    def _on_adblog_online_start(self):
        """连线ADB Log 开启/停止"""
        print(f"{self.tr('连线ADB Log按钮被点击，当前is_running状态: ')}{self.adblog_manager.is_running}")
        
        # 检查ADB Log是否正在运行
        if self.adblog_manager.is_running:
            print("ADB Log正在运行，执行停止操作")
            # 停止连线logcat进程
            self.adblog_manager.stop_online_adblog()
            return
        
        # 获取log名称
        from PyQt5.QtWidgets import QInputDialog
        log_name, ok = QInputDialog.getText(
            self,
            self.lang_manager.tr('输入log名称'),
            self.lang_manager.tr('请输入log名称:\n\n注意: 名称中不能包含空格，空格将被替换为下划线')
        )
        
        if not ok or not log_name:
            return
        
        # 处理log名称：替换空格为下划线
        log_name = log_name.replace(" ", "_")
        
        # 启动连线ADB Log
        self.append_log.emit(f"{self.lang_manager.tr('开启连线ADB Log...')}\n", None)
        self.adblog_manager.start_adblog("online", log_name)
        
    def _on_adblog_export(self):
        """ADB Log 导出（只处理离线模式）"""
        self.append_log.emit(self.lang_manager.tr("导出 ADB Log...") + "\n", None)
        self.adblog_manager.export_offline_adblog()
        
    # ADB Log管理器信号处理
    def _on_adblog_started(self):
        """ADB Log启动完成"""
        self.append_log.emit(self.lang_manager.tr("ADB Log已启动") + "\n", None)
        
    def _on_adblog_stopped(self):
        """ADB Log停止完成"""
        self.append_log.emit(self.lang_manager.tr("ADB Log已停止") + "\n", None)
        
    def _on_adblog_exported(self, export_path):
        """ADB Log导出完成"""
        self.append_log.emit(f"{self.lang_manager.tr('ADB Log已导出到:')} {export_path}\n", None)
        
    def _on_adblog_status(self, message):
        """ADB Log状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    def _on_clear_old_logs_required(self, device, file_count, txt_files):
        """需要清除旧log文件的提示"""
        from PyQt5.QtWidgets import QMessageBox
        
        # 显示文件名列表（最多显示5个）
        file_list = [os.path.basename(f.strip()) for f in txt_files if f.strip()][:5]
        file_display = '\n'.join(file_list)
        if file_count > 5:
            file_display += '\n...'
        
        reply = QMessageBox.question(
            self,
            self.lang_manager.tr('发现旧log文件'),
            f'在设备 {device} 的 /data/local/tmp 目录中发现 {file_count} 个txt文件:\n\n'
            f'{file_display}\n\n'
            '是否清除这些旧log文件？\n\n'
            '选择"是"：清除所有旧文件，然后输入新文件名\n'
            '选择"否"：保留旧文件，然后输入新文件名',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        # 通知管理器用户的选择
        clear_old = (reply == QMessageBox.Yes)
        self.adblog_manager.handle_clear_old_logs_decision(clear_old)
    
    def _on_online_mode_started(self):
        """连线模式已启动"""
        self.log_control_tab.set_online_mode_started()
    
    def _on_online_mode_stopped(self):
        """连线模式已停止"""
        self.log_control_tab.set_online_mode_stopped()
    
    def _on_usb_disconnected(self, device):
        """USB断开"""
        self.append_log.emit(f"{self.tr('USB断开 - ')}{device}\n", None)
    
    def _on_usb_reconnected(self, device):
        """USB重连"""
        self.append_log.emit(f"{self.tr('USB已重连 - ')}{device}\n", None)
        
    def _on_telephony_enable(self):
        """启用 Telephony"""
        self.telephony_manager.enable_telephony()
        
    def _on_google_log_toggle(self):
        """切换 Google 日志"""
        self.google_log_manager.toggle_google_log()
    
    def _on_google_log_started(self):
        """Google日志已启动，更新按钮状态"""
        self.log_control_tab.google_log_btn.setText(self.lang_manager.tr("停止 Google 日志"))
        self.log_control_tab.google_log_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
    
    def _on_google_log_stopped(self):
        """Google日志已停止，恢复按钮状态"""
        self.log_control_tab.google_log_btn.setText(self.lang_manager.tr("Google 日志"))
        self.log_control_tab.google_log_btn.setStyleSheet("")
        
    def _on_bugreport_generate(self):
        """生成 Bugreport"""
        self.bugreport_manager.generate_bugreport()
        
    def _on_bugreport_pull(self):
        """Pull Bugreport"""
        self.bugreport_manager.pull_bugreport()
        
    def _on_bugreport_delete(self):
        """删除 Bugreport"""
        self.bugreport_manager.delete_bugreport()
        
    def _on_aee_log_start(self):
        """AEE Log"""
        self.aee_log_manager.start_aee_log()
        
    def _on_tcpdump_show_dialog(self):
        """显示 TCPDUMP 对话框"""
        self.tcpdump_manager.show_tcpdump_dialog()
        
    # Log过滤 Tab 信号处理
    def _on_start_filtering(self):
        """开始过滤"""
        keyword = self.log_filter_tab.get_keyword()
        use_regex = self.log_filter_tab.is_use_regex()
        case_sensitive = self.log_filter_tab.is_case_sensitive()
        color_highlight = self.log_filter_tab.is_color_highlight()
        
        self.append_log.emit(f"{self.tr('开始过滤 - 关键字: ')}{keyword}\n", None)
        self.append_log.emit(f"  {self.tr('正则表达式: ')}{use_regex}, {self.tr('区分大小写: ')}{case_sensitive}, {self.tr('彩色高亮: ')}{color_highlight}\n", None)
        
        # 调用Log过滤管理器
        self.log_processor.start_filtering(keyword, use_regex, case_sensitive, color_highlight)
        
    def _on_stop_filtering(self):
        """停止过滤"""
        self.append_log.emit(self.lang_manager.tr("停止过滤...") + "\n", None)
        self.log_processor.stop_filtering()
        
    def _on_manage_log_keywords(self):
        """打开log关键字管理对话框"""
        try:
            from ui.log_keyword_dialog import LogKeywordDialog
            
            dialog = LogKeywordDialog(self.log_keyword_manager, parent=self)
            dialog.exec_()
            
            # 如果用户选择了关键字并点击了"加载到过滤"按钮
            selected_keyword = dialog.get_selected_keyword()
            if selected_keyword:
                self.log_filter_tab.set_keyword(selected_keyword)
                self.append_log.emit(f"✅ {self.tr('已加载关键字: ')}{selected_keyword}\n", "#00FF00")
                
                # 自动开始过滤
                self._on_start_filtering()
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('打开log关键字管理对话框失败:')} {e}")
            QMessageBox.critical(self, self.lang_manager.tr("错误"), f"{self.lang_manager.tr('打开log关键字管理失败')}：{str(e)}")
    
    def _on_keyword_loaded(self, keyword):
        """关键字已加载，更新输入框"""
        self.log_filter_tab.set_keyword(keyword)
    
    def _on_filter_state_changed(self, is_running, current_keyword):
        """过滤状态改变，更新TMO CC Tab的按钮状态"""
        self.tmo_cc_tab.update_filter_buttons(is_running, current_keyword)
        
    def _on_clear_logs(self):
        """清空日志"""
        self.log_viewer.clear_logs()
        self.append_log.emit(self.lang_manager.tr("日志已清空") + "\n", None)
        
    def _on_clear_device_logs(self):
        """清除设备日志缓存"""
        self.append_log.emit(self.lang_manager.tr("清除设备日志缓存...") + "\n", None)
        if hasattr(self, 'log_processor') and self.log_processor:
            self.log_processor.clear_device_logs()
        else:
            self.statusBar().showMessage(self.lang_manager.tr("日志处理器未初始化"))
        
    def _on_show_display_lines_dialog(self):
        """显示设置行数对话框"""
        self.append_log.emit(f"{self.lang_manager.tr('显示设置行数对话框...')}\n", None)
        
    def _on_save_logs(self):
        """保存日志"""
        if hasattr(self, 'log_processor') and self.log_processor:
            self.log_processor.save_logs()
        else:
            self.statusBar().showMessage(self.lang_manager.tr("日志处理器未初始化"))
        
    # Log过滤管理器信号处理
    def _on_filtering_started(self):
        """日志过滤启动完成"""
        # 更新UI状态为过滤中
        self.log_filter_tab.set_filtering_state(True)
        
    def _on_filtering_stopped(self):
        """日志过滤停止完成"""
        # 更新UI状态为停止过滤
        self.log_filter_tab.set_filtering_state(False)
        
    def _on_filter_log_received(self, log_line):
        """Log过滤接收日志"""
        self.append_log.emit(log_line, None)
        
    def _on_filter_status(self, message):
        """Log过滤状态消息"""
        self.append_log.emit(f"{message}\n", None)
        
    # 网络信息 Tab 信号处理
    def _on_start_network_info(self):
        """开始获取网络信息"""
        self.append_log.emit(self.lang_manager.tr("开始获取网络信息...") + "\n", None)
        self.network_info_manager.start_network_info()
        
    def _on_stop_network_info(self):
        """停止获取网络信息"""
        self.append_log.emit(self.lang_manager.tr("停止获取网络信息...") + "\n", None)
        self.network_info_manager.stop_network_info()
        
    def _on_start_ping(self):
        """开始 Ping"""
        self.append_log.emit(self.lang_manager.tr("开始 Ping 测试...") + "\n", None)
        self.network_info_manager.start_ping()
        
    def _on_stop_ping(self):
        """停止 Ping"""
        self.append_log.emit(self.lang_manager.tr("停止 Ping 测试...") + "\n", None)
        self.network_info_manager.stop_ping()
        
    # 网络信息管理器信号处理
    def _on_network_info_updated(self, network_info):
        """网络信息更新"""
        # 更新网络信息Tab的表格
        if hasattr(self, 'network_info_tab'):
            # network_info应该是一个列表
            if isinstance(network_info, list):
                self.network_info_tab.update_network_table(network_info)
            else:
                # 兼容旧格式
                self.network_info_tab.update_network_table([network_info])
        
    def _on_ping_result(self, result):
        """Ping结果"""
        # 打印到日志（除了 ping_stopped 消息）
        if result != "ping_stopped":
            self.append_log.emit(f"{result}\n", None)
        
        # 更新网络信息Tab的状态
        if hasattr(self, 'network_info_tab'):
            self.network_info_tab.update_ping_status(result)
        
    def _on_network_status(self, message):
        """网络信息状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    def _on_network_info_started(self):
        """网络信息获取启动成功"""
        # 更新Tab按钮状态
        if hasattr(self, 'network_info_tab'):
            self.network_info_tab.set_network_state(True)
    
    def _on_network_info_start_failed(self):
        """网络信息获取启动失败"""
        # 不改变Tab按钮状态，保持原样
        pass
    
    def _on_ping_started(self):
        """Ping启动成功"""
        # 更新Tab按钮状态
        if hasattr(self, 'network_info_tab'):
            self.network_info_tab.set_ping_state(True)
    
    def _on_ping_start_failed(self):
        """Ping启动失败"""
        # 不改变Tab按钮状态，保持原样
        pass
        
    # TMO CC Tab 信号处理
    def _on_push_cc_file(self):
        """推CC文件"""
        self.tmo_cc_manager.push_cc_file()
        
    def _on_pull_cc_file(self):
        """拉CC文件"""
        self.tmo_cc_manager.pull_cc_file()
        
    def _on_simple_filter(self):
        """简单过滤"""
        self.log_processor.simple_filter()
        
    def _on_complete_filter(self):
        """完全过滤"""
        self.log_processor.complete_filter()
        
    def _on_prod_server(self):
        """PROD服务器"""
        self.tmo_cc_manager.start_prod_server()
        
    def _on_stg_server(self):
        """STG服务器"""
        self.tmo_cc_manager.start_stg_server()
        
    # TMO Echolocate Tab 信号处理
    def _on_install_echolocate(self):
        """安装Echolocate"""
        self.echolocate_manager.install_echolocate()
        
    def _on_trigger_echolocate(self):
        """Trigger Echolocate"""
        self.echolocate_manager.trigger_echolocate()
        
    def _on_pull_echolocate_file(self):
        """Pull Echolocate文件"""
        self.echolocate_manager.pull_echolocate_file()
        
    def _on_delete_echolocate_file(self):
        """删除Echolocate文件"""
        self.echolocate_manager.delete_echolocate_file()
        
    def _on_get_echolocate_version(self):
        """获取Echolocate版本号"""
        self.echolocate_manager.get_echolocate_version()
        
    def _on_echolocate_log(self, message, color):
        """Echolocate日志消息（带颜色）"""
        # 检查是否包含版本号信息，如果是则只让版本号部分显示为绿色
        if "Echolocate版本号:" in message or "Echolocate版本信息:" in message:
            # 提取版本号部分并设置为绿色
            import re
            # 匹配版本号模式 (更宽泛的版本号格式)
            version_pattern = r'([0-9]+\.[0-9A-Za-z._-]+)'
            if re.search(version_pattern, message):
                # 分割消息，分别处理版本号部分和其他部分
                parts = re.split(version_pattern, message)
                for i, part in enumerate(parts):
                    if re.match(version_pattern, part):
                        # 版本号部分使用绿色
                        self.append_log.emit(part, "green")
                    else:
                        # 其他部分使用默认颜色，最后添加换行符
                        if i == len(parts) - 1:  # 最后一部分
                            self.append_log.emit(f"{part}\n", None)
                        else:
                            self.append_log.emit(part, None)
            else:
                # 如果没有匹配到版本号模式，使用原来的颜色
                self.append_log.emit(f"{message}\n", color)
        else:
            # 其他消息使用原来的颜色
            self.append_log.emit(f"{message}\n", color)
        
    def _on_filter_callid(self):
        """过滤CallID"""
        self.echolocate_manager.filter_callid()
        
    def _on_filter_callstate(self):
        """过滤CallState"""
        self.echolocate_manager.filter_callstate()
        
    def _on_filter_uicallstate(self):
        """过滤UICallState"""
        self.echolocate_manager.filter_uicallstate()
        
    def _on_filter_allcallstate(self):
        """过滤AllCallState"""
        self.echolocate_manager.filter_allcallstate()
        
    def _on_filter_ims_signalling(self):
        """过滤IMSSignallingMessageLine1"""
        self.echolocate_manager.filter_ims_signalling()
        
    def _on_filter_allcallflow(self):
        """过滤AllCallFlow"""
        self.echolocate_manager.filter_allcallflow()
        
    def _on_filter_voice_intent(self):
        """过滤voice_intent测试"""
        self.echolocate_manager.filter_voice_intent()
        
    # 24小时背景数据 Tab 信号处理
    def _on_configure_phone(self):
        """配置手机"""
        self.background_data_manager.configure_phone()
        
    def _on_analyze_logs(self):
        """分析日志"""
        self.background_data_manager.analyze_logs()
        
    # APP操作 Tab 信号处理
    def _on_query_package(self):
        """查询package"""
        self.app_operations_manager.query_package()
        
    def _on_query_package_name(self):
        """查询包名"""
        self.app_operations_manager.query_package_name()
        
    def _on_query_install_path(self):
        """查询安装路径"""
        self.app_operations_manager.query_install_path()
        
    def _on_pull_apk(self):
        """pull apk"""
        self.app_operations_manager.pull_apk()
        
    def _on_push_apk(self):
        """push apk"""
        self.app_operations_manager.push_apk()
        
    def _on_install_apk(self):
        """安装APK"""
        self.app_operations_manager.install_apk()
        
    def _on_view_processes(self):
        """查看进程"""
        self.app_operations_manager.view_processes()
        
    def _on_dump_app(self):
        """dump app"""
        self.app_operations_manager.dump_app()
        
    def _on_enable_app(self):
        """启用app"""
        self.app_operations_manager.enable_app()
        
    def _on_disable_app(self):
        """禁用app"""
        self.app_operations_manager.disable_app()
        
    # 其他 Tab 信号处理
    def _on_show_device_info_dialog(self):
        """显示手机信息对话框"""
        self.device_info_manager.show_device_info()
        
    def _on_set_screen_timeout(self):
        """设置灭屏时间"""
        self.device_info_manager.set_screen_timeout()
        
    def _on_merge_mtklog(self):
        """合并MTKlog"""
        self.other_operations_manager.merge_mtklog()
        
    def _on_extract_pcap_from_mtklog(self):
        """MTKlog提取pcap"""
        self.other_operations_manager.extract_pcap_from_mtklog()
        
    def _on_merge_pcap(self):
        """合并PCAP"""
        self.other_operations_manager.merge_pcap()
        
    def _on_extract_pcap_from_qualcomm_log(self):
        """高通log提取pcap"""
        self.other_operations_manager.extract_pcap_from_qualcomm_log()
        
    def _on_configure_hera(self):
        """赫拉配置"""
        self.hera_config_manager.configure_hera()
        
    def _on_configure_collect_data(self):
        """赫拉测试数据收集"""
        self.hera_config_manager.configure_collect_data()
        
    def _on_show_input_text_dialog(self):
        """显示输入文本对话框"""
        self.other_operations_manager.show_input_text_dialog()
    
    # 菜单栏信号处理
    def _on_show_display_lines_dialog(self):
        """显示设置显示行数对话框"""
        dialog = DisplayLinesDialog(current_lines=self.log_processor.adaptive_params['max_display_lines'], parent=self)
        if dialog.exec_() == DisplayLinesDialog.Accepted:
            new_lines = dialog.result_lines
            self.log_processor.adaptive_params['max_display_lines'] = new_lines
            self.log_processor.adaptive_params['trim_threshold'] = int(new_lines * 0.05)
            self.statusBar().showMessage(f"{self.lang_manager.tr('最大显示行数已设置为')}: {new_lines} {self.lang_manager.tr('行')}")
            QMessageBox.information(self, self.lang_manager.tr("成功"), 
                f"{self.lang_manager.tr('设置已应用')}!\n{self.lang_manager.tr('最大显示行数')}: {new_lines}\ntrim_threshold: {self.log_processor.adaptive_params['trim_threshold']}")
    
    def _on_show_tools_config_dialog(self):
        """显示工具配置对话框"""
        try:
            logger.debug(self.lang_manager.tr("打开工具配置对话框..."))
            dialog = ToolsConfigDialog(self.other_operations_manager.tool_config, parent=self)
            dialog.exec_()
            logger.debug(self.lang_manager.tr("工具配置对话框已关闭"))
        except Exception as e:
            logger.exception(self.lang_manager.tr("打开工具配置对话框失败"))
            QMessageBox.critical(self, self.lang_manager.tr("错误"), f"{self.lang_manager.tr('打开工具配置对话框失败')}：{str(e)}")
    
    def _setup_shortcuts(self):
        """设置快捷键"""
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence
        
        # Ctrl+F - 搜索
        shortcut_search = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut_search.activated.connect(lambda: self.log_viewer.search_edit.setFocus())
        
        # F3 - 查找下一个
        shortcut_next = QShortcut(QKeySequence("F3"), self)
        shortcut_next.activated.connect(self.log_viewer.find_next)
        
        # Shift+F3 - 查找上一个
        shortcut_prev = QShortcut(QKeySequence("Shift+F3"), self)
        shortcut_prev.activated.connect(self.log_viewer.find_previous)
        
        # Ctrl+G - 查找下一个（备用）
        shortcut_next_alt = QShortcut(QKeySequence("Ctrl+G"), self)
        shortcut_next_alt.activated.connect(self.log_viewer.find_next)
    
    # 截图管理器信号处理
    def _on_screenshot_completed(self, message):
        """截图完成"""
        self.append_log.emit(f"{message}\n", None)
    
    def _on_screenshot_progress(self, progress, status):
        """截图进度更新"""
        self.append_log.emit(f"[{progress}%] {status}\n", None)
    
    def _on_screenshot_status(self, message):
        """截图状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    # 录制管理器信号处理
    def _on_recording_started(self):
        """录制开始"""
        # 更新按钮状态
        self.toolbar.record_btn.setText(self.lang_manager.tr("停止录制"))
        self.toolbar.record_btn.setChecked(True)
        self.append_log.emit(self.lang_manager.tr("视频录制已开始") + "\n", None)
    
    def _on_recording_stopped(self):
        """录制停止"""
        # 更新按钮状态
        self.toolbar.record_btn.setText(self.lang_manager.tr("开始录制"))
        self.toolbar.record_btn.setChecked(False)
        self.append_log.emit(self.lang_manager.tr("视频录制已停止") + "\n", None)
    
    def _on_video_saved(self, folder, count):
        """视频保存完成"""
        self.append_log.emit(f"{self.tr('视频已保存到: ')}{folder} ({count}{self.tr('个文件)')}\n", None)
    
    def _on_video_status(self, message):
        """录制状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    # 其他管理器信号处理
    def _on_tcpdump_status(self, message):
        """TCPDUMP状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    def _on_telephony_status(self, message):
        """Telephony状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    def _on_google_log_status(self, message):
        """Google Log状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    def _on_aee_log_status(self, message):
        """AEE Log状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    def _on_bugreport_status(self, message):
        """Bugreport状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    # TMO CC管理器信号处理
    def _on_cc_pulled(self, folder):
        """CC文件拉取完成"""
        self.append_log.emit(f"{self.tr('CC文件已拉取到: ')}{folder}\n", None)
    
    def _on_cc_pushed(self, success_count, total_count):
        """CC文件推送完成"""
        self.append_log.emit(f"{self.tr('CC文件推送完成: ')}{success_count}/{total_count} {self.tr('个文件成功')}\n", None)
    
    def _on_server_started(self, server_type):
        """服务器启动完成"""
        self.append_log.emit(f"{server_type}{self.tr('服务器活动已启动')}\n", None)
    
    def _on_tmo_cc_status(self, message):
        """TMO CC状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    # Echolocate管理器信号处理
    def _on_echolocate_installed(self):
        """Echolocate安装完成"""
        self.append_log.emit(self.lang_manager.tr("Echolocate安装完成并已启动") + "\n", None)
    
    def _on_echolocate_triggered(self):
        """Echolocate触发完成"""
        self.append_log.emit(self.lang_manager.tr("Echolocate应用已启动") + "\n", None)
    
    def _on_echolocate_file_pulled(self, folder):
        """Echolocate文件拉取完成"""
        self.append_log.emit(f"{self.tr('Echolocate文件已拉取到: ')}{folder}\n", None)
    
    def _on_echolocate_file_deleted(self):
        """Echolocate文件删除完成"""
        self.append_log.emit(self.lang_manager.tr("Echolocate文件已删除") + "\n", None)
    
    def _on_echolocate_status(self, message):
        """Echolocate状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    # 背景数据管理器信号处理
    def _on_background_data_status(self, message):
        """背景数据状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    def _on_background_data_log(self, message, color):
        """背景数据日志消息（带颜色）"""
        self.append_log.emit(f"{message}\n", color)
    
    # APP操作管理器信号处理
    def _on_app_operations_status(self, message):
        """APP操作状态消息"""
        # 检查是否包含包名信息，如果是则使用绿色
        if "Current foreground app package:" in message or "当前前台应用包名:" in message:
            # 提取包名部分并设置为绿色
            import re
            # 匹配包名模式 (com.xxx.xxx 格式)
            package_pattern = r'(com\.[a-zA-Z0-9_.]+)'
            if re.search(package_pattern, message):
                # 分割消息，分别处理包名部分和其他部分
                parts = re.split(package_pattern, message)
                for i, part in enumerate(parts):
                    if re.match(package_pattern, part):
                        # 包名部分使用绿色
                        self.append_log.emit(part, "green")
                    else:
                        # 其他部分使用默认颜色，最后添加换行符
                        if i == len(parts) - 1:  # 最后一部分
                            self.append_log.emit(f"{part}\n", None)
                        else:
                            self.append_log.emit(part, None)
            else:
                self.append_log.emit(f"{message}\n", None)
        else:
            self.append_log.emit(f"{message}\n", None)
    
    # 设备信息管理器信号处理
    def _on_device_info_status(self, message):
        """设备信息状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    # 赫拉配置管理器信号处理
    def _on_hera_config_status(self, message):
        """赫拉配置状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    # 其他操作管理器信号处理
    def _on_other_operations_status(self, message):
        """其他操作状态消息"""
        self.append_log.emit(f"{message}\n", None)
    
    # 自定义按钮相关方法
    def load_custom_buttons_for_all_tabs(self):
        """为所有Tab加载自定义按钮"""
        try:
            logger.info(self.lang_manager.tr("开始为所有Tab加载自定义按钮..."))
            
            # 获取所有Tab对应的实例
            tabs = {
                'Log控制': self.log_control_tab,
                'Log过滤': self.log_filter_tab,
                '网络信息': self.network_info_tab,
                'TMO CC': self.tmo_cc_tab,
                'TMO Echolocate': self.tmo_echolocate_tab,
                '24小时背景数据': self.background_data_tab,
                'APP操作': self.app_operations_tab,
                '其他': self.other_tab
            }
            
            logger.debug(f"{self.lang_manager.tr('处理预制Tab:')} {list(tabs.keys())}")
            
            for tab_name, tab_instance in tabs.items():
                self.load_custom_buttons_for_tab(tab_name, tab_instance)
            
            # 处理自定义Tab
            logger.debug(f"{self.lang_manager.tr('处理自定义Tab...')}")
            for i in range(self.tab_widget.count()):
                widget = self.tab_widget.widget(i)
                if hasattr(widget, 'tab_id'):
                    tab_id = widget.tab_id
                    logger.debug(f"{self.lang_manager.tr('检查Tab:')} {tab_id}")
                    
                    # 检查是否是自定义Tab
                    for custom_tab in self.tab_config_manager.custom_tabs:
                        if custom_tab['id'] == tab_id:
                            logger.debug(f"{self.lang_manager.tr('找到自定义Tab:')} {custom_tab['name']}")
                            self.load_custom_buttons_for_custom_tab(custom_tab, widget)
                            break
            
            logger.info(self.lang_manager.tr("所有Tab的自定义按钮加载完成"))
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('加载自定义按钮失败:')} {e}")
    
    def load_custom_buttons_for_custom_tab(self, custom_tab, tab_widget):
        """为自定义Tab加载自定义按钮"""
        try:
            logger.debug(f"{self.lang_manager.tr('为自定义Tab加载按钮:')} {custom_tab['name']}")
            
            # 获取该自定义Tab的所有自定义Card
            custom_cards = self.tab_config_manager.get_custom_cards_for_tab(custom_tab['id'])
            logger.debug(f"{self.lang_manager.tr('找到')} {len(custom_cards)} {self.lang_manager.tr('个自定义Card')}")
            
            for card in custom_cards:
                logger.debug(f"{self.lang_manager.tr('处理Card:')} {card['name']}")
                
                # 获取该Card的自定义按钮
                tab_name = custom_tab['name']
                logger.debug(f"{self.lang_manager.tr('查找按钮: Tab=')} '{tab_name}', {self.lang_manager.tr('Card=')} '{card['name']}'")
                
                # 先检查所有按钮配置
                all_buttons = self.custom_button_manager.get_all_buttons()
                logger.debug(f"{self.lang_manager.tr('所有按钮配置:')} {len(all_buttons)} {self.lang_manager.tr('个')}")
                for btn in all_buttons:
                    logger.debug(f"  - {btn.get('name', '')} -> Tab: '{btn.get('tab', '')}', Card: '{btn.get('card', '')}'")
                
                buttons = self.custom_button_manager.get_buttons_by_location(tab_name, card['name'])
                logger.debug(f"{self.lang_manager.tr('Card')} '{card['name']}' {self.lang_manager.tr('有')} {len(buttons)} {self.lang_manager.tr('个按钮')}")
                
                if buttons:
                    # 查找对应的Card GroupBox并添加按钮
                    self._add_buttons_to_custom_card(tab_widget, card['name'], buttons)
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('为自定义Tab加载按钮失败:')} {e}")
    
    def _add_buttons_to_custom_card(self, tab_widget, card_name, buttons):
        """向自定义Card添加按钮"""
        try:
            from PyQt5.QtWidgets import QGroupBox, QPushButton, QHBoxLayout
            
            logger.debug(f"{self.lang_manager.tr('尝试向自定义Card添加按钮:')} '{card_name}'")
            
            # 查找对应的GroupBox
            group_boxes = tab_widget.findChildren(QGroupBox)
            logger.debug(f"{self.lang_manager.tr('找到')} {len(group_boxes)} {self.lang_manager.tr('个GroupBox')}")
            
            for group_box in group_boxes:
                if group_box.title() == card_name:
                    logger.debug(f"{self.lang_manager.tr('找到匹配的GroupBox:')} '{card_name}'")
                    
                    # 查找按钮布局
                    button_layouts = group_box.findChildren(QHBoxLayout)
                    logger.debug(f"{self.lang_manager.tr('找到')} {len(button_layouts)} {self.lang_manager.tr('个QHBoxLayout')}")
                    
                    if button_layouts:
                        button_layout = button_layouts[0]  # 使用第一个水平布局
                        logger.debug(f"{self.lang_manager.tr('使用按钮布局添加')} {len(buttons)} {self.lang_manager.tr('个按钮')}")
                        
                        for btn_data in buttons:
                            custom_btn = QPushButton(btn_data['name'])
                            custom_btn.setToolTip(btn_data.get('description', btn_data['command']))
                            custom_btn.setProperty('custom_button', True)
                            
                            custom_btn.clicked.connect(
                                lambda checked=False, data=btn_data: self.execute_custom_button_command(data)
                            )
                            
                            # 在stretch之前插入
                            count = button_layout.count()
                            if count > 0:
                                insert_pos = count - 1 if button_layout.itemAt(count - 1).spacerItem() else count
                                button_layout.insertWidget(insert_pos, custom_btn)
                            else:
                                button_layout.addWidget(custom_btn)
                            
                            logger.debug(f"{self.lang_manager.tr('添加按钮')} '{btn_data['name']}' {self.lang_manager.tr('到Card')} '{card_name}'")
                    else:
                        logger.warning(f"{self.lang_manager.tr('未找到按钮布局')}")
                    break
            else:
                logger.warning(f"{self.lang_manager.tr('未找到Card')} '{card_name}'")
                
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('向自定义Card添加按钮失败:')} {e}")
    
    def load_custom_buttons_for_tab(self, tab_name, tab_instance):
        """为指定Tab加载自定义按钮"""
        try:
            # 检查Tab实例是否有custom_buttons_container属性（用于存储自定义按钮）
            if not hasattr(tab_instance, 'custom_buttons_containers'):
                tab_instance.custom_buttons_containers = {}
            
            # 获取该Tab的所有卡片（GroupBox或Frame）
            # 遍历Tab中的所有子部件，找到卡片
            self._add_custom_buttons_to_tab(tab_name, tab_instance)
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('为Tab')} '{tab_name}' {self.lang_manager.tr('加载自定义按钮失败:')} {e}")
    
    def _add_custom_buttons_to_tab(self, tab_name, tab_instance):
        """为Tab添加自定义按钮"""
        # 获取Tab下所有可用的卡片名称
        cards = self.custom_button_manager.get_available_cards(tab_name)
        
        for card_name in cards:
            # 获取该位置的自定义按钮
            buttons = self.custom_button_manager.get_buttons_by_location(tab_name, card_name)
            
            if buttons:
                # 尝试找到对应的卡片容器并添加按钮
                self._inject_custom_buttons_to_card(tab_instance, card_name, buttons)
    
    def _inject_custom_buttons_to_card(self, tab_instance, card_name, buttons):
        """向指定卡片注入自定义按钮（仅处理预制Card）"""
        try:
            from PyQt5.QtWidgets import QFrame, QPushButton, QHBoxLayout, QVBoxLayout, QWidget, QLabel
            from PyQt5.QtCore import Qt
            
            logger.debug(f"{self.lang_manager.tr('尝试向预制卡片')} '{card_name}' {self.lang_manager.tr('注入')} {len(buttons)} {self.lang_manager.tr('个按钮')}")
            
            # 检查是否是自定义Card，如果是则跳过（自定义Card由_create_custom_card_group处理）
            custom_card = self._find_custom_card_by_name(card_name)
            if custom_card:
                logger.debug(f"{self.lang_manager.tr('跳过自定义Card')} '{card_name}' {self.lang_manager.tr('，由统一方法处理')}")
                return
            
            # 搜索Tab中的所有Frame/卡片（仅处理预制Card）
            frames = tab_instance.findChildren(QFrame)
            logger.debug(f"{self.lang_manager.tr('找到')} {len(frames)} {self.lang_manager.tr('个Frame')}")
            
            found_card = False
            for frame in frames:
                # 检查Frame上方是否有对应的标题Label
                parent_widget = frame.parent()
                if parent_widget:
                    labels = parent_widget.findChildren(QLabel)
                    
                    for label in labels:
                        label_text = label.text()
                        label_class = label.property("class")
                        
                        if label_text == card_name and label_class == "section-title":
                            logger.debug(f"{self.lang_manager.tr('找到匹配的预制卡片:')} '{card_name}'")
                            found_card = True
                            
                            # 找到了对应的卡片
                            layout = frame.layout()
                            if layout:
                                # 使用统一的按钮添加逻辑
                                self._add_buttons_to_layout(layout, buttons, card_name)
                                break
                    
                    if found_card:
                        break
                                    
            if not found_card:
                logger.warning(f"{self.lang_manager.tr('未找到预制卡片')} '{card_name}'")
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('向预制卡片')} '{card_name}' {self.lang_manager.tr('注入自定义按钮失败:')} {e}")
    
    def _add_buttons_to_layout(self, layout, buttons, card_name):
        """向布局中添加按钮（统一逻辑）"""
        try:
            from PyQt5.QtWidgets import QPushButton, QHBoxLayout
            
            # 查找合适的按钮布局
            button_layout = None
            
            if isinstance(layout, QVBoxLayout):
                # 查找最后一个QHBoxLayout
                for i in range(layout.count() - 1, -1, -1):
                    item = layout.itemAt(i)
                    if item and item.layout() and isinstance(item.layout(), QHBoxLayout):
                        button_layout = item.layout()
                        break
            elif isinstance(layout, QHBoxLayout):
                button_layout = layout
            
            if button_layout:
                logger.debug(f"{self.lang_manager.tr('找到按钮布局，添加')} {len(buttons)} {self.lang_manager.tr('个按钮')}")
                
                for btn_data in buttons:
                    custom_btn = QPushButton(btn_data['name'])
                    custom_btn.setToolTip(btn_data.get('description', btn_data['command']))
                    custom_btn.setProperty('custom_button', True)
                    
                    custom_btn.clicked.connect(
                        lambda checked=False, data=btn_data: self.execute_custom_button_command(data)
                    )
                    
                    # 在stretch之前插入
                    count = button_layout.count()
                    if count > 0:
                        insert_pos = count - 1 if button_layout.itemAt(count - 1).spacerItem() else count
                        button_layout.insertWidget(insert_pos, custom_btn)
                    else:
                        button_layout.addWidget(custom_btn)
                    
                    logger.debug(f"{self.lang_manager.tr('添加自定义按钮')} '{btn_data['name']}' {self.lang_manager.tr('到')} '{card_name}'")
            else:
                logger.warning(f"{self.lang_manager.tr('未找到合适的按钮布局')}")
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('向布局添加按钮失败:')} {e}")
    
    def execute_custom_button_command(self, button_data):
        """执行自定义按钮命令"""
        try:
            button_type = button_data.get('type', 'adb')
            command = button_data.get('command', '')
            name = button_data.get('name', self.lang_manager.tr('自定义按钮'))
            
            self.append_log.emit(f"🔧 {self.tr('执行自定义按钮: ')}{name}\n", "#17a2b8")
            
            # 使用新的统一执行方法
            success, output = self.custom_button_manager.execute_button_command(
                button_data, 
                self.device_manager.selected_device
            )
            
            if success:
                self.append_log.emit(f"✅ {self.tr('执行成功')}\n", "#28a745")
                if output:
                    self.append_log.emit(f"{output}\n", "#6c757d")
            else:
                self.append_log.emit(f"❌ {self.tr('执行失败: ')}{output}\n", "#dc3545")
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('执行自定义按钮命令失败:')} {e}")
            self.append_log.emit(f"❌ {self.tr('执行失败: ')}{str(e)}\n", "#dc3545")
    
    def on_custom_buttons_updated(self):
        """自定义按钮配置更新时的处理"""
        try:
            logger.info(self.lang_manager.tr("检测到自定义按钮配置更新，重新加载..."))
            
            # 清除所有Tab中的自定义按钮
            self._clear_all_custom_buttons()
            
            # 重新加载预制Tab的自定义按钮
            self.load_custom_buttons_for_all_tabs()
            
            # 重新加载自定义Tab（重新创建Tab实例以包含新的按钮）
            self._refresh_custom_tabs()
            
            # 为新创建的自定义Tab加载按钮
            self.load_custom_buttons_for_all_tabs()
            
            self.append_log.emit(self.lang_manager.tr("自定义按钮已更新") + "\n", "#00FF00")
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('更新自定义按钮失败:')} {e}")
    
    def _refresh_custom_tabs(self):
        """刷新自定义Tab（重新创建以包含新的按钮）"""
        try:
            logger.info(self.lang_manager.tr("刷新自定义Tab..."))
            
            # 获取当前Tab顺序和可见性
            tab_order = self.tab_config_manager.get_tab_order()
            tab_visibility = self.tab_config_manager.get_tab_visibility()
            
            # 找到所有自定义Tab的索引
            custom_tab_indices = []
            for i in range(self.tab_widget.count()):
                widget = self.tab_widget.widget(i)
                if hasattr(widget, 'tab_id'):
                    tab_id = widget.tab_id
                    # 检查是否是自定义Tab
                    for custom_tab in self.tab_config_manager.custom_tabs:
                        if custom_tab['id'] == tab_id:
                            custom_tab_indices.append(i)
                            break
            
            # 从后往前删除自定义Tab（避免索引变化）
            for i in reversed(custom_tab_indices):
                self.tab_widget.removeTab(i)
            
            # 重新创建自定义Tab
            for custom_tab in self.tab_config_manager.custom_tabs:
                tab_id = custom_tab['id']
                if tab_visibility.get(tab_id, True):
                    # 重新创建自定义Tab实例
                    custom_tab_instance = self._create_custom_tab_instance(custom_tab)
                    if custom_tab_instance:
                        # 找到正确的插入位置
                        insert_index = self._find_tab_insert_position(tab_id, tab_order)
                        tab_name = self._get_tab_name(tab_id, self.tab_config_manager.get_all_tabs())
                        self.tab_widget.insertTab(insert_index, custom_tab_instance, tab_name)
                        logger.debug(f"{self.lang_manager.tr('重新创建自定义Tab:')} {tab_name}")
            
            logger.info(self.lang_manager.tr("自定义Tab刷新完成"))
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('刷新自定义Tab失败:')} {e}")
    
    def _find_tab_insert_position(self, tab_id, tab_order):
        """找到Tab的插入位置"""
        try:
            # 找到tab_id在tab_order中的位置
            if tab_id in tab_order:
                target_index = tab_order.index(tab_id)
                
                # 计算当前Tab中应该插入的位置
                current_index = 0
                for i, ordered_tab_id in enumerate(tab_order):
                    if ordered_tab_id == tab_id:
                        return current_index
                    
                    # 检查这个Tab是否在当前Tab中可见
                    for j in range(self.tab_widget.count()):
                        widget = self.tab_widget.widget(j)
                        if hasattr(widget, 'tab_id') and widget.tab_id == ordered_tab_id:
                            current_index += 1
                            break
                
                return current_index
            
            return self.tab_widget.count()  # 如果找不到，插入到最后
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('查找Tab插入位置失败:')} {e}")
            return self.tab_widget.count()
    
    def _clear_all_custom_buttons(self):
        """清除所有自定义按钮"""
        try:
            from PyQt5.QtWidgets import QPushButton
            
            tabs = [
                self.log_control_tab,
                self.log_filter_tab,
                self.network_info_tab,
                self.tmo_cc_tab,
                self.tmo_echolocate_tab,
                self.background_data_tab,
                self.app_operations_tab,
                self.other_tab
            ]
            
            for tab in tabs:
                # 找到所有标记为自定义按钮的QPushButton并删除
                custom_buttons = tab.findChildren(QPushButton)
                for btn in custom_buttons:
                    if btn.property('custom_button'):
                        btn.setParent(None)
                        btn.deleteLater()
            
            logger.debug(self.lang_manager.tr("已清除所有自定义按钮"))
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('清除自定义按钮失败:')} {e}")
    
    def show_unified_manager_dialog(self):
        """显示自定义界面管理对话框"""
        try:
            from ui.unified_manager_dialog import UnifiedManagerDialog
            
            dialog = UnifiedManagerDialog(self.tab_config_manager, self.custom_button_manager, parent=self)
            dialog.exec_()
            
            # 对话框关闭后，重新加载Tab以应用可能的更改
            self.reload_tabs()
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('显示自定义界面管理对话框失败:')} {e}")
            QMessageBox.critical(self, self.lang_manager.tr("错误"), f"{self.lang_manager.tr('打开自定义界面管理失败')}：{str(e)}")
    
    def show_secret_code_dialog(self):
        """显示暗码管理对话框"""
        try:
            from ui.secret_code_dialog import SecretCodeDialog
            
            dialog = SecretCodeDialog(parent=self)
            dialog.exec_()
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('显示暗码管理对话框失败:')} {e}")
            QMessageBox.critical(self, self.lang_manager.tr("错误"), f"{self.lang_manager.tr('打开暗码管理失败')}：{str(e)}")
    
    def show_lock_cell_dialog(self):
        """显示高通lock cell对话框"""
        try:
            from ui.cell_lock_dialog import LockCellDialog
            
            dialog = LockCellDialog(parent=self)
            dialog.exec_()
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('显示高通lock cell对话框失败:')} {e}")
            QMessageBox.critical(self, self.lang_manager.tr("错误"), f"{self.lang_manager.tr('打开高通lock cell失败')}：{str(e)}")
    
    def _on_tab_moved(self, from_index, to_index):
        """Tab拖拽移动处理"""
        try:
            # 使用防抖机制，避免频繁保存
            if hasattr(self, '_tab_move_timer'):
                self._tab_move_timer.stop()
            else:
                from PyQt5.QtCore import QTimer
                self._tab_move_timer = QTimer()
                self._tab_move_timer.setSingleShot(True)
                self._tab_move_timer.timeout.connect(self._save_tab_order)
            
            # 延迟500ms保存，避免拖拽过程中频繁保存
            self._tab_move_timer.start(500)
            
        except Exception as e:
            logger.exception(f"{self.tr('Tab拖拽处理失败:')} {e}")
    
    def _save_tab_order(self):
        """保存Tab顺序（防抖处理）"""
        try:
            # 获取新的Tab顺序
            new_order = []
            for i in range(self.tab_widget.count()):
                widget = self.tab_widget.widget(i)
                tab_id = self._get_tab_id_by_widget(widget)
                if tab_id:
                    new_order.append(tab_id)
                    logger.debug(f"保存Tab顺序: 位置{i} -> Tab ID: {tab_id}, Widget: {type(widget).__name__}")
                else:
                    logger.warning(f"无法获取Tab ID: 位置{i}, Widget: {type(widget).__name__}")
            
            # 保存新的顺序
            self.tab_config_manager.set_tab_order(new_order)
            logger.debug(f"{self.tr('Tab顺序已更新:')} {new_order}")
            
        except Exception as e:
            logger.exception(f"{self.tr('保存Tab顺序失败:')} {e}")
    
    def _get_tab_id_by_widget(self, widget):
        """根据widget获取tab_id"""
        # 直接从widget的tab_id属性获取ID
        if hasattr(widget, 'tab_id'):
            tab_id = widget.tab_id
            logger.debug(f"从tab_id属性获取ID: {tab_id}, Widget: {type(widget).__name__}")
            return tab_id
        
        # 如果widget没有tab_id属性，使用旧的映射方法作为后备
        widget_to_id = {
            self.log_control_tab: 'log_control',
            self.log_filter_tab: 'log_filter',
            self.network_info_tab: 'network_info',
            self.tmo_cc_tab: 'tmo_cc',
            self.tmo_echolocate_tab: 'tmo_echolocate',
            self.background_data_tab: 'background_data',
            self.app_operations_tab: 'app_operations',
            self.other_tab: 'other'
        }
        
        # 检查是否是默认tab
        if widget in widget_to_id:
            tab_id = widget_to_id[widget]
            logger.debug(f"从widget_to_id映射获取ID: {tab_id}, Widget: {type(widget).__name__}")
            return tab_id
        
        # 检查是否是自定义tab
        for custom_tab in self.tab_config_manager.custom_tabs:
            # 这里需要根据实际的自定义tab实例来判断
            # 目前简化处理
            pass
        
        logger.warning(f"无法获取Tab ID: Widget: {type(widget).__name__}")
        return None
    
    def _on_tab_config_updated(self):
        """Tab配置更新处理"""
        try:
            logger.info(self.tr("检测到Tab配置更新，重新加载Tab..."))
            self.reload_tabs()
        except Exception as e:
            logger.exception(f"{self.tr('Tab配置更新处理失败:')} {e}")
    
    def reload_tabs(self):
        """重新加载Tab"""
        try:
            # 保存当前选中的tab
            current_index = self.tab_widget.currentIndex()
            current_widget = self.tab_widget.currentWidget() if current_index >= 0 else None
            
            # 清除所有tab
            while self.tab_widget.count() > 0:
                self.tab_widget.removeTab(0)
            
            # 重新设置tab
            self.setup_tabs()
            
            # 重新连接Tab信号槽
            self._reconnect_tab_signals()
            
            # 重新加载所有Tab的自定义按钮
            self.load_custom_buttons_for_all_tabs()
            
            # 尝试恢复之前选中的tab
            if current_widget:
                for i in range(self.tab_widget.count()):
                    if self.tab_widget.widget(i) == current_widget:
                        self.tab_widget.setCurrentIndex(i)
                        break
            
            logger.info(self.tr("Tab重新加载完成"))
            
        except Exception as e:
            logger.exception(f"{self.tr('Tab重新加载失败:')} {e}")
    
    def _reconnect_tab_signals(self):
        """重新连接Tab信号槽"""
        try:
            # 连接 Log控制 Tab 信号
            if hasattr(self, 'log_control_tab'):
                self.log_control_tab.mtklog_start.connect(self._on_mtklog_start)
                self.log_control_tab.mtklog_stop_export.connect(self._on_mtklog_stop_export)
                self.log_control_tab.mtklog_delete.connect(self._on_mtklog_delete)
                self.log_control_tab.mtklog_set_log_size.connect(self._on_mtklog_set_log_size)
                self.log_control_tab.mtklog_sd_mode.connect(self._on_mtklog_sd_mode)
                self.log_control_tab.mtklog_usb_mode.connect(self._on_mtklog_usb_mode)
                self.log_control_tab.mtklog_install.connect(self._on_mtklog_install)
                self.log_control_tab.adblog_start.connect(self._on_adblog_start)
                self.log_control_tab.adblog_online_start.connect(self._on_adblog_online_start)
                self.log_control_tab.adblog_export.connect(self._on_adblog_export)
                self.log_control_tab.telephony_enable.connect(self._on_telephony_enable)
                self.log_control_tab.google_log_toggle.connect(self._on_google_log_toggle)
                self.log_control_tab.bugreport_generate.connect(self._on_bugreport_generate)
                self.log_control_tab.bugreport_pull.connect(self._on_bugreport_pull)
                self.log_control_tab.bugreport_delete.connect(self._on_bugreport_delete)
                self.log_control_tab.aee_log_start.connect(self._on_aee_log_start)
                self.log_control_tab.tcpdump_show_dialog.connect(self._on_tcpdump_show_dialog)
            
            # 连接 Log过滤 Tab 信号
            if hasattr(self, 'log_filter_tab'):
                self.log_filter_tab.start_filtering.connect(self._on_start_filtering)
                self.log_filter_tab.stop_filtering.connect(self._on_stop_filtering)
                self.log_filter_tab.manage_log_keywords.connect(self._on_manage_log_keywords)
                self.log_filter_tab.clear_logs.connect(self._on_clear_logs)
                self.log_filter_tab.clear_device_logs.connect(self._on_clear_device_logs)
                self.log_filter_tab.show_display_lines_dialog.connect(self._on_show_display_lines_dialog)
                self.log_filter_tab.save_logs.connect(self._on_save_logs)
            
            # 连接 网络信息 Tab 信号
            if hasattr(self, 'network_info_tab'):
                self.network_info_tab.start_network_info.connect(self._on_start_network_info)
                self.network_info_tab.stop_network_info.connect(self._on_stop_network_info)
                self.network_info_tab.start_ping.connect(self._on_start_ping)
                self.network_info_tab.stop_ping.connect(self._on_stop_ping)
            
            # 连接 TMO CC Tab 信号
            if hasattr(self, 'tmo_cc_tab'):
                self.tmo_cc_tab.push_cc_file.connect(self._on_push_cc_file)
                self.tmo_cc_tab.pull_cc_file.connect(self._on_pull_cc_file)
                self.tmo_cc_tab.simple_filter.connect(self._on_simple_filter)
                self.tmo_cc_tab.complete_filter.connect(self._on_complete_filter)
                self.tmo_cc_tab.prod_server.connect(self._on_prod_server)
                self.tmo_cc_tab.stg_server.connect(self._on_stg_server)
                self.tmo_cc_tab.clear_logs.connect(self._on_clear_logs)
                self.tmo_cc_tab.clear_device_logs.connect(self._on_clear_device_logs)
            
            # 连接 TMO Echolocate Tab 信号
            if hasattr(self, 'tmo_echolocate_tab'):
                self.tmo_echolocate_tab.install_echolocate.connect(self._on_install_echolocate)
                self.tmo_echolocate_tab.trigger_echolocate.connect(self._on_trigger_echolocate)
                self.tmo_echolocate_tab.pull_echolocate_file.connect(self._on_pull_echolocate_file)
                self.tmo_echolocate_tab.delete_echolocate_file.connect(self._on_delete_echolocate_file)
                self.tmo_echolocate_tab.get_echolocate_version.connect(self._on_get_echolocate_version)
                self.tmo_echolocate_tab.filter_callid.connect(self._on_filter_callid)
                self.tmo_echolocate_tab.filter_callstate.connect(self._on_filter_callstate)
                self.tmo_echolocate_tab.filter_uicallstate.connect(self._on_filter_uicallstate)
                self.tmo_echolocate_tab.filter_allcallstate.connect(self._on_filter_allcallstate)
                self.tmo_echolocate_tab.filter_ims_signalling.connect(self._on_filter_ims_signalling)
                self.tmo_echolocate_tab.filter_allcallflow.connect(self._on_filter_allcallflow)
                self.tmo_echolocate_tab.filter_voice_intent.connect(self._on_filter_voice_intent)
            
            # 连接 24小时背景数据 Tab 信号
            if hasattr(self, 'background_data_tab'):
                self.background_data_tab.configure_phone.connect(self._on_configure_phone)
                self.background_data_tab.analyze_logs.connect(self._on_analyze_logs)
            
            # 连接 APP操作 Tab 信号
            if hasattr(self, 'app_operations_tab'):
                self.app_operations_tab.query_package.connect(self._on_query_package)
                self.app_operations_tab.query_package_name.connect(self._on_query_package_name)
                self.app_operations_tab.query_install_path.connect(self._on_query_install_path)
                self.app_operations_tab.pull_apk.connect(self._on_pull_apk)
                self.app_operations_tab.push_apk.connect(self._on_push_apk)
                self.app_operations_tab.install_apk.connect(self._on_install_apk)
                self.app_operations_tab.view_processes.connect(self._on_view_processes)
                self.app_operations_tab.dump_app.connect(self._on_dump_app)
                self.app_operations_tab.enable_app.connect(self._on_enable_app)
                self.app_operations_tab.disable_app.connect(self._on_disable_app)
            
            # 连接 其他 Tab 信号
            if hasattr(self, 'other_tab'):
                self.other_tab.show_device_info_dialog.connect(self._on_show_device_info_dialog)
                self.other_tab.set_screen_timeout.connect(self._on_set_screen_timeout)
                self.other_tab.merge_mtklog.connect(self._on_merge_mtklog)
                self.other_tab.extract_pcap_from_mtklog.connect(self._on_extract_pcap_from_mtklog)
                self.other_tab.merge_pcap.connect(self._on_merge_pcap)
                self.other_tab.extract_pcap_from_qualcomm_log.connect(self._on_extract_pcap_from_qualcomm_log)
                self.other_tab.configure_hera.connect(self._on_configure_hera)
                self.other_tab.configure_collect_data.connect(self._on_configure_collect_data)
                self.other_tab.show_input_text_dialog.connect(self._on_show_input_text_dialog)
                self.other_tab.show_tools_config_dialog.connect(self._on_show_tools_config_dialog)
                self.other_tab.show_display_lines_dialog.connect(self._on_show_display_lines_dialog)
                self.other_tab.show_unified_manager.connect(self.show_unified_manager_dialog)
            
            # 连接 SIM Tab 信号
            if hasattr(self, 'sim_tab'):
                self.sim_tab.status_message.connect(self._on_sim_status_message)
            
            logger.debug(self.tr("Tab信号槽重新连接完成"))
            
        except Exception as e:
            logger.exception(f"{self.tr('重新连接Tab信号槽失败:')} {e}")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 停止网络信息获取
            if hasattr(self, 'network_info_manager') and self.network_info_manager.is_running:
                self.network_info_manager.stop_network_info()
            
            # 停止MTKLOG
            if hasattr(self, 'mtklog_manager') and self.mtklog_manager.is_running:
                self.mtklog_manager.stop_mtklog()
            
            # 停止ADB Log
            if hasattr(self, 'adblog_manager') and self.adblog_manager.is_running:
                self.adblog_manager.stop_adblog()
            
            # 停止录制
            if hasattr(self, 'video_manager') and self.video_manager.is_recording:
                self.video_manager.stop_recording()
            
            # 接受关闭事件
            event.accept()
            
        except Exception as e:
            print(f"{self.lang_manager.tr('Close event error:')} {e}")
            event.accept()

