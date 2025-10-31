"""
数据结构
 {
    "Alpha Identifier": "Line 1",
    "TON_Type of number": "International Number (国际号码)",
    "NPI_Numbering plan identification": "ISDN/E.164 (国际电话编号计划)",
    "Dialing Number/SSC String": "19496486114"
 }
"""
import re
import logging

def get_number_type_info(ton_npi_value: str):
    """解析TON和NPI值并返回对应的描述"""
    ton_types = {
        '8': "Unknown (未知)",
        '9': "International Number (国际号码)",
        'A': "National Number (国家号码)",
        'B': "Network-Specific Number (网络专用号码)",
        'C': "Subscriber Number (订户号码)",
        'D': "Alphanumeric Number (字母数字号码)",
        'E': "Abbreviated Number (缩短号码)",
        'F': ""
    }
    
    npi_types = {
        '0': "Unknown (未知)",
        '1': "ISDN/E.164 (国际电话编号计划)",
        '3': "Data Numbering Plan, X.121 (数据编号计划)",
        '4': "Telex Numbering Plan (Telex 编号计划)",
        '6': "Land Mobile Numbering Plan (陆地移动编号计划)",
        '8': "Private Numbering Plan (国家特定编号计划)",
        'F': ""
    }
    
    if len(ton_npi_value) != 2:
        return "无效TON类型", "无效NPI类型"
        
    ton_value = ton_npi_value[0].upper()  # 转换为大写以统一处理
    npi_value = ton_npi_value[1]
    
    ton_description = ton_types.get(ton_value, "未定义的TON类型")
    npi_description = npi_types.get(npi_value, "未定义的NPI类型")
    
    return ton_description, npi_description

def parse_data(raw_data: list) -> list:
    """
    根据spec 31.102(chapter:4.2.26)解析MSISDN数据,主要构成:Alpha Identifier,TON/NPI,Dialing Number/SSC String
    1. 移除填充位F
    2. 存在变量X，所以需要倒着取数据，取到倒数第14个字节之前的所有数据（Alpha Identifier ），移除F后，如果长度为奇数，补充一个F
    3. 从末尾开始处理MDN相关数据，第14个字节是length，第13个字节是ton_npi
    4. 对MDN数据每个字节内的数字进行交换
    5. 只有当最后一个字符是'F'时才移除
    Returns:
        输出字典类型
    """    


    if not raw_data:
        logging.error("警告：收到了空数据")
        return []

    results = []
    for i, data_block in enumerate(raw_data):
        try:
            # 计算 Alpha Identifier 长度
            alpha_identifier_length = len(data_block) - 28  # 总长度 - 固定14字节
            if alpha_identifier_length < 0:
                logging.error("error：数据块 %s 长度异常", i+1)
                continue

            # 提取 Alpha Identifier
            alpha_hex = data_block[:alpha_identifier_length]
            alpha_hex = re.sub(r'[Ff]+$', '', alpha_hex)  # 去除末尾 F
            if len(alpha_hex) % 2 != 0:
                alpha_hex += 'F'
            try:
                alpha_text = bytes.fromhex(alpha_hex).decode('ascii', errors='replace') if alpha_hex else ""
            except Exception as e:
                logging.error("文本解析错误: %s, 问题字符串: %s", e, alpha_hex)
                alpha_text = "解析错误"

            # 解析固定部分的字段
            length = int(data_block[alpha_identifier_length:alpha_identifier_length+2], 16)  # X+1 (长度字节)
            ton_npi = data_block[alpha_identifier_length+2:alpha_identifier_length+4]  # X+2 (TON/NPI)

            # 获取 TON 和 NPI 解析信息
            ton_description, npi_description = get_number_type_info(ton_npi)

            # 解析 MDN (电话号码)
            dialing_hex = data_block[alpha_identifier_length+4:alpha_identifier_length+4+(length-1)*2]
            dialing_number = parse_dialing_number(dialing_hex)

            result = {
                "Alpha Identifier": alpha_text,
                "TON_Type of number": ton_description,
                "NPI_Numbering plan identification": npi_description,
                "Dialing Number/SSC String": dialing_number,
            }
            results.append(result)

        except Exception as e:
            logging.error("解析数据 %s 失败: %s", i+1, e)
    logging.debug("解析结果：%s", results)
    return results

def parse_dialing_number(hex_str: str) -> str:
    """解析 BCD 编码的电话号码"""
    if not hex_str:
        return ""
    # 交换每两个字符（因为 BCD 编码存储顺序不同）
    swapped_number = ''.join(hex_str[i+1] + hex_str[i] for i in range(0, len(hex_str)-1, 2))  
    return swapped_number.rstrip('F')   # 如果末尾是 'F'，则去除

def prompt():
    return "MSISDN按国际号码格式输入，如:19492861669" 


