"""
    数据结构:
        {
            "EHPLMN1": "311480",
            "EHPLMN2": "310580",
            "EHPLMN3": "310580",
            "EHPLMN4": "310580"
        }
"""

import logging

def parse_data(raw_data: list) -> list:
    logging.debug("收到的数据：%s 解析函数未开发", raw_data)
    results = []
    for index, data in enumerate(raw_data):
        logging.debug("index: %s, data: %s", index, data)
        results.append({"raw_data": data})
    
    return results

def encode_data(user_data: str,ef_file_len_decimal: int) -> str:
    try:
        encode_userdata = user_data.get('raw_data', '')
        if len(encode_userdata) <= ef_file_len_decimal*2:
            # Pad with 'F' if the length is less than required
            encode_userdata = encode_userdata.ljust(ef_file_len_decimal*2, 'F')
        else:
            logging.debug("Raw data longer than current EF (%d >%d),resize in write_data()",
                          len(encode_userdata) // 2, ef_file_len_decimal)
        return encode_userdata
            
    except Exception as e:
        encode_userdata = f"error: 未知错误 - {str(e)}"
        return encode_userdata    
