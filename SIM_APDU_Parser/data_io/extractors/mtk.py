
import re
from typing import List, Tuple

from SIM_APDU_Parser.core.models import Message
from SIM_APDU_Parser.core.utils import normalize_hex
from asn1crypto import parser as asn1_parser


# -----------------------------
# Regex for MTK log blocks
# -----------------------------
# Original format: APDU_rx 0: 00 01 0C 0F...
APDU_RX0 = re.compile(r'^\s*APDU_rx\s+0:\s*([0-9A-Fa-f]{2}(?:\s+[0-9A-Fa-f]{2})*)\s*$')
APDU_TX0 = re.compile(r'^\s*APDU_tx\s+0:\s*([0-9A-Fa-f]{2}(?:\s+[0-9A-Fa-f]{2})*)\s*$')
APDU_RXN = re.compile(r'^\s*APDU_rx\s+([1-9]\d*):\s*([0-9A-Fa-f]{2}(?:\s+[0-9A-Fa-f]{2})*)\s*$')
APDU_TXN = re.compile(r'^\s*APDU_tx\s+(\d+):\s*([0-9A-Fa-f]{2}(?:\s+[0-9A-Fa-f]{2})*)\s*$')

# Table format: PS	1459556	256477358	14:19:29:080	SIM_2	APDU_rx 7: 00 01 0C 0F...
APDU_RX0_TABLE = re.compile(r'^[^\t]*\t[^\t]*\t[^\t]*\t[^\t]*\t[^\t]*\tAPDU_rx\s+0:\s*([0-9A-Fa-f]{2}(?:\s+[0-9A-Fa-f]{2})*)\s*$')
APDU_TX0_TABLE = re.compile(r'^[^\t]*\t[^\t]*\t[^\t]*\t[^\t]*\t[^\t]*\tAPDU_tx\s+0:\s*([0-9A-Fa-f]{2}(?:\s+[0-9A-Fa-f]{2})*)\s*$')
APDU_RXN_TABLE = re.compile(r'^[^\t]*\t[^\t]*\t[^\t]*\t[^\t]*\t[^\t]*\tAPDU_rx\s+([1-9]\d*):\s*([0-9A-Fa-f]{2}(?:\s+[0-9A-Fa-f]{2})*)\s*$')
APDU_TXN_TABLE = re.compile(r'^[^\t]*\t[^\t]*\t[^\t]*\t[^\t]*\t[^\t]*\tAPDU_tx\s+(\d+):\s*([0-9A-Fa-f]{2}(?:\s+[0-9A-Fa-f]{2})*)\s*$')


# -----------------------------
# Helpers: APDU classification & header
# -----------------------------
def _is_lpa_to_esim(apdu_hex: str) -> bool:
    """LPA=>eSIM long E2 (ESx) write chain (INS=E2, CLA in 80..83 / C0..CF)."""
    s = apdu_hex
    if len(s) < 8:
        return False
    cla = int(s[0:2], 16)
    ins = int(s[2:4], 16)
    return ((0x80 <= cla <= 0x83) or (0xC0 <= cla <= 0xCF)) and ins == 0xE2


def _parse_apdu_header(apdu_hex: str) -> Tuple[int, int, int, int]:
    """Return (CLA, INS, P1, P2) or zeros if too short."""
    s = apdu_hex
    if len(s) < 8:
        return 0, 0, 0, 0
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), int(s[6:8], 16)


def _is_get_response_tx(apdu_hex: str) -> bool:
    """INS == 0xC0 (GET RESPONSE). CLA can vary."""
    return len(apdu_hex) >= 4 and int(apdu_hex[2:4], 16) == 0xC0


def _is_status_61xx(rx_hex: str) -> bool:
    """SW1=0x61, 'xx' more bytes available."""
    return len(rx_hex) == 4 and rx_hex[:2].upper() == "61"


def _is_status_9000(rx_hex: str) -> bool:
    """SW=9000 OK."""
    return rx_hex.upper() == "9000"


def _collect_one(lines: List[str], i: int, head_re0, cont_re):
    """Collect a TX/RX group starting at current line index."""
    m0 = head_re0.match(lines[i])
    if not m0:
        return None, i
    parts = [m0.group(1)]
    i += 1
    while i < len(lines):
        mn = cont_re.match(lines[i])
        if mn:
            parts.append(mn.group(2))
            i += 1
        else:
            break
    return ' '.join(parts), i


