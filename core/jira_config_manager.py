#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JIRA配置管理器包装类
提供与Jira_tool原有ConfigManager兼容的接口
底层使用tool_config.json存储配置
"""

import os
import json
from core.debug_logger import logger


class ConfigManager:
    """配置管理器 - 兼容Jira_tool原有接口"""
    
    def __init__(self):
        self.config_file = os.path.expanduser("~/.netui/tool_config.json")
        self._config = None
        self._load_config()
    
    def _load_config(self):
        """从tool_config.json加载配置"""
        defaults = {
            'jira_url': 'https://jira.tcl.com',
            'api_token': '',
            'confluence_url': 'https://confluence.tclking.com/',
            'confluence_api_token': '',
            'confluence_default_space': 'USVAL'
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    stored_config = json.load(f)
                    if isinstance(stored_config, dict):
                        # 从tool_config.json读取JIRA相关配置
                        defaults['jira_url'] = stored_config.get('jira_url', defaults['jira_url'])
                        defaults['api_token'] = stored_config.get('jira_api_token', defaults['api_token'])
                        defaults['confluence_url'] = stored_config.get('confluence_url', defaults['confluence_url'])
                        defaults['confluence_api_token'] = stored_config.get('confluence_api_token', defaults['confluence_api_token'])
                        defaults['confluence_default_space'] = stored_config.get('confluence_default_space', defaults['confluence_default_space'])
        except Exception as e:
            logger.error(f"读取JIRA配置失败: {e}")
        
        self._config = defaults
    
    def save_config(self):
        """保存配置到tool_config.json"""
        try:
            # 读取现有配置
            config = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            # 更新JIRA相关配置
            config['jira_url'] = self._config.get('jira_url', 'https://jira.tcl.com')
            config['jira_api_token'] = self._config.get('api_token', '')
            config['confluence_url'] = self._config.get('confluence_url', 'https://confluence.tclking.com/')
            config['confluence_api_token'] = self._config.get('confluence_api_token', '')
            config['confluence_default_space'] = self._config.get('confluence_default_space', 'USVAL')
            
            # 保存配置
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            logger.info("JIRA配置已保存到tool_config.json")
        except Exception as e:
            logger.error(f"保存JIRA配置失败: {e}")
            raise
    
    def get_token(self) -> str:
        """获取API Token"""
        return self._config.get('api_token', '')
    
    def get_jira_url(self) -> str:
        """获取JIRA URL"""
        return self._config.get('jira_url', 'https://jira.tcl.com')
    
    def set_token(self, token: str):
        """设置API Token"""
        self._config['api_token'] = token
    
    def set_jira_url(self, url: str):
        """设置JIRA URL"""
        self._config['jira_url'] = url
    
    def get_confluence_url(self) -> str:
        """获取Confluence URL"""
        return self._config.get('confluence_url', 'https://confluence.tclking.com/')
    
    def get_confluence_token(self) -> str:
        """获取Confluence API Token"""
        return self._config.get('confluence_api_token', '')
    
    def set_confluence_url(self, url: str):
        """设置Confluence URL"""
        self._config['confluence_url'] = url
    
    def set_confluence_token(self, token: str):
        """设置Confluence API Token"""
        self._config['confluence_api_token'] = token
    
    def get_default_confluence_space(self) -> str:
        """获取默认Confluence空间Key"""
        return self._config.get('confluence_default_space', 'USVAL')
    
    def set_default_confluence_space(self, space_key: str):
        """设置默认Confluence空间Key"""
        self._config['confluence_default_space'] = space_key
    
    def load_config(self) -> dict:
        """加载配置并返回字典"""
        self._load_config()
        return {
            'jira_url': self.get_jira_url(),
            'api_token': self.get_token()
        }


# 创建全局实例
_config_manager = ConfigManager()


def load_config() -> dict:
    """加载配置"""
    return _config_manager.load_config()


def save_config():
    """保存配置"""
    _config_manager.save_config()


def get_token() -> str:
    """获取API Token"""
    return _config_manager.get_token()


def get_jira_url() -> str:
    """获取JIRA URL"""
    return _config_manager.get_jira_url()


def set_token(token: str):
    """设置API Token"""
    _config_manager.set_token(token)
    _config_manager.save_config()


def set_jira_url(url: str):
    """设置JIRA URL"""
    _config_manager.set_jira_url(url)
    _config_manager.save_config()


def get_confluence_url() -> str:
    """获取Confluence URL"""
    return _config_manager.get_confluence_url()


def get_confluence_token() -> str:
    """获取Confluence API Token"""
    return _config_manager.get_confluence_token()


def set_confluence_url(url: str):
    """设置Confluence URL"""
    _config_manager.set_confluence_url(url)
    _config_manager.save_config()


def set_confluence_token(token: str):
    """设置Confluence API Token"""
    _config_manager.set_confluence_token(token)
    _config_manager.save_config()


def get_default_confluence_space() -> str:
    """获取默认Confluence空间Key"""
    return _config_manager.get_default_confluence_space()


def set_default_confluence_space(space_key: str):
    """设置默认Confluence空间Key"""
    _config_manager.set_default_confluence_space(space_key)
    _config_manager.save_config()
