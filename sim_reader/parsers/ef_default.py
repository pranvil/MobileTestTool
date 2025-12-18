import logging

def parse_data(raw_data: str) -> None:
    results = []
    for index, data in enumerate(raw_data):
        logging.debug("index: %s, data: %s", index, data)
        results.append({"raw_data": data})
    
    return results

def encode_data(user_data: str,ef_file_len_decimal: int) -> str:
    try:
        encode_userdata = user_data.get('raw_data', '')
        
        # 检查输入是否为空
        if not encode_userdata or not encode_userdata.strip():
            error_msg = "error: raw_data 为空，无法写入。请先读取数据或输入有效的十六进制数据"
            logging.error("[ef_default.encode_data] %s", error_msg)
            return error_msg
        
        # 验证是否为有效的十六进制字符串
        try:
            # 移除可能的空格和分隔符
            encode_userdata = encode_userdata.replace(' ', '').replace('-', '').replace(':', '')
            # 验证是否为有效的十六进制
            int(encode_userdata, 16)
        except ValueError:
            error_msg = f"error: raw_data 不是有效的十六进制字符串: {encode_userdata}"
            logging.error("[ef_default.encode_data] %s", error_msg)
            return error_msg
        
        # 检查长度
        if len(encode_userdata) <= ef_file_len_decimal * 2:
            # Pad with 'F' if the length is less than required
            encode_userdata = encode_userdata.ljust(ef_file_len_decimal * 2, 'F')
        else:
            logging.debug("Raw data longer than current EF (%d >%d),resize in write_data()",
                          len(encode_userdata) // 2, ef_file_len_decimal)
        return encode_userdata
            
    except Exception as e:
        encode_userdata = f"error: 未知错误 - {str(e)}"
        logging.error("[ef_default.encode_data] Exception: %s", e)
        return encode_userdata    
