# parsers/CAT/common.py
from SIM_APDU_Parser.core.models import ParseNode

def _hex2int(h): return int(h, 16) if h else 0

# ========== TLV 解析器注册表 ==========
# 用于统一管理所有 COMPREHENSION-TLV data objects 的解析函数
# 格式: {tag: (parser_function, display_name)}
# tag 可以是单个字符串或元组（支持多个 tag 变体）
TLV_PARSER_REGISTRY = {}

def register_tlv_parser(tags, parser_func, display_name):
    """
    注册 TLV 解析器
    
    Args:
        tags: Tag 字符串或元组（如 '02' 或 ('02', '82')）
        parser_func: 解析函数，接受 value_hex 参数，返回解析后的字符串
        display_name: 显示名称（如 "Device identities"）
    """
    if isinstance(tags, str):
        tags = (tags,)
    
    for tag in tags:
        TLV_PARSER_REGISTRY[tag.upper()] = (parser_func, display_name)

def get_tlv_parser(tag):
    """
    获取 TLV 解析器
    
    Args:
        tag: TLV tag 字符串
        
    Returns:
        (parser_func, display_name) 或 (None, None)
"""
    return TLV_PARSER_REGISTRY.get(tag.upper(), (None, None))

def parse_tlv_structure_recursive(value_hex: str, max_depth: int = 10) -> ParseNode:
    """
    递归解析TLV结构，尝试将value_hex解析为嵌套的TLV结构
    
    Args:
        value_hex: 要解析的十六进制字符串（不包含tag和length）
        max_depth: 最大递归深度，防止无限递归
        
    Returns:
        ParseNode对象，包含解析后的TLV结构树
    """
    if max_depth <= 0 or not value_hex or len(value_hex) < 4:
        # 无法解析为TLV结构，返回原始数据
        return None
    
    root = ParseNode(name="TLV Structure", value=f"Length: {len(value_hex)//2} bytes (0x{value_hex})")
    idx = 0
    n = len(value_hex)
    parsed_count = 0
    
    while idx + 4 <= n:
        # 尝试读取Tag (1字节)
        tag = value_hex[idx:idx+2].upper()
        idx += 2
        
        # 尝试读取Length (1字节)
        if idx + 2 > n:
            break
        try:
            length = int(value_hex[idx:idx+2], 16)
            idx += 2
        except ValueError:
            break
        
        # 读取Value
        if length == 0:
            # 长度为0，跳过
            continue
        
        if idx + length * 2 > n:
            # 数据不完整，停止解析
            break
        
        val_hex = value_hex[idx:idx+length*2]
        idx += length * 2
        
        # 尝试递归解析value部分
        child_node = parse_tlv_structure_recursive(val_hex, max_depth - 1)
        if child_node and len(child_node.children) > 0:
            # 如果value部分包含嵌套TLV，创建父节点
            tlv_node = ParseNode(name=f"TLV {tag}", value=f"Length: {length} bytes")
            tlv_node.children.append(child_node)
            root.children.append(tlv_node)
        else:
            # 无法递归解析，作为叶子节点
            # 尝试使用注册的解析器
            parser_func, display_name = get_tlv_parser(tag)
            if parser_func:
                try:
                    parsed_value = parser_func(val_hex)
                    name = f"{display_name} ({tag})" if display_name else f"TLV {tag}"
                    root.children.append(ParseNode(name=name, value=parsed_value))
                except:
                    root.children.append(ParseNode(name=f"TLV {tag}", value=f"Length: {length} bytes, Value: (0x{val_hex})"))
            else:
                root.children.append(ParseNode(name=f"TLV {tag}", value=f"Length: {length} bytes, Value: (0x{val_hex})"))
        
        parsed_count += 1
    
    if parsed_count == 0:
        # 没有成功解析任何TLV，返回None
        return None
    
    return root

def parse_tlv_to_node(tag: str, value_hex: str, root: ParseNode = None) -> ParseNode:
    """
    通用的 TLV 解析函数，根据 tag 自动调用对应的解析器
    
    Args:
        tag: TLV tag 字符串
        value_hex: TLV 的值部分（已去掉 tag 和 length）
        root: 可选的根节点，用于获取上下文信息（如event类型）
        
    Returns:
        ParseNode 对象
    """
    parser_func, display_name = get_tlv_parser(tag)
    
    if parser_func:
        try:
            # 对于1C/9C标签，需要从root节点获取event信息
            if tag.upper() in ('1C', '9C') and root is not None:
                event_type = _get_event_from_root(root)
                # 检查解析器是否支持event_type参数
                import inspect
                sig = inspect.signature(parser_func)
                if 'event_type' in sig.parameters:
                    parsed_value = parser_func(value_hex, event_type=event_type)
                else:
                    parsed_value = parser_func(value_hex)
            else:
                parsed_value = parser_func(value_hex)
            name = f"{display_name} ({tag})" if display_name else f"TLV {tag}"
            return ParseNode(name=name, value=parsed_value)
        except Exception as e:
            return ParseNode(name=f"TLV {tag} (Parse Error)", value=f"Error: {e}, Raw: {value_hex[:60]}")
    else:
        # 没有注册的解析器，尝试按TLV格式解析
        tlv_structure = parse_tlv_structure_recursive(value_hex)
        if tlv_structure and len(tlv_structure.children) > 0:
            # 成功解析为TLV结构，返回解析后的树
            tlv_structure.name = f"TLV {tag}"
            return tlv_structure
        else:
            # 无法解析为TLV结构，显示原始数据
            return ParseNode(name=f"TLV {tag}", value=f"Length: {len(value_hex)//2} bytes, Data: (0x{value_hex})")

def parse_tlvs_from_dict(root: ParseNode, tlv_data: dict, required_tags: list = None, optional_tags: list = None, exclude_tags: set = None):
    """
    通用的 TLV 解析函数，从 tlv_data 字典中解析指定的 TLV
    
    Args:
        root: 根 ParseNode，解析结果会添加到其 children
        tlv_data: TLV 数据字典 {tag: value_hex}
        required_tags: 必需标签列表，格式: [('02', '82'), ('1B', '9B')] 或 ['02', '82']
        optional_tags: 可选标签列表，格式同上
        exclude_tags: 排除的标签集合（如 Event List），不会显示为原始数据
    """
    if exclude_tags is None:
        exclude_tags = {'19', '99'}  # 默认排除 Event List
    
    parsed_tags = set()
    
    # 解析必需标签
    if required_tags:
        for tag_group in required_tags:
            if isinstance(tag_group, str):
                tag_group = (tag_group,)
            
            found = False
            for tag in tag_group:
                tag_upper = tag.upper()
                if tag_upper in tlv_data:
                    node = parse_tlv_to_node(tag_upper, tlv_data[tag_upper], root)
                    root.children.append(node)
                    parsed_tags.add(tag_upper)
                    found = True
                    break
            
            if not found:
                # 必需标签未找到，显示警告
                tag_str = '/'.join(tag_group)
                root.children.append(ParseNode(
                    name="Warning",
                    value=f"Required TLV ({tag_str}) not found"
                ))
    
    # 解析可选标签
    if optional_tags:
        for tag_group in optional_tags:
            if isinstance(tag_group, str):
                tag_group = (tag_group,)
            
            for tag in tag_group:
                tag_upper = tag.upper()
                if tag_upper in tlv_data:
                    node = parse_tlv_to_node(tag_upper, tlv_data[tag_upper], root)
                    root.children.append(node)
                    parsed_tags.add(tag_upper)
                    break
    
    # 显示其他未解析的 TLV 数据
    all_excluded = exclude_tags | parsed_tags
    other_tlvs = {tag: val for tag, val in tlv_data.items() if tag.upper() not in all_excluded}
    if other_tlvs:
        for tag, val in other_tlvs.items():
            node = parse_tlv_to_node(tag, val, root)
            root.children.append(node)

# ========== 注册所有已实现的 TLV 解析器 ==========
# 注意：这些函数需要在注册之前定义，所以注册代码放在文件末尾

# Event List (19/99 tag) 事件映射表
EVENT_MAP = {
    '00': 'MT call',
    '01': 'Call connected',
    '02': 'Call disconnected',
    '03': 'Location status',
    '04': 'User activity',
    '05': 'Idle screen available',
    '06': 'Card reader status',
    '07': 'Language selection',
    '08': 'Browser termination',
    '09': 'Data available',
    '0A': 'Channel status',
    '0B': 'Access Technology Change (single access technology)',
    '0C': 'Display parameters changed',
    '0D': 'Local connection',
    '0E': 'Network Search Mode Change',
    '0F': 'Browsing status',
    '10': 'Frames Information Change',
    '11': '(I-)WLAN Access Status',         # Defined in 3GPP TS 31.111
    '12': 'Network Rejection',              # Defined in 3GPP TS 31.111
    '13': 'HCI connectivity event',
    '14': 'Access Technology Change (multiple access technologies)',
    '15': 'CSG cell selection',             # Defined in 3GPP TS 31.111
    '16': 'Contactless state request',
    '17': 'IMS Registration',               # Defined in 3GPP TS 31.111
    '18': 'Incoming IMS data',              # Defined in 3GPP TS 31.111
    '19': 'Profile Container',
    # '1A': 'Void',                         # 1A is Void in standard
    '1B': 'Secured Profile Container',
    '1C': 'Poll Interval Negotiation',
    '1D': 'Data Connection Status Change',  # Defined in 3GPP TS 31.111 
    '1E': 'CAG cell selection',             # Defined in 3GPP TS 31.111 
    '1F': 'Slices Status Change'            # Defined in 3GPP TS 31.111 
}

def parse_event_list_info(value_hex: str) -> str:
    """解析Event List (19/99 tag)的内容"""
    events = []
    for i in range(0, len(value_hex), 2):
        event_code = value_hex[i:i+2]
        event_name = EVENT_MAP.get(event_code, f'Unknown event ({event_code})')
        events.append(event_name)
    
    return ', '.join(events)


def parse_event_list_to_nodes(value_hex: str) -> ParseNode:
    """解析Event List (19/99 tag)的内容，返回包含子节点的ParseNode"""
    root = ParseNode(name="Event List (19)")
    
    for i in range(0, len(value_hex), 2):
        event_code = value_hex[i:i+2]
        event_name = EVENT_MAP.get(event_code, f'Unknown event ({event_code})')
        root.children.append(ParseNode(name=f"Event {event_code}", value=event_name))
    
    return root

