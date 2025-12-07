#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在线更新逻辑实现"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple, Union

from core.update_manifest import LatestManifest, DownloadSource

ProgressCallback = Callable[[int, Optional[int]], None]

DEFAULT_UPDATE_FEED_URL: str = "https://raw.githubusercontent.com/pranvil/MobileTestTool/main/releases/latest.json"


class UpdateError(RuntimeError):
    """在线更新基础异常"""


class ManifestFetchError(UpdateError):
    """拉取 latest.json 失败"""


class ManifestValidationError(UpdateError):
    """latest.json 内容不合法"""


class VersionCompareError(UpdateError):
    """版本比较失败"""


class DownloadError(UpdateError):
    """安装包下载失败"""


class IntegrityError(UpdateError):
    """安装包校验失败"""


@dataclass(slots=True)
class DownloadResult:
    """下载结果信息"""

    file_path: str
    file_size: int
    sha256: str


class UpdateManager:
    """处理版本检测与安装包下载的核心类"""

    USER_AGENT = "MobileTestTool-Updater/1.0"

    def __init__(
        self,
        current_version: str,
        tool_config: Optional[dict] = None,
        *,
        timeout: Optional[int] = None,
        chunk_size: int = 256 * 1024,
        logger: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.current_version = (current_version or "0").strip()
        self.tool_config = tool_config or {}
        self.timeout = timeout or self.tool_config.get("update_timeout", 15)
        self.chunk_size = chunk_size
        self.logger = logger
        self._cancel_event = threading.Event()
        self._detected_region: Optional[str] = None
        self._detected_platform: Optional[str] = None

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------
    def fetch_latest_manifest(self) -> LatestManifest:
        """从配置的 URL 拉取最新版本描述"""

        url = (self.tool_config.get("update_feed_url") or DEFAULT_UPDATE_FEED_URL).strip()
        if not url:
            raise ManifestFetchError("未配置更新版本描述 URL")

        request = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})

        self._log(f"请求 latest.json: {url}")

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise ManifestFetchError(f"latest.json 请求失败，HTTP {response.status}")

                # 检查 Content-Type
                content_type = response.headers.get("Content-Type", "").lower()
                if "json" not in content_type and "text" not in content_type:
                    self._log(f"警告: Content-Type 为 {content_type}，可能不是 JSON 文件")

                raw = response.read()

        except urllib.error.HTTPError as exc:  # pragma: no cover - 网络错误难以覆盖
            raise ManifestFetchError(f"latest.json 请求失败，HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:  # pragma: no cover - 网络错误难以覆盖
            raise ManifestFetchError(f"无法访问 latest.json: {exc.reason}") from exc
        except TimeoutError as exc:  # pragma: no cover - 由底层抛出
            raise ManifestFetchError("请求 latest.json 超时") from exc

        # 尝试解码和解析 JSON，提供更详细的错误信息
        try:
            # 首先尝试 UTF-8 解码
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError as decode_exc:
                # UTF-8 解码失败，尝试其他常见编码
                encodings = ["utf-8-sig", "gbk", "gb2312", "latin-1", "iso-8859-1"]
                text = None
                last_error = decode_exc
                
                for encoding in encodings:
                    try:
                        text = raw.decode(encoding)
                        self._log(f"使用 {encoding} 编码成功解码响应")
                        break
                    except UnicodeDecodeError:
                        continue
                
                if text is None:
                    # 所有编码都失败，提供诊断信息
                    preview = raw[:200] if len(raw) > 200 else raw
                    hex_preview = preview.hex()[:100]
                    raise ManifestValidationError(
                        f"latest.json 无法解码为文本（尝试了 UTF-8、GBK、Latin-1 等编码）。"
                        f"响应前 {len(preview)} 字节的十六进制: {hex_preview}..."
                    ) from last_error
            
            # 检查是否是 HTML 错误页面
            text_lower = text.strip().lower()
            if text_lower.startswith("<!doctype") or text_lower.startswith("<html"):
                # 尝试提取错误信息
                error_msg = "latest.json 返回了 HTML 页面而不是 JSON"
                if "404" in text or "not found" in text_lower:
                    error_msg += "（可能是 404 错误页面）"
                elif "403" in text or "forbidden" in text_lower:
                    error_msg += "（可能是 403 禁止访问）"
                raise ManifestValidationError(error_msg)
            
            # 解析 JSON
            manifest_data = json.loads(text)
            
        except json.JSONDecodeError as json_exc:
            # JSON 解析失败，提供更多上下文
            preview = text[:500] if len(text) > 500 else text
            raise ManifestValidationError(
                f"latest.json 不是有效的 JSON 格式。"
                f"解析错误位置: 第 {json_exc.lineno} 行，第 {json_exc.colno} 列。"
                f"响应内容预览: {preview}..."
            ) from json_exc
        except ManifestValidationError:
            # 重新抛出我们自己的错误
            raise
        except Exception as exc:
            # 其他未预期的错误
            raise ManifestValidationError(f"解析 latest.json 时发生错误: {exc}") from exc

        try:
            manifest = LatestManifest.from_dict(manifest_data)
        except (TypeError, ValueError) as exc:
            raise ManifestValidationError(str(exc)) from exc

        self._log(f"latest.json 解析成功，最新版本: {manifest.version}")
        return manifest

    def is_update_available(self, manifest: LatestManifest) -> bool:
        """判断 manifest 是否比当前版本新"""

        try:
            return self._compare_versions(manifest.version, self.current_version) > 0
        except Exception as exc:  # pragma: no cover - 非常规版本号
            raise VersionCompareError(f"比较版本号失败: {exc}") from exc

    def download_release(
        self,
        manifest: LatestManifest,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> DownloadResult:
        """下载安装包并进行 SHA-256 校验"""

        self._cancel_event.clear()

        target_dir = self._resolve_download_dir()
        os.makedirs(target_dir, exist_ok=True)

        filename = self._determine_filename(manifest)
        target_path = os.path.join(target_dir, filename)

        # 智能选择最佳下载URL
        download_url = self._select_best_download_url(manifest)
        request = urllib.request.Request(download_url, headers={"User-Agent": self.USER_AGENT})

        self._log(f"开始下载安装包: {download_url}")

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise DownloadError(f"下载失败，HTTP {response.status}")

                total_size = self._extract_content_length(response)
                hasher = hashlib.sha256()
                downloaded = 0

                with open(target_path, "wb") as file_obj:
                    while not self._cancel_event.is_set():
                        chunk = response.read(self.chunk_size)
                        if not chunk:
                            break
                        file_obj.write(chunk)
                        hasher.update(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_size)

                if self._cancel_event.is_set():
                    try:
                        os.remove(target_path)
                    except FileNotFoundError:
                        pass
                    raise DownloadError("下载被取消")

        except urllib.error.HTTPError as exc:  # pragma: no cover - 网络错误难以覆盖
            raise DownloadError(f"下载失败，HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:  # pragma: no cover - 网络错误难以覆盖
            raise DownloadError(f"无法下载安装包: {exc.reason}") from exc
        except TimeoutError as exc:  # pragma: no cover
            raise DownloadError("下载超时") from exc

        digest = hasher.hexdigest()
        expected = manifest.sha256.lower()

        if expected and digest.lower() != expected:
            try:
                os.remove(target_path)
            except FileNotFoundError:
                pass
            raise IntegrityError("安装包SHA-256校验失败")

        file_size = os.path.getsize(target_path)
        self._log(f"安装包下载完成，大小 {file_size} 字节")
        return DownloadResult(file_path=target_path, file_size=file_size, sha256=digest)

    def cancel_download(self) -> None:
        """请求取消当前下载"""

        self._cancel_event.set()

    # ------------------------------------------------------------------
    # 内部工具函数
    # ------------------------------------------------------------------
    def _compare_versions(self, new_version: str, current_version: str) -> int:
        """对比版本号大小，返回 1/0/-1"""

        new_parts = self._normalize_version(new_version)
        current_parts = self._normalize_version(current_version)

        max_len = max(len(new_parts), len(current_parts))
        new_parts += (0,) * (max_len - len(new_parts))
        current_parts += (0,) * (max_len - len(current_parts))

        for new_value, current_value in zip(new_parts, current_parts):
            if new_value > current_value:
                return 1
            if new_value < current_value:
                return -1
        return 0

    def _normalize_version(self, version: str) -> Tuple[int, ...]:
        """将版本号转换为整数元组"""

        if not version:
            return (0,)

        parts = []
        for token in version.replace("-", ".").split("."):
            if not token:
                continue
            numeric = ''.join(ch for ch in token if ch.isdigit())
            if numeric:
                parts.append(int(numeric))
            else:
                parts.append(0)

        return tuple(parts) or (0,)

    def _resolve_download_dir(self) -> str:
        """获取下载目录，没有配置则使用临时目录"""

        configured_dir = (self.tool_config.get("update_download_dir") or "").strip()
        if configured_dir:
            return configured_dir

        return os.path.abspath(os.getcwd())

    def _determine_filename(self, manifest: LatestManifest) -> str:
        """根据 manifest 和 URL 推断文件名"""

        if manifest.file_name:
            return manifest.file_name

        parsed = urllib.parse.urlparse(manifest.download_url)
        basename = os.path.basename(parsed.path)
        if basename:
            return basename

        return f"MobileTestTool_{manifest.version}.exe"

    def _extract_content_length(self, response: Any) -> Optional[int]:
        """从响应头中提取 Content-Length"""

        length_value: Union[str, None] = response.headers.get("Content-Length")
        if not length_value:
            return None

        try:
            return int(length_value)
        except (TypeError, ValueError):
            return None

    def _log(self, message: str) -> None:
        if callable(self.logger):
            try:
                self.logger(message)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # 下载源选择相关方法
    # ------------------------------------------------------------------
    def _detect_region(self) -> str:
        """检测用户所在地区（基于时区）"""
        
        if self._detected_region:
            return self._detected_region
        
        try:
            # 获取系统时区
            if platform.system() == "Windows":
                import winreg
                try:
                    key = winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation"
                    )
                    timezone_name = winreg.QueryValueEx(key, "TimeZoneKeyName")[0]
                    winreg.CloseKey(key)
                    
                    # 判断是否为中国时区
                    if "China" in timezone_name or "Beijing" in timezone_name or "Shanghai" in timezone_name:
                        self._detected_region = "cn"
                        return "cn"
                except Exception:
                    pass
            else:
                # Linux/Mac: 读取 /etc/timezone 或使用环境变量
                try:
                    import subprocess
                    result = subprocess.run(
                        ["timedatectl", "show", "--property=Timezone", "--value"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0:
                        tz = result.stdout.strip()
                        if "Asia/Shanghai" in tz or "Asia/Beijing" in tz or "Asia/Chongqing" in tz:
                            self._detected_region = "cn"
                            return "cn"
                except Exception:
                    pass
            
            # 尝试通过IP地理位置检测（可选，需要网络请求）
            # 这里使用简单的时区判断，如果需要更准确可以调用IP地理位置API
            offset = time.timezone if (time.daylight == 0) else time.altzone
            # UTC+8 通常是中国的时区
            if offset == -28800:  # UTC+8
                self._detected_region = "cn"
                return "cn"
            
        except Exception:
            pass
        
        # 默认返回 "default" 或 "us"
        self._detected_region = "default"
        return "default"

    def _detect_platform(self) -> str:
        """检测当前运行平台"""
        
        if self._detected_platform:
            return self._detected_platform
        
        system = platform.system().lower()
        if system == "windows":
            self._detected_platform = "windows"
        elif system == "darwin":
            self._detected_platform = "mac"
        elif system == "linux":
            self._detected_platform = "linux"
        else:
            self._detected_platform = "all"
        
        return self._detected_platform

    def _select_best_download_url(self, manifest: LatestManifest) -> str:
        """根据用户地区和平台选择最佳下载URL"""
        
        # 如果没有配置多个下载源，使用默认URL
        if not manifest.download_urls:
            return manifest.download_url
        
        detected_region = self._detect_region()
        detected_platform = self._detect_platform()
        
        self._log(f"检测到地区: {detected_region}, 平台: {detected_platform}")
        
        # 评分系统：匹配度越高，分数越高
        best_source: Optional[DownloadSource] = None
        best_score = -1
        
        for source in manifest.download_urls:
            score = 0
            
            # 地区匹配评分
            if source.region:
                region_lower = source.region.lower()
                if region_lower == detected_region.lower():
                    score += 100  # 完全匹配（如 detected_region="cn" 匹配 region="cn"）
                elif region_lower == "default":
                    # 默认源：适用于所有未明确匹配的地区
                    # 如果用户地区是 "default"（其他国家），这个源会得到高分
                    if detected_region == "default":
                        score += 100  # 其他国家用户匹配 default 源
                    else:
                        score += 5   # 特定地区用户也可以使用 default 源，但优先级较低
            else:
                # 未指定地区：作为通用源，适用于所有地区
                score += 5  # 通用源，优先级较低
            
            # 平台匹配评分
            if source.platform:
                platform_lower = source.platform.lower()
                if platform_lower == detected_platform.lower():
                    score += 50  # 平台完全匹配
                elif platform_lower == "all":
                    score += 25  # 通用平台
            else:
                score += 25  # 未指定平台，作为通用源
            
            # 优先级加分
            score += source.priority
            
            if score > best_score:
                best_score = score
                best_source = source
        
        if best_source:
            self._log(f"选择下载源: {best_source.url} (评分: {best_score}, 地区: {best_source.region or '通用'}, 平台: {best_source.platform or '通用'})")
            return best_source.url
        
        # 如果所有源都不匹配（理论上不应该发生），使用默认URL
        self._log(f"未找到匹配的下载源，使用默认URL: {manifest.download_url}")
        return manifest.download_url


__all__ = [
    "UpdateManager",
    "DEFAULT_UPDATE_FEED_URL",
    "DownloadResult",
    "UpdateError",
    "ManifestFetchError",
    "ManifestValidationError",
    "VersionCompareError",
    "DownloadError",
    "IntegrityError",
]


