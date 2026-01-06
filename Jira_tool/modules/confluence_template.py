"""
Confluence模板管理模块
"""
import re
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from Jira_tool.confluence_client import get_page_content, ConfluenceAPIError
from Jira_tool.modules.local_templates import get_local_template_storage
from core.debug_logger import logger


# 预置模板配置
TEMPLATES = [
    {"name": "测试用例评审模板", "page_id": "221989592"},
    {"name": "会议纪要模板", "page_id": "310457377"},
    {"name": "通用评审模板", "page_id": "521081686"},
    {"name": "总结文档模板", "page_id": "SUMMARY_DOC"},
    {"name": "测试指导模板", "page_id": "TEST_GUIDE"}
]

# 模板字段定义（JSON配置）
TEMPLATE_FIELDS = {
    "221989592": {  # 测试用例评审模板
        "sections": [
            {
                "name": "基本信息",
                "fields": [
                    {
                        "name": "作者",
                        "field_name": "author",
                        "type": "person",
                        "required": True,
                        "search_patterns": ["作者", "author"]
                    },
                    {
                        "name": "部门",
                        "field_name": "department",
                        "type": "text",
                        "required": True,
                        "search_patterns": ["部门", "department"]
                    },
                    {
                        "name": "Feature名称",
                        "field_name": "feature_name",
                        "type": "text",
                        "required": True,
                        "search_patterns": ["Feature名称", "Feature", "feature"]
                    },
                    {
                        "name": "三方对接开发Owner",
                        "field_name": "third_party_owner",
                        "type": "person",
                        "required": False,
                        "search_patterns": ["三方对接开发Owner", "开发Owner", "owner"]
                    },
                    {
                        "name": "评审时间",
                        "field_name": "review_time",
                        "type": "date",
                        "required": False,
                        "search_patterns": ["评审时间", "时间", "time"]
                    },
                    {
                        "name": "评审结论",
                        "field_name": "review_conclusion",
                        "type": "radio",
                        "required": False,
                        "options": ["通过", "不通过", "修改后通过"],
                        "default": "修改后通过",
                        "search_patterns": ["评审结论", "结论", "conclusion"]
                    },
                    {
                        "name": "修改后重新评审",
                        "field_name": "re_review_after_modification",
                        "type": "checkbox",
                        "required": False,
                        "default": False,
                        "search_patterns": ["修改后重新评审", "重新评审", "re-review"]
                    }
                ]
            },
            {
                "name": "评审信息",
                "fields": [
                    {
                        "name": "被评用例路径",
                        "field_name": "test_case_path",
                        "type": "text",
                        "required": True,
                        "search_patterns": ["被评用例路径", "用例路径", "路径"]
                    },
                    {
                        "name": "FDE",
                        "field_name": "reviewer_fde",
                        "type": "person",
                        "required": False,
                        "search_patterns": ["FDE", "评审人员"],
                        "row_group": "reviewers"
                    },
                    {
                        "name": "SE",
                        "field_name": "reviewer_se",
                        "type": "person",
                        "required": False,
                        "search_patterns": ["SE", "评审人员"],
                        "row_group": "reviewers"
                    },
                    {
                        "name": "开发owner",
                        "field_name": "reviewer_dev_owner",
                        "type": "person",
                        "required": False,
                        "search_patterns": ["开发owner", "开发Owner", "评审人员"],
                        "row_group": "reviewers"
                    },
                    {
                        "name": "TM",
                        "field_name": "reviewer_tm",
                        "type": "person",
                        "required": False,
                        "search_patterns": ["TM", "评审人员"],
                        "row_group": "reviewers"
                    },
                    {
                        "name": "用例弱项洞察报告链接",
                        "field_name": "weakness_report_link",
                        "type": "url",
                        "required": False,
                        "search_patterns": ["用例弱项洞察报告链接", "弱项报告", "weakness report"]
                    },
                    {
                        "name": "需求文档链接",
                        "field_name": "requirement_doc_link",
                        "type": "url",
                        "required": False,
                        "search_patterns": ["需求文档链接", "需求文档", "requirement document"]
                    },
                    {
                        "name": "需求矩阵链接",
                        "field_name": "requirement_matrix_link",
                        "type": "url",
                        "required": False,
                        "search_patterns": ["需求矩阵链接", "需求矩阵", "requirement matrix"]
                    },
                    {
                        "name": "评审形式",
                        "field_name": "review_form",
                        "type": "text",
                        "required": False,
                        "search_patterns": ["评审形式", "形式", "form"],
                        "row_group": "review_metrics"
                    },
                    {
                        "name": "评审时长 (小时)",
                        "field_name": "review_duration_hours",
                        "type": "text",
                        "required": False,
                        "search_patterns": ["评审时长", "时长", "duration"],
                        "row_group": "review_metrics"
                    },
                    {
                        "name": "评审规模 (评审的文件个数)",
                        "field_name": "review_scope_files",
                        "type": "text",
                        "required": False,
                        "search_patterns": ["评审规模", "规模", "scope"],
                        "row_group": "review_metrics"
                    }
                ]
            },
            {
                "name": "问题记录",
                "type": "table",
                "field_name": "issue_records",
                "render": "issue_records_221",
                "columns": [
                    {"name": "序号", "field_name": "sequence_no", "type": "text", "required": False},
                    {"name": "建议与改善", "field_name": "suggestion", "type": "text", "required": True},
                    {"name": "提出人", "field_name": "proposer", "type": "person", "required": False},
                    {"name": "责任人", "field_name": "responsible", "type": "person", "required": False},
                    {"name": "完成情况", "field_name": "completion_status", "type": "text", "required": False},
                    {"name": "完成时间", "field_name": "completion_time", "type": "date", "required": False},
                    {"name": "评审单任务链接", "field_name": "review_task_link", "type": "url", "required": False},
                    {"name": "备注", "field_name": "remarks", "type": "text", "required": False}
                ],
                "search_patterns": ["问题记录", "问题", "issue"]
            }
        ]
    },
    "310457377": {  # 会议纪要模板（Confluence 页内结构为“单个大表格”，含会议信息 + 问题列表）
        "sections": [
            {
                "name": "会议信息",
                "fields": [
                    {
                        "name": "会议主题",
                        "field_name": "meeting_subject",
                        "type": "text",
                        "required": True,
                        "search_patterns": ["会议主题", "主题"]
                    },
                    {
                        "name": "参加人员",
                        "field_name": "participants",
                        "type": "textarea",
                        "required": True,
                        "search_patterns": ["参加人员", "参会人员"]
                    },
                    {
                        "name": "会议地点",
                        "field_name": "meeting_location",
                        "type": "text",
                        "required": False,
                        "search_patterns": ["会议地点", "地点"]
                    },
                    {
                        "name": "会议主持",
                        "field_name": "meeting_host",
                        "type": "text",
                        "required": True,
                        "search_patterns": ["会议主持", "主持"]
                    },
                    {
                        "name": "会议记录",
                        "field_name": "meeting_recorder",
                        "type": "text",
                        "required": True,
                        "search_patterns": ["会议记录", "记录"]
                    },
                ]
            },
            {
                "name": "问题列表",
                "type": "table",
                "field_name": "issue_list",
                # 该模板的“问题列表”嵌在同一个大表格里：需要替换表头行之后的多行<tr>
                "render": "issue_list_310",
                "columns": [
                    {"name": "序号", "field_name": "sequence_no", "type": "text", "required": False},
                    {"name": "*问题列表", "field_name": "issue", "type": "text", "required": True},
                    {"name": "*提出人", "field_name": "proposer", "type": "person", "required": True},
                    {"name": "*责任人", "field_name": "responsible", "type": "person", "required": True},
                    {"name": "*记录时间", "field_name": "record_time", "type": "date", "required": True},
                    {"name": "*完成时间", "field_name": "completion_time", "type": "date", "required": True},
                    {"name": "*完成情况", "field_name": "completion_status", "type": "text", "required": True},
                    {"name": "备注", "field_name": "remarks", "type": "text", "required": False},
                ],
                "search_patterns": ["问题列表"]
            }
        ]
    },
    "521081686": {  # 通用评审模板
        "sections": [
            {
                "name": "基本信息",
                "fields": [
                    {
                        "name": "作者",
                        "field_name": "author",
                        "type": "person",
                        "required": True,
                        "search_patterns": ["作者", "author"]
                    },
                    {
                        "name": "部门",
                        "field_name": "department",
                        "type": "text",
                        "required": True,
                        "search_patterns": ["部门", "department"]
                    },
                    {
                        "name": "项目名称",
                        "field_name": "project_name",
                        "type": "text",
                        "required": True,
                        "search_patterns": ["项目名称", "项目", "project"]
                    },
                    {
                        "name": "测试人员",
                        "field_name": "test_person",
                        "type": "text",
                        "required": False,
                        "search_patterns": ["测试人员"]
                    },
                    {
                        "name": "评审时间",
                        "field_name": "review_time",
                        "type": "date",
                        "required": False,
                        "search_patterns": ["评审时间", "时间"]
                    },
                    {
                        "name": "评审结论",
                        "field_name": "review_conclusion",
                        "type": "text",
                        "required": False,
                        "search_patterns": ["评审结论", "结论", "conclusion"]
                    }
                ]
            }
            ,
            {
                "name": "评审信息",
                "fields": [
                    {
                        "name": "被评代码或文档路径",
                        "field_name": "assessed_code_path",
                        "type": "text",
                        "required": False,
                        "search_patterns": ["被评代码或文档路径"]
                    },
                    {
                        "name": "评审人员",
                        "field_name": "reviewers",
                        "type": "textarea",
                        "required": False,
                        "search_patterns": ["评审人员"]
                    },
                    {
                        "name": "方案设计文档链接",
                        "field_name": "design_doc_link",
                        "type": "url",
                        "required": False,
                        "search_patterns": ["方案设计文档链接"]
                    },
                    {
                        "name": "评审形式",
                        "field_name": "review_form",
                        "type": "text",
                        "required": False,
                        "search_patterns": ["评审形式"]
                    },
                    {
                        "name": "需求矩阵链接",
                        "field_name": "requirement_matrix_link",
                        "type": "url",
                        "required": False,
                        "search_patterns": ["需求矩阵链接", "需求矩阵"]
                    },
                    {
                        "name": "评审时长（小时）",
                        "field_name": "review_duration_hours",
                        "type": "text",
                        "required": False,
                        "search_patterns": ["评审时长", "时长"]
                    },
                    {
                        "name": "自测用例&自测报告链接",
                        "field_name": "self_test_links",
                        "type": "url",
                        "required": False,
                        "search_patterns": ["自测用例", "自测报告", "自测用例&自测报告链接"]
                    },
                    {
                        "name": "评审规模（评审的文件个数）",
                        "field_name": "review_scope_files",
                        "type": "text",
                        "required": False,
                        "search_patterns": ["评审规模", "规模"]
                    },
                ]
            },
            {
                "name": "问题记录",
                "type": "table",
                "field_name": "issue_records",
                "render": "issue_records_521",
                "columns": [
                    {"name": "序号", "field_name": "sequence_no", "type": "text", "required": False},
                    {"name": "文件名", "field_name": "file_name", "type": "text", "required": False},
                    {"name": "建议/改善", "field_name": "suggestion", "type": "text", "required": False},
                    {"name": "提出人", "field_name": "proposer", "type": "person", "required": False},
                    {"name": "评审时间", "field_name": "review_time", "type": "date", "required": False},
                    {"name": "整改责任人", "field_name": "responsible", "type": "person", "required": False},
                    {"name": "完成情况", "field_name": "completion_status", "type": "text", "required": False},
                    {"name": "备注", "field_name": "remarks", "type": "text", "required": False},
                ],
                "search_patterns": ["问题记录"]
            }
        ]
    },
    "SUMMARY_DOC": {  # 总结文档模板
        "sections": [
            {
                "name": "基本信息",
                "fields": [
                    {
                        "name": "文档标题",
                        "field_name": "document_title",
                        "type": "text",
                        "required": False,
                        "search_patterns": ["文档标题", "document_title", "title"]
                    },
                    {
                        "name": "作者",
                        "field_name": "author",
                        "type": "person",
                        "required": True,
                        "search_patterns": ["作者", "author"],
                        "row_group": "basic_info_line1"
                    },
                    {
                        "name": "创建时间",
                        "field_name": "create_date",
                        "type": "date",
                        "required": False,
                        "search_patterns": ["创建时间", "create_date", "date"],
                        "row_group": "basic_info_line1"
                    },
                    {
                        "name": "版本",
                        "field_name": "version",
                        "type": "text",
                        "required": False,
                        "search_patterns": ["版本", "version"],
                        "row_group": "basic_info_line1"
                    },
                    {
                        "name": "摘要",
                        "field_name": "summary_content",
                        "type": "textarea",
                        "required": False,
                        "search_patterns": ["摘要", "summary", "summary_content"]
                    },
                    {
                        "name": "章节内容",
                        "field_name": "chapters_content",
                        "type": "chapters",
                        "required": False,
                        "search_patterns": ["章节", "chapters", "chapters_content"]
                    },
                    {
                        "name": "总结",
                        "field_name": "conclusion_content",
                        "type": "textarea",
                        "required": False,
                        "search_patterns": ["总结", "conclusion", "conclusion_content"]
                    }
                ]
            }
        ]
    },
    "TEST_GUIDE": {  # 测试指导模板
        "sections": [
            {
                "name": "元数据信息",
                "fields": [
                    {
                        "name": "Version",
                        "field_name": "version",
                        "type": "text",
                        "required": False,
                        "default": "1.0",
                        "search_patterns": ["Version", "版本"]
                    },
                    {
                        "name": "Status",
                        "field_name": "status",
                        "type": "text",
                        "required": False,
                        "default": "Released",
                        "search_patterns": ["Status", "状态"]
                    },
                    {
                        "name": "Date",
                        "field_name": "date",
                        "type": "date",
                        "required": False,
                        "search_patterns": ["Date", "日期"]
                    },
                    {
                        "name": "Creator",
                        "field_name": "creator",
                        "type": "person",
                        "required": False,
                        "search_patterns": ["Creator", "创建者"]
                    },
                    {
                        "name": "Reviewer",
                        "field_name": "reviewer",
                        "type": "person",
                        "required": False,
                        "search_patterns": ["Reviewer", "评审者"],
                        "prefix": "SE: "
                    },
                    {
                        "name": "Approval",
                        "field_name": "approval",
                        "type": "person",
                        "required": False,
                        "search_patterns": ["Approval", "批准"],
                        "prefix": "TM: "
                    },
                    {
                        "name": "Scope of application",
                        "field_name": "scope_of_application",
                        "type": "text",
                        "required": False,
                        "default": "US VAL",
                        "search_patterns": ["Scope of application", "适用范围"]
                    }
                ]
            },
            {
                "name": "版本历史",
                "type": "table",
                "field_name": "revision_history",
                "render": "revision_history_table",
                "readonly": True,  # 只读模式，不允许添加/删除行
                "single_row": True,  # 单行模式
                "columns": [
                    {"name": "Version", "field_name": "revision_version", "type": "text", "required": False, "default": "v1.0"},
                    {"name": "Summary of the revisions", "field_name": "revision_summary", "type": "textarea", "required": False},
                    {"name": "Date", "field_name": "revision_date", "type": "date", "required": False},
                    {"name": "Creator", "field_name": "revision_creator", "type": "person", "required": False},
                    {"name": "Reviewed by", "field_name": "revision_reviewed_by", "type": "person", "required": False, "prefix": "SE: "},
                    {"name": "Reviewed Date", "field_name": "revision_reviewed_date", "type": "date", "required": False}
                ],
                "search_patterns": ["版本历史", "revision history"]
            },
            {
                "name": "测试内容",
                "fields": [
                    {
                        "name": "测试说明",
                        "field_name": "test_instructions",
                        "type": "richtext_advanced",  # 使用高级富文本编辑器，支持图片和表格
                        "required": False,
                        "search_patterns": ["测试说明", "test instructions"]
                    }
                ]
            }
        ]
    }
}


