#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PCAT NV 读写封装（Qualcomm NV Browser / NB 插件）

注意：
- READ 不支持 -JSON 参数
- WRITE 在多字段场景需要 -JSON True，并且 -VALUE 后面传入 JSON-like 字符串（示例：{nam:0, mode:'Digital Only'}）
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple


@dataclass
class PcatResult:
    cmd: Sequence[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return (self.stdout or "") + ("\n" if self.stdout and self.stderr else "") + (self.stderr or "")


class PcatError(RuntimeError):
    pass


_RE_NV_VALUE = re.compile(r"NV\s*value\s*-\s*(.+)", re.IGNORECASE)
_RE_STATUS_TRUE = re.compile(r"Status\s*-\s*TRUE", re.IGNORECASE)
_RE_SUCCESS = re.compile(r"\bSUCCESS\b", re.IGNORECASE)
_RE_READ_SUCCESS = re.compile(r"\bread\s+successfully\b", re.IGNORECASE)
_RE_WRITE_SUCCESS = re.compile(r"\bwrite\s+successfully\b", re.IGNORECASE)


def build_read_cmd(device_id: str, nv_item: str, sub_id: int) -> list[str]:
    cmd = ["PCAT", "-PLUGIN", "NB", "-DEVICE", device_id, "-MODE", "READ", "-NVITEM", str(nv_item)]
    cmd += ["-SUB", str(sub_id)]
    return cmd


def build_write_cmd(device_id: str, nv_item: str, sub_id: int, value: str, use_json: bool) -> list[str]:
    """
    构建 PCAT WRITE 命令
    
    注意：当 use_json=True 时，value 应该是 JSON-like 字符串，例如 {cAPNWWAN:'vzwapp1'}
    值部分应该用引号包裹（单引号或双引号都可以）
    """
    cmd = ["PCAT", "-PLUGIN", "NB", "-DEVICE", device_id, "-MODE", "WRITE", "-NVITEM", str(nv_item)]
    cmd += ["-SUB", str(sub_id)]
    if use_json:
        cmd += ["-JSON", "True"]
    # 直接传递 value，subprocess 会自动处理特殊字符
    # 但确保 value 已经是完整的 JSON-like 字符串（如 {key:'value'}）
    cmd += ["-VALUE", str(value)]
    return cmd


def build_reset_cmd(device_id: str) -> list[str]:
    """构建 PCAT RESET 命令（重启设备）"""
    return ["PCAT", "-MODE", "RESET", "-DEVICE", device_id]


def run_pcat(cmd: Sequence[str], timeout: int = 60) -> PcatResult:
    try:
        completed = subprocess.run(
            list(cmd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        return PcatResult(cmd=cmd, returncode=completed.returncode, stdout=completed.stdout or "", stderr=completed.stderr or "")
    except FileNotFoundError as e:
        raise PcatError("未找到PCAT命令，请确认已安装并配置到PATH") from e
    except subprocess.TimeoutExpired as e:
        raise PcatError(f"PCAT执行超时（>{timeout}s）") from e
    except Exception as e:
        raise PcatError(f"PCAT执行异常: {e}") from e


def is_success(output: str) -> bool:
    if not output:
        return False
    return bool(_RE_STATUS_TRUE.search(output) or _RE_SUCCESS.search(output) or _RE_READ_SUCCESS.search(output) or _RE_WRITE_SUCCESS.search(output))


def extract_nv_value(output: str) -> Optional[str]:
    if not output:
        return None
    m = _RE_NV_VALUE.search(output)
    if not m:
        return None
    return m.group(1).strip()


def is_multi_value(value: Optional[str]) -> bool:
    if not value:
        return False
    # 经验规则：PCAT 读出的多字段值通常以逗号分隔（示例：0,vzwapp,1,...）
    return "," in value


def validate_json_like(input_text: str) -> Tuple[bool, str]:
    """
    宽松校验 PCAT 支持的 JSON-like 结构（非严格 JSON）：
    - 必须是 { ... } 包裹
    - 内部是逗号分隔的 key:value 对
    - key 允许下划线/数字（但建议以字母/下划线开头）
    - value 允许：
      - 整数（含负号）：如 123, -456
      - 引号包裹的字符串：如 'vzwapp1', "hello"（字符串值必须加引号）
      - 纯大写标识符/枚举：如 DigitalOnly, eQP_IMS_XXX（允许不带引号）
    """
    raw = (input_text or "").strip()
    if not (raw.startswith("{") and raw.endswith("}")):
        return False, "格式需以 { 开头并以 } 结尾"
    inner = raw[1:-1].strip()
    if ":" not in inner:
        return False, "格式需包含 key:value"
    if not inner:
        return False, "内容为空"

    parts = _split_top_level_commas(inner)
    for part in parts:
        seg = part.strip()
        if not seg:
            return False, "存在空字段"
        if ":" not in seg:
            return False, f"字段缺少冒号: {seg}"
        key, val = seg.split(":", 1)
        key = key.strip()
        val = val.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            return False, f"key格式不合法: {key}"
        if not _is_valid_value_token(val):
            return False, f"value格式不合法: {val}"

    return True, ""


def _split_top_level_commas(s: str) -> list[str]:
    """按顶层逗号切分，忽略引号内逗号。"""
    out: list[str] = []
    buf: list[str] = []
    in_single = False
    in_double = False
    escape = False

    for ch in s:
        if escape:
            buf.append(ch)
            escape = False
            continue

        if ch == "\\":
            buf.append(ch)
            escape = True
            continue

        if ch == "'" and not in_double:
            in_single = not in_single
            buf.append(ch)
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            buf.append(ch)
            continue

        if ch == "," and not in_single and not in_double:
            out.append("".join(buf))
            buf = []
            continue

        buf.append(ch)

    if buf:
        out.append("".join(buf))
    return out


def _is_valid_value_token(val: str) -> bool:
    """
    校验 value 格式：
    - 整数：允许（如 123, -456）
    - 引号包裹的字符串：允许（如 'vzwapp1', "hello"）
    - 字符串类型的值（包含字母数字组合）：必须有引号
    - 纯大写标识符/枚举：允许（如 DigitalOnly, eQP_IMS_XXX）
    """
    if not val:
        return False
    # 整数
    if re.fullmatch(r"-?\d+", val):
        return True
    # 单引号字符串
    if len(val) >= 2 and val[0] == "'" and val[-1] == "'":
        return True
    # 双引号字符串
    if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
        return True
    # 纯大写标识符/枚举（允许不带引号，如 DigitalOnly, eQP_IMS_XXX）
    # 但包含小写字母或数字组合的字符串值必须有引号
    if re.fullmatch(r"[A-Z_][A-Z0-9_]*", val):
        # 纯大写标识符，允许
        return True
    # 包含小写字母或数字的字符串值，必须用引号包裹
    if re.search(r"[a-z0-9]", val):
        return False  # 字符串值必须有引号
    # 其他情况（纯标识符但不全大写）：为了安全，也要求引号
    return False

