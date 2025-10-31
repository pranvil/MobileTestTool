"""
    数据结构:
        {
            "PLMN": "",
            "TAC_TAI1 Low": "",
            "TAC_TAI2 High": "",
            "PNN_Identifier": ""
        }
"""
from parsers.general import encode_PLMN,decode_PLMN
import logging
def parse_data(raw_data: list) -> list:

    if not raw_data:
        logging.error("警告：收到了空数据")

    results = []
    for data in raw_data:
        # 检查数据是否全是 FF
        if data.upper() == 'FF' * (len(data) // 2):
            result = {
                "PLMN": "FFFFFF",
                "TAC_TAI1 Low": "FFFFFF",
                "TAC_TAI2 High": "FFFFFF",
                "PNN_Identifier": "FF",
            }
            results.append(result)
            continue
            
        # 处理PLMN (前3个字节)
        raw_PLMN = data[:6]  
        # 处理TAC/LAI (第4到第7个字节)
        TAC_low = int(data[6:12], 16)  # 将16进制字符串转换为10进制整数
        TAC_high = int(data[12:18], 16)  # 将16进制字符串转换为10进制整数
        # 处理PNN Identifier (最后一个字节)
        PNN_Identifier = int(data[18:20], 16)  # Convert from hexadecimal to decimal
        PLMN = decode_PLMN(raw_PLMN)
        result = {
            "PLMN": PLMN,
            "TAC_TAI1 Low": TAC_low,
            "TAC_TAI2 High": TAC_high,
            "PNN_Identifier": PNN_Identifier,
        }
        results.append(result)
    return results




def encode_data(user_data: dict, ef_file_len_decimal: int) -> str:
    input_plmn = user_data.get("PLMN", "")
    input_tac_high = user_data.get("TAC_TAI2 High", "")
    input_tac_low = user_data.get("TAC_TAI1 Low", "")  
    input_pnn_id = user_data.get("PNN_Identifier", "")

    # 检查是否全是 FF 值
    if (input_plmn.upper() == "FFFFFF" and 
        input_tac_low.upper() == "FFFFFF" and 
        input_tac_high.upper() == "FFFFFF" and 
        input_pnn_id.upper() == "FF"):
        return "F" * (ef_file_len_decimal * 2)

    # 处理 PLMN
    input_plmn = str(input_plmn).strip() 
    if not input_plmn:
        input_plmn_packed = "FFFFFF"
    elif input_plmn.upper() == "FFFFFF":
        input_plmn_packed = input_plmn.upper()
    else:
        if len(input_plmn) > 6 or len(input_plmn) < 5:
            logging.error("PLMN长度需要是5或者6位：%s", input_plmn)
            return "error: PLMN长度需要是5或者6位"
        input_plmn_packed = encode_PLMN(input_plmn)
        if len(input_plmn_packed) != 6:
            logging.error("PLMN编码错误，结果长度为%s，期望为6位", len(input_plmn_packed))
            return "error: PLMN编码长度不正确"

    # 通用处理函数
    def handle_field(input_str, required_len, field_name):
        input_str = str(input_str).strip()
        if not input_str:
            return 'F' * required_len
        elif input_str.upper().replace('F', '') == '':
            return 'F' * required_len
        else:
            try:
                hex_val = hex(int(input_str))[2:].upper()
            except ValueError:
                logging.error("%s 不是合法的10进制数：%s", field_name, input_str)
                return f"error: {field_name}不是合法的10进制数"
            if len(hex_val) > required_len:
                logging.error("%s转换后的十六进制长度超出：%s > %s", field_name, len(hex_val), required_len)
                return f"error: {field_name}长度超出限制"
            return hex_val.zfill(required_len)

    # 字段长度要求
    TAC_HEX_LEN = 6  # 3字节
    PNN_HEX_LEN = 2  # 1字节

    input_tac_low_hex = handle_field(input_tac_low, TAC_HEX_LEN, "TAC_TAI1 Low")
    if input_tac_low_hex.startswith("error"):
        return input_tac_low_hex

    input_tac_high_hex = handle_field(input_tac_high, TAC_HEX_LEN, "TAC_TAI2 High")
    if input_tac_high_hex.startswith("error"):
        return input_tac_high_hex

    input_pnn_id_hex = handle_field(input_pnn_id, PNN_HEX_LEN, "PNN_Identifier")
    if input_pnn_id_hex.startswith("error"):
        return input_pnn_id_hex

    # 拼接
    encode_data = input_plmn_packed + input_tac_low_hex + input_tac_high_hex + input_pnn_id_hex
    logging.debug("组装后的data: %s", encode_data)

    if len(encode_data) != 20:
        logging.error("数据长度不正确：当前长度为 %d 字节，只能是 10 字节", len(encode_data) // 2)
        return "error: 数据长度不正确，只能是 10 字节"

    if len(encode_data) <= ef_file_len_decimal * 2:
        encode_data = encode_data.ljust(ef_file_len_decimal * 2, 'F')
    else:
        logging.debug("PLMN TAC PNN data longer than current EF (%d > %d), resize in write_data()",
                      len(encode_data) // 2, ef_file_len_decimal)

    return encode_data
