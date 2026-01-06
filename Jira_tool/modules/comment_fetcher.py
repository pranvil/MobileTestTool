"""
查询评论业务逻辑
"""
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional
import hashlib
import mimetypes
import re

import requests
import urllib3
from urllib.parse import urlparse

from Jira_tool.jira_client import get_comments, get_issue
from core.jira_config_manager import get_jira_url, get_token
from Jira_tool.core.paths import get_comments_output_path
from core.debug_logger import logger
from Jira_tool.core.exceptions import JiraAPIError, FileError

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


_IMG_SRC_RE = re.compile(r'(<img\b[^>]*?\bsrc=["\'])([^"\']+)(["\'])', re.IGNORECASE)


def _to_absolute_url(url_or_path: str) -> str:
    if not url_or_path:
        return url_or_path
    if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
        return url_or_path
    if url_or_path.startswith("data:") or url_or_path.startswith("cid:"):
        return url_or_path
    base = get_jira_url().rstrip("/")
    if url_or_path.startswith("/"):
        return f"{base}{url_or_path}"
    return f"{base}/{url_or_path}"


def _guess_ext(url: str, content_type: Optional[str]) -> str:
    ext = ""
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        ext = mimetypes.guess_extension(ct) or ""
    if not ext:
        try:
            ext = Path(urlparse(url).path).suffix or ""
        except Exception:
            ext = ""
    return ext if ext else ".bin"


def _download_to_assets(url: str, assets_dir: Path, timeout: int = 30) -> Optional[str]:
    """
    下载图片到 assets_dir，返回保存后的文件名；失败返回 None
    """
    token = get_token().strip()
    if not token:
        logger.warning("未配置 API Token，无法下载评论图片")
        return None

    abs_url = _to_absolute_url(url)
    if abs_url.startswith("data:") or abs_url.startswith("cid:"):
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "*/*",
        "User-Agent": "JiraAutomationTool/1.0",
    }

    try:
        resp = requests.get(abs_url, headers=headers, verify=False, timeout=timeout, allow_redirects=True)
        if resp.status_code >= 400:
            logger.warning(f"下载图片失败: {resp.status_code} | {abs_url}")
            return None

        ext = _guess_ext(abs_url, resp.headers.get("Content-Type"))
        name = hashlib.sha1(abs_url.encode("utf-8")).hexdigest()[:16] + ext
        out_path = assets_dir / name
        out_path.write_bytes(resp.content)
        return name
    except Exception as e:
        logger.warning(f"下载图片异常: {e} | {abs_url}")
        return None


def _rewrite_img_src_to_local(body_html: str, assets_dir: Path) -> str:
    """
    将 body_html 中的 <img src="..."> 下载到本地并改写为相对路径
    """
    if not body_html:
        return body_html

    def repl(m: re.Match) -> str:
        prefix, src, suffix = m.group(1), m.group(2), m.group(3)
        if not src or src.startswith("data:") or src.startswith("cid:"):
            return m.group(0)

        saved = _download_to_assets(src, assets_dir)
        if not saved:
            return m.group(0)

        # 相对引用，便于浏览器和 QTextBrowser 共同加载
        rel = f"{assets_dir.name}/{saved}"
        return f"{prefix}{rel}{suffix}"

    return _IMG_SRC_RE.sub(repl, body_html)


def fetch_comments_to_html(issue_key: str, download_images: bool = True) -> Tuple[bool, str, str]:
    """
    获取Issue评论并生成HTML文件
    
    Args:
        issue_key: Issue Key（如 'GF65DISH-1347'）
        download_images: 是否尝试下载评论中的图片到本地（方案2）
    
    Returns:
        (success, message, file_path)
        - success: 是否成功
        - message: 消息
        - file_path: 生成的HTML文件路径（成功时）或错误信息（失败时）
    """
    logger.info(f"开始获取Issue评论: {issue_key}")
    
    try:
        # 获取Issue信息（包括描述）
        issue_data = get_issue(issue_key)
        issue_fields = issue_data.get("fields", {})
        description = issue_fields.get("description", "")
        summary = issue_fields.get("summary", issue_key)
        
        # 获取评论数据
        response = get_comments(issue_key)
        comments = response.get("comments", [])
        
        logger.info(f"获取到 {len(comments)} 条评论")

        output_dir = get_comments_output_path()
        assets_dir = output_dir / f"{issue_key}_assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        
        # 处理描述中的图片
        if download_images and description:
            description = _rewrite_img_src_to_local(description, assets_dir)
        
        # 创建HTML内容
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Issue {issue_key} 评论汇总</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #0052CC;
            padding-bottom: 10px;
        }}
        .description-box {{
            border: 1px solid #0052CC;
            margin-bottom: 30px;
            padding: 15px;
            border-radius: 5px;
            background-color: #f0f7ff;
        }}
        .description-title {{
            color: #0052CC;
            font-size: 1.1em;
            font-weight: bold;
            margin-bottom: 10px;
            border-bottom: 1px solid #0052CC;
            padding-bottom: 5px;
        }}
        .description-body {{
            margin-top: 10px;
        }}
        .comment-box {{
            border: 1px solid #ddd;
            margin-bottom: 20px;
            padding: 15px;
            border-radius: 5px;
            background-color: #fafafa;
        }}
        .meta {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
            border-bottom: 1px solid #eee;
            padding-bottom: 5px;
        }}
        .meta strong {{
            color: #333;
        }}
        /* 还原 JEditor 表格的基本样式 */
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-top: 10px;
        }}
        th, td {{
            border: 1px solid #999;
            padding: 5px;
            text-align: left;
            font-size: 12px;
        }}
        th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
        .comment-body {{
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Issue: {issue_key} - {summary}</h1>
        <p>共 {len(comments)} 条评论，生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
"""
        
        # 添加描述部分
        if description:
            html_content += f"""
        <div class="description-box">
            <div class="description-title">Issue 描述</div>
            <div class="description-body">{description}</div>
        </div>
"""
        
        # 添加评论标题
        if comments:
            html_content += """
        <h2 style="color: #333; margin-top: 30px; border-bottom: 1px solid #ddd; padding-bottom: 10px;">评论列表</h2>
"""
        
        # 拼接评论内容
        for idx, comment in enumerate(comments, 1):
            author = comment.get("author", {}).get("displayName", "未知")
            created = comment.get("created", "")
            body = comment.get("body", "")

            if download_images:
                body = _rewrite_img_src_to_local(body, assets_dir)
            
            html_content += f"""
        <div class="comment-box">
            <div class="meta">#{idx} - <strong>{author}</strong> - {created}</div>
            <div class="comment-body">{body}</div>
        </div>
"""
        
        html_content += """
    </div>
</body>
</html>
"""
        
        # 保存文件
        filename = f"{issue_key}_comments.html"
        file_path = output_dir / filename
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info(f"HTML文件已保存: {file_path}")
        desc_msg = "（包含描述）" if description else ""
        return True, f"成功！已生成 {len(comments)} 条评论{desc_msg}", str(file_path)
    
    except JiraAPIError as e:
        error_msg = f"JIRA API错误: {e}"
        logger.error(error_msg)
        return False, error_msg, str(e)
    except Exception as e:
        error_msg = f"生成HTML文件失败: {e}"
        logger.exception(error_msg)
        return False, error_msg, str(e)

