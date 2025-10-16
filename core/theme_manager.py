#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主题管理器
负责加载和应用主题样式
"""

import os
from PyQt5.QtCore import QFile, QTextStream
from PyQt5.QtWidgets import QApplication


class ThemeManager:
    """主题管理器"""
    
    def __init__(self):
        self.current_theme = "dark"
        self.theme_dir = "ui/resources/themes"
        
    def load_theme(self, theme_name="dark"):
        """加载主题"""
        try:
            theme_file = os.path.join(self.theme_dir, f"{theme_name}.qss")
            
            if not os.path.exists(theme_file):
                print(f"Theme file not found: {theme_file}")
                return False
            
            # 读取样式表
            with open(theme_file, 'r', encoding='utf-8') as f:
                style_sheet = f.read()
            
            # 应用样式表
            QApplication.instance().setStyleSheet(style_sheet)
            
            self.current_theme = theme_name            
            return True
            
        except Exception as e:
            print(f"Failed to load theme: {str(e)}")
            return False
    
    def toggle_theme(self):
        """切换主题"""
        if self.current_theme == "dark":
            return self.load_theme("light")
        else:
            return self.load_theme("dark")
    
    def get_current_theme(self):
        """获取当前主题"""
        return self.current_theme
    
    def apply_custom_style(self, widget, style):
        """应用自定义样式到指定控件"""
        widget.setStyleSheet(style)

