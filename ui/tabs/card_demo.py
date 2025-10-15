#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
卡片阴影效果 Demo
直接运行此文件查看效果
"""

import sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGraphicsDropShadowEffect, QSpacerItem, QSizePolicy
)

DARK_QSS = r"""
/* 全局暗色 */
QWidget { background-color: #262626; color: #EAEAEA; font-family: "Microsoft YaHei", "Segoe UI", sans-serif; }

/* Section Header（分区标题） */
QLabel.section-title {
    color: #66B3FF;
    font-weight: 600;
    padding: 2px 6px;
    margin: 10px 2px 6px 2px;
    border: none;
}

/* 卡片容器（真正的内容区） */
#card {
    background: #2E2E2E;
    border: 1px solid #333333;
    border-radius: 10px;
    padding: 14px;
    margin: 6px 4px 16px 4px;
}

/* 按钮（暗色统一） */
QPushButton {
    background-color: #444444;
    color: #EAEAEA;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 6px 12px;
    min-width: 80px;
}
QPushButton:hover { background-color: #555555; border-color: #66B3FF; }
QPushButton:pressed { background-color: #3D3D3D; }
"""


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
    buttons: [("开肩", slot), ...] 这里传文本即可，示例不绑槽
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Card Demo - PyQt5")
        self.resize(900, 520)

        central = QWidget()
        lay = QVBoxLayout(central)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(0)  # 卡片间距在各自 margin 控制

        # MTKLOG 控制
        card1 = make_card("MTKLOG 控制", ["开启", "停止导出", "删除", "SD模式", "USB模式", "安装MTKLOGGER"])
        # ADB Log 控制
        card2 = make_card("ADB Log 控制", ["开启", "导出"])
        # Telephony 控制
        card3 = make_card("Telephony 控制", ["启用 Telephony 日志"])

        lay.addWidget(card1)
        lay.addWidget(card2)
        lay.addWidget(card3)
        lay.addStretch()

        self.setCentralWidget(central)
        self.setStyleSheet(DARK_QSS)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

