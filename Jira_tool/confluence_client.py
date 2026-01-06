"""
Confluence API 客户端封装
"""
import requests
import urllib3
import ssl
from pathlib import Path
from typing import Dict, Any, Optional, List
from requests.adapters import HTTPAdapter
from core.jira_config_manager import get_confluence_url, get_confluence_token
from Jira_tool.core.exceptions import ConfluenceAPIError
from core.debug_logger import logger

# 屏蔽 SSL 证书警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class LegacySSLAdapter(HTTPAdapter):
    """支持旧式SSL重新协商的适配器"""
    def init_poolmanager(self, *args, **kwargs):
        # 创建SSL上下文，允许旧式重新协商
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        # 允许旧式SSL重新协商 (OP_LEGACY_SERVER_CONNECT = 0x4)
        try:
            if hasattr(ssl, 'OP_LEGACY_SERVER_CONNECT'):
                ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
            else:
                ctx.options |= 0x4
        except Exception:
            pass
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)


class ConfluenceClient:
    """Confluence API 客户端"""
    
    def __init__(self, base_url: str = None, token: str = None):
        self.base_url = (base_url or get_confluence_url()).rstrip('/')
        self.token = token or get_confluence_token()
        self.session = requests.Session()
        self.session.verify = False  # 跳过SSL验证（内网自签名证书）
        self.session.mount('https://', LegacySSLAdapter())
    
    def _get_headers(self, content_type: str = "application/json") -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        发送HTTP请求
        
        Args:
            method: HTTP方法（GET, POST等）
            endpoint: API端点（如 '/rest/api/content'）
            **kwargs: 其他请求参数
        
        Returns:
            JSON响应数据
        
        Raises:
            ConfluenceAPIError: API调用失败时抛出
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                **kwargs
            )
            
            if response.status_code >= 400:
                error_msg = f"Confluence API错误: {response.status_code}"
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_msg += f" - {error_data['message']}"
                    elif 'data' in error_data:
                        error_msg += f" - {error_data['data']}"
                except:
                    error_msg += f" - {response.text[:200]}"
                
                logger.error(f"{error_msg} | URL: {url}")
                raise ConfluenceAPIError(
                    error_msg,
                    status_code=response.status_code,
                    response_text=response.text
                )
            
            if response.status_code == 204:  # No Content
                return {}
            
            return response.json()
        
        except ConfluenceAPIError:
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {e} | URL: {url}")
            raise ConfluenceAPIError(f"网络请求失败: {e}")
        except Exception as e:
            logger.error(f"未知错误: {e} | URL: {url}")
            raise ConfluenceAPIError(f"未知错误: {e}")
    
    def get_space(self, space_key: str) -> Dict[str, Any]:
        """
        获取空间信息
        
        Args:
            space_key: 空间Key（如 'USVAL'）
        
        Returns:
            空间信息字典
        
        Raises:
            ConfluenceAPIError: API调用失败时抛出
        """
        logger.debug(f"获取空间信息: {space_key}")
        return self._request("GET", f"/rest/api/space/{space_key}", params={'expand': 'homepage'})
    
    def get_page_by_id(self, page_id: str, expand: str = "body.storage,version") -> Dict[str, Any]:
        """
        根据ID获取页面信息
        
        Args:
            page_id: 页面ID
            expand: 需要展开的字段，默认包含body.storage和version
        
        Returns:
            页面信息字典
        
        Raises:
            ConfluenceAPIError: API调用失败时抛出
        """
        logger.debug(f"获取页面信息: {page_id}")
        return self._request("GET", f"/rest/api/content/{page_id}", params={'expand': expand})
    
    def get_page_content(self, page_id: str) -> str:
        """
        获取页面内容（Storage Format）
        
        Args:
            page_id: 页面ID
        
        Returns:
            页面内容的HTML字符串（Storage Format）
        
        Raises:
            ConfluenceAPIError: API调用失败时抛出
        """
        logger.debug(f"获取页面内容: {page_id}")
        page_data = self.get_page_by_id(page_id, expand="body.storage")
        body = page_data.get('body', {})
        storage = body.get('storage', {})
        return storage.get('value', '')
    
    def get_page_children(self, page_id: str, limit: int = 100) -> list:
        """
        获取页面的子页面
        
        Args:
            page_id: 父页面ID
            limit: 返回数量限制
        
        Returns:
            子页面列表
        
        Raises:
            ConfluenceAPIError: API调用失败时抛出
        """
        logger.debug(f"获取子页面: {page_id}")
        params = {
            'expand': 'children.page,version',
            'limit': limit
        }
        response = self._request("GET", f"/rest/api/content/{page_id}/child/page", params=params)
        return response.get('results', [])
    
    def create_page(
        self,
        title: str,
        content: str,
        space_key: str,
        parent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建页面
        
        Args:
            title: 页面标题
            content: 页面内容（Storage Format HTML）
            space_key: 空间Key
            parent_id: 父页面ID（可选，如果提供则创建为子页面）
        
        Returns:
            创建的页面信息
        
        Raises:
            ConfluenceAPIError: API调用失败时抛出
        """
        logger.debug(f"创建页面: {title} (空间: {space_key}, 父页面: {parent_id})")
        
        payload = {
            "type": "page",
            "title": title,
            "space": {
                "key": space_key
            },
            "body": {
                "storage": {
                    "value": content,
                    "representation": "storage"
                }
            }
        }
        
        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]
        
        return self._request("POST", "/rest/api/content", json=payload)

    def update_page(
        self,
        page_id: str,
        title: str,
        content: str,
        current_version: int,
        minor_edit: bool = True,
    ) -> Dict[str, Any]:
        """
        更新页面内容（Storage Format）

        Args:
            page_id: 页面ID
            title: 页面标题（Confluence 更新接口需要携带 title）
            content: 页面内容（Storage Format HTML）
            current_version: 当前版本号（将自动 +1）
            minor_edit: 是否作为小改动（不通知关注者/减少噪音，具体行为依 Confluence 配置）

        Returns:
            更新后的页面信息
        """
        logger.debug(f"更新页面: {page_id} (version: {current_version} -> {current_version + 1})")
        payload = {
            "id": page_id,
            "type": "page",
            "title": title,
            "version": {"number": int(current_version) + 1, "minorEdit": bool(minor_edit)},
            "body": {"storage": {"value": content, "representation": "storage"}},
        }
        return self._request("PUT", f"/rest/api/content/{page_id}", json=payload)
    
    def get_page_attachments(self, page_id: str) -> List[Dict[str, Any]]:
        """
        获取页面的附件列表
        
        Args:
            page_id: 页面ID
        
        Returns:
            附件列表，每个附件包含id、title、_links等信息
        
        Raises:
            ConfluenceAPIError: API调用失败时抛出
        """
        logger.debug(f"获取页面附件列表: {page_id}")
        params = {
            "expand": "version"
        }
        response = self._request("GET", f"/rest/api/content/{page_id}/child/attachment", params=params)
        return response.get('results', [])
    
    def delete_attachment(self, page_id: str, attachment_id: str) -> None:
        """
        删除页面附件
        
        Args:
            page_id: 页面ID
            attachment_id: 附件ID
        
        Raises:
            ConfluenceAPIError: API调用失败时抛出
        """
        logger.debug(f"删除附件: {attachment_id} (页面: {page_id})")
        self._request("DELETE", f"/rest/api/content/{page_id}/child/attachment/{attachment_id}")
    
    def upload_attachment(
        self,
        page_id: str,
        file_path: str,
        comment: str = ""
    ) -> Dict[str, Any]:
        """
        上传附件到页面
        
        Args:
            page_id: 页面ID
            file_path: 文件路径
            comment: 附件注释（可选）
        
        Returns:
            上传后的附件信息
        
        Raises:
            ConfluenceAPIError: API调用失败时抛出
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise ConfluenceAPIError(f"文件不存在: {file_path}")
        
        filename = file_path_obj.name
        logger.debug(f"上传附件到页面 {page_id}: {filename}")
        
        # 检查是否存在同名附件，如果存在则先删除
        try:
            attachments = self.get_page_attachments(page_id)
            for attachment in attachments:
                if attachment.get('title') == filename:
                    attachment_id = attachment.get('id')
                    if attachment_id:
                        logger.debug(f"发现同名附件 {filename} (ID: {attachment_id})，正在删除")
                        try:
                            self.delete_attachment(page_id, attachment_id)
                            logger.debug(f"已删除同名附件: {filename}")
                        except Exception as e:
                            logger.warning(f"删除同名附件失败: {e}，将继续尝试上传")
        except Exception as e:
            # 如果获取附件列表失败，继续尝试上传（向后兼容）
            logger.warning(f"获取附件列表失败: {e}，将继续尝试上传")
        
        url = f"{self.base_url}/rest/api/content/{page_id}/child/attachment"
        
        # 使用 multipart/form-data 上传
        # 不设置 Content-Type，让 requests 自动设置 multipart/form-data 和 boundary
        # 添加 X-Atlassian-Token 头以绕过 XSRF 检查（REST API 标准做法）
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
            "X-Atlassian-Token": "no-check"
            # 注意：不设置 Content-Type，requests 在使用 files 参数时会自动设置
        }
        
        try:
            with open(file_path_obj, 'rb') as f:
                files = {
                    'file': (filename, f)
                }
                data = {}
                if comment:
                    data['comment'] = comment
                
                response = self.session.post(
                    url,
                    headers=headers,
                    files=files,
                    data=data
                )
                
                if response.status_code >= 400:
                    error_msg = f"上传附件失败: {response.status_code}"
                    try:
                        error_data = response.json()
                        if 'message' in error_data:
                            error_msg += f" - {error_data['message']}"
                        elif 'data' in error_data:
                            error_msg += f" - {error_data['data']}"
                    except:
                        error_msg += f" - {response.text[:200]}"
                    
                    logger.error(f"{error_msg} | URL: {url} | File: {file_path}")
                    raise ConfluenceAPIError(
                        error_msg,
                        status_code=response.status_code,
                        response_text=response.text
                    )
                
                result = response.json()
                # 返回结果中包含 results 数组
                if 'results' in result and result['results']:
                    return result['results'][0]
                return result
        
        except ConfluenceAPIError:
            raise
        except FileNotFoundError:
            raise ConfluenceAPIError(f"文件不存在: {file_path}")
        except Exception as e:
            logger.error(f"上传附件异常: {e} | File: {file_path}")
            raise ConfluenceAPIError(f"上传附件失败: {e}")


