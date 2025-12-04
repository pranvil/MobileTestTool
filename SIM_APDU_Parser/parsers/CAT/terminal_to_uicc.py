# parsers/CAT/terminal_to_uicc.py
"""
手机发给UICC的CAT命令解析器
包括: 8010(TERMINAL PROFILE), 8014(TERMINAL RESPONSE), 80C2(ENVELOPE), 8012(FETCH), 80AA(TERMINAL CAPABILITY)
"""
from SIM_APDU_Parser.core.models import ParseNode
from SIM_APDU_Parser.parsers.CAT.common import (
    parse_comp_tlvs_to_nodes, EVENT_MAP, parse_event_list_to_nodes,
    parse_location_status_text, parse_location_info_text, device_identities_text,
    parse_access_tech_text, parse_tlvs_from_dict, parse_network_access_name_text,
    parse_data_connection_status_text, parse_data_connection_type_text,
    parse_esm_cause_text, parse_transaction_identifier_text,
    parse_date_time_timezone_text, parse_pdp_pdn_pdu_type_text,
    parse_address_pdp_pdn_pdu_type_text, parse_timer_identifier_text,
    parse_timer_value_text, parse_media_type_text
)
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
    
    def parse_command(self, cla: int, ins: int, payload_hex: str, le: int = None) -> ParseNode:
        """
        解析手机发给UICC的CAT命令
        
        Args:
            cla: CLA字节
            ins: INS字节  
            payload_hex: 去掉CLA/INS/P1/P2/LC后的数据部分
            le: Le字段（期望返回的数据长度），可选
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
            return self._parse_fetch(payload_hex, le)
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
        """解析 Call Control (D4)"""
        if not payload_hex or len(payload_hex) < 4:
            root.children.append(ParseNode(name="Data", value=payload_hex))
            return
        
        # payload_hex 应该以 D4 开头，去掉 D4 tag
        if payload_hex[:2].upper() != 'D4':
            root.children.append(ParseNode(name="Data", value=payload_hex))
            return
        
        idx = 2  # 跳过 D4 tag
        n = len(payload_hex)
        
        # 解析长度字段（可能是1字节或2字节）
        if idx + 2 > n:
            root.children.append(ParseNode(name="Data", value=payload_hex))
            return
        
        # 读取第一个字节作为长度
        length_byte1 = int(payload_hex[idx:idx+2], 16)
        idx += 2
        
        # 如果长度字节的最高位是1，表示是2字节长度
        if length_byte1 & 0x80:
            if idx + 2 > n:
                root.children.append(ParseNode(name="Data", value=payload_hex))
                return
            length = ((length_byte1 & 0x7F) << 8) | int(payload_hex[idx:idx+2], 16)
            idx += 2
        else:
            length = length_byte1
        
        # 解析 TLV 数据
        data_start = idx
        while idx < n and idx < data_start + length * 2:
            if idx + 4 > n:
                break
            
            tag = payload_hex[idx:idx+2].upper()
            idx += 2
            
            if idx + 2 > n:
                break
            
            ln = int(payload_hex[idx:idx+2], 16)
            idx += 2
            
            if idx + 2 * ln > n:
                val = payload_hex[idx:]
                idx = n
            else:
                val = payload_hex[idx:idx+2*ln]
                idx += 2 * ln
            
            # 根据 tag 调用对应的解析函数
            self._parse_call_control_tlv(root, tag, val)
    
    def _parse_call_control_tlv(self, root: ParseNode, tag: str, value_hex: str):
        """解析 Call Control 中的各个 TLV 字段"""
        from SIM_APDU_Parser.parsers.CAT.common import (
            device_identities_text, parse_address_text, parse_location_info_text,
            parse_alpha_identifier_text
        )
        
        if tag in ('02', '82'):
            # Device identities (Mandatory)
            root.children.append(ParseNode(
                name="Device identities (82)",
                value=device_identities_text(value_hex)
            ))
        elif tag in ('06', '86'):
            # Address (Mandatory - for call setup)
            root.children.append(ParseNode(
                name="Address (86)",
                value=parse_address_text(value_hex)
            ))
        elif tag in ('09', '89'):
            # SS String (Mandatory - for supplementary service)
            root.children.append(ParseNode(
                name="SS String (89)",
                value=value_hex  # TODO: 实现 SS String 解析
            ))
        elif tag in ('0A', '8A'):
            # USSD String (Mandatory - for USSD)
            root.children.append(ParseNode(
                name="USSD String (8A)",
                value=value_hex  # TODO: 实现 USSD String 解析
            ))
        elif tag == '52':
            # PDP Context Activation Parameters (Mandatory - for PDP context)
            root.children.append(ParseNode(
                name="PDP Context Activation Parameters (52)",
                value=value_hex  # TODO: 实现 PDP Context 解析
            ))
        elif tag in ('FC', '7C'):
            # EPS PDN Connection Activation Parameters (Mandatory - for EPS PDN)
            self._parse_eps_pdn_connection_activation(root, value_hex)
        elif tag in ('B1', '31'):
            # IMS URI (Mandatory - for IMS communication)
            root.children.append(ParseNode(
                name="IMS URI (B1)",
                value=value_hex  # TODO: 实现 IMS URI 解析
            ))
        elif tag in ('0C', '8C'):
            # PDU Session Establishment Parameters (Mandatory - for PDU session)
            root.children.append(ParseNode(
                name="PDU Session Establishment Parameters (8C)",
                value=value_hex  # TODO: 实现 PDU Session 解析
            ))
        elif tag in ('07', '87'):
            # Capability Configuration Parameters (Optional)
            root.children.append(ParseNode(
                name="Capability Configuration Parameters (87)",
                value=value_hex  # TODO: 实现 Capability Configuration 解析
            ))
        elif tag in ('05', '85'):
            # Subaddress (Optional)
            root.children.append(ParseNode(
                name="Subaddress (85)",
                value=parse_alpha_identifier_text(value_hex)  # 可能不是完全正确，但先这样
            ))
        elif tag in ('13', '93'):
            # Location Information (Conditional)
            root.children.append(ParseNode(
                name="Location Information (13)",
                value=parse_location_info_text(value_hex)
            ))
        else:
            # 未知 tag，显示原始数据
            root.children.append(ParseNode(
                name=f"Unknown TLV ({tag})",
                value=value_hex
            ))
    
    def _parse_eps_pdn_connection_activation(self, root: ParseNode, value_hex: str):
        """解析 EPS PDN Connection Activation Parameters (FC/7C) - NAS 消息"""
        if not value_hex or len(value_hex) < 6:
            root.children.append(ParseNode(name="EPS PDN Connection Activation Parameters (FC)", value=value_hex))
            return
        
        pdn_node = ParseNode(name="EPS PDN Connection Activation Parameters (FC)")
        
        idx = 0
        n = len(value_hex)
        
        # 解析第一个字节：EPS Bearer Identity (高4位) + Protocol Discriminator (低4位)
        if idx + 2 > n:
            pdn_node.children.append(ParseNode(name="Data", value=value_hex))
            root.children.append(pdn_node)
            return
        
        first_byte = int(value_hex[idx:idx+2], 16)
        eps_bearer_id = (first_byte >> 4) & 0x0F
        protocol_discriminator = first_byte & 0x0F
        idx += 2
        
        protocol_names = {
            0x0: "Group Call Control",
            0x1: "Broadcast Call Control",
            0x2: "EPS Session Management (ESM)",
            0x3: "Call Control",
            0x4: "Mobility Management",
            0x5: "GPRS Mobility Management",
            0x6: "SMS",
            0x7: "GPRS Session Management",
            0x8: "Non-Access Stratum (NAS) transport",
            0x9: "Location Services",
            0xA: "EPS Mobility Management",
            0xB: "EPS Connection Management",
            0xC: "LCS",
            0xD: "SBc",
            0xE: "Non-3GPP specific messages",
            0xF: "Reserved"
        }
        
        pdn_node.children.append(ParseNode(
            name="EPS Bearer Identity",
            value=f"{eps_bearer_id}"
        ))
        pdn_node.children.append(ParseNode(
            name="Protocol Discriminator",
            value=f"{protocol_discriminator} ({protocol_names.get(protocol_discriminator, 'Unknown')})"
        ))
        
        # 解析 Procedure Transaction Identity
        if idx + 2 > n:
            pdn_node.children.append(ParseNode(name="Remaining Data", value=value_hex[idx:]))
            root.children.append(pdn_node)
            return
        
        pti = int(value_hex[idx:idx+2], 16)
        idx += 2
        pdn_node.children.append(ParseNode(
            name="Procedure Transaction Identity",
            value=f"{pti}"
        ))
        
        # 解析 Message Type
        if idx + 2 > n:
            pdn_node.children.append(ParseNode(name="Remaining Data", value=value_hex[idx:]))
            root.children.append(pdn_node)
            return
        
        message_type = int(value_hex[idx:idx+2], 16)
        idx += 2
        
        message_type_names = {
            0xC0: "Activate default EPS bearer context request",
            0xC1: "Activate default EPS bearer context accept",
            0xC2: "Activate default EPS bearer context reject",
            0xC3: "Activate default EPS bearer context complete",
            0xD0: "PDN CONNECTIVITY REQUEST",
            0xD1: "PDN CONNECTIVITY REJECT",
            0xD2: "PDN DISCONNECT REQUEST",
            0xD3: "PDN DISCONNECT REJECT",
            0xD4: "Bearer resource allocation request",
            0xD5: "Bearer resource allocation reject",
            0xD6: "Bearer resource modification request",
            0xD7: "Bearer resource modification reject",
            0xD8: "Deactivate EPS bearer context request",
            0xD9: "Deactivate EPS bearer context accept",
            0xDA: "ESM status",
            0xDB: "ESM information request",
            0xDC: "ESM information response",
        }
        
        pdn_node.children.append(ParseNode(
            name="Message Type",
            value=f"0x{message_type:02X} ({message_type_names.get(message_type, 'Unknown')})"
        ))
        
        # 解析 PDN Type 和 Request Type
        if idx + 2 > n:
            pdn_node.children.append(ParseNode(name="Remaining Data", value=value_hex[idx:]))
            root.children.append(pdn_node)
            return
        
        pdn_type_byte = int(value_hex[idx:idx+2], 16)
        idx += 2
        
        pdn_type = (pdn_type_byte >> 4) & 0x07
        request_type = pdn_type_byte & 0x0F
        
        pdn_type_names = {
            0x1: "IPv4",
            0x2: "IPv6",
            0x3: "IPv4v6",
            0x4: "Non-IP",
            0x5: "Ethernet"
        }
        
        request_type_names = {
            0x1: "Initial request",
            0x2: "Handover",
            0x3: "Emergency",
            0x4: "Emergency fallback"
        }
        
        pdn_node.children.append(ParseNode(
            name="PDN Type",
            value=f"{pdn_type} ({pdn_type_names.get(pdn_type, 'Unknown')})"
        ))
        pdn_node.children.append(ParseNode(
            name="Request Type",
            value=f"{request_type} ({request_type_names.get(request_type, 'Unknown')})"
        ))
        
        # 解析后续的 IE（Information Elements）
        remaining_data = value_hex[idx:]
        if remaining_data:
            self._parse_nas_ies(pdn_node, remaining_data)
        
        root.children.append(pdn_node)
    
    def _parse_nas_ies(self, parent: ParseNode, data_hex: str):
        """解析 NAS 消息中的 IE (Information Elements)"""
        idx = 0
        n = len(data_hex)
        
        while idx < n:
            if idx + 2 > n:
                break
            
            ie_type = int(data_hex[idx:idx+2], 16)
            idx += 2
            
            # 根据 IE Type 解析
            if ie_type == 0x27:  # Protocol Configuration Options
                if idx + 2 > n:
                    break
                pco_length = int(data_hex[idx:idx+2], 16)
                idx += 2
                if idx + 2 * pco_length > n:
                    pco_data = data_hex[idx:]
                    idx = n
                else:
                    pco_data = data_hex[idx:idx+2*pco_length]
                    idx += 2 * pco_length
                
                parent.children.append(ParseNode(
                    name="Protocol Configuration Options (PCO)",
                    value=f"Length: {pco_length}, Data: {pco_data[:120]}{'...' if len(pco_data) > 120 else ''}"
                ))
            elif ie_type == 0x28:  # Access Point Name (APN)
                if idx + 2 > n:
                    break
                apn_length = int(data_hex[idx:idx+2], 16)
                idx += 2
                if idx + 2 * apn_length > n:
                    apn_data = data_hex[idx:]
                    idx = n
                else:
                    apn_data = data_hex[idx:idx+2*apn_length]
                    idx += 2 * apn_length
                
                # 解析 APN：第一个字节是长度，后面是 APN 字符串
                if len(apn_data) >= 2:
                    apn_label_len = int(apn_data[0:2], 16)
                    apn_str = ""
                    apn_idx = 2
                    while apn_idx < len(apn_data) and apn_label_len > 0:
                        if apn_idx + 2 * apn_label_len > len(apn_data):
                            break
                        label_hex = apn_data[apn_idx:apn_idx+2*apn_label_len]
                        try:
                            label_bytes = bytes.fromhex(label_hex)
                            apn_str += label_bytes.decode('ascii', errors='replace')
                            apn_idx += 2 * apn_label_len
                            if apn_idx < len(apn_data):
                                apn_label_len = int(apn_data[apn_idx:apn_idx+2], 16)
                                apn_idx += 2
                                if apn_label_len > 0:
                                    apn_str += "."
                        except:
                            break
                    
                    parent.children.append(ParseNode(
                        name="Access Point Name (APN)",
                        value=f"{apn_str}" if apn_str else f"Raw: {apn_data}"
                    ))
                else:
                    parent.children.append(ParseNode(
                        name="Access Point Name (APN)",
                        value=f"Raw: {apn_data}"
                    ))
            else:
                # 未知 IE，显示原始数据
                if idx + 2 > n:
                    parent.children.append(ParseNode(
                        name=f"Unknown IE (0x{ie_type:02X})",
                        value=data_hex[idx:]
                    ))
                    break
                
                # 尝试读取长度（如果存在）
                ie_length = int(data_hex[idx:idx+2], 16)
                idx += 2
                if idx + 2 * ie_length > n:
                    ie_data = data_hex[idx:]
                    idx = n
                else:
                    ie_data = data_hex[idx:idx+2*ie_length]
                    idx += 2 * ie_length
                
                parent.children.append(ParseNode(
                    name=f"Unknown IE (0x{ie_type:02X})",
                    value=f"Length: {ie_length}, Data: {ie_data[:60]}{'...' if len(ie_data) > 60 else ''}"
                ))
    
    def _parse_mo_short_message_control(self, root: ParseNode, payload_hex: str):
        """解析 MO Short Message control (D5) - 占位符"""
        root.children.append(ParseNode(name="Data", value=payload_hex))
    
    def _parse_event_download(self, root: ParseNode, payload_hex: str):
        """解析 Event Download (D6)"""
        if not payload_hex or len(payload_hex) < 4:
            root.children.append(ParseNode(name="Data", value=payload_hex))
            return
        
        # payload_hex 应该以 D6 开头，去掉 D6 tag
        if payload_hex[:2].upper() != 'D6':
            root.children.append(ParseNode(name="Data", value=payload_hex))
            return
        
        idx = 2  # 跳过 D6 tag
        n = len(payload_hex)
        
        # 解析长度字段（可能是1字节或2字节）
        if idx + 2 > n:
            root.children.append(ParseNode(name="Data", value=payload_hex))
            return
        
        # 读取第一个字节作为长度
        length_byte1 = int(payload_hex[idx:idx+2], 16)
        idx += 2
        
        # 如果长度字节的最高位是1，表示是2字节长度
        if length_byte1 & 0x80:
            if idx + 2 > n:
                root.children.append(ParseNode(name="Data", value=payload_hex))
                return
            length = ((length_byte1 & 0x7F) << 8) | int(payload_hex[idx:idx+2], 16)
            idx += 2
        else:
            length = length_byte1
        
        # 解析 TLV 数据，查找 Event List (Tag 19/99)
        data_start = idx
        event_types = []
        tlv_data = {}  # 存储所有 TLV 数据，供后续解析使用
        
        while idx < n and idx < data_start + length * 2:
            if idx + 4 > n:
                break
            
            tag = payload_hex[idx:idx+2].upper()
            idx += 2
            
            if idx + 2 > n:
                break
            
            ln = int(payload_hex[idx:idx+2], 16)
            idx += 2
            
            if idx + 2 * ln > n:
                val = payload_hex[idx:]
                idx = n
            else:
                val = payload_hex[idx:idx+2*ln]
                idx += 2 * ln
            
            # 存储 TLV 数据
            tlv_data[tag] = val
            
            # 查找 Event List (Tag 19/99)
            if tag in ('19', '99'):
                # 解析 Event List 获取事件类型
                event_list_node = parse_event_list_to_nodes(val)
                root.children.append(event_list_node)
                
                # 提取事件类型代码
                for event_node in event_list_node.children:
                    if event_node.name.startswith('Event '):
                        event_code = event_node.name.split(' ')[1]
                        event_types.append(event_code)
        
        # 根据事件类型调用对应的解析函数
        if event_types:
            # 使用第一个事件类型来确定解析函数
            primary_event = event_types[0]
            self._parse_event_download_by_type(root, payload_hex, primary_event, event_types, tlv_data)
        else:
            # 没有找到 Event List，显示所有 TLV 数据
            root.children.append(ParseNode(name="Warning", value="Event List not found"))
            for tag, val in tlv_data.items():
                root.children.append(ParseNode(
                    name=f"TLV {tag}",
                    value=f"Length: {len(val)//2}, Data: {val[:60]}{'...' if len(val) > 60 else ''}"
                ))
    
    def _parse_event_download_by_type(self, root: ParseNode, payload_hex: str, primary_event: str, all_events: list, tlv_data: dict):
        """根据事件类型调用对应的解析函数"""
        # 根据事件类型调用对应的解析函数
        if primary_event == '00':
            self._parse_event_mt_call(root, payload_hex, tlv_data)
        elif primary_event == '01':
            self._parse_event_call_connected(root, payload_hex, tlv_data)
        elif primary_event == '02':
            self._parse_event_call_disconnected(root, payload_hex, tlv_data)
        elif primary_event == '03':
            self._parse_event_location_status(root, payload_hex, tlv_data)
        elif primary_event == '04':
            self._parse_event_user_activity(root, payload_hex, tlv_data)
        elif primary_event == '05':
            self._parse_event_idle_screen_available(root, payload_hex, tlv_data)
        elif primary_event == '06':
            self._parse_event_card_reader_status(root, payload_hex, tlv_data)
        elif primary_event == '07':
            self._parse_event_language_selection(root, payload_hex, tlv_data)
        elif primary_event == '08':
            self._parse_event_browser_termination(root, payload_hex, tlv_data)
        elif primary_event == '09':
            self._parse_event_data_available(root, payload_hex, tlv_data)
        elif primary_event == '0A':
            self._parse_event_channel_status(root, payload_hex, tlv_data)
        elif primary_event == '0B':
            self._parse_event_access_technology_change_single(root, payload_hex, tlv_data)
        elif primary_event == '0C':
            self._parse_event_display_parameters_changed(root, payload_hex, tlv_data)
        elif primary_event == '0D':
            self._parse_event_local_connection(root, payload_hex, tlv_data)
        elif primary_event == '0E':
            self._parse_event_network_search_mode_change(root, payload_hex, tlv_data)
        elif primary_event == '0F':
            self._parse_event_browsing_status(root, payload_hex, tlv_data)
        elif primary_event == '10':
            self._parse_event_frames_information_change(root, payload_hex, tlv_data)
        elif primary_event == '11':
            self._parse_event_iwlan_access_status(root, payload_hex, tlv_data)
        elif primary_event == '12':
            self._parse_event_network_rejection(root, payload_hex, tlv_data)
        elif primary_event == '13':
            self._parse_event_hci_connectivity(root, payload_hex, tlv_data)
        elif primary_event == '14':
            self._parse_event_access_technology_change_multiple(root, payload_hex, tlv_data)
        elif primary_event == '15':
            self._parse_event_csg_cell_selection(root, payload_hex, tlv_data)
        elif primary_event == '16':
            self._parse_event_contactless_state_request(root, payload_hex, tlv_data)
        elif primary_event == '17':
            self._parse_event_ims_registration(root, payload_hex, tlv_data)
        elif primary_event == '18':
            self._parse_event_incoming_ims_data(root, payload_hex, tlv_data)
        elif primary_event == '19':
            self._parse_event_profile_container(root, payload_hex, tlv_data)
        elif primary_event == '1B':
            self._parse_event_secured_profile_container(root, payload_hex, tlv_data)
        elif primary_event == '1C':
            self._parse_event_poll_interval_negotiation(root, payload_hex, tlv_data)
        elif primary_event == '1D':
            self._parse_event_data_connection_status_change(root, payload_hex, tlv_data)
        elif primary_event == '1E':
            self._parse_event_cag_cell_selection(root, payload_hex, tlv_data)
        elif primary_event == '1F':
            self._parse_event_slices_status_change(root, payload_hex, tlv_data)
        else:
            # 未知事件类型
            root.children.append(ParseNode(
                name="Event Data",
                value=f"Unknown event type: {primary_event}, Raw: {payload_hex}"
            ))
    
    # ========== Event Download 类型解析函数（占位符） ==========
    
    def _parse_event_mt_call(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: MT call (00) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))

    def _parse_event_call_connected(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Call connected (01)"""
        if tlv_data is None:
            tlv_data = {}
        
        # 根据 TS 31.111 7.5.2A.2，Call connected 事件包含：
        # 必需字段：Event list (19/99), Device identities (02/82), Transaction identifier (1C/9C)
        # 可选字段：Media Type (7E/FE, 8.132)
        
        # 使用通用函数解析必需字段和可选字段
        parse_tlvs_from_dict(
            root=root,
            tlv_data=tlv_data,
            required_tags=[
                ('02', '82'),  # Device identities
                ('1C', '9C')  # Transaction identifier
            ],
            optional_tags=[
                ('7E', 'FE')  # Media Type (8.132)
            ],
            exclude_tags={'19', '99'}  # Event List
        )

    def _parse_event_call_disconnected(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Call disconnected (02)"""
        if tlv_data is None:
            tlv_data = {}
        
        # 根据 TS 31.111 7.5.3A.2，Call disconnected 事件包含：
        # 必需字段：Event list (19/99), Device identities (02/82), Transaction identifier (1C/9C)
        # 可选字段：Cause (1A/9A, 8.26), Media Type (7E/FE, 8.132), IMS call disconnection cause (55/D5, 8.133)
        
        # 使用通用函数解析必需字段和可选字段
        parse_tlvs_from_dict(
            root=root,
            tlv_data=tlv_data,
            required_tags=[
                ('02', '82'),  # Device identities
                ('1C', '9C')  # Transaction identifier
            ],
            optional_tags=[
                ('1A', '9A'),  # Cause (8.26)
                ('7E', 'FE'),  # Media Type (8.132)
                ('55', 'D5')   # IMS call disconnection cause (8.133)
            ],
            exclude_tags={'19', '99'}  # Event List
        )
    
    def _parse_event_location_status(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Location status (03)"""
        if tlv_data is None:
            tlv_data = {}
        
        # 使用通用函数解析 TLV
        # 必需字段：Device identities, Location status
        # 可选字段：Location Information
        parse_tlvs_from_dict(
            root=root,
            tlv_data=tlv_data,
            required_tags=[('02', '82'), ('1B', '9B')],  # Device identities, Location status
            optional_tags=[('13', '93')],  # Location Information
            exclude_tags={'19', '99'}  # Event List
        )
    
    def _parse_event_user_activity(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: User activity (04) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))

    def _parse_event_idle_screen_available(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Idle screen available (05) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))

    def _parse_event_card_reader_status(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Card reader status (06) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))

    def _parse_event_language_selection(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Language selection (07) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))

    def _parse_event_browser_termination(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Browser termination (08) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))

    def _parse_event_data_available(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Data available (09)"""
        if tlv_data is None:
            tlv_data = {}
        
        # 根据 TS 31.111 7.5.10.2，Data available 事件包含：
        # 必需字段：Event list (19/99), Device identities (02/82), Channel status (38/B8), Channel data length (37/B7)
        
        # 使用通用函数解析必需字段
        parse_tlvs_from_dict(
            root=root,
            tlv_data=tlv_data,
            required_tags=[
                ('02', '82'),  # Device identities
                ('38', 'B8'),  # Channel status (8.56)
                ('37', 'B7')  # Channel data length (8.54)
            ],
            optional_tags=[],
            exclude_tags={'19', '99'}  # Event List
        )

    def _parse_event_channel_status(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Channel status (0A)"""
        if tlv_data is None:
            tlv_data = {}
        
        # 根据 TS 31.111 7.5.11.2，Channel status 事件包含：
        # 必需字段：Event list (19/99), Device identities (02/82), Channel status (38/B8)
        # 可选字段：Bearer Description (35/B5), Other address (local address) (3E/BE)
        
        # 使用通用函数解析必需字段和可选字段
        parse_tlvs_from_dict(
            root=root,
            tlv_data=tlv_data,
            required_tags=[
                ('02', '82'),  # Device identities
                ('38', 'B8'),  # Channel status (8.56)
            ],
            optional_tags=[
                ('35', 'B5'),  # Bearer Description (8.52) - 条件可选
                ('3E', 'BE'),  # Other address (local address) (8.58) - 条件可选
            ],
            exclude_tags={'19', '99'}  # Event List
        )

    def _parse_event_access_technology_change_single(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Access Technology Change (single access technology) (0B)"""
        if tlv_data is None:
            tlv_data = {}
        
        # 使用通用函数解析 TLV
        # 必需字段：Device identities, Access Technology
        parse_tlvs_from_dict(
            root=root,
            tlv_data=tlv_data,
            required_tags=[('02', '82'), ('3F', 'BF')],  # Device identities, Access Technology
            exclude_tags={'19', '99'}  # Event List
        )

    def _parse_event_display_parameters_changed(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Display parameters changed (0C) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))

    def _parse_event_local_connection(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Local connection (0D) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))

    def _parse_event_network_search_mode_change(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Network Search Mode Change (0E) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))

    def _parse_event_browsing_status(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Browsing status (0F) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))

    def _parse_event_frames_information_change(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Frames Information Change (10) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))

    def _parse_event_iwlan_access_status(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: (I-)WLAN Access Status (11) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))

    def _parse_event_network_rejection(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Network Rejection (12) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))

    def _parse_event_hci_connectivity(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: HCI connectivity event (13) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))

    def _parse_event_access_technology_change_multiple(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Access Technology Change (multiple access technologies) (14)"""
        if tlv_data is None:
            tlv_data = {}
        
        # 使用通用函数解析 TLV
        # 必需字段：Device identities, Access Technology
        parse_tlvs_from_dict(
            root=root,
            tlv_data=tlv_data,
            required_tags=[('02', '82'), ('3F', 'BF')],  # Device identities, Access Technology
            exclude_tags={'19', '99'}  # Event List
        )

    def _parse_event_csg_cell_selection(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: CSG cell selection (15) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))

    def _parse_event_contactless_state_request(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Contactless state request (16) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))

    def _parse_event_ims_registration(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: IMS Registration (17)"""
        if tlv_data is None:
            tlv_data = {}
        
        # 使用通用函数解析必需字段
        # 必需字段：Device identities
        # 注意：IMPU List (77/F7) 和 IMS Status Code (78/F8) 需要手动解析，所以排除它们避免显示原始数据
        parse_tlvs_from_dict(
            root=root,
            tlv_data=tlv_data,
            required_tags=[
                ('02', '82')  # Device identities
            ],
            optional_tags=[],
            exclude_tags={'19', '99', '77', 'F7', '78', 'F8'}  # Event List, IMPU List, IMS Status Code
        )
        
        # 手动解析 IMPU List (77/F7) - 包含嵌套的 URI TLV
        for tag in ('77', 'F7'):
            tag_upper = tag.upper()
            if tag_upper in tlv_data:
                impu_list_node = ParseNode(name=f"IMPU List ({tag_upper})")
                self._parse_impu_list(impu_list_node, tlv_data[tag_upper])
                root.children.append(impu_list_node)
                break
        
        # 手动解析 IMS Status Code (78/F8) - ASCII 格式的数字序列
        for tag in ('78', 'F8'):
            tag_upper = tag.upper()
            if tag_upper in tlv_data:
                status_code = self._parse_ims_status_code(tlv_data[tag_upper])
                root.children.append(ParseNode(
                    name=f"IMS Status Code ({tag_upper})",
                    value=status_code
                ))
                break
    
    def _parse_impu_list(self, root: ParseNode, value_hex: str):
        """解析 IMPU List (77/F7) - 包含嵌套的 URI TLV (80)"""
        if not value_hex or len(value_hex) < 2:
            root.children.append(ParseNode(name="Error", value="Invalid IMPU List data"))
            return
        
        idx = 0
        n = len(value_hex)
        uri_count = 0
        
        # IMPU List 包含一个或多个 URI TLV 数据对象
        # URI TLV Tag: '80'
        # URI TLV Length: Z
        # URI TLV Value: UTF-8 编码的 IMPU (SIP URI 或 TEL URI)
        while idx < n:
            if idx + 2 > n:
                break
            
            tag = value_hex[idx:idx+2].upper()
            idx += 2
            
            if tag != '80':
                # 不是 URI TLV，可能是数据错误
                root.children.append(ParseNode(
                    name="Warning",
                    value=f"Unexpected tag {tag} in IMPU List at position {idx//2}"
                ))
                break
            
            if idx + 2 > n:
                break
            
            # 读取长度
            length = int(value_hex[idx:idx+2], 16)
            idx += 2
            
            if idx + length * 2 > n:
                # 数据不完整
                root.children.append(ParseNode(
                    name="Warning",
                    value=f"Incomplete URI TLV at position {idx//2}"
                ))
                break
            
            # 读取 URI 值（UTF-8 编码）
            uri_hex = value_hex[idx:idx+length*2]
            idx += length * 2
            
            # 解码 UTF-8
            try:
                uri_bytes = bytes.fromhex(uri_hex)
                uri_str = uri_bytes.decode('utf-8', errors='replace')
                uri_count += 1
                root.children.append(ParseNode(
                    name=f"IMPU {uri_count}",
                    value=uri_str
                ))
            except Exception as e:
                root.children.append(ParseNode(
                    name=f"IMPU {uri_count + 1} (Decode Error)",
                    value=f"Error: {e}, Raw: {uri_hex[:60]}{'...' if len(uri_hex) > 60 else ''}"
                ))
                uri_count += 1
        
        if uri_count == 0:
            root.children.append(ParseNode(name="Info", value="No IMPU found in list"))
    
    def _parse_ims_status_code(self, value_hex: str) -> str:
        """解析 IMS Status Code (78/F8) - ASCII 格式的数字序列"""
        if not value_hex:
            return "Invalid data"
        
        try:
            # IMS Status Code 是 ASCII 格式的数字序列（例如 "200", "403"）
            status_bytes = bytes.fromhex(value_hex)
            status_str = status_bytes.decode('ascii', errors='replace')
            return status_str
        except Exception as e:
            return f"Decode error: {e}, Raw: {value_hex[:60]}{'...' if len(value_hex) > 60 else ''}"

    def _parse_event_incoming_ims_data(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Incoming IMS data (18) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))

    def _parse_event_profile_container(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Profile Container (19) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))

    def _parse_event_secured_profile_container(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Secured Profile Container (1B) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))

    def _parse_event_poll_interval_negotiation(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Poll Interval Negotiation (1C) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))

    def _parse_event_data_connection_status_change(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Data Connection Status Change (1D)"""
        if tlv_data is None:
            tlv_data = {}
        
        # 使用通用函数解析所有已知字段
        # 必需字段：Device identities, Data connection status, Data connection type, Transaction identifier, Location status
        # 可选字段：Location Information, Access Technology, Network Access Name, Date-Time and Time zone, Address/PDP/PDN/PDU Type, (E/5G)SM cause
        parse_tlvs_from_dict(
            root=root,
            tlv_data=tlv_data,
            required_tags=[
                ('02', '82'),  # Device identities
                ('1D', '9D'),  # Data connection status
                ('2A', 'AA'),  # Data connection type
                ('1C', '9C'),  # Transaction identifier
                ('1B', '9B')   # Location status
            ],
            optional_tags=[
                ('13', '93'),  # Location Information
                ('3F', 'BF'),  # Access Technology
                ('47', 'C7'),  # Network Access Name
                ('26', 'A6'),  # Date-Time and Time zone
                ('0B', '8B'),  # Address / PDP/PDN/PDU Type
                ('2E', 'AE')   # (E/5G)SM cause
            ],
            exclude_tags={'19', '99'}  # Event List
        )

    def _parse_event_cag_cell_selection(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: CAG cell selection (1E) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))

    def _parse_event_slices_status_change(self, root: ParseNode, payload_hex: str, tlv_data: dict = None):
        """解析 Event: Slices Status Change (1F) - 占位符"""
        root.children.append(ParseNode(name="Event Data", value=payload_hex))
    
    def _parse_timer_expiration(self, root: ParseNode, payload_hex: str):
        """解析 Timer Expiration (D7)"""
        if not payload_hex or len(payload_hex) < 2:
            root.children.append(ParseNode(name="Data", value=payload_hex))
            return
        
        idx = 0
        n = len(payload_hex)
        
        # 跳过 D7 tag (已经在 _parse_envelope 中识别)
        if payload_hex[:2].upper() == 'D7':
            idx += 2
        
        # 解析长度字段（可能是1字节或2字节）
        if idx + 2 > n:
            root.children.append(ParseNode(name="Data", value=payload_hex))
            return
        
        # 读取第一个字节作为长度
        length_byte1 = int(payload_hex[idx:idx+2], 16)
        idx += 2
        
        # 如果长度字节的最高位是1，表示是2字节长度
        if length_byte1 & 0x80:
            if idx + 2 > n:
                root.children.append(ParseNode(name="Data", value=payload_hex))
                return
            length = ((length_byte1 & 0x7F) << 8) | int(payload_hex[idx:idx+2], 16)
            idx += 2
        else:
            length = length_byte1
        
        # 解析 TLV 数据
        tlv_data = {}
        data_start = idx
        
        while idx < n and idx < data_start + length * 2:
            if idx + 4 > n:
                break
            
            tag = payload_hex[idx:idx+2].upper()
            idx += 2
            
            if idx + 2 > n:
                break
            
            ln = int(payload_hex[idx:idx+2], 16)
            idx += 2
            
            if idx + 2 * ln > n:
                val = payload_hex[idx:]
                idx = n
            else:
                val = payload_hex[idx:idx+2*ln]
                idx += 2 * ln
            
            # 存储 TLV 数据
            tlv_data[tag] = val
        
        # 使用通用函数解析已知字段
        # 必需字段：Device identities, Timer identifier, Timer value
        parse_tlvs_from_dict(
            root=root,
            tlv_data=tlv_data,
            required_tags=[
                ('02', '82'),  # Device identities
                ('24', 'A4'),  # Timer identifier
                ('25', 'A5')   # Timer value
            ],
            optional_tags=[],
            exclude_tags=set()
        )
    
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
    
    def _parse_fetch(self, payload_hex: str, le: int = None) -> ParseNode:
        """
        解析 FETCH (8012)
        
        Args:
            payload_hex: 数据部分（FETCH 通常没有数据，只有 Le）
            le: Le字段（期望返回的数据长度）
        """
        title = "CAT: FETCH"
        root = ParseNode(name=title)
        
        # 如果有 Le 字段，显示数据长度
        if le is not None:
            root.children.append(ParseNode(name="Data length", value=str(le)))
        elif payload_hex:
            # 如果没有 Le 但 payload_hex 不为空，可能是 Le 在 payload_hex 中
            # FETCH 命令格式：8012 P1 P2 Le
            # 如果 payload_hex 是 1 字节，可能是 Le
            if len(payload_hex) == 2:
                try:
                    le_value = int(payload_hex, 16)
                    root.children.append(ParseNode(name="Data length", value=str(le_value)))
                except ValueError:
                    root.children.append(ParseNode(name="Data length", value=payload_hex))
            else:
                root.children.append(ParseNode(name="Data length", value=payload_hex))
        else:
            # 既没有 Le 也没有 payload_hex，显示未知
            root.children.append(ParseNode(name="Data length", value="Unknown"))
        
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
