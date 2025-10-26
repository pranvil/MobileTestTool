
from typing import Optional
from SIM_APDU_Parser.core.models import Message, ParseResult, MsgType, ParseNode, Apdu
from SIM_APDU_Parser.core.utils import parse_apdu_header
from SIM_APDU_Parser.core.tlv import parse_ber_tlvs
from SIM_APDU_Parser.core.registry import resolve

# 确保解析器被注册
from SIM_APDU_Parser.parsers.esim import *  # ensure registration
from SIM_APDU_Parser.parsers.CAT import *  # ensure registration

class IParser:
    def parse(self, msg: Message) -> ParseResult:
        raise NotImplementedError

class CatParser(IParser):
    def parse(self, msg: Message) -> ParseResult:
        hdr = parse_apdu_header(msg.raw)
        
        # 确定方向
        if msg.raw.startswith("80"):
            direction = "TERMINAL=>UICC"
            # 手机发给UICC的命令
            payload = msg.raw[10:] if len(msg.raw) > 10 else ""  # Skip APDU header
            from SIM_APDU_Parser.parsers.CAT.terminal_to_uicc import TerminalToUiccParser
            parser = TerminalToUiccParser()
            root = parser.parse_command(hdr.cla, hdr.ins, payload)
        elif msg.raw.startswith("D0") or (msg.raw.startswith("91") and len(msg.raw) == 4):
            direction = "UICC=>TERMINAL"
            # UICC发给手机的命令
            if msg.raw.startswith("91") and len(msg.raw) == 4:
                # 91开头的2字节数据，特殊处理
                from SIM_APDU_Parser.parsers.CAT.uicc_to_terminal import UiccToTerminalParser
                parser = UiccToTerminalParser()
                root = parser.parse_command(0x91, None, msg.raw)
            else:
                # D0 命令格式: D0 + 长度 + TLV数据
                if len(msg.raw) >= 4:
                    length_byte = int(msg.raw[2:4], 16)
                    payload = msg.raw[4:4+2*length_byte] if len(msg.raw) >= 4+2*length_byte else msg.raw[4:]
                else:
                    payload = ""
                from SIM_APDU_Parser.parsers.CAT.uicc_to_terminal import UiccToTerminalParser
                parser = UiccToTerminalParser()
                root = parser.parse_command(hdr.cla, hdr.ins, payload)
        else:
            # 未知命令
            direction = "UNKNOWN"
            root = ParseNode(name=f"Unknown CAT Command", value=msg.raw)
        
        # 使用解析结果的标题，确保包含方向信息
        detailed_title = root.name
        if not detailed_title.startswith('['):
            # 添加方向前缀
            direction_prefix = f"[{direction}] "
            detailed_title = direction_prefix + detailed_title
        
        return ParseResult(msg_type=MsgType.CAT, message=msg, apdu=hdr, root=root,
                           title=detailed_title, direction_hint=direction)

class EsimParser(IParser):
    def parse(self, msg: Message) -> ParseResult:
        hdr = parse_apdu_header(msg.raw)
        direction = "ESIM=>LPA" if msg.raw.startswith("BF") else "LPA=>ESIM"
        # Compute body & top-level tag
        body = msg.raw
        if hdr and hdr.ins == 0xE2 and len(body) >= 10:
            body = body[10:]  # strip 5-byte header
        tlvs = parse_ber_tlvs(body)
        root = ParseNode(name="eSIM")
        if tlvs:
            top = tlvs[0]
            handler_cls = resolve(MsgType.ESIM, top.tag)
            if handler_cls:
                handler = handler_cls()
                root = handler.build(top.value_hex, direction)
            else:
                # default: list TLVs
                root = ParseNode(name=f"Unknown eSIM container {top.tag}")
                for t in tlvs:
                    root.children.append(ParseNode(name=f"TLV {t.tag}", value=f"len={t.length}", hint=t.value_hex[:120]))
        else:
            root = ParseNode(name="eSIM (empty)")
        return ParseResult(msg_type=MsgType.ESIM, message=msg, apdu=hdr, root=root,
                           title="eSIM APDU", direction_hint=direction)


class NormalSimParser(IParser):
    def parse(self, msg: Message) -> ParseResult:
        from SIM_APDU_Parser.parsers.sim_apdu_parser import SimApduParser
        
        hdr = parse_apdu_header(msg.raw)
        parser = SimApduParser()
        root = parser.parse(msg)
        
        # 确定方向提示
        is_ue_to_sim = parser._is_ue_to_sim(msg.raw, hdr)
        direction_hint = "UE=>SIM" if is_ue_to_sim else "SIM=>UE"
        
        # 生成标题 - 包含命令信息和方向
        if is_ue_to_sim and hdr.ins is not None:
            # UE->SIM: 显示命令名称
            command_name = parser.ue_to_sim_commands.get(hdr.ins, f"Unknown Command (0x{hdr.ins:02X})")
            title = f"[UE->SIM] {command_name}"
        else:
            # SIM->UE: 显示响应类型
            if msg.raw.startswith("62") or msg.raw.startswith("6F"):
                title = "[SIM->UE] FCP Response"
            elif len(msg.raw) == 4:
                status = int(msg.raw, 16)
                status_desc = parser.sim_to_ue_status.get(status, "Unknown Status")
                title = f"[SIM->UE] {status_desc}"
            else:
                title = "[SIM->UE] Response Data"
            
        return ParseResult(msg_type=MsgType.NORMAL_SIM, message=msg, apdu=hdr, root=root,
                           title=title, direction_hint=direction_hint)
