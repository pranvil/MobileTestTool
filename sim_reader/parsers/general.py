"""
通用工具函数模块，提供各种数据编码解码功能
"""

import logging

def decode_PLMN(plmn_data):
    """
    解码PLMN（公共陆地移动网络）数据
    Args:
        plmn_data: 6位十六进制字符串，表示PLMN数据
    Returns:
        str: 解码后的PLMN字符串
    """
    swapped = plmn_data[1] + plmn_data[0] + plmn_data[3] + plmn_data[2] + plmn_data[5] + plmn_data[4]
    plmn = swapped[:3] + swapped[4:] + swapped[3]
    return plmn 


def encode_PLMN(plmn_data):
    """
    编码PLMN（公共陆地移动网络）数据
    Args:
        plmn_data: PLMN字符串，如果长度为5则自动补'F'
    Returns:
        str: 6位十六进制字符串，表示编码后的PLMN数据
    """
    # If the length of plmn_data is 5, append 'F' to it
    if len(plmn_data) == 5:
        plmn_data += 'F'
    
    swapped_plmn = plmn_data[1] + plmn_data[0] + plmn_data[5] + plmn_data[2] + plmn_data[4] + plmn_data[3]
    return swapped_plmn 

def decode_7bit(encoded_data):
    """
    解码7位编码的数据（常用于短信编码）
    Args:
        encoded_data: 十六进制字符串
    Returns:
        str: 解码后的ASCII字符串
    """
    byte_array = bytes.fromhex(encoded_data)
    decoded_chars = []  
    carry_over = 0
    carry_bits = 0

    for byte in byte_array:
        current_value = (byte << carry_bits) & 0x7F
        current_value |= carry_over
        if current_value == 0:
            continue
        decoded_chars.append(chr(current_value))
        carry_over = byte >> (7 - carry_bits)
        carry_bits += 1
        if carry_bits == 7:
            if carry_over:
                decoded_chars.append(chr(carry_over))
            carry_over = 0
            carry_bits = 0

    return ''.join(decoded_chars).strip()

def decode_ucs2(encoded_data):
    """
    解码UCS2编码的数据（UTF-16BE）
    Args:
        encoded_data: 十六进制字符串
    Returns:
        str: 解码后的Unicode字符串
    """
    byte_array = bytes.fromhex(encoded_data)  # 将十六进制字符串转换为字节数组
    try:
        return byte_array.decode('utf-16-be')  # 使用大端UTF-16解码
    except UnicodeDecodeError as e:
        logging.error("解码错误: %s", e)  # 输出错误信息
        return ""  # 返回空字符串或其他默认值

def encode_7bit(data):
    """
    将ASCII字符串编码为7位编码（常用于短信编码）
    Args:
        data: ASCII字符串
    Returns:
        str: 编码后的十六进制字符串
    """
    packed_bytes = []
    current_byte = 0
    bits_left = 0

    for char in data:
        char_value = ord(char) & 0x7F
        current_byte |= char_value << bits_left
        bits_left += 7
        while bits_left >= 8:
            packed_bytes.append(current_byte & 0xFF)
            current_byte >>= 8
            bits_left -= 8

    if bits_left > 0:
        packed_bytes.append(current_byte & 0xFF)

    return ''.join(f'{byte:02X}' for byte in packed_bytes) 

def swap_hex_string(hex_string):
    """
    交换十六进制字符串中相邻的字符
    Args:
        hex_string: 十六进制字符串
    Returns:
        str: 交换后的十六进制字符串，如果输入长度为奇数则补'F'
    """
    if len(hex_string) % 2 == 1:  # 检查是否是奇数长度
        hex_string += "F"  # 补一个 'F'
    
    swapped = ""
    for i in range(0, len(hex_string), 2):
        swapped += hex_string[i+1] + hex_string[i]  # 交换相邻的字符
    
    return swapped

def ascii_text_to_hex(ascii_string):
    """
    将ASCII字符串转换为十六进制字符串
    Args:
        ascii_string: ASCII字符串
    Returns:
        str: 大写的十六进制字符串
    """
    return ascii_string.encode('ascii').hex().upper()

def hex_to_ascii_text(hex_string):
    """
    将十六进制字符串转换为ASCII字符串
    Args:
        hex_string: 十六进制字符串
    Returns:
        str: ASCII字符串
    """
    return bytes.fromhex(hex_string).decode('ascii')


