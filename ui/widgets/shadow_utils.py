#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阴影效果工具函数
用于给QFrame等控件添加阴影效果
"""

from typing import Union, Tuple, Optional
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QWidget
from PyQt5.QtGui import QColor


def add_shadow(
    widget: QWidget,
    blur: float = 18,
    dx: float = 0,
    dy: float = 4,
    alpha: int = 120,
    color: Optional[Union[QColor, Tuple[int, int, int]]] = None
) -> QGraphicsDropShadowEffect:
    """
    给 widget 添加阴影效果（幂等：多次调用会更新现有effect，而非重复创建）
    
    参数:
        widget: 要添加阴影的控件（通常是QFrame）
        blur: 模糊半径，默认18（会自动限制≥0）
        dx: 水平偏移，默认0
        dy: 垂直偏移，默认4（轻微下坠）
        alpha: 透明度（0-255），默认120（约47%），会自动限制在0-255范围
        color: 阴影颜色，默认黑色。可传入QColor或RGB元组(r,g,b)
    
    返回:
        QGraphicsDropShadowEffect对象
    
    注意:
        - 多次调用会更新现有effect，而非重复创建（幂等性）
        - blur会自动限制≥0
        - alpha会自动限制在0-255范围
    """
    # 参数校验与限制
    blur = max(0, blur)
    alpha = max(0, min(255, int(alpha)))
    
    # 处理颜色参数
    if color is None:
        shadow_color = QColor(0, 0, 0, alpha)
    elif isinstance(color, QColor):
        shadow_color = QColor(color)
        shadow_color.setAlpha(alpha)
    elif isinstance(color, (tuple, list)) and len(color) >= 3:
        shadow_color = QColor(color[0], color[1], color[2], alpha)
    else:
        shadow_color = QColor(0, 0, 0, alpha)
    
    # 幂等性：检查是否已存在effect
    existing_effect = widget.graphicsEffect()
    if isinstance(existing_effect, QGraphicsDropShadowEffect):
        # 更新现有effect
        existing_effect.setBlurRadius(blur)
        existing_effect.setOffset(dx, dy)
        existing_effect.setColor(shadow_color)
        return existing_effect
    else:
        # 创建新effect
        eff = QGraphicsDropShadowEffect(widget)
        eff.setBlurRadius(blur)
        eff.setOffset(dx, dy)
        eff.setColor(shadow_color)
        widget.setGraphicsEffect(eff)
        return eff


def add_card_shadow(widget: QWidget) -> QGraphicsDropShadowEffect:
    """
    给卡片添加标准阴影效果（最常用）
    
    参数:
        widget: 要添加阴影的卡片控件
    
    返回:
        QGraphicsDropShadowEffect对象
    
    性能提示:
        - 大量卡片在QScrollArea中时，阴影会增加合成成本
        - 大列表建议按需开关或只为self.lang_manager.tr("首层卡片")加阴影
        - 确保卡片四周有margin（8-16px），否则阴影会被父容器裁掉
    """
    return add_shadow(widget, blur=18, dx=0, dy=4, alpha=120)


def add_light_shadow(widget: QWidget) -> QGraphicsDropShadowEffect:
    """
    给控件添加轻微阴影效果
    适用于较小的元素
    
    参数:
        widget: 要添加阴影的控件
    
    返回:
        QGraphicsDropShadowEffect对象
    """
    return add_shadow(widget, blur=12, dx=0, dy=2, alpha=80)


def add_strong_shadow(widget: QWidget) -> QGraphicsDropShadowEffect:
    """
    给控件添加强烈阴影效果
    适用于需要突出显示的元素
    
    参数:
        widget: 要添加阴影的控件
    
    返回:
        QGraphicsDropShadowEffect对象
    """
    return add_shadow(widget, blur=24, dx=0, dy=6, alpha=150)


def add_floating_shadow(widget: QWidget) -> QGraphicsDropShadowEffect:
    """
    给控件添加浮空阴影效果
    无偏移，适合悬浮按钮等
    
    参数:
        widget: 要添加阴影的控件
    
    返回:
        QGraphicsDropShadowEffect对象
    """
    return add_shadow(widget, blur=20, dx=0, dy=0, alpha=100)


def remove_shadow(widget: QWidget) -> None:
    """
    移除控件的阴影效果
    
    参数:
        widget: 要移除阴影的控件
    """
    widget.setGraphicsEffect(None)