def command_details_text(value_hex: str) -> str:
    # Value: cmd_num(1B) | type_of_command(1B) | qualifier(1B)
    cmd_map = {
        "01":"REFRESH","02":"MORE TIME","03":"POLL INTERVAL","04":"POLLING OFF","05":"SET UP EVENT LIST",
        "10":"SET UP CALL","11":"SEND SS","12":"SEND USSD","13":"SEND SHORT MESSAGE","14":"SEND DTMF",
        "15":"LAUNCH BROWSER","16":"GEOGRAPHICAL LOCATION REQUEST","20":"PLAY TONE","21":"DISPLAY TEXT",
        "22":"GET INKEY","23":"GET INPUT","24":"SELECT ITEM","25":"SET UP MENU","26":"PROVIDE LOCAL INFORMATION",
        "27":"TIMER MANAGEMENT","28":"SET UP IDLE MODE TEXT","30":"PERFORM CARD APDU","31":"POWER ON CARD",
        "32":"POWER OFF CARD","33":"GET READER STATUS","34":"RUN AT COMMAND","35":"LANGUAGE NOTIFICATION",
        "40":"OPEN CHANNEL","41":"CLOSE CHANNEL","42":"RECEIVE DATA","43":"SEND DATA","44":"GET CHANNEL STATUS",
        "45":"SERVICE SEARCH","46":"GET SERVICE INFORMATION","47":"DECLARE SERVICE",
        "50":"SET FRAMES","51":"GET FRAMES STATUS","60":"RETRIEVE MULTIMEDIA MESSAGE",
        "61":"SUBMIT MULTIMEDIA MESSAGE","62":"DISPLAY MULTIMEDIA MESSAGE","70":"ACTIVATE",
        "71":"CONTACTLESS STATE CHANGED","73":"ENCAPSULATED SESSION CONTROL","79":"LSI COMMAND",
        "81":"End of the proactive UICC session",
    }
    if len(value_hex) < 6:
        return "Unknown Command"
    cmd = value_hex[2:4].upper()
    q   = value_hex[4:6].upper()
    qual_map = {
        "01":{"00":"NAA Initialization and Full File Change Notification","01":"File Change Notification",
              "02":"NAA Initialization and File Change Notification","03":"NAA Initialization",
              "04":"UICC Reset","05":"NAA Application Reset","06":"NAA Session Reset",
              "07":"Reserved by 3GPP","08":"Reserved by 3GPP","09":"eUICC Profile State Change",
              "0A":"Application Update"},
        "10":{"00":"Set up call, not busy","01":"Set up call, not busy, with redial","02":"Set up call, put others on hold",
              "03":"Set up call, put others on hold, with redial","04":"Set up call, disconnect others",
              "05":"Set up call, disconnect others, with redial"},
        "13":{"00":"Packing not required","01":"SMS packing required"},
        "20":{"00":"Use of vibrate alert is up to the terminal","01":"Vibrate alert with the tone"},
        "21":{"00":"Normal priority","01":"High priority","80":"Clear message after a delay","81":"Wait for user to clear message"},
        "22":{"00":"Digits only","01":"Alphabet set","02":"SMS default alphabet","03":"UCS2 alphabet",
              "04":"Character sets enabled","05":"Character sets disabled, Yes/No response","08":"No help information","09":"Help information available"},
        "23":{"00":"Digits only","01":"Alphabet set","02":"SMS default alphabet","03":"UCS2 alphabet",
              "04":"Echo user input","05":"User input not revealed","08":"No help information","09":"Help information available"},
        "24":{"00":"Presentation type not specified","01":"Presentation type specified",
              "02":"Choice of data values","03":"Choice of navigation options","08":"No help information","09":"Help information available"},
        "25":{"00":"No selection preference","01":"Selection using soft key preferred","08":"No help information","09":"Help information available"},
        "26":{"00":"Location Information","01":"IMEI of the terminal","02":"Network Measurement results","03":"Date, time and time zone",
              "04":"Language setting","05":"Reserved for GSM","06":"Access Technology","07":"ESN of the terminal",
              "08":"IMEISV of the terminal","09":"Search Mode","0A":"Charge State of the Battery","0B":"MEID of the terminal",
              "0C":"Reserved for 3GPP","0D":"Broadcast Network information","0E":"Multiple Access Technologies",
              "0F":"Location Information for multiple access","10":"Network Measurement results for multiple access",
              "1A":"Supported Radio Access Technologies"},
        "27":{"00":"Start","01":"Deactivate","10":"Get current value"},
        "33":{"00":"Card reader status","01":"Card reader identifier"},
        "40":{"00":"On demand link establishment","01":"Immediate link establishment","02":"No automatic reconnection",
              "03":"Automatic reconnection","04":"No background mode","05":"Immediate link establishment in background mode",
              "06":"No DNS server address requested","07":"DNS server address requested"},
        "41":{"00":"No indication","01":"Indication for next CAT command"},
        "43":{"00":"Store data in Tx buffer","01":"Send data immediately"},
        "62":{"00":"Normal priority","01":"High priority","80":"Clear message after a delay","81":"Wait for user to clear message"},
        "73":{"00":"End encapsulated command session","01":"Request Master SA setup","02":"Request Connection SA setup",
              "03":"Request Secure Channel Start","04":"Close Master and Connection SA"},
        "79":{"00":"Proactive Session Request","01":"UICC Platform Reset"},
    }
    cmd_name = cmd_map.get(cmd, f"Unknown({cmd})")
    qual_desc = qual_map.get(cmd, {}).get(q, f"Qualifier {q}")
    return f"{cmd_name} - {qual_desc}"

def device_identities_text(value_hex: str) -> str:
    dev_map = {"01":"Keypad","02":"Display","03":"Earpiece","10":"Additional Reader 0","11":"Additional Reader 1",
               "12":"Additional Reader 2","13":"Additional Reader 3","14":"Additional Reader 4","15":"Additional Reader 5",
               "16":"Additional Reader 6","17":"Additional Reader 7","21":"Channel 1","22":"Channel 2","23":"Channel 3",
               "24":"Channel 4","25":"Channel 5","26":"Channel 6","27":"Channel 7","81":"UICC","82":"Terminal","83":"Network"}
    if len(value_hex) < 4: return f"Unknown device identities (0x{value_hex})"
    s = value_hex[:2].upper(); d = value_hex[2:4].upper()
    return f"{dev_map.get(s,'?')} -> {dev_map.get(d,'?')} (0x{value_hex})"

def result_details_text(value_hex: str) -> str:
    """解析Result Details (03/83 tag) - 完整的result details映射"""
    general_result_map = {
        "00": "Command performed successfully",
        "01": "Command performed with partial comprehension",
        "02": "Command performed, with missing information",
        "03": "REFRESH performed with additional EFs read",
        "04": "Command performed successfully, but requested icon could not be displayed",
        "05": "Command performed, but modified by call control by NAA",
        "06": "Command performed successfully, limited service",
        "07": "Command performed with modification",
        "08": "REFRESH performed but indicated NAA was not active",
        "09": "Command performed successfully, tone not played",
        "10": "Proactive UICC session terminated by the user",
        "11": "Backward move in the proactive UICC session requested by the user",
        "12": "No response from user",
        "13": "Help information required by the user",
        "14": "Reserved for GSM/3G",
        "15": "Reserved for 3GPP (for future usage)",
        "16": "Reserved for 3GPP (for future usage)",
        "20": "Terminal currently unable to process command",
        "21": "Network currently unable to process command",
        "22": "User did not accept the proactive command",
        "23": "User cleared down call before connection or network release",
        "24": "Action in contradiction with the current timer state",
        "25": "Interaction with call control by NAA, temporary problem",
        "26": "Launch browser generic error",
        "27": "MMS temporary problem",
        "28": "Reserved for 3GPP (for future usage)",
        "29": "Reserved for 3GPP (for future usage)",
        "30": "Command beyond terminal's capabilities",
        "31": "Command type not understood by terminal",
        "32": "Command data not understood by terminal",
        "33": "Command number not known by terminal",
        "36": "Error, required values are missing",
        "38": "MultipleCard commands error",
        "39": "Interaction with call control by NAA, permanent problem",
        "3A": "Bearer Independent Protocol error",
        "3B": "Access Technology unable to process command",
        "3C": "Frames error",
        "3D": "MMS Error",
    }

    additional_info_map = {
        "20": {
            "00": "No specific cause can be given",
            "01": "Screen is busy",
            "02": "Terminal currently busy on call",
            "04": "No service",
            "05": "Access control class bar",
            "06": "Radio resource not granted",
            "07": "Not in speech call",
            "09": "Terminal currently busy on SEND DTMF command",
            "0A": "No NAA active",
        },
        "21": {
            "00": "No specific cause can be given",
        },
        "38": {
            "00": "No specific cause can be given",
            "01": "Card reader removed or not present",
            "02": "Card removed or not present",
            "03": "Card reader busy",
            "04": "Card powered off",
            "05": "C-APDU format error",
            "06": "Mute card",
            "07": "Transmission error",
            "08": "Protocol not supported",
            "09": "Specified reader not valid",
        },
        "39": {
            "00": "No specific cause can be given",
            "01": "Action not allowed",
            "02": "The type of request has changed",
        },
        "26": {
            "00": "No specific cause can be given",
            "01": "Bearer unavailable",
            "02": "Browser unavailable",
            "03": "Terminal unable to read the provisioning data",
            "04": "Default URL unavailable",
        },
        "3A": {
            "00": "No specific cause can be given",
            "01": "No channel available",
            "02": "Channel closed",
            "03": "Channel identifier not valid",
            "04": "Requested buffer size not available",
            "05": "Security error (unsuccessful authentication)",
            "06": "Requested UICC/terminal interface transport level not available",
            "07": "Remote device is not reachable",
            "08": "Service error (service not available on remote device)",
            "09": "Service identifier unknown",
            "10": "Port not available",
            "11": "Launch parameters missing or incorrect",
            "12": "Application launch failed",
        },
        "3C": {
            "00": "No specific cause can be given",
            "01": "Frame identifier is not valid",
            "02": "Number of frames beyond the terminal's capabilities",
            "03": "No Frame defined",
            "04": "Requested size not supported",
            "05": "Default Active Frame is not valid",
        },
        "3D": {
            "00": "No specific cause can be given",
        },
    }

    if len(value_hex) < 2:
        return "Unknown General Result"

    general_result = value_hex[:2].upper()
    result_description = general_result_map.get(general_result, "Unknown General Result")

    additional_info = ""
    if len(value_hex) > 2:
        additional_info_code = value_hex[2:4].upper()
        additional_info_description = additional_info_map.get(general_result, {}).get(
            additional_info_code, "Unknown Additional Info"
        )
        additional_info = f", Additional Info: {additional_info_description}"

    return f"Result: {result_description}{additional_info} (0x{value_hex})"

def parse_duration_text(value_hex: str) -> str:
    if len(value_hex) != 4: return f"{value_hex} (0x{value_hex})"
    unit_map = {"00":"minutes","01":"seconds","02":"tenths"}
    unit = unit_map.get(value_hex[:2],"?"); val = _hex2int(value_hex[2:])
    if unit == "tenths": return f"{val/10:.1f} seconds (0x{value_hex})"
    return f"{val} {unit} (0x{value_hex})"

def parse_address_text(value_hex: str) -> str:
    if len(value_hex) < 2: return value_hex
    b = bin(int(value_hex[:2],16))[2:].zfill(8)
    ton_bits = b[1:4]; npi_bits = b[4:8]
    ton = {"000":"Unknown","001":"International","010":"National","011":"Network Specific"}.get(ton_bits,"Reserved")
    npi = {"0000":"Unknown","0001":"ISDN","0011":"Data","0100":"Telex","1001":"Private","1111":"Ext"}.get(npi_bits,"Reserved")
    dn = ""
    raw = value_hex[2:]
    for i in range(0,len(raw),2):
        if i+2<=len(raw):
            dn += raw[i+1:i+2] + raw[i:i+1]
    return f"TON={ton}, NPI={npi}, Dial={dn} (0x{value_hex})"

class ChannelMode:
    """Channel mode enumeration for Channel Status parsing"""
    GENERAL = "GENERAL"             # CS, Packet, IMS, Local, Default
    UICC_SERVER = "UICC_SERVER"     # TCP Server mode
    TERMINAL_SERVER = "TERM_SERVER" # TCP Client / Direct mode