def TLV_parser(data):
    """
    解析TLV（Tag-Length-Value）格式数据
    Args:
        data: TLV格式的十六进制字符串
    Returns:
        str: 解析后的ASCII字符串
    """
    raw_data = data[4:]      # 去除tag&length
    while raw_data.endswith("FF"):
        raw_data = raw_data[:-2]
    encoded_data = hex_to_ascii_text(raw_data)
    return encoded_data

def TLV_encode(data):
    """
    将数据编码为TLV（Tag-Length-Value）格式
    Args:
        data: 十六进制字符串
    Returns:
        str: TLV格式的十六进制字符串
    """
    first_byte = "80"           #tag 为8
    length = len(data)//2   
    logging.debug("length: %s", length)
    second_byte  = f"{length:02X}"
    encoded_data = first_byte + second_byte + data
    return encoded_data


def encode_service_bitmap(service_flags: list, ef_file_len_decimal: int) -> str:
    """
    将服务标志列表编码为位图格式
    Args:
        service_flags: 服务标志列表，每个元素为'Y'或'N'
        ef_file_len_decimal: 文件长度（十进制）
    Returns:
        str: 编码后的十六进制字符串，长度不足时补'F'
    """
    bits = ['1' if flag == 'Y' else '0' for flag in service_flags]
    while len(bits) % 8 != 0:
        bits.append('0')
    hex_result = ''.join(
        f"{int(''.join(bits[i:i+8][::-1]), 2):02X}"
        for i in range(0, len(bits), 8)
    )
    if len(hex_result) < ef_file_len_decimal * 2:
        hex_result = hex_result.ljust(ef_file_len_decimal * 2, 'F')
    return hex_result


def decode_service_bitmap(hex_data: str, service_mapping: list) -> dict:
    """
    将位图格式的服务标志解码为字典
    Args:
        hex_data: 十六进制字符串形式的位图
        service_mapping: 服务名称列表
    Returns:
        dict: 服务名称到标志('Y'/'N')的映射
    """
    binary_str = ''.join(f"{int(hex_data[i:i+2], 16):08b}"[::-1] for i in range(0, len(hex_data), 2))
    result = {}
    for i, name in enumerate(service_mapping):
        result[name] = 'Y' if i < len(binary_str) and binary_str[i] == '1' else 'N'
    return result


def decode_access_technology(hex_str: str) -> str:
    """
    解码访问技术标识符
    Args:
        hex_str: 4位十六进制字符串，前两位是第4字节，后两位是第5字节
    Returns:
        str: 解码后的访问技术字符串，多个技术用分号分隔
    """
    # 1) 先把 hex_str 拆成两字节
    if len(hex_str) != 4:
        return "Invalid data"
    byte4 = int(hex_str[0:2], 16)  # 第4字节
    byte5 = int(hex_str[2:4], 16)  # 第5字节

    # 用一个 list 暂存解析结果，最终 join 成字符串返回
    results = []

    # ================ 解析第 4 字节 ================
    # 先逐 bit 取出
    # （注意：b1=最低位，b8=最高位）
    b1 =  byte4       & 0x01      # bit1
    b2 = (byte4 >> 1) & 0x01      # bit2
    b3 = (byte4 >> 2) & 0x01      # bit3
    b4 = (byte4 >> 3) & 0x01      # bit4
    b5 = (byte4 >> 4) & 0x01      # bit5
    b6 = (byte4 >> 5) & 0x01      # bit6
    b7 = (byte4 >> 6) & 0x01      # bit7
    b8 = (byte4 >> 7) & 0x01      # bit8

    # 1) satellite
    if b1 == 1:
        results.append("satellite E-UTRAN in NB-S1 mode")
    if b2 == 1:
        results.append("satellite E-UTRAN in WB-S1 mode")
    if b3 == 1:
        results.append("satellite NG-RAN")

    # 2) NG-RAN
    if b4 == 1:
        results.append("NG-RAN")

    # 3) UTRAN
    if b8 == 1:
        results.append("UTRAN")

    # 4) E-UTRAN in ...
    #    如果 b7=1，则根据 (b6, b5) 三位一体解析你那几种场景
    if b7 == 1:
        if b6 == 0 and b5 == 0:
            results.append("E-UTRAN in WB-S1 mode and NB-S1 mode")
        elif b6 == 0 and b5 == 1:
            results.append("E-UTRAN in NB-S1 mode only")
        elif b6 == 1 and b5 == 0:
            results.append("E-UTRAN in WB-S1 mode only")
        elif b6 == 1 and b5 == 1:
            results.append("E-UTRAN in WB-S1 mode and NB-S1 mode")

    # ================ 解析第 5 字节 ================
    b1_2 =  byte5       & 0x01  # bit1
    b2_2 = (byte5 >> 1) & 0x01  # bit2
    b3_2 = (byte5 >> 2) & 0x01  # bit3
    b4_2 = (byte5 >> 3) & 0x01  # bit4
    b5_2 = (byte5 >> 4) & 0x01  # bit5
    b6_2 = (byte5 >> 5) & 0x01  # bit6
    b7_2 = (byte5 >> 6) & 0x01  # bit7
    b8_2 = (byte5 >> 7) & 0x01  # bit8

    # 1) 单独位
    if b5_2 == 1:
        results.append("cdma2000 1xRTT")
    if b6_2 == 1:
        results.append("cdma2000 HRPD")
    if b7_2 == 1:
        results.append("GSM COMPACT")

    # 2) b8=1 => GSM/EC-GSM 组合
    if b8_2 == 1:
        # 根据 (b4_2, b3_2) 四选一
        if (b4_2 == 0) and (b3_2 == 0):
            results.append("GSM and EC-GSM-IoT")
        elif (b4_2 == 0) and (b3_2 == 1):
            results.append("GSM without EC-GSM-IoT")
        elif (b4_2 == 1) and (b3_2 == 0):
            results.append("EC-GSM-IoT only")
        elif (b4_2 == 1) and (b3_2 == 1):
            results.append("GSM and EC-GSM-IoT")

    # 最后返回解析结果，分号拼接
    return "; ".join(results)

