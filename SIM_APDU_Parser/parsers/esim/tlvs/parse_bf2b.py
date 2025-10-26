
from SIM_APDU_Parser.core.models import MsgType, ParseNode
from SIM_APDU_Parser.core.registry import register, resolve
from SIM_APDU_Parser.core.tlv import parse_ber_tlvs
from .common_notification import parse_notification_event, parse_notification_metadata, build_notification_operation_node
from .common_signatures import parse_5f37_euicc_notification_signature, parse_5f37_euicc_sign_rpr, parse_other_signed_notification

@register(MsgType.ESIM, "BF2B")
class BF2BParser:
    """RetrieveNotificationsList (BF2B)"""

    def build(self, payload_hex: str, direction: str) -> ParseNode:
        dir_norm = (direction or "").lower()
        if dir_norm in ("lpa=>esim", "tx"):
            return self._parse_request(payload_hex)
        else:
            return self._parse_response(payload_hex)

    # ---------- Request ----------
    def _parse_request(self, payload_hex: str) -> ParseNode:
        root = ParseNode(name="BF2B: RetrieveNotificationsListRequest")
        tlvs = parse_ber_tlvs(payload_hex)
        
        # 检查是否有context-specific tag包装
        if tlvs and tlvs[0].tag.upper().startswith("A"):
            # 有context-specific tag包装，解析内部内容
            inner_tlvs = parse_ber_tlvs(tlvs[0].value_hex)
            for t in inner_tlvs:
                tag = t.tag.upper()
                if tag == "80":  # seqNumber [0] INTEGER
                    try:
                        val = int(t.value_hex or "0", 16)
                        root.children.append(ParseNode(name="seqNumber", value=str(val)))
                    except Exception:
                        root.children.append(ParseNode(name="seqNumber", value=t.value_hex))
                elif tag == "81":  # profileManagementOperation [1] NotificationEvent
                    events = parse_notification_event(t.value_hex)
                    op = build_notification_operation_node(events)
                    root.children.append(op)
                else:
                    root.children.append(ParseNode(name=f"TLV {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
        else:
            # 直接解析顶层TLV
            for t in tlvs:
                tag = t.tag.upper()
                if tag == "80":  # seqNumber [0] INTEGER
                    try:
                        val = int(t.value_hex or "0", 16)
                        root.children.append(ParseNode(name="seqNumber", value=str(val)))
                    except Exception:
                        root.children.append(ParseNode(name="seqNumber", value=t.value_hex))
                elif tag == "81":  # profileManagementOperation [1] NotificationEvent
                    events = parse_notification_event(t.value_hex)
                    op = build_notification_operation_node(events)
                    root.children.append(op)
                else:
                    root.children.append(ParseNode(name=f"TLV {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
        
        return root

    # ---------- Response ----------
    def _parse_response(self, payload_hex: str) -> ParseNode:
        root = ParseNode(name="BF2B: RetrieveNotificationsListResponse")
        tlvs = parse_ber_tlvs(payload_hex)
        if not tlvs:
            root.hint = "Empty CHOICE"
            return root

        t0 = tlvs[0]
        # Unwrap context-specific constructed (A0/A1/...) if present
        if t0.tag.upper().startswith("A"):
            inner = parse_ber_tlvs(t0.value_hex)
            if inner:
                t0 = inner[0]

        # Direct BF37 (single PendingNotification → profileInstallationResult)
        if t0.tag.upper() == "BF37":
            cls = resolve(MsgType.ESIM, "BF37")
            node = cls().build(t0.value_hex, "esim=>lpa") if cls else ParseNode(name="profileInstallationResult", value=t0.value_hex)
            node.name = "profileInstallationResult"
            root.children.append(node)
            return root

        # notificationList := SEQUENCE OF PendingNotification
        if t0.tag == "30":
            seq_node = ParseNode(name="notificationList")
            for item in parse_ber_tlvs(t0.value_hex):
                tag = item.tag.upper()
                if tag == "BF37":
                    cls = resolve(MsgType.ESIM, "BF37")
                    node = cls().build(item.value_hex, "esim=>lpa") if cls else ParseNode(name="profileInstallationResult", value=item.value_hex)
                    node.name = "profileInstallationResult"
                    seq_node.children.append(node)
                elif tag == "30":  # otherSignedNotification
                    seq_node.children.append(parse_other_signed_notification(item.value_hex))
                elif tag == "A1":  # loadRpmPackageResultSigned [1]
                    seq_node.children.append(self._parse_load_rpm_package_result_signed(item.value_hex))
                elif tag == "BF2F":  # NotificationMetadata (非标准，但实际数据中存在)
                    from .common_notification import parse_notification_metadata
                    metadata = parse_notification_metadata(item.value_hex)
                    metadata.name = "PendingNotification (NotificationMetadata)"
                    seq_node.children.append(metadata)
                elif tag == "5F37":  # 签名数据 (非标准，但实际数据中存在)
                    from .common_signatures import parse_5f37_signature
                    signature = parse_5f37_signature(item.value_hex, "otherSignedNotification")
                    signature.name = "PendingNotification (Signature)"
                    seq_node.children.append(signature)
                else:
                    seq_node.children.append(ParseNode(name=f"PendingNotification ({tag})", value=f"len={item.length}", hint=item.value_hex[:120]))
            root.children.append(seq_node)
            return root

        # notificationsListResultError INTEGER
        if t0.tag in ("81", "02"):
            try:
                code = int(t0.value_hex or "0", 16)
            except Exception:
                code = None
            name = {127: "undefinedError"}.get(code, f"Unknown({code})")
            root.children.append(ParseNode(name="notificationsListResultError", value=name))
            return root

        # Fallback
        root.children.append(ParseNode(name=f"TLV {t0.tag}", value=t0.value_hex[:120]))
        return root


    def _parse_load_rpm_package_result_signed(self, hexv: str) -> ParseNode:
        node = ParseNode(name="loadRpmPackageResultSigned")
        for t in parse_ber_tlvs(hexv):
            tag = t.tag.upper()
            if tag == "30":
                node.children.append(self._parse_load_rpm_package_result_data_signed(t.value_hex))
            elif tag == "5F37":
                node.children.append(parse_5f37_euicc_sign_rpr(t.value_hex))
            else:
                node.children.append(ParseNode(name=f"TLV {t.tag}", value=t.value_hex[:120]))
        return node

    def _parse_load_rpm_package_result_data_signed(self, hexv: str) -> ParseNode:
        grp = ParseNode(name="loadRpmPackageResultDataSigned")
        for t in parse_ber_tlvs(hexv):
            tag = t.tag.upper()
            if tag == "80":
                grp.children.append(ParseNode(name="transactionId", value=t.value_hex))
            elif tag == "BF2F":
                md = parse_notification_metadata(t.value_hex)
                grp.children.append(md)
            elif tag == "06":
                grp.children.append(ParseNode(name="smdpOid", value=t.value_hex))
            elif tag == "A2":
                grp.children.append(self._parse_final_result(t.value_hex))
            else:
                grp.children.append(ParseNode(name=f"TLV {t.tag}", value=t.value_hex[:120]))
        return grp

    def _parse_final_result(self, hexv: str) -> ParseNode:
        node = ParseNode(name="finalResult")
        for c in parse_ber_tlvs(hexv):
            tag = c.tag.upper()
            if tag == "30":
                seq = ParseNode(name="rpmPackageExecutionResult")
                for item in parse_ber_tlvs(c.value_hex):
                    seq.children.append(self._parse_rpm_command_result(item.value_hex if item.tag == "30" else item.value_hex))
                node.children.append(seq)
            elif tag in ("80", "02"):
                try:
                    val = int(c.value_hex or "0", 16)
                    err_map = {2: "invalidSignature", 5: "invalidTransactionId", 127: "undefinedError"}
                    node.children.append(ParseNode(name="loadRpmPackageErrorCodeSigned",
                                                   value=f"{err_map.get(val, 'Unknown')}({val})"))
                except Exception:
                    node.children.append(ParseNode(name="loadRpmPackageErrorCodeSigned", value=c.value_hex))
            else:
                node.children.append(ParseNode(name=f"TLV {c.tag}", value=c.value_hex[:120]))
        return node

    def _parse_rpm_command_result(self, hexv: str) -> ParseNode:
        node = ParseNode(name="RpmCommandResult")
        for t in parse_ber_tlvs(hexv):
            tag = t.tag.upper()
            if tag == "5A":
                node.children.append(ParseNode(name="iccid", value=t.value_hex))
            elif tag == "B1":
                node.children.append(ParseNode(name="enableResult", value=f"len={t.length}"))
            elif tag == "B2":
                node.children.append(ParseNode(name="disableResult", value=f"len={t.length}"))
            elif tag == "B3":
                node.children.append(ParseNode(name="deleteResult", value=f"len={t.length}"))
            elif tag == "AD":
                node.children.append(ParseNode(name="listProfileInfoResult", value=f"len={t.length}"))
            elif tag == "AA":
                node.children.append(ParseNode(name="updateMetadataResult", value=f"len={t.length}"))
            elif tag in ("81", "02"):
                try:
                    val = int(t.value_hex or "0", 16)
                    name = {
                        1: "resultSizeOverflow",
                        2: "unknownOrDamagedCommand",
                        3: "interruption",
                        4: "commandsWithRefreshExceeded",
                        5: "commandAfterContactPcmp",
                        6: "commandPackageTooLarge"
                    }.get(val, f"Unknown({val})")
                    node.children.append(ParseNode(name="rpmProcessingTerminated", value=name))
                except Exception:
                    node.children.append(ParseNode(name="rpmProcessingTerminated", value=t.value_hex))
            else:
                node.children.append(ParseNode(name=f"TLV {t.tag}", value=t.value_hex[:120]))
        return node
