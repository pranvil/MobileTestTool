"""
通用异常类
"""


class JiraAPIError(Exception):
    """JIRA API 调用异常"""
    def __init__(self, message: str, status_code: int = None, response_text: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class ConfigError(Exception):
    """配置文件相关异常"""
    pass


class ValidationError(Exception):
    """数据校验异常"""
    def __init__(self, message: str, errors: list = None):
        super().__init__(message)
        self.errors = errors or []


class FileError(Exception):
    """文件操作异常"""
    pass


class ConfluenceAPIError(Exception):
    """Confluence API 调用异常"""
    def __init__(self, message: str, status_code: int = None, response_text: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
