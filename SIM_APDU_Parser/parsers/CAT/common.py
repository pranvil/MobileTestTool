# parsers/CAT/common.py
from SIM_APDU_Parser.core.models import ParseNode

def _hex2int(h): return int(h, 16) if h else 0

def parse_event_list_info(value_hex: str) -> str:
    """解析Event List (19/99 tag)的内容"""
    event_map = {
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
        '11': '(I-)WLAN Access Status',
        '12': 'Network Rejection',
        '13': 'HCI connectivity event',
        '14': 'Access Technology Change (multiple access technologies)',
        '15': 'CSG cell selection',
        '16': 'Contactless state request',
        '17': 'IMS Registration',
        '18': 'Incoming IMS data',
        '19': 'Profile Container',
        '1B': 'Secured Profile Container',
        '1C': 'Poll Interval Negotiation',
    }
    
    events = []
    for i in range(0, len(value_hex), 2):
        event_code = value_hex[i:i+2]
        event_name = event_map.get(event_code, f'Unknown event ({event_code})')
        events.append(event_name)
    
    return ', '.join(events)


def parse_event_list_to_nodes(value_hex: str) -> ParseNode:
    """解析Event List (19/99 tag)的内容，返回包含子节点的ParseNode"""
    event_map = {
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
        '11': '(I-)WLAN Access Status',
        '12': 'Network Rejection',
        '13': 'HCI connectivity event',
        '14': 'Access Technology Change (multiple access technologies)',
        '15': 'CSG cell selection',
        '16': 'Contactless state request',
        '17': 'IMS Registration',
        '18': 'Incoming IMS data',
        '19': 'Profile Container',
        '1B': 'Secured Profile Container',
        '1C': 'Poll Interval Negotiation',
    }
    
    root = ParseNode(name="Event List (19)")
    
    for i in range(0, len(value_hex), 2):
        event_code = value_hex[i:i+2]
        event_name = event_map.get(event_code, f'Unknown event ({event_code})')
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
    if len(value_hex) < 4: return "Unknown device identities"
    s = value_hex[:2].upper(); d = value_hex[2:4].upper()
    return f"{dev_map.get(s,'?')} -> {dev_map.get(d,'?')}"

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

    return f"Result: {result_description}{additional_info}"

def parse_duration_text(value_hex: str) -> str:
    if len(value_hex) != 4: return f"{value_hex}"
    unit_map = {"00":"minutes","01":"seconds","02":"tenths"}
    unit = unit_map.get(value_hex[:2],"?"); val = _hex2int(value_hex[2:])
    if unit == "tenths": return f"{val/10:.1f} seconds"
    return f"{val} {unit}"

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
    return f"TON={ton}, NPI={npi}, Dial={dn}"

def parse_channel_status_text(value_hex: str) -> str:
    if len(value_hex) < 2: return value_hex
    b3 = int(value_hex[:2],16)
    ch = b3 & 0x07
    est = "BIP channel established" if (b3>>7)&1 else "BIP channel not established"
    further = ""
    if len(value_hex) >= 4:
        b4 = value_hex[2:4]
        if b4 == "00": further = "No further info"
        elif b4 == "05": further = "Link dropped"
    return f"Channel {ch}, {est}" + (f", {further}" if further else "")

def parse_access_tech_text(value_hex: str) -> str:
    m={"00":"GSM","03":"UTRAN","08":"E-UTRAN","0A":"NG-RAN"}
    return ", ".join(m.get(value_hex[i:i+2],"UNK") for i in range(0,len(value_hex),2))

def parse_timer_identifier_text(v:str)->str:
    m={'01':'Timer 1','02':'Timer 2','03':'Timer 3','04':'Timer 4','05':'Timer 5','06':'Timer 6','07':'Timer 7','08':'Timer 8'}
    return m.get(v, v)

def parse_imei_text(v:str)->str:
    out=""
    for i in range(0,len(v),2):
        b=v[i:i+2]
        if len(b)==2: out += b[1]+b[0]
    return out

def parse_bearer_description_text(value_hex: str) -> str:
    """解析Bearer Description (35/B5 tag)"""
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
    }
    
    if len(value_hex) < 2:
        return "Invalid bearer description"
    
    bearer_type = value_hex[:2]
    bearer_parameters = value_hex[2:]
    bearer_type_description = bearer_type_map.get(bearer_type, 'Unknown Bearer Type')
    
    return f"Bearer type: {bearer_type_description}, Bearer parameters: {bearer_parameters}"

def parse_data_destination_address_text(value_hex: str) -> str:
    """解析Data Destination Address (3E/BE tag)"""
    if len(value_hex) < 2:
        return "Unknown IP type"
    
    ip_type_byte = value_hex[0:2]
    ip_address = []
    
    if ip_type_byte == "21":  # IPv4
        for i in range(2, len(value_hex), 2):
            byte = int(value_hex[i:i+2], 16)
            ip_address.append(str(byte))
        return f"IPV4: {'.'.join(ip_address)}"
    elif ip_type_byte == "57":  # IPv6
        for i in range(2, len(value_hex), 4):
            byte_pair = value_hex[i:i+4]
            ip_address.append(byte_pair)
        return f"IPV6: {':'.join(ip_address)}"
    else:
        return "Unknown IP type"

