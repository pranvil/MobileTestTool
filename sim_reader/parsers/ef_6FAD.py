"""
    根据spec 31.102(chapter:4.2.18)解析Administrative Data数据
    1. UE operation mode 固定一个字节长度；
    2. Additional information 固定两个字节长度；
    3. Length of MNC in the IMSI 固定一个字节长度；
    4. 剩余字节RFU，长度不固定，这里不做解析
    数据结构:
        {
            "UE operation mode": "",
            "Additional information": "",
            "length of MNC in the IMSI": "",
        }
    """
import logging

# 定义模式映射在全局范围，使两个函数都能使用
mode_mapping = {
    "00": "00 - Normal operation",
    "80": "80 - Type approval operations",
    "01": "01 - Normal operation + specific facilities",
    "81": "81 - Type approval operations + specific facilities",
    "02": "02 - Maintenance (off-line)",
    "04": "04 - Cell test operation"
}

# 直接创建反向映射，避免每次创建
mode_reverse_mapping = {v: k for k, v in mode_mapping.items()}

def parse_data(raw_data: list) -> list:
    """
    解析 raw_data，提取 UE operation mode, MNC length。
    """
    if not raw_data or not isinstance(raw_data[0], str):
        raise ValueError("Invalid raw_data format. Expected a non-empty list containing a string.")
    results = []

    # 解析 UE operation mode（前 2 个字符）
    mode_byte = raw_data[0][:2]
    op_mode = mode_mapping.get(mode_byte, "RFU (Reserved for Future Use)")

    # 解析 Additional information（第 2-5 位）
    additional_info = raw_data[0][2:6]

    # 解析 MNC 长度（第 7-8 位）
    mnc_length = raw_data[0][7:8]  # 取 1 个字符
    if mnc_length not in ["0", "2", "3"]:
        mnc_length = "RFU (Reserved for Future Use)"

    results.append({
        "UE operation mode": op_mode,
        "Additional information": additional_info,
        "length of MNC in the IMSI": mnc_length
    })

    return results


def encode_data(user_data: dict, ef_file_len_decimal: int) -> str:
    """
    编码用户数据，将其转换为16进制字符串格式。
    """
    try:
        # 获取并转换 UE operation mode
        op_mode_userdata = user_data.get('UE operation mode', '')
        encoded_op_mode_userdata = mode_reverse_mapping.get(op_mode_userdata)
        if encoded_op_mode_userdata is None:
            valid_modes = "\n".join(mode_mapping.values())
            raise ValueError("Invalid mode: %s. Please enter one of:\n%s" % (op_mode_userdata, valid_modes))

        # 固定编码 Additional information（强制为 '0000'）
        encoded_additional_info_userdata = "0000"

        # 获取并检查 MNC 长度
        mnc_length_userdata = user_data.get('length of MNC in the IMSI', '').zfill(2).upper()
        if mnc_length_userdata not in {"00", "02", "03"}:
            raise ValueError(f"Invalid MNC length: {mnc_length_userdata}. Only 00, 02, 03 are allowed.")

        # 组合编码数据
        encode_userdata = encoded_op_mode_userdata + encoded_additional_info_userdata + mnc_length_userdata

        if len(encode_userdata) <= ef_file_len_decimal * 2:
            # Pad with 'F' if the length is less than required
            encode_userdata = encode_userdata.ljust(ef_file_len_decimal * 2, 'F')
        else:
            logging.debug("Administrative data longer than current EF (%d >%d),resize in write_data()",
                          len(encode_userdata) // 2, ef_file_len_decimal)

        return encode_userdata

    except Exception as e:
        logging.debug("error in encode_data: %s", e)
        return "error: encode_data failed"
