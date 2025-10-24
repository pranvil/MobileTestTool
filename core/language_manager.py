#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语言管理器
支持中英文切换
"""

import json
import os
import sys
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal
from core.debug_logger import logger

# 检测是否在PyInstaller打包环境中运行
def is_pyinstaller():
    """检测是否在PyInstaller打包环境中运行"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def get_resource_path(relative_path):
    """获取资源文件的正确路径，兼容exe环境"""
    if is_pyinstaller():
        # 在exe环境中，使用临时目录
        base_path = sys._MEIPASS
    else:
        # 在Python环境中，使用项目根目录
        base_path = os.path.dirname(os.path.dirname(__file__))
    
    return os.path.join(base_path, relative_path)


class LanguageManager(QObject):
    """语言管理器 - 单例模式"""
    
    # 语言改变信号
    language_changed = pyqtSignal(str)  # 发送新语言代码
    
    _instance = None
    _initialized = False
    
    def __new__(cls, parent=None):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super(LanguageManager, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls, parent=None):
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls(parent)
        return cls._instance
    
    def __init__(self, parent=None):
        # 避免重复初始化
        if self._initialized:
            return
            
        super().__init__(parent)
        self.current_lang = 'zh'  # 默认中文
        self.translations = {}
        self.missing_translations = set()
        
        # 加载翻译文件
        self._load_translations()
        
        # 加载用户上次选择的语言
        self._load_saved_language()
        
        # 标记为已初始化
        self._initialized = True
    
    def _load_translations(self):
        """加载翻译文件"""
        # 如果已经加载过，直接返回
        if hasattr(self, '_translations_loaded') and self._translations_loaded:
            return
            
        try:
            translation_file = get_resource_path('translations.json')
            logger.info(f"尝试加载翻译文件: {translation_file}")
            
            if os.path.exists(translation_file):
                with open(translation_file, 'r', encoding='utf-8') as f:
                    self.translations = json.load(f)
                logger.info("翻译文件加载成功")
            else:
                logger.warning(f"翻译文件不存在: {translation_file}")
                # 创建空的翻译字典
                self.translations = {'zh': {}, 'en': {}}
            
            # 标记为已加载
            self._translations_loaded = True
        except Exception as e:
            logger.error(f"加载翻译文件失败: {str(e)}")
            self.translations = {'zh': {}, 'en': {}}
            self._translations_loaded = True
    
    def _load_saved_language(self):
        """加载用户保存的语言偏好"""
        # 如果已经加载过，直接返回
        if hasattr(self, '_language_loaded') and self._language_loaded:
            return
            
        try:
            # 使用与保存相同的路径逻辑
            if is_pyinstaller():
                # 在exe环境中，从用户目录加载
                user_config_dir = os.path.join(os.path.expanduser('~'), '.MobileTestTool')
                config_file = os.path.join(user_config_dir, 'language.conf')
            else:
                # 在Python环境中，从项目目录加载
                config_dir = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    'config'
                )
                config_file = os.path.join(config_dir, 'language.conf')
            
            logger.info(f"尝试加载语言配置: {config_file}")
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    lang = f.read().strip()
                    if lang in ['zh', 'en']:
                        self.current_lang = lang
                        logger.info(f"加载保存的语言设置: {lang}")
            else:
                logger.info(f"语言配置文件不存在，使用默认语言: {self.current_lang}")
            
            # 标记为已加载
            self._language_loaded = True
        except Exception as e:
            logger.error(f"加载保存的语言设置失败: {str(e)}")
            self._language_loaded = True
    
    def _save_language_preference(self, lang):
        """保存语言偏好"""
        try:
            if is_pyinstaller():
                # 在exe环境中，保存到用户目录
                user_config_dir = os.path.join(os.path.expanduser('~'), '.MobileTestTool')
                os.makedirs(user_config_dir, exist_ok=True)
                config_file = os.path.join(user_config_dir, 'language.conf')
            else:
                # 在Python环境中，保存到项目目录
                config_dir = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    'config'
                )
                os.makedirs(config_dir, exist_ok=True)
                config_file = os.path.join(config_dir, 'language.conf')
            
            logger.info(f"尝试保存语言配置: {config_file}, 语言: {lang}")
            
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(lang)
            
            logger.info(f"语言偏好保存成功: {config_file}")
        except Exception as e:
            logger.error(f"保存语言设置失败: {str(e)}")
    
    def set_language(self, lang):
        """
        设置当前语言
        
        Args:
            lang: 'zh'
        """
        if lang not in ['zh', 'en']:
            logger.warning(f"不支持的语言代码: {lang}")
            return
        
        if lang == self.current_lang:
            return
        
        self.current_lang = lang
        # 语言切换日志由UI界面处理，这里不重复输出
        
        # 保存偏好
        self._save_language_preference(lang)
        
        # 发送语言改变信号
        self.language_changed.emit(lang)
    
    def get_current_language(self):
        """获取当前语言"""
        return self.current_lang
    
    def tr(self, text):
        """
        翻译文本
        
        Args:
            text: 要翻译的文本（中文）
            
        Returns:
            翻译后的文本
        """
        if not text:
            return text
        
        # 获取当前语言的翻译
        if self.current_lang not in self.translations:
            logger.warning(f"当前语言 '{self.current_lang}' 不在翻译文件中")
            return text
        
        result = self.translations[self.current_lang].get(text)
        
        if result is None:
            # 记录缺失的翻译
            if text not in self.missing_translations:
                self.missing_translations.add(text)
                self._log_missing_translation(text)
            
            # 不再在debug日志中输出翻译失败信息，减少日志噪音
            # logger.warning(f"翻译失败: '{text}' (语言: {self.current_lang}) -> 返回原文")
            # 如果是英文环境且找不到翻译，添加标记
            if self.current_lang == 'en':
                return f"[?] {text}"
            else:
                return text
        
        # 翻译成功时不记录日志，减少日志噪音
        return result
    
    def _log_missing_translation(self, text):
        """记录缺失的翻译"""
        try:
            # 创建专门的翻译失败日志文件
            log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            
            # 翻译失败日志文件
            translation_log_file = os.path.join(log_dir, 'translation_failures.txt')
            
            # 检查是否已经记录过这个翻译
            if os.path.exists(translation_log_file):
                try:
                    with open(translation_log_file, 'r', encoding='utf-8') as f:
                        existing_translations = f.read().splitlines()
                        if text in existing_translations:
                            return  # 已经记录过，不重复记录
                except UnicodeDecodeError:
                    # 如果UTF-8解码失败，尝试其他编码
                    try:
                        with open(translation_log_file, 'r', encoding='gbk') as f:
                            existing_translations = f.read().splitlines()
                            if text in existing_translations:
                                return
                    except UnicodeDecodeError:
                        # 如果还是失败，忽略检查，直接追加
                        pass
            
            # 记录到翻译失败日志文件
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(translation_log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {text}\n")
            
            # 同时记录到missing_translations.txt（保持向后兼容）
            missing_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'missing_translations.txt')
            with open(missing_file, 'a', encoding='utf-8') as f:
                f.write(f"{text}\n")
            
            # 不再在debug日志中输出翻译失败信息，减少日志噪音
            # logger.warning(f"发现缺失翻译: '{text}' (已记录到文件)")
        except Exception as e:
            logger.error(f"记录缺失翻译失败: {str(e)}")
    
    def get_missing_translations(self):
        """获取所有缺失的翻译"""
        return list(self.missing_translations)
    
    def reload_translations(self):
        """重新加载翻译文件"""
        self._load_translations()
        logger.info("翻译文件已重新加载")
    
    def debug_translation_status(self):
        """调试翻译状态"""
        logger.info("=== 翻译系统调试信息 ===")
        logger.info("当前语言:")
        logger.info("可用语言:")
        logger.info(f"{self.tr('中文翻译数量:')} {len(self.translations.get('zh', {}))}")
        logger.info(f"{self.tr('英文翻译数量:')} {len(self.translations.get('en', {}))}")
        logger.info("缺失翻译数量:")
        
        # 测试几个关键翻译
        test_keys = ['测试键1', '测试键2', '测试键3', '测试键4', '测试键5', '测试键6']
        logger.info("=== 关键翻译测试 ===")
        for key in test_keys:
            result = self.tr(key)
            logger.info(f"'{key}' -> '{result}'")
        
        logger.info("=== 调试信息结束 ===")

