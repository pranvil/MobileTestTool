#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在线更新版本描述结构定义"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


DEFAULT_MANIFEST_FILENAME: str = "latest.json"
MANIFEST_REQUIRED_FIELDS: Tuple[str, ...] = ("version", "download_url", "sha256")
MANIFEST_OPTIONAL_FIELDS: Tuple[str, ...] = (
    "file_name",
    "file_size",
    "release_notes",
    "published_at",
    "mandatory",
)


@dataclass(slots=True)
class LatestManifest:
    """latest.json 的规范化数据结构"""

    version: str
    download_url: str
    sha256: str
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    release_notes: Optional[str] = None
    published_at: Optional[str] = None
    mandatory: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "LatestManifest":
        """从原始字典构建 manifest 模型并进行基本校验"""

        if not isinstance(data, dict):
            raise TypeError("latest.json 内容必须是对象类型")

        missing_fields = [field for field in MANIFEST_REQUIRED_FIELDS if not data.get(field)]
        if missing_fields:
            raise ValueError(f"latest.json 缺少必要字段: {', '.join(missing_fields)}")

        file_size = data.get("file_size")
        if file_size in ("", None):
            normalized_size: Optional[int] = None
        else:
            try:
                normalized_size = int(file_size)
            except (TypeError, ValueError) as exc:
                raise ValueError("file_size 必须是整数") from exc

        return cls(
            version=str(data["version"]),
            download_url=str(data["download_url"]),
            sha256=str(data["sha256"]).lower(),
            file_name=data.get("file_name") or None,
            file_size=normalized_size,
            release_notes=data.get("release_notes") or None,
            published_at=data.get("published_at") or None,
            mandatory=bool(data.get("mandatory", False)),
        )


__all__ = [
    "DEFAULT_MANIFEST_FILENAME",
    "MANIFEST_REQUIRED_FIELDS",
    "MANIFEST_OPTIONAL_FIELDS",
    "LatestManifest",
]