def parse_channel_status_text(value_hex: str, mode: str = ChannelMode.GENERAL) -> str:
    """
    解析 Channel status (38/B8 tag, 8.56)
    
    Reference: ETSI TS 102 223 V18.2.0 Clause 8.56 / 3GPP TS 31.111 V18.11.0 Clause 8.56
    
    Args:
        value_hex: Channel status 的值部分（已去掉 tag 和 length），2字节的十六进制字符串
        mode: Channel mode，可选值：ChannelMode.GENERAL, ChannelMode.UICC_SERVER, ChannelMode.TERMINAL_SERVER
    
    Returns:
        解析后的字符串描述
    """
    if not value_hex or len(value_hex) < 4:
        return f"Invalid data: {value_hex}"
    
    # value_hex 应该是 2 字节 = 4 个十六进制字符
    if len(value_hex) < 4:
        return f"Invalid length: expected 4 hex chars, got {len(value_hex)}"
    
    try:
        # 转换为字节
        data = bytes.fromhex(value_hex)
        if len(data) != 2:
            return f"Invalid length: expected 2 bytes, got {len(data)}"
        
        byte1 = data[0]
        byte2 = data[1]
        
        # --- Byte 1: Channel ID and Status ---
        channel_id = byte1 & 0x07  # Bits 1-3
        
        if channel_id == 0:
            channel_desc = "No channel available"
        else:
            channel_desc = f"Channel {channel_id}"
        
        status_parts = [channel_desc]
        
        # 根据模式解析状态
        status_desc = "Unknown"
        
        if mode == ChannelMode.GENERAL:
            # GENERAL mode (CS, Packet, IMS, Local, Default)
            # Bit 8 indicates link status
            is_established = (byte1 & 0x80) != 0
            status_desc = "Link Established" if is_established else "Link Not Established"
            
        elif mode == ChannelMode.UICC_SERVER:
            # UICC Server Mode: Bits 7-8 indicate TCP state
            tcp_state = (byte1 >> 6) & 0x03
            if tcp_state == 0:
                status_desc = "TCP Closed"
            elif tcp_state == 1:
                status_desc = "TCP Listen"
            elif tcp_state == 2:
                status_desc = "TCP Established"
            else:
                status_desc = "Reserved"
                
        elif mode == ChannelMode.TERMINAL_SERVER:
            # Terminal Server Mode: Bits 7-8 indicate TCP/Direct state
            tcp_state = (byte1 >> 6) & 0x03
            if tcp_state == 0:
                status_desc = "Closed"
            elif tcp_state == 2:
                status_desc = "Established"
            else:
                status_desc = "Reserved"
        
        status_parts.append(status_desc)
        
        # --- Byte 2: Further Info ---
        info_map = {
            0x00: "No further info",
            0x01: "Not used",
            0x02: "Not used",
            0x03: "Not used",
            0x04: "Not used",
            0x05: "Link dropped (network failure or user cancellation)"
        }
        further_info = info_map.get(byte2, f"Reserved (0x{byte2:02X})")
        status_parts.append(further_info)
        
        return ", ".join(status_parts) + f" (0x{value_hex})"
    except Exception as e:
        return f"Parse error: {e}, Raw: {value_hex}"

def parse_channel_data_length_text(value_hex: str) -> str:
    """解析 Channel data length (37/B7 tag, 8.54)"""
    if not value_hex or len(value_hex) < 2:
        return f"Invalid data: {value_hex}"
    
    # Channel data length 数据对象结构：
    # Byte 1: Tag (37/B7) - 已经在调用时去掉了
    # Byte 2: Length = '01' - 已经在调用时去掉了
    # Byte 3: Channel data length (1 byte)
    
    # value_hex 已经是去掉了 tag 和 length 的值部分
    # 应该是 1 字节 = 2 个十六进制字符
    if len(value_hex) < 2:
        return f"Invalid length: expected 2 hex chars, got {len(value_hex)}"
    
    try:
        length_hex = value_hex[:2]
        length_value = int(length_hex, 16)
        
        if length_value == 0xFF:
            return f"more than 255 bytes are available ({value_hex})"
        else:
            return f"{length_value} bytes ({value_hex})"
    except Exception as e:
        return f"Parse error: {e}, Raw: {value_hex}"

def parse_access_tech_text(value_hex: str) -> str:
    """解析 Access Technology (3F/BF tag)"""
    access_tech_map = {
        "00": "GSM",
        "01": "TIA/EIA-553",
        "02": "TIA/EIA-136-270",
        "03": "UTRAN",
        "04": "TETRA",
        "05": "TIA/EIA-95-B",
        "06": "cdma2000 1x (TIA-2000.2)",
        "07": "cdma2000 HRPD (TIA-856)",
        "08": "E-UTRAN",
        "09": "eHRPD",
        "0A": "3GPP NG-RAN",
        "0B": "3GPP Satellite NG-RAN"
    }
    
    technologies = []
    for i in range(0, len(value_hex), 2):
        tech_code = value_hex[i:i+2]
        tech_name = access_tech_map.get(tech_code, f"Reserved (0x{tech_code})")
        technologies.append(f"{tech_name} (0x{tech_code})")
    
    result = ", ".join(technologies)
    return result

def parse_timer_identifier_text(v:str)->str:
    m={'01':'Timer 1','02':'Timer 2','03':'Timer 3','04':'Timer 4','05':'Timer 5','06':'Timer 6','07':'Timer 7','08':'Timer 8'}
    result = m.get(v, v)
    return f"{result} (0x{v})" if result != v else f"{v} (0x{v})"

def parse_timer_value_text(value_hex: str) -> str:
    """解析 Timer value (25/A5 tag) - 3字节 BCD 码 (Hour, Minute, Second)"""
    if not value_hex or len(value_hex) < 6:
        return f"Invalid data: {value_hex}"
    
    # Timer value 数据对象结构：
    # Byte 1: Tag (25/A5) - 已经在调用时去掉了
    # Byte 2: Length = '03' - 已经在调用时去掉了
    # Byte 3-5: Timer value (3 bytes BCD: Hour, Minute, Second)
    
    # value_hex 已经是去掉了 tag 和 length 的值部分
    # 应该是 3 字节 = 6 个十六进制字符
    if len(value_hex) < 6:
        return f"Invalid length: expected 6 hex chars, got {len(value_hex)}"
    
    try:
        # 解析 BCD 编码
        hour_hex = value_hex[0:2]
        minute_hex = value_hex[2:4]
        second_hex = value_hex[4:6]
        
        # BCD 解码
        hour = int(hour_hex, 16)
        minute = int(minute_hex, 16)
        second = int(second_hex, 16)
        
        return f"{hour:02d}:{minute:02d}:{second:02d} (Timer elapsed time) (0x{value_hex})"
    except Exception as e:
        return f"Parse error: {e}, Raw: {value_hex}"

def parse_imei_text(v:str)->str:
    out=""
    for i in range(0,len(v),2):
        b=v[i:i+2]
        if len(b)==2: out += b[1]+b[0]
    return f"{out} (0x{v})"

def parse_bearer_description_text(value_hex: str) -> str:
    """
    解析Bearer Description (35/B5 tag, 8.52)
    
    Reference: TS 31.111 8.52
    """
    bearer_type_map = {
        '01': 'CSD',
        '02': 'GPRS / UTRAN packet service / E-UTRAN / Satellite E-UTRAN / NG-RAN / Satellite NG-RAN',
        '03': 'Default bearer for requested transport layer',
        '04': 'Local link technology independent',
        '05': 'Bluetooth®',
        '06': 'IrDA',
        '07': 'RS232',
        '08': 'cdma2000 packet data service',
        '09': 'UTRAN packet service with extended parameters / HSDPA / E-UTRAN / Satellite E-UTRAN / NG-RAN / Satellite NG-RAN',
        '0A': '(I-)WLAN',
        '0B': 'E-UTRAN / Satellite E-UTRAN / NG-RAN / Satellite NG-RAN / mapped UTRAN packet service',
        '0C': 'NG-RAN / Satellite NG-RAN',
        '0D': 'Reserved for 3GPP',
        '0E': 'Reserved for 3GPP',
    }
    
    if len(value_hex) < 2:
        return "Invalid bearer description: too short"
    
    bearer_type = value_hex[:2]
    bearer_parameters_hex = value_hex[2:]
    bearer_type_description = bearer_type_map.get(bearer_type, 'Unknown Bearer Type')
    
    # 解析 Bearer parameters 根据类型
    params_desc = _parse_bearer_parameters(bearer_type, bearer_parameters_hex)
    
    if params_desc:
        return f"Bearer type: {bearer_type_description}, Parameters: {params_desc} (0x{value_hex})"
    elif bearer_parameters_hex:
        # 有参数但未解析，显示原始值
        return f"Bearer type: {bearer_type_description}, Parameters: {bearer_parameters_hex} (0x{value_hex})"
    else:
        # 没有参数，不显示 Parameters 部分
        return f"Bearer type: {bearer_type_description} (0x{value_hex})"