# 创建全局实例
_client = None


def _get_client() -> ConfluenceClient:
    """获取客户端实例（单例模式）"""
    global _client
    if _client is None:
        _client = ConfluenceClient()
    return _client


def reset_client():
    """重置客户端实例（配置更新后调用）"""
    global _client
    _client = None


def get_space(space_key: str) -> Dict[str, Any]:
    """获取空间信息"""
    return _get_client().get_space(space_key)


def get_page_by_id(page_id: str, expand: str = "body.storage,version") -> Dict[str, Any]:
    """根据ID获取页面信息"""
    return _get_client().get_page_by_id(page_id, expand)


def get_page_content(page_id: str) -> str:
    """获取页面内容"""
    return _get_client().get_page_content(page_id)


def get_page_children(page_id: str, limit: int = 100) -> list:
    """获取页面的子页面"""
    return _get_client().get_page_children(page_id, limit)


def create_page(
    title: str,
    content: str,
    space_key: str,
    parent_id: Optional[str] = None
) -> Dict[str, Any]:
    """创建页面"""
    return _get_client().create_page(title, content, space_key, parent_id)


def update_page_content(
    page_id: str,
    content: str,
    title: Optional[str] = None,
    minor_edit: bool = True,
) -> Dict[str, Any]:
    """
    更新页面内容（会先读取页面以获取 title/version）

    Args:
        page_id: 页面ID
        content: 新内容（Storage Format）
        title: 可选，指定标题；不提供则使用 Confluence 当前标题
        minor_edit: 是否作为小改动
    """
    page = get_page_by_id(page_id, expand="version")
    page_title = title or page.get("title") or ""
    version = (page.get("version") or {}).get("number")
    if not page_title or not isinstance(version, int):
        raise ConfluenceAPIError(f"无法获取页面 title/version，page_id={page_id}")
    return _get_client().update_page(page_id, page_title, content, version, minor_edit=minor_edit)


def upload_attachment(
    page_id: str,
    file_path: str,
    comment: str = ""
) -> Dict[str, Any]:
    """上传附件到页面"""
    return _get_client().upload_attachment(page_id, file_path, comment)


def get_page_attachments(page_id: str) -> List[Dict[str, Any]]:
    """获取页面附件列表"""
    return _get_client().get_page_attachments(page_id)


def delete_attachment(page_id: str, attachment_id: str) -> None:
    """删除页面附件"""
    return _get_client().delete_attachment(page_id, attachment_id)
