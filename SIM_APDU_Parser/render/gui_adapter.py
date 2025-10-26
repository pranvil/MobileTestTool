
from typing import List, Dict
from SIM_APDU_Parser.core.models import ParseResult, MsgType

def to_gui_events(results: List[ParseResult], show_normal_sim: bool = False, allowed_types: list[str] | None = None) -> List[Dict]:
    events: List[Dict] = []
    allowed = set([t.lower() for t in (allowed_types or [])])
    for r in results:
        if allowed:
            if r.msg_type.value not in allowed:
                continue
        else:
            if r.msg_type == MsgType.NORMAL_SIM and not show_normal_sim:
                continue
        if r.msg_type == MsgType.UNKNOWN:
            continue
        # GUI expects: kind, direction, tag, title, raw, parser_hint, parse_result
        events.append({
            "kind": r.msg_type.value,
            "direction": r.direction_hint,   # ASCII arrows, used by GUI for colors
            "tag": r.tag or "",
            "title": r.title,
            "raw": r.message.raw,
            "parser_hint": (r.tag or "").lower(),
            "parse_result": r  # 保存完整的解析结果
        })
    return events
