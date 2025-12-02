# parsers/CAT/terminal_to_uicc.py
"""
手机发给UICC的CAT命令解析器
包括: 8010(TERMINAL PROFILE), 8014(TERMINAL RESPONSE), 80C2(ENVELOPE), 8012(FETCH), 80AA(TERMINAL CAPABILITY)
"""
from SIM_APDU_Parser.core.models import ParseNode
from SIM_APDU_Parser.parsers.CAT.common import parse_comp_tlvs_to_nodes
from SIM_APDU_Parser.parsers.CAT.terminal_profile_parser import TerminalProfileParser
from SIM_APDU_Parser.parsers.CAT.terminal_capability_parser import TerminalCapabilityParser

# ENVELOPE 命令类型映射
ENVELOPE_TYPE_MAP = {
    'D1': 'SMS-PP Download',
    'D2': 'Cell Broadcast Download',
    'D3': 'Menu Selection',
    'D4': 'Call Control',
    'D5': 'MO Short Message control',
    'D6': 'Event Download',
    'D7': 'Timer Expiration',
    'D8': 'Reserved for intra-UICC communication',
    'D9': 'USSD Download',
    'DA': 'MMS Transfer status',
    'DB': 'MMS notification download',
    'DC': 'Terminal Applications',
    'DD': 'Geographical Location Reporting',
    'DE': 'Envelope Container',
    'DF': 'ProSe Report',
    'E0': '5G ProSe Report',
    'E1': 'Reserved for 3GPP',
    'E2': 'Reserved for 3GPP',
    'E3': 'Reserved for 3GPP',
    'E4': 'Reserved for GSMA',
}


