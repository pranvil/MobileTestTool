import logging
from parsers.general import hex_to_ascii_text

def parse_data(raw_data: list) -> list:
    """
    解析 EF6FF3 (EFePDGId) 数据。支持多个 TLV 块。
    TLV结构：
    Tag (1 byte): 0x80
    Length (1 byte)
    Address Type (1 byte): 00-FQDN, 01-IPv4, 02-IPv6
    Address (Length-1 bytes)

    返回:
    [
        {
            "Address Type": "FQDN / IPv4 / IPv6",
            "Home ePDG Address": "..."
        },
        ...
    ]
    """
    data = raw_data[0] if isinstance(raw_data, list) else raw_data
    index = 0
    result = []

    while index + 2 < len(data):
        tag = data[index:index+2]
        index += 2
        length_index = data[index:index + 2]
        length = int(length_index, 16)
        index += 2
        value = data[index:index + length*2]
        index += length*2
        if tag != "80":
            break  # 非预期Tag
        
        addr_type_byte = value[0:2]
        addr_data = value[2:length*2]
        logging.debug(f"length: {length}, addr_data: {addr_data}")

        if addr_type_byte == "00":  # FQDN
            try:
                address = hex_to_ascii_text(addr_data)
                addr_type = "FQDN"
            except Exception:
                address = "Invalid ASCII"
                addr_type = "FQDN"
        elif addr_type_byte == "01" and len(addr_data) == 8:  # IPv4 (4字节 = 8个十六进制字符)
            try:
                # 将十六进制字符串转换为IPv4地址
                ip_bytes = [int(addr_data[i:i+2], 16) for i in range(0, 8, 2)]
                address = ".".join(str(b) for b in ip_bytes)
                addr_type = "IPv4"
            except Exception:
                address = "Invalid IPv4"
                addr_type = "IPv4"
        elif addr_type_byte == "02" and len(addr_data) == 32:  # IPv6 (16字节 = 32个十六进制字符)
            try:
                # 将十六进制字符串转换为IPv6地址
                ip_groups = [addr_data[i:i+4] for i in range(0, 32, 4)]
                address = ":".join(ip_groups)
                addr_type = "IPv6"
            except Exception:
                address = "Invalid IPv6"
                addr_type = "IPv6"
        else:
            address = "Unsupported or Invalid"
            addr_type = f"Unknown({addr_type_byte})"

        result.append({
            "Address Type": addr_type,
            "Home ePDG Address": address
        })

       
    return result

def encode_data(user_data: dict, ef_file_len_decimal: int) -> str:
    return f"error: 暂不支持"
