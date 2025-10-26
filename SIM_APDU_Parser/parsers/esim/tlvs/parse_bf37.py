from SIM_APDU_Parser.core.models import MsgType, ParseNode
from SIM_APDU_Parser.core.registry import register
from SIM_APDU_Parser.core.tlv import parse_ber_tlvs
from SIM_APDU_Parser.core.utils import parse_iccid
from .common_signatures import parse_bf27_profile_installation_result_data, parse_5f37_euicc_sign_pir
from .common_notification import parse_notification_event_with_count, parse_notification_metadata










@register(MsgType.ESIM, "BF37")
class BF37Parser:
    """ProfileInstallationResult - 根据ASN定义重写"""
    def build(self, payload_hex: str, direction: str) -> ParseNode:
        root = ParseNode(name="BF37: ProfileInstallationResult")
        tlvs = parse_ber_tlvs(payload_hex)

        # ProfileInstallationResult ::= [55] SEQUENCE
        for t in tlvs:
            if t.tag == "BF27":  # profileInstallationResultData [39]
                data_node = parse_bf27_profile_installation_result_data(t.value_hex)
                root.children.append(data_node)

            elif t.tag == "5F37":  # euiccSignPIR [APPLICATION 55] OCTET STRING
                root.children.append(parse_5f37_euicc_sign_pir(t.value_hex))
            else:
                # 兜底：显示未知TLV
                root.children.append(ParseNode(name=f"TLV {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))

        # 如果没有解析到任何内容，显示原始TLV
        if not root.children:
            for t in tlvs:
                root.children.append(ParseNode(name=f"TLV {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))

        return root
