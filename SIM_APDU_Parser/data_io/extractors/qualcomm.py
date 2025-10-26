import re
from typing import List, Tuple

from SIM_APDU_Parser.core.models import Message
from SIM_APDU_Parser.core.utils import normalize_hex


class QualcommExtractor:
    """
    提取高通APDU日志中的RX Data和TX Data消息。
    - 提取"RX Data = {"和"TX Data = {"开头的行
    - 去掉括号和空格，只保留十六进制数据
    - RX Data如果第一个字节是C0或12，去掉第一个字节
    - 连续的TX Data消息合并在一行
    """

    def __init__(self):
        # 匹配RX Data和TX Data行的正则表达式
        self.rx_pattern = re.compile(r'^\s*RX\s+Data\s*=\s*\{\s*([0-9A-Fa-f\s]*)\s*\}\s*$')
        self.tx_pattern = re.compile(r'^\s*TX\s+Data\s*=\s*\{\s*([0-9A-Fa-f\s]*)\s*\}\s*$')

    def extract_from_text(self, text: str) -> List[Message]:
        """从文本中提取高通APDU消息"""
        lines = text.splitlines()
        
        # 第一步：先提取所有RX Data和TX Data行
        extracted_lines = []
        for line in lines:
            line = line.strip()
            tx_match = self.tx_pattern.match(line)
            rx_match = self.rx_pattern.match(line)
            
            if tx_match:
                extracted_lines.append(('TX', self._clean_hex_data(tx_match.group(1))))
            elif rx_match:
                extracted_lines.append(('RX', self._clean_hex_data(rx_match.group(1))))
        
        # 第二步：在这些提取的行中判断连续性并合并
        msgs: List[Message] = []
        i = 0
        while i < len(extracted_lines):
            direction, data = extracted_lines[i]
            
            if direction == 'TX':
                # 如果当前是TX，下一个扫描到的还是TX，就需要格式化后追加到上一行的TX
                j = i + 1
                while j < len(extracted_lines) and extracted_lines[j][0] == 'TX':
                    next_data = extracted_lines[j][1]
                    if next_data:
                        data += next_data  # 追加到当前TX Data
                    j += 1
                msgs.append(Message(raw=data, direction="tx", meta={"source": "qualcomm"}))
                i = j
                
            elif direction == 'RX':
                # 如果第一个字节是C0或12，去掉第一个字节
                data = self._remove_first_byte_if_needed(data)
                msgs.append(Message(raw=data, direction="rx", meta={"source": "qualcomm"}))
                i += 1
        
        return msgs

    def _clean_hex_data(self, hex_str: str) -> str:
        """清理十六进制数据，去掉空格并规范化"""
        if not hex_str:
            return ""
        # 去掉所有空格
        clean_hex = hex_str.replace(" ", "").replace("\t", "").replace("\n", "")
        # 使用normalize_hex进行规范化
        return normalize_hex(clean_hex)

    def _remove_first_byte_if_needed(self, hex_data: str) -> str:
        """如果第一个字节是C0或12，去掉第一个字节"""
        if not hex_data or len(hex_data) < 2:
            return hex_data
        
        # 去掉空格后检查第一个字节
        clean_data = hex_data.replace(" ", "")
        if len(clean_data) >= 2:
            first_byte = clean_data[:2].upper()
            if first_byte in ["C0", "12"]:
                # 去掉第一个字节
                return clean_data[2:]
        
        return hex_data
