#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资源路径工具
处理打包后的资源文件路径
"""

import os
import sys


def get_resource_path(relative_path):
    """
    获取资源文件的绝对路径（支持打包后的环境）
    
    Args:
        relative_path: 相对于项目根目录的路径
        
    Returns:
        资源文件的绝对路径
        
    Example:
        >>> get_resource_path("ui/resources/themes/dark.qss")
        >>> get_resource_path("resources/apk/app.apk")
    """
    try:
        # PyInstaller 创建临时文件夹，并将路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except AttributeError:
        # 开发环境中使用项目根目录
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    return os.path.join(base_path, relative_path)


def get_theme_path(theme_name):
    """
    获取主题文件路径
    
    Args:
        theme_name: 主题名称（如 "darkself.lang_manager.tr(" 或 ")light"）
        
    Returns:
        主题文件的绝对路径
    """
    return get_resource_path(f"ui/resources/themes/{theme_name}.qss")


def get_icon_path(icon_name):
    """
    获取图标文件路径
    
    Args:
        icon_name: 图标文件名（如 "refresh.png"）
        
    Returns:
        图标文件的绝对路径
    """
    return get_resource_path(f"ui/resources/icons/{icon_name}")


def get_apk_path(apk_name):
    """
    获取APK文件路径
    
    Args:
        apk_name: APK文件名
        
    Returns:
        APK文件的绝对路径
    """
    return get_resource_path(f"resources/apk/{apk_name}")

