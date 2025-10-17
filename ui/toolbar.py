#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顶部工具栏
"""

from PyQt5.QtWidgets import (QToolBar, QWidget, QHBoxLayout, QLabel, 
                              QComboBox, QPushButton, QFrame, QLineEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
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
    screen_timeout_clicked = pyqtSignal()  # 永不灭屏按钮
    root_remount_clicked = pyqtSignal()
    theme_toggled = pyqtSignal()
    adb_command_executed = pyqtSignal(str)  # 执行adb命令
    
    def __init__(self, parent=None):
        super().__init__(parent)
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
        self.setIconSize(QSize(16, 16))  # 设置较小的图标尺寸
        
        # 设备选择区域
        device_widget = QWidget()
        device_layout = QHBoxLayout(device_widget)
        device_layout.setContentsMargins(2, 0, 2, 0)
        device_layout.setSpacing(3)
        
        # 设备标签
        device_label = QLabel("设备:")
        device_layout.addWidget(device_label)
        
        # 设备下拉框
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(200)
        self.device_combo.setMaximumWidth(250)
        self.device_combo.setEditable(False)
        self.device_combo.currentTextChanged.connect(self.device_changed.emit)
        device_layout.addWidget(self.device_combo)
        
        # 刷新设备按钮
        self.refresh_btn = QPushButton("刷新设备")
        self.refresh_btn.setIcon(self.refresh_icon)
        self.refresh_btn.setMaximumWidth(80)
        self.refresh_btn.setStyleSheet("QPushButton { padding: 2px 6px; }")
        self.refresh_btn.clicked.connect(self.refresh_clicked.emit)
        device_layout.addWidget(self.refresh_btn)
        
        self.addWidget(device_widget)
        
        # 添加分隔符
        self.addSeparator()
        
        # 快捷操作区域
        quick_widget = QWidget()
        quick_layout = QHBoxLayout(quick_widget)
        quick_layout.setContentsMargins(2, 0, 2, 0)
        quick_layout.setSpacing(3)
        
        # 截图按钮
        self.screenshot_btn = QPushButton("截图")
        self.screenshot_btn.setIcon(self.screenshot_icon)
        self.screenshot_btn.setMaximumWidth(60)
        self.screenshot_btn.setStyleSheet("QPushButton { padding: 2px 6px; }")
        self.screenshot_btn.clicked.connect(self.screenshot_clicked.emit)
        quick_layout.addWidget(self.screenshot_btn)
        
        # 录制按钮
        self.record_btn = QPushButton("开始录制")
        self.record_btn.setIcon(self.record_icon)
        self.record_btn.setMaximumWidth(80)
        self.record_btn.setStyleSheet("QPushButton { padding: 2px 6px; }")
        self.record_btn.setCheckable(True)
        self.record_btn.clicked.connect(self.record_toggled.emit)
        quick_layout.addWidget(self.record_btn)
        
        # 重启手机按钮
        self.reboot_btn = QPushButton("重启手机")
        self.reboot_btn.setMaximumWidth(80)
        self.reboot_btn.setStyleSheet("QPushButton { padding: 2px 6px; }")
        self.reboot_btn.clicked.connect(self.reboot_clicked.emit)
        quick_layout.addWidget(self.reboot_btn)
        
        # 永不灭屏按钮
        self.screen_timeout_btn = QPushButton("永不灭屏")
        self.screen_timeout_btn.setMaximumWidth(80)
        self.screen_timeout_btn.setStyleSheet("QPushButton { padding: 2px 6px; }")
        self.screen_timeout_btn.clicked.connect(self.screen_timeout_clicked.emit)
        quick_layout.addWidget(self.screen_timeout_btn)
        
        # Root&remount按钮
        self.root_remount_btn = QPushButton("Root&&Remount")
        self.root_remount_btn.setMaximumWidth(100)
        self.root_remount_btn.setStyleSheet("QPushButton { padding: 2px 6px; }")
        self.root_remount_btn.clicked.connect(self.root_remount_clicked.emit)
        quick_layout.addWidget(self.root_remount_btn)
        
        self.addWidget(quick_widget)
        
        # 添加分隔符
        self.addSeparator()
        
        # ADB命令输入区域
        adb_widget = QWidget()
        adb_layout = QHBoxLayout(adb_widget)
        adb_layout.setContentsMargins(2, 0, 2, 0)
        adb_layout.setSpacing(3)
        
        # ADB命令标签
        adb_label = QLabel("ADB命令:")
        adb_layout.addWidget(adb_label)
        
        # ADB命令输入框
        self.adb_input = QLineEdit()
        self.adb_input.setPlaceholderText("快速执行adb命令（如: adb devices, adb shell getprop）")
        self.adb_input.setMinimumWidth(250)
        self.adb_input.setMaximumWidth(350)
        self.adb_input.setToolTip(
            "支持快速执行一次性ADB命令\n"
            "例如: adb devices, adb shell pm list packages 等\n"
            "不支持持续输出命令（logcat、top等），请使用对应功能"
        )
        self.adb_input.returnPressed.connect(self._on_adb_command_entered)
        adb_layout.addWidget(self.adb_input)
        
        self.addWidget(adb_widget)
        
        # 添加弹性空间
        self.addWidget(QWidget())
        
        # 主题切换按钮（放置在右侧）
        self.theme_btn = QPushButton("暗色主题")
        self.theme_btn.setIcon(self.theme_dark_icon)
        self.theme_btn.setMaximumWidth(90)
        self.theme_btn.setStyleSheet("QPushButton { padding: 2px 6px; }")
        self.theme_btn.clicked.connect(self.theme_toggled.emit)
        self.addWidget(self.theme_btn)
        
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
            self.record_btn.setText("停止录制")
            self.record_btn.setChecked(True)
        else:
            self.record_btn.setText("开始录制")
            self.record_btn.setChecked(False)
    
    def update_theme_button(self, theme_name):
        """更新主题按钮文本和图标"""
        if theme_name == "dark":
            self.theme_btn.setText("亮色主题")
            self.theme_btn.setIcon(self.theme_light_icon)
        else:
            self.theme_btn.setText("暗色主题")
            self.theme_btn.setIcon(self.theme_dark_icon)
    
    def _on_adb_command_entered(self):
        """处理ADB命令输入"""
        command = self.adb_input.text().strip()
        if command:
            self.adb_command_executed.emit(command)
            self.adb_input.clear()