def _collect_one_table(lines: List[str], i: int, head_re0, cont_re):
    """Collect a TX/RX group from table format starting at current line index."""
    m0 = head_re0.match(lines[i])
    if not m0:
        return None, i
    parts = [m0.group(1)]
    i += 1
    while i < len(lines):
        mn = cont_re.match(lines[i])
        if mn:
            parts.append(mn.group(2))
            i += 1
        else:
            break
    return ' '.join(parts), i


def _collect_rx_group_table_all(lines: List[str], i: int) -> Tuple[str, int, List[int]]:
    """Collect an RX group from table format, handling both 0 and non-0 indices."""
    # 首先尝试匹配当前行
    m0 = APDU_RX0_TABLE.match(lines[i])
    if m0:
        # 这是索引0的RX
        parts = [m0.group(1)]
        consumed = [i]
        i += 1
        while i < len(lines):
            mn = APDU_RXN_TABLE.match(lines[i])
            if mn:
                parts.append(mn.group(2))
                consumed.append(i)
                i += 1
            else:
                break
        return normalize_hex(" ".join(parts)), i, consumed
    
    # 尝试匹配非0索引的RX
    mn = APDU_RXN_TABLE.match(lines[i])
    if mn:
        parts = [mn.group(2)]
        consumed = [i]
        i += 1
        while i < len(lines):
            mn2 = APDU_RXN_TABLE.match(lines[i])
            if mn2:
                parts.append(mn2.group(2))
                consumed.append(i)
                i += 1
            else:
                break
        return normalize_hex(" ".join(parts)), i, consumed
    
    return "", i, []


def _collect_rx_group(lines: List[str], i: int) -> Tuple[str, int, List[int]]:
    """Collect an RX group and return (hex, next_index, consumed_line_indices)."""
    m0 = APDU_RX0.match(lines[i])
    if not m0:
        return "", i, []
    parts = [m0.group(1)]
    consumed = [i]
    i += 1
    while i < len(lines):
        mn = APDU_RXN.match(lines[i])
        if mn:
            parts.append(mn.group(2))
            consumed.append(i)
            i += 1
        else:
            break
    return normalize_hex(" ".join(parts)), i, consumed


def _collect_rx_group_table(lines: List[str], i: int) -> Tuple[str, int, List[int]]:
    """Collect an RX group from table format and return (hex, next_index, consumed_line_indices)."""
    m0 = APDU_RX0_TABLE.match(lines[i])
    if not m0:
        return "", i, []
    parts = [m0.group(1)]
    consumed = [i]
    i += 1
    while i < len(lines):
        mn = APDU_RXN_TABLE.match(lines[i])
        if mn:
            parts.append(mn.group(2))
            consumed.append(i)
            i += 1
        else:
            break
    return normalize_hex(" ".join(parts)), i, consumed


# -----------------------------
# eSIM TLV helpers
# -----------------------------
def _extract_esim_tag_and_length(apdu_hex: str) -> Tuple[str, int, int]:
    """
    From an LPA=>eSIM 'E2' APDU, extract (tag_hex, value_length, len_len_bytes)
    from the first TLV in the DATA field. Supports short/long length.
    """
    s = normalize_hex(apdu_hex)
    if len(s) < 10:
        return "", 0, 0
    data_start = 10  # skip 5-byte APDU header (CLA INS P1 P2 Lc)
    if len(s) < data_start + 2:
        return "", 0, 0

    # Tag may be 1 or >1 bytes (e.g. BFxx)
    tag = s[data_start:data_start+2]
    if tag in ("9F", "5F", "7F", "BF") and len(s) >= data_start + 4:
        tag = s[data_start:data_start+4]
        length_start = data_start + 4
    else:
        length_start = data_start + 2

    if len(s) < length_start + 2:
        return tag, 0, 0

    first_len_octet = int(s[length_start:length_start+2], 16)
    if first_len_octet < 0x80:
        value_len = first_len_octet
        len_len = 1
    else:
        n = first_len_octet & 0x7F
        if len(s) < length_start + 2 + 2*n:
            return tag, 0, 0
        value_len = int(s[length_start+2:length_start+2+2*n], 16)
        len_len = 1 + n
    return tag, value_len, len_len


