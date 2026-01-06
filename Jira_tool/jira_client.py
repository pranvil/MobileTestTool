"""
JIRA API 客户端封装
"""
import requests
import urllib3
from typing import Dict, Any, Optional, List
from core.jira_config_manager import get_jira_url, get_token
from Jira_tool.core.exceptions import JiraAPIError
from core.debug_logger import logger

# 屏蔽 SSL 证书警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class JiraClient:
    """JIRA API 客户端"""
    
    def __init__(self, base_url: str = None, token: str = None):
        self.base_url = base_url or get_jira_url()
        self.token = token or get_token()
        self.session = requests.Session()
        self.session.verify = False  # 跳过SSL验证（内网自签名证书）
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        发送HTTP请求
        
        Args:
            method: HTTP方法（GET, POST等）
            endpoint: API端点（如 '/rest/api/2/issue'）
            **kwargs: 其他请求参数
        
        Returns:
            JSON响应数据
        
        Raises:
            JiraAPIError: API调用失败时抛出
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
                error_msg = f"JIRA API错误: {response.status_code}"
                try:
                    error_data = response.json()
                    if 'errorMessages' in error_data:
                        error_msg += f" - {', '.join(error_data['errorMessages'])}"
                    elif 'errors' in error_data:
                        error_msg += f" - {error_data['errors']}"
                except:
                    error_msg += f" - {response.text[:200]}"
                
                logger.error(f"{error_msg} | URL: {url}")
                raise JiraAPIError(
                    error_msg,
                    status_code=response.status_code,
                    response_text=response.text
                )
            
            if response.status_code == 204:  # No Content
                return {}
            
            return response.json()
        
        except JiraAPIError:
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {e} | URL: {url}")
            raise JiraAPIError(f"网络请求失败: {e}")
        except Exception as e:
            logger.error(f"未知错误: {e} | URL: {url}")
            raise JiraAPIError(f"未知错误: {e}")
    
    def get_myself(self) -> Dict[str, Any]:
        """
        获取当前用户信息（用于测试Token有效性）
        
        Returns:
            用户信息字典
        
        Raises:
            JiraAPIError: API调用失败时抛出
        """
        logger.debug("获取当前用户信息")
        return self._request("GET", "/rest/api/2/myself")
    
    def get_issue(self, issue_key: str, expand: str = None) -> Dict[str, Any]:
        """
        获取Issue信息（包括描述、摘要等）
        
        Args:
            issue_key: Issue Key（如 'GF65DISH-1347'）
            expand: 扩展参数，如 'renderedFields,names,schema' 来获取更多字段信息
        
        Returns:
            Issue数据字典
        
        Raises:
            JiraAPIError: API调用失败时抛出
        """
        logger.debug(f"获取Issue信息: {issue_key}")
        params = {}
        if expand:
            params['expand'] = expand
        return self._request("GET", f"/rest/api/2/issue/{issue_key}", params=params)
    
    def get_edit_meta(self, issue_key: str) -> Dict[str, Any]:
        """
        获取Issue的编辑元数据（包括所有可编辑字段的定义）
        
        Args:
            issue_key: Issue Key
        
        Returns:
            编辑元数据字典，包含所有字段定义
        
        Raises:
            JiraAPIError: API调用失败时抛出
        """
        logger.debug(f"获取Issue编辑元数据: {issue_key}")
        return self._request("GET", f"/rest/api/2/issue/{issue_key}/editmeta")
    
    def get_comments(self, issue_key: str) -> Dict[str, Any]:
        """
        获取Issue评论
        
        Args:
            issue_key: Issue Key（如 'GF65DISH-1347'）
        
        Returns:
            评论数据字典
        
        Raises:
            JiraAPIError: API调用失败时抛出
        """
        logger.debug(f"获取Issue评论: {issue_key}")
        return self._request("GET", f"/rest/api/2/issue/{issue_key}/comment")
    
    def get_create_meta(self, project_key: str, issue_type: str = None) -> Dict[str, Any]:
        """
        获取创建Issue的元数据（必填字段、字段定义等）
        
        Args:
            project_key: 项目Key
            issue_type: Issue类型名称（可选，如果不提供则获取所有类型）
        
        Returns:
            元数据字典
        
        Raises:
            JiraAPIError: API调用失败时抛出
        """
        logger.debug(f"获取创建元数据: project={project_key}, issue_type={issue_type}")
        # 使用editmeta接口获取创建元数据
        params = {
            "projectKeys": project_key,
            "expand": "projects.issuetypes.fields"
        }
        # 只有当提供了issue_type且不包含空格时才使用issuetypeNames参数
        # 因为JIRA API的issuetypeNames参数可能不支持包含空格的类型名称
        if issue_type and ' ' not in issue_type:
            params["issuetypeNames"] = issue_type
        return self._request("GET", "/rest/api/2/issue/createmeta", params=params)
    
    def get_available_issue_types(self, project_key: str) -> List[Dict[str, Any]]:
        """
        获取项目所有可用的Issue类型列表
        
        Args:
            project_key: 项目Key
        
        Returns:
            Issue类型列表，每个元素包含name, id等信息
        
        Raises:
            JiraAPIError: API调用失败时抛出
        """
        logger.debug(f"获取可用Issue类型列表: project={project_key}")
        # 不指定issuetypeNames，获取所有类型
        params = {
            "projectKeys": project_key,
            "expand": "projects.issuetypes"
        }
        meta = self._request("GET", "/rest/api/2/issue/createmeta", params=params)
        
        try:
            projects = meta.get("projects", [])
            if not projects:
                raise JiraAPIError("未找到项目元数据")
            
            project = projects[0]
            issuetypes = project.get("issuetypes", [])
            return issuetypes
        
        except JiraAPIError:
            raise
        except Exception as e:
            logger.error(f"解析Issue类型列表失败: {e}")
            raise JiraAPIError(f"解析Issue类型列表失败: {e}")
    
    def get_fields(self, project_key: str, issue_type: str) -> Dict[str, Any]:
        """
        获取字段定义（字段ID、类型、选项等）
        
        Args:
            project_key: 项目Key
            issue_type: Issue类型名称
        
        Returns:
            字段定义字典
        
        Raises:
            JiraAPIError: API调用失败时抛出
        """
        logger.debug(f"获取字段定义: project={project_key}, issue_type={issue_type}")
        
        # 如果类型名称包含空格，直接获取所有类型然后匹配
        # 因为JIRA API的issuetypeNames参数可能不支持包含空格的类型名称
        issue_type_trimmed = issue_type.strip()
        if ' ' in issue_type_trimmed:
            logger.debug(f"类型名称包含空格，获取所有类型进行匹配")
            meta = self.get_create_meta(project_key)  # 不指定issue_type，获取所有类型
        else:
            # 先尝试使用指定的issue_type获取
            meta = self.get_create_meta(project_key, issue_type)
        
        # 从元数据中提取字段定义
        try:
            projects = meta.get("projects", [])
            if not projects:
                raise JiraAPIError("未找到项目元数据")
            
            project = projects[0]
            issuetypes = project.get("issuetypes", [])
            
            if not issuetypes:
                # 如果返回为空，尝试获取所有可用类型
                logger.debug(f"未找到类型，尝试获取所有可用类型")
                available_types = self.get_available_issue_types(project_key)
                type_names = [it.get("name", "") for it in available_types if it.get("name")]
                available_types_str = "\n  - " + "\n  - ".join(type_names) if type_names else "（无可用类型）"
                error_msg = f"未找到Issue类型 '{issue_type}'。\n\n可用的Issue类型:\n{available_types_str}"
                raise JiraAPIError(error_msg)
            
            # 查找匹配的Issue类型（精确匹配，去除空格）
            matched_type = None
            for it in issuetypes:
                it_name = it.get("name", "").strip()
                if it_name == issue_type_trimmed:
                    matched_type = it
                    break
            
            # 如果精确匹配失败，尝试不区分大小写的匹配
            if not matched_type:
                issue_type_lower = issue_type_trimmed.lower()
                for it in issuetypes:
                    it_name = it.get("name", "").strip()
                    if it_name.lower() == issue_type_lower:
                        matched_type = it
                        logger.debug(f"通过大小写不敏感匹配找到类型: '{it_name}'")
                        break
            
            if matched_type:
                return matched_type.get("fields", {})
            
            # 如果没有匹配，列出所有可用类型
            try:
                available_types = self.get_available_issue_types(project_key)
                type_names = [it.get("name", "") for it in available_types if it.get("name")]
                available_types_str = "\n  - " + "\n  - ".join(type_names) if type_names else "（无可用类型）"
                error_msg = f"未找到Issue类型 '{issue_type}'。\n\n可用的Issue类型:\n{available_types_str}"
            except Exception:
                error_msg = f"未找到Issue类型: {issue_type}"
            raise JiraAPIError(error_msg)
        
        except JiraAPIError:
            raise
        except Exception as e:
            logger.error(f"解析字段定义失败: {e}")
            raise JiraAPIError(f"解析字段定义失败: {e}")
    
    def create_issue(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建Issue
        
        Args:
            payload: 完整的JIRA API格式的payload
        
        Returns:
            创建的Issue信息
        
        Raises:
            JiraAPIError: API调用失败时抛出
        """
        logger.debug(f"创建Issue: {payload.get('fields', {}).get('summary', 'N/A')}")
        return self._request("POST", "/rest/api/2/issue", json=payload)
    
    def update_issue(self, issue_key: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新Issue字段
        
        Args:
            issue_key: Issue Key（如 'TCTCL-69007'）
            fields: 要更新的字段字典，格式为 {field_id: value} 或 {field_name: value}
        
        Returns:
            更新后的Issue信息（如果API返回）
        
        Raises:
            JiraAPIError: API调用失败时抛出
        """
        logger.debug(f"更新Issue: {issue_key}")
        payload = {"fields": fields}
        return self._request("PUT", f"/rest/api/2/issue/{issue_key}", json=payload)
    
    def search_issues(self, jql: str, max_results: int = 100, start_at: int = 0) -> Dict[str, Any]:
        """
        使用JQL查询Issue
        
        Args:
            jql: JQL查询语句
            max_results: 最大返回结果数，默认100
            start_at: 起始位置，默认0
        
        Returns:
            查询结果字典，包含issues列表和总数
        
        Raises:
            JiraAPIError: API调用失败时抛出
        """
        logger.debug(f"JQL查询: {jql}")
        params = {
            "jql": jql,
            "maxResults": max_results,
            "startAt": start_at,
            "fields": "key,summary"  # 只返回key和summary，减少数据量
        }
        return self._request("GET", "/rest/api/2/search", params=params)

    def download_issue_export_xlsx(
        self,
        jql: str,
        temp_max: int = 5000,
        context: str = "issue_navigator",
        timeout: int = 120,
    ) -> bytes:
        """
        调用 Better Excel 插件接口导出 Issue Navigator 的 Excel。

        API:
          GET /rest/com.midori.jira.plugin.betterexcel/1.0/xls/xls-view/2021/render

        Query params:
          - jql: 动态（requests 会进行 URL encoding）
          - tempMax: 固定 5000（默认）
          - context: 固定 issue_navigator（默认）
        """
        jql = (jql or "").strip()
        if not jql:
            raise JiraAPIError("JQL 不能为空")

        token = (self.token or "").strip()
        if not token:
            raise JiraAPIError("未配置 API Token，请先在设置中填写并验证")

        endpoint = "/rest/com.midori.jira.plugin.betterexcel/1.0/xls/xls-view/2021/render"
        base = (self.base_url or "").rstrip("/")
        url = f"{base}{endpoint}"

        params = {
            "jql": jql,
            "tempMax": int(temp_max),
            "context": context,
        }
        headers = {
            "Accept": "*/*",
            "Authorization": f"Bearer {token}",
            "User-Agent": "JiraAutomationTool/1.0",
        }

        try:
            resp = self.session.get(url, headers=headers, params=params, timeout=timeout)
            if resp.status_code >= 400:
                error_msg = f"JIRA 导出接口错误: {resp.status_code}"
                try:
                    error_data = resp.json()
                    if isinstance(error_data, dict):
                        if "errorMessages" in error_data and isinstance(error_data["errorMessages"], list):
                            error_msg += f" - {', '.join([str(x) for x in error_data['errorMessages']])}"
                        elif "message" in error_data:
                            error_msg += f" - {error_data['message']}"
                        elif "errors" in error_data:
                            error_msg += f" - {error_data['errors']}"
                except Exception:
                    error_msg += f" - {resp.text[:200]}"

                logger.error(f"{error_msg} | URL: {url}")
                raise JiraAPIError(
                    error_msg,
                    status_code=resp.status_code,
                    response_text=resp.text,
                )

            return resp.content
        except JiraAPIError:
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"导出请求异常: {e} | URL: {url}")
            raise JiraAPIError(f"网络请求失败: {e}")
        except Exception as e:
            logger.error(f"导出未知错误: {e} | URL: {url}")
            raise JiraAPIError(f"未知错误: {e}")


