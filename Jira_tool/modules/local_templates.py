"""
本地固定模板（Confluence Storage Format）

用途：
- 将指定 pageId 的模板内容写死在代码中，避免在线拉取导致的结构差异与模糊替换错位
- 统一使用显式占位符 `{field_name}`，由 replace_variables 做精确替换

说明：
- 这里的字符串需保持 Confluence Storage Format 的 XHTML 结构（尤其是 <p> / <br />）
- 表格行区域用 `{issue_records}` / `{issue_list}` 等占位符承载，由代码生成 `<tr>...</tr>` 多行片段替换
"""

from __future__ import annotations

import re
from typing import Optional, Dict, List, Any


LOCAL_TEMPLATE_STORAGE: Dict[str, str] = {
    # 221989592: 测试用例评审模板（A）
    "221989592": r"""
<p><br /></p>
<h2><strong>基本信息：</strong></h2>
<table class="relative-table wrapped" style="width: 542.708px;"><colgroup><col style="width: 103.052px;" /><col style="width: 438.656px;" /></colgroup>
<tbody>
<tr>
<td class="highlight-green" style="text-align: center;vertical-align: middle;" colspan="1" data-highlight-colour="green">作者</td>
<td style="text-align: left;" colspan="1"><p>{author}<br /></p></td></tr>
<tr>
<td class="highlight-green" style="text-align: center;vertical-align: middle;" colspan="1" data-highlight-colour="green">部门</td>
<td style="text-align: left;" colspan="1"><p>{department}<br /></p></td></tr>
<tr>
<td class="highlight-green" style="text-align: center;vertical-align: middle;" colspan="1" data-highlight-colour="green">Feature名称</td>
<td style="text-align: left;" colspan="1"><p>{feature_name}<br /></p></td></tr>
<tr>
<td class="highlight-green" style="text-align: center;vertical-align: middle;" colspan="1" data-highlight-colour="green">三方对接开发Owner</td>
<td style="text-align: left;" colspan="1"><p>{third_party_owner}<br /></p></td></tr>
<tr>
<td class="highlight-green" style="text-align: center;vertical-align: middle;" colspan="1" data-highlight-colour="green">评审时间</td>
<td style="text-align: left;" colspan="1"><p>{review_time}<br /></p></td></tr>
<tr>
<td class="highlight-green" style="text-align: center;vertical-align: middle;" colspan="1" data-highlight-colour="green">评审结论</td>
<td style="text-align: left;" colspan="1">
<p>{review_conclusion}<br /></p>
<p>修改后重新评审：{re_review_after_modification}<br /></p>
</td></tr></tbody></table>
<table class="relative-table wrapped" style="width: 545.0px;"><colgroup><col style="width: 107.0px;" /><col style="width: 138.0px;" /><col style="width: 88.0px;" /><col style="width: 209.0px;" /></colgroup>
<tbody>
<tr>
<td class="highlight-green" style="text-align: left;" colspan="1" data-highlight-colour="green">被评用例路径</td>
<td style="text-align: left;" colspan="1"><p>{test_case_path}<br /></p></td>
<td class="highlight-green" style="text-align: left;" colspan="1" data-highlight-colour="green">评审人员</td>
<td style="text-align: left;" colspan="1">
<div class="content-wrapper">
<p>FDE: {reviewer_fde}</p>
<p>SE: {reviewer_se}</p>
<p>开发owner: {reviewer_dev_owner}</p>
<p>TM: {reviewer_tm}</p>
<p><br /></p>
<p><br /></p></div></td></tr>
<tr>
<td class="highlight-green" style="text-align: left;" colspan="1" data-highlight-colour="green">用例弱项洞察报告链接</td>
<td style="text-align: left;" colspan="1"><p>{weakness_report_link}<br /></p></td>
<td class="highlight-green" style="text-align: left;" colspan="1" data-highlight-colour="green">评审形式</td>
<td style="text-align: left;" colspan="1"><p>{review_form}<br /></p></td></tr>
<tr>
<td class="highlight-green" style="text-align: left;" colspan="1" data-highlight-colour="green">需求文档链接</td>
<td style="text-align: left;" colspan="1"><p>{requirement_doc_link}<br /></p></td>
<td class="highlight-green" style="text-align: left;" colspan="1" data-highlight-colour="green">评审时长（小时）</td>
<td style="text-align: left;" colspan="1"><p>{review_duration_hours}<br /></p></td></tr>
<tr>
<td class="highlight-green" style="text-align: left;" colspan="1" data-highlight-colour="green">需求矩阵链接</td>
<td style="text-align: left;" colspan="1"><p>{requirement_matrix_link}<br /></p></td>
<td class="highlight-green" style="text-align: left;" colspan="1" data-highlight-colour="green">评审规模<br title="" />(评审的文件个数)</td>
<td style="text-align: left;" colspan="1"><p>{review_scope_files}<br /></p></td></tr></tbody></table>
<h2><strong>问题记录</strong>：</h2>
<table class="relative-table wrapped" style="width: 1243.0px;"><colgroup><col style="width: 35.0px;" /><col style="width: 59.0px;" /><col style="width: 60.0px;" /><col style="width: 153.0px;" /><col style="width: 97.0px;" /><col style="width: 70.0px;" /><col style="width: 67.0px;" /><col style="width: 81.0px;" /><col style="width: 85.0px;" /><col style="width: 267.0px;" /><col style="width: 267.0px;" /></colgroup>
<tbody>
<tr>
<td class="highlight-#e3fcef" style="vertical-align: middle;text-align: center;" data-highlight-colour="#e3fcef"><strong>序号</strong></td>
<td class="highlight-#e3fcef" style="vertical-align: middle;text-align: center;" colspan="4" data-highlight-colour="#e3fcef"><strong>建议与改善</strong></td>
<td class="highlight-#e3fcef" style="vertical-align: middle;text-align: center;" data-highlight-colour="#e3fcef"><strong>提出人</strong></td>
<td class="highlight-#e3fcef" style="vertical-align: middle;text-align: center;" data-highlight-colour="#e3fcef"><strong>责任人</strong></td>
<td class="highlight-#e3fcef" style="vertical-align: middle;text-align: center;" data-highlight-colour="#e3fcef"><strong>完成情况</strong></td>
<td class="highlight-#e3fcef" style="vertical-align: middle;text-align: center;" data-highlight-colour="#e3fcef"><strong>完成时间</strong></td>
<td class="highlight-#e3fcef" style="vertical-align: middle;text-align: center;" data-highlight-colour="#e3fcef"><strong>评审单任务链接</strong></td>
<td class="highlight-#e3fcef" style="vertical-align: middle;text-align: center;" data-highlight-colour="#e3fcef"><strong title="">备注</strong></td></tr>
{issue_records}
</tbody></table>
""".strip(),

    # 521081686: 通用评审模板（B，含"问题记录(文件名)"）
    "521081686": r"""
<p><br /></p>
<h2><strong>基本信息：</strong></h2>
<table class="relative-table wrapped" style="width: 542.708px;"><colgroup><col style="width: 103.052px;" /><col style="width: 438.656px;" /></colgroup>
<tbody>
<tr>
<td class="highlight-green" style="text-align: center;vertical-align: middle;" colspan="1" data-highlight-colour="green">作者</td>
<td style="text-align: left;" colspan="1"><p>{author}<br /></p></td></tr>
<tr>
<td class="highlight-green" style="text-align: center;vertical-align: middle;" colspan="1" data-highlight-colour="green">部门</td>
<td style="text-align: left;" colspan="1"><p>{department}<br /></p></td></tr>
<tr>
<td class="highlight-green" style="text-align: center;vertical-align: middle;" colspan="1" data-highlight-colour="green">项目名称</td>
<td style="text-align: left;" colspan="1"><p>{project_name}<br /></p></td></tr>
<tr>
<td class="highlight-green" style="text-align: center;vertical-align: middle;" colspan="1" data-highlight-colour="green">测试人员</td>
<td style="text-align: left;" colspan="1"><p>{test_person}<br /></p></td></tr>
<tr>
<td class="highlight-green" style="text-align: center;vertical-align: middle;" colspan="1" data-highlight-colour="green">评审时间</td>
<td style="text-align: left;" colspan="1"><p>{review_time}<br /></p></td></tr>
<tr>
<td class="highlight-green" style="text-align: center;vertical-align: middle;" colspan="1" data-highlight-colour="green">评审结论</td>
<td style="text-align: left;" colspan="1"><p>{review_conclusion}<br /></p></td></tr>
</tbody></table>
<h2><strong>评审信息：</strong></h2>
<table class="relative-table wrapped" style="width: 545.0px;"><colgroup><col style="width: 107.0px;" /><col style="width: 438.0px;" /></colgroup>
<tbody>
<tr>
<td class="highlight-green" style="text-align: left;" colspan="1" data-highlight-colour="green">被评代码或文档路径</td>
<td style="text-align: left;" colspan="1"><p>{assessed_code_path}<br /></p></td></tr>
<tr>
<td class="highlight-green" style="text-align: left;" colspan="1" data-highlight-colour="green">评审人员</td>
<td style="text-align: left;" colspan="1"><p>{reviewers}<br /></p></td></tr>
<tr>
<td class="highlight-green" style="text-align: left;" colspan="1" data-highlight-colour="green">方案设计文档链接</td>
<td style="text-align: left;" colspan="1"><p>{design_doc_link}<br /></p></td></tr>
<tr>
<td class="highlight-green" style="text-align: left;" colspan="1" data-highlight-colour="green">评审形式</td>
<td style="text-align: left;" colspan="1"><p>{review_form}<br /></p></td></tr>
<tr>
<td class="highlight-green" style="text-align: left;" colspan="1" data-highlight-colour="green">需求矩阵链接</td>
<td style="text-align: left;" colspan="1"><p>{requirement_matrix_link}<br /></p></td></tr>
<tr>
<td class="highlight-green" style="text-align: left;" colspan="1" data-highlight-colour="green">评审时长（小时）</td>
<td style="text-align: left;" colspan="1"><p>{review_duration_hours}<br /></p></td></tr>
<tr>
<td class="highlight-green" style="text-align: left;" colspan="1" data-highlight-colour="green">自测用例&自测报告链接</td>
<td style="text-align: left;" colspan="1"><p>{self_test_links}<br /></p></td></tr>
<tr>
<td class="highlight-green" style="text-align: left;" colspan="1" data-highlight-colour="green">评审规模（评审的文件个数）</td>
<td style="text-align: left;" colspan="1"><p>{review_scope_files}<br /></p></td></tr>
</tbody></table>
<h2><strong>问题记录：</strong></h2>
<table class="relative-table wrapped" style="width: 1243.0px;"><colgroup><col style="width: 35.0px;" /><col style="width: 59.0px;" /><col style="width: 60.0px;" /><col style="width: 153.0px;" /><col style="width: 97.0px;" /><col style="width: 70.0px;" /><col style="width: 67.0px;" /><col style="width: 81.0px;" /><col style="width: 85.0px;" /><col style="width: 267.0px;" /></colgroup>
<tbody>
<tr>
<td class="highlight-#e3fcef" style="vertical-align: middle;text-align: center;" data-highlight-colour="#e3fcef"><strong>序号</strong></td>
<td class="highlight-#e3fcef" style="vertical-align: middle;text-align: center;" data-highlight-colour="#e3fcef"><strong>文件名</strong></td>
<td class="highlight-#e3fcef" style="vertical-align: middle;text-align: center;" colspan="4" data-highlight-colour="#e3fcef"><strong>建议/改善</strong></td>
<td class="highlight-#e3fcef" style="vertical-align: middle;text-align: center;" data-highlight-colour="#e3fcef"><strong>提出人</strong></td>
<td class="highlight-#e3fcef" style="vertical-align: middle;text-align: center;" data-highlight-colour="#e3fcef"><strong>评审时间</strong></td>
<td class="highlight-#e3fcef" style="vertical-align: middle;text-align: center;" data-highlight-colour="#e3fcef"><strong>整改责任人</strong></td>
<td class="highlight-#e3fcef" style="vertical-align: middle;text-align: center;" data-highlight-colour="#e3fcef"><strong>完成情况</strong></td>
<td class="highlight-#e3fcef" style="vertical-align: middle;text-align: center;" data-highlight-colour="#e3fcef"><strong title="">备注</strong></td></tr>
{issue_records}
</tbody></table>
""".strip(),

    # 310457377: 会议纪要模板（灰色大表格，会议信息+问题列表）
    "310457377": r"""
<h1>会议纪要</h1>
<table class="relative-table wrapped">
<tbody>
<tr>
<td class="highlight-grey" style="text-align: left;" colspan="8" data-highlight-colour="grey">
<p title=""><strong>会议主题：<span>{meeting_subject}</span>评审</strong></p></td></tr>
<tr>
<td style="text-align: left;"><p><strong>参加人员</strong></p></td>
<td style="text-align: left;" colspan="7"><p>{participants}</p></td></tr>
<tr>
<td style="text-align: left;"><p><strong>会议地点</strong></p></td>
<td style="text-align: left;" colspan="7"><p>{meeting_location}</p></td></tr>
<tr>
<td style="text-align: left;"><p><strong>会议主持</strong></p></td>
<td style="text-align: left;" colspan="7"><p>{meeting_host}（<span>*</span>被评审人）</p></td></tr>
<tr>
<td style="text-align: left;"><p><strong>会议记录</strong></p></td>
<td style="text-align: left;" colspan="7"><p>{meeting_recorder}（<span>*</span>被评审人）</p></td></tr>
<tr>
<td class="highlight-grey" style="text-align: center;" data-highlight-colour="grey"><p title=""><strong>序号</strong></p></td>
<td class="highlight-grey" style="text-align: center;" data-highlight-colour="grey"><p title=""><strong>*</strong><strong>问题列表</strong></p></td>
<td class="highlight-grey" style="text-align: center;" data-highlight-colour="grey"><p title=""><strong>*</strong><strong>提出人</strong></p></td>
<td class="highlight-grey" style="text-align: center;" data-highlight-colour="grey"><p title=""><strong>*</strong><strong>责任人</strong></p></td>
<td class="highlight-grey" style="text-align: center;" data-highlight-colour="grey"><p title=""><strong>*</strong><strong>记录时间</strong></p></td>
<td class="highlight-grey" style="text-align: center;" data-highlight-colour="grey"><p title=""><strong>*</strong><strong>完成时间</strong></p></td>
<td class="highlight-grey" style="text-align: center;" data-highlight-colour="grey"><p title=""><strong>*</strong><strong>完成情况</strong></p></td>
<td class="highlight-grey" style="text-align: center;" data-highlight-colour="grey"><p title=""><strong>备注</strong></p></td></tr>
{issue_list}
</tbody></table>
""".strip(),

    # SUMMARY_DOC: 总结文档模板（支持多级章节、表格、图片、自动目录）
    "SUMMARY_DOC": r"""
<h1 style="color: #0052CC; border-bottom: 3px solid #0052CC; padding-bottom: 15px;"><strong>{document_title}</strong></h1>
<p style="font-size: 14px; color: #666; margin-bottom: 20px;">创建时间：{create_date} | 作者：{author} | 版本：{version}<br /></p>

<h2 style="color: #0052CC; border-bottom: 2px solid #0052CC; padding-bottom: 10px; margin-top: 30px;">摘要</h2>
<p style="font-size: 15px; line-height: 1.6; color: #333;">{summary_content}<br /></p>

{table_of_contents}

{chapters_content}

<h2 style="color: #0052CC; border-bottom: 2px solid #0052CC; padding-bottom: 10px; margin-top: 30px;">总结</h2>
<p style="font-size: 15px; line-height: 1.6; color: #333;">{conclusion_content}<br /></p>
""".strip(),

    # TEST_GUIDE: 测试指导模板
    "TEST_GUIDE": r"""
<table class="relative-table" style="width: 680.0px;">
<thead>
<tr>
<th style="text-align: left;">Version</th>
<td style="text-align: left;">{version}</td></tr></thead><colgroup><col style="width: 100.0px;" /><col style="width: 579.0px;" /></colgroup>
<tbody>
<tr>
<th style="text-align: left;">Status</th>
<td style="text-align: left;">
<div class="content-wrapper">
<p>{status}</p></div></td></tr>
<tr>
<th style="text-align: left;">Date</th>
<td style="text-align: left;">
<div class="content-wrapper">
<p>{date}&nbsp;</p></div></td></tr>
<tr>
<th style="text-align: left;">Creator</th>
<td style="text-align: left;">
<div class="content-wrapper">
<p>{creator}&nbsp;</p></div></td></tr>
<tr>
<th style="text-align: left;">Reviewer</th>
<td style="text-align: left;">
<div class="content-wrapper">
<p><span>{reviewer}</span></p></div></td></tr>
<tr>
<th style="text-align: left;">Approval</th>
<td style="text-align: left;">
<div class="content-wrapper">
<p>{approval}&nbsp;</p></div></td></tr>
<tr>
<th style="text-align: left;">Scope of application</th>
<td style="text-align: left;">{scope_of_application}</td></tr></tbody></table>
<table class="relative-table" style="width: 1278.0px;"><colgroup><col style="width: 98.0px;" /><col style="width: 213.0px;" /><col style="width: 213.0px;" /><col style="width: 251.0px;" /><col style="width: 251.0px;" /><col style="width: 251.0px;" /></colgroup>
<thead>
<tr>
<th style="text-align: center;">
<p>Version</p></th>
<th style="text-align: center;">
<p>Summary of the revisions</p></th>
<th style="text-align: center;">
<p>Date</p></th>
<th style="text-align: center;">
<p>Creator</p></th>
<th style="text-align: center;">
<p><strong>Reviewed by</strong></p></th>
<th style="text-align: center;">
<p><strong>Reviewed Date</strong></p></th></tr></thead>
<tbody>
{revision_history}
<tr>
<td style="text-align: left;"><br /></td>
<td style="text-align: left;"><br /></td>
<td style="text-align: left;"><br /></td>
<td style="text-align: left;"><br /></td>
<td style="text-align: left;"><br /></td>
<td style="text-align: left;"><br /></td></tr></tbody></table>
<p><br /></p>
{table_of_contents}
{test_instructions}
""".strip(),
}


