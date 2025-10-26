
from SIM_APDU_Parser.core.models import MsgType, ParseNode
from SIM_APDU_Parser.core.registry import register
from SIM_APDU_Parser.core.tlv import parse_ber_tlvs
from SIM_APDU_Parser.core.utils import parse_iccid

@register(MsgType.ESIM, "BF31")
class BF31Parser:
    """EnableProfile - 启用配置文件"""
    def build(self, payload_hex: str, direction: str) -> ParseNode:
        dir_norm = (direction or "").lower()
        if dir_norm in ("lpa=>esim", "tx"):
            return self._parse_request(payload_hex)
        else:
            return self._parse_response(payload_hex)

    # ---------- Request ----------
    def _parse_request(self, payload_hex: str) -> ParseNode:
        root = ParseNode(name="BF31: EnableProfileRequest")
        tlvs = parse_ber_tlvs(payload_hex)

        for t in tlvs:
            if t.tag == "A0":
                # profileIdentifier CHOICE 被 [0] 包裹（AUTOMATIC TAGS）
                pid = ParseNode(name="profileIdentifier")
                for st in parse_ber_tlvs(t.value_hex):
                    if st.tag == "4F":
                        pid.children.append(ParseNode(name="isdpAid", value=st.value_hex))
                    elif st.tag == "5A":
                        pid.children.append(ParseNode(name="iccid", value=parse_iccid(st.value_hex)))
                    else:
                        pid.children.append(ParseNode(name=f"Unknown {st.tag}", value=st.value_hex))
                root.children.append(pid)

            elif t.tag == "4F":  # 也兼容未包裹的直接形式
                root.children.append(ParseNode(name="profileIdentifier.isdpAid", value=t.value_hex))
            elif t.tag == "5A":
                root.children.append(ParseNode(name="profileIdentifier.iccid", value=parse_iccid(t.value_hex)))

            elif t.tag in ("81", "01"):   # refreshFlag: 优先 context [1] = 0x81，也兼容 UNIVERSAL BOOLEAN(0x01)
                is_true = 0 if t.value_hex == "" else (int(t.value_hex, 16) != 0)
                root.children.append(ParseNode(name="refreshFlag", value="True" if is_true else "False",
                                               hint=f"BOOLEAN({t.tag}): {t.value_hex}"))

            elif t.tag in ("82", "02"):   # targetEsimPort: 优先 context [2] = 0x82，兼容 UNIVERSAL INTEGER(0x02)
                try:
                    port_num = int(t.value_hex or "0", 16)
                    root.children.append(ParseNode(name="targetEsimPort", value=str(port_num),
                                                   hint=f"INTEGER({t.tag}): {t.value_hex} (OPTIONAL)"))
                except Exception:
                    root.children.append(ParseNode(name="targetEsimPort", value=t.value_hex,
                                                   hint=f"INTEGER({t.tag}) parse failed"))

            else:
                root.children.append(ParseNode(name=f"TLV {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
        return root

    # ---------- Response ----------
    def _parse_response(self, payload_hex: str) -> ParseNode:
        root = ParseNode(name="BF31: EnableProfileResponse")
        tlvs = parse_ber_tlvs(payload_hex)

        # 映射表
        result_map = {
            0: "ok",
            1: "iccidOrAidNotFound",
            2: "profileNotInDisabledState",
            3: "disallowedByPolicy",
            4: "wrongProfileReenabling",
            5: "catBusy",
            6: "disallowedByEnterpriseRule",
            7: "commandError",
            9: "disallowedForRpm",
            10: "noEsimPortAvailable",
            127: "undefinedError",
        }

        seen_enable_result = False
        for t in tlvs:
            if t.tag in ("80", "02"):  # enableResult: context [0] 或 UNIVERSAL INTEGER
                val = int(t.value_hex or "0", 16)
                name = result_map.get(val, f"Unknown({val})")
                root.children.append(ParseNode(name="enableResult", value=f"{name}({val})",
                                               hint=f"INTEGER({t.tag}): {t.value_hex}"))
                seen_enable_result = True
            elif t.tag in ("82", "02"):  # targetEsimPort（可选），同样兼容两种
                # 只有已经看到 enableResult 后，才把第二个 INTEGER 当作端口
                try:
                    val = int(t.value_hex or "0", 16)
                except Exception:
                    val = t.value_hex
                if seen_enable_result:
                    root.children.append(ParseNode(name="targetEsimPort", value=str(val),
                                                   hint=f"INTEGER({t.tag}): {t.value_hex} (OPTIONAL)"))
                else:
                    # 保护：如果实现把顺序反了，也给出原始TLV，避免误判
                    root.children.append(ParseNode(name=f"TLV {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
            else:
                root.children.append(ParseNode(name=f"TLV {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
        return root