# 创建全局实例
_client = None


def _get_client() -> JiraClient:
    """获取客户端实例（单例模式）"""
    global _client
    if _client is None:
        _client = JiraClient()
    return _client


def reset_client():
    """重置客户端实例（配置更新后调用）"""
    global _client
    _client = None


def get_myself() -> Dict[str, Any]:
    """获取当前用户信息"""
    return _get_client().get_myself()


def get_issue(issue_key: str, expand: str = None) -> Dict[str, Any]:
    """获取Issue信息"""
    return _get_client().get_issue(issue_key, expand)


def get_edit_meta(issue_key: str) -> Dict[str, Any]:
    """获取Issue的编辑元数据"""
    return _get_client().get_edit_meta(issue_key)


def get_comments(issue_key: str) -> Dict[str, Any]:
    """获取Issue评论"""
    return _get_client().get_comments(issue_key)


def get_create_meta(project_key: str, issue_type: str) -> Dict[str, Any]:
    """获取创建Issue的元数据"""
    return _get_client().get_create_meta(project_key, issue_type)


def get_available_issue_types(project_key: str) -> List[Dict[str, Any]]:
    """获取项目所有可用的Issue类型列表"""
    return _get_client().get_available_issue_types(project_key)


def get_fields(project_key: str, issue_type: str) -> Dict[str, Any]:
    """获取字段定义"""
    return _get_client().get_fields(project_key, issue_type)


def create_issue(payload: Dict[str, Any]) -> Dict[str, Any]:
    """创建Issue"""
    return _get_client().create_issue(payload)


def update_issue(issue_key: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """更新Issue字段"""
    return _get_client().update_issue(issue_key, fields)


def search_issues(jql: str, max_results: int = 100, start_at: int = 0) -> Dict[str, Any]:
    """使用JQL查询Issue"""
    return _get_client().search_issues(jql, max_results, start_at)