class TerminalToUiccParser:
    """手机发给UICC的CAT命令解析器"""
    
    def parse_command(self, cla: int, ins: int, payload_hex: str) -> ParseNode:
        """
        解析手机发给UICC的CAT命令
        
        Args:
            cla: CLA字节
            ins: INS字节  
            payload_hex: 去掉CLA/INS/P1/P2/LC后的数据部分
        """
        if cla == 0x80 and ins == 0x10:
            # TERMINAL PROFILE (8010)
            return self._parse_terminal_profile(payload_hex)
        elif cla == 0x80 and ins == 0x14:
            # TERMINAL RESPONSE (8014)
            return self._parse_terminal_response(payload_hex)
        elif cla == 0x80 and ins == 0xC2:
            # ENVELOPE (80C2)
            return self._parse_envelope(payload_hex)
        elif cla == 0x80 and ins == 0x12:
            # FETCH (8012)
            return self._parse_fetch(payload_hex)
        elif cla == 0x80 and ins == 0xAA:
            # TERMINAL CAPABILITY (80AA)
            return self._parse_terminal_capability(payload_hex)
        else:
            # 未知命令
            return ParseNode(name=f"Unknown Terminal->UICC Command (0x{cla:02X} {ins:02X})", value=payload_hex)
    
    def _parse_terminal_profile(self, payload_hex: str) -> ParseNode:
        """解析 TERMINAL PROFILE (8010)"""
        parser = TerminalProfileParser()
        profile_node = parser.parse_profile_data(payload_hex)
        
        # 设置标题
        title = "CAT: TERMINAL PROFILE"
        root = ParseNode(name=title)
        root.children.extend(profile_node.children)
        
        return root
    
    def _parse_terminal_response(self, payload_hex: str) -> ParseNode:
        """解析 TERMINAL RESPONSE (8014)"""
        comp_root, first = parse_comp_tlvs_to_nodes(payload_hex)
        title = "CAT: TERMINAL RESPONSE" + (f" - {first}" if first else "")
        root = ParseNode(name=title)
        root.children.extend(comp_root.children)
        return root
    
    def _parse_envelope(self, payload_hex: str) -> ParseNode:
        """解析 ENVELOPE (80C2)"""
        if not payload_hex or len(payload_hex) < 2:
            root = ParseNode(name="[TERMINAL=>UICC] CAT: ENVELOPE")
            root.children.append(ParseNode(name="Data", value=payload_hex))
            return root
        
        # 解析第一个 TLV tag 来识别 ENVELOPE 类型
        envelope_tag = payload_hex[:2].upper()
        envelope_type = ENVELOPE_TYPE_MAP.get(envelope_tag, f'Unknown ({envelope_tag})')
        
        # 设置标题
        title = f"[TERMINAL=>UICC] CAT: ENVELOPE - {envelope_type}"
        root = ParseNode(name=title)
        
        # 根据类型调用对应的解析函数
        if envelope_tag == 'D1':
            self._parse_sms_pp_download(root, payload_hex)
        elif envelope_tag == 'D2':
            self._parse_cell_broadcast_download(root, payload_hex)
        elif envelope_tag == 'D3':
            self._parse_menu_selection(root, payload_hex)
        elif envelope_tag == 'D4':
            self._parse_call_control(root, payload_hex)
        elif envelope_tag == 'D5':
            self._parse_mo_short_message_control(root, payload_hex)
        elif envelope_tag == 'D6':
            self._parse_event_download(root, payload_hex)
        elif envelope_tag == 'D7':
            self._parse_timer_expiration(root, payload_hex)
        elif envelope_tag == 'D8':
            self._parse_reserved_intra_uicc(root, payload_hex)
        elif envelope_tag == 'D9':
            self._parse_ussd_download(root, payload_hex)
        elif envelope_tag == 'DA':
            self._parse_mms_transfer_status(root, payload_hex)
        elif envelope_tag == 'DB':
            self._parse_mms_notification_download(root, payload_hex)
        elif envelope_tag == 'DC':
            self._parse_terminal_applications(root, payload_hex)
        elif envelope_tag == 'DD':
            self._parse_geographical_location_reporting(root, payload_hex)
        elif envelope_tag == 'DE':
            self._parse_envelope_container(root, payload_hex)
        elif envelope_tag == 'DF':
            self._parse_prose_report(root, payload_hex)
        elif envelope_tag == 'E0':
            self._parse_5g_prose_report(root, payload_hex)
        elif envelope_tag in ('E1', 'E2', 'E3', 'E4'):
            self._parse_reserved(root, payload_hex, envelope_tag)
        else:
            # 未知类型，显示原始数据
            root.children.append(ParseNode(name="Data", value=payload_hex))
        
        return root
    
    # ========== ENVELOPE 类型解析函数（占位符） ==========
    
    def _parse_sms_pp_download(self, root: ParseNode, payload_hex: str):
        """解析 SMS-PP Download (D1) - 占位符"""
        root.children.append(ParseNode(name="Data", value=payload_hex))
    
    def _parse_cell_broadcast_download(self, root: ParseNode, payload_hex: str):
        """解析 Cell Broadcast Download (D2) - 占位符"""
        root.children.append(ParseNode(name="Data", value=payload_hex))
    
    def _parse_menu_selection(self, root: ParseNode, payload_hex: str):
        """解析 Menu Selection (D3) - 占位符"""
        root.children.append(ParseNode(name="Data", value=payload_hex))
    
    def _parse_call_control(self, root: ParseNode, payload_hex: str):
        """解析 Call Control (D4) - 占位符"""
        root.children.append(ParseNode(name="Data", value=payload_hex))
    
    def _parse_mo_short_message_control(self, root: ParseNode, payload_hex: str):
        """解析 MO Short Message control (D5) - 占位符"""
        root.children.append(ParseNode(name="Data", value=payload_hex))
    
    def _parse_event_download(self, root: ParseNode, payload_hex: str):
        """解析 Event Download (D6) - 占位符"""
        root.children.append(ParseNode(name="Data", value=payload_hex))
    
    def _parse_timer_expiration(self, root: ParseNode, payload_hex: str):
        """解析 Timer Expiration (D7) - 占位符"""
        root.children.append(ParseNode(name="Data", value=payload_hex))
    
    def _parse_reserved_intra_uicc(self, root: ParseNode, payload_hex: str):
        """解析 Reserved for intra-UICC communication (D8) - 占位符"""
        root.children.append(ParseNode(name="Data", value=payload_hex))
    
    def _parse_ussd_download(self, root: ParseNode, payload_hex: str):
        """解析 USSD Download (D9) - 占位符"""
        root.children.append(ParseNode(name="Data", value=payload_hex))
    
    def _parse_mms_transfer_status(self, root: ParseNode, payload_hex: str):
        """解析 MMS Transfer status (DA) - 占位符"""
        root.children.append(ParseNode(name="Data", value=payload_hex))
    
    def _parse_mms_notification_download(self, root: ParseNode, payload_hex: str):
        """解析 MMS notification download (DB) - 占位符"""
        root.children.append(ParseNode(name="Data", value=payload_hex))
    
    def _parse_terminal_applications(self, root: ParseNode, payload_hex: str):
        """解析 Terminal Applications (DC) - 占位符"""
        root.children.append(ParseNode(name="Data", value=payload_hex))
    
    def _parse_geographical_location_reporting(self, root: ParseNode, payload_hex: str):
        """解析 Geographical Location Reporting (DD) - 占位符"""
        root.children.append(ParseNode(name="Data", value=payload_hex))
    
    def _parse_envelope_container(self, root: ParseNode, payload_hex: str):
        """解析 Envelope Container (DE) - 占位符"""
        root.children.append(ParseNode(name="Data", value=payload_hex))
    
    def _parse_prose_report(self, root: ParseNode, payload_hex: str):
        """解析 ProSe Report (DF) - 占位符"""
        root.children.append(ParseNode(name="Data", value=payload_hex))
    
    def _parse_5g_prose_report(self, root: ParseNode, payload_hex: str):
        """解析 5G ProSe Report (E0) - 占位符"""
        root.children.append(ParseNode(name="Data", value=payload_hex))
    
    def _parse_reserved(self, root: ParseNode, payload_hex: str, tag: str):
        """解析 Reserved (E1-E4) - 占位符"""
        root.children.append(ParseNode(name="Data", value=payload_hex))
    
    def _parse_fetch(self, payload_hex: str) -> ParseNode:
        """解析 FETCH (8012) - 直接显示数据部分"""
        title = "CAT: FETCH"
        root = ParseNode(name=title)
        root.children.append(ParseNode(name="Data", value=payload_hex))
        return root
    
    def _parse_terminal_capability(self, payload_hex: str) -> ParseNode:
        """解析 TERMINAL CAPABILITY (80AA)"""
        parser = TerminalCapabilityParser()
        capability_node = parser.parse_capability_data(payload_hex)
        
        # 设置标题
        title = "TERMINAL CAPABILITY"
        root = ParseNode(name=title)
        root.children.extend(capability_node.children)
        
        return root
