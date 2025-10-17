#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拖拽功能实现示例
展示如何在自定义按钮中实现拖拽排序
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QFrame, QLabel, QApplication)
from PyQt5.QtCore import Qt, QMimeData, QPoint
from PyQt5.QtGui import QDrag, QPainter, QPixmap
import sys

class DraggableButton(QPushButton):
    """可拖拽的按钮"""
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setAcceptDrops(True)
        self.original_parent = parent
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        
        if ((event.pos() - self.drag_start_position).manhattanLength() < 
            QApplication.startDragDistance()):
            return
        
        # 开始拖拽
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.text())
        drag.setMimeData(mime_data)
        
        # 创建拖拽预览
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        
        # 执行拖拽
        drop_action = drag.exec_(Qt.MoveAction)

class DropArea(QWidget):
    """可接受拖拽的区域"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(5)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        if event.mimeData().hasText():
            text = event.mimeData().text()
            
            # 找到拖拽的源按钮
            source_button = event.source()
            if source_button and isinstance(source_button, DraggableButton):
                # 从原位置移除
                if source_button.parent():
                    source_button.parent().layout().removeWidget(source_button)
                
                # 计算插入位置
                drop_position = event.pos()
                insert_index = self._get_insert_position(drop_position)
                
                # 插入到新位置
                self.layout.insertWidget(insert_index, source_button)
                source_button.setParent(self)
                
                event.acceptProposedAction()
            else:
                # 创建新按钮
                new_button = DraggableButton(text, self)
                insert_index = self._get_insert_position(event.pos())
                self.layout.insertWidget(insert_index, new_button)
                event.acceptProposedAction()
        else:
            event.ignore()
    
    def _get_insert_position(self, pos):
        """根据鼠标位置计算插入位置"""
        for i in range(self.layout.count()):
            item = self.layout.itemAt(i)
            if item and item.widget():
                widget_rect = item.widget().geometry()
                if pos.x() < widget_rect.center().x():
                    return i
        return self.layout.count()

class CustomButtonCard(QFrame):
    """自定义按钮卡片"""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setFrameStyle(QFrame.StyledPanel)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel(title)
        title_label.setProperty("class", "section-title")
        layout.addWidget(title_label)
        
        # 按钮区域
        self.button_area = DropArea()
        layout.addWidget(self.button_area)
        
        # 添加一些示例按钮
        self._add_example_buttons()
    
    def _add_example_buttons(self):
        """添加示例按钮"""
        buttons = ["原有按钮1", "原有按钮2"]
        for text in buttons:
            btn = QPushButton(text)
            self.button_area.layout().addWidget(btn)
    
    def add_custom_button(self, button_text):
        """添加自定义按钮"""
        custom_btn = DraggableButton(button_text, self.button_area)
        self.button_area.layout().addWidget(custom_btn)

# 使用示例
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("拖拽功能示例")
        self.setGeometry(100, 100, 800, 600)
        
        layout = QVBoxLayout(self)
        
        # 创建卡片
        self.card = CustomButtonCard("示例卡片")
        layout.addWidget(self.card)
        
        # 添加自定义按钮的按钮
        add_btn = QPushButton("添加自定义按钮")
        add_btn.clicked.connect(self.add_custom_button)
        layout.addWidget(add_btn)
    
    def add_custom_button(self):
        """添加自定义按钮"""
        import time
        text = f"自定义按钮_{int(time.time())}"
        self.card.add_custom_button(text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

"""
实现要点总结：

1. **DraggableButton类**：
   - 继承QPushButton
   - 重写mousePressEvent和mouseMoveEvent
   - 实现拖拽开始逻辑

2. **DropArea类**：
   - 继承QWidget
   - 重写dragEnterEvent, dragMoveEvent, dropEvent
   - 处理拖拽放置逻辑

3. **插入位置计算**：
   - 根据鼠标位置计算插入索引
   - 动态调整布局

4. **集成到现有系统**：
   - 修改CustomButtonManager
   - 更新UI注入逻辑
   - 保存新的按钮顺序

实现难度：中等
开发时间：1-2天
测试时间：1天
"""
