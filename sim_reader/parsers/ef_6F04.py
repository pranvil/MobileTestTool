"""
    数据结构，线性文件:
        [{
            "IMPU": ""
        }]
    """
from parsers.general import TLV_parser, TLV_encode, ascii_text_to_hex
import logging

def parse_data(raw_data: list) -> list:
    logging.debug("收到的数据：%s", raw_data)
    results = []
    for index, data in enumerate(raw_data):
        decoded_data = TLV_parser(data)
        results.append({"IMPU": decoded_data})

    return results

def encode_data(user_data: str,ef_file_len_decimal: int) -> str:
    try:
        encode_userdata = user_data.get('IMPU', '')
        encode_userdata = ascii_text_to_hex(encode_userdata)        #TLV 结构Value部分
        encode_userdata = TLV_encode(encode_userdata)  
        if len(encode_userdata) <= ef_file_len_decimal * 2:
            encode_userdata = encode_userdata.ljust(ef_file_len_decimal * 2, 'F')
        else:
            logging.debug("IMPU longer than current EF (%d >%d),resize in write_data()",
                          len(encode_userdata) // 2, ef_file_len_decimal)
             
        return encode_userdata
            
    except Exception as e:
        encode_userdata = "error: 未知错误 - %s" % str(e)
        return encode_userdata   