def _parse_bearer_parameters(bearer_type: str, params_hex: str) -> str:
    """
    解析 Bearer parameters 根据 Bearer type (8.52.1-8.52.6)
    
    Args:
        bearer_type: Bearer type 代码 (如 '01', '02', '09' 等)
        params_hex: Bearer parameters 的十六进制字符串
    
    Returns:
        解析后的参数字符串描述
    """
    if not params_hex:
        return ""
    
    try:
        if bearer_type == '01':  # CSD (8.52.1, X=3)
            if len(params_hex) < 6:
                return f"Incomplete CSD parameters: {params_hex}"
            # Byte 4: Data rate (speed)
            data_rate = params_hex[0:2]
            # Byte 5: Bearer service (name)
            bearer_service = params_hex[2:4]
            # Byte 6: Connection element (ce)
            connection_element = params_hex[4:6]
            return f"Data rate: 0x{data_rate}, Bearer service: 0x{bearer_service}, Connection element: 0x{connection_element}"
        
        elif bearer_type == '02':  # GPRS/UTRAN (8.52.2, X=6)
            if len(params_hex) < 12:
                return f"Incomplete GPRS/UTRAN parameters: {params_hex}"
            # Byte 4-9: QoS parameters
            precedence = params_hex[0:2]
            delay = params_hex[2:4]
            reliability = params_hex[4:6]
            peak = params_hex[6:8]
            mean = params_hex[8:10]
            pdp_type = params_hex[10:12]
            pdp_type_desc = "IP" if pdp_type == '02' else ("Non-IP" if pdp_type == '07' else f"Reserved (0x{pdp_type})")
            return f"Precedence: 0x{precedence}, Delay: 0x{delay}, Reliability: 0x{reliability}, Peak: 0x{peak}, Mean: 0x{mean}, PDP type: {pdp_type_desc}"
        
        elif bearer_type == '09':  # UTRAN with extended parameters (8.52.3, X=17)
            if len(params_hex) < 34:
                return f"Incomplete UTRAN extended parameters: {params_hex}"
            # Byte 4-20: Extended QoS parameters
            traffic_class = params_hex[0:2]
            max_bitrate_ul = params_hex[2:6]
            max_bitrate_dl = params_hex[6:10]
            guaranteed_bitrate_ul = params_hex[10:14]
            guaranteed_bitrate_dl = params_hex[14:18]
            delivery_order = params_hex[18:20]
            max_sdu_size = params_hex[20:22]
            sdu_error_ratio = params_hex[22:24]
            residual_bit_error_ratio = params_hex[24:26]
            delivery_erroneous_sdus = params_hex[26:28]
            transfer_delay = params_hex[28:30]
            traffic_handling_priority = params_hex[30:32]
            pdp_type = params_hex[32:34]
            return (f"Traffic class: 0x{traffic_class}, Max bitrate UL: 0x{max_bitrate_ul}, "
                   f"Max bitrate DL: 0x{max_bitrate_dl}, Guaranteed bitrate UL: 0x{guaranteed_bitrate_ul}, "
                   f"Guaranteed bitrate DL: 0x{guaranteed_bitrate_dl}, Delivery order: 0x{delivery_order}, "
                   f"Max SDU size: 0x{max_sdu_size}, SDU error ratio: 0x{sdu_error_ratio}, "
                   f"Residual bit error ratio: 0x{residual_bit_error_ratio}, Delivery erroneous SDUs: 0x{delivery_erroneous_sdus}, "
                   f"Transfer delay: 0x{transfer_delay}, Traffic handling priority: 0x{traffic_handling_priority}, "
                   f"PDP type: 0x{pdp_type}")
        
        elif bearer_type == '0A':  # (I-)WLAN (8.52.4, X=0)
            return "RFU (no parameters)"
        
        elif bearer_type == '0B':  # E-UTRAN/NG-RAN mapped (8.52.5, X=2/6/10/14)
            if len(params_hex) < 4:
                return f"Incomplete E-UTRAN parameters: {params_hex}"
            # Byte 4: QCI (always present)
            qci = params_hex[0:2]
            # Byte 5 to X+2: Additional QoS parameters (if GBR)
            # Byte X+3: PDP type
            if len(params_hex) >= 4:
                pdp_type = params_hex[-2:] if len(params_hex) >= 4 else "N/A"
                additional_params = params_hex[2:-2] if len(params_hex) > 4 else ""
                if additional_params:
                    return f"QCI: 0x{qci}, Additional QoS: {additional_params}, PDP type: 0x{pdp_type}"
                else:
                    return f"QCI: 0x{qci}, PDP type: 0x{pdp_type}"
            return f"QCI: 0x{qci}"
        
        elif bearer_type == '0C':  # NG-RAN/Satellite NG-RAN (8.52.6, X=1+)
            if len(params_hex) < 2:
                return f"Incomplete NG-RAN parameters: {params_hex}"
            # Byte 4: PDU session type
            pdu_session_type = params_hex[0:2]
            # Further bytes: RFU
            rfu = params_hex[2:] if len(params_hex) > 2 else ""
            if rfu:
                return f"PDU session type: 0x{pdu_session_type}, RFU: {rfu}"
            return f"PDU session type: 0x{pdu_session_type}"
        
        elif bearer_type == '03':  # Default bearer for requested transport layer
            # Bearer type '03' 可能没有参数，或者参数格式未在规范中详细说明
            if params_hex:
                return params_hex  # 如果有参数，返回原始值
            else:
                return ""  # 没有参数，返回空字符串
        
        else:
            # 其他类型，返回原始参数
            return params_hex if params_hex else ""
    
    except Exception as e:
        return f"Parse error: {e}, Raw: {params_hex}"

def parse_data_destination_address_text(value_hex: str) -> str:
    """
    解析Data Destination Address / Other Address (3E/BE tag, 8.58)
    
    Reference: TS 31.111 8.58
    """
    # Null address: Length = '00', no Value part
    if not value_hex or value_hex == "":
        return "Null address (terminal shall request dynamic address)"
    
    if len(value_hex) < 2:
        return f"Invalid address: too short ({value_hex})"
    
    address_type = value_hex[0:2]
    address_data = value_hex[2:]
    
    if address_type == "21":  # IPv4 (8.58)
        # IPv4 address: 4 bytes (octet 4-7)
        if len(address_data) < 8:
            return f"Incomplete IPv4 address: {address_data}"
        ip_bytes = []
        for i in range(0, 8, 2):
            byte_val = int(address_data[i:i+2], 16)
            ip_bytes.append(str(byte_val))
        return f"IPv4: {'.'.join(ip_bytes)} (0x{value_hex})"
    
    elif address_type == "57":  # IPv6 (8.58)
        # IPv6 address: 16 bytes (octet 4-19) = 32 hex chars
        if len(address_data) < 32:
            return f"Incomplete IPv6 address: {address_data} (0x{value_hex})"
        ipv6_groups = []
        for i in range(0, 32, 4):
            group_hex = address_data[i:i+4]
            # Convert to integer and format as hex (remove leading zeros)
            group_int = int(group_hex, 16)
            ipv6_groups.append(f"{group_int:x}")
        return f"IPv6: {':'.join(ipv6_groups)} (0x{value_hex})"
    
    else:
        return f"Reserved address type: 0x{address_type}, Address data: {address_data} (0x{value_hex})"

def parse_location_info_text(value_hex: str) -> str:
    """解析Location Info (13/93 tag)"""
    # Decode MCCMNC
    if len(value_hex) < 6:
        return f"Location info length error (0x{value_hex})"
    
    mccmnc_bytes = value_hex[:6]
    mccmnc = f"{mccmnc_bytes[1]}{mccmnc_bytes[0]}{mccmnc_bytes[3]}{mccmnc_bytes[5]}{mccmnc_bytes[4]}{mccmnc_bytes[2]}"
    
    # 判断长度确定 4G / 5G
    if len(value_hex) == 22:  # 11 bytes => 5G
        tac = value_hex[6:12]
        cell_id = value_hex[12:]
    elif len(value_hex) == 18:  # 9 bytes => 4G
        tac = value_hex[6:10]
        cell_id = value_hex[10:]
    else:
        return f"Invalid location info length: {len(value_hex)//2} bytes (0x{value_hex})"
    
    return f"MCCMNC: {mccmnc}, TAC: {tac}, CELL ID: {cell_id} (0x{value_hex})"

def parse_location_status_text(value_hex: str) -> str:
    """解析 Location status (1B/9B tag)"""
    if not value_hex or len(value_hex) < 2:
        return f"Invalid data: {value_hex}"
    
    # Location status 数据对象结构：
    # Byte 1: Tag (1B/9B) - 已经在调用时去掉了
    # Byte 2: Length (1 byte) - 已经在调用时去掉了
    # Byte 3: Location status value (1 byte)
    
    # value_hex 已经是去掉了 tag 和 length 的值部分
    # 所以第一个字节就是 status value
    status_byte = value_hex[:2]
    status_code = int(status_byte, 16)
    
    # 根据编码显示状态
    status_map = {
        0x00: 'Normal service',
        0x01: 'Limited service',
        0x02: 'No service'
    }
    
    status_description = status_map.get(status_code, f'Unknown status (0x{status_code:02X})')
    
    result = f"{status_description} (0x{status_byte})"
    if len(value_hex) > 2:
        result += f", Additional data: {value_hex[2:]}"
    
    return result

def parse_data_connection_status_text(value_hex: str) -> str:
    """解析 Data connection status (1D/9D tag, 8.137)"""
    if not value_hex or len(value_hex) < 2:
        return f"Invalid data: {value_hex}"
    
    # Data connection status 数据对象结构：
    # Byte 1: Tag (1D/9D) - 已经在调用时去掉了
    # Byte 2: Length = '01' - 已经在调用时去掉了
    # Byte 3: Data connection status value (1 byte)
    
    status_byte = value_hex[:2]
    status_code = int(status_byte, 16)
    
    status_map = {
        0x00: 'Successful',
        0x01: 'Rejected',
        0x02: 'Dropped/Deactivated'
    }
    
    status_description = status_map.get(status_code, f'RFU (0x{status_code:02X})')
    
    return f"{status_description} (0x{status_byte})"

def parse_data_connection_type_text(value_hex: str) -> str:
    """解析 Data connection type (2A/AA tag, 8.138)"""
    if not value_hex or len(value_hex) < 2:
        return f"Invalid data: {value_hex}"
    
    # Data connection type 数据对象结构：
    # Byte 1: Tag (2A/AA) - 已经在调用时去掉了
    # Byte 2: Length = '01' - 已经在调用时去掉了
    # Byte 3: Data connection type (1 byte)
    
    type_byte = value_hex[:2]
    type_code = int(type_byte, 16)
    
    type_map = {
        0x00: 'PDP connection (2G/3G)',
        0x01: 'PDN connection (4G)',
        0x02: 'PDU connection (5G)'
    }
    
    type_description = type_map.get(type_code, f'RFU (0x{type_code:02X})')
    
    return f"{type_description} (0x{type_byte})"

def parse_esm_cause_text(value_hex: str) -> str:
    """解析 (E/5G)SM cause (2E/AE tag, 8.139) - 直接显示 cause value"""
    if not value_hex or len(value_hex) < 2:
        return f"Invalid data: {value_hex}"
    
    # (E/5G)SM cause 数据对象结构：
    # Byte 1: Tag (2E/AE) - 已经在调用时去掉了
    # Byte 2: Length = '01' - 已经在调用时去掉了
    # Byte 3: (E/5G)SM cause value (1 byte)
    
    # 直接显示 value
    return f"0x{value_hex[:2]} ({value_hex[:2]})"

def _get_event_from_root(root: ParseNode) -> str:
    """从root节点中提取event类型"""
    # 查找Event List节点
    for child in root.children:
        if child.name == "Event List (19)":
            # 查找第一个Event子节点
            for event_child in child.children:
                if event_child.name.startswith("Event "):
                    # 提取event代码（如"Event 02" -> "02"）
                    event_code = event_child.name.split()[1] if len(event_child.name.split()) > 1 else None
                    if event_code:
                        return EVENT_MAP.get(event_code, "")
    return None

def parse_transaction_identifier_text(value_hex: str, event_type: str = None) -> str:
    """解析 Transaction identifier (1C/9C tag, 8.28)
    
    Args:
        value_hex: TLV的值部分（已去掉tag和length）
        event_type: 事件类型（如'Call connected', 'Call disconnected', 'MT call'），用于增强解析
    """
    if not value_hex or len(value_hex) < 2:
        return f"Invalid data: {value_hex}"
    
    # Transaction identifier 数据对象结构：
    # Byte 1: Tag (1C/9C) - 已经在调用时去掉了
    # Byte 2: Length (X) - 已经在调用时去掉了
    # Byte 3 to X+2: Transaction identifier list
    
    # value_hex 已经是去掉了 tag 和 length 的值部分
    # 每个字节定义一个 transaction identifier
    identifiers = []
    for i in range(0, len(value_hex), 2):
        if i + 2 > len(value_hex):
            break
        ti_byte = value_hex[i:i+2]
        ti_value = int(ti_byte, 16)
        
        # 解析 TI: bits 5-7 = TI value, bit 8 = TI flag (最高位)
        ti_value_part = (ti_value >> 1) & 0x07  # bits 5-7
        bit_8 = (ti_value >> 7) & 0x01  # bit 8 (最高位)
        
        # 根据event类型进行增强解析
        if event_type and event_type.strip():  # 确保event_type不为None且不为空字符串
            if event_type == 'Call connected':
                if bit_8 == 1:
                    result = "Call connected"
                else:
                    result = "状态未知"
            elif event_type == 'MT call':
                if bit_8 == 0:
                    result = "MT CALL event"
                else:
                    result = "状态未知"
            elif event_type == 'Call disconnected':
                if bit_8 == 0:
                    result = "MO disconnects the call"
                else:
                    result = "MT disconnects the call"
            else:
                # 其他event类型，直接显示值
                result = f"TI={ti_value_part}, Flag={bit_8} (0x{ti_byte})"
            
            identifiers.append(f"{result} (0x{ti_byte})")
        else:
            # 没有event信息，使用默认解析
            identifiers.append(f"TI={ti_value_part}, Flag={bit_8} (0x{ti_byte})")
    
    return ", ".join(identifiers) if identifiers else f"Raw: {value_hex}"

