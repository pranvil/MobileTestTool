"""
Confluence页面树管理模块
实现懒加载和缓存机制
"""
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from Jira_tool.confluence_client import get_space, get_page_children, ConfluenceAPIError
from Jira_tool.core.paths import get_cache_path
from core.debug_logger import logger

_STATE_FILE_NAME = "confluence_page_tree_state.json"


def _state_file_path():
    return get_cache_path() / _STATE_FILE_NAME


def _load_state() -> Dict[str, Any]:
    """
    状态文件结构：
    {
      "spaces": {
        "USVAL": {
          "last_auto_load_time": "2025-12-30T10:11:12",
          "homepage_id": "12345",
          "root_pages": [ ... ]
        },
        ...
      }
    }
    """
    path = _state_file_path()
    if not path.exists():
        return {"spaces": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"spaces": {}}
        data.setdefault("spaces", {})
        if not isinstance(data["spaces"], dict):
            data["spaces"] = {}
        return data
    except Exception as e:
        logger.warning(f"读取页面树状态文件失败，将忽略缓存: {e}")
        return {"spaces": {}}


def _save_state(data: Dict[str, Any]) -> None:
    path = _state_file_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"保存页面树状态文件失败: {e}")


class PageTreeCache:
    """页面树缓存管理器"""
    
    def __init__(self, space_key: str):
        self.space_key = space_key
        self._cache: Dict[str, List[Dict]] = {}  # {page_id: children_list}
        self._loaded_pages: set = set()  # 已加载的页面ID集合
        self._last_auto_load_time: Optional[datetime] = None  # 上次自动加载时间
        self._homepage_id: Optional[str] = None  # 空间首页ID
        self._root_pages: List[Dict] = []  # 一级目录缓存

        # 从状态文件恢复“上次自动加载时间/根目录”（跨进程生效）
        state = _load_state()
        space_state = state.get("spaces", {}).get(space_key, {}) if isinstance(state.get("spaces", {}), dict) else {}
        ts = space_state.get("last_auto_load_time")
        if isinstance(ts, str) and ts:
            try:
                self._last_auto_load_time = datetime.fromisoformat(ts)
            except Exception:
                self._last_auto_load_time = None

        homepage_id = space_state.get("homepage_id")
        root_pages = space_state.get("root_pages")
        if isinstance(homepage_id, str) and homepage_id and isinstance(root_pages, list) and root_pages:
            self._homepage_id = homepage_id
            self._root_pages = root_pages
    
    def load_page_tree(self, space_key: str, force_reload: bool = False) -> Tuple[Optional[str], List[Dict]]:
        """
        加载空间的一级目录（页面树根节点）
        
        Args:
            space_key: 空间Key
            force_reload: 是否强制重新加载（忽略缓存）
        
        Returns:
            (homepage_id, root_pages) 元组
            homepage_id: 空间首页ID
            root_pages: 一级目录页面列表
        
        Raises:
            ConfluenceAPIError: API调用失败时抛出
        """
        try:
            # 如果已有缓存且不强制重新加载，直接返回
            if not force_reload and self._homepage_id and self._root_pages:
                logger.debug(f"使用缓存的页面树: {space_key}")
                return self._homepage_id, self._root_pages

            # 内存无缓存时，尝试从磁盘状态文件恢复（避免启动就打 API）
            if not force_reload:
                state = _load_state()
                space_state = state.get("spaces", {}).get(space_key, {}) if isinstance(state.get("spaces", {}), dict) else {}
                homepage_id = space_state.get("homepage_id")
                root_pages = space_state.get("root_pages")
                if isinstance(homepage_id, str) and homepage_id and isinstance(root_pages, list) and root_pages:
                    self._homepage_id = homepage_id
                    self._root_pages = root_pages
                    logger.debug(f"使用磁盘缓存的页面树: {space_key} ({len(root_pages)} 个一级目录)")
                    return homepage_id, root_pages
            
            logger.info(f"加载空间页面树: {space_key}")
            
            # 获取空间信息
            space_data = get_space(space_key)
            homepage = space_data.get('homepage')
            
            if not homepage:
                logger.warning(f"空间 {space_key} 没有设置首页")
                return None, []
            
            homepage_id = homepage.get('id')
            logger.debug(f"空间首页ID: {homepage_id}")
            
            # 获取首页的直接子页面（一级目录）
            root_pages = self.load_children(homepage_id, force_reload=force_reload)
            
            # 更新缓存
            self._homepage_id = homepage_id
            self._root_pages = root_pages

            # 落盘根目录缓存（跨进程复用）
            state = _load_state()
            spaces = state.setdefault("spaces", {})
            space_state = spaces.get(space_key, {})
            if not isinstance(space_state, dict):
                space_state = {}
            space_state["homepage_id"] = homepage_id
            space_state["root_pages"] = root_pages
            spaces[space_key] = space_state
            _save_state(state)
            
            logger.info(f"加载完成: 找到 {len(root_pages)} 个一级目录")
            return homepage_id, root_pages
            
        except ConfluenceAPIError as e:
            logger.error(f"加载页面树失败: {e}")
            raise
        except Exception as e:
            logger.exception(f"加载页面树时发生未知错误: {e}")
            raise ConfluenceAPIError(f"加载页面树失败: {e}")
    
    def load_all_pages_recursive(self, space_key: str, page_id: str, max_depth: int = 2, current_depth: int = 0):
        """
        递归加载所有页面（用于手动刷新）
        
        Args:
            space_key: 空间Key
            page_id: 起始页面ID
            max_depth: 最大深度（默认3层：homepage -> 一级 -> 二级 -> 三级）
            current_depth: 当前深度
        """
        if current_depth >= max_depth:
            return
        
        try:
            # 加载子页面
            children = self.load_children(page_id, force_reload=True)
            
            # 递归加载每个子页面
            for child in children:
                child_id = child.get('id')
                if child_id:
                    self.load_all_pages_recursive(space_key, child_id, max_depth, current_depth + 1)
        except Exception as e:
            logger.warning(f"递归加载页面失败 (page_id={page_id}, depth={current_depth}): {e}")
    
    def should_auto_load(self) -> bool:
        """判断是否应该自动加载（24小时内未加载过）"""
        if self._last_auto_load_time is None:
            return True
        
        time_diff = datetime.now() - self._last_auto_load_time
        return time_diff >= timedelta(hours=24)
    
    def mark_auto_loaded(self):
        """标记已自动加载"""
        self._last_auto_load_time = datetime.now()
        # 落盘（跨进程节流）
        state = _load_state()
        spaces = state.setdefault("spaces", {})
        space_state = spaces.get(self.space_key, {})
        if not isinstance(space_state, dict):
            space_state = {}
        space_state["last_auto_load_time"] = self._last_auto_load_time.isoformat(timespec="seconds")
        spaces[self.space_key] = space_state
        _save_state(state)
    
    def load_children(self, page_id: str, force_reload: bool = False) -> List[Dict]:
        """
        加载页面的子页面（支持缓存）
        
        Args:
            page_id: 父页面ID
            force_reload: 是否强制重新加载（忽略缓存）
        
        Returns:
            子页面列表
        
        Raises:
            ConfluenceAPIError: API调用失败时抛出
        """
        # 检查缓存
        if not force_reload and page_id in self._cache:
            logger.debug(f"从缓存加载子页面: {page_id}")
            return self._cache[page_id]
        
        try:
            logger.debug(f"从API加载子页面: {page_id}")
            children = get_page_children(page_id)
            
            # 更新缓存
            self._cache[page_id] = children
            self._loaded_pages.add(page_id)
            
            logger.debug(f"加载完成: {page_id} 有 {len(children)} 个子页面")
            return children
            
        except ConfluenceAPIError as e:
            logger.error(f"加载子页面失败: {e}")
            raise
        except Exception as e:
            logger.exception(f"加载子页面时发生未知错误: {e}")
            raise ConfluenceAPIError(f"加载子页面失败: {e}")
    
    def is_loaded(self, page_id: str) -> bool:
        """检查页面是否已加载"""
        return page_id in self._loaded_pages
    
    def clear_cache(self, page_id: Optional[str] = None):
        """
        清除缓存
        
        Args:
            page_id: 如果提供，只清除该页面的缓存；否则清除所有缓存
        """
        if page_id:
            self._cache.pop(page_id, None)
            self._loaded_pages.discard(page_id)
            logger.debug(f"已清除页面缓存: {page_id}")
        else:
            self._cache.clear()
            self._loaded_pages.clear()
            self._homepage_id = None
            self._root_pages = []
            logger.debug("已清除所有页面缓存")
    
    def get_cached_children(self, page_id: str) -> Optional[List[Dict]]:
        """获取缓存的子页面（不触发API调用）"""
        return self._cache.get(page_id)


