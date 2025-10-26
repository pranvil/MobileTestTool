def parse_fcp_data(fcp_data):
    """解析FCP（File Control Parameters）数据
    根据ETSI TS 102 221 V18.2.0 (2024-06) Table 11.4规范解析FCP模板
    
    Args:
        fcp_data (str): FCP数据的十六进制字符串
        
    Returns:
        dict: 包含以下字段的字典：
            - file_accessibility: 文件可访问性（Shareable/Not shareable）
            - file_type: 文件类型（Working EF/Internal EF/DF or ADF）
            - ef_structure: EF结构（transparent/linear/cyclic）
            - recorder: 记录器信息
            - record_length: 记录长度
            - life_cycle_status: 生命周期状态
            - file_length: 文件总长度
            - sec_attr: 安全属性
            - sfi: 短文件标识符
    """
    if not fcp_data.startswith("62"):
        return fcp_data

    # 初始化EF信息字典，所有字段默认为"none"
    ef_info = {
        'file_accessibility': "none",
                'ef_structure': "none",
                'file_length': "none", 
                'recorder': "none", 
                'record_length': "none", 
                'life_cycle_status': "none", 
                'file_type': "none", 
                'sec_attr': "none",
                'sfi': "none",
                }
    
    
    # 跳过FCP标签(62)和长度字段
    index = 4
    data_length = len(fcp_data)

    while index < data_length: 
        # 解析TAG-LENGTH-VALUE结构
        tag = fcp_data[index:index + 2]
        index += 2

        length = int(fcp_data[index:index + 2], 16)
        index += 2

        value = fcp_data[index:index + length * 2]
        index += length * 2

   
        if tag == '82':  # 文件描述符
            if length == 0x02:
                file_type = parse_file_descriptor_T(value)
            elif length == 0x05:
                file_type = parse_file_descriptor_L(value)

            # 更新文件描述符相关字段
            if len(file_type) > 0:
                ef_info["file_accessibility"] = file_type[0]
            if len(file_type) > 1:
                ef_info["file_type"] = file_type[1]
            if len(file_type) > 2:
                ef_info["ef_structure"] = file_type[2]
            if len(file_type) > 3:
                ef_info["record_length"] = file_type[3]
            if len(file_type) > 4:
                ef_info["recorder"] = file_type[4]

        elif tag == '8A':  # 生命周期状态
            life_cycle_status = parse_life_cycle_status(value)
            ef_info["life_cycle_status"] = life_cycle_status
            
        elif tag == '80':  # 文件总大小
            ef_info["file_length"] = value

        elif tag == '8B':  # 安全属性
            if len(value) > 6:
                ef_info["sec_attr"] = value[0:6]
            else:
                ef_info["sec_attr"] = value
            
        elif tag == '88':  # 短文件标识符
            if length == 0x00:
                ef_info["sfi"] = ""
            else:
                ef_info["sfi"] = value

    return ef_info

def parse_file_descriptor_T(value: str):
    """解析2字节文件描述符
    根据ETSI TS 102 221 V18.2.0 (2024-06) Table 11.5规范解析
    
    Args:
        value (str): 2字节的十六进制字符串
        
    Returns:
        list: 包含以下信息的列表：
            - file_accessibility: 文件可访问性
            - file_type: 文件类型
            - ef_structure: EF结构
            
    Raises:
        ValueError: 当输入值长度不足时抛出
    """
    if len(value) < 1:
        raise ValueError("值的长度不足，无法解析文件描述符")
    
    # 解析第一个字节
    file_descriptor_byte = int(value[0:2], 16)

    # 解析文件可访问性 (b7)
    shareable_file = (file_descriptor_byte >> 6) & 0x01
    file_accessibility = "Shareable" if shareable_file else "Not shareable"

    # 解析文件类型 (b6, b5)
    file_type = (file_descriptor_byte >> 3) & 0x07
    
    # 解析文件结构 (b4, b3, b2, b1)
    ef_structure = (file_descriptor_byte & 0x07)

    result = []
    result.append(file_accessibility)

    # 解析文件类型
    if file_type == 0b00:
        result.append("Working EF")
    elif file_type == 0b01:
        result.append("Internal EF")
    elif file_descriptor_byte & 0x3F == 0b111000:
        result.append("DF or ADF")
    else:
        result.append("RFU")

    # 解析EF结构
    if ef_structure == 0b00:
        result.append("No information given")
    elif ef_structure == 0b01:
        result.append("transparent")
    elif ef_structure == 0b10:
        result.append("linear")
    elif ef_structure == 0b110:
        result.append("cyclic")
    else:
        result.append("RFU")

    return result

def parse_file_descriptor_L(value: str):
    """解析5字节文件描述符
    根据ETSI TS 102 221 V18.2.0 (2024-06) Table 11.5规范解析
    
    Args:
        value (str): 5字节的十六进制字符串
        
    Returns:
        list: 包含以下信息的列表：
            - file_accessibility: 文件可访问性
            - file_type: 文件类型
            - ef_structure: EF结构
            - recorder: 记录器信息
            - record_length: 记录长度
            
    Raises:
        ValueError: 当输入值长度不足时抛出
    """
    if len(value) < 1:
        raise ValueError("值的长度不足，无法解析文件描述符")
    
    # 解析第一个字节
    file_descriptor_byte = int(value[0:2], 16)

    # 解析文件可访问性 (b7)
    shareable_file = (file_descriptor_byte >> 6) & 0x01
    file_accessibility = "Shareable" if shareable_file else "Not shareable"
    
    # 解析文件类型 (b6, b5)
    file_type = (file_descriptor_byte >> 3) & 0x07
    
    # 解析文件结构 (b4, b3, b2, b1)
    ef_structure = (file_descriptor_byte & 0x07)

    result = []
    result.append(file_accessibility)

    # 解析文件类型
    if file_type == 0b00:
        result.append("Working EF")
    elif file_type == 0b01:
        result.append("Internal EF")
    elif file_descriptor_byte & 0x3F == 0b111000:
        result.append("DF or ADF")
    else:
        result.append("RFU")

    # 解析EF结构
    if ef_structure == 0b00:
        result.append("No information given")
    elif ef_structure == 0b01:
        result.append("transparent")
    elif ef_structure == 0b10:
        result.append("linear")
    elif ef_structure == 0b110:
        result.append("cyclic")
    else:
        result.append("RFU")
    
    # 添加记录器信息和记录长度
    result.append(value[4:8])  # recorder
    result.append(value[8:10])  # record length
    
    return result

def parse_life_cycle_status(value):
    """解析生命周期状态
    根据ETSI TS 102 221 V18.2.0 (2024-06) Table 11.7b规范解析
    
    Args:
        value (str): 单字节的十六进制字符串
        
    Returns:
        str: 生命周期状态的描述字符串
    """
    
    # 转换为整数并验证范围
    life_cycle_byte = int(value, 16) 
    if not (0 <= life_cycle_byte <= 255):
        return "Invalid value, must be a byte (0-255)."
    
    # 根据规范判断状态
    if life_cycle_byte == 0:
        status = "No information given"
    elif life_cycle_byte == 1:
        status = "Creation"
    elif life_cycle_byte == 3:
        status = "Initialization"
    elif life_cycle_byte == 5 or life_cycle_byte == 7:
        status = "activated"
    elif life_cycle_byte == 4 or life_cycle_byte == 6:
        status = "deactivated"
    elif life_cycle_byte >> 2 == 3:
        status = "Termination state"
    elif life_cycle_byte >> 4 != 0:
        status = "Proprietary"
    else:
        status = "RFU"
        
    return status