def parse_date_time_timezone_text(value_hex: str) -> str:
    """解析 Date-Time and Time zone (26/A6 tag, 8.39) - 按照 TS 123 040 格式（半字节交换 BCD 码）"""
    if not value_hex or len(value_hex) < 14:
        return f"Invalid data: {value_hex}"
    
    # Date-Time and Time zone 数据对象结构：
    # Byte 1: Tag (26/A6) - 已经在调用时去掉了
    # Byte 2: Length = '07' - 已经在调用时去掉了
    # Byte 3-9: Date-Time and Time zone (7 bytes)
    # 按照 TS 123 040 格式：半字节交换 BCD 码
    # 规则：低4位是十位，高4位是个位，结果 = 十位 * 10 + 个位
    
    # value_hex 已经是去掉了 tag 和 length 的值部分
    # 应该是 7 字节 = 14 个十六进制字符
    if len(value_hex) < 14:
        return f"Invalid length: expected 14 hex chars, got {len(value_hex)}"
    
    try:
        # 解析半字节交换 BCD 编码
        # 例如：52 (hex) = 0101 0010 (binary)
        # 低4位：0010 = 2（十位）
        # 高4位：0101 = 5（个位）
        # 结果：2 * 10 + 5 = 25
        def parse_bcd_swapped(hex_byte):
            """解析半字节交换 BCD：52 -> 25"""
            val = int(hex_byte, 16)
            low_nibble = val & 0x0F  # 低4位（十位）
            high_nibble = (val >> 4) & 0x0F  # 高4位（个位）
            return low_nibble * 10 + high_nibble
        
        year_hex = value_hex[0:2]
        month_hex = value_hex[2:4]
        day_hex = value_hex[4:6]
        hour_hex = value_hex[6:8]
        minute_hex = value_hex[8:10]
        second_hex = value_hex[10:12]
        timezone_hex = value_hex[12:14]
        
        # BCD 解码（半字节交换）
        year = parse_bcd_swapped(year_hex)
        month = parse_bcd_swapped(month_hex)
        day = parse_bcd_swapped(day_hex)
        hour = parse_bcd_swapped(hour_hex)
        minute = parse_bcd_swapped(minute_hex)
        second = parse_bcd_swapped(second_hex)
        
        # Time zone 处理（也采用半字节交换，但包含符号位）
        timezone_val = int(timezone_hex, 16)
        if timezone_val == 0xFF:
            timezone_str = "Unknown"
        else:
            # Time zone 编码：低4位的最高位（bit 3）是符号位，其余是十位；高4位是个位
            # 例如：29 (hex) = 0010 1001 (binary)
            # 低4位：1001 -> bit 3 = 1（负号），低3位 = 001（十位 = 1）
            # 高4位：0010 -> 个位 = 2
            # 值：-12 个 15 分钟 = -180 分钟 = -3 小时
            low_nibble = timezone_val & 0x0F
            high_nibble = (timezone_val >> 4) & 0x0F
            
            # 符号位：bit 3 of low_nibble
            sign_bit = (low_nibble >> 3) & 0x01
            sign = "-" if sign_bit == 1 else "+"
            
            # 十位：低4位的低3位
            tens = low_nibble & 0x07
            # 个位：高4位
            ones = high_nibble
            
            # 计算时区值（以15分钟为单位）
            tz_quarters = tens * 10 + ones
            tz_minutes = tz_quarters * 15
            tz_hours = tz_minutes // 60
            tz_mins = tz_minutes % 60
            
            timezone_str = f"{sign}{tz_hours:02d}:{tz_mins:02d}"
        
        return f"{2000+year}年{month:02d}月{day:02d}日 {hour:02d}:{minute:02d}:{second:02d} (Timezone: {timezone_str}) (0x{value_hex})"
    except Exception as e:
        return f"Parse error: {e}, Raw: {value_hex}"

def parse_address_pdp_pdn_pdu_type_text(value_hex: str) -> str:
    """解析 Address / PDP/PDN/PDU Type (0B/8B tag)"""
    if not value_hex or len(value_hex) < 2:
        return f"Invalid data: {value_hex}"
    
    # Address / PDP/PDN/PDU Type 数据对象结构：
    # Byte 1: Tag (0B/8B) - 已经在调用时去掉了
    # Byte 2: Length = '01' - 已经在调用时去掉了
    # Byte 3: Type value (1 byte)
    
    type_byte = value_hex[:2]
    type_code = int(type_byte, 16)
    
    # Address / PDP/PDN/PDU Type coding
    type_map = {
        0x00: 'IPv4',
        0x01: 'IPv6',
        0x03: 'IPv4v6',
        0x05: 'Non-IP'
    }
    
    type_description = type_map.get(type_code, f'RFU (0x{type_code:02X})')
    
    return f"{type_description} (0x{type_byte})"

def parse_pdp_pdn_pdu_type_text(value_hex: str) -> str:
    """解析 PDP/PDN/PDU type (0C/8C tag, 8.142)"""
    if not value_hex or len(value_hex) < 2:
        return f"Invalid data: {value_hex}"
    
    # PDP/PDN/PDU type 数据对象结构：
    # Byte 1: Tag (0C/8C) - 已经在调用时去掉了
    # Byte 2: Length = '01' - 已经在调用时去掉了
    # Byte 3: PDP/PDN type or PDU Session type (1 byte)
    
    type_byte = value_hex[:2]
    type_code = int(type_byte, 16)
    
    # PDP/PDN type coding
    pdp_pdn_map = {
        0x00: 'IPv4',
        0x01: 'IPv6',
        0x03: 'IPv4v6',
        0x04: 'PPP',
        0x05: 'non IP'
    }
    
    # PDU Session type coding
    pdu_map = {
        0x00: 'IPv4',
        0x01: 'IPv6',
        0x03: 'IPv4v6',
        0x04: 'Unstructured',
        0x05: 'Ethernet'
    }
    
    # 注意：根据 Access Technology 的值来区分是 PDP/PDN 还是 PDU
    # 这里先显示两种可能的解释
    pdp_pdn_desc = pdp_pdn_map.get(type_code, 'RFU')
    pdu_desc = pdu_map.get(type_code, 'RFU')
    
    if pdp_pdn_desc == pdu_desc:
        return f"{pdp_pdn_desc} (0x{type_byte})"
    else:
        return f"PDP/PDN: {pdp_pdn_desc} or PDU: {pdu_desc} (0x{type_byte})"

def parse_media_type_text(value_hex: str) -> str:
    """解析 Media Type (8.132)"""
    if not value_hex or len(value_hex) < 2:
        return f"Invalid data: {value_hex}"
    
    # Media Type 数据对象结构：
    # Byte 1: Tag - 已经在调用时去掉了
    # Byte 2: Length = '01' - 已经在调用时去掉了
    # Byte 3: Media type value (1 byte) - bitmap
    
    # value_hex 已经是去掉了 tag 和 length 的值部分
    # 应该是 1 字节 = 2 个十六进制字符
    if len(value_hex) < 2:
        return f"Invalid length: expected 2 hex chars, got {len(value_hex)}"
    
    try:
        media_type_byte = value_hex[:2]
        media_type_value = int(media_type_byte, 16)
        
        # 解析 bitmap
        # b1: Bit = 1 if the type of media is voice
        # b2: Bit = 1 if the type of media is video
        # b3-b8: RFU (Reserved for Future Use)
        
        media_types = []
        
        # b1 (bit 0, 最低位)
        if media_type_value & 0x01:
            media_types.append("Voice")
        
        # b2 (bit 1)
        if media_type_value & 0x02:
            media_types.append("Video")
        
        # 检查 RFU bits (b3-b8, bits 2-7) 是否都为0
        rfu_bits = (media_type_value >> 2) & 0x3F
        if rfu_bits != 0:
            media_types.append(f"RFU bits set: 0x{rfu_bits:02X}")
        
        if not media_types:
            return f"No media type set (0x{media_type_byte})"
        
        return ", ".join(media_types) + f" (0x{media_type_byte})"
    except Exception as e:
        return f"Parse error: {e}, Raw: {value_hex}"

def parse_ims_call_disconnection_cause_text(value_hex: str) -> str:
    """解析 IMS call disconnection cause (55/D5 tag, 8.133)"""
    if not value_hex or len(value_hex) < 6:
        return f"Invalid data: {value_hex}"
    
    # IMS call disconnection cause 数据对象结构：
    # Byte 1: Tag (55/D5) - 已经在调用时去掉了
    # Byte 2: Length = '03' - 已经在调用时去掉了
    # Byte 3: Protocol (1 byte)
    # Byte 4-5: Cause (2 bytes)
    
    # value_hex 已经是去掉了 tag 和 length 的值部分
    # 应该是 3 字节 = 6 个十六进制字符
    if len(value_hex) < 6:
        return f"Invalid length: expected 6 hex chars, got {len(value_hex)}"
    
    try:
        protocol_hex = value_hex[0:2]
        cause_hex = value_hex[2:6]
        
        protocol_value = int(protocol_hex, 16)
        cause_value = int(cause_hex, 16)
        
        # Protocol 编码
        protocol_map = {
            0x01: 'SIP',
            0x02: 'Q.850'
        }
        
        protocol_desc = protocol_map.get(protocol_value, f'RFU (0x{protocol_hex})')
        
        return f"Protocol: {protocol_desc}, Cause: {cause_value} (0x{cause_hex}) ({value_hex})"
    except Exception as e:
        return f"Parse error: {e}, Raw: {value_hex}"

def parse_cause_text(value_hex: str) -> str:
    """解析 Cause (1A/9A tag, 8.26) - 仅显示 hex 值"""
    # Cause 数据对象结构：
    # Byte 1: Tag (1A/9A) - 已经在调用时去掉了
    # Byte 2: Length (X) - 已经在调用时去掉了
    # Byte 3 to X+2: Cause value
    
    # 直接显示 hex 值，不解析
    return f"{value_hex} ({value_hex})" if value_hex else ""

def parse_buffer_size_text(value_hex: str) -> str:
    """
    解析 Buffer size (39/B9 tag, 8.55)
    
    Reference: TS 31.111 8.55
    """
    if not value_hex:
        return "Invalid buffer size"
    try:
        # Buffer size 是一个整数（字节数）
        buffer_size = int(value_hex, 16)
        return f"{buffer_size} bytes (0x{value_hex})"
    except Exception as e:
        return f"Parse error: {e}, Raw: {value_hex}"

def parse_icon_identifier_text(value_hex: str) -> str:
    """
    解析 Icon identifier (1E/9E tag, 8.31)
    
    Reference: TS 31.111 8.31
    """
    if not value_hex:
        return "Invalid icon identifier"
    try:
        # Icon identifier 通常是 1-2 字节的标识符
        icon_id = int(value_hex, 16)
        return f"Icon ID: {icon_id} (0x{value_hex})"
    except Exception as e:
        return f"Parse error: {e}, Raw: {value_hex}"

