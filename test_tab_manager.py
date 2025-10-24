#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tab管理功能测试脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication
from core.tab_config_manager import TabConfigManager
from core.debug_logger import logger

def test_tab_config_manager():
    """测试Tab配置管理器"""
    print("开始测试Tab配置管理器...")
    
    # 创建管理器实例
    manager = TabConfigManager()
    
    # 测试获取默认配置
    print(f"默认Tab顺序: {manager.get_tab_order()}")
    print(f"默认Tab可见性: {manager.get_tab_visibility()}")
    print(f"可见Tab列表: {manager.get_visible_tabs()}")
    
    # 测试创建自定义Tab
    custom_tab_data = {
        'name': '测试Tab',
        'description': '这是一个测试Tab',
        'cards': []
    }
    
    tab_id = manager.create_custom_tab(custom_tab_data)
    print(f"创建自定义Tab ID: {tab_id}")
    
    # 测试创建自定义Card
    custom_card_data = {
        'name': '测试Card',
        'description': '这是一个测试Card',
        'tab_id': tab_id,
        'buttons': []
    }
    
    card_id = manager.create_custom_card(custom_card_data)
    print(f"创建自定义Card ID: {card_id}")
    
    # 测试获取配置信息
    config_info = manager.get_config_info()
    print(f"配置信息: {config_info}")
    
    print("Tab配置管理器测试完成!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_tab_config_manager()
    app.quit()
