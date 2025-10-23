#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顶部工具栏
"""

from PyQt5.QtWidgets import (QToolBar, QWidget, QHBoxLayout, QLabel, 
                              QComboBox, QPushButton, QFrame, QLineEdit)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from core.resource_utils import get_icon_path


class DeviceToolBar(QToolBar):
    """设备工具栏"""
    
    # 信号定义
    device_changed = pyqtSignal(str)
    refresh_clicked = pyqtSignal()
    screenshot_clicked = pyqtSignal()
    record_toggled = pyqtSignal(bool)
    reboot_clicked = pyqtSignal()
    root_remount_clicked = pyqtSignal()
    theme_toggled = pyqtSignal()
    adb_command_executed = pyqtSignal(str)  # 执行adb命令
    language_changed = pyqtSignal(str)  # 语言切换信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 从父窗口获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            # 如果没有父窗口或语言管理器，创建一个默认的
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager()
        self.setup_icons()
        self.setup_toolbar()
    
    def setup_icons(self):
        """设置图标"""
        # 工具栏图标
        self.refresh_icon = QIcon(get_icon_path('refresh.png'))
        self.screenshot_icon = QIcon(get_icon_path('screenshot.png'))
        self.record_icon = QIcon(get_icon_path('record.png'))
        self.theme_dark_icon = QIcon(get_icon_path('theme_dark.png'))
        self.theme_light_icon = QIcon(get_icon_path('theme_light.png'))
        
    def setup_toolbar(self):
        """设置工具栏"""
        # 设置工具栏属性
        self.setMovable(False)
        self.setFloatable(False)
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        
        # 设备选择区域
        device_widget = QWidget()
        device_layout = QHBoxLayout(device_widget)
        device_layout.setContentsMargins(0, 0, 0, 0)
        device_layout.setSpacing(5)
        
        # 设备标签
        device_label = QLabel(self.lang_manager.tr("设备:"))
        device_layout.addWidget(device_label)
        
        # 设备下拉框
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(250)
        self.device_combo.setEditable(False)
        self.device_combo.currentTextChanged.connect(self.device_changed.emit)
        device_layout.addWidget(self.device_combo)
        
        # 刷新设备按钮
        self.refresh_btn = QPushButton(self.lang_manager.tr("刷新设备"))
        self.refresh_btn.setIcon(self.refresh_icon)
        self.refresh_btn.clicked.connect(self.refresh_clicked.emit)
        device_layout.addWidget(self.refresh_btn)
        
        self.addWidget(device_widget)
        
        # 添加分隔符
        self.addSeparator()
        
        # 快捷操作区域
        quick_widget = QWidget()
        quick_layout = QHBoxLayout(quick_widget)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(5)
        
        # 截图按钮
        self.screenshot_btn = QPushButton(self.lang_manager.tr("截图"))
        self.screenshot_btn.setIcon(self.screenshot_icon)
        self.screenshot_btn.clicked.connect(self.screenshot_clicked.emit)
        quick_layout.addWidget(self.screenshot_btn)
        
        # 录制按钮
        self.record_btn = QPushButton(self.lang_manager.tr("开始录制"))
        self.record_btn.setIcon(self.record_icon)
        self.record_btn.setCheckable(True)
        self.record_btn.clicked.connect(self.record_toggled.emit)
        quick_layout.addWidget(self.record_btn)
        
        # 重启手机按钮
        self.reboot_btn = QPushButton(self.lang_manager.tr("重启手机"))
        self.reboot_btn.clicked.connect(self.reboot_clicked.emit)
        quick_layout.addWidget(self.reboot_btn)
        
        # Root&remount按钮
        self.root_remount_btn = QPushButton(self.lang_manager.tr("Root&&Remount"))
        self.root_remount_btn.clicked.connect(self.root_remount_clicked.emit)
        quick_layout.addWidget(self.root_remount_btn)
        
        self.addWidget(quick_widget)
        
        # 添加分隔符
        self.addSeparator()
        
        # ADB命令输入区域
        adb_widget = QWidget()
        adb_layout = QHBoxLayout(adb_widget)
        adb_layout.setContentsMargins(0, 0, 0, 0)
        adb_layout.setSpacing(5)
        
        # ADB命令标签
        adb_label = QLabel(self.lang_manager.tr("ADB命令:"))
        adb_layout.addWidget(adb_label)
        
        # ADB命令输入框
        self.adb_input = QLineEdit()
        self.adb_input.setPlaceholderText(self.lang_manager.tr("快速执行adb命令（如: adb devices, adb shell getprop）"))
        self.adb_input.setMinimumWidth(300)
        self.adb_input.setToolTip(
            self.lang_manager.tr("支持快速执行一次性ADB命令\n") +
            self.lang_manager.tr("例如: adb devices, adb shell pm list packages 等\n") +
            self.lang_manager.tr("不支持持续输出命令（logcat、top等），请使用对应功能")
        )
        self.adb_input.returnPressed.connect(self._on_adb_command_entered)
        adb_layout.addWidget(self.adb_input)
        
        self.addWidget(adb_widget)
        
        # 添加弹性空间
        self.addWidget(QWidget())
        
        # 主题切换按钮
        self.theme_btn = QPushButton(self.lang_manager.tr("暗色主题"))
        self.theme_btn.setIcon(self.theme_dark_icon)
        self.theme_btn.clicked.connect(self.theme_toggled.emit)
        self.addWidget(self.theme_btn)
        
        # 语言切换按钮（放置在右侧）
        self.language_btn = QPushButton("🌐 中/EN")
        self.language_btn.setToolTip(self.lang_manager.tr("点击切换语言 / Click to switch language"))
        self.language_btn.clicked.connect(self._on_language_toggle)
        self.addWidget(self.language_btn)

    def set_device_list(self, devices):
        """设置设备列表"""
        self.device_combo.clear()
        self.device_combo.addItems(devices)
        
    def get_selected_device(self):
        """获取选中的设备"""
        return self.device_combo.currentText()
        
    def set_selected_device(self, device):
        """设置选中的设备"""
        index = self.device_combo.findText(device)
        if index >= 0:
            self.device_combo.setCurrentIndex(index)
            
    def update_record_button(self, is_recording):
        """更新录制按钮状态"""
        if is_recording:
            self.record_btn.setText(self.lang_manager.tr("停止录制"))
            self.record_btn.setChecked(True)
        else:
            self.record_btn.setText(self.lang_manager.tr("开始录制"))
            self.record_btn.setChecked(False)
    
    def update_theme_button(self, theme_name):
        """更新主题按钮文本和图标"""
        if theme_name == "dark":
            self.theme_btn.setText(self.lang_manager.tr("亮色主题"))
            self.theme_btn.setIcon(self.theme_light_icon)
        else:
            self.theme_btn.setText(self.lang_manager.tr("暗色主题"))
            self.theme_btn.setIcon(self.theme_dark_icon)
    
    def _on_adb_command_entered(self):
        """处理ADB命令输入"""
        command = self.adb_input.text().strip()
        if command:
            self.adb_command_executed.emit(command)
            self.adb_input.clear()
    
    def _on_language_toggle(self):
        """处理语言切换"""
        current_lang = self.lang_manager.get_current_language()
        new_lang = 'en' if current_lang == 'zh' else 'zh'
        self.lang_manager.set_language(new_lang)
        self.language_changed.emit(new_lang)
        self._update_language_button()
    
    def _update_language_button(self):
        """更新语言按钮显示"""
        current_lang = self.lang_manager.get_current_language()
        if current_lang == 'zh':
            self.language_btn.setText("🌐 " + self.lang_manager.tr("中/EN"))
        else:
            self.language_btn.setText("🌐 " + self.lang_manager.tr("EN/中"))
    
    def refresh_texts(self, lang_manager=None):
        """刷新所有文本（用于语言切换）"""
        if lang_manager:
            self.lang_manager = lang_manager
        
        if not self.lang_manager:
            return
        
        # 刷新设备标签
        device_label = self.findChild(QLabel)
        if device_label and device_label.text() == self.lang_manager.tr("设备:"):
            device_label.setText(self.lang_manager.tr("设备:"))
        
        # 刷新按钮文本
        self.refresh_btn.setText(self.lang_manager.tr("刷新设备"))
        self.screenshot_btn.setText(self.lang_manager.tr("截图"))
        self.record_btn.setText(self.lang_manager.tr("开始录制"))
        self.reboot_btn.setText(self.lang_manager.tr("重启手机"))
        self.root_remount_btn.setText(self.lang_manager.tr("Root&&Remount"))
        
        # 刷新ADB命令标签
        adb_label = None
        for widget in self.findChildren(QLabel):
            if widget.text() == "ADB命令:":
                adb_label = widget
                break
        if adb_label:
            adb_label.setText(self.lang_manager.tr("ADB命令:"))
        
        # 刷新ADB输入框占位符
        self.adb_input.setPlaceholderText(self.lang_manager.tr("快速执行adb命令（如: adb devices, adb shell getprop）"))
        
        # 刷新主题按钮
        current_theme = "dark"  # 默认主题
        if hasattr(self, 'theme_btn'):
            if "亮色" in self.theme_btn.text():
                current_theme = "light"
            self.theme_btn.setText(self.lang_manager.tr("暗色主题") if current_theme == "dark" else self.lang_manager.tr("亮色主题"))
        
        # 更新语言按钮
        self._update_language_button()

