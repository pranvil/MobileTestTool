"""
    数据结构:
        {
            "PLMN1": "",
            "Access Technology Identifier1": "",
            "PLMN2": "",
            "Access Technology Identifier2": "",
            "PLMN3": "",
            "Access Technology Identifier3": "",
            "PLMN4": "",
            "Access Technology Identifier4": ""
        }


"""

import logging
from parsers.general import decode_PLMN, encode_PLMN, decode_access_technology, encode_access_technology, encode_plmn_data

def parse_data(raw_data: list) -> list:
    results = []
    data_list = raw_data[0]

    if len(data_list) % 10 != 0:
        logging.error("数据长度错误: %s，应为10的倍数", len(data_list))
        return f"error: 数据长度异常"
    result = {}
    for i in range(0, len(data_list), 10):
        if i+10 > len(data_list):
            break
        plmn = decode_PLMN(data_list[i:i+6])
        access_tech = decode_access_technology(data_list[i+6:i+10])
        result[f"PLMN{int(i/10)+1}"] = plmn
        result[f"Access Technology Identifier{int(i/10)+1}"] = access_tech
    results.append(result)
        
    return results

def encode_data(data_dict: dict, ef_file_len_decimal: int) -> str:
    return encode_plmn_data(data_dict, ef_file_len_decimal)
