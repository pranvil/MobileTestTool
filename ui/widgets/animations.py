#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动画效果工具类
"""

from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QAbstractAnimation
from PyQt5.QtWidgets import QPushButton


class ButtonAnimation:
    """按钮动画类"""
    
    @staticmethod
    def fade_in(button, duration=150):
        """淡入动画"""
        animation = QPropertyAnimation(button, b"windowOpacity")
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.start(QAbstractAnimation.DeleteWhenStopped)
        return animation
    
    @staticmethod
    def fade_out(button, duration=150):
        """淡出动画"""
        animation = QPropertyAnimation(button, b"windowOpacity")
        animation.setDuration(duration)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.start(QAbstractAnimation.DeleteWhenStopped)
        return animation
    
    @staticmethod
    def scale(button, start_scale=1.0, end_scale=0.95, duration=100):
        """缩放动画"""
        animation = QPropertyAnimation(button, b"geometry")
        animation.setDuration(duration)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        
        rect = button.geometry()
        width = rect.width()
        height = rect.height()
        center_x = rect.x() + width / 2
        center_y = rect.y() + height / 2
        
        animation.setStartValue(rect)
        
        new_width = int(width * end_scale)
        new_height = int(height * end_scale)
        new_x = int(center_x - new_width / 2)
        new_y = int(center_y - new_height / 2)
        
        from PyQt5.QtCore import QRect
        animation.setEndValue(QRect(new_x, new_y, new_width, new_height))
        animation.start(QAbstractAnimation.DeleteWhenStopped)
        return animation
    
    @staticmethod
    def pulse(button, duration=300):
        """脉冲动画"""
        # 先缩小
        scale1 = ButtonAnimation.scale(button, 1.0, 0.95, duration // 2)
        
        # 然后恢复
        def restore():
            scale2 = ButtonAnimation.scale(button, 0.95, 1.0, duration // 2)
            return scale2
        
        scale1.finished.connect(restore)
        return scale1


class AnimatedButton(QPushButton):
    """带动画的按钮"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._animation_enabled = True
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if self._animation_enabled:
            ButtonAnimation.scale(self, 1.0, 0.95, 100)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if self._animation_enabled:
            ButtonAnimation.scale(self, 0.95, 1.0, 100)
        super().mouseReleaseEvent(event)
    
    def set_animation_enabled(self, enabled):
        """设置动画是否启用"""
        self._animation_enabled = enabled
    
    def animate_click(self):
        """动画点击效果"""
        ButtonAnimation.pulse(self, 200)

