from SIM_APDU_Parser.core.models import MsgType, ParseNode
from SIM_APDU_Parser.core.registry import register
from SIM_APDU_Parser.core.tlv import parse_ber_tlvs

@register(MsgType.ESIM, "BF30")
class BF30Parser:
    """NotificationSent - 通知发送"""
    def build(self, payload_hex: str, direction: str) -> ParseNode:
        dir_norm = (direction or "").lower()
        if dir_norm in ("lpa=>esim", "tx"):
            return self._parse_request(payload_hex)
        else:
            return self._parse_response(payload_hex)

    # ---------- Request ----------
    def _parse_request(self, payload_hex: str) -> ParseNode:
        root = ParseNode(name="BF30: NotificationSentRequest")
        tlvs = parse_ber_tlvs(payload_hex)

        for t in tlvs:
            if t.tag == "80":  # context [0] - seqNumber
                try:
                    seq_num = int(t.value_hex or "0", 16)
                    root.children.append(ParseNode(
                        name="seqNumber", 
                        value=str(seq_num),
                        hint=f"INTEGER({t.tag}): {t.value_hex}"
                    ))
                except Exception:
                    root.children.append(ParseNode(
                        name="seqNumber", 
                        value=t.value_hex,
                        hint=f"INTEGER({t.tag}) parse failed"
                    ))
            else:
                root.children.append(ParseNode(
                    name=f"TLV {t.tag}", 
                    value=f"len={t.length}", 
                    hint=t.value_hex[:120]
                ))
        return root

    # ---------- Response ----------
    def _parse_response(self, payload_hex: str) -> ParseNode:
        root = ParseNode(name="BF30: NotificationSentResponse")
        tlvs = parse_ber_tlvs(payload_hex)

        # 状态映射表
        status_map = {
            0: "ok",
            1: "nothingToDelete", 
            127: "undefinedError"
        }

        for t in tlvs:
            if t.tag == "80":  # context [0] - deleteNotificationStatus
                try:
                    status_val = int(t.value_hex or "0", 16)
                    status_name = status_map.get(status_val, f"Unknown({status_val})")
                    root.children.append(ParseNode(
                        name="deleteNotificationStatus", 
                        value=f"{status_name}({status_val})",
                        hint=f"INTEGER({t.tag}): {t.value_hex}"
                    ))
                except Exception:
                    root.children.append(ParseNode(
                        name="deleteNotificationStatus", 
                        value=t.value_hex,
                        hint=f"INTEGER({t.tag}) parse failed"
                    ))
            else:
                root.children.append(ParseNode(
                    name=f"TLV {t.tag}", 
                    value=f"len={t.length}", 
                    hint=t.value_hex[:120]
                ))
        return root
