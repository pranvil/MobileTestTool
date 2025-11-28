#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3GPP RRC/NAS/SMS 消息解码器
支持LTE、5G、SMS三种类型的协议解码
"""

import os
from pathlib import Path
import subprocess
import time
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal


LOG_DIR = Path(r"c:\log")
TEMP_DIR = LOG_DIR / "temp"
WIRESHARK_DIR = Path(r"C:\Program Files\Wireshark")
TEXT2PCAP = WIRESHARK_DIR / "text2pcap.exe"
USER_DLTS = Path(os.path.expandvars(r"%HOMEPATH%")) / r"AppData\Roaming\Wireshark\user_dlts"


# 协议映射表
PROTOCOL_MAP = {
    'SMS': {
        'MO SMS': 'nas-eps_plain',
        'MT SMS': 'nas-eps_plain'
    },
    'LTE': {
        'lte-rrc.bcch.bch': 'lte-rrc.bcch.bch',
        'lte-rrc.bcch.dl.sch': 'lte-rrc.bcch.dl.sch',
        'lte-rrc.pcch': 'lte-rrc.pcch',
        'lte-rrc.dl.ccch': 'lte-rrc.dl.ccch',
        'lte-rrc.dl.dcch': 'lte-rrc.dl.dcch',
        'lte-rrc.ul.ccch': 'lte-rrc.ul.ccch',
        'lte-rrc.ul.dcch': 'lte-rrc.ul.dcch',
        'lte-rrc.mcch': 'lte-rrc.mcch',
        'nas-eps': 'nas-eps',
        'nas-eps_plain': 'nas-eps_plain',
    },
    '5G': {
        'nr-rrc.bcch.bch': 'nr-rrc.bcch.bch',
        'nr-rrc.bcch.dl.sch': 'nr-rrc.bcch.dl.sch',
        'nr-rrc.pcch': 'nr-rrc.pcch',
        'nr-rrc.dl.ccch': 'nr-rrc.dl.ccch',
        'nr-rrc.dl.dcch': 'nr-rrc.dl.dcch',
        'nr-rrc.ul.ccch': 'nr-rrc.ul.ccch',
        'nr-rrc.ul.dcch': 'nr-rrc.ul.dcch',
        'nas-5gs': 'nas-5gs',
    }
}


class RRC3GPPDecoder(QObject):
    """3GPP RRC/NAS/SMS 解码管理器"""
    
    # 信号定义
    status_message = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None

    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text

    def ensure_dirs(self):
        """确保目录存在"""
        LOG_DIR.mkdir(exist_ok=True)
        TEMP_DIR.mkdir(exist_ok=True)

    def clean_temp_txt(self):
        """清理临时文件"""
        for f in TEMP_DIR.glob("*.txt"):
            try:
                f.unlink()
            except Exception as e:
                self.status_message.emit(f"{self.tr('清理临时文件失败:')} {f.name} - {str(e)}")

    def to_hex_even(self, n: int) -> str:
        """十进制 -> 大写十六进制, 确保是偶数位(1位就补0)"""
        h = format(n, "X").upper()
        if len(h) % 2 == 1:
            h = "0" + h
        return h

    def make_hex_lines(self, full_hex: str):
        """生成和bat一样的hex.txt格式"""
        per_line = 32  # 16 bytes
        total = len(full_hex)
        rows = total // per_line + (1 if total % per_line else 0)
        code = "0123456789ABCDEF"
        lines = []
        last_off = "0"
        for n in range(rows):
            start = n * per_line
            chunk = full_hex[start:start+per_line]
            # split to bytes
            bytes_list = [chunk[i:i+2] for i in range(0, len(chunk), 2)]
            bytes_part = " ".join(bytes_list)
            # offset = n -> hex (no leading 0)
            off_hex = ""
            tmp = n
            while True:
                r = tmp % 16
                off_hex = code[r] + off_hex
                tmp //= 16
                if tmp == 0:
                    break
            last_off = off_hex
            lines.append(f"00{off_hex}0 {bytes_part}")
        # final offset line
        lines.append(last_off)
        return lines

    def process_sms_data(self, hex_data: str, sms_type: str, length: int) -> str:
        """
        处理SMS数据，构建NAS消息
        返回：完整的NAS十六进制字符串
        """
        # compact hex data
        compact = "".join(hex_data.split())
        compact = compact.replace(" ", "").replace("\t", "").replace("\n", "").replace("\r", "")
        
        # drop last 1 byte
        if len(compact) < 2:
            raise ValueError(self.tr("原始数据太短"))
        compact2 = compact[:-2]
        
        # take last L bytes
        need_chars = length * 2
        if len(compact2) < need_chars:
            raise ValueError(self.tr("原始数据长度不足以支持给定的长度"))
        data = compact2[-need_chars:]
        
        # build len1/len2
        len2_hex = self.to_hex_even(length)
        len1_hex = self.to_hex_even(length + 3)
        
        # build NAS
        if sms_type == "MO SMS" or sms_type == "1":
            nas = f"0763{len1_hex}2901{len2_hex}{data}"
        else:  # MT SMS
            nas = f"0762{len1_hex}0901{len2_hex}{data}"
        
        return nas

    def decode_messages(self, messages):
        """
        解码多条3GPP消息，生成一个包含所有消息的PCAP文件
        
        Args:
            messages: 消息列表，每个消息是字典，包含：
                - technology: "LTE", "5G", 或 "SMS"
                - protocol: 协议名称（如 "MO SMS", "LTE-RRC.DL.DCCH" 等）
                - length: 数据长度（仅SMS需要，其他为None）
                - hex_data: 16进制数据（字符串）
        
        Returns:
            (success: bool, message: str)
        """
        try:
            if not messages:
                raise ValueError(self.tr("消息列表不能为空"))
            
            # 1. prepare
            self.clean_temp_txt()
            self.ensure_dirs()
            
            # 2. 处理每条消息
            nas_data_list = []
            for i, msg in enumerate(messages):
                technology = msg['technology']
                protocol = msg['protocol']
                hex_data = msg['hex_data']
                
                # 验证十六进制数据
                compact = "".join(hex_data.split())
                compact = compact.replace(" ", "").replace("\t", "").replace("\n", "").replace("\r", "")
                
                if not compact:
                    raise ValueError(self.tr("消息 #{} 的十六进制数据不能为空").format(i + 1))
                
                try:
                    int(compact, 16)
                except ValueError:
                    raise ValueError(self.tr("消息 #{} 的十六进制数据格式不正确").format(i + 1))
                
                # 根据技术类型处理数据
                if technology == "SMS":
                    length = msg.get('length')
                    if not length:
                        raise ValueError(self.tr("消息 #{} SMS类型必须提供数据长度").format(i + 1))
                    nas = self.process_sms_data(compact, protocol, length)
                else:
                    # LTE和5G：直接使用原始数据
                    nas = compact
                
                nas_data_list.append(nas)
            
            # 3. 按协议分组消息（相同协议的消息合并到一个PCAP）
            if not TEXT2PCAP.exists():
                raise FileNotFoundError(self.tr("text2pcap未找到，请确保Wireshark已安装: {}").format(TEXT2PCAP))
            
            now = datetime.now()
            header = '# This file is automatically generated, DO NOT MODIFY.\n'
            USER_DLTS.parent.mkdir(parents=True, exist_ok=True)
            
            # 按协议分组：key为(technology, protocol)，value为消息索引列表
            protocol_groups = {}
            for i, msg in enumerate(messages):
                key = (msg['technology'], msg['protocol'])
                if key not in protocol_groups:
                    protocol_groups[key] = []
                protocol_groups[key].append(i)
            
            pcap_paths = []
            pcap_protocols = []  # 保存每个PCAP文件对应的协议信息
            group_index = 0
            
            # 为每个协议组生成一个PCAP文件
            for (technology, protocol_key), indices in protocol_groups.items():
                group_index += 1
                
                # 获取该协议组的Wireshark协议名称
                if technology in PROTOCOL_MAP and protocol_key in PROTOCOL_MAP[technology]:
                    wireshark_protocol = PROTOCOL_MAP[technology][protocol_key]
                else:
                    wireshark_protocol = protocol_key.lower().replace('-', '-').replace('_', '-')
                
                # 设置user_dlts（生成PCAP时需要）
                dlt_line = f'"User 0 (DLT=147)","{wireshark_protocol}","0","","0",""\n'
                USER_DLTS.write_text(header + dlt_line, encoding="utf-8")
                
                # 合并该协议组内所有消息的hex数据
                all_hex_lines = []
                for idx, i in enumerate(indices):
                    nas = nas_data_list[i]
                    hex_lines = self.make_hex_lines(nas)
                    if idx > 0:
                        all_hex_lines.append("")  # 空行表示前一个数据包结束
                    all_hex_lines.extend(hex_lines)
                
                (TEMP_DIR / "hex.txt").write_text("\n".join(all_hex_lines) + "\n", encoding="utf-8")
                
                # 生成PCAP文件
                if len(protocol_groups) == 1:
                    # 只有一个协议组，使用简单文件名
                    pcap_name = f"3GPP_{now.strftime('%H%M%S')}.pcap"
                else:
                    # 多个协议组，使用带索引的文件名
                    pcap_name = f"3GPP_{now.strftime('%H%M%S')}_{group_index}.pcap"
                pcap_path = TEMP_DIR / pcap_name
                
                # 保存PCAP路径和对应的协议信息
                pcap_protocols.append((pcap_path, dlt_line))
                
                cmd = [
                    str(TEXT2PCAP),
                    "-D",
                    "-l", "147",
                    str(TEMP_DIR / "hex.txt"),
                    str(pcap_path),
                ]
                
                self.status_message.emit(self.tr("正在生成PCAP文件（协议组 {}/{}，包含{}条消息）...").format(
                    group_index, len(protocol_groups), len(indices)))
                result = subprocess.run(cmd, cwd=str(WIRESHARK_DIR), 
                                      capture_output=True, text=True,
                                      creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                
                if result.returncode != 0:
                    raise RuntimeError(self.tr("text2pcap执行失败（协议组 {}）: {}").format(group_index, result.stderr))
                
                pcap_paths.append(pcap_path)
            
            # 打开所有PCAP文件（在打开每个文件前设置对应的协议）
            time.sleep(0.5)  # 初始延迟
            
            for pcap_path, dlt_line in pcap_protocols:
                # 在打开文件前设置对应的user_dlts
                USER_DLTS.write_text(header + dlt_line, encoding="utf-8")
                time.sleep(0.3)  # 延迟，确保user_dlts写入完成
                
                # 打开文件
                os.startfile(str(pcap_path))
                
                # 等待Wireshark读取user_dlts并打开文件
                # 增加延迟，确保Wireshark有足够时间读取user_dlts
                time.sleep(2.0)  # 延迟2秒
            
            time.sleep(3)  # 最终延迟
            
            # 清理
            self.clean_temp_txt()
            # 保留最后一个协议的user_dlts设置
            if pcap_protocols:
                USER_DLTS.write_text(header + pcap_protocols[-1][1], encoding="utf-8")
            
            if len(protocol_groups) == 1:
                self.status_message.emit(self.tr("3GPP消息解码完成，PCAP文件已打开（包含{}条消息）").format(len(messages)))
                return True, self.tr("解码成功，共处理{}条消息").format(len(messages))
            else:
                self.status_message.emit(self.tr("3GPP消息解码完成，已打开{}个PCAP文件（按协议分组）").format(len(pcap_paths)))
                return True, self.tr("解码成功，共处理{}条消息，生成了{}个PCAP文件（按协议分组）").format(len(messages), len(pcap_paths))
            
        except Exception as e:
            error_msg = str(e)
            self.status_message.emit(self.tr("3GPP消息解码失败: {}").format(error_msg))
            return False, error_msg

