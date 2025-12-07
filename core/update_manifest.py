#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在线更新版本描述结构定义"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any


DEFAULT_MANIFEST_FILENAME: str = "latest.json"
MANIFEST_REQUIRED_FIELDS: Tuple[str, ...] = ("version", "sha256")
MANIFEST_OPTIONAL_FIELDS: Tuple[str, ...] = (
    "download_url",
    "download_urls",
    "file_name",
    "file_size",
    "release_notes",
    "published_at",
    "mandatory",
)


@dataclass(slots=True)
class DownloadSource:
    """下载源配置"""
    
    url: str
    region: Optional[str] = None  # 地区代码，如 "cn", "us", "default"
    platform: Optional[str] = None  # 平台，如 "windows", "mac", "linux", "all"
    priority: int = 0  # 优先级，数字越大优先级越高


@dataclass(slots=True)
class LatestManifest:
    """latest.json 的规范化数据结构"""

    version: str
    download_url: str  # 向后兼容的默认下载URL
    sha256: str
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    release_notes: Optional[str] = None
    published_at: Optional[str] = None
    mandatory: bool = False
    download_urls: Optional[List[DownloadSource]] = None  # 多下载源支持

    @classmethod
    def from_dict(cls, data: dict) -> "LatestManifest":
        """从原始字典构建 manifest 模型并进行基本校验"""

        if not isinstance(data, dict):
            raise TypeError("latest.json 内容必须是对象类型")

        missing_fields = [field for field in MANIFEST_REQUIRED_FIELDS if not data.get(field)]
        if missing_fields:
            raise ValueError(f"latest.json 缺少必要字段: {', '.join(missing_fields)}")

        # 必须提供 download_url 或 download_urls 之一
        if not data.get("download_url") and not data.get("download_urls"):
            raise ValueError("latest.json 必须提供 download_url 或 download_urls 字段")

        file_size = data.get("file_size")
        if file_size in ("", None):
            normalized_size: Optional[int] = None
        else:
            try:
                normalized_size = int(file_size)
            except (TypeError, ValueError) as exc:
                raise ValueError("file_size 必须是整数") from exc

        # 解析 download_urls（多下载源）
        download_urls: Optional[List[DownloadSource]] = None
        if data.get("download_urls"):
            urls_data = data["download_urls"]
            if not isinstance(urls_data, list):
                raise ValueError("download_urls 必须是数组类型")
            
            download_urls = []
            for idx, url_item in enumerate(urls_data):
                if isinstance(url_item, str):
                    # 简单字符串格式，转换为 DownloadSource
                    download_urls.append(DownloadSource(url=url_item))
                elif isinstance(url_item, dict):
                    # 对象格式，支持 region, platform, priority
                    if "url" not in url_item:
                        raise ValueError(f"download_urls[{idx}] 缺少 url 字段")
                    download_urls.append(DownloadSource(
                        url=str(url_item["url"]),
                        region=url_item.get("region"),
                        platform=url_item.get("platform"),
                        priority=int(url_item.get("priority", 0))
                    ))
                else:
                    raise ValueError(f"download_urls[{idx}] 必须是字符串或对象类型")

        # download_url 作为默认值（向后兼容）
        default_download_url = data.get("download_url") or ""
        if download_urls and not default_download_url:
            # 如果没有提供 download_url，使用第一个 download_urls 作为默认值
            default_download_url = download_urls[0].url

        return cls(
            version=str(data["version"]),
            download_url=default_download_url,
            sha256=str(data["sha256"]).lower(),
            file_name=data.get("file_name") or None,
            file_size=normalized_size,
            release_notes=data.get("release_notes") or None,
            published_at=data.get("published_at") or None,
            mandatory=bool(data.get("mandatory", False)),
            download_urls=download_urls,
        )

    def to_dict(self) -> dict:
        """转换为可序列化的字典"""

        result: Dict[str, Any] = {
            "version": self.version,
            "download_url": self.download_url,
            "sha256": self.sha256,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "release_notes": self.release_notes,
            "published_at": self.published_at,
            "mandatory": self.mandatory,
        }
        
        # 如果有多个下载源，也包含在输出中
        if self.download_urls:
            result["download_urls"] = [
                {
                    "url": source.url,
                    "region": source.region,
                    "platform": source.platform,
                    "priority": source.priority,
                }
                for source in self.download_urls
            ]
        
        return result


__all__ = [
    "DEFAULT_MANIFEST_FILENAME",
    "MANIFEST_REQUIRED_FIELDS",
    "MANIFEST_OPTIONAL_FIELDS",
    "LatestManifest",
    "DownloadSource",
]


