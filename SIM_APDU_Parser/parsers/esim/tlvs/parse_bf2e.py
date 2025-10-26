from SIM_APDU_Parser.core.models import MsgType, ParseNode
from SIM_APDU_Parser.core.registry import register
from SIM_APDU_Parser.core.tlv import parse_ber_tlvs

@register(MsgType.ESIM, "BF2E")
class BF2EParser:
    """GetEuiccChallenge - 获取eUICC挑战值"""
    def build(self, payload_hex: str, direction: str) -> ParseNode:
        root = ParseNode(name="BF2E: GetEuiccChallenge")
        tlvs = parse_ber_tlvs(payload_hex)
        
        if not tlvs:
            # 请求格式：空序列
            if direction == "LPA=>ESIM":
                root.hint = "GetEuiccChallengeRequest (empty sequence)"
            else:
                root.hint = "GetEuiccChallengeResponse (empty or malformed)"
            return root
        
        # 响应格式：包含euiccChallenge
        for t in tlvs:
            if t.tag == "04":  # OCTET STRING (Octet16)
                # euiccChallenge是16字节的随机挑战值
                challenge_hex = t.value_hex
                if len(challenge_hex) == 32:  # 16 bytes = 32 hex chars
                    root.children.append(ParseNode(
                        name="euiccChallenge", 
                        value=challenge_hex,
                        hint=f"16-byte random challenge: {challenge_hex[:16]}..."
                    ))
                else:
                    root.children.append(ParseNode(
                        name="euiccChallenge", 
                        value=challenge_hex,
                        hint=f"Invalid length: {len(challenge_hex)//2} bytes (expected 16)"
                    ))
            else:
                root.children.append(ParseNode(
                    name=f"Unknown TLV {t.tag}", 
                    value=f"len={t.length}", 
                    hint=t.value_hex[:120]
                ))
        
        return root
