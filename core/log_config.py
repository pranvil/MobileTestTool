#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置管理模块
用于管理debug日志的配置选项
"""

import os
import json
import sys


class LogConfig:
    """日志配置管理类"""
    
    # 日志级别映射
    LEVELS = {
        'DEBUG': 0,
        'INFO': 1,
        'WARNING': 2,
        'ERROR': 3,
        'EXCEPTION': 3  # EXCEPTION级别等同于ERROR
    }
    
    # 默认配置
    DEFAULT_CONFIG = {
        'enabled': True,                    # 是否启用日志
        'log_level': 'DEBUG',               # 最低日志级别
        'max_file_size_mb': 10,            # 单个日志文件最大大小(MB)
        'max_files': 5,                    # 保留的最大日志文件数
        'retention_days': 7,               # 日志保留天数
        'buffer_size': 100,                 # 日志缓冲队列大小
        'flush_interval': 1.0,              # 日志刷新间隔(秒)
        'enable_rotation': True,            # 是否启用日志轮转
        'rotation_by_size': True,          # 按大小轮转
        'rotation_by_date': True,           # 按日期轮转
        'include_module': True,             # 包含模块名
        'include_function': True,          # 包含函数名
        'include_line': True                # 包含行号
    }
    
    _instance = None
    _config = None
    _config_file = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """初始化配置"""
        try:
            # 获取配置文件路径
            if getattr(sys, 'frozen', False):
                # 打包环境：使用exe所在目录
                app_dir = os.path.dirname(os.path.abspath(sys.executable))
            else:
                # 开发环境：使用项目根目录
                app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            log_dir = os.path.join(app_dir, 'logs')
            os.makedirs(log_dir, exist_ok=True)
            
            self._config_file = os.path.join(log_dir, 'debug_log_config.json')
            
            # 加载配置
            self._load_config()
            
        except Exception as e:
            # 如果加载失败，使用默认配置
            self._config = self.DEFAULT_CONFIG.copy()
    
    def _load_config(self):
        """从文件加载配置"""
        if os.path.exists(self._config_file):
            try:
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                
                # 合并默认配置和加载的配置
                self._config = self.DEFAULT_CONFIG.copy()
                self._config.update(loaded_config)
                
                # 验证配置值
                self._validate_config()
                
            except Exception as e:
                # 如果加载失败，使用默认配置
                self._config = self.DEFAULT_CONFIG.copy()
                self._save_config()  # 保存默认配置到文件
        else:
            # 文件不存在，使用默认配置并保存
            self._config = self.DEFAULT_CONFIG.copy()
            self._save_config()
    
    def _validate_config(self):
        """验证配置值的有效性"""
        # 验证日志级别
        if self._config['log_level'] not in self.LEVELS:
            self._config['log_level'] = self.DEFAULT_CONFIG['log_level']
        
        # 验证数值范围
        if self._config['max_file_size_mb'] < 1:
            self._config['max_file_size_mb'] = 1
        if self._config['max_file_size_mb'] > 1000:
            self._config['max_file_size_mb'] = 1000
        
        if self._config['max_files'] < 1:
            self._config['max_files'] = 1
        if self._config['max_files'] > 100:
            self._config['max_files'] = 100
        
        if self._config['retention_days'] < 1:
            self._config['retention_days'] = 1
        if self._config['retention_days'] > 365:
            self._config['retention_days'] = 365
        
        if self._config['buffer_size'] < 1:
            self._config['buffer_size'] = 1
        if self._config['buffer_size'] > 10000:
            self._config['buffer_size'] = 10000
        
        if self._config['flush_interval'] < 0.1:
            self._config['flush_interval'] = 0.1
        if self._config['flush_interval'] > 60:
            self._config['flush_interval'] = 60
    
    def _save_config(self):
        """保存配置到文件"""
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # 静默处理保存错误
    
    def get(self, key, default=None):
        """获取配置值"""
        return self._config.get(key, default)
    
    def set(self, key, value):
        """设置配置值"""
        if key in self._config:
            self._config[key] = value
            self._validate_config()
            self._save_config()
    
    def update(self, config_dict):
        """批量更新配置"""
        self._config.update(config_dict)
        self._validate_config()
        self._save_config()
    
    def get_all(self):
        """获取所有配置"""
        return self._config.copy()
    
    def should_log(self, level):
        """判断指定级别的日志是否应该记录"""
        if not self._config['enabled']:
            return False
        
        current_level = self.LEVELS.get(self._config['log_level'], 1)
        log_level = self.LEVELS.get(level, 1)
        
        return log_level >= current_level
    
    def get_log_level_value(self):
        """获取当前日志级别的数值"""
        return self.LEVELS.get(self._config['log_level'], 1)
    
    def get_config_file_path(self):
        """获取配置文件路径"""
        return self._config_file


# 创建全局配置实例
config = LogConfig()

