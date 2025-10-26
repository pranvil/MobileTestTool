#!/usr/bin/env python3
# TERMINAL CAPABILITY 解析器

from SIM_APDU_Parser.core.models import ParseNode


class TerminalCapabilityParser:
    """TERMINAL CAPABILITY 解析器"""
    
    def parse_capability_data(self, payload_hex: str) -> ParseNode:
        """
        解析 TERMINAL CAPABILITY 数据
        
        Args:
            payload_hex: 去掉APDU头部后的数据部分
            
        Returns:
            ParseNode: 解析结果
        """
        root = ParseNode(name="TERMINAL CAPABILITY")
        
        # 解析 A9 容器标签
        if payload_hex.startswith("A9"):
            # 提取长度
            if len(payload_hex) >= 4:
                length_byte = int(payload_hex[2:4], 16)
                tlv_data = payload_hex[4:4+2*length_byte] if len(payload_hex) >= 4+2*length_byte else payload_hex[4:]
                
                # 解析子 TLV
                self._parse_tlv_data(tlv_data, root)
            else:
                root.children.append(ParseNode(name="错误", value="数据长度不足"))
        else:
            root.children.append(ParseNode(name="错误", value="不是有效的 TERMINAL CAPABILITY 数据"))
        
        return root
    
    def _parse_tlv_data(self, tlv_data: str, root: ParseNode):
        """解析 TLV 数据"""
        idx = 0
        n = len(tlv_data)
        
        while idx + 4 <= n:
            tag = tlv_data[idx:idx+2].upper()
            idx += 2
            ln = int(tlv_data[idx:idx+2], 16) if idx+2 <= n else 0
            idx += 2
            val = tlv_data[idx:idx+2*ln] if idx+2*ln <= n else ""
            idx += 2*ln
            
            # 根据标签解析
            if tag == "80":
                self._parse_terminal_power_supply(val, root)
            elif tag == "81":
                self._parse_extended_logical_channels(val, root)
            elif tag == "82":
                self._parse_additional_interfaces(val, root)
            elif tag == "83":
                self._parse_lpa_device_capabilities(val, root)
            elif tag == "84":
                self._parse_euicc_iot_capabilities(val, root)
            else:
                root.children.append(ParseNode(name=f"未知标签 ({tag})", value=val))
            
            if idx >= n:
                break
    
    def _parse_terminal_power_supply(self, val: str, root: ParseNode):
        """解析 Terminal power supply (80)"""
        if len(val) < 6:  # 至少需要3字节
            root.children.append(ParseNode(name="Terminal power supply (80)", value="数据长度不足"))
            return
        
        node = ParseNode(name="Terminal power supply (80)")
        
        # 解析第3字节：supply_voltage_class
        byte3 = val[0:2]
        voltage_class_map = {"A": "5.0V", "B": "3.0V", "C": "1.8V"}
        voltage_class = voltage_class_map.get(byte3, f"未知 ({byte3})")
        node.children.append(ParseNode(name="Supply voltage class", value=f"{byte3} ({voltage_class})"))
        
        # 解析第4字节：max_available_power_mA
        if len(val) >= 4:
            byte4 = val[2:4]
            power_mA = int(byte4, 16)
            node.children.append(ParseNode(name="Max available power", value=f"{byte4} ({power_mA} mA)"))
        
        # 解析第5字节：actual_used_clock_frequency
        if len(val) >= 6:
            byte5 = val[4:6]
            if byte5 == "FF":
                freq_info = "No clock frequency indicated"
            else:
                freq_MHz = int(byte5, 16) * 0.1
                freq_info = f"{freq_MHz} MHz"
            node.children.append(ParseNode(name="Clock frequency", value=f"{byte5} ({freq_info})"))
        
        root.children.append(node)
    
    def _parse_extended_logical_channels(self, val: str, root: ParseNode):
        """解析 Extended logical channels terminal support (81)"""
        node = ParseNode(name="Extended logical channels terminal support (81)")
        
        if len(val) == 0:
            node.children.append(ParseNode(name="支持状态", value="Terminal supports more logical channels than standard set"))
        else:
            node.children.append(ParseNode(name="支持状态", value="Non-zero length (interpreted as zero-length for forward compatibility)"))
            node.children.append(ParseNode(name="原始数据", value=val))
        
        root.children.append(node)
    
    def _parse_additional_interfaces(self, val: str, root: ParseNode):
        """解析 Additional interfaces support (82)"""
        node = ParseNode(name="Additional interfaces support (82)")
        
        if len(val) >= 2:
            byte1 = int(val[0:2], 16)
            
            # 解析位图
            uicc_clf_supported = (byte1 & 0x01) != 0
            node.children.append(ParseNode(name="UICC-CLF interface", value="Supported" if uicc_clf_supported else "Not supported"))
            
            # 检查 RFU 位
            rfu_bits = []
            for i in range(1, 8):
                if (byte1 & (1 << i)) != 0:
                    rfu_bits.append(f"b{i+1}")
            
            if rfu_bits:
                node.children.append(ParseNode(name="RFU bits set", value=", ".join(rfu_bits)))
            
            if len(val) > 2:
                node.children.append(ParseNode(name="额外数据", value=val[2:]))
        else:
            node.children.append(ParseNode(name="错误", value="数据长度不足"))
        
        root.children.append(node)
    
    def _parse_lpa_device_capabilities(self, val: str, root: ParseNode):
        """解析 LPA & Device capabilities (83)"""
        node = ParseNode(name="LPA & Device capabilities (83)")
        
        if len(val) >= 2:
            byte1 = int(val[0:2], 16)
            
            # 解析位图
            capabilities = [
                ("LUId (Local User Interface in the Device)", 0),
                ("LPDd (Local Profile Download in the Device)", 1),
                ("LDSd (Local Discovery Service in the Device)", 2),
                ("LUle based on SCWS", 3),
                ("Metadata update alerting", 4),
                ("Enterprise capability of device", 5),
                ("LUle using E4E", 6),
                ("LPR", 7)
            ]
            
            for name, bit_pos in capabilities:
                supported = (byte1 & (1 << bit_pos)) != 0
                if name == "Enterprise capability of device":
                    value = "Enterprise capable device" if supported else "Non-enterprise capable device"
                else:
                    value = "Supported" if supported else "Not supported"
                node.children.append(ParseNode(name=name, value=value))
            
            if len(val) > 2:
                node.children.append(ParseNode(name="额外数据", value=val[2:]))
        else:
            node.children.append(ParseNode(name="错误", value="数据长度不足"))
        
        root.children.append(node)
    
    def _parse_euicc_iot_capabilities(self, val: str, root: ParseNode):
        """解析 eUICC-related IoT Device Capabilities (84)"""
        node = ParseNode(name="eUICC-related IoT Device Capabilities (84)")
        
        if len(val) >= 2:
            byte1 = int(val[0:2], 16)
            
            # 解析位图
            ipad_supported = (byte1 & 0x01) != 0
            node.children.append(ParseNode(name="IPAd", value="Supported" if ipad_supported else "Not supported"))
            
            # 检查其他位（应该都是0）
            other_bits = []
            for i in range(1, 8):
                if (byte1 & (1 << i)) != 0:
                    other_bits.append(f"b{i+1}")
            
            if other_bits:
                node.children.append(ParseNode(name="非零位", value=", ".join(other_bits) + " (Not applicable)"))
            
            if len(val) > 2:
                node.children.append(ParseNode(name="额外数据", value=val[2:]))
        else:
            node.children.append(ParseNode(name="错误", value="数据长度不足"))
        
        root.children.append(node)