"""
Confluence模板字段解析模块
解析HTML模板，提取可编辑字段
"""
import re
from typing import List, Dict, Any
from html.parser import HTMLParser
from core.debug_logger import logger


class TemplateFieldParser(HTMLParser):
    """HTML模板字段解析器"""
    
    def __init__(self):
        super().__init__()
        self.fields: List[Dict[str, Any]] = []
        self.current_table_row = []
        self.in_table = False
        self.in_td = False
        self.current_td_text = ""
        self.current_row_index = 0
        self.table_rows = []
    
    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.in_table = True
        elif tag == 'tr':
            self.current_table_row = []
            self.current_row_index = len(self.table_rows)
        elif tag == 'td':
            self.in_td = True
            self.current_td_text = ""
    
    def handle_endtag(self, tag):
        if tag == 'table':
            self.in_table = False
            # 处理表格数据
            self._process_table_fields()
        elif tag == 'tr':
            if self.current_table_row:
                self.table_rows.append(self.current_table_row.copy())
            self.current_table_row = []
        elif tag == 'td':
            self.in_td = False
            if self.current_td_text:
                self.current_table_row.append(self.current_td_text.strip())
            self.current_td_text = ""
    
    def handle_data(self, data):
        if self.in_td:
            self.current_td_text += data
    
    def _process_table_fields(self):
        """处理表格字段"""
        for row in self.table_rows:
            if len(row) >= 2:
                # 假设左侧列是标签，右侧列是值
                label = row[0]
                value = row[1] if len(row) > 1 else ""
                
                # 检查值列是否包含占位符
                if self._is_placeholder(value):
                    field = self._create_field_from_label(label, value)
                    if field:
                        self.fields.append(field)
    
    def _is_placeholder(self, text: str) -> bool:
        """判断文本是否为占位符"""
        if not text:
            return True
        
        placeholder_patterns = [
            r'^XXX.*$',
            r'^\(\*.*\)$',  # (*评审人)
            r'^\{.*\}$',  # {variable}
            r'^.*XXX.*$',
        ]
        
        for pattern in placeholder_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _create_field_from_label(self, label: str, placeholder: str) -> Dict[str, Any]:
        """根据标签创建字段定义"""
        if not label or not label.strip():
            return None
        
        # 清理标签文本
        label = label.strip()
        
        # 确定字段类型
        field_type = self._detect_field_type(label, placeholder)
        
        # 确定是否必填（根据标签中的*号或常见必填字段）
        required = '*' in label or self._is_required_field(label)
        
        # 生成字段名（用于变量替换）
        field_name = self._generate_field_name(label)
        
        return {
            "name": label,
            "field_name": field_name,
            "type": field_type,
            "required": required,
            "placeholder": placeholder,
            "default_value": ""
        }
    
    def _detect_field_type(self, label: str, placeholder: str) -> str:
        """检测字段类型"""
        label_lower = label.lower()
        
        # 日期相关
        if any(keyword in label_lower for keyword in ['日期', '时间', 'date', 'time']):
            return "date"
        
        # 链接相关
        if any(keyword in label_lower for keyword in ['链接', 'link', 'url', '文档']):
            return "url"
        
        # 人员相关
        if any(keyword in label_lower for keyword in ['人员', '人', '评审人', '提出人', '责任人', 'person', 'reviewer']):
            return "person"
        
        # 多行文本（如果占位符较长或包含换行）
        if len(placeholder) > 50 or '\n' in placeholder:
            return "textarea"
        
        # 默认文本输入
        return "text"
    
    def _is_required_field(self, label: str) -> bool:
        """判断字段是否必填"""
        required_keywords = ['主题', '标题', '名称', '结论', 'subject', 'title', 'name', 'conclusion']
        label_lower = label.lower()
        return any(keyword in label_lower for keyword in required_keywords)
    
    def _generate_field_name(self, label: str) -> str:
        """生成字段名（用于变量替换）"""
        # 移除特殊字符，转换为下划线命名
        field_name = re.sub(r'[^\w\u4e00-\u9fff]', '_', label)
        field_name = re.sub(r'_+', '_', field_name)
        field_name = field_name.strip('_')
        
        # 如果为空，使用序号
        if not field_name:
            field_name = f"field_{len(self.fields) + 1}"
        
        return field_name


def parse_fields(html_content: str) -> List[Dict[str, Any]]:
    """
    解析HTML模板，提取可编辑字段
    
    Args:
        html_content: HTML模板内容（Confluence Storage Format）
    
    Returns:
        字段定义列表，每个字段包含：
        - name: 字段显示名称
        - field_name: 字段变量名（用于替换）
        - type: 字段类型（text, textarea, date, url, person）
        - required: 是否必填
        - placeholder: 占位符文本
        - default_value: 默认值
    """
    try:
        parser = TemplateFieldParser()
        parser.feed(html_content)
        fields = parser.fields
        
        logger.info(f"解析模板字段: 找到 {len(fields)} 个字段")
        
        # 去重（基于字段名）
        seen = set()
        unique_fields = []
        for field in fields:
            field_key = field['name']
            if field_key not in seen:
                seen.add(field_key)
                unique_fields.append(field)
        
        logger.info(f"去重后字段数: {len(unique_fields)}")
        return unique_fields
    
    except Exception as e:
        logger.exception(f"解析模板字段失败: {e}")
        # 返回空列表，让调用者处理
        return []


def replace_field_in_content(content: str, field_name: str, value: str) -> str:
    """
    在内容中替换特定字段的值
    
    Args:
        content: 模板内容
        field_name: 字段名
        value: 替换值
    
    Returns:
        替换后的内容
    """
    if not value:
        return content
    
    # 转义HTML
    escaped_value = (
        str(value)
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#39;')
    )
    
    # 多种替换模式
    patterns = [
        (f"{{{field_name}}}", escaped_value),
        (f"{{{{{field_name}}}}}", escaped_value),
        (f"(*{field_name})", escaped_value),
    ]
    
    result = content
    for pattern, replacement in patterns:
        result = result.replace(pattern, replacement)
    
    return result