def get_local_template_storage(page_id: str) -> Optional[str]:
    return LOCAL_TEMPLATE_STORAGE.get(str(page_id))


def _generate_anchor_id(title: str, index: int) -> str:
    """生成锚点ID"""
    # 清理标题，生成有效的ID（保留中文、英文、数字）
    anchor = re.sub(r'[^\w\u4e00-\u9fff]', '_', title)
    anchor = re.sub(r'_+', '_', anchor)  # 合并多个下划线
    anchor = anchor.strip('_')
    if not anchor:
        anchor = f"section_{index}"
    return anchor


def _generate_anchor_macro(anchor_id: str) -> str:
    """生成Confluence Anchor宏（完整格式，包含schema-version和macro-id，包装在p标签中）"""
    import uuid
    macro_id = str(uuid.uuid4())
    return f'<p><ac:structured-macro ac:name="anchor" ac:schema-version="1" ac:macro-id="{macro_id}"><ac:parameter ac:name="">{anchor_id}</ac:parameter></ac:structured-macro></p>'


def generate_table_of_contents(chapters: List[Dict[str, Any]], index_map: Dict[str, int] = None) -> str:
    """
    生成浮动目录（Float TOC），使用Confluence内置的浮动目录宏，自动识别标题并支持跳转
    
    Args:
        chapters: 章节列表（用于检查是否有章节）
        index_map: 章节索引映射（未使用，保留以兼容接口）
    
    Returns:
        目录的HTML内容（使用Confluence浮动目录宏）
    """
    # 检查是否有章节
    if not chapters:
        return ""
    
    # 使用Confluence内置的浮动目录宏（float_toc），它会自动扫描页面中的标题并生成可跳转的浮动目录
    import uuid
    toc_macro_id = str(uuid.uuid4())
    toc_html = f'<h1><strong><ac:structured-macro ac:name="float_toc" ac:schema-version="1" ac:macro-id="{toc_macro_id}"><ac:parameter ac:name="Hidable">false</ac:parameter><ac:parameter ac:name="Maxlvl">4</ac:parameter></ac:structured-macro></strong></h1>'
    
    return toc_html


