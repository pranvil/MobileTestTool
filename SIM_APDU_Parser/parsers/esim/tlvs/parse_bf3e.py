from SIM_APDU_Parser.core.models import MsgType, ParseNode
from SIM_APDU_Parser.core.registry import register
from SIM_APDU_Parser.core.tlv import parse_ber_tlvs
from SIM_APDU_Parser.core.utils import parse_iccid, hex_to_utf8

def _decode_taglist_hex(taglist_hex: str):
    """解析标签列表，复用BF2D中的逻辑"""
    s = taglist_hex.upper().replace(" ", "")
    idx = 0; n = len(s); out = []
    
    # Tag meaning mapping
    tag_meaning_map = {
        "5A": "EID",
        "5B": "EID",
        "5C": "Tag List",
        "5D": "Profile Info List",
        "5E": "Profile Info List",
        "5F": "Profile Info List",
        "BF2D": "Profile Info List",
        "BF3E": "GetEuiccData",
        "BF3F": "GetEuiccData",
        "BF40": "GetEuiccData",
        "BF41": "GetEuiccData",
        "BF42": "GetEuiccData",
        "BF43": "GetEuiccData",
        "BF44": "GetEuiccData",
        "BF45": "GetEuiccData",
        "BF46": "GetEuiccData",
        "BF47": "GetEuiccData",
        "BF48": "GetEuiccData",
        "BF49": "GetEuiccData",
        "BF4A": "GetEuiccData",
        "BF4B": "GetEuiccData",
        "BF4C": "GetEuiccData",
        "BF4D": "GetEuiccData",
        "BF4E": "GetEuiccData",
        "BF4F": "GetEuiccData",
        "BF50": "GetEuiccData",
        "BF51": "GetEuiccData",
        "BF52": "GetEuiccData",
        "BF53": "GetEuiccData",
        "BF54": "GetEuiccData",
        "BF55": "GetEuiccData",
        "BF56": "GetEuiccData",
        "BF57": "GetEuiccData",
        "BF58": "GetEuiccData",
        "BF59": "GetEuiccData",
        "BF5A": "GetEuiccData",
        "BF5B": "GetEuiccData",
        "BF5C": "GetEuiccData",
        "BF5D": "GetEuiccData",
        "BF5E": "GetEuiccData",
        "BF5F": "GetEuiccData",
        "BF60": "GetEuiccData",
        "BF61": "GetEuiccData",
        "BF62": "GetEuiccData",
        "BF63": "GetEuiccData",
        "BF64": "GetEuiccData",
        "BF65": "GetEuiccData",
        "BF66": "GetEuiccData",
        "BF67": "GetEuiccData",
        "BF68": "GetEuiccData",
        "BF69": "GetEuiccData",
        "BF6A": "GetEuiccData",
        "BF6B": "GetEuiccData",
        "BF6C": "GetEuiccData",
        "BF6D": "GetEuiccData",
        "BF6E": "GetEuiccData",
        "BF6F": "GetEuiccData",
        "BF70": "GetEuiccData",
        "BF71": "GetEuiccData",
        "BF72": "GetEuiccData",
        "BF73": "GetEuiccData",
        "BF74": "GetEuiccData",
        "BF75": "GetEuiccData",
        "BF76": "GetEuiccData",
        "BF77": "GetEuiccData",
        "BF78": "GetEuiccData",
        "BF79": "GetEuiccData",
        "BF7A": "GetEuiccData",
        "BF7B": "GetEuiccData",
        "BF7C": "GetEuiccData",
        "BF7D": "GetEuiccData",
        "BF7E": "GetEuiccData",
        "BF7F": "GetEuiccData",
    }
    
    while idx < n:
        if idx+2>n: break
        t1 = s[idx:idx+2]; idx += 2
        if t1 in ("9F","BF","5F","7F") and idx+2<=n:
            t2 = s[idx:idx+2]; idx += 2
            tag = t1+t2
        else:
            tag = t1
        meaning = tag_meaning_map.get(tag, "Unknown")
        out.append((tag, meaning))
    return out

@register(MsgType.ESIM, "BF3E")
class BF3EParser:
    def build(self, payload_hex: str, direction: str) -> ParseNode:
        if direction == "LPA=>ESIM":  # Request
            return self._parse_request(payload_hex)
        else:  # Response (ESIM=>LPA)
            return self._parse_response(payload_hex)
    
    def _parse_request(self, payload_hex: str) -> ParseNode:
        """解析GetEuiccDataRequest"""
        root = ParseNode(name="BF3E: GetEuiccDataRequest")
        
        if payload_hex == "00":
            root.hint = "Default request (BF3E 00)"
            return root
            
        tlvs = parse_ber_tlvs(payload_hex)
        for t in tlvs:
            if t.tag == "5C":
                # Tag List - 根据ASN.1定义，值应该是'5A'表示请求EID
                if t.value_hex == "5A":
                    root.children.append(ParseNode(name="Tag List (5C)", value="EID"))
                else:
                    # 如果不是简单的'5A'，则解析标签列表
                    tag_pairs = _decode_taglist_hex(t.value_hex)
                    tag_list = [f"{tag}({meaning})" for tag, meaning in tag_pairs]
                    sub = ParseNode(name="Tag List (5C)", value=", ".join(tag_list))
                    for tag, meaning in tag_pairs:
                        sub.children.append(ParseNode(name=f"Tag {tag}", value=meaning))
                    root.children.append(sub)
            else:
                root.children.append(ParseNode(name=f"Unknown TLV {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
        
        return root
    
    def _parse_response(self, payload_hex: str) -> ParseNode:
        """解析GetEuiccDataResponse"""
        root = ParseNode(name="BF3E: GetEuiccDataResponse")
        
        tlvs = parse_ber_tlvs(payload_hex)
        for t in tlvs:
            if t.tag == "5A":
                # EID Value - 16字节的EID
                eid_value = t.value_hex
                if len(eid_value) == 32:  # 16字节 = 32个十六进制字符
                    # 格式化EID显示
                    formatted_eid = " ".join([eid_value[i:i+2] for i in range(0, len(eid_value), 2)])
                    root.children.append(ParseNode(name="EID Value (5A)", value=formatted_eid))
                else:
                    root.children.append(ParseNode(name="EID Value (5A)", value=eid_value, hint="Invalid EID length"))
            else:
                root.children.append(ParseNode(name=f"Unknown TLV {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
        
        return root
