"""
路径管理模块
统一管理应用的所有路径
"""
from pathlib import Path
import os


class PathManager:
    """路径管理器"""
    
    def __init__(self):
        # 获取项目根目录（当前文件所在目录的父目录）
        self.base_dir = Path(__file__).parent.parent.resolve()
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保所有必要的目录存在"""
        directories = [
            self.base_dir / "config",
            self.base_dir / "output",
            self.base_dir / "output" / "logs",
            self.base_dir / "output" / "comments",
            self.base_dir / "output" / "create_progress_logs",
            self.base_dir / "output" / "error_reports",
            self.base_dir / "output" / "cache",
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_config_path(self) -> Path:
        """获取配置文件路径"""
        return self.base_dir / "config" / "config.ini"
    
    def get_log_path(self) -> Path:
        """获取日志文件路径"""
        return self.base_dir / "output" / "logs" / "app.log"
    
    def get_comments_output_path(self) -> Path:
        """获取评论HTML输出目录"""
        return self.base_dir / "output" / "comments"
    
    def get_progress_logs_path(self) -> Path:
        """获取创建进度日志目录"""
        return self.base_dir / "output" / "create_progress_logs"
    
    def get_error_reports_path(self) -> Path:
        """获取错误报告目录"""
        return self.base_dir / "output" / "error_reports"

    def get_cache_path(self) -> Path:
        """获取缓存目录"""
        return self.base_dir / "output" / "cache"
    
    def get_base_dir(self) -> Path:
        """获取项目根目录"""
        return self.base_dir


# 创建全局实例
_path_manager = PathManager()


def get_config_path() -> Path:
    """获取配置文件路径"""
    return _path_manager.get_config_path()


def get_log_path() -> Path:
    """获取日志文件路径"""
    return _path_manager.get_log_path()


def get_comments_output_path() -> Path:
    """获取评论HTML输出目录"""
    return _path_manager.get_comments_output_path()


def get_progress_logs_path() -> Path:
    """获取创建进度日志目录"""
    return _path_manager.get_progress_logs_path()


def get_error_reports_path() -> Path:
    """获取错误报告目录"""
    return _path_manager.get_error_reports_path()


def get_cache_path() -> Path:
    """获取缓存目录"""
    return _path_manager.get_cache_path()


def get_base_dir() -> Path:
    """获取项目根目录"""
    return _path_manager.get_base_dir()

