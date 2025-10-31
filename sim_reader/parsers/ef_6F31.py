"""
    数据结构:
        {
            "Time interval": ""
        }


"""
import logging

def parse_data(raw_data: list) -> list:
    results = []

    # 获取Time interval 
    time_interval = raw_data[0]
    results.append({"Time interval": time_interval})
    
    return results
def encode_data(user_data: str,ef_file_len_decimal: int) -> str:
    try:
        encode_userdata = user_data.get('Time interval', '')
        if len(encode_userdata) > 2:
            return f"error: Time interval 只能1个字节（2位）"
        if len(encode_userdata) <= ef_file_len_decimal*2:
            encode_userdata = encode_userdata.ljust(ef_file_len_decimal*2, 'F')
        else:
            logging.debug("Time interval longer than current EF (%d >%d),resize in write_data()",
                          len(encode_userdata) // 2, ef_file_len_decimal)
        return encode_userdata
            
    except Exception as e:
        encode_userdata = f"error: 未知错误 - {str(e)}"
        return encode_userdata    