def parse_location_info_text(value_hex: str) -> str:
    """解析Location Info (13/93 tag)"""
    # Decode MCCMNC
    if len(value_hex) < 6:
        return "Location info length error"
    
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
        return f"Invalid location info length: {len(value_hex)//2} bytes"
    
    return f"MCCMNC: {mccmnc}, TAC: {tac}, CELL ID: {cell_id}"

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
    return f"SMS TPDU: {tpdu_name}, Data: {value_hex[2:]}"

def parse_network_access_name_text(value_hex: str) -> str:
    """解析Network Access Name (47/C7 tag)"""
    if len(value_hex) < 2:
        return value_hex
    
    try:
        # 跳过第一个字节，解码剩余部分
        if len(value_hex) >= 4:
            decoded = bytes.fromhex(value_hex[2:]).decode('ascii', errors='replace')
            return decoded
        else:
            return value_hex
    except Exception:
        return value_hex

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
        
        return result
        
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
            sms_info = parse_sms_tpdu_text(val)
            root.children.append(ParseNode(name="SMS TPDU (0B)", value=sms_info))
        elif is_tag("39","B9"):
            root.children.append(ParseNode(name="Buffer size (39)", value=str(int(val or "0",16))))
        elif is_tag("47","C7"):
            network_info = parse_network_access_name_text(val)
            root.children.append(ParseNode(name="Network Access Name (47)", value=network_info))
        elif is_tag("3C","BC"):
            t = val[:2]; port = int(val[2:] or "0",16)
            pm = {"01":"UDP client remote","02":"TCP client remote","03":"TCP server","04":"UDP client local","05":"TCP client local","06":"direct"}
            root.children.append(ParseNode(name="Transport Protocol (3C)", value=f"{pm.get(t,'?')}, port={port}"))
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
        elif is_tag("2F","AF"):
            root.children.append(ParseNode(name="AID (2F)", value=val))
        elif is_tag("3E","BE"):
            data_dest_info = parse_data_destination_address_text(val)
            root.children.append(ParseNode(name="Data dest address (3E)", value=data_dest_info))
        elif is_tag("36","B6"):
            root.children.append(ParseNode(name="Channel data (36)", value=val))
        elif is_tag("37","B7"):
            root.children.append(ParseNode(name="Channel data length (37)", value=val))
        elif is_tag("3F","BF"):
            root.children.append(ParseNode(name="Access Technology (3F)", value=parse_access_tech_text(val)))
        elif is_tag("A2","22"):
            root.children.append(ParseNode(name="C-APDU (A2)", value=val))
        elif is_tag("A4","24"):
            root.children.append(ParseNode(name="Timer identifier (A4)", value=parse_timer_identifier_text(val)))
        elif is_tag("A5","25"):
            root.children.append(ParseNode(name="Timer (A5)", value=f"{val[0:2]}:{val[2:4]}:{val[4:6]}" if len(val)>=6 else val))
        elif is_tag("21","A1"):
            root.children.append(ParseNode(name="Card ATR (21)", value=val))
        elif is_tag("E0","60"):
            root.children.append(ParseNode(name="MAC (E0)", value=val))
        elif is_tag("A6","26"):
            root.children.append(ParseNode(name="Date/Time/TZ (A6)", value=val))
        elif is_tag("6C","EC"):
            root.children.append(ParseNode(name="MMS Transfer Status (6C)", value=val))
        elif is_tag("7E","FE"):
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
            root.children.append(ParseNode(name="Cause (1A)", value=val))
        elif is_tag("1B","9B"):
            root.children.append(ParseNode(name="Location status (1B)", value=val))
        elif is_tag("1C","9C"):
            root.children.append(ParseNode(name="Transaction identifier (1C)", value=val))
        elif is_tag("1D","9D"):
            root.children.append(ParseNode(name="BCCH channel list (1D)", value=val))
        elif is_tag("1E","9E"):
            root.children.append(ParseNode(name="Icon identifier (1E)", value=val))
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
            root.children.append(ParseNode(name="BC Repeat Indicator / Data connection type (2A)", value=val))
        elif is_tag("2B","AB"):
            root.children.append(ParseNode(name="Immediate response (2B)", value=val))
        elif is_tag("2C","AC"):
            root.children.append(ParseNode(name="DTMF string (2C)", value=val))
        elif is_tag("2D","AD"):
            root.children.append(ParseNode(name="Language (2D)", value=val))
        elif is_tag("2E","AE"):
            root.children.append(ParseNode(name="Timing Advance / E/5G (2E)", value=val))
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
        else:
            root.children.append(ParseNode(name=f"TLV {tag}", value=f"len={ln}", hint=val[:120]))
    
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
            return f"Identifier: {identifier_hex} ({identifier})"
        
        # 解码ASCII
        try:
            ascii_bytes = bytes.fromhex(ascii_hex)
            ascii_string = ascii_bytes.decode('ascii', errors='ignore')
            return f"Identifier: {identifier_hex}: '{ascii_string}'"
        except Exception as e:
            return f"Identifier: {identifier_hex} ({identifier}), ASCII解码错误: {e}"
            
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
