"""
eSIM TLV解析中的通用通知相关结构解析模块
"""

from SIM_APDU_Parser.core.models import ParseNode
from SIM_APDU_Parser.core.tlv import parse_ber_tlvs
from SIM_APDU_Parser.core.utils import parse_iccid, hex_to_utf8


def parse_notification_event(bitstring_hex: str) -> list[tuple[str, str]]:
    """
    解析NotificationEvent位串，返回事件类型列表
    
    根据ASN.1/X.690 BIT STRING规范：
    - 第一个字节是未使用位数 (0-7)
    - 后续字节是位数据
    - bit 0 = 第一个字节的MSB (0x80)
    - bit 1 = 第一个字节的次MSB (0x40)
    - 以此类推...
    
    Args:
        bitstring_hex: NotificationEvent BIT STRING的十六进制字符串
        
    Returns:
        list[tuple[str, str]]: 事件类型列表，每个元组包含(事件名, 状态)
    """
    if len(bitstring_hex) < 2:
        return []
    
    # 检查是否是带未用位的格式
    # 带未用位格式的特征：第一个字节是未用位数(0-7)，且长度至少4个字符(2字节)
    # 直接位串格式：没有未用位标识
    if len(bitstring_hex) >= 4:
        first_byte = int(bitstring_hex[:2], 16)
        # 更严格的判断：第一个字节必须是0-7，且剩余部分长度必须合理
        # 对于2字节数据，如果第一个字节是0-7，很可能是未用位数
        if first_byte <= 7 and len(bitstring_hex) == 4:
            # 2字节数据，第一个字节是0-7，很可能是未用位格式
            unused_bits = first_byte
            value_hex = bitstring_hex[2:]
        elif first_byte <= 7 and len(bitstring_hex) > 4:
            # 多字节数据，第一个字节是0-7，可能是未用位格式
            # 但需要检查是否合理（剩余字节数应该足够）
            remaining_bytes = (len(bitstring_hex) - 2) // 2
            if remaining_bytes > 0:
                unused_bits = first_byte
                value_hex = bitstring_hex[2:]
            else:
                unused_bits = 0
                value_hex = bitstring_hex
        else:
            # 直接位串格式：没有未用位
            unused_bits = 0
            value_hex = bitstring_hex
    else:
        # 长度不足4个字符，直接按位串处理
        unused_bits = 0
        value_hex = bitstring_hex
    
    if not value_hex:
        return []
    
    # 计算有效位数
    total_bits = len(value_hex) * 4
    effective_bits = total_bits - unused_bits
    
    # 事件类型映射（根据NotificationEvent BIT STRING规范）
    event_types = [
        "notificationInstall",           # bit 0
        "notificationLocalEnable",       # bit 1
        "notificationLocalDisable",      # bit 2
        "notificationLocalDelete",       # bit 3
        "notificationRpmEnable",         # bit 4 (SupportedForRpmV3.0.0)
        "notificationRpmDisable",        # bit 5 (SupportedForRpmV3.0.0)
        "notificationRpmDelete",         # bit 6 (SupportedForRpmV3.0.0)
        "loadRpmPackageResult"          # bit 7 (SupportedForRpmV3.0.0)
    ]
    
    events = []
    
    # 按字节解析位数据
    for i, event_name in enumerate(event_types):
        if i >= effective_bits:
            # 超出有效位数范围
            break
            
        # 计算位所在的字节和字节内位置
        byte_index = i // 8
        bit_in_byte = i % 8
        
        if byte_index < len(value_hex):
            # 获取字节值
            byte_value = int(value_hex[byte_index * 2:(byte_index + 1) * 2], 16)
            # 计算掩码 (bit 0 = 0x80, bit 1 = 0x40, ..., bit 7 = 0x01)
            mask = 0x80 >> bit_in_byte
            # 检查位是否被设置
            if (byte_value & mask) != 0:
                events.append((event_name, "Requested"))
            else:
                events.append((event_name, "Not Requested"))
        else:
            # 超出字节范围
            events.append((event_name, "Not Requested"))
    
    return events


