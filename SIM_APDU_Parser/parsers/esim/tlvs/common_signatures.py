"""
eSIM TLV解析中的通用签名和数据结构解析模块
"""

from SIM_APDU_Parser.core.models import ParseNode
from SIM_APDU_Parser.core.tlv import parse_ber_tlvs


def parse_bf27_profile_installation_result_data(hexv: str) -> ParseNode:
    """
    解析BF27: profileInstallationResultData [39]
    
    Args:
        hexv: BF27 TLV的value部分（十六进制字符串）
    
    Returns:
        ParseNode: 解析后的profileInstallationResultData节点
    """
    data_node = ParseNode(name="profileInstallationResultData")
    inner_tlvs = parse_ber_tlvs(hexv)

    for st in inner_tlvs:
        if st.tag == "80":  # transactionId [0] TransactionId
            data_node.children.append(ParseNode(name="transactionId", value=st.value_hex))
        elif st.tag == "BF2F":  # notificationMetadata [47] NotificationMetadata
            from .common_notification import parse_notification_metadata
            meta = parse_notification_metadata(st.value_hex)
            data_node.children.append(meta)
        elif st.tag == "06":  # smdpOid OBJECT IDENTIFIER
            data_node.children.append(ParseNode(name="smdpOid", value=st.value_hex))
        elif st.tag == "A2":  # finalResult [2] CHOICE
            final_result = _parse_final_result_choice(st.value_hex)
            data_node.children.append(final_result)
        else:
            data_node.children.append(ParseNode(
                name=f"Unknown {st.tag}",
                value=f"len={st.length}",
                hint=st.value_hex[:120]
            ))

    return data_node


def _parse_final_result_choice(hexv: str) -> ParseNode:
    """
    解析finalResult CHOICE结构
    
    Args:
        hexv: A2 TLV的value部分（十六进制字符串）
    
    Returns:
        ParseNode: 解析后的finalResult节点
    """
    final_result = ParseNode(name="finalResult")
    choice_tlvs = parse_ber_tlvs(hexv)

    for ct in choice_tlvs:
        if ct.tag == "A0":  # successResult
            success = _parse_success_result(ct.value_hex)
            final_result.children.append(success)
        elif ct.tag == "A1":  # errorResult
            error = _parse_error_result(ct.value_hex)
            final_result.children.append(error)
        else:
            final_result.children.append(ParseNode(
                name=f"Unknown choice {ct.tag}",
                value=f"len={ct.length}",
                hint=ct.value_hex[:120]
            ))

    return final_result