def parse_iwlan_identifier_text(value_hex: str) -> str:
    """
    解析 I-WLAN Identifier (4A/CA tag, 8.83)
    
    Reference: TS 31.111 8.83
    TODO: 实现详细解析逻辑
    """
    if not value_hex:
        return "Invalid I-WLAN identifier"
    return f"I-WLAN Identifier: {value_hex}"

def parse_text_attribute_text(value_hex: str) -> str:
    """
    解析 Text Attribute (50/D0 tag, 8.70/8.72)
    
    Reference: TS 31.111 8.70, 8.72
    TODO: 实现详细解析逻辑
    """
    if not value_hex:
        return "Invalid text attribute"
    return f"Text Attribute: {value_hex} ({value_hex})"

def parse_frame_identifier_text(value_hex: str) -> str:
    """
    解析 Frame Identifier (68/E8 tag, 8.80/8.82)
    
    Reference: TS 31.111 8.80, 8.82
    TODO: 实现详细解析逻辑
    """
    if not value_hex:
        return "Invalid frame identifier"
    try:
        frame_id = int(value_hex, 16)
        return f"Frame ID: {frame_id} (0x{value_hex})"
    except Exception as e:
        return f"Parse error: {e}, Raw: {value_hex}"

def parse_iari_text(value_hex: str) -> str:
    """
    解析 IARI (76/F6 tag, 8.110)
    
    Reference: TS 31.111 8.110
    TODO: 实现详细解析逻辑
    """
    if not value_hex:
        return "Invalid IARI"
    return f"IARI: {value_hex} ({value_hex})"

def parse_transport_level_text(value_hex: str) -> str:
    """
    解析 UICC/terminal interface transport level (3C/BC tag, 8.59)
    
    Reference: TS 31.111 8.59
    """
    if not value_hex or len(value_hex) < 2:
        return "Invalid transport level"
    try:
        transport_type = value_hex[:2]
        port_hex = value_hex[2:] if len(value_hex) > 2 else "00"
        port = int(port_hex, 16)
        
        transport_map = {
            "01": "UDP client remote",
            "02": "TCP client remote",
            "03": "TCP server",
            "04": "UDP client local",
            "05": "TCP client local",
            "06": "direct"
        }
        transport_desc = transport_map.get(transport_type, f"Unknown (0x{transport_type})")
        return f"{transport_desc}, port={port} (0x{value_hex})"
    except Exception as e:
        return f"Parse error: {e}, Raw: {value_hex}"

def parse_measurement_qualifier_text(value_hex: str) -> str:
    """解析 UTRAN/E-UTRAN/NG-RAN/Satellite NG-RAN Measurement Qualifier (69/E9 tag)"""
    if not value_hex or len(value_hex) < 2:
        return f"Invalid data: {value_hex}"
    
    # Measurement Qualifier 数据对象结构：
    # Byte 1: Tag (69/E9) - 已经在调用时去掉了
    # Byte 2: Length = '01' - 已经在调用时去掉了
    # Byte 3: Measurement Qualifier value (1 byte)
    
    qualifier_byte = value_hex[:2]
    qualifier_map = {
        '01': 'UTRAN Intra-frequency measurements',
        '02': 'UTRAN Inter-frequency measurements',
        '03': 'UTRAN Inter-RAT (GERAN) measurements',
        '04': 'UTRAN Inter-RAT (E-UTRAN) measurements',
        '05': 'E-UTRAN/Satellite E-UTRAN Intra-frequency measurements',
        '06': 'E-UTRAN/Satellite E-UTRAN Inter-frequency measurements',
        '07': 'E-UTRAN/Satellite E-UTRAN Inter-RAT (GERAN) measurements',
        '08': 'E-UTRAN/Satellite E-UTRAN Inter-RAT (UTRAN) measurements',
        '09': 'E-UTRAN/Satellite E-UTRAN Inter-RAT (NR) measurements',
        '0A': 'NG-RAN/Satellite NG-RAN Intra-frequency measurements',
        '0B': 'NG-RAN/Satellite NG-RAN Inter-frequency measurements',
        '0C': 'NG-RAN/Satellite NG-RAN Inter-RAT (E-UTRAN) measurements',
        '0D': 'NG-RAN/Satellite NG-RAN Inter-RAT (UTRAN) measurements'
    }
    
    qualifier_desc = qualifier_map.get(qualifier_byte.upper(), f'Reserved')
    
    # 统一格式：描述文本 (0x值)
    return f"{qualifier_desc} (0x{qualifier_byte})"

def parse_alpha_identifier_text(value_hex: str) -> str:
    """解析Alpha Identifier (05/85 tag)"""
    try:
        # 尝试解码为ASCII
        if len(value_hex) % 2 == 0:
            decoded = bytes.fromhex(value_hex).decode('ascii', errors='replace')
            # 如果解码后为空或只有空白字符，直接返回空字符串
            if not decoded.strip():
                return ""
            return decoded
        else:
            return value_hex
    except Exception:
        return value_hex

def parse_sms_tpdu_text(value_hex: str) -> str:
    """解析SMS TPDU (0B/8B tag)"""
    if len(value_hex) < 2:
        return f"SMS TPDU: {value_hex}"
    
    # 基本的TPDU类型解析
    tpdu_type = value_hex[:2]
    tpdu_map = {
        '00': 'SMS-DELIVER',
        '01': 'SMS-SUBMIT',
        '02': 'SMS-STATUS-REPORT',
        '04': 'SMS-DELIVER-REPORT',
        '05': 'SMS-SUBMIT-REPORT',
    }
    
    tpdu_name = tpdu_map.get(tpdu_type, f'Unknown TPDU ({tpdu_type})')
    return f"SMS TPDU: {tpdu_name}, Data: {value_hex[2:]} ({value_hex})"

def parse_network_access_name_text(value_hex: str) -> str:
    """解析Network Access Name (47/C7 tag) - 按照 TS 23.003 Label 格式"""
    if len(value_hex) < 2:
        return value_hex
    
    try:
        # 按照 TS 23.003 编码：Label 格式
        # 每个 label 的第一个字节是长度，后面是 ASCII 字符
        # 例如：08 69 6E 74... -> "internet"
        # 显示时需要将长度字节转换为点号分隔
        
        idx = 0
        labels = []
        n = len(value_hex)
        
        # 检查第一个字节是否是有效的长度（0-63，通常 Label 长度不会超过 63）
        first_byte = int(value_hex[0:2], 16) if len(value_hex) >= 2 else 0
        
        # 如果第一个字节看起来不像长度（> 63 或已经是 ASCII 字符），可能是点号分隔格式
        # 尝试按点号分隔格式解析
        if first_byte > 63 or (first_byte >= 0x20 and first_byte <= 0x7E):
            # 可能是点号分隔格式，直接解码
            try:
                decoded = bytes.fromhex(value_hex).decode('ascii', errors='replace')
                # 如果包含点号，返回解码结果和 raw data
                if '.' in decoded:
                    return f"{decoded} (0x{value_hex})"
                # 否则尝试按 Label 格式解析
            except:
                pass
        
        # 按 Label 格式解析
        while idx < n:
            if idx + 2 > n:
                break
            
            # 读取 label 长度
            label_len = int(value_hex[idx:idx+2], 16)
            idx += 2
            
            if label_len == 0:
                break  # 空 label 表示结束
            
            # 检查长度是否合理（Label 长度通常不超过 63）
            if label_len > 63:
                # 长度不合理，可能是数据格式错误，尝试按点号分隔格式解析
                try:
                    decoded = bytes.fromhex(value_hex).decode('ascii', errors='replace')
                    return f"{decoded} (0x{value_hex})"
                except:
                    return f"{value_hex} (0x{value_hex})"
            
            if idx + label_len * 2 > n:
                # 数据不完整
                labels.append(value_hex[idx:])
                break
            
            # 读取 label 内容（ASCII）
            label_bytes = bytes.fromhex(value_hex[idx:idx+label_len*2])
            try:
                label_str = label_bytes.decode('ascii', errors='replace')
                labels.append(label_str)
            except:
                labels.append(label_bytes.hex())
            
            idx += label_len * 2
        
        # 用点号连接所有 labels
        result = '.'.join(labels) if labels else value_hex
        # 统一格式：描述文本 (0x值)
        return f"{result} (0x{value_hex})"
    except Exception as e:
        return f"Parse error: {e}, Raw: {value_hex}"

def parse_terminal_profile_text(value_hex: str) -> str:
    """解析TERMINAL PROFILE (80/10 tag)"""
    if len(value_hex) < 2:
        return f"Invalid TERMINAL PROFILE length: {len(value_hex)//2} bytes"
    
    try:
        # TERMINAL PROFILE 数据直接就是终端能力信息
        # 不需要解析长度字段，因为长度已经在APDU头部中
        profile_data = value_hex
        
        # 使用专门的解析器
        from SIM_APDU_Parser.parsers.CAT.terminal_profile_parser import TerminalProfileParser
        parser = TerminalProfileParser()
        profile_node = parser.parse_profile_data(profile_data)
        
        # 生成简化的文本描述
        capabilities = []
        for child in profile_node.children:
            if child.children:
                byte_name = child.name.split(' (')[0]  # 去掉十六进制部分
                supported = []
                for subchild in child.children:
                    if subchild.name == "Supported" and subchild.value != "None":
                        supported.append(subchild.value)
                    elif subchild.name == "Flags" and subchild.value:
                        supported.append(subchild.value)
                    elif subchild.name == "Value":
                        supported.append(f"Value: {subchild.value}")
                
                if supported:
                    capabilities.append(f"{byte_name}: {', '.join(supported)}")
        
        result = f"Data length: {len(profile_data)//2} bytes"
        if capabilities:
            result += f", Capabilities: {'; '.join(capabilities)}"
        else:
            result += f", Raw data: {profile_data}"
        
        return result
        
    except Exception as e:
        return f"TERMINAL PROFILE parse error: {value_hex}"

def parse_terminal_capability_text(value_hex: str) -> str:
    """解析TERMINAL CAPABILITY (80/AA tag)"""
    # TODO: 实现 TERMINAL CAPABILITY 解析
    return f"TERMINAL CAPABILITY: {value_hex}"

def parse_file_list_text(value_hex: str) -> str:
    """解析File List (12/92 tag)"""
    if len(value_hex) < 2:
        return f"Invalid file list length: {len(value_hex)//2} bytes"
    
    try:
        # 解析文件数量 (第一个字节)
        num_files = int(value_hex[:2], 16)
        
        # 解析文件列表 (从第二个字节开始)
        files_hex = value_hex[2:]
        files = []
        
        # 根据文件数量来解析文件路径
        # 每个文件路径至少4字节
        idx = 0
        for i in range(num_files):
            if idx < len(files_hex):
                # 寻找以3F开头的文件路径
                next_3f = files_hex.find('3F', idx)
                if next_3f != -1:
                    # 找到3F，从3F开始解析文件路径
                    file_start = next_3f
                    # 寻找下一个3F来确定文件路径长度
                    next_file_start = files_hex.find('3F', file_start + 2)
                    if next_file_start != -1:
                        # 找到下一个文件，当前文件路径到下一个文件之前
                        file_path = files_hex[file_start:next_file_start]
                    else:
                        # 没有下一个文件，当前文件路径到数据末尾
                        file_path = files_hex[file_start:]
                    
                    files.append(file_path)
                    idx = file_start + len(file_path)
                else:
                    # 没有找到3F，按固定长度解析（至少4字节）
                    remaining = len(files_hex) - idx
                    if remaining >= 8:
                        file_path = files_hex[idx:idx+8]
                        files.append(file_path)
                        idx += 8
                    else:
                        # 剩余数据不足8字节，取全部
                        file_path = files_hex[idx:]
                        files.append(file_path)
                        break
            else:
                break
        
        result = f"Number of files: {num_files}"
        if files:
            result += f", Files: {', '.join(files)}"
        else:
            result += f", Raw data: {files_hex}"
        
        return f"{result} ({value_hex})"
        
    except Exception as e:
        return f"File list parse error: {value_hex}"

