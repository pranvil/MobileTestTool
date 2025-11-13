#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
转码工具对话框
支持ASCII和GSM 7-bit编码的双向转换
"""

import re
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTextEdit, QTabWidget, QWidget, QLabel, QMessageBox, QSizePolicy)
from PyQt5.QtCore import Qt
from core.debug_logger import logger

# 导入GSM 7-bit编码函数
import sys
import os
# 确保项目根目录在 Python 路径中，以便正确导入 sim_reader 包
# 在PyInstaller打包环境中，使用sys._MEIPASS获取资源路径
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # PyInstaller打包环境：sim_reader在sys._MEIPASS中
    base_path = sys._MEIPASS
    project_root = base_path
else:
    # 开发环境：使用__file__计算路径
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from sim_reader.parsers.general import encode_7bit, decode_7bit
except ImportError:
    # 如果导入失败，尝试使用 importlib 动态导入
    import importlib.util
    general_path = os.path.join(project_root, 'sim_reader', 'parsers', 'general.py')
    spec = importlib.util.spec_from_file_location("general", general_path)
    if spec and spec.loader:
        general_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(general_module)
        encode_7bit = general_module.encode_7bit
        decode_7bit = general_module.decode_7bit
    else:
        raise ImportError(f"无法加载 general 模块: {general_path}")


class EncodingToolDialog(QDialog):
    """转码工具对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 从父窗口获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager.get_instance()
        
        self.setWindowTitle(self.lang_manager.tr("转码工具"))
        # 设置初始大小，允许用户自由调整
        self.resize(700, 500)
        # 设置一个更小的最小尺寸，使对话框可以更灵活地调整
        self.setMinimumSize(400, 250)
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        
        # ASCII编码选项卡
        ascii_tab = self.create_ascii_tab()
        self.tab_widget.addTab(ascii_tab, self.lang_manager.tr("ASCII编码"))
        
        # GSM 7-bit编码选项卡
        gsm_tab = self.create_gsm_tab()
        self.tab_widget.addTab(gsm_tab, self.lang_manager.tr("GSM 7-bit编码"))
        
        main_layout.addWidget(self.tab_widget)
        
        # 关闭按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton(self.lang_manager.tr("关闭"))
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        main_layout.addLayout(button_layout)
    
    def create_ascii_tab(self):
        """创建ASCII编码选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # 说明标签
        info_label = QLabel(self.lang_manager.tr("ASCII编码：将文本转换为ASCII十六进制编码，或将ASCII十六进制编码转换为文本"))
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; padding: 5px;")
        layout.addWidget(info_label)
        
        # 输入区域
        input_label = QLabel(self.lang_manager.tr("输入:"))
        layout.addWidget(input_label)
        
        self.ascii_input = QTextEdit()
        self.ascii_input.setPlaceholderText(self.lang_manager.tr("在此输入文本或ASCII HEX..."))
        # 设置较小的最小高度，允许对话框缩小
        self.ascii_input.setMinimumHeight(40)
        # 使用Ignored策略，绕过控件的sizeHint，完全由最小高度和布局控制
        self.ascii_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        layout.addWidget(self.ascii_input, 1)  # stretch因子为1
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.ascii_text_to_hex_btn = QPushButton(self.lang_manager.tr("文本 → ASCII HEX"))
        self.ascii_text_to_hex_btn.clicked.connect(self.ascii_text_to_hex)
        button_layout.addWidget(self.ascii_text_to_hex_btn)
        
        self.ascii_hex_to_text_btn = QPushButton(self.lang_manager.tr("ASCII HEX → 文本"))
        self.ascii_hex_to_text_btn.clicked.connect(self.ascii_hex_to_text)
        button_layout.addWidget(self.ascii_hex_to_text_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 输出区域
        output_label = QLabel(self.lang_manager.tr("输出:"))
        layout.addWidget(output_label)
        
        self.ascii_output = QTextEdit()
        self.ascii_output.setReadOnly(True)
        self.ascii_output.setPlaceholderText(self.lang_manager.tr("转换结果将显示在这里..."))
        # 设置较小的最小高度，允许对话框缩小
        self.ascii_output.setMinimumHeight(40)
        # 使用Ignored策略，绕过控件的sizeHint，完全由最小高度和布局控制
        self.ascii_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        layout.addWidget(self.ascii_output, 1)  # stretch因子为1，与输入框相同
        
        return widget
    
    def create_gsm_tab(self):
        """创建GSM 7-bit编码选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # 说明标签
        info_label = QLabel(self.lang_manager.tr("GSM 7-bit编码：将文本转换为GSM 7-bit打包的十六进制编码，或将GSM 7-bit打包的十六进制编码转换为文本"))
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; padding: 5px;")
        layout.addWidget(info_label)
        
        # 输入区域
        input_label = QLabel(self.lang_manager.tr("输入:"))
        layout.addWidget(input_label)
        
        self.gsm_input = QTextEdit()
        self.gsm_input.setPlaceholderText(self.lang_manager.tr("在此输入文本或7-bit packed HEX..."))
        # 设置较小的最小高度，允许对话框缩小
        self.gsm_input.setMinimumHeight(40)
        # 使用Ignored策略，绕过控件的sizeHint，完全由最小高度和布局控制
        self.gsm_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        layout.addWidget(self.gsm_input, 1)  # stretch因子为1
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.gsm_text_to_hex_btn = QPushButton(self.lang_manager.tr("文本 → 7-bit packed HEX"))
        self.gsm_text_to_hex_btn.clicked.connect(self.gsm_text_to_hex)
        button_layout.addWidget(self.gsm_text_to_hex_btn)
        
        self.gsm_hex_to_text_btn = QPushButton(self.lang_manager.tr("7-bit packed HEX → 文本"))
        self.gsm_hex_to_text_btn.clicked.connect(self.gsm_hex_to_text)
        button_layout.addWidget(self.gsm_hex_to_text_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 输出区域
        output_label = QLabel(self.lang_manager.tr("输出:"))
        layout.addWidget(output_label)
        
        self.gsm_output = QTextEdit()
        self.gsm_output.setReadOnly(True)
        self.gsm_output.setPlaceholderText(self.lang_manager.tr("转换结果将显示在这里..."))
        # 设置较小的最小高度，允许对话框缩小
        self.gsm_output.setMinimumHeight(40)
        # 使用Ignored策略，绕过控件的sizeHint，完全由最小高度和布局控制
        self.gsm_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        layout.addWidget(self.gsm_output, 1)  # stretch因子为1，与输入框相同
        
        return widget
    
    def clean_hex_string(self, hex_string):
        """清理十六进制字符串，去除空格、制表符、换行符等"""
        if not hex_string:
            return ""
        # 去除所有空白字符
        cleaned = re.sub(r'\s+', '', hex_string.strip())
        return cleaned
    
    def validate_hex_string(self, hex_string):
        """验证十六进制字符串是否有效"""
        cleaned = self.clean_hex_string(hex_string)
        if not cleaned:
            return False, self.lang_manager.tr("输入为空")
        
        # 检查是否为有效的十六进制字符
        if not re.match(r'^[0-9A-Fa-f]+$', cleaned):
            return False, self.lang_manager.tr("包含无效的十六进制字符（只允许0-9, A-F, a-f）")
        
        # 检查长度是否为偶数（每个字节需要两个十六进制字符）
        if len(cleaned) % 2 != 0:
            return False, self.lang_manager.tr("十六进制字符串长度必须为偶数（每个字节需要两个字符）")
        
        return True, cleaned
    
    def format_hex_output(self, hex_string):
        """格式化十六进制输出，每个字节用空格分隔"""
        cleaned = self.clean_hex_string(hex_string)
        if not cleaned:
            return ""
        # 每两个字符一组，用空格分隔
        formatted = ' '.join(cleaned[i:i+2] for i in range(0, len(cleaned), 2))
        return formatted.upper()
    
    def ascii_text_to_hex(self):
        """ASCII文本转十六进制"""
        try:
            text = self.ascii_input.toPlainText()
            if not text:
                QMessageBox.warning(self, self.lang_manager.tr("输入错误"), 
                                  self.lang_manager.tr("请输入要转换的文本"))
                return
            
            # 将每个字符转换为两位十六进制，用空格分隔
            hex_result = ' '.join(f'{ord(c):02X}' for c in text)
            
            self.ascii_output.setPlainText(hex_result)
            logger.debug(f"ASCII文本转HEX: {text[:50]}... -> {hex_result[:50]}...")
            
        except Exception as e:
            error_msg = self.lang_manager.tr(f"转换失败: {str(e)}")
            QMessageBox.critical(self, self.lang_manager.tr("错误"), error_msg)
            logger.exception("ASCII文本转HEX失败")
            self.ascii_output.setPlainText("")
    
    def ascii_hex_to_text(self):
        """ASCII十六进制转文本"""
        try:
            hex_input = self.ascii_input.toPlainText()
            
            # 验证和清理输入
            is_valid, result = self.validate_hex_string(hex_input)
            if not is_valid:
                QMessageBox.warning(self, self.lang_manager.tr("输入错误"), result)
                self.ascii_output.setPlainText("")
                return
            
            cleaned_hex = result
            
            # 每两个字符一组转换为字符
            text_result = ""
            for i in range(0, len(cleaned_hex), 2):
                hex_byte = cleaned_hex[i:i+2]
                try:
                    char_code = int(hex_byte, 16)
                    # 检查是否为有效的ASCII字符（0-127）
                    if char_code > 127:
                        QMessageBox.warning(self, self.lang_manager.tr("警告"), 
                                          self.lang_manager.tr(f"字符码 {char_code} (0x{hex_byte}) 超出ASCII范围（0-127），将尝试显示"))
                    text_result += chr(char_code)
                except ValueError as e:
                    raise ValueError(self.lang_manager.tr(f"无效的十六进制字节: {hex_byte}"))
            
            self.ascii_output.setPlainText(text_result)
            logger.debug(f"ASCII HEX转文本: {cleaned_hex[:50]}... -> {text_result[:50]}...")
            
        except Exception as e:
            error_msg = self.lang_manager.tr(f"转换失败: {str(e)}")
            QMessageBox.critical(self, self.lang_manager.tr("错误"), error_msg)
            logger.exception("ASCII HEX转文本失败")
            self.ascii_output.setPlainText("")
    
    def gsm_text_to_hex(self):
        """GSM 7-bit文本转十六进制"""
        try:
            text = self.gsm_input.toPlainText()
            if not text:
                QMessageBox.warning(self, self.lang_manager.tr("输入错误"), 
                                  self.lang_manager.tr("请输入要转换的文本"))
                return
            
            # 检查字符是否在GSM 7-bit字符集内（基本ASCII 0-127）
            invalid_chars = []
            for i, char in enumerate(text):
                char_code = ord(char)
                if char_code > 127:
                    invalid_chars.append(f"位置{i+1}: '{char}' (U+{char_code:04X})")
            
            if invalid_chars:
                warning_msg = self.lang_manager.tr("警告：以下字符可能不在标准GSM 7-bit字符集内：\n") + "\n".join(invalid_chars[:10])
                if len(invalid_chars) > 10:
                    warning_msg += f"\n... 还有 {len(invalid_chars) - 10} 个字符"
                QMessageBox.warning(self, self.lang_manager.tr("字符集警告"), warning_msg)
            
            # 使用GSM 7-bit编码函数
            hex_result = encode_7bit(text)
            
            # 格式化输出，每个字节用空格分隔
            formatted_result = self.format_hex_output(hex_result)
            
            self.gsm_output.setPlainText(formatted_result)
            logger.debug(f"GSM 7-bit文本转HEX: {text[:50]}... -> {formatted_result[:50]}...")
            
        except Exception as e:
            error_msg = self.lang_manager.tr(f"转换失败: {str(e)}")
            QMessageBox.critical(self, self.lang_manager.tr("错误"), error_msg)
            logger.exception("GSM 7-bit文本转HEX失败")
            self.gsm_output.setPlainText("")
    
    def gsm_hex_to_text(self):
        """GSM 7-bit十六进制转文本"""
        try:
            hex_input = self.gsm_input.toPlainText()
            
            # 验证和清理输入
            is_valid, result = self.validate_hex_string(hex_input)
            if not is_valid:
                QMessageBox.warning(self, self.lang_manager.tr("输入错误"), result)
                self.gsm_output.setPlainText("")
                return
            
            cleaned_hex = result
            
            # 使用GSM 7-bit解码函数
            text_result = decode_7bit(cleaned_hex)
            
            self.gsm_output.setPlainText(text_result)
            logger.debug(f"GSM 7-bit HEX转文本: {cleaned_hex[:50]}... -> {text_result[:50]}...")
            
        except Exception as e:
            error_msg = self.lang_manager.tr(f"转换失败: {str(e)}")
            QMessageBox.critical(self, self.lang_manager.tr("错误"), error_msg)
            logger.exception("GSM 7-bit HEX转文本失败")
            self.gsm_output.setPlainText("")