def parse_notification_event_with_count(bitstring_hex: str) -> tuple[list[tuple[str, str]], int]:
    """
    解析NotificationEvent位串，返回事件类型列表和请求数量
    
    根据ASN.1/X.690 BIT STRING规范：
    - 第一个字节是未使用位数 (0-7)
    - 后续字节是位数据
    - bit 0 = 第一个字节的MSB (0x80)
    - bit 1 = 第一个字节的次MSB (0x40)
    - 以此类推...
    
    Args:
        bitstring_hex: NotificationEvent BIT STRING的十六进制字符串
        
    Returns:
        tuple[list[tuple[str, str]], int]: (事件类型列表, 请求数量)
    """
    if len(bitstring_hex) < 2:
        return [], 0
    
    # 检查是否是带未用位的格式
    if len(bitstring_hex) >= 4:
        first_byte = int(bitstring_hex[:2], 16)
        if first_byte <= 7 and len(bitstring_hex) == 4:
            # 2字节数据，第一个字节是0-7，很可能是未用位格式
            unused_bits = first_byte
            value_hex = bitstring_hex[2:]
        elif first_byte <= 7 and len(bitstring_hex) > 4:
            # 多字节数据，第一个字节是0-7，可能是未用位格式
            remaining_bytes = (len(bitstring_hex) - 2) // 2
            if remaining_bytes > 0:
                unused_bits = first_byte
                value_hex = bitstring_hex[2:]
            else:
                unused_bits = 0
                value_hex = bitstring_hex
        else:
            # 直接位串格式：没有未用位
            unused_bits = 0
            value_hex = bitstring_hex
    else:
        # 长度不足4个字符，直接按位串处理
        unused_bits = 0
        value_hex = bitstring_hex
    
    if not value_hex:
        return [], 0
    
    # 计算有效位数
    total_bits = len(value_hex) * 4
    effective_bits = total_bits - unused_bits
    
    # 事件类型映射（根据NotificationEvent BIT STRING规范）
    event_types = [
        "notificationInstall",           # bit 0
        "notificationLocalEnable",       # bit 1
        "notificationLocalDisable",      # bit 2
        "notificationLocalDelete",       # bit 3
        "notificationRpmEnable",         # bit 4 (SupportedForRpmV3.0.0)
        "notificationRpmDisable",        # bit 5 (SupportedForRpmV3.0.0)
        "notificationRpmDelete",         # bit 6 (SupportedForRpmV3.0.0)
        "loadRpmPackageResult"          # bit 7 (SupportedForRpmV3.0.0)
    ]
    
    rows, cnt = [], 0
    
    # 按字节解析位数据
    for i, event_name in enumerate(event_types):
        if i >= effective_bits:
            # 超出有效位数范围
            break
            
        # 计算位所在的字节和字节内位置
        byte_index = i // 8
        bit_in_byte = i % 8
        
        if byte_index < len(value_hex):
            # 获取字节值
            byte_value = int(value_hex[byte_index * 2:(byte_index + 1) * 2], 16)
            # 计算掩码 (bit 0 = 0x80, bit 1 = 0x40, ..., bit 7 = 0x01)
            mask = 0x80 >> bit_in_byte
            # 检查位是否被设置
            if (byte_value & mask) != 0:
                rows.append((event_name, "Requested"))
                cnt += 1
            else:
                rows.append((event_name, "Not Requested"))
        else:
            # 超出字节范围
            rows.append((event_name, "Not Requested"))
    
    return rows, cnt


def parse_notification_metadata(metadata_hex: str) -> ParseNode:
    """
    解析NotificationMetadata结构
    
    Args:
        metadata_hex: NotificationMetadata的十六进制字符串
        
    Returns:
        ParseNode: 解析后的NotificationMetadata节点
    """
    metadata = ParseNode(name="NotificationMetadata")
    tlvs = parse_ber_tlvs(metadata_hex)

    for t in tlvs:
        if t.tag == "80":  # seqNumber [0] INTEGER
            try:
                seq_num = int(t.value_hex, 16)
                metadata.children.append(ParseNode(name="seqNumber", value=str(seq_num)))
            except ValueError:
                metadata.children.append(ParseNode(name="seqNumber", value=t.value_hex))

        elif t.tag == "81":  # profileManagementOperation [1] NotificationEvent (BIT STRING)
            op_node = ParseNode(name="profileManagementOperation")
            rows, cnt = parse_notification_event_with_count(t.value_hex)
            if rows:
                for name, status in rows:
                    op_node.children.append(ParseNode(name=name, value=status))
                if cnt != 1:
                    op_node.hint = f"Spec: Only one bit SHALL be set to 1, observed={cnt}"
            else:
                op_node.children.append(ParseNode(name="parse-error", value=t.value_hex))
            metadata.children.append(op_node)

        elif t.tag == "0C":  # notificationAddress UTF8String
            try:
                address = bytes.fromhex(t.value_hex).decode('utf-8')
                metadata.children.append(ParseNode(name="notificationAddress", value=address))
            except Exception:
                metadata.children.append(ParseNode(name="notificationAddress", value=t.value_hex))

        elif t.tag == "5A":  # iccid Iccid
            iccid = parse_iccid(t.value_hex)
            metadata.children.append(ParseNode(name="iccid", value=iccid))

        else:
            metadata.children.append(ParseNode(name=f"Field {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))

    return metadata


def build_notification_operation_node(events: list[tuple[str, str]], node_name: str = "profileManagementOperation") -> ParseNode:
    """
    构建profileManagementOperation节点
    
    Args:
        events: 事件列表
        node_name: 节点名称
        
    Returns:
        ParseNode: 构建的节点
    """
    op_node = ParseNode(name=node_name)
    if events:
        for name, status in events:
            op_node.children.append(ParseNode(name=name, value=status))
    else:
        op_node.children.append(ParseNode(name="No events", value="All bits set to 0 (no notifications requested)"))
    return op_node