class TemplateManager:
    """模板管理器"""
    
    def __init__(self):
        self._template_cache: Dict[str, str] = {}  # {page_id: content}
        self._template_fields_cache: Dict[str, List[Dict]] = {}  # {page_id: fields}
    
    def get_template_list(self) -> List[Dict[str, str]]:
        """
        返回预置模板列表
        
        Returns:
            模板列表，每个模板包含name和page_id
        """
        return TEMPLATES.copy()
    
    def load_template_from_confluence(self, page_id: str, use_cache: bool = True) -> str:
        """
        从Confluence获取模板内容
        
        Args:
            page_id: 模板页面ID
            use_cache: 是否使用缓存
        
        Returns:
            模板内容的HTML字符串（Storage Format）
        
        Raises:
            ConfluenceAPIError: API调用失败时抛出
        """
        # 本地固定模板：不在线拉取
        local = get_local_template_storage(page_id)
        if local is not None:
            self._template_cache[page_id] = local
            return local

        if use_cache and page_id in self._template_cache:
            logger.debug(f"从缓存加载模板: {page_id}")
            return self._template_cache[page_id]
        
        try:
            logger.info(f"从Confluence加载模板: {page_id}")
            content = get_page_content(page_id)
            self._template_cache[page_id] = content
            return content
        except ConfluenceAPIError as e:
            logger.error(f"加载模板失败: {e}")
            raise
        except Exception as e:
            logger.error(f"加载模板时发生未知错误: {e}")
            raise ConfluenceAPIError(f"加载模板失败: {e}")
    
    def get_template_fields(self, page_id: str) -> List[Dict[str, Any]]:
        """
        获取模板字段定义（从JSON配置）
        
        Args:
            page_id: 模板页面ID
        
        Returns:
            字段定义列表
        """
        if page_id in self._template_fields_cache:
            return self._template_fields_cache[page_id]
        
        if page_id not in TEMPLATE_FIELDS:
            logger.warning(f"未找到模板字段定义: {page_id}")
            return []
        
        # 从JSON配置构建字段列表
        fields = []
        template_config = TEMPLATE_FIELDS[page_id]
        
        for section in template_config.get("sections", []):
            section_name = section.get("name", "")
            section_type = section.get("type", "form")
            
            if section_type == "table":
                # 表格类型字段
                # 生成合适的field_name（使用search_patterns的第一个或section_name）
                field_name = section.get("field_name", "")
                if not field_name:
                    # 如果没有指定，使用search_patterns的第一个，或使用section_name
                    search_patterns = section.get("search_patterns", [])
                    if search_patterns:
                        # 将中文转换为拼音或使用英文
                        field_name = search_patterns[0].lower().replace(" ", "_")
                    else:
                        # 使用section_name，转换为合适的格式
                        field_name = section_name.lower().replace(" ", "_").replace("问题记录", "issue_records").replace("问题", "issues")
                
                table_field = {
                    "name": section_name,
                    "field_name": field_name,
                    "type": "table",
                    "required": False,
                    "columns": section.get("columns", []),
                    "search_patterns": section.get("search_patterns", [])
                }
                fields.append(table_field)
            else:
                # 普通表单字段
                for field in section.get("fields", []):
                    fields.append(field)
        
        self._template_fields_cache[page_id] = fields
        logger.info(f"从JSON配置加载模板字段: {page_id}, 共 {len(fields)} 个字段")
        return fields
    
    def replace_variables(self, template_content: str, variables: Dict[str, Any], page_id: Optional[str] = None) -> str:
        """
        替换模板中的变量（支持模糊匹配）
        
        Args:
            template_content: 模板内容（HTML）
            variables: 变量字典 {变量名: 值}，值可以是字符串或列表（用于表格）
            page_id: 模板页面ID（用于获取字段配置）
        
        Returns:
            替换后的内容
        """
        result = template_content
        
        # 获取模板字段配置（用于模糊匹配）
        field_configs = {}
        if page_id and page_id in TEMPLATE_FIELDS:
            template_config = TEMPLATE_FIELDS[page_id]
            for section in template_config.get("sections", []):
                for field in section.get("fields", []):
                    field_name = field.get("field_name", "")
                    if field_name:
                        field_configs[field_name] = field
                if section.get("type") == "table":
                    # 使用field_name而不是name来匹配
                    table_field_name = section.get("field_name", "")
                    if not table_field_name:
                        table_field_name = section.get("name", "").lower().replace(" ", "_").replace("问题记录", "issue_records")
                    field_configs[table_field_name] = section
                    # 同时使用name作为key（兼容）
                    table_name = section.get("name", "").lower().replace(" ", "_")
                    if table_name != table_field_name:
                        field_configs[table_name] = section
        
        # 转义HTML特殊字符
        def escape_html(text: str) -> str:
            if not text:
                return ''
            return (
                str(text)
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;')
            )
        
        # 处理表格数据
        for var_name, var_value in variables.items():
            if isinstance(var_value, list):
                # 表格数据，需要生成HTML表格
                if var_name in field_configs:
                    table_config = field_configs[var_name]
                    columns = table_config.get("columns", [])
                    render_mode = table_config.get("render", "")
                    if render_mode == "issue_records_221":
                        table_html = self._generate_issue_records_rows_221(var_value, columns, default_rows=8)
                    elif render_mode == "issue_records_521":
                        table_html = self._generate_issue_records_rows_521(var_value, columns, default_rows=7)
                    elif render_mode == "issue_list_310":
                        table_html = self._generate_issue_list_rows_310(var_value, columns, default_rows=5)
                    elif render_mode == "revision_history_table":
                        table_html = self._generate_revision_history_rows(var_value, columns, default_rows=2)
                    # 兼容旧逻辑：嵌入行（旧版会议纪要）
                    elif render_mode == "embedded_rows":
                        table_html = self._generate_table_rows_confluence(var_value, columns)
                    else:
                        # 默认：生成完整<table>用于替换
                        table_html = self._generate_table_html(var_value, columns)

                    # 精确占位符替换（即使关闭模糊也可用）
                    exact_patterns = [
                        f"{{{var_name}}}",
                        f"{{{{{var_name}}}}}",
                        f"(*{var_name})",
                    ]
                    for pattern in exact_patterns:
                        result = result.replace(pattern, table_html)

                    # 模糊替换（可开关）
                continue
        
        # 处理普通字段
        for var_name, var_value in variables.items():
            if isinstance(var_value, list):
                continue  # 表格已在上面处理
            
            raw_value = str(var_value) if var_value else ''
            
            # 特殊处理：某些变量已经是 HTML 格式，不需要转义
            # 这些变量名通常包含 "content", "html", "chapters", "toc", "richtext" 等关键词
            field_config = field_configs.get(var_name, {})
            field_type = field_config.get("type", "")
            is_html_content = (
                field_type == "richtext" or
                field_type == "richtext_advanced" or
                field_type == "chapters" or
                var_name.endswith("_content") or 
                var_name.endswith("_html") or 
                var_name == "chapters_content" or
                var_name == "table_of_contents" or
                var_name.startswith("html_") or
                var_name.startswith("test_")  # 测试相关字段可能是HTML
            )
            
            if is_html_content:
                # HTML 内容直接使用，不转义
                # 但需要清理可能导致XML解析错误的标签（如<!DOCTYPE>、<html>、<head>、<body>等）
                final_value = self._clean_html_content(raw_value)
                # #region agent log
                try:
                    if var_name == "chapters_content":
                        log_path = Path(__file__).parent.parent / ".cursor" / "debug.log"
                        with open(log_path, "a", encoding="utf-8") as f:
                            sample_value = final_value[:500] if len(final_value) > 500 else final_value
                            log_entry = json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "confluence_template.py:654", "message": "Processing chapters_content", "data": {"var_name": var_name, "value_length": len(final_value), "sample_value": sample_value, "has_id": 'id="' in sample_value}, "timestamp": __import__("time").time() * 1000})
                            f.write(log_entry + "\n")
                except: pass
                # #endregion
            else:
                # 普通文本需要转义
                escaped_value = escape_html(raw_value)
                
                # 获取字段配置
                field_config = field_configs.get(var_name, {})
                field_type = field_config.get("type", "")
                
                # 处理人员字段的前缀（如 "SE: " 或 "TM: "）
                if field_type == "person" and escaped_value:
                    prefix = field_config.get("prefix", "")
                    if prefix:
                        escaped_value = prefix + escaped_value
                
                # textarea/多行文本：把换行转换为 <br />，避免 Confluence 中被折叠成空格
                if field_type == "textarea" and escaped_value:
                    escaped_value = escaped_value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br />")
                
                final_value = escaped_value
            
            # 精确匹配替换
            exact_patterns = [
                f"{{{var_name}}}",
                f"{{{{{var_name}}}}}",
                f"(*{var_name})",
            ]
            
            for pattern in exact_patterns:
                if pattern in result:
                    result_before = result
                    result = result.replace(pattern, final_value)
                    # #region agent log
                    try:
                        if var_name == "chapters_content":
                            log_path = Path(__file__).parent.parent / ".cursor" / "debug.log"
                            with open(log_path, "a", encoding="utf-8") as f:
                                sample_result = result[:500] if len(result) > 500 else result
                                log_entry = json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "confluence_template.py:677", "message": "After replace chapters_content", "data": {"var_name": var_name, "pattern": pattern, "result_length": len(result), "sample_result": sample_result, "has_id_after_replace": 'id="' in sample_result}, "timestamp": __import__("time").time() * 1000})
                                f.write(log_entry + "\n")
                    except: pass
                    # #endregion
        
        # 处理空的摘要和总结section（仅针对SUMMARY_DOC模板）
        if page_id == "SUMMARY_DOC":
            # 检查summary_content变量值是否为空
            summary_value = variables.get("summary_content", "")
            if not summary_value or (isinstance(summary_value, str) and not summary_value.strip()):
                # 移除摘要section（包括h2标题和p标签，p标签中可能只包含<br />或空白）
                # 匹配：<h2...>摘要</h2> 后面的 <p...>...</p>，其中p标签内容只包含<br />、空白字符等
                result = re.sub(
                    r'<h2[^>]*>摘要</h2>\s*<p[^>]*>\s*(?:<br\s*/?>)?\s*</p>',
                    '',
                    result,
                    flags=re.IGNORECASE
                )
            
            # 检查conclusion_content变量值是否为空
            conclusion_value = variables.get("conclusion_content", "")
            if not conclusion_value or (isinstance(conclusion_value, str) and not conclusion_value.strip()):
                # 移除总结section（包括h2标题和p标签，p标签中可能只包含<br />或空白）
                result = re.sub(
                    r'<h2[^>]*>总结</h2>\s*<p[^>]*>\s*(?:<br\s*/?>)?\s*</p>',
                    '',
                    result,
                    flags=re.IGNORECASE
                )
        
        return result

    def _escape_cell_text(self, text: Any) -> str:
        """表格单元格用：转义并把换行转换为 <br />"""
        if text is None:
            return ""
        s = str(text)
        s = (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
        s = s.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br />")
        return s

    def _cell_html(self, value: str, wrap_p: bool = True) -> str:
        """空值时返回 <br />，非空时返回 <p>...</p>（与模板保持接近）"""
        if not value:
            return "<br />"
        return f"<p>{value}</p>" if wrap_p else value

    def _generate_issue_records_rows_221(self, rows: List[Dict], columns: List[Dict], default_rows: int = 8) -> str:
        """
        生成 221989592 的“问题记录”多行<tr>：
        - 建议与改善列 colspan=4
        - 默认输出 8 行（与模板一致）
        """
        if not rows:
            rows = [{} for _ in range(default_rows)]

        html = ""
        for idx, row in enumerate(rows, start=1):
            seq = str(row.get("sequence_no") or idx).strip()
            suggestion = self._escape_cell_text(row.get("suggestion", "")).strip()
            proposer = self._escape_cell_text(row.get("proposer", "")).strip()
            responsible = self._escape_cell_text(row.get("responsible", "")).strip()
            completion_status = self._escape_cell_text(row.get("completion_status", "")).strip()
            completion_time = self._escape_cell_text(row.get("completion_time", "")).strip()
            review_task_link = self._escape_cell_text(row.get("review_task_link", "")).strip()
            remarks = self._escape_cell_text(row.get("remarks", "")).strip()

            html += "<tr>"
            html += f'<td style="text-align: left;">{seq or ""}</td>'
            html += f'<td style="text-align: left;" colspan="4">{self._cell_html(suggestion, wrap_p=False)}</td>'
            html += f'<td style="text-align: left;">{self._cell_html(proposer, wrap_p=False)}</td>'
            html += f'<td style="text-align: left;">{self._cell_html(responsible, wrap_p=False)}</td>'
            html += f'<td style="text-align: left;">{self._cell_html(completion_status, wrap_p=False)}</td>'
            html += f'<td style="text-align: left;">{self._cell_html(completion_time, wrap_p=False)}</td>'
            html += f'<td style="text-align: left;">{self._cell_html(review_task_link, wrap_p=False)}</td>'
            html += f'<td style="text-align: left;">{self._cell_html(remarks, wrap_p=False)}</td>'
            html += "</tr>\n"
        return html

    def _generate_issue_records_rows_521(self, rows: List[Dict], columns: List[Dict], default_rows: int = 7) -> str:
        """
        生成 521081686 的“问题记录”多行<tr>：
        - 建议/改善列 colspan=4
        - 默认输出 7 行（与用户提供 storage 中行数接近）
        """
        if not rows:
            rows = [{} for _ in range(default_rows)]

        html = ""
        for idx, row in enumerate(rows, start=1):
            seq = str(row.get("sequence_no") or idx).strip()
            file_name = self._escape_cell_text(row.get("file_name", "")).strip()
            suggestion = self._escape_cell_text(row.get("suggestion", "")).strip()
            proposer = self._escape_cell_text(row.get("proposer", "")).strip()
            review_time = self._escape_cell_text(row.get("review_time", "")).strip()
            responsible = self._escape_cell_text(row.get("responsible", "")).strip()
            completion_status = self._escape_cell_text(row.get("completion_status", "")).strip()
            remarks = self._escape_cell_text(row.get("remarks", "")).strip()

            html += "<tr>"
            html += f'<td style="text-align: left;">{seq or ""}</td>'
            html += f'<td style="text-align: left;">{self._cell_html(file_name, wrap_p=False)}</td>'
            html += f'<td style="text-align: left;" colspan="4">{self._cell_html(suggestion, wrap_p=False)}</td>'
            html += f'<td style="text-align: left;">{self._cell_html(proposer, wrap_p=False)}</td>'
            html += f'<td style="text-align: left;">{self._cell_html(review_time, wrap_p=False)}</td>'
            html += f'<td style="text-align: left;">{self._cell_html(responsible, wrap_p=False)}</td>'
            html += f'<td style="text-align: left;">{self._cell_html(completion_status, wrap_p=False)}</td>'
            html += f'<td style="text-align: left;">{self._cell_html(remarks, wrap_p=False)}</td>'
            html += "</tr>\n"
        return html

    def _generate_issue_list_rows_310(self, rows: List[Dict], columns: List[Dict], default_rows: int = 5) -> str:
        """生成 310457377（灰色大表格）的问题列表多行<tr>，默认 5 行。"""
        if not rows:
            rows = [{} for _ in range(default_rows)]

        def td(val: str, strong_seq: bool = False) -> str:
            if not val:
                return "<br />"
            if strong_seq:
                return f"<p><strong>{val}</strong></p>"
            return f"<p>{val}</p>"

        html = ""
        for idx, row in enumerate(rows, start=1):
            seq = str(row.get("sequence_no") or idx).strip()
            issue = self._escape_cell_text(row.get("issue", "")).strip()
            proposer = self._escape_cell_text(row.get("proposer", "")).strip()
            responsible = self._escape_cell_text(row.get("responsible", "")).strip()
            record_time = self._escape_cell_text(row.get("record_time", "")).strip()
            completion_time = self._escape_cell_text(row.get("completion_time", "")).strip()
            completion_status = self._escape_cell_text(row.get("completion_status", "")).strip()
            remarks = self._escape_cell_text(row.get("remarks", "")).strip()

            html += "<tr>"
            html += f'<td style="text-align: left;">{td(seq, strong_seq=True)}</td>'
            html += f'<td style="text-align: left;">{td(issue)}</td>'
            html += f'<td style="text-align: left;">{td(proposer)}</td>'
            html += f'<td style="text-align: left;">{td(responsible)}</td>'
            html += f'<td style="text-align: left;">{td(record_time)}</td>'
            html += f'<td style="text-align: left;">{td(completion_time)}</td>'
            html += f'<td style="text-align: left;">{td(completion_status)}</td>'
            html += f'<td style="text-align: left;">{td(remarks)}</td>'
            html += "</tr>\n"
        return html

    def _generate_revision_history_rows(self, rows: List[Dict], columns: List[Dict], default_rows: int = 1) -> str:
        """生成版本历史表格的单行<tr>（只渲染第一行）。"""
        if not rows:
            rows = [{}]

        def td(val: str) -> str:
            if not val:
                return "<br />"
            return f"<p>{val}</p>"

        # 只取第一行
        row = rows[0] if rows else {}
        revision_version = self._escape_cell_text(row.get("revision_version", "")).strip()
        revision_summary = self._escape_cell_text(row.get("revision_summary", "")).strip()
        revision_date = self._escape_cell_text(row.get("revision_date", "")).strip()
        revision_creator = self._escape_cell_text(row.get("revision_creator", "")).strip()
        revision_reviewed_by = self._escape_cell_text(row.get("revision_reviewed_by", "")).strip()
        revision_reviewed_date = self._escape_cell_text(row.get("revision_reviewed_date", "")).strip()

        html = "<tr>"
        html += f'<td style="text-align: left;">{td(revision_version)}</td>'
        html += f'<td style="text-align: left;">{td(revision_summary)}</td>'
        html += f'<td style="text-align: left;">{td(revision_date)}</td>'
        html += f'<td style="text-align: left;">{td(revision_creator)}</td>'
        html += f'<td style="text-align: left;">{td(revision_reviewed_by)}</td>'
        html += f'<td style="text-align: left;">{td(revision_reviewed_date)}</td>'
        html += "</tr>\n"
        return html

    def build_meeting_minutes_template_storage(self) -> str:
        """
        构建“会议纪要模板（310457377）”的默认 Storage Format 内容（与 WebUI 字段一致）。

        说明：
        - 这里使用显式占位符 `{field_name}`，即使关闭模糊替换也能稳定替换
        - 标签里的 * 用于体现必填，与 WebUI 保持一致
        """
        # 颜色/样式尽量沿用 Confluence 常见模板写法
        label_cell = 'class="highlight-green" data-highlight-colour="green"'
        rows = [
            ("会议主题*", "{meeting_subject}"),
            ("参加人员*", "{participants}"),
            ("会议时间", "{meeting_time}"),
            ("会议地点", "{meeting_location}"),
            ("会议议程", "{agenda}"),
            ("讨论内容", "{discussion}"),
            ("决议事项", "{decisions}"),
        ]

        tr_html = []
        for label, placeholder in rows:
            tr_html.append(
                "<tr>"
                f"<td {label_cell}>{label}</td>"
                f"<td>{placeholder}</td>"
                "</tr>"
            )

        return (
            '<h1>会议纪要</h1>'
            '<table class="relative-table wrapped"><tbody>'
            + "".join(tr_html)
            + "</tbody></table>"
        )
    

    def _generate_table_rows_confluence(self, rows: List[Dict], columns: List[Dict]) -> str:
        """
        生成 Confluence 大表格内的多行<tr>（不包含<table>外壳）。
        用于像 310457377 这种“会议信息 + 问题列表”在同一个表格里的模板。
        """
        def _escape(text: str) -> str:
            if text is None:
                return ""
            return (
                str(text)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )

        # 默认保留 5 行空行的体验（与模板一致）
        if not rows:
            rows = [{} for _ in range(5)]

        html = ""
        for idx, row in enumerate(rows, start=1):
            html += "<tr>"
            for col in columns:
                col_field = col.get("field_name", "")
                val = row.get(col_field, "")
                if col_field == "sequence_no" and (val is None or str(val).strip() == ""):
                    val = str(idx)
                cell = _escape(val)
                # 问题列表内容通常较长，左对齐更友好；其余居中
                align = "left" if col_field == "issue" else "center"
                html += f'<td style="text-align: {align};"><p>{cell}</p></td>'
            html += "</tr>"
        return html
    
    def _generate_table_html(self, rows: List[Dict], columns: List[Dict]) -> str:
        """
        生成表格HTML（带样式）
        
        Args:
            rows: 行数据列表，每行是一个字典
            columns: 列定义列表
        
        Returns:
            表格HTML字符串
        """
        # 添加表格样式
        style = """
        <style>
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 10px 0;
            font-size: 14px;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        </style>
        """
        
        html = style + '<table><thead><tr>'
        # 生成表头
        for col in columns:
            col_name = col.get("name", "")
            # 转义HTML
            col_name = (
                col_name
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
            )
            html += f'<th>{col_name}</th>'
        html += '</tr></thead><tbody>'
        
        # 如果没有数据，至少显示一个空行
        if not rows:
            html += '<tr>'
            for col in columns:
                html += '<td></td>'
            html += '</tr>'
        else:
            # 生成数据行 - 确保按列定义顺序输出，避免列顺序错乱
            for row_idx, row in enumerate(rows):
                html += '<tr>'
                for col_idx, col in enumerate(columns):
                    col_field = col.get("field_name", "")
                    col_name = col.get("name", "")
                    # 从row字典中获取对应字段的值
                    cell_value = str(row.get(col_field, ""))
                    # 转义HTML
                    cell_value = (
                        cell_value
                        .replace('&', '&amp;')
                        .replace('<', '&lt;')
                        .replace('>', '&gt;')
                        .replace('"', '&quot;')
                    )
                    html += f'<td>{cell_value}</td>'
                html += '</tr>'
        
        html += '</tbody></table>'
        return html
    
    def _clean_html_content(self, html_content: str) -> str:
        """
        清理HTML内容，移除可能导致XML解析错误的标签
        
        Args:
            html_content: 原始HTML内容
        
        Returns:
            清理后的HTML内容
        """
        if not html_content:
            return ""
        
        # 移除可能导致XML解析错误的标签和指令
        # 1. 移除 <!DOCTYPE> 声明
        html_content = re.sub(r'<!DOCTYPE[^>]*>', '', html_content, flags=re.IGNORECASE)
        
        # 2. 移除 XML 声明 <?xml ... ?>
        html_content = re.sub(r'<\?xml[^>]*\?>', '', html_content, flags=re.IGNORECASE)
        
        # 3. 移除 <html>、<head>、<body> 标签，但保留内容
        html_content = re.sub(r'</?html[^>]*>', '', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'</?head[^>]*>', '', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'</?body[^>]*>', '', html_content, flags=re.IGNORECASE)
        
        # 4. 移除 <meta> 标签
        html_content = re.sub(r'<meta[^>]*>', '', html_content, flags=re.IGNORECASE)
        
        # 5. 移除 <style> 标签及其内容
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
        
        # 6. 移除 <script> 标签及其内容
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
        
        # 7. 移除 <title> 标签及其内容
        html_content = re.sub(r'<title[^>]*>.*?</title>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
        
        return html_content.strip()
    
    def clear_cache(self, page_id: Optional[str] = None):
        """
        清除模板缓存
        
        Args:
            page_id: 如果提供，只清除该模板的缓存；否则清除所有缓存
        """
        if page_id:
            self._template_cache.pop(page_id, None)
            self._template_fields_cache.pop(page_id, None)
            logger.debug(f"已清除模板缓存: {page_id}")
        else:
            self._template_cache.clear()
            self._template_fields_cache.clear()
            logger.debug("已清除所有模板缓存")


# 创建全局实例
_template_manager = TemplateManager()


def get_template_list() -> List[Dict[str, str]]:
    """获取模板列表"""
    return _template_manager.get_template_list()


def load_template_from_confluence(page_id: str, use_cache: bool = True) -> str:
    """从Confluence加载模板"""
    return _template_manager.load_template_from_confluence(page_id, use_cache)


def get_template_fields(page_id: str) -> List[Dict[str, Any]]:
    """获取模板字段定义"""
    return _template_manager.get_template_fields(page_id)


def replace_variables(template_content: str, variables: Dict[str, Any], page_id: Optional[str] = None) -> str:
    """替换模板变量（支持模糊匹配）"""
    return _template_manager.replace_variables(template_content, variables, page_id)


def clear_template_cache(page_id: Optional[str] = None):
    """清除模板缓存"""
    _template_manager.clear_cache(page_id)