# 创建全局实例（按空间Key分别缓存）
_space_caches: Dict[str, PageTreeCache] = {}


def get_page_tree_cache(space_key: str) -> PageTreeCache:
    """获取指定空间的页面树缓存"""
    if space_key not in _space_caches:
        _space_caches[space_key] = PageTreeCache(space_key)
    return _space_caches[space_key]


def load_page_tree(space_key: str, force_reload: bool = False) -> Tuple[Optional[str], List[Dict]]:
    """加载空间页面树"""
    cache = get_page_tree_cache(space_key)
    return cache.load_page_tree(space_key, force_reload)


def load_all_pages(space_key: str, homepage_id: str):
    """加载所有页面（用于手动刷新）"""
    cache = get_page_tree_cache(space_key)
    cache.load_all_pages_recursive(space_key, homepage_id)


def should_auto_load_page_tree(space_key: str) -> bool:
    """判断是否应该自动加载页面树"""
    cache = get_page_tree_cache(space_key)
    return cache.should_auto_load()


def mark_auto_loaded(space_key: str):
    """标记页面树已自动加载"""
    cache = get_page_tree_cache(space_key)
    cache.mark_auto_loaded()


def load_children(page_id: str, space_key: str, force_reload: bool = False) -> List[Dict]:
    """加载子页面"""
    cache = get_page_tree_cache(space_key)
    return cache.load_children(page_id, force_reload)


def clear_page_tree_cache(space_key: Optional[str] = None):
    """清除页面树缓存"""
    if space_key:
        _space_caches.pop(space_key, None)
        logger.debug(f"已清除空间缓存: {space_key}")

        # 同时清除磁盘缓存（避免下次启动继续复用旧目录）
        try:
            state = _load_state()
            spaces = state.get("spaces", {})
            if isinstance(spaces, dict) and space_key in spaces:
                spaces.pop(space_key, None)
                _save_state(state)
        except Exception as e:
            logger.warning(f"清除页面树磁盘缓存失败: {e}")
    else:
        _space_caches.clear()
        logger.debug("已清除所有空间缓存")
        try:
            _save_state({"spaces": {}})
        except Exception:
            pass