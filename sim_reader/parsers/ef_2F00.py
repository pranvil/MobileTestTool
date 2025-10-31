"""
    数据结构
        {
            "AID": "",
            "label": ""
        }
"""
import logging

def parse_data(raw_data: list) -> list:
    results = []
    for data in raw_data:
        result = {}  # 在每次循环开始时初始化 result 字典
        if data.startswith("FFFF"):
            result["AID"] = ""
            result["label"] = ""
            results.append(result)
        else:
            index = 4       #skip tag
            data_length = len(data)       
            while index < data_length:
                tag = data[index:index+2]
                index += 2  # skip tag
                length = int(data[index:index + 2], 16)  # 获取长度并将长度转换为整数        
                index += 2  # skip length
                value = data[index:index + length * 2]  # 获取值value
                index += length * 2  # skip value

                if tag == "4F":
                    result["AID"] = value  # 更新字典中的 adf
                elif tag == "50":
                    result["label"] = value  # 更新字典中的 label
                elif tag == "FF":  
                    break  # 终止循环
                else:  
                    logging.error("Unknown tag: %s", tag)  # 修正拼写错误
            results.append(result)
    return results

def encode_data(user_data: dict, ef_file_len_decimal: int) -> str:
    return f"error: DIR文件不允许写入"
    # try:
    #     aid = user_data.get("AID", "")
    #     label = user_data.get("label", "")
    #     if not aid:
    #         return "error: AID不能为空"
    #     # 组装AID TLV
    #     aid_len = len(aid) // 2
    #     if aid_len < 1 or aid_len > 16:
    #         return "error: AID长度必须为1~16字节"
    #     aid_tlv = f"4F{aid_len:02X}{aid}"
    #     # 组装label TLV（可选，支持明文或HEX）
    #     label_tlv = ""
    #     if label:
    #         # 判断label是否为HEX字符串
    #         def is_hex(s):
    #             try:
    #                 int(s, 16)
    #                 return len(s) % 2 == 0
    #             except Exception:
    #                 return False
    #         if is_hex(label):
    #             label_bytes_len = len(label) // 2
    #             if label_bytes_len > 32:
    #                 return "error: label长度不能超过32字节"
    #             label_hex = label.upper()
    #         else:
    #             label_bytes = bytes(label, "ascii")
    #             if len(label_bytes) > 32:
    #                 return "error: label长度不能超过32字节"
    #             label_hex = label_bytes.hex().upper()
    #             label_bytes_len = len(label_bytes)
    #         label_tlv = f"50{label_bytes_len:02X}{label_hex}"
    #     # 拼接内部内容
    #     inner_tlv = aid_tlv + label_tlv
    #     # 外层61 TLV
    #     inner_len = len(inner_tlv) // 2
    #     if inner_len > 127:
    #         return "error: TLV内容超长"
    #     outer_tlv = f"61{inner_len:02X}{inner_tlv}"
    #     # 补齐长度
    #     if len(outer_tlv) < ef_file_len_decimal * 2:
    #         outer_tlv = outer_tlv.ljust(ef_file_len_decimal * 2, 'F')
    #     return outer_tlv
    # except Exception as e:
    #     return f"error: 未知错误 - {str(e)}"