def parse_comp_tlvs_to_nodes(hexstr: str) -> tuple[ParseNode, str]:
    """把 Comprehension TLV 串解析成 ParseNode 子树；返回(root, 首个命令名)。"""
    idx=0; n=len(hexstr); root=ParseNode(name="Comprehension TLVs"); first=None
    while idx+4 <= n:
        tag = hexstr[idx:idx+2].upper(); idx+=2
        ln  = int(hexstr[idx:idx+2],16) if idx+2<=n else 0; idx+=2
        val = hexstr[idx:idx+2*ln] if idx+2*ln<=n else ""; idx += 2*ln

        def is_tag(*alts): return tag in alts
        if is_tag("01","81"):
            txt = command_details_text(val)
            root.children.append(ParseNode(name="Command details (01)", value=txt))
            if first is None: first = txt.split(" - ")[0]
        elif is_tag("02","82"):
            root.children.append(ParseNode(name="Device identities (02)", value=device_identities_text(val)))
        elif is_tag("03","83"):
            root.children.append(ParseNode(name="Result (03)", value=result_details_text(val)))
        elif is_tag("04","84"):
            root.children.append(ParseNode(name="Duration (04)", value=parse_duration_text(val)))
        elif is_tag("05","85"):
            alpha_info = parse_alpha_identifier_text(val)
            root.children.append(ParseNode(name="Alpha identifier (05)", value=alpha_info))
        elif is_tag("06","86"):
            root.children.append(ParseNode(name="Address (06)", value=parse_address_text(val)))
        elif is_tag("38","B8"):
            root.children.append(ParseNode(name="Channel status (38)", value=parse_channel_status_text(val)))
        elif is_tag("0B","8B"):
            # '0B'/'8B' 可能用于 Address / PDP/PDN/PDU Type 或 SMS TPDU
            # 优先尝试解析为 Address / PDP/PDN/PDU Type（更常见）
            if len(val) == 2:
                # 1字节长度，可能是 Address / PDP/PDN/PDU Type
                address_type_info = parse_address_pdp_pdn_pdu_type_text(val)
                root.children.append(ParseNode(name="Address / PDP/PDN/PDU Type (0B)", value=address_type_info))
            else:
                # 其他长度，可能是 SMS TPDU
                sms_info = parse_sms_tpdu_text(val)
                root.children.append(ParseNode(name="SMS TPDU (0B)", value=sms_info))
        elif is_tag("39","B9"):
            buffer_info = parse_buffer_size_text(val)
            root.children.append(ParseNode(name="Buffer size (39)", value=buffer_info))
        elif is_tag("47","C7"):
            network_info = parse_network_access_name_text(val)
            root.children.append(ParseNode(name="Network Access Name (47)", value=network_info))
        elif is_tag("3C","BC"):
            transport_info = parse_transport_level_text(val)
            root.children.append(ParseNode(name="UICC/terminal interface transport level (3C)", value=transport_info))
        elif is_tag("FD","7D"):
            if len(val)>=6:
                mccmnc_raw = val[:6]
                mccmnc = f"{mccmnc_raw[1]}{mccmnc_raw[0]}{mccmnc_raw[3]}{mccmnc_raw[5]}{mccmnc_raw[4]}{mccmnc_raw[2]}"
                tac = val[6:]
                root.children.append(ParseNode(name="MCCMNC+TAC (FD)", value=f"{mccmnc}, TAC:{tac}"))
        elif is_tag("B5","35"):
            bearer_info = parse_bearer_description_text(val)
            root.children.append(ParseNode(name="Bearer description (B5)", value=bearer_info))
        elif is_tag("13","93"):
            location_info = parse_location_info_text(val)
            root.children.append(ParseNode(name="Location Info (13)", value=location_info))
        elif is_tag("14","94"):
            root.children.append(ParseNode(name="IMEI (14)", value=parse_imei_text(val)))
        elif is_tag("62","E2"):
            # IMEISV使用与IMEI相同的BCD编码格式，需要换位处理
            imeisv_decoded = parse_imei_text(val)
            root.children.append(ParseNode(name="IMEISV (62)", value=imeisv_decoded, hint=f"Raw: {val}"))
        elif is_tag("19","99"):
            event_list_node = parse_event_list_to_nodes(val)
            root.children.append(event_list_node)
        elif is_tag("2E","AE"):
            # (E/5G)SM cause (2E/AE tag)
            esm_cause_info = parse_esm_cause_text(val)
            root.children.append(ParseNode(name="(E/5G)SM cause (2E)", value=esm_cause_info))
        elif is_tag("2F","AF"):
            root.children.append(ParseNode(name="AID (2F)", value=val))
        elif is_tag("3E","BE"):
            data_dest_info = parse_data_destination_address_text(val)
            root.children.append(ParseNode(name="Data dest address (3E)", value=data_dest_info))
        elif is_tag("36","B6"):
            root.children.append(ParseNode(name="Channel data (36)", value=val))
        elif is_tag("37","B7"):
            channel_data_length_info = parse_channel_data_length_text(val)
            root.children.append(ParseNode(name="Channel data length (37)", value=channel_data_length_info))
        elif is_tag("3F","BF"):
            root.children.append(ParseNode(name="Access Technology (3F)", value=parse_access_tech_text(val)))
        elif is_tag("A2","22"):
            root.children.append(ParseNode(name="C-APDU (A2)", value=val))
        elif is_tag("A4","24"):
            root.children.append(ParseNode(name="Timer identifier (A4)", value=parse_timer_identifier_text(val)))
        elif is_tag("A5","25"):
            timer_value_info = parse_timer_value_text(val)
            root.children.append(ParseNode(name="Timer value (A5)", value=timer_value_info))
        elif is_tag("21","A1"):
            root.children.append(ParseNode(name="Card ATR (21)", value=val))
        elif is_tag("E0","60"):
            root.children.append(ParseNode(name="MAC (E0)", value=val))
        elif is_tag("A6","26"):
            date_time_info = parse_date_time_timezone_text(val)
            root.children.append(ParseNode(name="Date/Time/TZ (A6)", value=date_time_info))
        elif is_tag("6C","EC"):
            root.children.append(ParseNode(name="MMS Transfer Status (6C)", value=val))
        elif is_tag("7E","FE"):
            # '7E'/'FE' 可能用于 Media Type (8.132) 或 CSG ID list
            # Media Type 长度固定为 1 字节，CSG ID list 长度更长
            if len(val) == 2:  # 1 字节 = Media Type
                media_type_info = parse_media_type_text(val)
                root.children.append(ParseNode(name="Media Type (7E)", value=media_type_info))
            else:  # 其他长度 = CSG ID list
                root.children.append(ParseNode(name="CSG ID list (7E)", value=val))
        elif is_tag("56","D6"):
            root.children.append(ParseNode(name="CSG ID (56)", value=val))
        elif is_tag("57","D7"):
            root.children.append(ParseNode(name="Timer Expiration (57)", value=val))
        # ---------- 新增的 tag 解析 ----------
        elif is_tag("07","87"):
            root.children.append(ParseNode(name="Capability configuration parameters (07)", value=val))
        elif is_tag("08","88"):
            root.children.append(ParseNode(name="Subaddress (08)", value=val))
        elif is_tag("09","89"):
            root.children.append(ParseNode(name="SS string / BSSID / PLMN ID / E-UTRAN/Satellite E-UTRAN Timing Advance (09)", value=val))
        elif is_tag("0A","8A"):
            root.children.append(ParseNode(name="USSD string (0A)", value=val))
        elif is_tag("0C","8C"):
            # 根据上下文判断是 PDP/PDN/PDU type 还是其他用途
            # 如果是1字节长度，可能是 PDP/PDN/PDU type
            if len(val) == 2:
                pdp_pdn_pdu_info = parse_pdp_pdn_pdu_type_text(val)
                root.children.append(ParseNode(name="PDP/PDN/PDU type (0C)", value=pdp_pdn_pdu_info))
            else:
                root.children.append(ParseNode(name="PDP/PDN/PDU type / Cell Broadcast page / PDU session establishment parameters (0C)", value=val))
        elif is_tag("0D","8D"):
            root.children.append(ParseNode(name="Text string (0D)", value=val))
        elif is_tag("0E","8E"):
            root.children.append(ParseNode(name="Tone / eCAT client profile (0E)", value=val))
        elif is_tag("0F","8F"):
            root.children.append(ParseNode(name="Item (0F)", value=parse_item_ecat_client_identity_text(val)))
        elif is_tag("10","90"):
            root.children.append(ParseNode(name="Item identifier / Encapsulated envelope (10)", value=val))
        elif is_tag("11","91"):
            root.children.append(ParseNode(name="Response length / Call control result (11)", value=val))
        elif is_tag("12","92"):
            file_list_info = parse_file_list_text(val)
            root.children.append(ParseNode(name="File List / CAT service list (12)", value=file_list_info))
        elif is_tag("15","95"):
            root.children.append(ParseNode(name="Help request (15)", value=val))
        elif is_tag("16","96"):
            root.children.append(ParseNode(name="Network Measurement Results (16)", value=val))
        elif is_tag("17","97"):
            root.children.append(ParseNode(name="Default Text / Items Next Action Indicator (17)", value=val))
        elif is_tag("1A","9A"):
            cause_info = parse_cause_text(val)
            root.children.append(ParseNode(name="Cause (1A)", value=cause_info))
        elif is_tag("1B","9B"):
            location_status_info = parse_location_status_text(val)
            root.children.append(ParseNode(name="Location status (1B)", value=location_status_info))
        elif is_tag("1C","9C"):
            # 从已解析的节点中获取event类型
            event_type = _get_event_from_root(root)
            transaction_info = parse_transaction_identifier_text(val, event_type)
            root.children.append(ParseNode(name="Transaction identifier (1C)", value=transaction_info))
        elif is_tag("1D","9D"):
            # '1D'/'9D' 可能用于 Data connection status 或 BCCH channel list
            # 如果长度是1字节，可能是 Data connection status
            if len(val) == 2:
                data_conn_status_info = parse_data_connection_status_text(val)
                root.children.append(ParseNode(name="Data connection status (1D)", value=data_conn_status_info))
            else:
                root.children.append(ParseNode(name="BCCH channel list (1D)", value=val))
        elif is_tag("1E","9E"):
            icon_info = parse_icon_identifier_text(val)
            root.children.append(ParseNode(name="Icon identifier (1E)", value=icon_info))
        elif is_tag("4A","CA"):
            iwlan_info = parse_iwlan_identifier_text(val)
            root.children.append(ParseNode(name="I-WLAN Identifier (4A)", value=iwlan_info))
        elif is_tag("50","D0"):
            text_attr_info = parse_text_attribute_text(val)
            root.children.append(ParseNode(name="Text Attribute (50)", value=text_attr_info))
        elif is_tag("68","E8"):
            frame_info = parse_frame_identifier_text(val)
            root.children.append(ParseNode(name="Frame Identifier (68)", value=frame_info))
        elif is_tag("69","E9"):
            measurement_qualifier_info = parse_measurement_qualifier_text(val)
            root.children.append(ParseNode(name="Measurement Qualifier (69)", value=measurement_qualifier_info))
        elif is_tag("76","F6"):
            iari_info = parse_iari_text(val)
            root.children.append(ParseNode(name="IARI (76)", value=iari_info))
        elif is_tag("1F","9F"):
            root.children.append(ParseNode(name="Item Icon identifier list (1F)", value=val))
        elif is_tag("20","A0"):
            root.children.append(ParseNode(name="Card reader status (20)", value=val))
        elif is_tag("23","A3"):
            root.children.append(ParseNode(name="R-APDU / SA template (23)", value=val))
        elif is_tag("27","A7"):
            root.children.append(ParseNode(name="Call control requested action (27)", value=val))
        elif is_tag("28","A8"):
            root.children.append(ParseNode(name="AT Command (28)", value=val))
        elif is_tag("29","A9"):
            root.children.append(ParseNode(name="AT Response (29)", value=val))
        elif is_tag("2A","AA"):
            # '2A'/'AA' 可能用于 Data connection type 或 BC Repeat Indicator
            # 如果长度是1字节，可能是 Data connection type
            if len(val) == 2:
                data_conn_type_info = parse_data_connection_type_text(val)
                root.children.append(ParseNode(name="Data connection type (2A)", value=data_conn_type_info))
            else:
                root.children.append(ParseNode(name="BC Repeat Indicator (2A)", value=val))
        elif is_tag("2B","AB"):
            root.children.append(ParseNode(name="Immediate response (2B)", value=val))
        elif is_tag("2C","AC"):
            root.children.append(ParseNode(name="DTMF string (2C)", value=val))
        elif is_tag("2D","AD"):
            root.children.append(ParseNode(name="Language (2D)", value=val))
        elif is_tag("2E","AE"):
            # '2E'/'AE' 可能用于 (E/5G)SM cause 或 Timing Advance
            # 如果长度是1字节，可能是 (E/5G)SM cause
            if len(val) == 2:
                esm_cause_info = parse_esm_cause_text(val)
                root.children.append(ParseNode(name="(E/5G)SM cause (2E)", value=esm_cause_info))
            else:
                root.children.append(ParseNode(name="Timing Advance (2E)", value=val))
        elif is_tag("30","B0"):
            root.children.append(ParseNode(name="Browser Identity (30)", value=val))
        elif is_tag("32","B2"):
            root.children.append(ParseNode(name="Bearer (32)", value=val))
        elif is_tag("33","B3"):
            root.children.append(ParseNode(name="Provisioning Reference File (33)", value=val))
        elif is_tag("34","B4"):
            root.children.append(ParseNode(name="Browser Termination Cause (34)", value=val))
        elif is_tag("3A","BA"):
            root.children.append(ParseNode(name="Card reader identifier / REFRESH Enforcement Policy (3A)", value=val))
        elif is_tag("3B","BB"):
            root.children.append(ParseNode(name="File Update Information / Application specific refresh data (3B)", value=val))
        elif is_tag("3D","BD"):
            root.children.append(ParseNode(name="Not used (3D)", value=val))
        elif is_tag("40","C0"):
            dns_info = parse_data_destination_address_text(val)
            root.children.append(ParseNode(name="Display parameters / DNS server address (40)", value=dns_info))
        elif is_tag("55","D5"):
            ims_cause_info = parse_ims_call_disconnection_cause_text(val)
            root.children.append(ParseNode(name="IMS call disconnection cause (55)", value=ims_cause_info))
        else:
            # 对于未硬编码的 tag，尝试使用注册的 TLV 解析器
            parser_func, display_name = get_tlv_parser(tag)
            if parser_func:
                try:
                    parsed_value = parser_func(val)
                    name = f"{display_name} ({tag})" if display_name else f"TLV {tag}"
                    root.children.append(ParseNode(name=name, value=parsed_value))
                except Exception as e:
                    root.children.append(ParseNode(name=f"TLV {tag} (Parse Error)", value=f"Error: {e}, Raw: {val[:60]}"))
            else:
                # 没有注册的解析器，尝试按TLV格式解析
                tlv_structure = parse_tlv_structure_recursive(val)
                if tlv_structure and len(tlv_structure.children) > 0:
                    # 成功解析为TLV结构，添加解析后的树
                    tlv_structure.name = f"TLV {tag}"
                    root.children.append(tlv_structure)
                else:
                    # 无法解析为TLV结构，显示原始数据
                    root.children.append(ParseNode(name=f"TLV {tag}", value=f"Length: {ln} bytes, Value: (0x{val})"))
    
    # 对子节点进行分组处理
    root.children = group_similar_tags(root.children)
    
    return root, (first or "")