def _rx_expected_total_len_from_tlv(first_rx_hex: str) -> int:
    """
    Try to determine the total TLV size (header+value) from the first RX chunk,
    using asn1crypto low-level parser. Returns 0 if unknown.
    """
    hs = first_rx_hex.replace(" ", "").replace("\n", "")
    if len(hs) % 2:
        hs = hs[:-1]
    try:
        data = bytes.fromhex(hs)
    except Exception:
        return 0
    try:
        info, _ = asn1_parser._parse(data, len(data), pointer=0, lengths_only=False, depth=0)
    except Exception:
        return 0
    _cls, _constructed, _tag_no, header, value, _ = info
    return len(header) + len(value)


def reassemble_e2_segments(segments: List[str], tag_hex: str) -> str:
    """Combine multiple E2 data segments into a single TLV: tag + new length + value."""
    if not segments:
        return ""
    norm_segments = [normalize_hex(s) for s in segments if s]
    first = norm_segments[0]
    if len(first) <= 10:
        return ""
    first_data = first[10:]
    if len(first_data) >= 2 and first_data[-2:] == "00":
        first_data = first_data[:-2]

    # tag/len in the first TLV
    tag_in_first, _val_len, len_len = _extract_esim_tag_and_length(first)
    tag_hex2 = tag_in_first or tag_hex
    tag_len = len(tag_hex2) // 2
    value_start = tag_len*2 + len_len*2
    if len(first_data) < value_start:
        return ""
    value_hex = first_data[value_start:]

    for seg in norm_segments[1:]:
        if len(seg) <= 10:
            continue
        data = seg[10:]
        if len(data) >= 2 and data[-2:] == "00":
            data = data[:-2]
        value_hex += data

    vlen = len(value_hex) // 2
    if vlen < 0x80:
        len_enc = f"{vlen:02X}"
    else:
        blen = (vlen.bit_length() + 7) // 8
        len_enc = f"{0x80 | blen:02X}" + vlen.to_bytes(blen, "big").hex().upper()
    header = first[:10]  # keep original 5-byte APDU header
    return header + (tag_hex2 or tag_hex) + len_enc + value_hex


