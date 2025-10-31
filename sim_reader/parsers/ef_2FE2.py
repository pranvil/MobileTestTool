"""
    数据结构
        {
            "ICCID": ""
        }
"""
import logging
def parse_data(raw_data: list) -> list:

    results = []
    result = {}
    

    # 将原始数据转换为字符串
    raw_string = ''.join(raw_data)  # 假设 raw_data 是一个字符列表

    # 交换每对字符
    swapped_pairs = []
    for i in range(0, len(raw_string), 2):  # 每次步进2
        if i + 1 < len(raw_string):  # 确保不会越界
            swapped = raw_string[i + 1] + raw_string[i]  # 交换每对字符
            swapped_pairs.append(swapped)  # 将交换后的字符对添加到列表中

    # 将结果合并为一个字符串
    final_result = ''.join(swapped_pairs)
    result["ICCID"] = final_result  # 将最终结果放入字典中
    results.append(result)  # 将字典添加到结果列表中
    return results  # 返回结果列表

def swapped_pairs(swap_data):
    swapped_pairs = []  # 初始化列表以存储交换后的字符对
    for i in range(0, len(swap_data), 2):  # 每次步进2
        if i + 1 < len(swap_data):  # 确保不会越界
            swapped = swap_data[i + 1] + swap_data[i]  # 交换每对字符
            swapped_pairs.append(swapped)  # 将交换后的字符对添加到列表中
    swap_result = ''.join(swapped_pairs)
    return swap_result  # 返回交换后的字符对列表
    
def encode_data(user_data: dict,ef_file_len_decimal: int) -> str:
    logging.debug("encode_data数据: %s", user_data)
    input_iccid = user_data.get("ICCID", "")
    
    # 检查输入数据的长度是否为奇数
    if len(input_iccid) % 2 != 0:
        encode_data = f"error: 请检查输入数据，长度应为偶数位"
        return encode_data
    if not all(c.isdigit() or c.upper() == 'F' for c in input_iccid):
        encode_data = f"error: ICCID只能为数字或F"
        return encode_data
    if len(input_iccid) >20:
        encode_data = f"error: ICCID长度超限"
        return encode_data
    if not input_iccid:
        encode_data = f"error: ICCID不能为空"
        return encode_data
    if ' ' in input_iccid:
        encode_data = f"error: 输入不能有空格"
        return encode_data

    input_iccid_packed = swapped_pairs(input_iccid)
    encode_data = input_iccid_packed
    
    if len(encode_data) <= ef_file_len_decimal * 2:
        # Pad with 'F' if the length is less than required
        encode_data = encode_data.ljust(ef_file_len_decimal * 2, 'F')
    else:
        logging.debug("ICCID data longer than current EF (%d >%d),resize in write_data()",
                      len(encode_data) // 2, ef_file_len_decimal)
    
    return encode_data