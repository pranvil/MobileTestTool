#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
卡片阴影效果示例
展示如何在QFrame上添加阴影效果（与demo完全一致）
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                              QPushButton, QLabel, QGraphicsDropShadowEffect,
                              QSpacerItem, QSizePolicy)
from PyQt5.QtGui import QColor


def make_shadow(widget, radius=18, dx=0, dy=4, alpha=120):
    """给 widget 添加阴影效果"""
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(radius)
    eff.setOffset(dx, dy)
    eff.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(eff)


def make_card(title_text, buttons):
    """
    创建一组：Section Title + Card(QFrame) 容器 + 按钮布局
    buttons: [("开启", slot), ...] 这里传文本即可，示例不绑槽
    """
    root = QWidget()
    root_layout = QVBoxLayout(root)
    root_layout.setContentsMargins(0, 0, 0, 0)
    root_layout.setSpacing(6)

    # Section Header
    title = QLabel(title_text)
    title.setObjectName("sectionTitle")
    title.setProperty("class", "section-title")   # 供 QSS 选择器使用
    title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    root_layout.addWidget(title)

    # Card 容器（加阴影）
    card = QFrame()
    card.setObjectName("card")
    make_shadow(card)  # 真实阴影
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(12, 12, 12, 12)
    card_layout.setSpacing(10)

    # 一行按钮
    row = QHBoxLayout()
    row.setSpacing(10)
    for text in buttons:
        btn = QPushButton(text)
        row.addWidget(btn)
    row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
    card_layout.addLayout(row)

    root_layout.addWidget(card)
    return root


class CardShadowExample(QWidget):
    """卡片阴影示例"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(0)  # 卡片间距在各自 margin 控制

        # MTKLOG 控制
        card1 = make_card("MTKLOG 控制", ["开启", "停止导出", "删除", "SD模式", "USB模式", "安装MTKLOGGER"])
        # ADB Log 控制
        card2 = make_card("ADB Log 控制", ["开启", "导出"])
        # Telephony 控制
        card3 = make_card("Telephony 控制", ["启用 Telephony 日志"])

        main_layout.addWidget(card1)
        main_layout.addWidget(card2)
        main_layout.addWidget(card3)
        main_layout.addStretch()


# 使用示例：
# 在 log_control_tab.py 中，可以这样改造 create_mtklog_group 方法：
#
# def create_mtklog_group(self):
#     """创建 MTKLOG 控制组（带阴影的卡片）"""
#     # 使用 make_card 函数
#     return make_card("MTKLOG 控制", ["开启", "停止导出", "删除"])

