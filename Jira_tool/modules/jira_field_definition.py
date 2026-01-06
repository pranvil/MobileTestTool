"""
JIRA字段定义模块
提供结构化的字段定义类和便捷的查询方法
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from Jira_tool.jira_client import get_fields
from Jira_tool.core.exceptions import JiraAPIError
from core.debug_logger import logger


@dataclass
class JiraFieldDefinition:
    """
    JIRA字段定义数据类
    封装单个字段的所有信息
    """
    field_id: str
    name: str
    field_type: str  # schema.type
    custom_type: str = ""  # schema.custom（如果是自定义字段）
    required: bool = False
    options: List[Any] = field(default_factory=list)  # allowedValues（对于选择类型字段）
    default_value: Any = None  # defaultValue
    schema: Dict[str, Any] = field(default_factory=dict)  # 完整的schema信息
    raw_data: Dict[str, Any] = field(default_factory=dict)  # 原始字段数据
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"JiraFieldDefinition(id={self.field_id}, name={self.name}, type={self.field_type}, required={self.required})"
    
    def __repr__(self) -> str:
        """对象表示"""
        return self.__str__()


class JiraIssueTypeFields:
    """
    JIRA Issue类型字段管理器
    管理某个项目下某个Issue类型的所有字段定义
    """
    
    def __init__(self, project_key: str, issue_type: str, fields_data: Dict[str, Any]):
        """
        初始化字段管理器
        
        Args:
            project_key: 项目Key
            issue_type: Issue类型名称
            fields_data: JIRA API返回的字段定义字典（field_id -> field_info）
        """
        self.project_key = project_key
        self.issue_type = issue_type
        self._fields: Dict[str, JiraFieldDefinition] = {}
        self._name_to_id: Dict[str, str] = {}  # 字段名到字段ID的映射（可能有多个同名字段，存储第一个）
        self._required_fields: List[str] = []  # 必填字段ID列表
        
        # 解析字段数据
        self._parse_fields(fields_data)
    
    def _parse_fields(self, fields_data: Dict[str, Any]) -> None:
        """
        解析字段数据，构建字段定义对象
        
        Args:
            fields_data: JIRA API返回的字段定义字典
        """
        for field_id, field_info in fields_data.items():
            try:
                # 提取字段信息
                name = field_info.get('name', '')
                schema = field_info.get('schema', {})
                field_type = schema.get('type', 'unknown')
                custom_type = schema.get('custom', '')
                required = field_info.get('required', False)
                allowed_values = field_info.get('allowedValues', [])
                default_value = field_info.get('defaultValue')
                
                # 创建字段定义对象
                field_def = JiraFieldDefinition(
                    field_id=field_id,
                    name=name,
                    field_type=field_type,
                    custom_type=custom_type,
                    required=required,
                    options=allowed_values if isinstance(allowed_values, list) else [],
                    default_value=default_value,
                    schema=schema,
                    raw_data=field_info
                )
                
                # 存储字段定义
                self._fields[field_id] = field_def
                
                # 建立名称到ID的映射（如果有名称且尚未映射）
                if name and name not in self._name_to_id:
                    self._name_to_id[name] = field_id
                
                # 记录必填字段
                if required:
                    self._required_fields.append(field_id)
            
            except Exception as e:
                logger.warning(f"解析字段 {field_id} 失败: {e}")
                continue
        
        logger.debug(f"解析完成: project={self.project_key}, issue_type={self.issue_type}, "
                    f"总字段数={len(self._fields)}, 必填字段数={len(self._required_fields)}")
    
    def get_all_fields(self) -> List[JiraFieldDefinition]:
        """
        获取所有字段列表
        
        Returns:
            字段定义对象列表
        """
        return list(self._fields.values())
    
    def get_field_by_id(self, field_id: str) -> Optional[JiraFieldDefinition]:
        """
        根据字段ID获取字段信息
        
        Args:
            field_id: 字段ID
        
        Returns:
            字段定义对象，如果不存在则返回None
        """
        return self._fields.get(field_id)
    
    def get_field_by_name(self, field_name: str) -> Optional[JiraFieldDefinition]:
        """
        根据字段名查找字段ID和信息
        
        Args:
            field_name: 字段名称（精确匹配）
        
        Returns:
            字段定义对象，如果不存在则返回None
        """
        field_id = self._name_to_id.get(field_name)
        if field_id:
            return self._fields.get(field_id)
        return None
    
    def get_required_fields(self) -> List[JiraFieldDefinition]:
        """
        获取所有必填字段
        
        Returns:
            必填字段定义对象列表
        """
        return [self._fields[field_id] for field_id in self._required_fields if field_id in self._fields]
    
    def get_field_ids(self) -> List[str]:
        """
        获取所有字段ID列表
        
        Returns:
            字段ID列表
        """
        return list(self._fields.keys())
    
    def find_fields_by_keyword(self, keyword: str, case_sensitive: bool = False) -> List[JiraFieldDefinition]:
        """
        根据关键字模糊查找字段（在字段名中搜索）
        
        Args:
            keyword: 搜索关键字
            case_sensitive: 是否区分大小写，默认为False
        
        Returns:
            匹配的字段定义对象列表
        """
        matches = []
        if case_sensitive:
            search_keyword = keyword
        else:
            search_keyword = keyword.lower()
        
        for field_def in self._fields.values():
            if case_sensitive:
                field_name = field_def.name
            else:
                field_name = field_def.name.lower()
            
            if search_keyword in field_name:
                matches.append(field_def)
        
        return matches
    
    def __len__(self) -> int:
        """返回字段数量"""
        return len(self._fields)
    
    def __repr__(self) -> str:
        """对象表示"""
        return f"JiraIssueTypeFields(project={self.project_key}, issue_type={self.issue_type}, fields_count={len(self._fields)})"


# 缓存字典：键为 (project_key, issue_type) 元组
_field_cache: Dict[Tuple[str, str], JiraIssueTypeFields] = {}


def get_issue_type_fields(project_key: str, issue_type: str, use_cache: bool = True) -> JiraIssueTypeFields:
    """
    获取指定项目下指定Issue类型的字段定义
    
    Args:
        project_key: 项目Key
        issue_type: Issue类型名称
        use_cache: 是否使用缓存，默认为True
    
    Returns:
        JiraIssueTypeFields对象
    
    Raises:
        JiraAPIError: API调用失败时抛出
    """
    cache_key = (project_key, issue_type)
    
    # 如果使用缓存且缓存中存在，直接返回
    if use_cache and cache_key in _field_cache:
        logger.debug(f"使用缓存: project={project_key}, issue_type={issue_type}")
        return _field_cache[cache_key]
    
    # 从JIRA API获取字段定义
    logger.debug(f"从API获取字段定义: project={project_key}, issue_type={issue_type}")
    try:
        fields_data = get_fields(project_key, issue_type)
        
        # 创建字段管理器对象
        fields_manager = JiraIssueTypeFields(project_key, issue_type, fields_data)
        
        # 存入缓存
        if use_cache:
            _field_cache[cache_key] = fields_manager
            logger.debug(f"已缓存字段定义: project={project_key}, issue_type={issue_type}")
        
        return fields_manager
    
    except JiraAPIError:
        raise
    except Exception as e:
        logger.error(f"获取字段定义失败: {e}")
        raise JiraAPIError(f"获取字段定义失败: {e}")


def clear_field_cache(project_key: str = None, issue_type: str = None) -> None:
    """
    清除字段定义缓存
    
    Args:
        project_key: 可选，如果提供则只清除指定项目的缓存
        issue_type: 可选，如果提供则只清除指定Issue类型的缓存（需要同时提供project_key）
    """
    global _field_cache
    
    if project_key is None:
        # 清除所有缓存
        _field_cache.clear()
        logger.debug("已清除所有字段定义缓存")
    elif issue_type is None:
        # 清除指定项目的所有缓存
        keys_to_remove = [key for key in _field_cache.keys() if key[0] == project_key]
        for key in keys_to_remove:
            del _field_cache[key]
        logger.debug(f"已清除项目 {project_key} 的所有字段定义缓存")
    else:
        # 清除指定项目和Issue类型的缓存
        cache_key = (project_key, issue_type)
        if cache_key in _field_cache:
            del _field_cache[cache_key]
            logger.debug(f"已清除缓存: project={project_key}, issue_type={issue_type}")