def encode_access_technology(tech_str: str) -> str:
    """
    编码访问技术标识符
    Args:
        tech_str: 访问技术字符串，多个技术用分号分隔
    Returns:
        str: 4位十六进制字符串，前两位是第4字节，后两位是第5字节
    """
    # 第四字节各 token => 对应的 bits (从右到左 b1=0x01, b2=0x02, b3=0x04, b4=0x08, b5=0x10, b6=0x20, b7=0x40, b8=0x80)
    bit_map_4th = {
        # 卫星 E-UTRAN
        "satellite E-UTRAN": 0x01,  # 你说想让它=0x01
        "satellite E-UTRAN in NB-S1 mode": 0x01,  # b1
        "satellite E-UTRAN in WB-S1 mode": 0x02,  # b2
        "satellite NG-RAN": 0x04,                 # b3
        "NG-RAN": 0x08,                           # b4
        "UTRAN": 0x80,                            # b8

        # E-UTRAN in ...  (以下几种场景互斥，分别置 b7,b6,b5)
        #   E-UTRAN in WB-S1 mode and NB-S1 mode => b7=1,b6=1,b5=1 => 0x70 (0111_0000)
        "E-UTRAN in WB-S1 mode and NB-S1 mode": 0x70,

        #   E-UTRAN in NB-S1 mode only => b7=1,b6=0,b5=1 => 0x50 (0101_0000)
        "E-UTRAN in NB-S1 mode only": 0x50,

        #   E-UTRAN in WB-S1 mode only => b7=1,b6=1,b5=0 => 0x60 (0110_0000)
        "E-UTRAN in WB-S1 mode only": 0x60,
    }

    # 第五字节各 token => 对应 bits (b1=0x01, b2=0x02, b3=0x04, b4=0x08, b5=0x10, b6=0x20, b7=0x40, b8=0x80)
    bit_map_5th = {
        # 你列出的单个 bits
        "cdma2000 1xRTT": 0x10,   # b5
        "cdma2000 HRPD": 0x20,    # b6
        "GSM COMPACT": 0x40,      # b7

        # GSM/EC-GSM 四种组合都需要 b8=1，再根据 b4,b3 的不同
        #   GSM and EC-GSM-IoT     => bit8=1, bit4=0, bit3=0 => 0x80
        #   GSM without EC-GSM-IoT => bit8=1, bit4=0, bit3=1 => 0x84
        #   EC-GSM-IoT only        => bit8=1, bit4=1, bit3=0 => 0x88
        #   GSM and EC-GSM-IoT(另一版) => bit8=1, bit4=1, bit3=1 => 0x8C
        "GSM and EC-GSM-IoT": 0x8C,
        "GSM without EC-GSM-IoT": 0x84,
        "EC-GSM-IoT only": 0x88,
    }

    # 去掉换行符后再分号拆分
    tokens = [x.strip() for x in tech_str.replace("\n", " ").split(";") if x.strip()]

    byte4 = 0
    byte5 = 0

    for token in tokens:
        # 若和第四字节映射中任意键"精确相等"，则OR上相应bit
        if token in bit_map_4th:
            byte4 |= bit_map_4th[token]

        # 若和第五字节映射中任意键"精确相等"，则OR上相应bit
        if token in bit_map_5th:
            byte5 |= bit_map_5th[token]

    return f"{byte4:02X}{byte5:02X}"

