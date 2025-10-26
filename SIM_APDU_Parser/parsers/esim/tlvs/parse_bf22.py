from SIM_APDU_Parser.core.models import MsgType, ParseNode
from SIM_APDU_Parser.core.registry import register
from SIM_APDU_Parser.core.tlv import parse_ber_tlvs
from SIM_APDU_Parser.core.utils import parse_bitstring

@register(MsgType.ESIM, "BF22")
class BF22Parser:
    """GetEuiccInfo2"""
    def build(self, payload_hex: str, direction: str) -> ParseNode:
        root = ParseNode(name="BF22: GetEuiccInfo2")
        tlvs = parse_ber_tlvs(payload_hex)
        for t in tlvs:
            if t.tag == "81":
                root.children.append(ParseNode(name="baseProfilePackageVersion", value=t.value_hex))
            elif t.tag == "82":
                root.children.append(ParseNode(name="lowestSvn", value=t.value_hex))
            elif t.tag == "83":
                root.children.append(ParseNode(name="euiccFirmwareVersion", value=t.value_hex))
            elif t.tag == "84":
                grp = ParseNode(name="extCardResource")
                for st in parse_ber_tlvs(t.value_hex):
                    if st.tag == "81":
                        grp.children.append(ParseNode(name="Number of installed application", value=st.value_hex))
                    elif st.tag == "82":
                        grp.children.append(ParseNode(name="Available ROM (bytes)", value=str(int(st.value_hex, 16))))
                    elif st.tag == "83":
                        grp.children.append(ParseNode(name="Available RAM (bytes)", value=str(int(st.value_hex, 16))))
                    else:
                        grp.children.append(ParseNode(name=f"Unknown {st.tag}", value=st.value_hex))
                root.children.append(grp)
            elif t.tag == "85":
                names = ["contactlessSupport","usimSupport","isimSupport","csimSupport",
                         "akaMilenage","akaCave","akaTuak128","akaTuak256",
                         "usimTestAlgorithm","rfu2","gbaAuthenUsim","gbaAuthenISim",
                         "mbmsAuthenUsim","eapClient","javacard","multos",
                         "multipleUsimSupport","multipleIsimSupport","multipleCsimSupport",
                         "berTlvFileSupport","dfLinkSupport","catTp","getIdentity",
                         "profile-a-x25519","profile-b-p256","suciCalculatorApi",
                         "dns-resolution","scp11ac","scp11c-authorization-mechanism",
                         "s16mode","eaka","iotminimal"]
                grp = ParseNode(name="UICCCapability")
                for nm, val in parse_bitstring(t.value_hex, names):
                    grp.children.append(ParseNode(name=nm, value=val))
                root.children.append(grp)
            elif t.tag == "86":
                root.children.append(ParseNode(name="ts102241Version", value=t.value_hex))
            elif t.tag == "87":
                root.children.append(ParseNode(name="globalplatformVersion", value=t.value_hex))
            elif t.tag == "88":
                names = ["additionalProfile","loadCrlSupport","rpmSupport","testProfileSupport",
                         "deviceInfoExtensibilitySupport","serviceSpecificDataSupport","hriServerAddressSupport",
                         "serviceProviderMessageSupport","lpaProxySupport","enterpriseProfilesSupport",
                         "serviceDescriptionSupport","deviceChangeSupport","encryptedDeviceChangeDataSupport",
                         "estimatedProfileSizeIndicationSupport","profileSizeInProfilesInfoSupport",
                         "crlStaplingV3Support","certChainV3VerificationSupport","signedSmdsResponseV3Support",
                         "euiccRspCapInInfo1","osUpdateSupport","cancelForEmptySpnPnSupport",
                         "updateNotifConfigInfoSupport","updateMetadataV3Support"]
                grp = ParseNode(name="euiccRspCapability")
                for nm, val in parse_bitstring(t.value_hex, names):
                    grp.children.append(ParseNode(name=nm, value=val))
                root.children.append(grp)
            elif t.tag == "A9":
                root.children.append(ParseNode(name="euiccCiPKIdListForVerification", value=t.value_hex))
            elif t.tag == "AA":
                root.children.append(ParseNode(name="euiccCiPKIdListForSigning", value=t.value_hex))

            # --------- 新增：AUTOMATIC TAGS 优先匹配（同时保留原兜底） ---------
            elif t.tag == "80":  # ppVersion (AUTOMATIC TAGS 常见为 [0] -> 0x80)
                root.children.append(ParseNode(name="ppVersion", value=t.value_hex))
            elif t.tag == "94":  # sasAcreditationNumber (常见为 [20] -> 0x94)
                try:
                    root.children.append(ParseNode(name="sasAcreditationNumber", value=bytes.fromhex(t.value_hex).decode('utf-8')))
                except Exception:
                    root.children.append(ParseNode(name="sasAcreditationNumber", value=t.value_hex))

            # --------- 新增：其余缺失字段 ---------
            elif t.tag == "8B":  # euiccCategory [11] INTEGER {other(0), basicEuicc(1), mediumEuicc(2), contactlessEuicc(3)}
                try:
                    cat_val = int(t.value_hex, 16)
                except Exception:
                    cat_val = t.value_hex
                root.children.append(ParseNode(name="euiccCategory", value=str(cat_val)))
            elif t.tag == "99":
                root.children.append(ParseNode(name="forbiddenProfilePolicyRules", value=t.value_hex))
            elif t.tag == "8D":  # treProperties [13] BIT STRING
                tre_names = ["isDiscrete", "isIntegrated", "usesRemoteMemory"]
                grp = ParseNode(name="treProperties")
                for nm, val in parse_bitstring(t.value_hex, tre_names):
                    grp.children.append(ParseNode(name=nm, value=val))
                root.children.append(grp)
            elif t.tag == "8E":  # treProductReference [14] UTF8String
                try:
                    root.children.append(ParseNode(name="treProductReference", value=bytes.fromhex(t.value_hex).decode('utf-8')))
                except Exception:
                    root.children.append(ParseNode(name="treProductReference", value=t.value_hex))
            elif t.tag == "AF":  # additionalProfilePackageVersions [15] SEQUENCE OF VersionType
                grp = ParseNode(name="additionalProfilePackageVersions")
                # 轻量把内部 VersionType(通常为通用 04)逐项列出
                for vt in parse_ber_tlvs(t.value_hex):
                    if vt.tag == "04":  # OCTET STRING (SIZE(3))
                        grp.children.append(ParseNode(name="VersionType", value=vt.value_hex))
                    else:
                        grp.children.append(ParseNode(name=f"Unknown {vt.tag}", value=vt.value_hex))
                root.children.append(grp)
            elif t.tag == "90":  # lpaMode [16] INTEGER {lpad(0), lpae(1)}
                try:
                    mode = int(t.value_hex, 16)
                except Exception:
                    mode = t.value_hex
                root.children.append(ParseNode(name="lpaMode", value=str(mode)))
            elif t.tag == "B1":  # euiccCiPKIdListForSigningV3 [17] SEQUENCE OF SubjectKeyIdentifier
                root.children.append(ParseNode(name="euiccCiPKIdListForSigningV3", value=t.value_hex))
            elif t.tag == "92":  # additionalEuiccInfo [18] OCTET STRING
                root.children.append(ParseNode(name="additionalEuiccInfo", value=t.value_hex))
            elif t.tag == "93":  # highestSvn [19] VersionType
                root.children.append(ParseNode(name="highestSvn", value=t.value_hex))

            # --------- 兼容兜底（保留你的原逻辑） ---------
            elif t.tag == "0C":  # UNIVERSAL UTF8String（历史/非规范编码兜底）
                try:
                    root.children.append(ParseNode(name="sasAcreditationNumber", value=bytes.fromhex(t.value_hex).decode('utf-8')))
                except Exception:
                    root.children.append(ParseNode(name="sasAcreditationNumber", value=t.value_hex))
            elif t.tag == "AC":
                grp = ParseNode(name="certificationDataObject")
                for st in parse_ber_tlvs(t.value_hex):
                    if st.tag == "80":
                        try:
                            grp.children.append(ParseNode(name="platformLabel", value=bytes.fromhex(st.value_hex).decode('utf-8')))
                        except Exception:
                            grp.children.append(ParseNode(name="platformLabel", value=st.value_hex))
                    elif st.tag == "81":
                        try:
                            grp.children.append(ParseNode(name="discoveryBaseURL", value=bytes.fromhex(st.value_hex).decode('utf-8')))
                        except Exception:
                            grp.children.append(ParseNode(name="discoveryBaseURL", value=st.value_hex))
                    else:
                        grp.children.append(ParseNode(name=f"Unknown {st.tag}", value=st.value_hex))
                root.children.append(grp)
            elif t.tag == "04":  # UNIVERSAL OCTET STRING（历史/非规范编码兜底）
                root.children.append(ParseNode(name="ppVersion", value=t.value_hex))
            else:
                root.children.append(ParseNode(name=f"TLV {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
        return root

@register(MsgType.ESIM, "BF20")
class BF20Parser(BF22Parser):
    """GetEuiccInfo1 - 复用BF22的解析逻辑"""
    def build(self, payload_hex: str, direction: str) -> ParseNode:
        # 调用父类的build方法，但修改根节点名称为BF20
        root = super().build(payload_hex, direction)
        root.name = "BF20: GetEuiccInfo1"
        return root
