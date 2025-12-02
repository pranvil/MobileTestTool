# parsers/CAT/terminal_profile_parser.py
from SIM_APDU_Parser.core.models import ParseNode

class TerminalProfileParser:
    """TERMINAL PROFILE 解析器"""
    
    def __init__(self):
        self.profile_rules = self._get_profile_rules()
    
    def _get_ordinal_suffix(self, n: int) -> str:
        """将数字转换为序数词（first, second, third, twenty-first等）"""
        ordinal_map = {
            1: "First", 2: "Second", 3: "Third", 4: "Fourth", 5: "Fifth",
            6: "Sixth", 7: "Seventh", 8: "Eighth", 9: "Ninth", 10: "Tenth",
            11: "Eleventh", 12: "Twelfth", 13: "Thirteenth", 14: "Fourteenth", 15: "Fifteenth",
            16: "Sixteenth", 17: "Seventeenth", 18: "Eighteenth", 19: "Nineteenth", 20: "Twentieth",
            21: "Twenty-first", 22: "Twenty-second", 23: "Twenty-third", 24: "Twenty-fourth", 25: "Twenty-fifth",
            26: "Twenty-sixth", 27: "Twenty-seventh", 28: "Twenty-eighth", 29: "Twenty-ninth", 30: "Thirtieth",
            31: "Thirty-first", 32: "Thirty-second", 33: "Thirty-third", 34: "Thirty-fourth", 35: "Thirty-fifth",
            36: "Thirty-sixth", 37: "Thirty-seventh", 38: "Thirty-eighth", 39: "Thirty-ninth", 40: "Fortieth"
        }
        return ordinal_map.get(n, f"{n}th")
    
    def _get_profile_rules(self):
        """获取 TERMINAL PROFILE 解析规则（嵌入在代码中）"""
        return self._get_embedded_rules()
    
    def parse_profile_data(self, profile_data_hex: str) -> ParseNode:
        """解析 TERMINAL PROFILE 数据"""
        root = ParseNode(name="TERMINAL PROFILE")
        
        if not self.profile_rules:
            root.children.append(ParseNode(name="Error", value="Failed to load profile rules"))
            return root
        
        byte_index = 1  # 从第1个字节开始
        
        for i in range(0, len(profile_data_hex), 2):
            if i + 2 <= len(profile_data_hex):
                byte_hex = profile_data_hex[i:i+2]
                byte_value = int(byte_hex, 16)
                
                # 查找对应的规则
                rule = None
                for r in self.profile_rules:
                    if r.get("byte") == byte_index:
                        rule = r
                        break
                
                if rule:
                    byte_node = self._parse_byte(rule, byte_value, byte_hex)
                    root.children.append(byte_node)
                
                byte_index += 1
        
        return root
    
    def _parse_byte(self, rule: dict, byte_value: int, byte_hex: str) -> ParseNode:
        """解析单个字节"""
        byte_name = rule.get("name", f"Byte {rule.get('byte', '?')}")
        byte_type = rule.get("type", "unknown")
        byte_index = rule.get("byte", 0)
        ordinal = self._get_ordinal_suffix(byte_index)
        
        byte_node = ParseNode(name=f"{byte_name} ({byte_hex}) - {ordinal} byte")
        
        if byte_type == "flags":
            self._parse_flags(byte_node, rule, byte_value)
        elif byte_type == "value":
            self._parse_value(byte_node, rule, byte_value)
        elif byte_type == "mixed":
            self._parse_mixed(byte_node, rule, byte_value)
        elif byte_type == "flags+value":
            self._parse_flags_value(byte_node, rule, byte_value)
        else:
            byte_node.children.append(ParseNode(name="Unknown type", value=f"Raw: {byte_hex}"))
        
        return byte_node
    
    def _parse_flags(self, byte_node: ParseNode, rule: dict, byte_value: int):
        """解析 flags 类型字节"""
        bits = rule.get("bits", {})
        
        # 显示所有能力（b1 到 b8），支持的显示 Supported，不支持的显示 Not Supported
        for bit_pos in range(1, 9):  # b1 到 b8
            bit_key = f"b{bit_pos}"
            if bit_key in bits:
                bit_mask = 1 << (bit_pos - 1)  # b1=0x01, b2=0x02, b3=0x04, ...
                is_supported = (byte_value & bit_mask) != 0
                status = "Supported" if is_supported else "Not Supported"
                byte_node.children.append(ParseNode(name=status, value=bits[bit_key]))
    
    def _parse_value(self, byte_node: ParseNode, rule: dict, byte_value: int):
        """解析 value 类型字节"""
        value_rules = rule.get("value_rules", "")
        byte_node.children.append(ParseNode(name="Value", value=str(byte_value)))
        if value_rules:
            byte_node.children.append(ParseNode(name="Description", value=value_rules))
    
    def _parse_mixed(self, byte_node: ParseNode, rule: dict, byte_value: int):
        """解析 mixed 类型字节（既有flags又有value）"""
        bits = rule.get("bits", {})
        value_rules = rule.get("value_rules", "")
        
        # 解析flags部分 - 显示所有能力
        for bit_pos in range(1, 9):
            bit_key = f"b{bit_pos}"
            if bit_key in bits:
                bit_mask = 1 << (bit_pos - 1)
                is_supported = (byte_value & bit_mask) != 0
                status = "Supported" if is_supported else "Not Supported"
                byte_node.children.append(ParseNode(name=status, value=bits[bit_key]))
        
        # 解析value部分
        if value_rules:
            byte_node.children.append(ParseNode(name="Value", value=str(byte_value)))
            byte_node.children.append(ParseNode(name="Description", value=value_rules))
    
    def _parse_flags_value(self, byte_node: ParseNode, rule: dict, byte_value: int):
        """解析 flags+value 类型字节"""
        bits = rule.get("bits", {})
        value_rules = rule.get("value_rules", "")
        
        # 解析flags部分（b1-b5 是bearer类型）- 显示所有能力
        for bit_pos in range(1, 6):  # b1-b5 是bearer类型
            bit_key = f"b{bit_pos}"
            if bit_key in bits:
                bit_mask = 1 << (bit_pos - 1)
                is_supported = (byte_value & bit_mask) != 0
                status = "Supported" if is_supported else "Not Supported"
                byte_node.children.append(ParseNode(name=status, value=bits[bit_key]))
        
        # 解析value部分（通常是低3位）
        if value_rules:
            # 提取低3位作为value
            value_part = byte_value & 0x07  # 低3位
            byte_node.children.append(ParseNode(name="Channels", value=str(value_part)))
            byte_node.children.append(ParseNode(name="Description", value=value_rules))
    
    def _get_embedded_rules(self):
        """返回嵌入的 TERMINAL PROFILE 解析规则"""
        return [
            {
                "byte": 1,
                "name": "Download",
                "type": "flags",
                "bits": {
                "b1": "Profile download",
                "b2": "SMS-PP data download",
                "b3": "Cell Broadcast data download",
                "b4": "Menu selection",
                "b5": "SMS-PP data download",
                "b6": "Timer expiration",
                "b7": "USSD string data object supported in Call Control by USIM",
                "b8": "Call Control by NAA"
                }
            },
            {
                "byte": 2,
                "name": "Other",
                "type": "flags",
                "bits": {
                "b1": "Command result",
                "b2": "Call Control by NAA",
                "b3": "Call Control by NAA",
                "b4": "MO short message control support",
                "b5": "MO short message control by USIM",
                "b6": "UCS2 Entry supported",
                "b7": "UCS2 Display supported",
                "b8": "Display Text"
                }
            },
            {
                "byte": 3,
                "name": "Proactive UICC",
                "type": "flags",
                "bits": {
                "b1": "Proactive UICC: DISPLAY TEXT",
                "b2": "Proactive UICC: GET INKEY",
                "b3": "Proactive UICC: GET INPUT",
                "b4": "Proactive UICC: MORE TIME",
                "b5": "Proactive UICC: PLAY TONE",
                "b6": "Proactive UICC: POLL INTERVAL",
                "b7": "Proactive UICC: POLLING OFF",
                "b8": "Proactive UICC: REFRESH"
                }
            },
            {
                "byte": 4,
                "name": "Proactive UICC",
                "type": "flags",
                "bits": {
                "b1": "Proactive UICC: SELECT ITEM",
                "b2": "Proactive UICC: SEND SHORT MESSAGE with 3GPP-SMS-TPDU",
                "b3": "Proactive UICC: SEND SS",
                "b4": "Proactive UICC: SEND USSD",
                "b5": "Proactive UICC: SET UP CALL",
                "b6": "Proactive UICC: SET UP MENU",
                "b7": "Proactive UICC: PROVIDE LOCAL INFORMATION (MCC, MNC, LAC, Cell ID & IMEI)",
                "b8": "Proactive UICC: PROVIDE LOCAL INFORMATION (NMR)"
                }
            },
            {
                "byte": 5,
                "name": "Event driven information",
                "type": "flags",
                "bits": {
                "b1": "Proactive UICC: SET UP EVENT LIST",
                "b2": "Event: MT call",
                "b3": "Event: Call connected",
                "b4": "Event: Call disconnected",
                "b5": "Event: Location status",
                "b6": "Event: User activity",
                "b7": "Event: Idle screen available",
                "b8": "Event: Card reader status"
                }
            },
            {
                "byte": 6,
                "name": "Event driven information extensions",
                "type": "flags",
                "bits": {
                "b1": "Event: Language selection",
                "b2": "Event: Browser Termination",
                "b3": "Event: Data available",
                "b4": "Event: Channel status",
                "b5": "Event: Access Technology Change",
                "b6": "Event: Display parameters changed",
                "b7": "Event: Local Connection",
                "b8": "Event: Network Search Mode Change"
                }
            },
            {
                "byte": 7,
                "name": "Multiple card proactive commands",
                "type": "flags",
                "bits": {
                "b1": "Proactive UICC: POWER ON CARD",
                "b2": "Proactive UICC: POWER OFF CARD",
                "b3": "Proactive UICC: PERFORM CARD APDU",
                "b4": "Proactive UICC: GET READER STATUS (Card reader status)",
                "b5": "Proactive UICC: GET READER STATUS (Card reader identifier)",
                "b6": "RFU, bit = 0",
                "b7": "RFU, bit = 0",
                "b8": "RFU, bit = 0"
                }
            },
            {
                "byte": 8,
                "name": "Proactive UICC",
                "type": "flags",
                "bits": {
                "b1": "Proactive UICC: TIMER MANAGEMENT (start, stop)",
                "b2": "Proactive UICC: TIMER MANAGEMENT (get current value)",
                "b3": "Proactive UICC: PROVIDE LOCAL INFORMATION (date, time and time zone)",
                "b4": "GET INKEY",
                "b5": "SET UP IDLE MODE TEXT",
                "b6": "RUN AT COMMAND",
                "b7": "SET UP CALL",
                "b8": "Call Control by NAA"
                }
            },
            {
                "byte": 9,
                "name": "Proactive UICC",
                "type": "flags",
                "bits": {
                "b1": "DISPLAY TEXT",
                "b2": "SEND DTMF command",
                "b3": "Proactive UICC: PROVIDE LOCAL INFORMATION (NMR)",
                "b4": "Proactive UICC: PROVIDE LOCAL INFORMATION (language)",
                "b5": "Proactive UICC: PROVIDE LOCAL INFORMATION (Timing Advance)",
                "b6": "Proactive UICC: LANGUAGE NOTIFICATION",
                "b7": "Proactive UICC: LAUNCH BROWSER",
                "b8": "Proactive UICC: PROVIDE LOCAL INFORMATION (Access Technology)"
                }
            },
            {
                "byte": 10,
                "name": "Soft keys support",
                "type": "flags",
                "bits": {
                "b1": "Soft keys support for SELECT ITEM",
                "b2": "Soft Keys support for SET UP MENU",
                "b3": "RFU, bit = 0",
                "b4": "RFU, bit = 0",
                "b5": "RFU, bit = 0",
                "b6": "RFU, bit = 0",
                "b7": "RFU, bit = 0",
                "b8": "RFU, bit = 0"
                }
            },
            {
                "byte": 11,
                "name": "Soft keys information",
                "type": "byte_value",
                "description": "Maximum number of soft keys available"
            },
            {
                "byte": 12,
                "name": "Bearer Independent protocol proactive commands",
                "type": "flags",
                "bits": {
                "b1": "Proactive UICC: OPEN CHANNEL",
                "b2": "Proactive UICC: CLOSE CHANNEL",
                "b3": "Proactive UICC: RECEIVE DATA",
                "b4": "Proactive UICC: SEND DATA",
                "b5": "Proactive UICC: GET CHANNEL STATUS",
                "b6": "Proactive UICC: SERVICE SEARCH",
                "b7": "Proactive UICC: GET SERVICE INFORMATION",
                "b8": "Proactive UICC: DECLARE SERVICE"
                }
            },
            {
                "byte": 13,
                "name": "Bearer Independent protocol supported bearers",
                "type": "flags",
                "bits": {
                "b1": "CSD",
                "b2": "GPRS",
                "b3": "Bluetooth",
                "b4": "IrDA",
                "b5": "RS232",
                "b6": "Number of channels supported by terminal (bit 1)",
                "b7": "Number of channels supported by terminal (bit 2)",
                "b8": "Number of channels supported by terminal (bit 3)"
                }
            },
            {
                "byte": 14,
                "name": "Screen height",
                "type": "flags",
                "bits": {
                "b1": "Number of characters supported down the terminal display (bit 1)",
                "b2": "Number of characters supported down the terminal display (bit 2)",
                "b3": "Number of characters supported down the terminal display (bit 3)",
                "b4": "Number of characters supported down the terminal display (bit 4)",
                "b5": "Number of characters supported down the terminal display (bit 5)",
                "b6": "No display capability",
                "b7": "No keypad available",
                "b8": "Screen Sizing Parameters supported"
                }
            },
            {
                "byte": 15,
                "name": "Screen width",
                "type": "flags",
                "bits": {
                "b1": "Number of characters supported across the terminal display (bit 1)",
                "b2": "Number of characters supported across the terminal display (bit 2)",
                "b3": "Number of characters supported across the terminal display (bit 3)",
                "b4": "Number of characters supported across the terminal display (bit 4)",
                "b5": "Number of characters supported across the terminal display (bit 5)",
                "b6": "Number of characters supported across the terminal display (bit 6)",
                "b7": "Number of characters supported across the terminal display (bit 7)",
                "b8": "Variable size fonts"
                }
            },
            {
                "byte": 16,
                "name": "Screen effects",
                "type": "flags",
                "bits": {
                "b1": "Display can be resized",
                "b2": "Text Wrapping supported",
                "b3": "Text Scrolling supported",
                "b4": "Text Attributes supported",
                "b5": "RFU",
                "b6": "Width reduction when in a menu",
                "b7": "RFU",
                "b8": "RFU"
                }
            },
            {
                "byte": 17,
                "name": "Bearer independent protocol supported transport interface/bearers",
                "type": "flags",
                "bits": {
                "b1": "TCP, UICC in client mode, remote connection",
                "b2": "UDP, UICC in client mode, remote connection",
                "b3": "TCP, UICC in server mode",
                "b4": "TCP, UICC in client mode, local connection",
                "b5": "UDP, UICC in client mode, local connection",
                "b6": "Direct communication channel",
                "b7": "E-UTRAN",
                "b8": "HSDPA"
                }
            },
            {
                "byte": 18,
                "name": "Additional display/PLI/BIP features",
                "type": "flags",
                "bits": {
                "b1": "Proactive UICC: DISPLAY TEXT (Variable Time out)",
                "b2": "Proactive UICC: GET INKEY (help is supported while waiting for immediate response or variable timeout)",
                "b3": "USB",
                "b4": "Proactive UICC: GET INKEY (Variable Timeout)",
                "b5": "Proactive UICC: PROVIDE LOCAL INFORMATION (ESN)",
                "b6": "Call control on GPRS",
                "b7": "Proactive UICC: PROVIDE LOCAL INFORMATION (IMEISV)",
                "b8": "Proactive UICC: PROVIDE LOCAL INFORMATION (Search Mode change)"
                }
            },
            {
                "byte": 19,
                "name": "Reserved for TIA/EIA-136-270 facilities",
                "type": "flags",
                "bits": {
                "b1": "Reserved by TIA/EIA-136-270 (Protocol Version support)",
                "b2": "RFU, bit = 0",
                "b3": "RFU, bit = 0",
                "b4": "RFU, bit = 0",
                "b5": "RFU, bit = 0",
                "b6": "RFU, bit = 0",
                "b7": "RFU, bit = 0",
                "b8": "RFU, bit = 0"
                }
            },
            {
                "byte": 20,
                "name": "Reserved for 3GPP2 C.S0035-B CCAT",
                "type": "flags",
                "bits": {
                "b1": "Reserved by 3GPP2",
                "b2": "Reserved by 3GPP2",
                "b3": "Reserved by 3GPP2",
                "b4": "Reserved by 3GPP2",
                "b5": "Reserved by 3GPP2",
                "b6": "Reserved by 3GPP2",
                "b7": "Reserved by 3GPP2",
                "b8": "Reserved by 3GPP2"
                }
            },
            {
                "byte": 21,
                "name": "Extended Launch Browser Capability",
                "type": "flags",
                "bits": {
                "b1": "WML",
                "b2": "XHTML",
                "b3": "HTML",
                "b4": "CHTML",
                "b5": "RFU, bit = 0",
                "b6": "RFU, bit = 0",
                "b7": "RFU, bit = 0",
                "b8": "RFU, bit = 0"
                }
            },
            {
                "byte": 22,
                "name": "Multimedia & extended PLI features",
                "type": "flags",
                "bits": {
                "b1": "Support of UTRAN PS with extended parameters",
                "b2": "Proactive UICC: PROVIDE LOCAL INFORMATION (battery state)",
                "b3": "Proactive UICC: PLAY TONE (Melody tones and Themed tones supported)",
                "b4": "Multi-media Calls in SET UP CALL",
                "b5": "Toolkit-initiated GBA",
                "b6": "Proactive UICC: RETRIEVE MULTIMEDIA MESSAGE",
                "b7": "Proactive UICC: SUBMIT MULTIMEDIA MESSAGE",
                "b8": "Proactive UICC: DISPLAY MULTIMEDIA MESSAGE"
                }
            },
            {
                "byte": 23,
                "name": "Frames, MMS & PLI extensions",
                "type": "flags",
                "bits": {
                "b1": "Proactive UICC: SET FRAMES",
                "b2": "Proactive UICC: GET FRAMES STATUS",
                "b3": "MMS notification download",
                "b4": "Alpha Identifier in REFRESH command supported by terminal",
                "b5": "Geographical Location Reporting",
                "b6": "Proactive UICC: PROVIDE LOCAL INFORMATION (MEID)",
                "b7": "Proactive UICC: PROVIDE LOCAL INFORMATION (NMR(UTRAN/E-UTRAN/Satellite E-UTRAN/NG-RAN/Satellite NG-RAN))",
                "b8": "USSD Data download and application mode"
                }
            },
            {
                "byte": 24,
                "name": "Frames (class i)",
                "type": "flags",
                "bits": {
                "b1": "Maximum number of frames supported (including frames created in existing frames) (bit 1)",
                "b2": "Maximum number of frames supported (including frames created in existing frames) (bit 2)",
                "b3": "Maximum number of frames supported (including frames created in existing frames) (bit 3)",
                "b4": "Maximum number of frames supported (including frames created in existing frames) (bit 4)",
                "b5": "RFU, bit 0",
                "b6": "RFU, bit 0",
                "b7": "RFU, bit 0",
                "b8": "RFU, bit 0"
                }
            },
            {
                "byte": 25,
                "name": "Event driven information extensions",
                "type": "flags",
                "bits": {
                "b1": "Event: Browsing status",
                "b2": "Event: MMS Transfer status",
                "b3": "Event: Frame Information changed",
                "b4": "Event: I-WLAN Access status",
                "b5": "Event: Network Rejection for GERAN/UTRAN",
                "b6": "Event: HCI connectivity event",
                "b7": "Event: Network Rejection for E-UTRAN/Satellite E-UTRAN",
                "b8": "Multiple access technologies supported in Event Access Technology Change and PROVIDE LOCAL INFORMATION"
                }
            },
            {
                "byte": 26,
                "name": "Event driven information extensions",
                "type": "flags",
                "bits": {
                "b1": "Event: CSG Cell Selection",
                "b2": "Event: Contactless state request",
                "b3": "RFU, bit = 0",
                "b4": "RFU, bit = 0",
                "b5": "RFU, bit = 0",
                "b6": "RFU, bit = 0",
                "b7": "RFU, bit = 0",
                "b8": "RFU, bit = 0"
                }
            },
            {
                "byte": 27,
                "name": "Event driven information extensions",
                "type": "flags",
                "bits": {
                "b1": "Event: HCI connectivity event",
                "b2": "RFU, bit = 0",
                "b3": "RFU, bit = 0",
                "b4": "RFU, bit = 0",
                "b5": "RFU, bit = 0",
                "b6": "RFU, bit = 0",
                "b7": "RFU, bit = 0",
                "b8": "RFU, bit = 0"
                }
            },
            {
                "byte": 28,
                "name": "Text attributes",
                "type": "flags",
                "bits": {
                "b1": "Alignment left supported by Terminal",
                "b2": "Alignment centre supported by Terminal",
                "b3": "Alignment right supported by Terminal",
                "b4": "Font size normal supported by Terminal",
                "b5": "Font size large supported by Terminal",
                "b6": "Font size small supported by Terminal",
                "b7": "RFU, bit = 0",
                "b8": "RFU, bit = 0"
                }
            },
            {
                "byte": 29,
                "name": "Text attributes",
                "type": "flags",
                "bits": {
                "b1": "Style normal supported by Terminal",
                "b2": "Style bold supported by Terminal",
                "b3": "Style italic supported by Terminal",
                "b4": "Style underlined supported by Terminal",
                "b5": "Style strikethrough supported by Terminal",
                "b6": "Style text foreground colour supported by Terminal",
                "b7": "Style text background colour supported by Terminal",
                "b8": "RFU, bit = 0"
                }
            },
            {
                "byte": 30,
                "name": "I-WLAN & terminal applications",
                "type": "flags",
                "bits": {
                "b1": "I-WLAN bearer support",
                "b2": "Proactive UICC PROVIDE LOCAL INFORMATION (WSID of the current I-WLAN connection)",
                "b3": "TERMINAL APPLICATIONS",
                "b4": "\"Steering of Roaming\" REFRESH support",
                "b5": "Proactive UICC: ACTIVATE",
                "b6": "Proactive UICC: GEOGRAPHICAL LOCATION REQUEST",
                "b7": "Proactive UICC: PROVIDE LOCAL INFORMATION (Broadcast Network Information)",
                "b8": "\"Steering of Roaming for I-WLAN\" REFRESH support"
                }
            },
            {
                "byte": 31,
                "name": "Contactless, CSG & CAT over modem",
                "type": "flags",
                "bits": {
                "b1": "Proactive UICC: Contactless State Changed",
                "b2": "Support of CSG cell discovery",
                "b3": "Confirmation parameters supported for OPEN CHANNEL in Terminal Server Mode",
                "b4": "Communication Control for IMS",
                "b5": "Support of CAT over the modem interface",
                "b6": "Support for Incoming IMS Data event",
                "b7": "Support for IMS Registration event",
                "b8": "Proactive UICC: Profile Container, Envelope Container, COMMAND CONTAINER and ENCAPSULATED SESSION CONTROL"
                }
            },
            {
                "byte": 32,
                "name": "IMS & H(e)NB / refresh enforcement",
                "type": "flags",
                "bits": {
                "b1": "Support of IMS as a bearer for BIP",
                "b2": "Support of PROVIDE LOCAL INFORMATION, H(e)NB IP address",
                "b3": "Support of PROVIDE LOCAL INFORMATION, H(e)NB surrounding macrocells",
                "b4": "Launch parameters supported for OPEN CHANNEL in Terminal Server Mode",
                "b5": "Direct communication channel supported for OPEN CHANNEL in Terminal Server Mode",
                "b6": "Proactive UICC: Security for Profile Container, Envelope Container, COMMAND CONTAINER and ENCAPSULATED SESSION CONTROL",
                "b7": "CAT service list for eCAT client",
                "b8": "Support of refresh enforcement policy"
                }
            },
            {
                "byte": 33,
                "name": "WLAN/ProSe/RAT information",
                "type": "flags",
                "bits": {
                "b1": "Support of DNS server address request for OPEN CHANNEL related to packet data service bearer",
                "b2": "Support of Network Access Name reuse indication for CLOSE CHANNEL related to packet data service bearer",
                "b3": "Event: Poll Interval Negotiation",
                "b4": "Prose usage information reporting",
                "b5": "Proactive UICC PROVIDE LOCAL INFORMATION (Supported Radio Access Technologies)",
                "b6": "Event: WLAN Access status",
                "b7": "WLAN bearer support",
                "b8": "Proactive UICC: PROVIDE LOCAL INFORMATION (WLAN identifier of the current WLAN connection)"
                }
            },
            {
                "byte": 34,
                "name": "URI, media type & TA extensions",
                "type": "flags",
                "bits": {
                "b1": "URI support for SEND SHORT MESSAGE",
                "b2": "IMS URI supported for SET UP CALL",
                "b3": "Media Type \"Voice\" supported for SET UP CALL and Call Control by USIM",
                "b4": "Media Type \"Video\" supported for SET UP CALL and Call Control by USIM",
                "b5": "Proactive UICC: PROVIDE LOCAL INFORMATION (E-UTRAN Timing Advance Information)",
                "b6": "REFRESH with \"eUICC Profile State Change\" mode",
                "b7": "Extended Rejection Cause Code in Event: Network Rejection for E-UTRAN",
                "b8": "Deprecated, bit = 0"
                }
            },
            {
                "byte": 35,
                "name": "Get Input (VT), data-connection events & LSI",
                "type": "flags",
                "bits": {
                "b1": "Proactive UICC: GET INPUT (Variable Time out)",
                "b2": "Data Connection Status Change Event support - PDP Connection",
                "b3": "Data Connection Status Change Event support - PDN Connection",
                "b4": "REFRESH with \"Application Update\" mode",
                "b5": "Proactive UICC: LSI COMMAND with \"Proactive Session Request\"",
                "b6": "Proactive UICC: LSI COMMAND with \"UICC Platform Reset\"",
                "b7": "RFU, bit = 0",
                "b8": "RFU, bit = 0"
                }
            },
            {
                "byte": 36,
                "name": "NG-RAN / Non-IP / Slice information",
                "type": "flags",
                "bits": {
                "b1": "Data Connection Status Change Event support - PDU Connection",
                "b2": "Event: Network Rejection for NG-RAN",
                "b3": "Non-IP Data Delivery support",
                "b4": "Support of PROVIDE LOCAL INFORMATION, Slice(s) information",
                "b5": "REFRESH \"Steering of Roaming\" SOR-CMCI parameter support",
                "b6": "Event: Network Rejection for Satellite NG-RAN",
                "b7": "Support of CAG feature",
                "b8": "Event: Slices Status Change"
                }
            },
            {
                "byte": 37,
                "name": "Slice information (extended) & future use",
                "type": "flags",
                "bits": {
                "b1": "Support of PROVIDE LOCAL INFORMATION, Rejected Slice(s) Information",
                "b2": "Support of Extended information for PLI(Location Information)/Location Status events",
                "b3": "Support of chaining of PLI/Envelope commands",
                "b4": "5G ProSe usage information reporting",
                "b5": "Reserved by 3GPP (for future usage)",
                "b6": "Reserved by 3GPP (for future usage)",
                "b7": "Reserved by 3GPP (for future usage)",
                "b8": "Reserved by 3GPP (for future usage)"
                }
            },
            {
                "byte": 38,
                "name": "Reserved",
                "type": "flags",
                "bits": {
                "b1": "Reserved by 3GPP (for future usage)",
                "b2": "Reserved by 3GPP (for future usage)",
                "b3": "Reserved by 3GPP (for future usage)",
                "b4": "Reserved by 3GPP (for future usage)",
                "b5": "Reserved by 3GPP (for future usage)",
                "b6": "Reserved by 3GPP (for future usage)",
                "b7": "Reserved by 3GPP (for future usage)",
                "b8": "Reserved by 3GPP (for future usage)"
                }
            },
            {
                "byte": 39,
                "name": "NG-RAN / Satellite TA information",
                "type": "flags",
                "bits": {
                "b1": "Proactive UICC: PROVIDE LOCAL INFORMATION (NG-RAN/Satellite NG-RAN Timing Advance Information)",
                "b2": "Reserved by 3GPP (for future usage)",
                "b3": "Reserved by 3GPP (for future usage)",
                "b4": "Reserved by 3GPP (for future usage)",
                "b5": "Reserved by 3GPP (for future usage)",
                "b6": "Reserved by 3GPP (for future usage)",
                "b7": "Reserved by 3GPP (for future usage)",
                "b8": "Reserved by 3GPP (for future usage)"
                }
            }
            ]
