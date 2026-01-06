"""
常用 JQL 记录管理（本地 JSON 持久化）

文件位置：output/cache/jql_records.json
结构示例：
[
  { "name": "我的待办", "jql": "assignee = currentUser() AND status = Open" }
]
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from Jira_tool.core.paths import get_cache_path
from core.debug_logger import logger


_FILE_NAME = "jql_records.json"


def _records_path() -> Path:
    return get_cache_path() / _FILE_NAME


def load_records() -> List[Dict[str, str]]:
    """
    读取本地 JSON，返回规范化后的记录列表。
    - 文件不存在：返回 []
    - 文件损坏/结构错误：返回 [] 并记录 warning
    """
    path = _records_path()
    if not path.exists():
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning(f"读取 JQL 记录文件失败，将忽略该文件: {e}")
        return []

    if not isinstance(data, list):
        return []

    records: List[Dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        jql = item.get("jql")
        if not isinstance(name, str) or not isinstance(jql, str):
            continue
        name = name.strip()
        jql = jql.strip()
        if not name or not jql:
            continue
        records.append({"name": name, "jql": jql})
    return records


def save_records(records: List[Dict[str, str]]) -> None:
    """保存记录列表到 JSON（ensure_ascii=False, indent=2）。"""
    path = _records_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"保存 JQL 记录文件失败: {e}")


def upsert_record(name: str, jql: str) -> Tuple[bool, List[Dict[str, str]]]:
    """
    新增或更新同名记录。

    Returns:
        (replaced, new_records)
    """
    name = (name or "").strip()
    jql = (jql or "").strip()
    if not name or not jql:
        return False, load_records()

    records = load_records()
    replaced = False
    new_records: List[Dict[str, str]] = []

    for r in records:
        if r.get("name") == name:
            new_records.append({"name": name, "jql": jql})
            replaced = True
        else:
            new_records.append(r)

    if not replaced:
        new_records.append({"name": name, "jql": jql})

    save_records(new_records)
    return replaced, new_records


def delete_record(name: str) -> List[Dict[str, str]]:
    """删除指定 name 的记录并落盘，返回删除后的列表。"""
    name = (name or "").strip()
    if not name:
        return load_records()

    records = load_records()
    new_records = [r for r in records if r.get("name") != name]
    save_records(new_records)
    return new_records

