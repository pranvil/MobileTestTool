"""
Test Suite查询模块
用于查询Test Case关联的Test Suite信息
"""
import re
import urllib.parse
from typing import Dict, Any, Optional, List

from Jira_tool.jira_client import _get_client, get_issue
from core.debug_logger import logger


def get_test_suites_for_case(issue_key: str) -> Optional[List[Dict[str, Any]]]:
    """
    获取Test Case关联的所有Test Suite
    通过页面HTML解析获取Test Suite数据
    
    Args:
        issue_key: Issue Key (如 'TCTCL-76940')
    
    Returns:
        Test Suite列表，每个元素包含id, name, hierarchy, tsFocusId等信息，如果未找到则返回None
    """
    client = _get_client()
    
    # 先获取issue ID
    try:
        issue_data = get_issue(issue_key)
        issue_id = issue_data.get('id')
        tc_id = str(issue_id)
    except Exception as e:
        logger.error(f"获取Issue ID失败: {e}")
        return None
    
    # 通过页面HTML解析获取
    try:
        # 获取issue页面HTML
        endpoint = f"/browse/{issue_key}"
        url = f"{client.base_url}{endpoint}"
        headers = client._get_headers()
        headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        
        response = client.session.request("GET", url, headers=headers, verify=False)
        
        if response.status_code == 200:
            html_content = response.text
            
            # 从HTML中提取test suite信息
            # 匹配格式: /secure/ExpandTestSuite.jspa?testSuiteId=数字&testSuiteName=名称&tcFocusId=数字&tsFocusId=数字
            test_suites = []
            
            # 模式1: 从ExpandTestSuite链接中提取
            pattern = r'/secure/ExpandTestSuite\.jspa\?testSuiteId=(\d+)&testSuiteName=([^&]+)&tcFocusId=\d+&tsFocusId=(\d+)'
            matches = re.findall(pattern, html_content)
            
            # 用于去重（基于tsFocusId）
            seen_ts_focus_ids = set()
            
            for match in matches:
                test_suite_id, test_suite_name, ts_focus_id = match
                
                # 避免重复
                if ts_focus_id in seen_ts_focus_ids:
                    continue
                seen_ts_focus_ids.add(ts_focus_id)
                
                # 解码URL编码的名称
                test_suite_name = urllib.parse.unquote(test_suite_name)
                
                # 从data-hierarchy属性提取层级信息
                # 查找包含这个testSuiteId的链接，然后提取data-hierarchy
                hierarchy_pattern = rf'data-hierarchy="([^"]+)"[^>]*href="/secure/ExpandTestSuite\.jspa\?testSuiteId={re.escape(test_suite_id)}'
                hierarchy_match = re.search(hierarchy_pattern, html_content)
                hierarchy = hierarchy_match.group(1) if hierarchy_match else None
                
                test_suite = {
                    'id': test_suite_id,
                    'tsFocusId': ts_focus_id,
                    'name': test_suite_name,
                    'hierarchy': hierarchy,
                    'tcId': tc_id,
                    'tcKey': issue_key
                }
                test_suites.append(test_suite)
            
            if test_suites:
                logger.info(f"成功获取 {len(test_suites)} 个Test Suite")
                return test_suites
            else:
                logger.warning(f"HTML中未找到Test Suite数据 (issue_key: {issue_key})")
                return None
        else:
            logger.error(f"获取页面失败: {response.status_code} (issue_key: {issue_key})")
            return None
            
    except Exception as e:
        logger.error(f"获取Test Suite失败: {e} (issue_key: {issue_key})")
        return None


def is_case_in_test_suite(issue_key: str, test_suite_name: str, exact_match: bool = False) -> bool:
    """
    检查某个Test Case是否属于指定的Test Suite
    
    Args:
        issue_key: Issue Key (如 'TCTCL-76940')
        test_suite_name: Test Suite名称
        exact_match: 是否精确匹配（True：完全匹配，False：部分匹配，默认False）
    
    Returns:
        True表示属于该Test Suite，False表示不属于或未找到
    """
    test_suites = get_test_suites_for_case(issue_key)
    
    if not test_suites:
        return False
    
    # 标准化查询名称
    test_suite_name_lower = test_suite_name.lower().strip()
    
    for suite in test_suites:
        suite_name = suite.get('name', '').lower()
        
        if exact_match:
            # 精确匹配
            if test_suite_name_lower == suite_name:
                return True
        else:
            # 部分匹配（支持双向包含）
            if test_suite_name_lower in suite_name or suite_name in test_suite_name_lower:
                return True
    
    return False


def get_test_suite_names(issue_key: str) -> List[str]:
    """
    获取Test Case关联的所有Test Suite名称列表
    
    Args:
        issue_key: Issue Key (如 'TCTCL-76940')
    
    Returns:
        Test Suite名称列表，如果未找到则返回空列表
    """
    test_suites = get_test_suites_for_case(issue_key)
    
    if not test_suites:
        return []
    
    return [suite.get('name', '') for suite in test_suites if suite.get('name')]

