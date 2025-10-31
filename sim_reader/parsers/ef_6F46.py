
"""
SIM卡服务提供商名称(SPN)文件解析模块

此模块用于解析和编码SIM卡中的服务提供商名称(Service Provider Name)信息。
数据结构包含两个字段：
    - Display Condition: 显示条件，2字节
    - Service Provider Name: 服务提供商名称，最多16字节ASCII字符

文件格式：
    - 总长度：32字节
    - Display Condition: 前2字节
    - Service Provider Name: 后30字节，使用ASCII编码，不足部分用'F'填充
"""

import logging

def parse_data(raw_data: list) -> list:
    """
    解析服务提供商名称(SPN)数据

    Args:
        raw_data (list): 原始数据列表，包含一个十六进制字符串

    Returns:
        list: 包含解析后的SPN信息的字典列表
    """
    raw_data_str = raw_data[0]
    spn_dict = {}

    # 判断是否全为F
    if all(c == 'F' for c in raw_data_str):
        spn_dict["Display Condition"] = "FF"
        spn_dict["Service Provider Name"] = "F" * 16
        return [spn_dict]

    display_condition = raw_data_str[0:2]

    spn_raw = raw_data_str[2:34].rstrip('F')
    if len(spn_raw) % 2 != 0:
        spn_raw += 'F'

    try:
        spn = bytes.fromhex(spn_raw).decode('ascii').strip()
    except Exception as e:
        logging.error("SPN解析失败: 原始数据=%s, 错误=%s", spn_raw, e)
        spn = "<Decode Error>"

    spn_dict["Display Condition"] = display_condition
    spn_dict["Service Provider Name"] = spn
    return [spn_dict]


def encode_data(user_data: dict, ef_file_len_decimal: int) -> str:
    """
    将SPN信息编码为十六进制字符串

    Args:
        user_data (dict): 包含SPN信息的字典
        ef_file_len_decimal (int): EF文件长度（十进制）

    Returns:
        str: 编码后的十六进制字符串，如果发生错误则返回错误信息
    """
    try:
        encode_userdata = ""
        display_condition = user_data.get("Display Condition", "FF")
        spn = user_data.get("Service Provider Name", "F" * 16)

        # 验证显示条件
        try:
            encoded_display_condition = f"{int(display_condition, 16):02X}"
        except ValueError:
            return "error: Display Condition 不是有效的十六进制数"

        encode_userdata += encoded_display_condition

        try:
            encoded_spn = spn.encode('ascii').hex().upper()
        except Exception as e:
            logging.error("服务提供商名称编码失败: %s", e)
            return "error: Service Provider Name 含非法ASCII字符"

        if len(encoded_spn) > 32:
            return "error: Service Provider Name 长度无效"

        encoded_spn = encoded_spn.ljust(32, 'F')
        encode_userdata += encoded_spn

        if len(encode_userdata) <= ef_file_len_decimal * 2:
            encode_userdata = encode_userdata.ljust(ef_file_len_decimal * 2, 'F')
        else:
            logging.warning("SPN数据长度(%d字节)超过EF文件长度(%d字节)，将在write_data()中调整大小",
                            len(encode_userdata) // 2, ef_file_len_decimal)

        return encode_userdata

    except Exception as e:
        logging.error("SPN编码过程中发生错误: %s", str(e))
        return f"error: 错误 - {str(e)}"
