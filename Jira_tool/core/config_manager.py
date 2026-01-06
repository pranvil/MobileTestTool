"""
配置文件管理模块
使用INI格式存储配置
"""
import configparser
from pathlib import Path
from Jira_tool.core.paths import get_config_path
from Jira_tool.core.exceptions import ConfigError
from Jira_tool.core.logger import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.config_path = get_config_path()
        self.config = configparser.ConfigParser()
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        if self.config_path.exists():
            try:
                self.config.read(self.config_path, encoding='utf-8')
            except Exception as e:
                logger.error(f"读取配置文件失败: {e}")
                raise ConfigError(f"读取配置文件失败: {e}")
        else:
            # 如果配置文件不存在，创建默认配置
            self._create_default_config()
    
    def _create_default_config(self):
        """创建默认配置"""
        self.config['JIRA'] = {
            'jira_url': 'https://jira.tcl.com',
            'api_token': ''
        }
        self.config['CONFLUENCE'] = {
            'confluence_url': 'https://confluence.tclking.com/',
            'api_token': ''
        }
        self.save_config()
        logger.info("创建默认配置文件")
    
    def save_config(self):
        """保存配置到文件"""
        try:
            # 确保配置目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.config.write(f)
            logger.info("配置文件已保存")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            raise ConfigError(f"保存配置文件失败: {e}")
    
    def load_config(self) -> dict:
        """加载配置并返回字典"""
        self._load_config()
        return {
            'jira_url': self.get_jira_url(),
            'api_token': self.get_token()
        }
    
    def get_token(self) -> str:
        """获取API Token"""
        return self.config.get('JIRA', 'api_token', fallback='')
    
    def get_jira_url(self) -> str:
        """获取JIRA URL"""
        return self.config.get('JIRA', 'jira_url', fallback='https://jira.tcl.com')
    
    def set_token(self, token: str):
        """设置API Token"""
        if 'JIRA' not in self.config:
            self.config['JIRA'] = {}
        self.config['JIRA']['api_token'] = token
    
    def set_jira_url(self, url: str):
        """设置JIRA URL"""
        if 'JIRA' not in self.config:
            self.config['JIRA'] = {}
        self.config['JIRA']['jira_url'] = url
    
    def get_confluence_url(self) -> str:
        """获取Confluence URL"""
        return self.config.get('CONFLUENCE', 'confluence_url', fallback='https://confluence.tclking.com/')
    
    def get_confluence_token(self) -> str:
        """获取Confluence API Token"""
        return self.config.get('CONFLUENCE', 'api_token', fallback='')
    
    def set_confluence_url(self, url: str):
        """设置Confluence URL"""
        if 'CONFLUENCE' not in self.config:
            self.config['CONFLUENCE'] = {}
        self.config['CONFLUENCE']['confluence_url'] = url
    
    def set_confluence_token(self, token: str):
        """设置Confluence API Token"""
        if 'CONFLUENCE' not in self.config:
            self.config['CONFLUENCE'] = {}
        self.config['CONFLUENCE']['api_token'] = token
    
    def get_default_confluence_space(self) -> str:
        """获取默认Confluence空间Key"""
        return self.config.get('CONFLUENCE', 'default_space', fallback='USVAL')
    
    def set_default_confluence_space(self, space_key: str):
        """设置默认Confluence空间Key"""
        if 'CONFLUENCE' not in self.config:
            self.config['CONFLUENCE'] = {}
        self.config['CONFLUENCE']['default_space'] = space_key


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

