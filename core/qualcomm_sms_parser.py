#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高通SMS解析管理器
将原始十六进制文本构建为NAS SMS PCAP文件
"""

import os
from pathlib import Path
import subprocess
import time
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal


LOG_DIR = Path(r"C:\log")
TEMP_DIR = LOG_DIR / "temp"
WIRESHARK_DIR = Path(r"C:\Program Files\Wireshark")
TEXT2PCAP = WIRESHARK_DIR / "text2pcap.exe"
USER_DLTS = Path(os.path.expandvars(r"%HOMEPATH%")) / r"AppData\Roaming\Wireshark\user_dlts"


class QualcommSMSParser(QObject):
    """高通SMS解析管理器"""
    
    # 信号定义
    status_message = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 从父窗口获取语言管理器
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
    
    def tr(self, text):
        """安全地获取翻译文本"""
        return self.lang_manager.tr(text) if self.lang_manager else text
    
    def ensure_dirs(self):
        """确保目录存在"""
        LOG_DIR.mkdir(exist_ok=True)
        TEMP_DIR.mkdir(exist_ok=True)
    
    def clean_temp_txt(self):
        """清理临时txt文件"""
        for f in TEMP_DIR.glob("*.txt"):
            try:
                f.unlink()
            except:
                pass
    
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
    
    def parse_sms_multiple(self, messages):
        """
        解析多条SMS消息，生成一个包含所有消息的PCAP文件
        
        Args:
            messages: 消息列表，每个消息是字典，包含：
                - sms_type: "MO SMS" 或 "MT SMS"
                - length: 数据长度（十进制）
                - hex_data: SMS 16进制数据（字符串）
        
        Returns:
            (success: bool, message: str)
        """
        try:
            if not messages:
                raise ValueError(self.tr("消息列表不能为空"))
            
            # 1. prepare
            self.clean_temp_txt()
            self.ensure_dirs()
            
            # 2. 处理每条消息，生成NAS数据
            nas_data_list = []
            for i, msg in enumerate(messages):
                sms_type = msg['sms_type']
                length = msg['length']
                hex_data = msg['hex_data']
                
                # compact hex data
                compact = "".join(hex_data.split())
                compact = compact.replace(" ", "").replace("\t", "").replace("\n", "").replace("\r", "")
                
                if not compact:
                    raise ValueError(self.tr("消息 #{} 的十六进制数据不能为空").format(i + 1))
                
                # 验证是否为有效的十六进制
                try:
                    int(compact, 16)
                except ValueError:
                    raise ValueError(self.tr("消息 #{} 的十六进制数据格式不正确").format(i + 1))
                
                # drop last 1 byte
                if len(compact) < 2:
                    raise ValueError(self.tr("消息 #{} 的原始数据太短").format(i + 1))
                compact2 = compact[:-2]
                
                # take last L bytes
                need_chars = length * 2
                if len(compact2) < need_chars:
                    raise ValueError(self.tr("消息 #{} 的原始数据长度不足以支持给定的长度").format(i + 1))
                data = compact2[-need_chars:]
                
                # build len1/len2
                len2_hex = self.to_hex_even(length)
                len1_hex = self.to_hex_even(length + 3)
                
                # build NAS
                if sms_type == "MO SMS" or sms_type == "1":
                    nas = f"0763{len1_hex}2901{len2_hex}{data}"
                else:  # MT SMS
                    nas = f"0762{len1_hex}0901{len2_hex}{data}"
                
                nas_data_list.append(nas)
            
            # 3. 生成包含所有消息的hex.txt
            # 每条消息作为独立的数据包，从偏移量0开始
            # text2pcap会将每个从偏移量0开始的新块识别为新的数据包
            all_hex_lines = []
            for i, nas in enumerate(nas_data_list):
                hex_lines = self.make_hex_lines(nas)
                # 在第一条消息之前不需要分隔，后续消息前添加空行以便text2pcap识别新数据包
                if i > 0:
                    all_hex_lines.append("")  # 空行表示前一个数据包结束
                all_hex_lines.extend(hex_lines)
            
            (TEMP_DIR / "hex.txt").write_text("\n".join(all_hex_lines) + "\n", encoding="utf-8")
            
            # 4. write user_dlts
            USER_DLTS.parent.mkdir(parents=True, exist_ok=True)
            header = '# This file is automatically generated, DO NOT MODIFY.\n'
            dlt_line = '"User 0 (DLT=147)","nas-eps_plain","0","","0",""\n'
            USER_DLTS.write_text(header + dlt_line, encoding="utf-8")
            
            # 5. call text2pcap
            if not TEXT2PCAP.exists():
                raise FileNotFoundError(self.tr("text2pcap未找到，请确保Wireshark已安装: {}").format(TEXT2PCAP))
            
            now = datetime.now()
            pcap_name = f"SMS_Multi_{now.strftime('%H%M%S')}.pcap"
            pcap_path = TEMP_DIR / pcap_name
            
            cmd = [
                str(TEXT2PCAP),
                "-D",
                "-l", "147",
                str(TEMP_DIR / "hex.txt"),
                str(pcap_path),
            ]
            
            self.status_message.emit(self.tr("正在生成PCAP文件（包含{}条消息）...").format(len(messages)))
            result = subprocess.run(cmd, cwd=str(WIRESHARK_DIR), 
                                  capture_output=True, text=True,
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                raise RuntimeError(self.tr("text2pcap执行失败: {}").format(result.stderr))
            
            # 6. open pcap file
            time.sleep(0.2)
            os.startfile(str(pcap_path))
            time.sleep(6)
            
            # 7. clean
            self.clean_temp_txt()
            USER_DLTS.write_text(header + dlt_line, encoding="utf-8")
            
            self.status_message.emit(self.tr("SMS解析完成，PCAP文件已打开（包含{}条消息）").format(len(messages)))
            return True, self.tr("解析成功，共处理{}条消息").format(len(messages))
            
        except Exception as e:
            error_msg = str(e)
            self.status_message.emit(self.tr("SMS解析失败: {}").format(error_msg))
            return False, error_msg
    
    def parse_sms(self, sms_type: str, length: int, hex_data: str):
        """
        解析单条SMS（保留向后兼容）
        
        Args:
            sms_type: "MO SMS" 或 "MT SMS"
            length: 数据长度（十进制）
            hex_data: SMS 16进制数据（字符串，不包含空格/制表符/换行符）
        """
        return self.parse_sms_multiple([{
            'sms_type': sms_type,
            'length': length,
            'hex_data': hex_data
        }])

