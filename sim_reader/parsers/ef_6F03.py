"""
    数据结构:
        {
            "Domain": ""
        }
"""
from parsers.general import ascii_text_to_hex, TLV_parser, TLV_encode
import logging
def parse_data(raw_data: str) -> None:
    results = []
    raw_data = raw_data[0]
    encode_userdata = TLV_parser(raw_data)
    results.append({"Domain": encode_userdata})
    return results
def encode_data(user_data: str,ef_file_len_decimal: int) -> str:
    try:
        encode_userdata = user_data.get('Domain', '')
        encode_userdata = ascii_text_to_hex(encode_userdata)        #TLV 结构Value部分
        encode_userdata = TLV_encode(encode_userdata)    
        if len(encode_userdata) <= ef_file_len_decimal * 2:
            encode_userdata = encode_userdata.ljust(ef_file_len_decimal * 2, 'F')
        else:
            logging.debug("Domain longer than current EF (%d >%d),resize in write_data()",
                          len(encode_userdata) // 2, ef_file_len_decimal)
           
        return encode_userdata
            
    except Exception as e:
        encode_userdata = f"error: 未知错误 - {str(e)}"
        return encode_userdata  