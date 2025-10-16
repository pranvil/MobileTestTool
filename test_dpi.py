#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DPI信息检测工具
用于验证DPI配置是否正确生效
"""

import sys
import os
import platform

# 设置DPI环境变量
os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
os.environ['QT_SCALE_FACTOR_ROUNDING_POLICY'] = 'PassThrough'
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class DPITestWindow(QWidget):
    """DPI测试窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DPI信息检测工具")
        self.setMinimumSize(600, 500)
        self.setup_ui()
        self.collect_info()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("DPI配置检测")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 说明
        desc = QLabel("这个工具显示当前系统的DPI设置和Qt配置信息\n用于验证DPI优化是否生效")
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(desc)
        
        # 信息显示区域
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.info_text)
        
        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新信息")
        refresh_btn.clicked.connect(self.collect_info)
        refresh_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 11pt;
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        layout.addWidget(refresh_btn)
        
    def collect_info(self):
        """收集DPI信息"""
        info_lines = []
        
        # 分隔线
        def separator(title=""):
            if title:
                info_lines.append(f"\n{'='*60}")
                info_lines.append(f"  {title}")
                info_lines.append(f"{'='*60}")
            else:
                info_lines.append(f"{'-'*60}")
        
        separator("系统信息")
        info_lines.append(f"操作系统: {platform.system()} {platform.release()}")
        info_lines.append(f"版本: {platform.version()}")
        info_lines.append(f"架构: {platform.machine()}")
        info_lines.append(f"Python版本: {sys.version.split()[0]}")
        
        # Qt版本
        from PyQt5.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
        info_lines.append(f"Qt版本: {QT_VERSION_STR}")
        info_lines.append(f"PyQt版本: {PYQT_VERSION_STR}")
        
        separator("环境变量")
        env_vars = [
            'QT_ENABLE_HIGHDPI_SCALING',
            'QT_SCALE_FACTOR_ROUNDING_POLICY',
            'QT_AUTO_SCREEN_SCALE_FACTOR',
            'QT_FONT_DPI',
            'QT_SCREEN_SCALE_FACTORS',
        ]
        for var in env_vars:
            value = os.environ.get(var, '(未设置)')
            status = "✅" if value != '(未设置)' else "❌"
            info_lines.append(f"{status} {var}: {value}")
        
        separator("Qt属性")
        app = QApplication.instance()
        
        # 检查Qt属性
        attrs = [
            (Qt.AA_EnableHighDpiScaling, "AA_EnableHighDpiScaling"),
            (Qt.AA_UseHighDpiPixmaps, "AA_UseHighDpiPixmaps"),
            (Qt.AA_DisableHighDpiScaling, "AA_DisableHighDpiScaling"),
        ]
        
        for attr, name in attrs:
            # 注意：testAttribute在app创建后才能用
            try:
                enabled = app.testAttribute(attr)
                status = "✅ 已启用" if enabled else "❌ 未启用"
            except:
                status = "⚠️  无法检测"
            info_lines.append(f"{name}: {status}")
        
        separator("主显示器信息")
        screen = app.primaryScreen()
        
        # 物理尺寸
        size = screen.size()
        physical_size = screen.physicalSize()
        info_lines.append(f"分辨率: {size.width()} x {size.height()} 像素")
        info_lines.append(f"物理尺寸: {physical_size.width():.1f} x {physical_size.height():.1f} mm")
        
        # DPI信息
        physical_dpi_x = screen.physicalDotsPerInchX()
        physical_dpi_y = screen.physicalDotsPerInchY()
        logical_dpi_x = screen.logicalDotsPerInchX()
        logical_dpi_y = screen.logicalDotsPerInchY()
        
        info_lines.append(f"物理DPI: {physical_dpi_x:.1f} x {physical_dpi_y:.1f}")
        info_lines.append(f"逻辑DPI: {logical_dpi_x:.1f} x {logical_dpi_y:.1f}")
        
        # 缩放比例
        device_ratio = screen.devicePixelRatio()
        info_lines.append(f"设备像素比: {device_ratio:.2f}")
        
        # 推算Windows缩放百分比
        scale_percent = int(logical_dpi_x / 96 * 100)
        info_lines.append(f"Windows缩放设置: 约 {scale_percent}%")
        
        # 刷新率
        refresh_rate = screen.refreshRate()
        info_lines.append(f"刷新率: {refresh_rate} Hz")
        
        # 可用几何区域
        geometry = screen.geometry()
        available_geometry = screen.availableGeometry()
        info_lines.append(f"屏幕几何区域: {geometry.width()} x {geometry.height()}")
        info_lines.append(f"可用区域: {available_geometry.width()} x {available_geometry.height()}")
        
        separator("所有显示器")
        screens = app.screens()
        info_lines.append(f"检测到 {len(screens)} 个显示器\n")
        
        for i, screen in enumerate(screens, 1):
            info_lines.append(f"显示器 #{i}: {screen.name()}")
            size = screen.size()
            dpi = screen.logicalDotsPerInch()
            ratio = screen.devicePixelRatio()
            scale = int(dpi / 96 * 100)
            
            info_lines.append(f"  分辨率: {size.width()} x {size.height()}")
            info_lines.append(f"  逻辑DPI: {dpi:.1f}")
            info_lines.append(f"  缩放比例: {ratio:.2f} ({scale}%)")
            
            if i == len(screens):
                info_lines.append("")
        
        separator("字体信息")
        font = app.font()
        info_lines.append(f"系统字体: {font.family()}")
        info_lines.append(f"字体大小: {font.pointSize()} pt")
        info_lines.append(f"像素大小: {font.pixelSize()} px")
        
        hinting = font.hintingPreference()
        hinting_names = {
            QFont.PreferDefaultHinting: "默认",
            QFont.PreferNoHinting: "无微调",
            QFont.PreferVerticalHinting: "垂直微调",
            QFont.PreferFullHinting: "完整微调",
        }
        info_lines.append(f"字体微调: {hinting_names.get(hinting, '未知')}")
        
        strategy = font.styleStrategy()
        info_lines.append(f"渲染策略: {strategy}")
        
        # 字体大小建议
        info_lines.append(f"\n📏 字体大小建议:")
        current_dpi = screen.logicalDotsPerInch()
        dpi_scale = current_dpi / 96.0
        
        if dpi_scale <= 1.0:
            info_lines.append(f"   当前DPI ({current_dpi}): 建议字体大小 9pt")
        elif dpi_scale <= 1.25:
            info_lines.append(f"   当前DPI ({current_dpi}): 建议字体大小 10pt")
        elif dpi_scale <= 1.5:
            info_lines.append(f"   当前DPI ({current_dpi}): 建议字体大小 11pt")
        elif dpi_scale <= 2.0:
            info_lines.append(f"   当前DPI ({current_dpi}): 建议字体大小 12pt")
        else:
            info_lines.append(f"   当前DPI ({current_dpi}): 建议字体大小 13pt")
        
        info_lines.append(f"   实际字体大小: {font.pointSize()}pt")
        
        if font.pointSize() < 9:
            info_lines.append("   ⚠️  字体可能过小，建议增大")
        elif font.pointSize() > 13:
            info_lines.append("   ⚠️  字体可能过大，建议减小")
        else:
            info_lines.append("   ✅ 字体大小合适")
        
        separator("诊断建议")
        
        # 诊断
        issues = []
        suggestions = []
        
        # 检查DPI缩放
        if scale_percent > 100:
            if not app.testAttribute(Qt.AA_EnableHighDpiScaling):
                issues.append("⚠️  高DPI显示器但未启用AA_EnableHighDpiScaling")
                suggestions.append("在创建QApplication前调用: QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)")
        
        # 检查环境变量
        if os.environ.get('QT_ENABLE_HIGHDPI_SCALING') != '1':
            issues.append("⚠️  未设置QT_ENABLE_HIGHDPI_SCALING环境变量")
            suggestions.append("在导入PyQt前设置: os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'")
        
        # 检查manifest（仅Windows）
        if platform.system() == 'Windows':
            info_lines.append("📋 Manifest检查:")
            info_lines.append("   请确认exe包含DPI感知的manifest文件")
            info_lines.append("   使用Resource Hacker查看RT_MANIFEST资源")
        
        if not issues:
            info_lines.append("✅ 所有DPI配置看起来正常!")
            info_lines.append("   如果仍有模糊问题，可能需要检查Windows manifest配置")
        else:
            for issue in issues:
                info_lines.append(issue)
            info_lines.append("\n🔧 建议修复:")
            for suggestion in suggestions:
                info_lines.append(f"   {suggestion}")
        
        separator()
        info_lines.append("\n💡 提示: 更改系统DPI设置后，需要注销重新登录才能完全生效")
        
        # 显示信息
        self.info_text.setPlainText("\n".join(info_lines))


def main():
    """主函数"""
    # 必须在创建QApplication之前设置
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("DPI测试工具")
    
    window = DPITestWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