# -----------------------------
# MTK extractor
# -----------------------------
class MTKExtractor:
    """
    Extract APDU_tx/APDU_rx groups from MTK logs.
    - Reassembles LPA=>eSIM E2 multi-part TX with interleaving tolerance
    - Reassembles RX streams that require GET RESPONSE (61xx ... C0 ... 9000)
    - Supports both original format and table format logs
    """

    def _detect_table_format(self, lines: List[str]) -> bool:
        """Detect if the log is in table format (tab-separated with APDU in Message column)."""
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            if '\t' in line and ('APDU_rx' in line or 'APDU_tx' in line):
                return True
        return False

    def extract_from_text(self, text: str) -> List[Message]:
        lines = text.splitlines()
        msgs: List[Message] = []
        i = 0
        processed_indices = set()  # only RX/TX group lines that were actually consumed
        
        # Detect if this is table format by checking first few lines
        is_table_format = self._detect_table_format(lines)

        while i < len(lines):
            if i in processed_indices:
                i += 1
                continue

            line = lines[i].strip()

            # TX groups
            if line.startswith("APDU_tx") or (is_table_format and "\tAPDU_tx" in line):
                if is_table_format:
                    r = _collect_one_table(lines, i, APDU_TX0_TABLE, APDU_TXN_TABLE)
                else:
                    r = _collect_one(lines, i, APDU_TX0, APDU_TXN)
                if r[0] is not None:
                    raw, next_i = r
                    s = normalize_hex(raw) if raw else ""
                    if s and _is_lpa_to_esim(s):
                        reassembled, used = self._try_reassemble_lpa_esim(lines, i, s, is_table_format)
                        if reassembled and len(used) > 1:
                            msgs.append(Message(raw=reassembled, direction="tx",
                                                meta={"source": "mtk", "reassembled": True,
                                                      "segments": used}))
                            # mark consumed TX lines only
                            for idx in used:
                                processed_indices.add(idx)
                            i += 1
                            continue
                        else:
                            msgs.append(Message(raw=s, direction="tx", meta={"source": "mtk"}))
                            # mark current TX block lines as processed to avoid re-reading
                            for idx in range(i, next_i):
                                processed_indices.add(idx)
                            i += 1
                            continue
                    else:
                        msgs.append(Message(raw=s, direction="tx", meta={"source": "mtk"}))
                        for idx in range(i, next_i):
                            processed_indices.add(idx)
                        i += 1
                        continue

            # RX groups
            elif line.startswith("APDU_rx") or (is_table_format and "\tAPDU_rx" in line):
                if is_table_format:
                    s, next_i, consumed_rx = _collect_rx_group_table_all(lines, i)
                    if s:
                        # Attempt GET RESPONSE reassembly for "data" (not pure 61xx/9000)
                        if not _is_status_61xx(s) and not _is_status_9000(s):
                            assembled, consumed_rx = self._try_reassemble_rx_get_response(lines, i, s, next_i, is_table_format)
                            msgs.append(Message(raw=assembled, direction="rx",
                                                meta={"source": "mtk",
                                                      "rx_reassembled": len(consumed_rx) > 0,
                                                      "segments": consumed_rx}))
                            for idx in consumed_rx:
                                processed_indices.add(idx)
                            i += 1
                            continue
                        else:
                            msgs.append(Message(raw=s, direction="rx", meta={"source": "mtk"}))
                            for idx in consumed_rx:
                                processed_indices.add(idx)
                            i += 1
                            continue
                else:
                    raw, next_i = _collect_one(lines, i, APDU_RX0, APDU_RXN)
                    if raw is not None:
                        s = normalize_hex(raw) if raw else ""
                        if s:
                            # Attempt GET RESPONSE reassembly for "data" (not pure 61xx/9000)
                            if not _is_status_61xx(s) and not _is_status_9000(s):
                                assembled, consumed_rx = self._try_reassemble_rx_get_response(lines, i, s, next_i, is_table_format)
                                msgs.append(Message(raw=assembled, direction="rx",
                                                    meta={"source": "mtk",
                                                          "rx_reassembled": len(consumed_rx) > 0,
                                                          "segments": consumed_rx}))
                                for idx in consumed_rx:
                                    processed_indices.add(idx)
                                i += 1
                                continue
                            else:
                                msgs.append(Message(raw=s, direction="rx", meta={"source": "mtk"}))
                                for idx in range(i, next_i):
                                    processed_indices.add(idx)
                                i += 1
                                continue

            # non-matching line or already processed
            i += 1

        return msgs

    # -------------------------
    # Reassemble LPA=>eSIM E2 TX chain with interleaving tolerance
    # -------------------------
    def _try_reassemble_lpa_esim(self, lines: List[str], start_idx: int, first_apdu: str, is_table_format: bool = False) -> Tuple[str, List[int]]:
        first_apdu = normalize_hex(first_apdu)
        cla0, ins0, p10, p20 = _parse_apdu_header(first_apdu)
        if not _is_lpa_to_esim(first_apdu):
            return first_apdu, [start_idx]

        # Read first tag and expected total value length (for stop-by-size)
        tag_hex, expected_total_len, _ = _extract_esim_tag_and_length(first_apdu)
        if not tag_hex:
            return first_apdu, [start_idx]

        def _payload_len_of_segment(apdu_hex: str) -> int:
            if len(apdu_hex) <= 10:
                return 0
            data = apdu_hex[10:]
            if len(data) >= 2 and data[-2:] == "00":
                data = data[:-2]
            return len(data) // 2

        segments = [first_apdu]
        consumed = [start_idx]
        expected_p2 = p20
        found_last = (p10 == 0x91)
        collected_value_len = _payload_len_of_segment(first_apdu)

        MAX_LOOKAHEAD_GROUPS = 200
        i = start_idx + 1
        looked_groups = 0

        while i < len(lines) and not found_last and looked_groups < MAX_LOOKAHEAD_GROUPS:
            line = lines[i].rstrip("\n")

            # only consider new TX blocks; skip RX and others
            if is_table_format:
                m0 = APDU_TX0_TABLE.match(line)
                if not m0:
                    i += 1
                    continue
                seg_start = i
                parts = [m0.group(1)]
                i += 1
                while i < len(lines):
                    mn = APDU_TXN_TABLE.match(lines[i])
                    if mn:
                        parts.append(mn.group(2))
                        i += 1
                    else:
                        break
            else:
                m0 = APDU_TX0.match(line)
                if not m0:
                    i += 1
                    continue
                seg_start = i
                parts = [m0.group(1)]
                i += 1
                while i < len(lines):
                    mn = APDU_TXN.match(lines[i])
                    if mn:
                        parts.append(mn.group(2))
                        i += 1
                    else:
                        break
            looked_groups += 1

            apdu_hex = normalize_hex(" ".join(parts))
            cla, ins, p1, p2 = _parse_apdu_header(apdu_hex)

            is_candidate = (
                cla == cla0 and ins == ins0 and
                (p1 in (0x11, 0x91)) and
                ((p2 == expected_p2 + 1) or (expected_p2 == 0 and p2 == 1))
            )
            if not is_candidate:
                # unrelated TX group; keep scanning
                continue

            # merge this segment
            segments.append(apdu_hex)
            consumed.extend(range(seg_start, i))
            expected_p2 = p2
            found_last = (p1 == 0x91)
            collected_value_len += _payload_len_of_segment(apdu_hex)

            if expected_total_len and collected_value_len >= expected_total_len:
                found_last = True
                break

        if len(segments) > 1:
            reassembled = reassemble_e2_segments(segments, tag_hex)
            return reassembled, consumed

        return first_apdu, [start_idx]

    # -------------------------
    # Reassemble RX chain: 61xx -> (GET RESPONSE) -> data ... -> 9000
    # -------------------------
    def _try_reassemble_rx_get_response(self, lines: List[str],
                                        start_idx: int,
                                        first_rx_hex: str,
                                        next_i: int,
                                        is_table_format: bool = False) -> Tuple[str, List[int]]:
        # 检查第一个RX数据是否为6100状态码，如果是则跳过
        if _is_status_61xx(first_rx_hex):
            assembled = ""
            consumed_rx = list(range(start_idx, next_i))
            expected_total = 0
            wait_for_next_data = True
        else:
            assembled = first_rx_hex
            consumed_rx = list(range(start_idx, next_i))
            expected_total = _rx_expected_total_len_from_tlv(first_rx_hex)
            wait_for_next_data = False

        i = next_i
        LOOKAHEAD_LIMIT = 2000
        steps = 0

        while i < len(lines) and steps < LOOKAHEAD_LIMIT:
            steps += 1
            line = lines[i].strip()

            if line.startswith("APDU_rx:len"):
                i += 1
                continue

            if line.startswith("APDU_rx 0:") or (is_table_format and "\tAPDU_rx 0:" in line):
                if is_table_format:
                    rx_hex, next_j, rx_used = _collect_rx_group_table(lines, i)
                else:
                    rx_hex, next_j, rx_used = _collect_rx_group(lines, i)
                if not rx_hex:
                    i += 1
                    continue

                if _is_status_61xx(rx_hex):
                    consumed_rx.extend(rx_used)
                    wait_for_next_data = True
                    i = next_j
                    continue

                if _is_status_9000(rx_hex):
                    consumed_rx.extend(rx_used)
                    break

                if wait_for_next_data:
                    assembled += rx_hex
                    consumed_rx.extend(rx_used)
                    wait_for_next_data = False
                    if expected_total and len(bytes.fromhex(assembled)) >= expected_total:
                        break
                    i = next_j
                    continue

                # Another RX data chunk without GET RESPONSE in between - allow merge (logs sometimes split)
                # 但是要排除状态码，因为它们不应该被拼接
                if not _is_status_61xx(rx_hex) and not _is_status_9000(rx_hex):
                    assembled += rx_hex
                    consumed_rx.extend(rx_used)
                    if expected_total and len(bytes.fromhex(assembled)) >= expected_total:
                        break
                    i = next_j
                    continue
                else:
                    # 这是状态码，不应该被拼接，但需要标记为已消费
                    consumed_rx.extend(rx_used)
                    if _is_status_9000(rx_hex):
                        break
                    i = next_j
                    continue

            if line.startswith("APDU_tx") or (is_table_format and "\tAPDU_tx" in line):
                # Collect the TX block but do NOT consume it (we want to show it separately)
                if is_table_format:
                    tx_raw, tx_next = _collect_one_table(lines, i, APDU_TX0_TABLE, APDU_TXN_TABLE)
                else:
                    tx_raw, tx_next = _collect_one(lines, i, APDU_TX0, APDU_TXN)
                tx_hex = normalize_hex(tx_raw) if tx_raw else ""
                if tx_hex and _is_get_response_tx(tx_hex):
                    i = tx_next
                    continue
                else:
                    # concurrent unrelated TX - conservatively stop
                    break

            i += 1

        return assembled, sorted(set(consumed_rx))
