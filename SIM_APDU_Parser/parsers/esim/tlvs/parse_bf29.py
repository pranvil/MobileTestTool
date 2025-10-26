from SIM_APDU_Parser.core.models import MsgType, ParseNode
from SIM_APDU_Parser.core.registry import register
from SIM_APDU_Parser.core.tlv import parse_ber_tlvs
from SIM_APDU_Parser.core.utils import parse_iccid, hex_to_utf8

@register(MsgType.ESIM, "BF29")
class BF29Parser:
    """SetNickname - 设置配置文件昵称"""
    def build(self, payload_hex: str, direction: str) -> ParseNode:
        dir_norm = (direction or "").lower()
        if dir_norm in ("lpa=>esim", "tx"):
            return self._parse_request(payload_hex)
        else:
            return self._parse_response(payload_hex)

    # ---------- Request ----------
    def _parse_request(self, payload_hex: str) -> ParseNode:
        """解析SetNicknameRequest"""
        root = ParseNode(name="BF29: SetNicknameRequest")
        tlvs = parse_ber_tlvs(payload_hex)

        for t in tlvs:
            if t.tag == "5A":  # iccid Iccid (APPLICATION 26)
                iccid = parse_iccid(t.value_hex)
                root.children.append(ParseNode(name="iccid", value=iccid, hint=f"Raw: {t.value_hex}"))
            
            elif t.tag == "90":  # profileNickname [16] UTF8String (AUTOMATIC TAGS [16] -> 0x90)
                try:
                    nickname = hex_to_utf8(t.value_hex)
                    if nickname:
                        root.children.append(ParseNode(name="profileNickname", value=nickname, hint=f"UTF8String({t.tag}): {t.value_hex}"))
                    else:
                        root.children.append(ParseNode(name="profileNickname", value=t.value_hex, hint=f"UTF8String({t.tag}) decode failed"))
                except Exception:
                    root.children.append(ParseNode(name="profileNickname", value=t.value_hex, hint=f"UTF8String({t.tag}) parse error"))
            
            elif t.tag == "0C":  # 兼容 UNIVERSAL UTF8String 编码
                try:
                    nickname = hex_to_utf8(t.value_hex)
                    if nickname:
                        root.children.append(ParseNode(name="profileNickname", value=nickname, hint=f"UTF8String({t.tag}): {t.value_hex}"))
                    else:
                        root.children.append(ParseNode(name="profileNickname", value=t.value_hex, hint=f"UTF8String({t.tag}) decode failed"))
                except Exception:
                    root.children.append(ParseNode(name="profileNickname", value=t.value_hex, hint=f"UTF8String({t.tag}) parse error"))
            
            else:
                root.children.append(ParseNode(name=f"TLV {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))

        return root

    # ---------- Response ----------
    def _parse_response(self, payload_hex: str) -> ParseNode:
        """解析SetNicknameResponse"""
        root = ParseNode(name="BF29: SetNicknameResponse")
        tlvs = parse_ber_tlvs(payload_hex)

        # 结果映射表
        result_map = {
            0: "ok",
            1: "iccidNotFound", 
            127: "undefinedError"
        }

        for t in tlvs:
            if t.tag in ("80", "02"):  # setNicknameResult: context [0] 或 UNIVERSAL INTEGER
                try:
                    result_val = int(t.value_hex or "0", 16)
                    result_name = result_map.get(result_val, f"Unknown({result_val})")
                    root.children.append(ParseNode(
                        name="setNicknameResult", 
                        value=f"{result_name}({result_val})",
                        hint=f"INTEGER({t.tag}): {t.value_hex}"
                    ))
                except Exception:
                    root.children.append(ParseNode(
                        name="setNicknameResult", 
                        value=t.value_hex,
                        hint=f"INTEGER({t.tag}) parse failed"
                    ))
            else:
                root.children.append(ParseNode(name=f"TLV {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))

        return root
