from SIM_APDU_Parser.core.models import MsgType, ParseNode
from SIM_APDU_Parser.core.registry import register
from SIM_APDU_Parser.core.tlv import parse_ber_tlvs
from SIM_APDU_Parser.core.utils import parse_bitstring
from .common_signatures import parse_5f37_server_signature1

def _decode_utf8(hexv: str) -> str:
    try:
        return bytes.fromhex(hexv).decode("utf-8")
    except Exception:
        return hexv

def _decode_bool(hexv: str) -> str:
    # DER BOOLEAN: '00' = FALSE, any non-zero = TRUE
    try:
        return "True" if int(hexv or "00", 16) != 0 else "False"
    except Exception:
        return hexv

def _parse_session_context(hexv: str) -> ParseNode:
    grp = ParseNode(name="SessionContext")
    for t in parse_ber_tlvs(hexv):
        if t.tag == "80":       # serverSvn [0] VersionType
            grp.children.append(ParseNode(name="serverSvn", value=t.value_hex))
        elif t.tag == "81":     # crlStaplingV3Used [1] BOOLEAN
            grp.children.append(ParseNode(name="crlStaplingV3Used", value=_decode_bool(t.value_hex)))
        elif t.tag == "82":     # euiccCiPKIdToBeUsedV3 [2] SubjectKeyIdentifier
            grp.children.append(ParseNode(name="euiccCiPKIdToBeUsedV3", value=t.value_hex))
        elif t.tag == "A3":     # supportedPushServices [3] SEQUENCE OF OBJECT IDENTIFIER
            oids = ParseNode(name="supportedPushServices")
            for st in parse_ber_tlvs(t.value_hex):
                if st.tag == "06":  # OBJECT IDENTIFIER (raw)
                    oids.children.append(ParseNode(name="OID", value=st.value_hex))
                else:
                    oids.children.append(ParseNode(name=f"Unknown {st.tag}", value=st.value_hex))
            grp.children.append(oids)
        else:
            grp.children.append(ParseNode(name=f"Unknown {t.tag}", value=t.value_hex))
    return grp

def _parse_server_signed1(hexv: str) -> ParseNode:
    grp = ParseNode(name="serverSigned1")
    for t in parse_ber_tlvs(hexv):
        if t.tag == "80":       # transactionId [0] TransactionId
            grp.children.append(ParseNode(name="transactionId", value=t.value_hex))
        elif t.tag == "81":     # euiccChallenge [1] Octet16
            grp.children.append(ParseNode(name="euiccChallenge", value=t.value_hex))
        elif t.tag == "83":     # serverAddress [3] UTF8String
            grp.children.append(ParseNode(name="serverAddress", value=_decode_utf8(t.value_hex)))
        elif t.tag == "84":     # serverChallenge [4] Octet16
            grp.children.append(ParseNode(name="serverChallenge", value=t.value_hex))
        elif t.tag == "A5":     # sessionContext [5] SessionContext
            grp.children.append(_parse_session_context(t.value_hex))
        elif t.tag == "86":     # serverRspCapability [6] BIT STRING
            names = ["crlStaplingV3Support", "eventListSigningV3Support",
                     "pushServiceV3Support", "cancelForEmptySpnPnSupport"]
            cap = ParseNode(name="serverRspCapability")
            for nm, val in parse_bitstring(t.value_hex, names):
                cap.children.append(ParseNode(name=nm, value=val))
            grp.children.append(cap)
        else:
            grp.children.append(ParseNode(name=f"Unknown {t.tag}", value=t.value_hex))
    return grp

