"""
数据结构
{
    "5G-GUTI for non-3GPP access": "",
    "Last visited registered TAI in 5GS for non-3GPP access": "",
    "5GS update status for non-3GPP access": "",
}
""" 
import logging
def parse_data(raw_data: str) -> None:
    results = []
    raw_data = raw_data[0]
    guti = raw_data[0:26]
    last_visited_registered_tai = raw_data[26:38]
    update_status = raw_data[38:40]
    

    results.append({"5G-GUTI for non-3GPP access": guti, "Last visited registered TAI in 5GS for non-3GPP access": last_visited_registered_tai, "5GS update status for non-3GPP access": update_status})
    return results
    

def encode_data(user_data: str,ef_file_len_decimal: int) -> str:
    try:
        encoded_guti = user_data.get('5G-GUTI for non-3GPP access', '')
        if len(encoded_guti) != 26: 
            raise ValueError("5G-GUTI长度不正确")
        encoded_last_visited_registered_tai = user_data.get('Last visited registered TAI in 5GS for non-3GPP access', '')
        if len(encoded_last_visited_registered_tai) != 12:
                raise ValueError("Last visited registered TAI in 5GS for non-3GPP access长度不正确")
        encoded_update_status = user_data.get('5GS update status for non-3GPP access', '')
        if len(encoded_update_status) != 2:
            raise ValueError("5GS update status for non-3GPP access长度不正确")
        encode_userdata = encoded_guti + encoded_last_visited_registered_tai + encoded_update_status
        
        if len(encode_userdata) <= ef_file_len_decimal * 2:
            # Pad with 'F' if the length is less than required
            encode_userdata = encode_userdata.ljust(ef_file_len_decimal * 2, 'F')
        else:
            logging.debug("5G-GUTI data longer than current EF (%d >%d),resize in write_data()",
                          len(encode_userdata) // 2, ef_file_len_decimal)
        
        return encode_userdata
    except Exception as e:
        return f"error: 未知错误 - {str(e)}"


