#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Log关键字管理器
支持用户自定义log过滤关键字的保存、加载、导入导出
"""

import os
import json
import datetime
from PyQt5.QtCore import QObject, pyqtSignal
from core.debug_logger import logger


class LogKeywordManager(QObject):
    """Log关键字配置管理器"""
    
    # 信号定义
    keywords_updated = pyqtSignal()  # 关键字配置更新
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_file = os.path.expanduser("~/.netui/log_keywords.json")
        self.keywords = []
        # 从父窗口获取语言管理器
        if parent and hasattr(parent, 'lang_manager'):
            self.lang_manager = parent.lang_manager
        else:
            # 如果没有父窗口或语言管理器，创建一个默认的
            from core.language_manager import LanguageManager
            self.lang_manager = LanguageManager()
        self.load_keywords()
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def load_keywords(self):
        """加载关键字配置"""
        try:
            if os.path.exists(self.config_file):
                # 使用 utf-8-sig 编码来正确处理BOM
                with open(self.config_file, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    self.keywords = data.get('log_keywords', [])
                    logger.info(f"{self.lang_manager.tr('成功加载')} {len(self.keywords)} {self.lang_manager.tr('个log关键字')}")
            else:
                # 创建默认配置
                self.keywords = self._create_default_keywords()
                self.save_keywords()
                logger.info(self.lang_manager.tr("创建默认log关键字配置"))
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('加载log关键字配置失败:')} {e}")
            # 如果配置文件损坏，创建默认配置
            logger.info(self.lang_manager.tr("尝试创建默认配置..."))
            self.keywords = self._create_default_keywords()
            self.save_keywords()
    
    def save_keywords(self):
        """保存关键字配置"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            data = {
                'log_keywords': self.keywords,
                'version': '1.0'
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"{self.lang_manager.tr('成功保存')} {len(self.keywords)} {self.lang_manager.tr('个log关键字配置')}")
            self.keywords_updated.emit()
            return True
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('保存log关键字配置失败:')} {e}")
            return False
    
    def _create_default_keywords(self):
        """创建默认关键字示例"""
        return [
            {
                'id': 'default_001',
                'name': self.lang_manager.tr('Error日志'),
                'keyword': 'Error|Exception|FATAL',
                'description': self.lang_manager.tr('匹配Error、Exception和FATAL关键字')
            },
            {
                'id': 'default_002',
                'name': self.lang_manager.tr('Warning日志'),
                'keyword': 'Warning|WARN',
                'description': self.lang_manager.tr('匹配Warning和WARN关键字')
            },
            {
                'id': 'default_003',
                'name': self.lang_manager.tr('网络相关'),
                'keyword': 'Network|Connection|Socket|HTTP',
                'description': self.lang_manager.tr('匹配网络相关日志')
            }
        ]
    
    def get_all_keywords(self):
        """获取所有关键字"""
        return self.keywords
    
    def get_keyword_by_id(self, keyword_id):
        """根据ID获取关键字"""
        for kw in self.keywords:
            if kw.get('id') == keyword_id:
                return kw
        return None
    
    def add_keyword(self, keyword_data):
        """添加关键字"""
        try:
            # 生成ID
            if 'id' not in keyword_data:
                keyword_data['id'] = f"custom_{len(self.keywords) + 1:03d}"
            
            # 验证必填字段
            if not keyword_data.get('name') or not keyword_data.get('keyword'):
                logger.error(self.lang_manager.tr("关键字名称和关键字内容不能为空"))
                return False
            
            self.keywords.append(keyword_data)
            return self.save_keywords()
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('添加关键字失败:')} {e}")
            return False
    
    def update_keyword(self, keyword_id, keyword_data):
        """更新关键字"""
        try:
            for i, kw in enumerate(self.keywords):
                if kw['id'] == keyword_id:
                    # 保留ID
                    keyword_data['id'] = keyword_id
                    self.keywords[i] = keyword_data
                    return self.save_keywords()
            
            logger.error(f"{self.lang_manager.tr('未找到ID为')} {keyword_id} {self.lang_manager.tr('的关键字')}")
            return False
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('更新关键字失败:')} {e}")
            return False
    
    def delete_keyword(self, keyword_id):
        """删除关键字"""
        try:
            self.keywords = [kw for kw in self.keywords if kw['id'] != keyword_id]
            return self.save_keywords()
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('删除关键字失败:')} {e}")
            return False
    
    def import_keywords(self, file_path):
        """从文件导入关键字配置"""
        try:
            # 尝试不同的编码方式
            encodings = ['utf-8-sig', 'utf-8', 'gbk']
            data = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        data = json.load(f)
                        break
                except UnicodeDecodeError:
                    continue
            
            if data is None:
                logger.error(f"{self.lang_manager.tr('无法读取文件')} {file_path}，{self.lang_manager.tr('尝试了多种编码')}")
                return False
            
            imported_keywords = data.get('log_keywords', [])
            
            # 合并关键字（避免ID冲突）
            existing_ids = {kw['id'] for kw in self.keywords}
            for kw in imported_keywords:
                if kw['id'] in existing_ids:
                    # 重新生成ID
                    kw['id'] = f"imported_{len(self.keywords) + 1:03d}"
                self.keywords.append(kw)
            
            return self.save_keywords()
                
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('导入关键字配置失败:')} {e}")
            return False
    
    def export_keywords(self, file_path):
        """导出关键字配置到文件"""
        try:
            data = {
                'log_keywords': self.keywords,
                'version': '1.0',
                'export_time': datetime.datetime.now().isoformat(),
                'export_note': self.lang_manager.tr('Log关键字配置导出')
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"{self.lang_manager.tr('成功导出关键字配置到:')} {file_path}")
            return True
            
        except Exception as e:
            logger.exception(f"{self.lang_manager.tr('导出关键字配置失败:')} {e}")
            return False
    
    def get_config_info(self):
        """获取配置信息"""
        return {
            'keyword_count': len(self.keywords),
            'config_file': self.config_file,
            'keywords': [
                {
                    'name': kw.get('name', ''),
                    'keyword': kw.get('keyword', ''),
                    'description': kw.get('description', '')
                }
                for kw in self.keywords
            ]
        }

