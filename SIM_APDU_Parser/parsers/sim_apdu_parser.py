from SIM_APDU_Parser.core.models import ParseNode, Apdu
from SIM_APDU_Parser.core.utils import parse_apdu_header
from SIM_APDU_Parser.parsers.SIM_APDU.fcp_parser import parse_fcp_data


class SimApduParser:
    """SIM APDU解析器
    
    解析普通的SIM APDU，包括：
    1. UE->SIM: 根据CLA和INS指令解析
    2. SIM->UE: 62开头表示FCP，使用FCP解析器
    """
    
    def __init__(self):
        # UE->SIM指令映射表（根据截图中的Table 10.5）
        self.ue_to_sim_commands = {
            0xA4: "SELECT FILE",
            0xF2: "STATUS", 
            0xB0: "READ BINARY",
            0xD6: "UPDATE BINARY",
            0xB2: "READ RECORD",
            0xDC: "UPDATE RECORD",
            0xA2: "SEARCH RECORD",
            0x32: "INCREASE",
            0xCB: "RETRIEVE DATA",
            0xDB: "SET DATA",
            0x20: "VERIFY PIN",
            0x24: "CHANGE PIN",
            0x26: "DISABLE PIN",
            0x28: "ENABLE PIN",
            0x2C: "UNBLOCK PIN",
            0x04: "DEACTIVATE FILE",
            0x44: "ACTIVATE FILE",
            0x88: "AUTHENTICATE",
            0x89: "AUTHENTICATE",
            0x84: "GET CHALLENGE",
            0xAA: "TERMINAL CAPABILITY",
            0x10: "TERMINAL PROFILE",
            0xC2: "ENVELOPE",
            0x12: "FETCH",
            0x14: "TERMINAL RESPONSE",
            0x70: "MANAGE CHANNEL",
            0x73: "MANAGE SECURE CHANNEL",
            0x75: "TRANSACT DATA",
            0x76: "SUSPEND UICC",
            0xC0: "GET RESPONSE"
        }
        
        # EF文件ID到文件名的映射字典
        self.ef_file_names = {
            # DF (Directory Files)
            "3F00": "MF (Master File)",
            "7F10": "DF_Telecom",
            "7F20": "DF_GSM", 
            "5FC0": "DF_5G",

            # EF (Elementary Files)
            "2F05": "EF_PL",
            "2F00": "DIR",
            "2F06": "ARR",
            "2FE2": "ICCID",
            "6F37": "ACM maximum value",
            "6F38": "USIM service table",
            "6F39": "Accumulated call meter",
            "6F3B": "Fixed dialling numbers",
            "6F3C": "Short messages or Key for hidden phone book entries",
            "6F3E": "Group identifier level 1",
            "6F3F": "Group identifier level 2",
            "6F40": "MSISDN storage",
            "6F41": "PUCT",
            "6F42": "SMS parameters or SMS parameters",
            "6F43": "SMS status or SMS status",
            "6F45": "CBMI",
            "6F46": "Service provider name",
            "6F47": "Short message status reports or Short message status reports",
            "6F48": "CBMID",
            "6F49": "Service Dialling Numbers",
            "6F4B": "Extension 2",
            "6F4C": "Extension 3",
            "6F4D": "Barred dialling numbers",
            "6F4E": "Extension 5",
            "6F4F": "Capability configuration parameters 2",
            "6F50": "CBMIR",
            "6F54": "SetUP Menu Elements",
            "6F55": "Extension 4",
            "6F56": "Enabled services table",
            "6F57": "Access point name control list",
            "6F58": "Comparison method information",
            "6F5B": "Initialisation value for Hyperframe number",
            "6F5C": "Maximum value of START",
            "6F60": "User controlled PLMN selector with Access Technology",
            "6F61": "Operator controlled PLMN selector with Access Technology",
            "6F62": "HPLMN selector with Access Technology",
            "6F73": "Packet switched location information",
            "6F78": "Access control class",
            "6F7B": "Forbidden PLMNs",
            "6F7E": "Location information",
            "6F80": "Incoming call information",
            "6F81": "Outgoing call information",
            "6F82": "Incoming call timer",
            "6F83": "Outgoing call timer",
            "6FAD": "Administrative data or Administrative Data",
            "6FBD": "GBA NAF List",
            "6FD9": "EHPLMN",
            "6FDB": "EHPLMN Presentation Indication",
            "6FDC": "Last RPLMN Selection Indication",
            "6FDD": "NAF Key Centre Address or NAF Key Centre Address",
            "6FDE": "Service Provider Name Icon",
            "6FDF": "PLMN Network Name Icon",
            "6FE0": "In Case of Emergency – Dialling Number",
            "6FE1": "In Case of Emergency – Free Format",
            "6FE2": "Network Connectivity Parameters for UICC IP connections",
            "6FE3": "EPS location information",
            "6FE4": "EPS NAS Security Context",
            "6FE5": "Public Service Identity of the SM-SC or Public Service Identity of the SM-SC",
            "6FE6": "USAT Facility Control",
            "6FE7": "UICC IARI or UICC IARI",
            "6FE8": "Non Access Stratum Configuration",
            "6FE9": "UICC certificate",
            "6FEA": "Relay node ID",
            "6FEB": "Max value of Secure Channel counter",
            "6FEC": "Public Warning System",
            "6FED": "FDN URI",
            "6FEE": "BDN URI",
            "6FEF": "SDN URI",
            "6FF0": "IMEI(SV) Allowed List",
            "6FF1": "IMEI(SV) Pairing Status",
            "6FF2": "IMEI(SV) Pairing Devices",
            "6FF3": "Home ePDG Identifier",
            "6FF4": "ePDG Selection Information",
            "6FF5": "Emergency ePDG Identifier",
            "6FF6": "ePDG Selection Information for Emergency Services",
            "6FF7": "From Preferred or From Preferred",
            "6FF8": "IMSConfigData or IMSConfigData",
            "6FF9": "3GPPPSDATAOFF",
            "6FFA": "3GPPPSDATAOFFServicelist or WebRTC URI",
            "6FFB": "TV Configuration",
            "6FFC": "XCAP Configuration Data or XCAP Configuration Data",
            "6FFD": "EARFCN List for MTC/NB-IOT UEs",
            "6FFE": "MuD and MiD configuration data or MuD and MiD configuration data",
            "6F02": "ISIM: IMPI/USIM: OCST",
            "6F03": "Home Network Domain Name",
            "6F04": "IMS public user identity",
            "6F06": "Access Rule Reference or Access rule reference (under ADFUSIM and DFTELECOM)",
            "6F07": "ISIM: ISIM Service Table/USIM: IMSI",
            "6F09": "ISIM: P-CSCF address /USIM: KeysPS",
            "6F0A": "Access Control to GBA_U API",
            "6F0B": "IMS DC Establishment Indication",
            "6F2C": "De-personalization Control Keys",
            "6F31": "Higher Priority PLMN search period",
            "6F32": "Co-operative network list",
            "6FB1": "Voice Group Call Service",
            "6FB2": "Voice Group Call Service Status",
            "6FB3": "Voice Broadcast Service",
            "6FB4": "Voice Broadcast Service Status",
            "6FB5": "Enhanced Multi Level Pre-emption and Priority",
            "6FB6": "Automatic Answer for eMLPP Service",
            "6FB7": "Emergency Call Codes",
            "6FC3": "Key for hidden phone book entries",
            "6FC4": "Network Parameters",
            "6FC5": "PLMN Network Name",
            "6FC6": "Operator Network List",
            "6FC7": "Mailbox Dialling Numbers",
            "6FC8": "Extension 6",
            "6FC9": "Mailbox Identifier",
            "6FCA": "Message Waiting Indication Status",
            "6FCB": "Call Forwarding Indication Status",
            "6FCC": "Extension 7",
            "6FCD": "Service Provider Display Information",
            "6FD7": "EFMSK (MBMS Service Key List)",
            "6FD8": "EFMUK (MBMS User Key)",
            "6FCE": "MMS Notification",
            "6FCF": "Extension 8",
            "6FD0": "MMS Issuer Connectivity Parameters",
            "6FDA": "GBA NAF List",
            "6FD5": "GBA Bootstrapping parameters",
            "6FD6": "GBA Bootstrapping parameters",
            "4F16": "KAUSF derivation configuration",
            "4F20": "Image data",
            "4F21": "GSM Ciphering key Kc",
            "4F22": "Image Instance data Files",
            "4F23": "Phone book synchronisation counter",
            "4F24": "Change counter",
            "4F2F": "Previous unique identifier",
            "4F30": "Phone book reference file",
            "4F31": "SoLSA LSA List",
            "4F40": "Capability configuration parameters 1",
            "4F41": "Pseudonym",
            "4F42": "User controlled PLMN selector for I-WLAN",
            "4F43": "Operator controlled PLMN selector for I-WLAN",
            "4F44": "User controlled WSID List",
            "4F45": "Operator controlled WSID List",
            "4F46": "WLAN Reauthentication Identity",
            "4F47": "Home I-WLAN Specific Identifier List",
            "4F48": "Multimedia Messages",
            "4F49": "I-WLAN Equivalent HPLMN Presentation Indication",
            "4F4A": "Multimedia Messages Data File",
            "4F52": "GPRS Ciphering key KcGPRS",
            "4F63": "CPBCCH Information",
            "4F64": "Investigation Scan",
            "4F82": "CSG Type",
            "4F83": "HNB name",
            "4F84": "Operator CSG lists",
            "4F85": "Operator CSG Type",
            "4F86": "Operator HNB name",
            "4F01": " EF5GS3GPPLOCI (5GS 3GPP location information)",                         
            "4F02": " EF5GSN3GPPLOCI (5GS non-3GPP location information)",                     
            "4F03": " EF5GS3GPPNSC (5GS 3GPP Access NAS Security Context)",                    
            "4F04": " EF5GSN3GPPNSC (5GS non-3GPP Access NAS Security Context)",                
            "4F05": " EF5GAUTHKEYS",                                                            
            "4F06": " EFUAC_AIC",                                                              
            "4F07": " EFSUCI_Calc_Info",                                                        
            "4F08": " EFOPL5G",                                                                
            "4F09": " EFSUPI_NAI",                                                              
            "4F0A": " EFRouting_Indicator",                                                     
            "4F0B": " EFURSP",                                                                 
            "4F0C": " EFTN3GPPSNN",                                                            
            "4F0D": " EFCAG",                                                                   
            "4F0E": " EFSOR-CMCI",                                                              
            "4F0F": " EFDRI"   
        }
        
        # SIM->UE状态码映射
        self.sim_to_ue_status = {
            0x9000: "OK",
            0x6200: "Warning: No information given",
            0x6281: "Warning: Part of returned data may be corrupted",
            0x6282: "Warning: End of file/record reached before reading Le bytes",
            0x6283: "Warning: Selected file invalidated",
            0x6284: "Warning: FCI not formatted according to ISO 7816-4",
            0x6300: "Warning: Authentication failed",
            0x6381: "Warning: File filled up by the last write",
            0x6400: "Error: No information given",
            0x6500: "Error: Memory failure",
            0x6581: "Error: Memory failure",
            0x6700: "Error: Wrong length",
            0x6800: "Error: No information given",
            0x6881: "Error: Logical channel not supported",
            0x6882: "Error: Secure messaging not supported",
            0x6900: "Error: No information given",
            0x6981: "Error: Command incompatible with file structure",
            0x6982: "Error: Security status not satisfied",
            0x6983: "Error: Authentication method blocked",
            0x6984: "Error: Referenced data invalidated",
            0x6985: "Error: Conditions of use not satisfied",
            0x6986: "Error: Command not allowed (no current EF)",
            0x6987: "Error: Expected secure messaging data objects missing",
            0x6988: "Error: Incorrect secure messaging data objects",
            0x6A00: "Error: No information given",
            0x6A80: "Error: Incorrect parameters in the data field",
            0x6A81: "Error: Function not supported",
            0x6A82: "Error: File not found",
            0x6A83: "Error: Record not found",
            0x6A84: "Error: Not enough memory space in the file",
            0x6A85: "Error: Lc inconsistent with TLV structure",
            0x6A86: "Error: Incorrect parameters P1-P2",
            0x6A87: "Error: Lc inconsistent with P1-P2",
            0x6A88: "Error: Referenced data not found",
            0x6A89: "Error: File already exists",
            0x6A8A: "Error: DF name already exists",
            0x6B00: "Error: Wrong parameters P1-P2",
            0x6C00: "Error: Wrong Le field",
            0x6D00: "Error: Instruction not supported or invalid",
            0x6E00: "Error: Class not supported",
            0x6F00: "Error: No precise diagnosis"
        }
        
    def _get_file_name(self, file_id: str) -> str:
        """根据文件ID获取文件名，如果找不到则返回文件ID"""
        return self.ef_file_names.get(file_id.upper(), file_id)
    
    def _extract_file_id_from_fcp(self, fcp_data: str) -> str:
        """从FCP数据中提取文件ID"""
        try:
            # FCP中提取EF ID的简单方法：找到第一个83 TAG（表示EF ID）
            # 格式：83 + 长度 + EF ID
            if len(fcp_data) >= 6:
                # 查找第一个tag 83 (文件标识符)
                pos = fcp_data.find('83')
                if pos != -1 and pos + 6 <= len(fcp_data):
                    # 83后面是长度（1字节），然后是文件ID（2字节）
                    length_pos = pos + 2
                    length = int(fcp_data[length_pos:length_pos+2], 16)
                    
                    # 检查长度是否为2（EF ID通常是2字节）
                    if length == 2 and length_pos + 4 <= len(fcp_data):
                        file_id = fcp_data[length_pos+2:length_pos+6]
                        return file_id
            return None
        except Exception:
            return None
        
    def parse(self, msg) -> ParseNode:
        """解析SIM APDU消息"""
        hdr = parse_apdu_header(msg.raw)
        
        # 判断方向：UE->SIM 还是 SIM->UE
        if self._is_ue_to_sim(msg.raw, hdr):
            return self._parse_ue_to_sim(msg.raw, hdr)
        else:
            return self._parse_sim_to_ue(msg.raw, hdr)
    
    def _is_ue_to_sim(self, raw: str, hdr: Apdu) -> bool:
        """判断是否为UE->SIM方向"""
        # UE->SIM的特征：
        # 1. 有完整的APDU头部（CLA, INS, P1, P2）
        # 2. 不是以62或6F开头的FCP响应
        # 3. 不是状态码（90xx, 6xxx等）
        # 4. INS在ue_to_sim_commands字典中
        
        if len(raw) < 8:  # 至少需要4字节头部
            return False
            
        if raw.startswith("62") or raw.startswith("6F"):  # FCP响应
            return False
            
        # 检查是否为状态码
        if len(raw) == 4:
            status = int(raw, 16)
            if status in self.sim_to_ue_status:
                return False
        
        # 检查INS是否在UE->SIM命令字典中
        if hdr.ins is not None and hdr.ins in self.ue_to_sim_commands:
            return True
            
        return False
    
    def _parse_ue_to_sim(self, raw: str, hdr: Apdu) -> ParseNode:
        """解析UE->SIM的APDU"""
        root = ParseNode(name="UE->SIM APDU")
        
        # 解析APDU头部
        header_node = ParseNode(name="APDU Header")
        header_node.children.append(ParseNode(name="CLA", value=f"0x{hdr.cla:02X}" if hdr.cla is not None else "N/A"))
        header_node.children.append(ParseNode(name="INS", value=f"0x{hdr.ins:02X}" if hdr.ins is not None else "N/A"))
        header_node.children.append(ParseNode(name="P1", value=f"0x{hdr.p1:02X}" if hdr.p1 is not None else "N/A"))
        header_node.children.append(ParseNode(name="P2", value=f"0x{hdr.p2:02X}" if hdr.p2 is not None else "N/A"))
        
        if hdr.lc is not None:
            header_node.children.append(ParseNode(name="Lc", value=f"0x{hdr.lc:02X}"))
        if hdr.le is not None:
            header_node.children.append(ParseNode(name="Le", value=f"0x{hdr.le:02X}"))
            
        root.children.append(header_node)
        
        # 解析指令名称
        if hdr.ins is not None:
            command_name = self.ue_to_sim_commands.get(hdr.ins, f"Unknown Command (0x{hdr.ins:02X})")
            command_node = ParseNode(name="Command", value=command_name)
            root.children.append(command_node)
            
            # 根据具体指令添加详细解析
            self._parse_command_details(root, hdr, raw)
        
        # 解析数据部分
        if hdr.data_hex:
            data_node = ParseNode(name="Data", value=hdr.data_hex)
            root.children.append(data_node)
        
        return root
    
    def _parse_command_details(self, root: ParseNode, hdr: Apdu, raw: str):
        """根据具体指令解析详细信息"""
        if hdr.ins == 0xA4:  # SELECT FILE
            self._parse_select_file(root, hdr, raw)
        elif hdr.ins == 0xB0:  # READ BINARY
            self._parse_read_binary(root, hdr, raw)
        elif hdr.ins == 0xB2:  # READ RECORD
            self._parse_read_record(root, hdr, raw)
        elif hdr.ins == 0x20:  # VERIFY PIN
            self._parse_verify_pin(root, hdr, raw)
        elif hdr.ins == 0x88 or hdr.ins == 0x89:  # AUTHENTICATE
            self._parse_authenticate(root, hdr, raw)
        elif hdr.ins == 0xC0:  # GET RESPONSE
            self._parse_get_response(root, hdr, raw)
        elif hdr.ins == 0x70:  # MANAGE CHANNEL
            self._parse_manage_channel(root, hdr, raw)
    
    def _parse_select_file(self, root: ParseNode, hdr: Apdu, raw: str):
        """解析SELECT FILE指令"""
        details = ParseNode(name="SELECT FILE Details")
        
        # P1参数解析
        if hdr.p1 == 0x00:
            details.children.append(ParseNode(name="Selection Mode", value="Select by file ID"))
        elif hdr.p1 == 0x01:
            details.children.append(ParseNode(name="Selection Mode", value="Select parent DF"))
        elif hdr.p1 == 0x03:
            details.children.append(ParseNode(name="Selection Mode", value="Select by DF name"))
        elif hdr.p1 == 0x04:
            details.children.append(ParseNode(name="Selection Mode", value="Select from EF"))
        elif hdr.p1 == 0x08:
            details.children.append(ParseNode(name="Selection Mode", value="Select by path"))
        elif hdr.p1 == 0x09:
            details.children.append(ParseNode(name="Selection Mode", value="Select by path (first occurrence)"))
        
        # P2参数解析
        if hdr.p2 == 0x00:
            details.children.append(ParseNode(name="Return Mode", value="No response data"))
        elif hdr.p2 == 0x01:
            details.children.append(ParseNode(name="Return Mode", value="Return FCP"))
        elif hdr.p2 == 0x02:
            details.children.append(ParseNode(name="Return Mode", value="Return FMD"))
        elif hdr.p2 == 0x03:
            details.children.append(ParseNode(name="Return Mode", value="Return FCP and FMD"))
        
        # 文件ID或AID解析
        if hdr.data_hex and len(hdr.data_hex) >= 4:
            data_length = len(hdr.data_hex) // 2  # 转换为字节数
            
            if data_length > 6:
                # 长度大于6字节，解析为AID
                aid = hdr.data_hex
                details.children.append(ParseNode(name="AID", value=f"0x{aid}"))
                details.children.append(ParseNode(name="AID Length", value=f"{data_length} bytes"))
                details.children.append(ParseNode(name="Type", value="Application Identifier"))
            else:
                # 长度小于等于6字节，解析为文件ID
                # 如果数据长度大于2个字节，取数据部分的最后两个字节作为EF ID
                if data_length > 2:
                    # 从hdr.data_hex中取最后两个字节作为文件ID
                    file_id = hdr.data_hex[-4:]  # 最后4个字符（2个字节）
                else:
                    # 正常情况，取前两个字节
                    file_id = hdr.data_hex[:4]
                
                details.children.append(ParseNode(name="File ID", value=f"0x{file_id}"))
                
                # 获取文件名
                file_name = self._get_file_name(file_id)
                details.children.append(ParseNode(name="File Name", value=file_name))
        
        root.children.append(details)
    
    def _parse_read_binary(self, root: ParseNode, hdr: Apdu, raw: str):
        """解析READ BINARY指令"""
        details = ParseNode(name="READ BINARY Details")
        
        # P1参数解析（文件偏移高字节）
        if hdr.p1 is not None:
            details.children.append(ParseNode(name="Offset High Byte", value=f"0x{hdr.p1:02X}"))
        
        # P2参数解析（文件偏移低字节）
        if hdr.p2 is not None:
            details.children.append(ParseNode(name="Offset Low Byte", value=f"0x{hdr.p2:02X}"))
            offset = hdr.p1 * 256 + hdr.p2 if hdr.p1 is not None else hdr.p2
            details.children.append(ParseNode(name="File Offset", value=f"{offset} bytes"))
        
        # Le参数解析（要读取的字节数）
        if hdr.le is not None:
            details.children.append(ParseNode(name="Read Length", value=f"{hdr.le} bytes"))
        
        root.children.append(details)
    
    def _parse_read_record(self, root: ParseNode, hdr: Apdu, raw: str):
        """解析READ RECORD指令"""
        details = ParseNode(name="READ RECORD Details")
        
        # P1参数解析
        if hdr.p1 == 0x00:
            details.children.append(ParseNode(name="Record Mode", value="Read current record"))
        elif hdr.p1 == 0x01:
            details.children.append(ParseNode(name="Record Mode", value="Read first record"))
        elif hdr.p1 == 0x02:
            details.children.append(ParseNode(name="Record Mode", value="Read last record"))
        elif hdr.p1 == 0x03:
            details.children.append(ParseNode(name="Record Mode", value="Read next record"))
        elif hdr.p1 == 0x04:
            details.children.append(ParseNode(name="Record Mode", value="Read previous record"))
        elif hdr.p1 == 0x05:
            details.children.append(ParseNode(name="Record Mode", value="Read record by number"))
        
        # P2参数解析
        if hdr.p2 is not None:
            details.children.append(ParseNode(name="Record Number", value=f"{hdr.p2}"))
        
        # Le参数解析
        if hdr.le is not None:
            details.children.append(ParseNode(name="Read Length", value=f"{hdr.le} bytes"))
        
        root.children.append(details)
    
    def _parse_verify_pin(self, root: ParseNode, hdr: Apdu, raw: str):
        """解析VERIFY PIN指令"""
        details = ParseNode(name="VERIFY PIN Details")
        
        # P1参数解析
        if hdr.p1 == 0x00:
            details.children.append(ParseNode(name="PIN Type", value="PIN1"))
        elif hdr.p1 == 0x01:
            details.children.append(ParseNode(name="PIN Type", value="PIN2"))
        elif hdr.p1 == 0x02:
            details.children.append(ParseNode(name="PIN Type", value="ADM1"))
        elif hdr.p1 == 0x03:
            details.children.append(ParseNode(name="PIN Type", value="ADM2"))
        elif hdr.p1 == 0x04:
            details.children.append(ParseNode(name="PIN Type", value="ADM3"))
        elif hdr.p1 == 0x05:
            details.children.append(ParseNode(name="PIN Type", value="ADM4"))
        elif hdr.p1 == 0x06:
            details.children.append(ParseNode(name="PIN Type", value="ADM5"))
        elif hdr.p1 == 0x07:
            details.children.append(ParseNode(name="PIN Type", value="ADM6"))
        
        # P2参数解析
        if hdr.p2 == 0x00:
            details.children.append(ParseNode(name="PIN Format", value="BCD format"))
        elif hdr.p2 == 0x01:
            details.children.append(ParseNode(name="PIN Format", value="ASCII format"))
        
        # Lc参数解析
        if hdr.lc is not None:
            details.children.append(ParseNode(name="PIN Length", value=f"{hdr.lc} bytes"))
        
        root.children.append(details)
    
    def _parse_authenticate(self, root: ParseNode, hdr: Apdu, raw: str):
        """解析AUTHENTICATE指令"""
        details = ParseNode(name="AUTHENTICATE Details")
        
        # INS参数解析
        if hdr.ins == 0x88:
            details.children.append(ParseNode(name="Authentication Type", value="GSM Authentication"))
        elif hdr.ins == 0x89:
            details.children.append(ParseNode(name="Authentication Type", value="UMTS Authentication"))
        
        # P1参数解析
        if hdr.p1 is not None:
            details.children.append(ParseNode(name="P1", value=f"0x{hdr.p1:02X}"))
        
        # P2参数解析
        if hdr.p2 is not None:
            details.children.append(ParseNode(name="P2", value=f"0x{hdr.p2:02X}"))
        
        # Lc参数解析
        if hdr.lc is not None:
            details.children.append(ParseNode(name="Challenge Length", value=f"{hdr.lc} bytes"))
        
        root.children.append(details)
    
    def _parse_get_response(self, root: ParseNode, hdr: Apdu, raw: str):
        """解析GET RESPONSE指令"""
        details = ParseNode(name="GET RESPONSE Details")
        
        # P1参数解析
        if hdr.p1 is not None:
            details.children.append(ParseNode(name="P1", value=f"0x{hdr.p1:02X}"))
        
        # P2参数解析
        if hdr.p2 is not None:
            details.children.append(ParseNode(name="P2", value=f"0x{hdr.p2:02X}"))
        
        # Le参数解析
        if hdr.le is not None:
            details.children.append(ParseNode(name="Expected Length", value=f"{hdr.le} bytes"))
        
        root.children.append(details)
    
    def _parse_manage_channel(self, root: ParseNode, hdr: Apdu, raw: str):
        """解析MANAGE CHANNEL指令"""
        details = ParseNode(name="MANAGE CHANNEL Details")
        
        # P1参数解析
        if hdr.p1 is not None:
            if hdr.p1 == 0x00:
                details.children.append(ParseNode(name="Operation", value="Open channel"))
            elif hdr.p1 == 0x01:
                details.children.append(ParseNode(name="Operation", value="Close channel"))
            elif hdr.p1 == 0x02:
                details.children.append(ParseNode(name="Operation", value="Get channel status"))
            elif hdr.p1 == 0x80:
                details.children.append(ParseNode(name="Operation", value="Close channel"))
            else:
                details.children.append(ParseNode(name="Operation", value=f"Unknown operation (0x{hdr.p1:02X})"))
        
        # P2参数解析（Channel number）
        if hdr.p2 is not None:
            if hdr.p2 == 0x00:
                details.children.append(ParseNode(name="Channel Number", value="Basic channel (0)"))
            else:
                details.children.append(ParseNode(name="Channel Number", value=f"Channel {hdr.p2}"))
        
        # Le参数解析
        if hdr.le is not None:
            details.children.append(ParseNode(name="Expected Length", value=f"{hdr.le} bytes"))
        
        root.children.append(details)
    
    def _parse_sim_to_ue(self, raw: str, hdr: Apdu) -> ParseNode:
        """解析SIM->UE的APDU"""
        root = ParseNode(name="SIM->UE APDU")
        
        # 检查是否为FCP响应
        if raw.startswith("62"):
            # 尝试从FCP数据中提取文件ID
            file_id = self._extract_file_id_from_fcp(raw)
            if file_id:
                file_name = self._get_file_name(file_id)
                fcp_node = ParseNode(name=f"FCP_{file_name}")
            else:
                fcp_node = ParseNode(name="FCP (File Control Parameters)")
            
            try:
                fcp_data = parse_fcp_data(raw)
                if isinstance(fcp_data, dict):
                    # 解析FCP数据
                    for key, value in fcp_data.items():
                        fcp_node.children.append(ParseNode(name=key, value=str(value)))
                else:
                    fcp_node.children.append(ParseNode(name="FCP Data", value=str(fcp_data)))
            except Exception as e:
                fcp_node.children.append(ParseNode(name="FCP Parse Error", value=str(e)))
            root.children.append(fcp_node)
        else:
            # 解析状态码
            if len(raw) == 4:
                status = int(raw, 16)
                status_node = ParseNode(name="Status Code")
                status_node.children.append(ParseNode(name="SW1", value=f"0x{raw[:2]}"))
                status_node.children.append(ParseNode(name="SW2", value=f"0x{raw[2:]}"))
                
                status_desc = self.sim_to_ue_status.get(status, "Unknown Status")
                status_node.children.append(ParseNode(name="Description", value=status_desc))
                
                root.children.append(status_node)
            else:
                # 其他响应数据
                data_node = ParseNode(name="Response Data", value=raw)
                root.children.append(data_node)
        
        return root
