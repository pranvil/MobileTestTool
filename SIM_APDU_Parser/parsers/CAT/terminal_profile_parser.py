# parsers/CAT/terminal_profile_parser.py
from SIM_APDU_Parser.core.models import ParseNode

class TerminalProfileParser:
    """TERMINAL PROFILE 解析器"""
    
    def __init__(self):
        self.profile_rules = self._get_profile_rules()
    
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
        
        byte_node = ParseNode(name=f"{byte_name} ({byte_hex})")
        
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
        capabilities = []
        
        for bit_pos in range(1, 9):  # b1 到 b8
            bit_key = f"b{bit_pos}"
            if bit_key in bits:
                bit_mask = 1 << (bit_pos - 1)  # b1=0x01, b2=0x02, b3=0x04, ...
                if byte_value & bit_mask:
                    capabilities.append(bits[bit_key])
        
        if capabilities:
            # 每个能力单独显示为一行
            for capability in capabilities:
                byte_node.children.append(ParseNode(name="Supported", value=capability))
        else:
            byte_node.children.append(ParseNode(name="Supported", value="None"))
    
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
        
        # 解析flags部分
        flags_capabilities = []
        for bit_pos in range(1, 9):
            bit_key = f"b{bit_pos}"
            if bit_key in bits:
                bit_mask = 1 << (bit_pos - 1)
                if byte_value & bit_mask:
                    flags_capabilities.append(bits[bit_key])
        
        if flags_capabilities:
            # 每个能力单独显示为一行
            for capability in flags_capabilities:
                byte_node.children.append(ParseNode(name="Flags", value=capability))
        
        # 解析value部分
        if value_rules:
            byte_node.children.append(ParseNode(name="Value", value=str(byte_value)))
            byte_node.children.append(ParseNode(name="Description", value=value_rules))
    
    def _parse_flags_value(self, byte_node: ParseNode, rule: dict, byte_value: int):
        """解析 flags+value 类型字节"""
        bits = rule.get("bits", {})
        value_rules = rule.get("value_rules", "")
        
        # 解析flags部分（b1-b5 是bearer类型）
        flags_capabilities = []
        for bit_pos in range(1, 6):  # b1-b5 是bearer类型
            bit_key = f"b{bit_pos}"
            if bit_key in bits:
                bit_mask = 1 << (bit_pos - 1)
                if byte_value & bit_mask:
                    flags_capabilities.append(bits[bit_key])
        
        if flags_capabilities:
            # 每个能力单独显示为一行
            for capability in flags_capabilities:
                byte_node.children.append(ParseNode(name="Supported Bearer", value=capability))
        
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
                    "b2": "Reserved (3GPP: SMS-PP data download)",
                    "b3": "Reserved (3GPP: Cell Broadcast data download)",
                    "b4": "Menu selection",
                    "b5": "Reserved (3GPP: SMS-PP data download)",
                    "b6": "Timer expiration",
                    "b7": "Reserved (3GPP/3GPP2: USSD string data object support in Call Control by USIM)",
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
                    "b4": "Reserved (3GPP: MO short message control support)",
                    "b5": "Call Control by NAA",
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
                    "b1": "DISPLAY TEXT",
                    "b2": "GET INKEY",
                    "b3": "GET INPUT",
                    "b4": "MORE TIME",
                    "b5": "PLAY TONE",
                    "b6": "POLL INTERVAL",
                    "b7": "POLLING OFF",
                    "b8": "REFRESH"
                }
            },
            {
                "byte": 4,
                "name": "Proactive UICC",
                "type": "flags",
                "bits": {
                    "b1": "SELECT ITEM",
                    "b2": "Reserved (3GPP: SEND SHORT MESSAGE with 3GPP-SMS-TPDU)",
                    "b3": "Reserved (3GPP: SEND SS)",
                    "b4": "Reserved (3GPP & 3GPP2: SEND USSD)",
                    "b5": "SET UP CALL",
                    "b6": "SET UP MENU",
                    "b7": "PROVIDE LOCAL INFORMATION (MCC, MNC, LAC, Cell ID & IMEI)",
                    "b8": "PROVIDE LOCAL INFORMATION (NMR)"
                }
            },
            {
                "byte": 5,
                "name": "Event driven information",
                "type": "flags",
                "bits": {
                    "b1": "SET UP EVENT LIST",
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
                    "b2": "Event: Browser Termination (class \"ac\" supported)",
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
                "name": "Multiple card proactive commands (class \"a\")",
                "type": "flags",
                "bits": {
                    "b1": "POWER ON CARD",
                    "b2": "POWER OFF CARD",
                    "b3": "PERFORM CARD APDU",
                    "b4": "GET READER STATUS (Card reader status)",
                    "b5": "GET READER STATUS (Card reader identifier)",
                    "b6": "RFU (bit = 0)",
                    "b7": "RFU (bit = 0)",
                    "b8": "RFU (bit = 0)"
                }
            },
            {
                "byte": 8,
                "name": "Proactive UICC",
                "type": "flags",
                "bits": {
                    "b1": "TIMER MANAGEMENT (start/stop)",
                    "b2": "TIMER MANAGEMENT (get current value)",
                    "b3": "PROVIDE LOCAL INFORMATION (date, time, time zone)",
                    "b4": "GET INKEY",
                    "b5": "SET UP IDLE MODE TEXT",
                    "b6": "RUN AT COMMAND (class \"b\" supported)",
                    "b7": "SET UP CALL",
                    "b8": "Call Control by NAA"
                }
            },
            {
                "byte": 9,
                "name": "Proactive UICC (cont.)",
                "type": "flags",
                "bits": {
                    "b1": "DISPLAY TEXT",
                    "b2": "SEND DTMF command",
                    "b3": "PROVIDE LOCAL INFORMATION (NMR)",
                    "b4": "PROVIDE LOCAL INFORMATION (language)",
                    "b5": "Reserved (3GPP: PROVIDE LOCAL INFORMATION, Timing Advance)",
                    "b6": "LANGUAGE NOTIFICATION",
                    "b7": "LAUNCH BROWSER (class \"ab\" supported)",
                    "b8": "PROVIDE LOCAL INFORMATION (Access Technology)"
                }
            },
            {
                "byte": 10,
                "name": "Soft keys support (class \"d\")",
                "type": "flags",
                "bits": {
                    "b1": "Soft keys support for SELECT ITEM",
                    "b2": "Soft keys support for SET UP MENU",
                    "b3": "RFU (bit = 0)",
                    "b4": "RFU (bit = 0)",
                    "b5": "RFU (bit = 0)",
                    "b6": "RFU (bit = 0)",
                    "b7": "RFU (bit = 0)",
                    "b8": "RFU (bit = 0)"
                }
            },
            {
                "byte": 11,
                "name": "Soft keys information",
                "type": "value",
                "value_rules": "Unsigned 8-bit value: maximum number of soft keys available. 0xFF reserved for future use."
            },
            {
                "byte": 12,
                "name": "Bearer Independent Protocol proactive commands (class \"e\")",
                "type": "flags",
                "bits": {
                    "b1": "OPEN CHANNEL",
                    "b2": "CLOSE CHANNEL",
                    "b3": "RECEIVE DATA",
                    "b4": "SEND DATA",
                    "b5": "GET CHANNEL STATUS",
                    "b6": "SERVICE SEARCH",
                    "b7": "GET SERVICE INFORMATION",
                    "b8": "DECLARE SERVICE"
                }
            },
            {
                "byte": 13,
                "name": "Bearer Independent Protocol supported bearers (class \"e\")",
                "type": "flags+value",
                "bits": {
                    "b1": "CSD",
                    "b2": "GPRS",
                    "b3": "Bluetooth",
                    "b4": "IrDA",
                    "b5": "RS232"
                },
                "value_rules": "Lower 3 bits (b3..b1) encode 'Number of channels supported by terminal' (0..7)."
            },
            {
                "byte": 14,
                "name": "Screen height",
                "type": "mixed",
                "bits": {
                    "b1": "Number of characters supported down the display (MSB)",
                    "b2": "Number of characters supported down the display",
                    "b3": "Number of characters supported down the display",
                    "b4": "Number of characters supported down the display (LSB)",
                    "b5": "No display capability (class \"ND\")",
                    "b6": "No keypad available (class \"NK\")",
                    "b7": "Screen Sizing Parameters supported (see 5.3)",
                    "b8": "RFU (bit = 0)"
                },
                "value_rules": "b8..b5 form a 4-bit unsigned integer for the vertical character count; others are flags."
            },
            {
                "byte": 15,
                "name": "Screen width",
                "type": "mixed",
                "bits": {
                    "b1": "Number of characters supported across the display (MSB)",
                    "b2": "Number of characters supported across the display",
                    "b3": "Number of characters supported across the display",
                    "b4": "Number of characters supported across the display (LSB)",
                    "b5": "Variable size fonts support",
                    "b6": "RFU (bit = 0)",
                    "b7": "RFU (bit = 0)",
                    "b8": "RFU (bit = 0)"
                },
                "value_rules": "b8..b5 form a 4-bit unsigned integer for the horizontal character count; others are flags."
            },
            {
                "byte": 16,
                "name": "Screen effects",
                "type": "flags",
                "bits": {
                    "b1": "Display can be resized (see 5.3.3)",
                    "b2": "Text Wrapping (see 5.3.4)",
                    "b3": "Text Scrolling (see 5.3.5)",
                    "b4": "Text Attributes (see 5.3.7)",
                    "b5": "RFU (bit = 0)",
                    "b6": "Width reduction when in a menu (see 5.3.6)",
                    "b7": "RFU (bit = 0)",
                    "b8": "RFU (bit = 0)"
                }
            },
            {
                "byte": 17,
                "name": "BIP supported transport interface/bearers (class \"e\")",
                "type": "flags",
                "bits": {
                    "b1": "TCP, client mode, remote connection",
                    "b2": "UDP, client mode, remote connection",
                    "b3": "TCP, server mode",
                    "b4": "TCP, client mode, local connection (class \"x\")",
                    "b5": "UDP, client mode, local connection (class \"x\")",
                    "b6": "Direct communication channel (class \"x\")",
                    "b7": "Reserved by 3GPP (E-UTRAN)",
                    "b8": "Reserved by 3GPP (HSDPA)"
                }
            },
            {
                "byte": 18,
                "name": "Proactive UICC (misc)",
                "type": "flags",
                "bits": {
                    "b1": "DISPLAY TEXT (Variable Time out)",
                    "b2": "GET INKEY (help while waiting for immediate response / variable timeout)",
                    "b3": "USB bearer (class \"e\")",
                    "b4": "GET INKEY (Variable Timeout)",
                    "b5": "PROVIDE LOCAL INFORMATION (ESN)",
                    "b6": "Reserved by 3GPP (Call control on GPRS)",
                    "b7": "PROVIDE LOCAL INFORMATION (IMEISV)",
                    "b8": "PROVIDE LOCAL INFORMATION (Search Mode change)"
                }
            },
            {
                "byte": 19,
                "name": "Reserved for TIA/EIA-136-270 facilities",
                "type": "flags",
                "bits": {
                    "b1": "Reserved by TIA/EIA-136-270 (Protocol Version support)",
                    "b2": "RFU (bit = 0)",
                    "b3": "RFU (bit = 0)",
                    "b4": "RFU (bit = 0)",
                    "b5": "RFU (bit = 0)",
                    "b6": "RFU (bit = 0)",
                    "b7": "RFU (bit = 0)",
                    "b8": "RFU (bit = 0)"
                }
            },
            {
                "byte": 20,
                "name": "Reserved for 3GPP2 C.S0035-B CCAT",
                "type": "flags",
                "bits": {
                    "b1": "Reserved by CCAT",
                    "b2": "RFU (bit = 0)",
                    "b3": "RFU (bit = 0)",
                    "b4": "RFU (bit = 0)",
                    "b5": "RFU (bit = 0)",
                    "b6": "RFU (bit = 0)",
                    "b7": "RFU (bit = 0)",
                    "b8": "RFU (bit = 0)"
                }
            },
            {
                "byte": 21,
                "name": "Extended Launch Browser Capability (class \"ac\")",
                "type": "flags",
                "bits": {
                    "b1": "WML",
                    "b2": "XHTML",
                    "b3": "HTML",
                    "b4": "CHTML",
                    "b5": "RFU (bit = 0)",
                    "b6": "RFU (bit = 0)",
                    "b7": "RFU (bit = 0)",
                    "b8": "RFU (bit = 0)"
                }
            },
            {
                "byte": 22,
                "name": "Misc/Multimedia and GBA",
                "type": "flags",
                "bits": {
                    "b1": "Reserved (Support of UTRAN PS with extended parameters)",
                    "b2": "PROVIDE LOCAL INFORMATION (battery state) (class \"g\")",
                    "b3": "PLAY TONE (Melody tones and Themed tones supported)",
                    "b4": "Multi-media Calls in SET UP CALL (class \"h\")",
                    "b5": "Reserved (Toolkit-initiated GBA)",
                    "b6": "RETRIEVE MULTIMEDIA MESSAGE (class \"j\")",
                    "b7": "SUBMIT MULTIMEDIA MESSAGE (class \"j\")",
                    "b8": "DISPLAY MULTIMEDIA MESSAGE (class \"j\")"
                }
            },
            {
                "byte": 23,
                "name": "Frames, MMS, Alpha Id, Geographic Info, NMR/ESN/IMEI",
                "type": "flags",
                "bits": {
                    "b1": "SET FRAMES (class \"i\")",
                    "b2": "GET FRAMES STATUS (class \"i\")",
                    "b3": "MMS notification download (class \"j\")",
                    "b4": "Alpha Identifier in REFRESH supported by terminal",
                    "b5": "Reserved (Geographical Location Reporting)",
                    "b6": "PROVIDE LOCAL INFORMATION (MEID)",
                    "b7": "Reserved (PROVIDE LOCAL INFORMATION (NMR / UTRAN/E-UTRAN))",
                    "b8": "Reserved (USSD Data download and application mode)"
                }
            },
            {
                "byte": 24,
                "name": "Frames (class \"i\")",
                "type": "value",
                "value_rules": "Unsigned 8-bit value: Maximum number of frames supported (including frames created in existing frames). RFU if bit = 0."
            },
            {
                "byte": 25,
                "name": "Event driven information extensions (more)",
                "type": "flags",
                "bits": {
                    "b1": "Event: Browsing status (class \"ac\")",
                    "b2": "Event: MMS Transfer status (class \"j\")",
                    "b3": "Event: Frame Information changed (class \"i\")",
                    "b4": "Reserved (Event: I-WLAN Access status)",
                    "b5": "Reserved (Event: Event Network Rejection)",
                    "b6": "Event: HCI connectivity event (class \"m\")",
                    "b7": "Reserved (E-UTRAN support in Event Network Rejection)",
                    "b8": "Multiple access technologies supported in Event Access Technology Change and PROVIDE LOCAL INFORMATION"
                }
            },
            {
                "byte": 26,
                "name": "Event driven information extensions (contactless/CSG)",
                "type": "flags",
                "bits": {
                    "b1": "Reserved (3GPP: CSG Cell Selection)",
                    "b2": "Event: Contactless state request (class \"m\")",
                    "b3": "RFU (bit = 0)",
                    "b4": "RFU (bit = 0)",
                    "b5": "RFU (bit = 0)",
                    "b6": "RFU (bit = 0)",
                    "b7": "RFU (bit = 0)",
                    "b8": "RFU (bit = 0)"
                }
            },
            {
                "byte": 27,
                "name": "Event driven information extensions (future)",
                "type": "flags",
                "bits": {
                    "b1": "RFU (bit = 0)",
                    "b2": "RFU (bit = 0)",
                    "b3": "RFU (bit = 0)",
                    "b4": "RFU (bit = 0)",
                    "b5": "RFU (bit = 0)",
                    "b6": "RFU (bit = 0)",
                    "b7": "RFU (bit = 0)",
                    "b8": "RFU (bit = 0)"
                }
            },
            {
                "byte": 28,
                "name": "Text attributes (alignment & size)",
                "type": "flags",
                "bits": {
                    "b1": "Alignment left supported by Terminal",
                    "b2": "Alignment centre supported by Terminal",
                    "b3": "Alignment right supported by Terminal",
                    "b4": "Font size normal supported by Terminal",
                    "b5": "Font size large supported by Terminal",
                    "b6": "Font size small supported by Terminal",
                    "b7": "RFU (bit = 0)",
                    "b8": "RFU (bit = 0)"
                }
            },
            {
                "byte": 29,
                "name": "Text attributes (style & color)",
                "type": "flags",
                "bits": {
                    "b1": "Style normal supported by Terminal",
                    "b2": "Style bold supported by Terminal",
                    "b3": "Style italic supported by Terminal",
                    "b4": "Style underlined supported by Terminal",
                    "b5": "Style strikethrough supported by Terminal",
                    "b6": "Style text foreground colour supported by Terminal",
                    "b7": "Style text background colour supported by Terminal",
                    "b8": "RFU (bit = 0)"
                }
            }
        ]
