# parsers/CAT/uicc_to_terminal.py
"""
UICC发给手机的CAT命令解析器
主要是D0开头的proactive命令
"""
from SIM_APDU_Parser.core.models import ParseNode
from SIM_APDU_Parser.parsers.CAT.common import parse_comp_tlvs_to_nodes


class UiccToTerminalParser:
    """UICC发给手机的CAT命令解析器"""
    
    def parse_command(self, cla: int, ins: int, payload_hex: str) -> ParseNode:
        """
        解析UICC发给手机的CAT命令
        
        Args:
            cla: CLA字节
            ins: INS字节
            payload_hex: 去掉CLA/INS/P1/P2/LC后的数据部分，或者91开头的完整数据
        """
        if cla == 0xD0:
            # Proactive Command (D0)
            return self._parse_proactive_command(payload_hex)
        elif cla == 0x91 and len(payload_hex) == 4:
            # Proactive Command Pending (91) - 2字节数据
            return self._parse_proactive_command_pending(payload_hex)
        else:
            # 未知命令
            cla_str = f"{cla:02X}" if cla is not None else "??"
            ins_str = f"{ins:02X}" if ins is not None else "??"
            return ParseNode(name=f"Unknown UICC->Terminal Command (0x{cla_str} {ins_str})", value=payload_hex)
    
    def _parse_proactive_command(self, payload_hex: str) -> ParseNode:
        """解析 Proactive Command (D0)"""
        comp_root, first = parse_comp_tlvs_to_nodes(payload_hex)
        title = "CAT: Proactive Command (D0)" + (f" - {first}" if first else "")
        root = ParseNode(name=title)
        root.children.extend(comp_root.children)
        return root
    
    def _parse_proactive_command_pending(self, payload_hex: str) -> ParseNode:
        """解析 Proactive Command Pending (91)"""
        if len(payload_hex) != 4:
            return ParseNode(name="CAT: Proactive Command Pending (91) - Invalid length", value=payload_hex)
        
        # 第一个字节是91，第二个字节是长度
        status_byte = payload_hex[:2]
        length_byte = payload_hex[2:4]
        length_value = int(length_byte, 16)
        
        title = "CAT: Proactive Command Pending (91)"
        root = ParseNode(name=title)
        
        # 添加详细信息
        root.children.append(ParseNode(name="Status", value="Proactive Command Pending"))
        root.children.append(ParseNode(name="Length", value=f"{length_value} bytes"))
        root.children.append(ParseNode(name="Raw Data", value=payload_hex))
        
        return root
