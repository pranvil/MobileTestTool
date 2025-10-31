"""
    数据结构:
        {
            "5GS NAS Security Context": "",
        }
"""

import logging
def parse_data(raw_data: list) -> list:
    results = []
    for index, data in enumerate(raw_data):
        results.append({"5GS NAS Security Context": data})
    
    return results
def encode_data(user_data: str,ef_file_len_decimal: int) -> str:
    try:
        encode_userdata = user_data.get('5GS NAS Security Context', '')
        if len(encode_userdata) <= ef_file_len_decimal * 2:
            # Pad with 'F' if the length is less than required
            encode_userdata = encode_userdata.ljust(ef_file_len_decimal * 2, 'F')
        else:
            logging.debug("5GS NAS Security Context longer than current EF (%d >%d),resize in write_data()",
                          len(encode_userdata) // 2, ef_file_len_decimal)
        return encode_userdata
            
    except Exception as e:
        encode_userdata = f"error: 未知错误 - {str(e)}"
        return encode_userdata    