def parse_item_ecat_client_identity_text(value_hex: str) -> str:
    """
    解析 Item (0F) 数据
    
    Args:
        value_hex: TLV的值部分（不包含标签和长度）
        
    Returns:
        str: 解析结果字符串
    """
    if not value_hex or len(value_hex) < 2:
        return "数据长度不足"
    
    try:
        # 第一个字节是Identifier
        identifier_hex = value_hex[0:2]
        identifier = int(identifier_hex, 16)
        
        # 后面的部分是ASCII
        ascii_hex = value_hex[2:]
        
        if len(ascii_hex) == 0:
            return f"Identifier: {identifier_hex} ({identifier}) ({value_hex})"
        
        # 解码ASCII
        try:
            ascii_bytes = bytes.fromhex(ascii_hex)
            ascii_string = ascii_bytes.decode('ascii', errors='ignore')
            return f"Identifier: {identifier_hex}: '{ascii_string}' ({value_hex})"
        except Exception as e:
            return f"Identifier: {identifier_hex} ({identifier}), ASCII解码错误: {e} ({value_hex})"
            
    except Exception as e:
        return f"解析错误: {e}"


def group_similar_tags(nodes: list) -> list:
    """
    将相同标签的节点分组，创建可折叠的父节点
    
    Args:
        nodes: ParseNode 列表
        
    Returns:
        分组后的 ParseNode 列表
    """
    from collections import defaultdict
    
    # 按标签名称分组
    tag_groups = defaultdict(list)
    
    for node in nodes:
        # 提取标签名称（去掉序号）
        tag_name = node.name
        if '(' in tag_name and ')' in tag_name:
            # 提取标签部分，如 "Display parameters / DNS server address (40)"
            tag_part = tag_name.split('(')[0].strip()
            tag_groups[tag_part].append(node)
        else:
            # 如果没有标签格式，直接添加
            tag_groups[tag_name].append(node)
    
    result = []
    for tag_name, group_nodes in tag_groups.items():
        if len(group_nodes) == 1:
            # 只有一个节点，直接添加
            result.append(group_nodes[0])
        else:
            # 多个节点，创建分组父节点
            parent_node = ParseNode(name=f"{tag_name} ({len(group_nodes)} items)")
            for i, child_node in enumerate(group_nodes):
                # 为子节点添加序号
                child_node.name = f"{i+1}. {child_node.name}"
                parent_node.children.append(child_node)
            result.append(parent_node)
    
    return result

# ========== 注册所有已实现的 TLV 解析器 ==========
# 在文件末尾注册，确保所有解析函数都已定义

# 注册已实现的 TLV 解析器
register_tlv_parser(('02', '82'), device_identities_text, "Device identities")
register_tlv_parser(('06', '86'), parse_address_text, "Address")
register_tlv_parser(('13', '93'), parse_location_info_text, "Location Information")
register_tlv_parser(('1B', '9B'), parse_location_status_text, "Location status")
register_tlv_parser(('3F', 'BF'), parse_access_tech_text, "Access Technology")
register_tlv_parser(('05', '85'), parse_alpha_identifier_text, "Alpha identifier")
register_tlv_parser(('0A', '8A'), lambda v: v, "USSD string")  # TODO: 实现 USSD 解析
register_tlv_parser(('09', '89'), lambda v: v, "SS string")  # TODO: 实现 SS string 解析
register_tlv_parser(('04', '84'), parse_duration_text, "Duration")
register_tlv_parser(('38', 'B8'), parse_channel_status_text, "Channel status")
register_tlv_parser(('37', 'B7'), parse_channel_data_length_text, "Channel data length")
register_tlv_parser(('0B', '8B'), parse_address_pdp_pdn_pdu_type_text, "Address / PDP/PDN/PDU Type")
# 注意：'0B'/'8B' 可能也用于 SMS TPDU，需要根据上下文判断
register_tlv_parser(('47', 'C7'), parse_network_access_name_text, "Network Access Name")
register_tlv_parser(('B5', '35'), parse_bearer_description_text, "Bearer description")
register_tlv_parser(('14', '94'), parse_imei_text, "IMEI")
register_tlv_parser(('62', 'E2'), parse_imei_text, "IMEISV")
register_tlv_parser(('3E', 'BE'), parse_data_destination_address_text, "Data destination address")
register_tlv_parser(('A4', '24'), parse_timer_identifier_text, "Timer identifier")
register_tlv_parser(('A5', '25'), parse_timer_value_text, "Timer value")
register_tlv_parser(('0F', '8F'), parse_item_ecat_client_identity_text, "Item")
register_tlv_parser(('12', '92'), parse_file_list_text, "File List")
# Data Connection Status Change 相关
register_tlv_parser(('1D', '9D'), parse_data_connection_status_text, "Data connection status")
register_tlv_parser(('2A', 'AA'), parse_data_connection_type_text, "Data connection type")
register_tlv_parser(('2E', 'AE'), parse_esm_cause_text, "(E/5G)SM cause")
register_tlv_parser(('1C', '9C'), parse_transaction_identifier_text, "Transaction identifier")
register_tlv_parser(('26', 'A6'), parse_date_time_timezone_text, "Date-Time and Time zone")
register_tlv_parser(('0C', '8C'), parse_pdp_pdn_pdu_type_text, "PDP/PDN/PDU type")
register_tlv_parser(('7E', 'FE'), parse_media_type_text, "Media Type")
register_tlv_parser(('1A', '9A'), parse_cause_text, "Cause")
register_tlv_parser(('55', 'D5'), parse_ims_call_disconnection_cause_text, "IMS call disconnection cause")
# OPEN CHANNEL 相关
register_tlv_parser(('39', 'B9'), parse_buffer_size_text, "Buffer size")
register_tlv_parser(('1E', '9E'), parse_icon_identifier_text, "Icon identifier")
register_tlv_parser(('4A', 'CA'), parse_iwlan_identifier_text, "I-WLAN Identifier")
register_tlv_parser(('3C', 'BC'), parse_transport_level_text, "UICC/terminal interface transport level")
register_tlv_parser(('50', 'D0'), parse_text_attribute_text, "Text Attribute")
register_tlv_parser(('68', 'E8'), parse_frame_identifier_text, "Frame Identifier")
register_tlv_parser(('69', 'E9'), parse_measurement_qualifier_text, "Measurement Qualifier")
register_tlv_parser(('76', 'F6'), parse_iari_text, "IARI")
# 注意：Event List (19/99) 使用特殊的 parse_event_list_to_nodes 函数，不在这里注册