def _parse_device_info(hexv: str) -> ParseNode:
    """
    解析DeviceInfo结构
    
    DeviceInfo ::= SEQUENCE {
        tac Octet4,
        deviceCapabilities DeviceCapabilities,
        imei Octet8 OPTIONAL,
        preferredLanguages SEQUENCE OF UTF8String OPTIONAL
    }
    """
    grp = ParseNode(name="DeviceInfo")
    for t in parse_ber_tlvs(hexv):
        if t.tag == "80":  # tac [0] Octet4
            grp.children.append(ParseNode(name="tac", value=t.value_hex))
        elif t.tag == "A1":  # deviceCapabilities [1] DeviceCapabilities
            grp.children.append(ParseNode(name="deviceCapabilities", value=t.value_hex, hint="Device capabilities"))
        elif t.tag == "82":  # imei [2] Octet8 OPTIONAL
            # IMEI需要BCD换位处理
            from SIM_APDU_Parser.parsers.CAT.common import parse_imei_text
            imei_decoded = parse_imei_text(t.value_hex)
            grp.children.append(ParseNode(name="imei", value=imei_decoded, hint=f"Raw: {t.value_hex}"))
        elif t.tag == "A3":  # preferredLanguages [3] SEQUENCE OF UTF8String OPTIONAL
            languages = ParseNode(name="preferredLanguages")
            for lang_t in parse_ber_tlvs(t.value_hex):
                if lang_t.tag == "0C":  # UTF8String
                    languages.children.append(ParseNode(name="language", value=_decode_utf8(lang_t.value_hex)))
                else:
                    languages.children.append(ParseNode(name=f"Unknown {lang_t.tag}", value=lang_t.value_hex))
            grp.children.append(languages)
        else:
            grp.children.append(ParseNode(name=f"Unknown {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
    return grp

def _parse_ctx_params_common_auth(hexv: str) -> ParseNode:
    """
    解析CtxParamsForCommonAuthentication结构
    
    用于通用认证的上下文参数
    """
    grp = ParseNode(name="CtxParamsForCommonAuthentication")
    for t in parse_ber_tlvs(hexv):
        if t.tag == "80":  # matchingId [0] UTF8String OPTIONAL
            grp.children.append(ParseNode(name="matchingId", value=_decode_utf8(t.value_hex)))
        elif t.tag == "A1":  # deviceInfo [1] DeviceInfo
            grp.children.append(_parse_device_info(t.value_hex))
        elif t.tag == "82":  # operationType [2] BIT STRING (DEFAULT {profileDownload})
            names = ["profileDownload", "rpm"]
            op = ParseNode(name="operationType")
            for nm, val in parse_bitstring(t.value_hex, names):
                op.children.append(ParseNode(name=nm, value=val))
            grp.children.append(op)
        elif t.tag == "5A":  # iccid (APPLICATION 26) OPTIONAL
            grp.children.append(ParseNode(name="iccid", value=t.value_hex))
        elif t.tag == "83":  # matchingIdSource [3] CHOICE OPTIONAL (wrapped)
            # 尝试解析内部 CHOICE（none[0] NULL / activationCode[1] NULL / smdsOid[2] OID）
            inner = parse_ber_tlvs(t.value_hex)
            if inner:
                c = inner[0]
                if c.tag == "80":
                    grp.children.append(ParseNode(name="matchingIdSource", value="none"))
                elif c.tag == "81":
                    grp.children.append(ParseNode(name="matchingIdSource", value="activationCode"))
                elif c.tag == "06" or c.tag == "82":
                    # 有的实现可能将 OID 直接作为 UNIVERSAL 06 放入
                    grp.children.append(ParseNode(name="matchingIdSource", value=f"smdsOid:{c.value_hex}"))
                else:
                    grp.children.append(ParseNode(name="matchingIdSource", value=t.value_hex))
            else:
                grp.children.append(ParseNode(name="matchingIdSource", value=t.value_hex))
        elif t.tag == "A4":  # vendorSpecificExtension [4] OPTIONAL
            grp.children.append(ParseNode(name="vendorSpecificExtension", value=t.value_hex))
        else:
            grp.children.append(ParseNode(name=f"Unknown {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
    return grp

def _parse_ctx_params_device_change(hexv: str) -> ParseNode:
    """
    解析CtxParamsForDeviceChange结构
    
    用于设备变更的上下文参数
    """
    grp = ParseNode(name="CtxParamsForDeviceChange")
    iccid_seen = False
    for t in parse_ber_tlvs(hexv):
        if t.tag == "5A" and not iccid_seen:  # iccid Iccid
            grp.children.append(ParseNode(name="iccid", value=t.value_hex))
            iccid_seen = True
        elif t.tag == "A1":  # deviceInfo [1]
            grp.children.append(ParseNode(name="deviceInfo", value=t.value_hex))
        elif t.tag == "5A" and iccid_seen:  # targetEidValue [APPLICATION 26] Octet16 OPTIONAL（部分实现复用 5A）
            grp.children.append(ParseNode(name="targetEidValue", value=t.value_hex))
        elif t.tag == "82":  # targetTacValue [2] Octet4 OPTIONAL
            grp.children.append(ParseNode(name="targetTacValue", value=t.value_hex))
        elif t.tag == "A3":  # vendorSpecificExtension [3] OPTIONAL
            grp.children.append(ParseNode(name="vendorSpecificExtension", value=t.value_hex))
        else:
            grp.children.append(ParseNode(name=f"Unknown {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
    return grp

def _parse_ctx_params_profile_recovery(hexv: str) -> ParseNode:
    """
    解析CtxParamsForProfileRecovery结构
    
    用于Profile恢复的上下文参数
    """
    grp = ParseNode(name="CtxParamsForProfileRecovery")
    for t in parse_ber_tlvs(hexv):
        if t.tag == "5A":      # iccid Iccid
            grp.children.append(ParseNode(name="iccid", value=t.value_hex))
        elif t.tag == "A1":    # deviceInfo [1]
            grp.children.append(ParseNode(name="deviceInfo", value=t.value_hex))
        elif t.tag == "A2":    # vendorSpecificExtension [2] OPTIONAL
            grp.children.append(ParseNode(name="vendorSpecificExtension", value=t.value_hex))
        else:
            grp.children.append(ParseNode(name=f"Unknown {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
    return grp

def _parse_ctx_params_push_service(hexv: str) -> ParseNode:
    """
    解析CtxParamsForPushServiceRegistration结构
    
    用于推送服务注册的上下文参数
    """
    grp = ParseNode(name="CtxParamsForPushServiceRegistration")
    for t in parse_ber_tlvs(hexv):
        if t.tag == "80":      # selectedPushService [0] OBJECT IDENTIFIER
            grp.children.append(ParseNode(name="selectedPushServiceOID", value=t.value_hex))
        elif t.tag == "81":    # pushToken [1] UTF8String
            grp.children.append(ParseNode(name="pushToken", value=_decode_utf8(t.value_hex)))
        else:
            grp.children.append(ParseNode(name=f"Unknown {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
    return grp

def _parse_ctx_params1(hexv: str) -> ParseNode:
    """
    解析CtxParams1 CHOICE结构
    
    CtxParams1 ::= CHOICE { 
        ctxParamsForCommonAuthentication[0] CtxParamsForCommonAuthentication, 
        ctxParamsForDeviceChange [1] CtxParamsForDeviceChange, 
        ctxParamsForProfileRecovery [2] CtxParamsForProfileRecovery, 
        ctxParamsForPushServiceRegistration [3] CtxParamsForPushServiceRegistration 
    }
    """
    grp = ParseNode(name="CtxParams1")
    inner = parse_ber_tlvs(hexv)
    
    # 处理CHOICE结构：A0/A1/A2/A3 分别对应 [0]/[1]/[2]/[3]
    if len(inner) == 1 and inner[0].tag in ("A0", "A1", "A2", "A3"):
        ch = inner[0]
        if ch.tag == "A0":  # [0] ctxParamsForCommonAuthentication
            grp.children.append(_parse_ctx_params_common_auth(ch.value_hex))
        elif ch.tag == "A1":  # [1] ctxParamsForDeviceChange
            grp.children.append(_parse_ctx_params_device_change(ch.value_hex))
        elif ch.tag == "A2":  # [2] ctxParamsForProfileRecovery
            grp.children.append(_parse_ctx_params_profile_recovery(ch.value_hex))
        elif ch.tag == "A3":  # [3] ctxParamsForPushServiceRegistration
            grp.children.append(_parse_ctx_params_push_service(ch.value_hex))
        return grp
    
    # 如果没有包装标签，直接解析为CommonAuthentication（最常见的情况）
    # 根据ASN.1定义，CtxParamsForCommonAuthentication是SEQUENCE，直接包含字段
    grp.children.append(_parse_ctx_params_common_auth(hexv))
    return grp

def _parse_euicc_signed1(hexv: str) -> ParseNode:
    """
    解析EuiccSigned1结构
    
    EuiccSigned1 ::= SEQUENCE {
        transactionId [0] TransactionId,
        serverAddress [3] UTF8String,
        serverChallenge [4] Octet16,
        euiccInfo2 [34] EUICCInfo2,
        ctxParams1 CtxParams1
    }
    """
    grp = ParseNode(name="EuiccSigned1")
    for t in parse_ber_tlvs(hexv):
        if t.tag == "80":       # transactionId [0] TransactionId
            grp.children.append(ParseNode(name="transactionId", value=t.value_hex))
        elif t.tag == "83":     # serverAddress [3] UTF8String
            grp.children.append(ParseNode(name="serverAddress", value=_decode_utf8(t.value_hex)))
        elif t.tag == "84":     # serverChallenge [4] Octet16
            grp.children.append(ParseNode(name="serverChallenge", value=t.value_hex))
        elif t.tag == "BF22":   # euiccInfo2 [34] EUICCInfo2
            grp.children.append(ParseNode(name="euiccInfo2", value=t.value_hex, hint="EUICCInfo2"))
        elif t.tag == "A0":     # ctxParams1 CtxParams1
            grp.children.append(_parse_ctx_params1(t.value_hex))
        else:
            grp.children.append(ParseNode(name=f"Unknown {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
    return grp

def _parse_authenticate_response_ok(hexv: str) -> ParseNode:
    """
    解析AuthenticateResponseOk结构
    
    AuthenticateResponseOk ::= SEQUENCE {
        euiccSigned1 EuiccSigned1,
        euiccSignature1 [APPLICATION 55] OCTET STRING,
        euiccCertificate Certificate,
        nextCertInChain Certificate,
        otherCertsInChain [0] CertificateChain OPTIONAL
    }
    """
    grp = ParseNode(name="AuthenticateResponseOk")
    for t in parse_ber_tlvs(hexv):
        if t.tag == "30":       # euiccSigned1 EuiccSigned1
            grp.children.append(_parse_euicc_signed1(t.value_hex))
        elif t.tag == "5F37":   # euiccSignature1 [APPLICATION 55] OCTET STRING
            grp.children.append(parse_5f37_server_signature1(t.value_hex))
        elif t.tag == "30":     # euiccCertificate Certificate (X.509 DER)
            # 需要根据上下文判断是euiccCertificate还是nextCertInChain
            if len(grp.children) > 0 and grp.children[-1].name == "euiccSignature1":
                grp.children.append(ParseNode(name="euiccCertificate", value=t.value_hex, hint="X.509 Certificate"))
            else:
                grp.children.append(ParseNode(name="nextCertInChain", value=t.value_hex, hint="X.509 Certificate"))
        elif t.tag == "A0":     # otherCertsInChain [0] CertificateChain OPTIONAL
            chain = ParseNode(name="otherCertsInChain")
            for st in parse_ber_tlvs(t.value_hex):
                chain.children.append(ParseNode(name=f"Certificate {len(chain.children)+1}", value=st.value_hex, hint=st.tag))
            grp.children.append(chain)
        else:
            grp.children.append(ParseNode(name=f"Unknown {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
    return grp

def _parse_authenticate_response_error(hexv: str) -> ParseNode:
    """
    解析AuthenticateResponseError结构
    
    AuthenticateResponseError ::= SEQUENCE {
        transactionId [0] TransactionId,
        authenticateErrorCode AuthenticateErrorCode
    }
    """
    grp = ParseNode(name="AuthenticateResponseError")
    for t in parse_ber_tlvs(hexv):
        if t.tag == "80":       # transactionId [0] TransactionId
            grp.children.append(ParseNode(name="transactionId", value=t.value_hex))
        elif t.tag == "02":     # authenticateErrorCode INTEGER
            error_codes = {
                1: "invalidCertificate", 2: "invalidSignature", 3: "unsupportedCurve",
                4: "noSession", 5: "invalidOid", 6: "euiccChallengeMismatch",
                7: "ciPKUnknown", 8: "transactionIdError", 9: "missingCrl",
                10: "invalidCrlSignature", 11: "revokedCert", 12: "invalidCertOrCrlTime",
                13: "invalidCertOrCrlConfiguration", 14: "invalidIccid", 127: "undefinedError"
            }
            try:
                code = int(t.value_hex, 16)
                error_name = error_codes.get(code, f"Unknown({code})")
                grp.children.append(ParseNode(name="authenticateErrorCode", value=f"{error_name}({code})"))
            except ValueError:
                grp.children.append(ParseNode(name="authenticateErrorCode", value=t.value_hex))
        else:
            grp.children.append(ParseNode(name=f"Unknown {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
    return grp

@register(MsgType.ESIM, "BF38")
class BF38Parser:
    """AuthenticateServerRequest/Response - BF38 is a CHOICE"""
    def build(self, payload_hex: str, direction: str) -> ParseNode:
        # 根据方向判断是Request还是Response
        if direction == "LPA=>ESIM":
            return self._parse_request(payload_hex)
        else:  # ESIM=>LPA
            return self._parse_response(payload_hex)
    
    def _parse_request(self, payload_hex: str) -> ParseNode:
        """解析AuthenticateServerRequest"""
        root = ParseNode(name="BF38: AuthenticateServerRequest")
        for t in parse_ber_tlvs(payload_hex):
            if t.tag == "30":             # serverSigned1  (SEQUENCE)
                root.children.append(_parse_server_signed1(t.value_hex))
            elif t.tag == "5F37":         # serverSignature1 [APPLICATION 55] OCTET STRING
                root.children.append(parse_5f37_server_signature1(t.value_hex))
            elif t.tag == "04":           # euiccCiPKIdToBeUsed SubjectKeyIdentifier OPTIONAL
                root.children.append(ParseNode(name="euiccCiPKIdToBeUsed", value=t.value_hex))
            elif t.tag == "30":           # serverCertificate Certificate (X.509 DER)
                # 注意：这里可能有冲突，因为30也是SEQUENCE，需要根据上下文判断
                # 如果前面已经有30（serverSigned1），那么这个30应该是serverCertificate
                if len(root.children) > 0 and root.children[-1].name == "serverSigned1":
                    root.children.append(ParseNode(name="serverCertificate", value=t.value_hex, hint="X.509 Certificate"))
                else:
                    root.children.append(_parse_server_signed1(t.value_hex))
            elif t.tag == "A0":           # ctxParams1  (AUTOMATIC TAGS -> [0]) CHOICE
                root.children.append(_parse_ctx_params1(t.value_hex))
            elif t.tag == "A1":           # otherCertsInChain [1] CertificateChain OPTIONAL
                chain = ParseNode(name="otherCertsInChain")
                # 通常内部是一系列 X.509 Certificate (UNIVERSAL 30)
                for st in parse_ber_tlvs(t.value_hex):
                    chain.children.append(ParseNode(name=f"Certificate {len(chain.children)+1}", value=st.value_hex, hint=st.tag))
                root.children.append(chain)
            elif t.tag == "A2":           # crlList [2] SEQUENCE OF CertificateList OPTIONAL
                crls = ParseNode(name="crlList")
                for st in parse_ber_tlvs(t.value_hex):
                    crls.children.append(ParseNode(name=f"CRL {len(crls.children)+1}", value=st.value_hex, hint=st.tag))
                root.children.append(crls)
            else:
                root.children.append(ParseNode(name=f"TLV {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
        return root
    
    def _parse_response(self, payload_hex: str) -> ParseNode:
        """解析AuthenticateServerResponse"""
        root = ParseNode(name="BF38: AuthenticateServerResponse")
        for t in parse_ber_tlvs(payload_hex):
            if t.tag == "A0":             # authenticateResponseOk [0]
                root.children.append(_parse_authenticate_response_ok(t.value_hex))
            elif t.tag == "A1":           # authenticateResponseError [1]
                root.children.append(_parse_authenticate_response_error(t.value_hex))
            else:
                root.children.append(ParseNode(name=f"Unknown {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
        return root
