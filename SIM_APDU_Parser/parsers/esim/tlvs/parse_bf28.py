from SIM_APDU_Parser.core.models import MsgType, ParseNode
from SIM_APDU_Parser.core.registry import register
from SIM_APDU_Parser.core.tlv import parse_ber_tlvs
from SIM_APDU_Parser.core.utils import parse_iccid, hex_to_utf8
from .common_notification import parse_notification_event, parse_notification_metadata, build_notification_operation_node



@register(MsgType.ESIM, "BF28")
class BF28Parser:
    """ListNotificationRequest/Response - 通知列表查询"""
    def build(self, payload_hex: str, direction: str) -> ParseNode:
        # 根据方向判断是请求还是响应
        dir_norm = (direction or "").lower()
        if dir_norm in ("lpa=>esim", "tx"):
            return self._parse_request(payload_hex)
        else:
            return self._parse_response(payload_hex)

    def _parse_request(self, payload_hex: str) -> ParseNode:
        """解析ListNotificationRequest"""
        root = ParseNode(name="BF28: ListNotificationRequest")
        tlvs = parse_ber_tlvs(payload_hex)
        
        for t in tlvs:
            if t.tag == "81":  # profileManagementOperation [1] NotificationEvent (AUTOMATIC TAGS [1] -> 81)
                events = parse_notification_event(t.value_hex)
                op_node = build_notification_operation_node(events)
                root.children.append(op_node)
            
            elif t.tag == "A8":  # 兼容其他可能的编码形式
                events = parse_notification_event(t.value_hex)
                op_node = build_notification_operation_node(events)
                root.children.append(op_node)
            
            else:
                root.children.append(ParseNode(name=f"TLV {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
        
        # 如果没有TLV，说明是默认请求（返回所有通知）
        if not root.children:
            root.hint = "Default request (return all notifications)"
        
        return root

    def _parse_response(self, payload_hex: str) -> ParseNode:
        """解析ListNotificationResponse - CHOICE结构"""
        root = ParseNode(name="BF28: ListNotificationResponse")
        tlvs = parse_ber_tlvs(payload_hex)

        # 聚合一个 metadata list，兼容两种结构：
        # 1) A0( [0] notificationMetadataList ) 下多条 BF2F
        # 2) 顶层直接就是多个 BF2F
        metadata_list = None

        for t in tlvs:
            if t.tag == "A0":  # [0] notificationMetadataList
                if metadata_list is None:
                    metadata_list = ParseNode(name="notificationMetadataList")
                inner_tlvs = parse_ber_tlvs(t.value_hex)
                for inner_t in inner_tlvs:
                    if inner_t.tag == "BF2F":  # 单条 NotificationMetadata
                        md = parse_notification_metadata(inner_t.value_hex)
                        md.name = f"NotificationMetadata {len(metadata_list.children)+1}"
                        # 规范校验：Only one bit SHALL be set to 1
                        self._check_single_bit_rule(md)
                        metadata_list.children.append(md)
                    else:
                        # 兼容性兜底：尝试按一条 Metadata 解
                        md = parse_notification_metadata(inner_t.value_hex)
                        md.name = f"NotificationMetadata {len(metadata_list.children)+1}"
                        self._check_single_bit_rule(md)
                        metadata_list.children.append(md)

            elif t.tag == "BF2F":  # 顶层直接出现单条 NotificationMetadata（一些实现可能这样发）
                if metadata_list is None:
                    metadata_list = ParseNode(name="notificationMetadataList")
                md = parse_notification_metadata(t.value_hex)
                md.name = f"NotificationMetadata {len(metadata_list.children)+1}"
                self._check_single_bit_rule(md)
                metadata_list.children.append(md)

            elif t.tag in ("81", "02"):  # [1] listNotificationsResultError（ctx-specific）或 UNIVERSAL INTEGER
                try:
                    error_code = int(t.value_hex, 16)
                    error_map = {127: "undefinedError"}
                    error_name = error_map.get(error_code, f"Unknown({error_code})")
                    root.children.append(ParseNode(
                        name="listNotificationsResultError",
                        value=f"{error_name}({error_code})",
                        hint=f"INTEGER({t.tag}): {t.value_hex}"
                    ))
                    root.hint = f"Error response: {error_name}"
                except ValueError:
                    root.children.append(ParseNode(
                        name="listNotificationsResultError",
                        value=t.value_hex,
                        hint=f"INTEGER({t.tag}) parse failed"
                    ))

            else:
                # 未知顶层TLV，保留现场
                root.children.append(ParseNode(
                    name=f"TLV {t.tag}",
                    value=f"len={t.length}",
                    hint=t.value_hex[:120]
                ))

        if metadata_list is not None:
            root.children.append(metadata_list)

        return root

    # 新增的私有方法：不改已有函数名/变量名
    def _check_single_bit_rule(self, metadata_node: ParseNode) -> None:
        """规范校验：profileManagementOperation 中应当只有一个 Requested"""
        # 找到 profileManagementOperation 节点
        op = None
        for c in metadata_node.children:
            if c.name == "profileManagementOperation":
                op = c
                break
        if not op:
            return
        requested = [x for x in op.children if getattr(x, "value", None) == "Requested"]
        if len(requested) != 1:
            # 不满足规范，打个提示
            op.hint = f"Spec: Only one bit SHALL be set to 1, observed={len(requested)}"
