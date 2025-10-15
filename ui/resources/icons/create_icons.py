#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建简单的图标文件
使用PIL创建基本的PNG图标
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(name, color, size=48):
    """创建简单图标"""
    # 创建图像
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 绘制圆形背景
    margin = 4
    draw.ellipse([margin, margin, size-margin, size-margin], 
                 fill=color, outline=(255, 255, 255, 200), width=2)
    
    # 保存
    icon_path = os.path.join('ui/resources/icons', f'{name}.png')
    img.save(icon_path)
    print(f'Created: {icon_path}')

def main():
    """主函数"""
    # 确保目录存在
    os.makedirs('ui/resources/icons', exist_ok=True)
    
    # 定义图标
    icons = {
        'refresh': (66, 133, 244),      # 蓝色
        'screenshot': (52, 211, 153),   # 绿色
        'record': (239, 68, 68),        # 红色
        'theme_dark': (30, 41, 59),     # 深色
        'theme_light': (241, 245, 249), # 浅色
        'start': (52, 211, 153),        # 绿色
        'stop': (239, 68, 68),          # 红色
        'export': (59, 130, 246),       # 蓝色
        'delete': (239, 68, 68),        # 红色
        'settings': (168, 85, 247),     # 紫色
        'info': (59, 130, 246),         # 蓝色
        'warning': (251, 191, 36),      # 黄色
        'error': (239, 68, 68),         # 红色
        'success': (52, 211, 153),      # 绿色
    }
    
    # 创建所有图标
    for name, color in icons.items():
        create_icon(name, color)
    
    print('\nAll icons created successfully!')

if __name__ == '__main__':
    main()

