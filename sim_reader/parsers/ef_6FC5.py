"""
    根据spec 31.102(chapter:4.2.58)解析PNN数据
    1. 找到tag为43，45及80的记录，分别解析full name，short name及PLMN_Additional_Information
    2. decode_7bit函数对full name，short name进行解码
    3. 对PLMN_Additional_Information进行解码，解码方式涉及到UCS2编码,且为可选字段，所以需要判断是否存在，暂不开发该字段处理
    数据结构:
        {
            "Index": "",
            "Full name": "",
            "Short name": "",
            "PLMN_Additional_Information": ""
        }
"""

from parsers.general import decode_7bit, decode_ucs2, encode_7bit, encode_pnn_data
import logging

def parse_data(raw_data: list) -> list:
    if not raw_data:
        logging.debug("警告：收到了空数据")

    results = []
    
    for index, data in enumerate(raw_data):
        parsed_result = parse_single_data(data)
        parsed_result["Index"] = index + 1  # 添加索引
        results.append(parsed_result)

    return results


def parse_single_data(data: str) -> dict:
    full_name, short_name, plmn_info = "", "", ""
    i = 0
    data_length = len(data)
    while i < data_length:
        try:
            tag = data[i:i+2]   # get tag
            i += 2  # skip tag
            length_val = int(data[i:i+2], 16)  # get length
            i += 2  # skip length
            remain_len = (length_val - 1) * 2   #-1是减去Coding Byte 长度
            i += 2  # 读取 Coding Byte（当前不知道如何使用）
            value = data[i:i + remain_len]  # get value
            i += remain_len  # skip value

            # 解析 Value
            if tag == "43":
                full_name = decode_7bit(value)
            elif tag == "45":
                short_name = decode_7bit(value)
            elif tag == "80":
                plmn_info = decode_ucs2(value.zfill(len(value) + 4 - (len(value) % 4))) if len(value) % 4 != 0 else decode_ucs2(value)

        except (ValueError, IndexError):
            logging.debug("解析数据 %s 时出错", data)
            break  # 跳出当前数据的解析，进入下一个数据

    return {
        "Full name": full_name,
        "Short name": short_name,
        "PLMN_Additional_Information": plmn_info
    }


def encode_data(user_data: dict, ef_file_len_decimal: int) -> str:
    """封装 EF 6FC5 (PNN) 写卡数据。

    参数:
        user_data: {
            "Full name": str,           # 必选/可选
            "Short name": str,          # 可选
            "PLMN_Additional_Information": str  # 可选
        }
        ef_file_len_decimal: 目标 EF 记录长度 (十进制字节)

    返回:
        长度固定为 ef_file_len_decimal * 2 的 HEX 字符串，符合 TS 24.008。
    """
    logging.debug("[6FC5] encode_data() user_data=%s, len=%d", user_data, ef_file_len_decimal)

    encoded_hex = encode_pnn_data(user_data)
    if len(encoded_hex) <= ef_file_len_decimal * 2:
        encoded_hex = encoded_hex.ljust(ef_file_len_decimal * 2, 'F')
    else:
        logging.debug("PNN 数据长度(%d) > EF 容量(%d)，后续写卡时需扩容", len(encoded_hex)//2, ef_file_len_decimal)


    logging.debug("[6FC5] encoded hex (len=%d): %s", len(encoded_hex) // 2, encoded_hex.upper())
    return encoded_hex
