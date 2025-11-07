#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PR翻译对话框
"""

import os
import urllib.parse
import urllib.request
import json
import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QTextEdit, QPushButton, QMessageBox,
                             QScrollArea, QWidget, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from ui.widgets.shadow_utils import add_card_shadow
from core.debug_logger import logger

try:
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


class TranslationWorker(QThread):
    """翻译工作线程"""
    finished = pyqtSignal(str)  # 翻译完成，传递文件路径
    error = pyqtSignal(str)  # 翻译错误
    progress = pyqtSignal(str)  # 进度更新
    
    def __init__(self, data_dict, email=None, parent=None):
        super().__init__(parent)
        self.data_dict = data_dict
        self.email = email
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def run(self):
        """执行翻译"""
        try:
            # 定义不需要翻译的字段
            no_translate_fields = ['log', 'associate_specification', 'test_plan_reference', 
                                  'tools_and_platforms', 'user_impact', 'reproducing_rate']
            
            # 翻译所有字段
            translations = {}
            for key, chinese_text in self.data_dict.items():
                if chinese_text and chinese_text.strip():
                    if key in no_translate_fields:
                        # 不需要翻译的字段，直接使用中文
                        translations[key] = ""
                        self.progress.emit(f"{self.tr('跳过翻译')}: {key}...")
                    else:
                        # 需要翻译的字段
                        self.progress.emit(f"{self.tr('正在翻译')}: {key}...")
                        translated = self.translate_text(chinese_text)
                        translations[key] = translated
                else:
                    translations[key] = ""
            
            # 生成Word文档
            self.progress.emit(self.tr("正在生成Word文档..."))
            doc_path = self.generate_word_document(self.data_dict, translations)
            
            self.finished.emit(doc_path)
        except Exception as e:
            logger.exception(f"{self.tr('翻译失败')}: {str(e)}")
            self.error.emit(str(e))
    
    def translate_text(self, text):
        """使用MyMemory API翻译文本"""
        try:
            # 构建API URL
            base_url = "https://api.mymemory.translated.net/get"
            params = {
                'q': text,
                'langpair': 'zh|en'
            }
            
            # 如果提供了邮箱，添加到参数中
            if self.email and self.email.strip():
                params['de'] = self.email.strip()
            
            url = f"{base_url}?{urllib.parse.urlencode(params)}"
            
            # 发送请求
            request = urllib.request.Request(url)
            request.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                if data.get('responseStatus') == 200:
                    translated_text = data.get('responseData', {}).get('translatedText', '')
                    return translated_text
                else:
                    logger.warning(f"MyMemory API错误: {data.get('responseStatus')}")
                    return text  # 翻译失败时返回原文
        except Exception as e:
            logger.exception(f"翻译API调用失败: {str(e)}")
            return text  # 翻译失败时返回原文
    
    def generate_word_document(self, chinese_dict, english_dict):
        """生成Word文档"""
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx库未安装，请运行: pip install python-docx")
        
        # 创建文档
        doc = Document()
        
        # 定义标题映射
        title_map = {
            'summary': '概要/Summary',
            'defect_description': '缺陷描述/DEFECT DESCRIPTION',
            'preconditions': '前置条件/Preconditions',
            'steps': '步骤/Steps',
            'actual_result': '实际结果/Actual result',
            'expected_result': '预期结果/Expected result',
            'log': '日志如下/Log as below',
            'associate_specification': '关联规范/ASSOCIATE SPECIFICATION',
            'test_plan_reference': '测试计划参考/TEST PLAN REFERENCE',
            'tools_and_platforms': '使用的工具和平台/TOOLS AND PLATFORMS USED',
            'user_impact': '用户影响/USER IMPACT',
            'reproducing_rate': '复现率/REPRODUCING RATE',
            'reference_mobile': '对于场测问题（FT PR），请列出参考机的表现/For FT PR,Please list reference mobile\'s behavior'
        }
        
        # 遍历所有字段
        for key, title in title_map.items():
            chinese_text = chinese_dict.get(key, '').strip()
            english_text = english_dict.get(key, '').strip()
            
            # 添加标题（加粗，后面加冒号）
            title_para = doc.add_paragraph()
            title_run = title_para.add_run(f"{title}:")
            title_run.bold = True
            title_run.font.size = Pt(12)
            
            # 添加内容
            if chinese_text:
                # 添加中文内容（字号比标题小两个字号，即10pt）
                chinese_para = doc.add_paragraph(chinese_text)
                chinese_para.paragraph_format.space_after = Pt(6)
                for run in chinese_para.runs:
                    run.font.size = Pt(10)
                
                # 添加英文翻译
                if english_text:
                    if key == 'summary':
                        # 概要：中文后紧跟英文，不换行
                        chinese_run = chinese_para.runs[0]
                        chinese_run.add_text(f" / {english_text}")
                    else:
                        # 其他字段：换行显示英文（字号10pt）
                        english_para = doc.add_paragraph(english_text)
                        english_para.paragraph_format.space_after = Pt(12)
                        for run in english_para.runs:
                            run.font.size = Pt(10)
            
            # 添加段落间距（在标题和内容之后）
            doc.add_paragraph()
        
        # 获取存储路径（和log的存储路径逻辑一致）
        storage_path = self.get_storage_path()
        
        # 确保目录存在
        if not os.path.exists(storage_path):
            os.makedirs(storage_path)
        
        # 保存文档
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"PR_Translation_{timestamp}.docx"
        file_path = os.path.join(storage_path, filename)
        doc.save(file_path)
        
        return file_path
    
    def get_storage_path(self):
        """获取存储路径，优先使用用户配置的路径"""
        # 从父窗口（PRTranslationDialog）获取主窗口的工具配置
        parent_dialog = self.parent()
        if parent_dialog and hasattr(parent_dialog, 'parent'):
            main_window = parent_dialog.parent()
            if main_window and hasattr(main_window, 'tool_config') and main_window.tool_config:
                storage_path = main_window.tool_config.get("storage_path", "")
                if storage_path:
                    return storage_path
        
        # 使用默认路径
        current_date = datetime.datetime.now().strftime("%Y%m%d")
        return f"c:\\log\\{current_date}"


class PRTranslationDialog(QDialog):
    """PR翻译对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.translation_worker = None
        self.setup_ui()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle(self.tr("PR翻译"))
        self.setModal(True)
        self.resize(800, 700)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 创建滚动内容容器
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(5, 5, 5, 5)
        scroll_layout.setSpacing(10)
        
        # 邮箱输入框
        email_container = QWidget()
        email_layout = QVBoxLayout(email_container)
        email_layout.setContentsMargins(0, 0, 0, 0)
        email_layout.setSpacing(4)
        
        email_title = QLabel(self.tr("邮箱（可选）"))
        email_title.setProperty("class", "section-title")
        email_layout.addWidget(email_title)
        
        email_card = QFrame()
        email_card.setObjectName("card")
        add_card_shadow(email_card)
        email_card_layout = QVBoxLayout(email_card)
        email_card_layout.setContentsMargins(10, 1, 10, 1)
        
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText(self.tr("输入邮箱地址（可选，用于提高翻译配额）"))
        email_card_layout.addWidget(self.email_edit)
        
        email_layout.addWidget(email_card)
        scroll_layout.addWidget(email_container)
        
        # 定义字段配置：字段名 -> (标题, 是否多行)
        fields_config = {
            'summary': (self.tr('概要/Summary'), False),
            'defect_description': (self.tr('缺陷描述/DEFECT DESCRIPTION'), False),
            'preconditions': (self.tr('前置条件/Preconditions'), False),
            'steps': (self.tr('步骤/Steps'), True),
            'actual_result': (self.tr('实际结果/Actual result'), True),
            'expected_result': (self.tr('预期结果/Expected result'), True),
            'log': (self.tr('日志如下/Log as below'), False),
            'associate_specification': (self.tr('关联规范/ASSOCIATE SPECIFICATION'), False),
            'test_plan_reference': (self.tr('测试计划参考/TEST PLAN REFERENCE'), False),
            'tools_and_platforms': (self.tr('使用的工具和平台/TOOLS AND PLATFORMS USED'), False),
            'user_impact': (self.tr('用户影响/USER IMPACT'), False),
            'reproducing_rate': (self.tr('复现率/REPRODUCING RATE'), False),
            'reference_mobile': (self.tr('对于场测问题（FT PR），请列出参考机的表现/For FT PR,Please list reference mobile\'s behavior'), False)
        }
        
        # 存储输入框引用
        self.input_fields = {}
        
        # 创建每个字段的输入区域
        for field_key, (field_title, is_multiline) in fields_config.items():
            field_container = QWidget()
            field_layout = QVBoxLayout(field_container)
            field_layout.setContentsMargins(0, 0, 0, 0)
            field_layout.setSpacing(4)
            
            # 标题
            title_label = QLabel(field_title)
            title_label.setProperty("class", "section-title")
            field_layout.addWidget(title_label)
            
            # 卡片容器
            field_card = QFrame()
            field_card.setObjectName("card")
            add_card_shadow(field_card)
            field_card_layout = QVBoxLayout(field_card)
            field_card_layout.setContentsMargins(10, 1, 10, 1)
            
            # 输入框
            if is_multiline:
                input_widget = QTextEdit()
                input_widget.setMaximumHeight(100)
            else:
                input_widget = QLineEdit()
            
            field_card_layout.addWidget(input_widget)
            field_layout.addWidget(field_card)
            scroll_layout.addWidget(field_container)
            
            # 保存引用
            self.input_fields[field_key] = input_widget
        
        # 设置滚动区域的内容
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.translate_btn = QPushButton(self.tr("确认翻译"))
        self.translate_btn.clicked.connect(self.on_translate)
        button_layout.addWidget(self.translate_btn)
        
        self.cancel_btn = QPushButton(self.tr("取消"))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(button_layout)
    
    def on_translate(self):
        """开始翻译"""
        # 检查python-docx是否可用
        if not DOCX_AVAILABLE:
            QMessageBox.warning(
                self, 
                self.tr("缺少依赖"), 
                self.tr("需要安装python-docx库才能生成Word文档。\n请运行: pip install python-docx")
            )
            return
        
        # 收集所有输入数据
        data_dict = {}
        for field_key, input_widget in self.input_fields.items():
            if isinstance(input_widget, QTextEdit):
                text = input_widget.toPlainText().strip()
            else:
                text = input_widget.text().strip()
            data_dict[field_key] = text
        
        # 检查是否有任何内容需要翻译
        has_content = any(data_dict.values())
        if not has_content:
            QMessageBox.warning(self, self.tr("输入错误"), self.tr("请至少输入一个字段的内容"))
            return
        
        # 获取邮箱
        email = self.email_edit.text().strip() if self.email_edit.text().strip() else None
        
        # 禁用按钮
        self.translate_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        
        # 创建进度对话框
        self.progress_dialog = QMessageBox(self)
        self.progress_dialog.setWindowTitle(self.tr("翻译中"))
        self.progress_dialog.setText(self.tr("正在翻译，请稍候..."))
        self.progress_dialog.setStandardButtons(QMessageBox.NoButton)
        self.progress_dialog.show()
        
        # 创建工作线程
        self.translation_worker = TranslationWorker(data_dict, email, self)
        self.translation_worker.finished.connect(self.on_translation_finished)
        self.translation_worker.error.connect(self.on_translation_error)
        self.translation_worker.progress.connect(self.on_translation_progress)
        self.translation_worker.start()
    
    def on_translation_progress(self, message):
        """翻译进度更新"""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.setText(message)
    
    def on_translation_finished(self, file_path):
        """翻译完成"""
        # 关闭进度对话框
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
        
        # 恢复按钮
        self.translate_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        
        # 打开Word文档
        try:
            os.startfile(file_path)
            QMessageBox.information(
                self, 
                self.tr("翻译完成"), 
                self.tr(f"翻译完成！Word文档已生成并打开。\n文件路径: {file_path}")
            )
            # 不自动关闭对话框，让用户可以继续使用
        except Exception as e:
            QMessageBox.critical(
                self, 
                self.tr("打开失败"), 
                self.tr(f"翻译完成，但打开文档失败: {str(e)}\n文件路径: {file_path}")
            )
    
    def on_translation_error(self, error_msg):
        """翻译错误"""
        # 关闭进度对话框
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
        
        # 恢复按钮
        self.translate_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        
        QMessageBox.critical(self, self.tr("翻译失败"), self.tr(f"翻译过程中发生错误: {error_msg}"))

