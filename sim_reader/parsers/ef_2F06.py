"""
EF_ARR (2F06) 解析器
依据：
  • ISO/IEC 7816‑4  Table 17 (Access mode byte for EFs)
  • ETSI TS 102 221   Table 9.3 (PIN / ADM mapping)
  • ETSI TS 101 220   Table 7.10 (Security‑Condition tags)
返回格式：
[
    {
        "Index": 1,
        "AC1": "DELETE/ACTIVATE/DEACTIVATE/UPDATE/ERASE/READ:ADM1",
        "AC2": "TERMINATE:NEVER"
    },
  ...
]
"""

import logging
from typing import List, Dict, Tuple

# ---------- 常量区 ---------- #
ACCESS_MODE_BITS: Tuple[Tuple[int, str], ...] = (
    (0x40, "DELETE"),
    (0x20, "TERMINATE"),
    (0x10, "ACTIVATE"),
    (0x08, "DEACTIVATE"),
    (0x04, "WRITE/APPEND"),
    (0x02, "UPDATE/ERASE"),
    (0x01, "READ"),
)

def keyref_to_condition(k: int) -> str:
    if 0x01 <= k <= 0x08:
        return f"PIN App {k}"
    if 0x0A <= k <= 0x0E:
        return f"ADM{k-0x09}"
    if k == 0x11:
        return "PIN Universal"
    if 0x81 <= k <= 0x88:
        return f"PIN2 App {k-0x80}"
    if 0x8A <= k <= 0x8E:
        return f"ADM{k-0x84}"
    return f"ADM/PIN ({k:02X})"



# ---------- BER‑TLV 工具 ---------- #
def _decode_len(buf: str, pos: int) -> Tuple[int, int]:
    if pos + 2 > len(buf):
        logging.debug("跳过无法读取长度字段的位置: pos=%d", pos)
        return 0, pos
    first_hex = buf[pos:pos+2]
    if not first_hex:
        logging.warning("长度字段为空: pos=%d", pos)
        return 0, pos
    first = int(first_hex, 16); pos += 2
    if first < 0x80:
        return first, pos
    n = first & 0x7F
    if pos + n*2 > len(buf):
        # logging.debug("长度字段超范围(pos=%d, n=%d), 停止本段解析", pos, n)
        return 0, pos
    length_hex = buf[pos:pos+n*2]
    if not length_hex:
        logging.warning("长度值为空: pos=%d, n=%d", pos, n)
        return 0, pos
    length = int(length_hex, 16)
    return length, pos + n*2


def _walk(buf: str):
    p = 0
    while p < len(buf):
        tag = buf[p:p+2].upper(); p += 2
        ln, p = _decode_len(buf, p)
        value = buf[p:p+ln*2].upper(); p += ln*2
        cons = (int(tag, 16) & 0x20) != 0
        yield tag, value, cons

# ---------- Access‑Rule 解析 ---------- #
def _decode_am(byte_hex: str) -> str:
    v = int(byte_hex, 16)
    return "/".join(name for bit, name in ACCESS_MODE_BITS if v & bit and bit != 0x04)

def parse_single_arr_record(rec_hex: str) -> List[Tuple[str, str]]:
    """返回 [(AccessModeStr, SecCondStr), ...]"""
    rules: List[Tuple[str, str]] = []
    pending_am = ""
    logging.debug("解析记录: %s", rec_hex)

    def _collect_sc(tag: str, val_hex: str):
        nonlocal pending_am
        if not pending_am:
            return
        if tag == "90":
            sc = "ALW"
        elif tag == "97":
            sc = "NEVER"
        elif tag == "A4":
            key_ref = None
            for t, v, _ in _walk(val_hex):
                if t == "83" and len(v) == 2:
                    key_ref = int(v, 16); break
            sc = keyref_to_condition(key_ref) if key_ref is not None else "UNKNOWN"
        else:
            return
        rules.append((pending_am, sc))
        pending_am = ""

    for tag, val, cons in _walk(rec_hex):
        if tag == "80" and len(val) == 2:
            pending_am = _decode_am(val)
        elif tag in ("90", "97", "A4"):
            _collect_sc(tag, val)
        if cons and tag != "A4":
            for t2, v2, c2 in _walk(val):
                if t2 in ("90", "97", "A4"):
                    _collect_sc(t2, v2)

    if pending_am:  # dangling
        rules.append((pending_am, "UNKNOWN"))
    return rules

# ---------- 外部接口 ---------- #
def parse_data(raw_records: List[str]) -> List[Dict[str, str]]:
    output = []
    for idx, rec in enumerate(raw_records, 1):
        rules = parse_single_arr_record(rec)          # [(Access,Condition), ...]
        d: Dict[str, str] = {"Index": idx}

        # 把已有规则写入 AC1..AC5
        for i in range(1, 6):
            if i <= len(rules):
                am, sc = rules[i-1]
                d[f"AC{i}"] = f"{am}:{sc}"
            else:
                d[f"AC{i}"] = ""                      # 不足 5 条时补空串

        output.append(d)
    return output


def encode_data(user_data: str,ef_file_len_decimal: int) -> str:
    try:
        encode_userdata = user_data.get('raw_data', '')
        if len(encode_userdata) <= ef_file_len_decimal * 2:
            # Pad with 'F' if the length is less than required
            encode_userdata = encode_userdata.ljust(ef_file_len_decimal * 2, 'F')
        else:
            logging.debug("Raw data longer than current EF (%d >%d),resize in write_data()",
                          len(encode_userdata) // 2, ef_file_len_decimal)
        return encode_userdata
            
    except Exception as e:
        encode_userdata = f"error: 未知错误 - {str(e)}"
        return encode_userdata    