def _parse_success_result(hexv: str) -> ParseNode:
    """
    解析SuccessResult结构
    
    Args:
        hexv: A0 TLV的value部分（十六进制字符串）
    
    Returns:
        ParseNode: 解析后的SuccessResult节点
    """
    result = ParseNode(name="SuccessResult")
    tlvs = parse_ber_tlvs(hexv)

    for t in tlvs:
        if t.tag == "4F":  # aid [APPLICATION 15] OCTET STRING
            result.children.append(ParseNode(name="aid", value=t.value_hex))
        elif t.tag == "04":  # ppiResponse OCTET STRING
            # 解析EUICCResponse（支持 A0..AF 容器 + 多个 SEQUENCE）
            ppi_node = _parse_euicc_response(t.value_hex)
            result.children.append(ppi_node)
        else:
            result.children.append(ParseNode(name=f"Unknown {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))

    return result


def _parse_error_result(hexv: str) -> ParseNode:
    """
    解析ErrorResult结构
    
    Args:
        hexv: A1 TLV的value部分（十六进制字符串）
    
    Returns:
        ParseNode: 解析后的ErrorResult节点
    """
    result = ParseNode(name="ErrorResult")
    tlvs = parse_ber_tlvs(hexv)

    bpp_command_map = {
        0: "initialiseSecureChannel", 1: "configureISDP", 2: "storeMetadata",
        3: "storeMetadata2", 4: "replaceSessionKeys", 5: "loadProfileElements"
    }
    error_reason_map = {
        1: "incorrectInputValues", 2: "invalidSignature", 3: "invalidTransactionId",
        4: "unsupportedCrtValues", 5: "unsupportedRemoteOperationType", 6: "unsupportedProfileClass",
        7: "bspStructureError", 8: "bspSecurityError", 9: "installFailedDueToIccidAlreadyExistsOnEuicc",
        10: "installFailedDueToInsufficientMemoryForProfile", 11: "installFailedDueToInterruption",
        12: "installFailedDueToPEProcessingError", 13: "installFailedDueToDataMismatch",
        14: "testProfileInstallFailedDueToInvalidNaaKey", 15: "pprNotAllowed",
        17: "enterpriseProfilesNotSupported", 18: "enterpriseRulesNotAllowed",
        19: "enterpriseProfileNotAllowed", 20: "enterpriseOidMismatch",
        21: "enterpriseRulesError", 22: "enterpriseProfilesOnly", 23: "lprNotSupported",
        26: "unknownTlvInMetadata", 127: "installFailedDueToUnknownError"
    }

    saw_cmd = False
    for t in tlvs:
        if t.tag == "02":  # INTEGER：先 bppCommandId，后 errorReason
            try:
                val = int(t.value_hex, 16)
                if not saw_cmd:
                    saw_cmd = True
                    cmd_name = bpp_command_map.get(val, f"Unknown({val})")
                    result.children.append(ParseNode(name="bppCommandId", value=f"{cmd_name}({val})"))
                else:
                    reason_name = error_reason_map.get(val, f"Unknown({val})")
                    result.children.append(ParseNode(name="errorReason", value=f"{reason_name}({val})"))
            except ValueError:
                result.children.append(ParseNode(name="INTEGER", value=t.value_hex))

        elif t.tag == "04":  # ppiResponse OCTET STRING OPTIONAL
            ppi_node = _parse_euicc_response(t.value_hex)
            result.children.append(ppi_node)

        else:
            result.children.append(ParseNode(name=f"Unknown {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))

    return result


def _parse_euicc_response(hexv: str) -> ParseNode:
    """
    解析EUICCResponse结构
    
    Args:
        hexv: EUICCResponse的十六进制字符串
    
    Returns:
        ParseNode: 解析后的peStatus节点
    """
    node = ParseNode(name="peStatus")
    s = "".join(hexv.split())

    status_map = {
        0: "ok", 1: "pe-not-supported", 2: "memory-failure", 3: "bad-values",
        4: "not-enough-memory", 5: "invalid-request-format", 6: "invalid-parameter",
        7: "runtime-not-supported", 8: "lib-not-supported", 9: "template-not-supported",
        10: "feature-not-supported", 11: "pin-code-missing", 31: "unsupported-profile-version"
    }

    def _emit_status(val_hex: str):
        try:
            v = int(val_hex, 16)
            node.children.append(ParseNode(name="status", value=f"{status_map.get(v, 'Unknown Status')}({v})"))
        except ValueError:
            node.children.append(ParseNode(name="status", value=f"parse_error({val_hex})"))

    def _emit_ident(val_hex: str):
        try:
            v = int(val_hex, 16)
            node.children.append(ParseNode(name="identification number", value=str(v)))
        except ValueError:
            node.children.append(ParseNode(name="identification number", value=val_hex))

    def _walk_ppi_tlvs(tlvs_list):
        """递归下钻任何层级的 30/A0..AF，抽取 80/81；其它保留为 Unknown。"""
        for x in tlvs_list:
            tag = x.tag
            if tag == "80":
                _emit_status(x.value_hex)
            elif tag == "81":
                _emit_ident(x.value_hex)
            elif tag == "30":
                _walk_ppi_tlvs(parse_ber_tlvs(x.value_hex))
            elif tag and tag[0] in "Aa":  # A0..AF：ctx-specific constructed 容器
                _walk_ppi_tlvs(parse_ber_tlvs(x.value_hex))
            else:
                node.children.append(ParseNode(name=f"Unknown {tag}", value=x.value_hex[:120]))

    # ---------- 首选：BER 解析 ----------
    try:
        tlvs = parse_ber_tlvs(s)
        if tlvs:
            _walk_ppi_tlvs(tlvs)
            # 如果确实解出了 status/ident，就返回
            if any(c.name in ("status", "identification number") for c in node.children):
                return node
    except Exception:
        # 继续走回退
        pass

    # ---------- 回退：旧的逐字节解析（兼容少见厂商格式） ----------
    length = len(s)
    index = 0
    if length > 8:
        index = 8  # 兼容某些实现的头部
    while index < length:
        if index + 2 > length:
            break
        tag = s[index:index+2]; index += 2
        if index + 2 > length:
            break
        length_byte = int(s[index:index+2], 16); index += 2
        if length_byte == 0:
            node.children.append(ParseNode(name="profileInstallationAborted", value="true"))
            continue
        if index + length_byte * 2 > length:
            break
        value = s[index:index + (length_byte * 2)]
        index += length_byte * 2

        if tag == "30":  # SEQUENCE
            inner_index = 0
            inner_length = length_byte * 2
            while inner_index < inner_length:
                if inner_index + 2 > inner_length:
                    break
                inner_tag = value[inner_index:inner_index+2]; inner_index += 2
                if inner_index + 2 > inner_length:
                    break
                inner_len = int(value[inner_index:inner_index+2], 16); inner_index += 2
                if inner_index + inner_len * 2 > inner_length:
                    break
                inner_val = value[inner_index:inner_index + (inner_len * 2)]
                inner_index += inner_len * 2

                if inner_tag == "80":
                    _emit_status(inner_val)
                elif inner_tag == "81":
                    _emit_ident(inner_val)
                else:
                    node.children.append(ParseNode(name=f"Unknown {inner_tag}", value=inner_val))
        else:
            node.children.append(ParseNode(name=f"Unknown {tag}", value=value))

    return node


def parse_5f37_signature(hexv: str, signature_type: str = "euiccSignature") -> ParseNode:
    """
    解析5F37签名数据
    
    Args:
        hexv: 5F37 TLV的value部分（十六进制字符串）
        signature_type: 签名类型名称，用于生成节点名称
    
    Returns:
        ParseNode: 解析后的签名节点
    """
    return ParseNode(name=signature_type, value=hexv, hint="eUICC signature")


def parse_5f37_euicc_notification_signature(hexv: str) -> ParseNode:
    """
    解析5F37: euiccNotificationSignature
    
    Args:
        hexv: 5F37 TLV的value部分（十六进制字符串）
    
    Returns:
        ParseNode: 解析后的euiccNotificationSignature节点
    """
    return parse_5f37_signature(hexv, "euiccNotificationSignature")


def parse_5f37_euicc_sign_pir(hexv: str) -> ParseNode:
    """
    解析5F37: euiccSignPIR
    
    Args:
        hexv: 5F37 TLV的value部分（十六进制字符串）
    
    Returns:
        ParseNode: 解析后的euiccSignPIR节点
    """
    return parse_5f37_signature(hexv, "euiccSignPIR")


def parse_5f37_euicc_sign_rpr(hexv: str) -> ParseNode:
    """
    解析5F37: euiccSignRPR
    
    Args:
        hexv: 5F37 TLV的value部分（十六进制字符串）
    
    Returns:
        ParseNode: 解析后的euiccSignRPR节点
    """
    return parse_5f37_signature(hexv, "euiccSignRPR")


def parse_5f37_server_signature1(hexv: str) -> ParseNode:
    """
    解析5F37: serverSignature1
    
    Args:
        hexv: 5F37 TLV的value部分（十六进制字符串）
    
    Returns:
        ParseNode: 解析后的serverSignature1节点
    """
    return parse_5f37_signature(hexv, "serverSignature1")


def parse_other_signed_notification(hexv: str) -> ParseNode:
    """
    解析OtherSignedNotification结构
    
    根据ASN.1定义：
    OtherSignedNotification ::= SEQUENCE { 
        tbsOtherNotification NotificationMetadata, 
        euiccNotificationSignature EuiccSign, 
        euiccCertificate Certificate, -- eUICC Certificate (CERT.EUICC.SIG) 
        nextCertInChain Certificate, -- The certificate certifying the eUICC Certificate 
        otherCertsInChain [1] CertificateChain OPTIONAL -- #SupportedFromV3.0.0# Other Certificates in the eUICC certificate chain, if any 
    }
    
    Args:
        hexv: OtherSignedNotification的十六进制字符串
    
    Returns:
        ParseNode: 解析后的otherSignedNotification节点
    """
    from .common_notification import parse_notification_metadata
    
    node = ParseNode(name="otherSignedNotification")
    tlvs = parse_ber_tlvs(hexv)
    
    for t in tlvs:
        tag = t.tag.upper()
        if tag == "BF2F":  # tbsOtherNotification NotificationMetadata
            metadata = parse_notification_metadata(t.value_hex)
            metadata.name = "tbsOtherNotification"
            node.children.append(metadata)
        elif tag == "5F37":  # euiccNotificationSignature EuiccSign
            signature = parse_5f37_euicc_notification_signature(t.value_hex)
            signature.name = "euiccNotificationSignature"
            node.children.append(signature)
        elif tag == "30":  # euiccCertificate Certificate
            cert_node = ParseNode(name="euiccCertificate", value=f"len={t.length}")
            cert_node.hint = t.value_hex[:120]
            node.children.append(cert_node)
        elif tag == "A1":  # otherCertsInChain [1] CertificateChain OPTIONAL
            chain_node = ParseNode(name="otherCertsInChain", value=f"len={t.length}")
            chain_node.hint = t.value_hex[:120]
            node.children.append(chain_node)
        else:
            # 可能是nextCertInChain Certificate（没有特定tag，按顺序识别）
            # 或者未知字段
            if len(node.children) >= 2:  # 已经有tbsOtherNotification和euiccNotificationSignature
                # 这可能是nextCertInChain
                cert_node = ParseNode(name="nextCertInChain", value=f"len={t.length}")
                cert_node.hint = t.value_hex[:120]
                node.children.append(cert_node)
            else:
                node.children.append(ParseNode(name=f"Unknown {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
    
    return node