def encode_data(user_data: dict, ef_file_len_decimal: int) -> str:
    logging.debug("6FC5:encode_data数据: %s, ef_file_len_decimal: %s", user_data, ef_file_len_decimal)

    if user_data:
        # 编码 Alpha Identifier 
        alpha_identifier = user_data.get('Alpha Identifier', '')
        if alpha_identifier == "":
            encoded_alpha_identifier = 'FF' * (ef_file_len_decimal - 14)  # 补足F
        else:
            encoded_alpha_identifier = alpha_identifier.encode('ascii').hex().upper()  # 编码
            if len(encoded_alpha_identifier) / 2 < ef_file_len_decimal - 14:
                fill_len = ef_file_len_decimal - 14 - int(len(encoded_alpha_identifier)/2)
                encoded_alpha_identifier += 'FF' * fill_len
 
        # 编码Dialing Number/SSC String
        # 编码length_SCC, SCC长度为encoded_dialing_number长度+一个字节TON and NPI的长度 
        dialing_number = user_data.get('Dialing Number/SSC String', '')
        if dialing_number == "":
            length_SCC = "FF"
            ton_value = "F" 
            npi_value ="F" 
            encoded_dialing_number = "FFFFFFFFFFFFFFFFFFFF" 
            last_2_bytes = "FFFF"
        elif not dialing_number.isdigit():
            return "error: Dialing Number/SSC String must be numeric"
        else:
            if len(dialing_number) >20:
                encode_data =f"error: Dialing Number/SSC String输入超限"
                return encode_data
            else:
                if len(dialing_number) % 2 != 0:  # 确保dialing_number长度为偶数
                    dialing_number += 'F'  # Append 'F' to make the length even
                
                length_SCC = hex(int((len(dialing_number) + 2) / 2))[2:].upper().zfill(2)  # 编码SCC长度，dialing_number长度+1
                dialing_number += 'F' * (20 - len(dialing_number))  # 补充 F 直到长度为 20

            
            encoded_dialing_number = ''.join(dialing_number[i:i+2][::-1] for i in range(0, len(dialing_number), 2))
 
            # 查找 TON_Type of number 对应的值
            ton_description = user_data.get('TON_Type of number', '')
            ton_value = {  # 反向映射
                "Unknown (未知)": '8',
                "International Number (国际号码)": '9',
                "National Number (国家号码)": 'A',
                "Network-Specific Number (网络专用号码)": 'B',
                "Subscriber Number (订户号码)": 'C',
                "Alphanumeric Number (字母数字号码)": 'D',
                "Abbreviated Number (缩短号码)": 'E',
                "": '9'  # 用户没有输入默认 9
            }
            ton_value = ton_value.get(ton_description, '9')  # 尝试获取值，如果不存在则返回 9
            
            logging.info("TON_Type of number 可选输入类型为:\n"
                    "  - International Number (国际号码)\n"
                    "  - National Number (国家号码)\n"
                    "  - Network-Specific Number (网络专用号码)\n"
                    "  - Subscriber Number (订户号码)\n"
                    "  - Alphanumeric Number (字母数字号码)\n"
                    "  - Abbreviated Number (缩短号码)")

            
            # 将NPI_Numbering plan identification 转换为16进制
            npi_description = user_data.get('NPI_Numbering plan identification', '')
            npi_value = {  # 反向映射
                "Unknown (未知)": '0',
                "ISDN/E.164 (国际电话编号计划)": '1',
                "Data Numbering Plan, X.121 (数据编号计划)": '3',
                "Telex Numbering Plan (Telex 编号计划)": '4',
                "Land Mobile Numbering Plan (陆地移动编号计划)": '6',
                "Private Numbering Plan (国家特定编号计划)": '8',
                "": '1'  # 用户没有输入默认 1
            }
            npi_value = npi_value.get(npi_description, '1')  # 尝试获取值，如果不存在则返回 1
            
            logging.info("NPI_Numbering plan identification可选输入类型为:\n"
                    " - ISDN/E.164 (国际电话编号计划)\n"
                    " - Data Numbering Plan, X.121 (数据编号计划)\n" 
                    " - Telex Numbering Plan (Telex 编号计划)\n" 
                    " - Land Mobile Numbering Plan (陆地移动编号计划)\n" 
                    " - Private Numbering Plan (国家特定编号计划)")
            
            last_2_bytes = 'FFFF'   # 不编码Capability/Configuration1 Record Identifier和Extension1 Record Identifier，默认FF

        # 将结果拼接成一个字符串
        encode_data = encoded_alpha_identifier + length_SCC + ton_value + npi_value + encoded_dialing_number + last_2_bytes
        
        if len(encode_data) <= ef_file_len_decimal * 2:
            # Pad with 'F' if the length is less than required
            encode_data = encode_data.ljust(ef_file_len_decimal * 2, 'F')
        else:
            logging.debug("MSISDN data longer than current EF (%d >%d),resize in write_data()",
                          len(encode_data) // 2, ef_file_len_decimal)
        
        return encode_data
    else:
        return "error: encode_data failed"  
