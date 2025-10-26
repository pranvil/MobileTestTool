# parsers/CAT/terminal_to_uicc.py
"""
手机发给UICC的CAT命令解析器
包括: 8010(TERMINAL PROFILE), 8014(TERMINAL RESPONSE), 80C2(ENVELOPE), 8012(FETCH), 80AA(TERMINAL CAPABILITY)
"""
from SIM_APDU_Parser.core.models import ParseNode
from SIM_APDU_Parser.parsers.CAT.common import parse_comp_tlvs_to_nodes
from SIM_APDU_Parser.parsers.CAT.terminal_profile_parser import TerminalProfileParser
from SIM_APDU_Parser.parsers.CAT.terminal_capability_parser import TerminalCapabilityParser


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
        """解析 ENVELOPE (80C2) - 直接显示数据部分"""
        title = "CAT: ENVELOPE"
        root = ParseNode(name=title)
        root.children.append(ParseNode(name="Data", value=payload_hex))
        return root
    
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