def encode_plmn_data(data_dict: dict, ef_file_len_decimal: int) -> str:
    """
    编码PLMN数据
    Args:
        data_dict: 包含PLMN和访问技术标识符的字典
        ef_file_len_decimal: 文件长度（十进制）
    Returns:
        str: 编码后的十六进制字符串，长度不足时补'F'
    """
    try:
        result_hex = ""
        idx = 1
        while True:
            plmn_key = f"PLMN{idx}"
            tech_key = f"Access Technology Identifier{idx}"
            # 如果对应键不存在，跳出
            if plmn_key not in data_dict or tech_key not in data_dict:
                break
            
            plmn_str = data_dict[plmn_key]
            tech_str = data_dict[tech_key]
            
            # 编码 PLMN -> 3字节 => 6个hex
            plmn_hex = encode_PLMN(plmn_str)
            
            # 编码 Access Technology -> 2字节 => 4个hex
            tech_hex = encode_access_technology(tech_str)
            
            # 拼接
            result_hex += plmn_hex + tech_hex
            idx += 1

        if len(result_hex) <= ef_file_len_decimal*2:
            # Pad with 'F' if the length is less than required
            result_hex = result_hex.ljust(ef_file_len_decimal*2, 'F')
        else:
            logging.debug("PLMN list longer than current EF (%d >%d),resize in write_data()",
                          len(result_hex) // 2, ef_file_len_decimal)

        return result_hex
    except Exception as e:
        return f"error: 未知错误 - {str(e)}"



# Network Name 编码24.008 章节10.5.3.5a
def _pack_network_name(tag: str, text: str, add_ci: bool = False) -> str:
    """内部: 按 GSM 7‑bit 将单个 Network‑Name 字符串封装为 TLV 段。"""
    if not text:
        return ""

    packed_hex = encode_7bit(text)
    total_bits = len(text) * 7
    spare_bits = (8 - (total_bits % 8)) % 8  # 0‑7
    # ext=1 (bit8), coding=000 (bit7‑5), Add CI=(bit4), spare bits=(bit3‑1)
    flags = 0b10000000 | (0b00010000 if add_ci else 0) | spare_bits

    length_octets = len(packed_hex) // 2 + 1  # +1 for flag octet itself
    return f"{tag}{length_octets:02X}{flags:02X}{packed_hex}"


def _pack_plmn_additional_info(info: str) -> str:
    """内部: UCS2‑BE 封装可选 PLMN_Additional_Information (Tag 0x80)"""
    if not info:
        return ""
    encoded = info.encode('utf-16-be').hex().upper()
    length_octets = len(encoded) // 2  # UTF‑16BE bytes count
    return f"80{length_octets:02X}{encoded}"


def encode_pnn_data(user_data) -> str:
    """将用户输入的 PNN 字段编码成写卡 hex 字符串。

    Args:
        user_data: {"Full name": str, "Short name": str, "PLMN_Additional_Information": str}
        ef_file_len_decimal: 目标 EF 文件长度（十进制字节数）

    Returns:
        长度为 ef_file_len_decimal×2 的 hex 字符串（不足补 F）。
    """
    f_name = user_data.get("Full name", "")
    s_name = user_data.get("Short name", "")
    plmn_info = user_data.get("PLMN_Additional_Information", "")

    full_part = _pack_network_name("43", f_name)
    short_part = _pack_network_name("45", s_name)
    plmn_part = _pack_plmn_additional_info(plmn_info)

    encoded = full_part + short_part + plmn_part

    return encoded