def _build_chapter_index_map(chapters: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    构建章节索引映射
    
    Args:
        chapters: 章节列表
    
    Returns:
        索引映射 {path: index}
    """
    index_map = {}
    index_counter = {"count": 0}
    
    def traverse_chapters(chapter_list: List[Dict], parent_path: str = ""):
        for chapter in chapter_list:
            title = chapter.get("title", "")
            if not title:
                continue
            
            current_path = f"{parent_path}/{title}" if parent_path else title
            index_map[current_path] = index_counter["count"]
            index_counter["count"] += 1
            
            sections = chapter.get("sections", [])
            if sections:
                traverse_chapters(sections, current_path)
    
    traverse_chapters(chapters)
    return index_map


def generate_summary_doc_chapters(chapters: List[Dict[str, Any]], generate_toc: bool = True) -> tuple[str, str]:
    """
    生成总结文档的章节内容（同时生成目录）
    
    Args:
        chapters: 章节列表，每个章节包含：
            - title: 章节标题
            - level: 标题级别 (1-6，对应 h1-h6)
            - content: 章节正文内容（可选）
            - sections: 子章节列表（可选）
            - tables: 表格数据列表（可选）
            - images: 图片列表（可选）
        generate_toc: 是否生成目录
    
    Returns:
        (toc_html, chapters_html) 元组
    """
    # 构建索引映射（确保目录和章节使用相同的索引）
    index_map = _build_chapter_index_map(chapters)
    
    # 生成目录（使用索引映射）
    toc_html = ""
    if generate_toc:
        toc_html = generate_table_of_contents(chapters, index_map)
    
    html_parts = []
    chapter_index = {"count": 0}  # 章节索引计数器（与索引映射保持一致）
    
    def process_chapter(chapter: Dict, parent_path: str = ""):
        """递归处理章节"""
        title = chapter.get("title", "")
        if not title:
            return
        
        level = max(1, min(6, int(chapter.get("level", 2))))
        content = chapter.get("content", "")
        sections = chapter.get("sections", [])
        tables = chapter.get("tables", [])
        images = chapter.get("images", [])
        
        # 生成唯一路径
        current_path = f"{parent_path}/{title}" if parent_path else title
        # 从索引映射中获取索引（与目录生成保持一致）
        index = index_map.get(current_path, chapter_index["count"])
        chapter_index["count"] += 1
        
        # 生成锚点ID
        anchor_id = _generate_anchor_id(title, index)
        
        # 生成标题样式
        # 如果是子章节（有parent_path），使用更大的margin-top来与父章节内容区分
        is_subchapter = bool(parent_path)
        
        if level == 1:
            margin_top = "50px" if is_subchapter else "30px"
            title_style = f"color: #0052CC; border-bottom: 3px solid #0052CC; padding-bottom: 15px; margin-top: {margin_top};"
        elif level == 2:
            margin_top = "50px" if is_subchapter else "30px"
            title_style = f"color: #0052CC; border-bottom: 2px solid #0052CC; padding-bottom: 10px; margin-top: {margin_top};"
        elif level == 3:
            margin_top = "40px" if is_subchapter else "30px"
            title_style = f"color: #0052CC; border-bottom: 2px solid #0052CC; padding-bottom: 10px; margin-top: {margin_top};"
        elif level >= 4:
            margin_top = "30px" if is_subchapter else "20px"
            title_style = f"color: #333; margin-top: {margin_top};"
        
        # 生成标题HTML，并在标题前添加锚点宏以支持目录跳转
        anchor_macro = _generate_anchor_macro(anchor_id)
        title_html = f'{anchor_macro}<h{level} style="{title_style}"><strong>{title}</strong></h{level}>'
        html_parts.append(title_html)
        
        # 添加正文内容（支持占位符精确位置插入）
        if content:
            # 创建表格和图片的字典索引（通过ID）
            tables_dict = {table.get("id", ""): table for table in tables}
            images_dict = {image.get("id", ""): image for image in images}
            
            # 处理包含占位符的正文内容
            processed_content = _process_content_with_placeholders(
                content, tables_dict, images_dict
            )
            html_parts.append(processed_content)
        
        # 递归处理子章节
        if sections:
            for subchapter in sections:
                process_chapter(subchapter, current_path)
    
    # 处理所有章节
    for chapter in chapters:
        process_chapter(chapter)
    
    chapters_html = '\n'.join(html_parts)
    return toc_html, chapters_html


def _process_content_with_placeholders(content: str, tables_dict: Dict[str, Dict], images_dict: Dict[str, Dict]) -> str:
    """
    处理包含占位符的正文内容，在占位符位置插入对应的HTML
    
    Args:
        content: 正文内容（包含占位符）
        tables_dict: 表格字典 {id: table_data}
        images_dict: 图片字典 {id: image_data}
    
    Returns:
        处理后的HTML内容
    """
    # 匹配占位符： [表格:table_<uuid>] 或 [图片:image_<uuid>]
    pattern = r'\[(表格|图片):(table_|image_)([a-f0-9\-]+)\]'
    
    # 如果没有占位符，直接处理整个内容
    if not re.search(pattern, content):
        if content.strip():
            text_html = content.replace("\n", "<br />")
            return f'<p style="font-size: 15px; line-height: 1.6; color: #333; margin-top: 10px;">{text_html}</p>'
        return ""
    
    parts = []
    last_pos = 0
    last_was_placeholder = False  # 跟踪最后添加的是否为占位符（图片/表格）
    
    for match in re.finditer(pattern, content):
        # 添加占位符前的文本
        text_before = content[last_pos:match.start()]
        
        if text_before.strip():
            # 处理换行：将多个连续换行合并为单个<br />
            text_html = re.sub(r'\n+', '<br />', text_before.strip())
            parts.append(f'<p style="font-size: 15px; line-height: 1.6; color: #333; margin-top: 10px;">{text_html}</p>')
            last_was_placeholder = False
        elif text_before and not text_before.strip():
            # 如果只有空白或换行（没有实际文本），但这是在占位符之间
            # 需要添加换行分隔，避免图片和表格紧挨着
            # 添加一个空段落来保持间距
            parts.append('<p><br /></p>')
            last_was_placeholder = False
        
        placeholder_type = match.group(1)
        item_id = match.group(3)
        
        if placeholder_type == "表格":
            table = tables_dict.get(item_id)
            if table:
                parts.append(_generate_table_html(table))
                last_was_placeholder = True
        elif placeholder_type == "图片":
            image = images_dict.get(item_id)
            if image:
                image_html = _generate_image_html(image)
                parts.append(image_html)
                last_was_placeholder = True
        
        last_pos = match.end()
    
    # 添加最后一段文本
    text_after = content[last_pos:]
    if text_after.strip():
        text_html = re.sub(r'\n+', '<br />', text_after.strip())
        parts.append(f'<p style="font-size: 15px; line-height: 1.6; color: #333; margin-top: 10px;">{text_html}</p>')
        last_was_placeholder = False
    
    # 如果最后添加的是图片或表格，添加多个换行段落，确保与下一个章节有足够的间距
    if last_was_placeholder:
        # 添加多个空段落，确保子章节标题有足够的间距
        parts.append('<p><br /></p>')
        parts.append('<p><br /></p>')
    
    return '\n'.join(parts)


def _generate_image_html(image: Dict) -> str:
    """生成图片HTML（强制使用居中，避免左对齐导致的换行问题）"""
    filename = image.get("filename", "")
    width = image.get("width", 600)
    # 强制使用居中，忽略用户选择的对齐方式，避免左对齐导致的换行问题
    align = "center"
    if filename:
        return f'''<p><ac:image ac:align="{align}" ac:width="{width}">
<ri:attachment ri:filename="{filename}" />
</ac:image></p>'''
    return ""


def _generate_table_html(table: Dict) -> str:
    """生成表格HTML（支持合并单元格）"""
    headers = table.get("headers", [])
    rows = table.get("rows", [])
    if not headers:
        return ""
    
    table_html = ['<table class="relative-table wrapped" style="width: 100%; margin-top: 15px; margin-bottom: 15px;"><tbody>']
    
    # 表头（支持合并单元格）
    # 计算标题行的实际列数（考虑合并单元格的colspan）
    actual_header_cols = sum(header.get("colspan", 1) for header in headers)
    max_cols = actual_header_cols  # 使用实际列数
    processed_header = [False] * max_cols
    header_row = '<tr>'
    col_idx = 0
    
    for header in headers:
        # 跳过被合并的列
        while col_idx < max_cols and processed_header[col_idx]:
            col_idx += 1
        if col_idx >= max_cols:
            break
        
        header_text = header.get("text", "")
        header_style = header.get("style", "")
        header_bg = header.get("background_color", "#e3fcef")
        rowspan = header.get("rowspan", 1)
        colspan = header.get("colspan", 1)
        
        # 标记被合并的列
        for c in range(col_idx, min(col_idx + colspan, max_cols)):
            processed_header[c] = True
        
        # 构建单元格属性
        attrs = []
        if rowspan > 1:
            attrs.append(f'rowspan="{rowspan}"')
        if colspan > 1:
            attrs.append(f'colspan="{colspan}"')
        attr_str = ' ' + ' '.join(attrs) if attrs else ''
        
        if not header_style:
            header_style = f'class="highlight-{header_bg}" style="text-align: center; vertical-align: middle;" data-highlight-colour="{header_bg}"'
        
        escaped_text = (
            header_text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
        )
        
        header_row += f'<td{attr_str} {header_style}><strong>{escaped_text}</strong></td>'
        col_idx += colspan
    
    header_row += '</tr>'
    table_html.append(header_row)
    
    # 数据行（支持合并单元格）
    # 使用二维数组跟踪哪些单元格已经被合并
    processed = [[False for _ in range(max_cols)] for _ in range(len(rows))]
    
    for i, row in enumerate(rows):
        row_html = '<tr>'
        col_idx = 0
        for cell_data in row:
            # 跳过已处理的单元格（被合并的单元格）
            while col_idx < max_cols and processed[i][col_idx]:
                col_idx += 1
            
            if col_idx >= max_cols:
                break
            
            # 支持新的单元格数据结构（字典）
            if isinstance(cell_data, dict):
                cell_text = cell_data.get("text", "")
                rowspan = cell_data.get("rowspan", 1)
                colspan = cell_data.get("colspan", 1)
            else:
                # 兼容旧格式（纯文本）
                cell_text = str(cell_data) if cell_data else ""
                rowspan = 1
                colspan = 1
            
            # 标记被合并的单元格为已处理
            for r in range(i, min(i + rowspan, len(rows))):
                for c in range(col_idx, min(col_idx + colspan, max_cols)):
                    processed[r][c] = True
            
            # 构建单元格属性
            attrs = []
            if rowspan > 1:
                attrs.append(f'rowspan="{rowspan}"')
            if colspan > 1:
                attrs.append(f'colspan="{colspan}"')
            attr_str = ' ' + ' '.join(attrs) if attrs else ''
            
            cell_style = 'style="text-align: left; vertical-align: middle;"'
            escaped_text = (
                cell_text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
            )
            row_html += f'<td{attr_str} {cell_style}><p>{escaped_text}<br /></p></td>'
            
            col_idx += colspan
        
        row_html += '</tr>'
        table_html.append(row_html)
    
    table_html.append('</tbody></table>')
    return ''.join(table_html)
