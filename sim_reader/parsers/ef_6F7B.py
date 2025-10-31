"""
    数据结构:
        {
            "FPLMN1": "311480",
            "FPLMN2": "310580",
            "FPLMN3": "310580",
            "FPLMN4": "310580"
        }
"""

from parsers.general import encode_PLMN
import logging

def parse_data(raw_data: list) -> list:
    logging.debug("Received Data: %s", raw_data)
    
    # Extract the first value from the list
    raw_data_str = raw_data[0]
    
    # Ensure data length is a multiple of 6 hex characters (3 bytes)
    if len(raw_data_str) % 6 != 0:
        logging.debug("error: Invalid data length")
        return []
    
    fplmn_dict = {}
    fplmn_count = 1
    
    for i in range(0, len(raw_data_str), 6):
        entry = raw_data_str[i:i+6]
        
        # Check if entry is an unused entry (FF FF FF)
        if entry.upper() == "FFFFFF":
            fplmn_dict[f"FPLMN{fplmn_count}"] = "FFFFFF"
            fplmn_count += 1
            continue
        
        # Decode MCC and MNC based on 3GPP encoding
        mcc = entry[1] + entry[0] + entry[3]  # Rearranged MCC
        mnc = entry[5] + entry[4]  # Rearranged MNC
        
        # Check if MNC is 2-digit (0xF is used as padding)
        if entry[2] != 'F':
            mnc = mnc + entry[2]
        
        # Combine MCC and MNC
        fplmn_code = mcc + mnc
        
        fplmn_dict[f"FPLMN{fplmn_count}"] = fplmn_code
        fplmn_count += 1
    
    logging.debug("FPLMN dict: %s", fplmn_dict)
    return [fplmn_dict]

def encode_data(user_data: dict, ef_file_len_decimal: int) -> str:
    try:
        encode_userdata = ""
        
        for key, value in user_data.items():
            # Handle empty or None values
            if not value or value.strip() == "":
                encode_userdata += "FFFFFF"
                continue
                
            # Check if the length of value is 5 or 6
            if len(value) not in [5, 6]:
                logging.debug("错误：%s", value)
                return f"error: {key} 的长度无效"
            
            # Encode each PLMN value
            encoded_plmn = encode_PLMN(value)
            encode_userdata += encoded_plmn
        
        if len(encode_userdata) <= ef_file_len_decimal * 2:
            # Pad with 'F' if the length is less than required
            encode_userdata = encode_userdata.ljust(ef_file_len_decimal * 2, 'F')
        else:
            logging.debug("FPLMN list longer than current EF (%d >%d),resize in write_data()",
                          len(encode_userdata) // 2, ef_file_len_decimal)
    
        return encode_userdata
            
    except Exception as e:
        return f"error: 错误 - {str(e)}"    
