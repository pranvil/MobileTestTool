"""
根据spec 31.102(chapter:4.2.26)解析SMSP数据,主要构成:Alpha-Identifier, Parameter Indicators, TP-Destination Address ,TS-Service Centre Address,TP-Protocol Identifier,TP-Data Coding Scheme,TP-Validity Period
    1. 移除填充位F
    2. 存在变量X，所以需要倒着取数据，取到倒数第14个字节之前的所有数据（Alpha Identifier ），移除F后，如果长度为奇数，补充一个F
    3. 从末尾开始处理MDN相关数据，第14个字节是length，第13个字节是ton_npi
    4. 对MDN数据每个字节内的数字进行交换
    5. 只有当最后一个字符是'F'时才移除
    数据结构:
        {
            "Alpha-Identifier": "",
            "Parameter Indicators": "",
            "TP-Destination Address": "",
            "TS-Service Centre Address": "",
            "TP-Protocol Identifier": "",
            "TP-Data Coding Scheme": "",
            "TP-Validity Period": ""
        }
"""
from parsers.general import swap_hex_string
import logging

def parse_data(raw_data: list) -> list:
    results = []
    for data in raw_data:
        # 初始化解析结果字典
        result = {}

        # 获取TP-Validity Period
        tp_vp = int(data[-2:], 16)  # 将最后两个字符从16进制转换为10进制
        if 0 <= tp_vp <= 143:
            result['TP-Validity Period'] = f"{(tp_vp + 1) * 5} minutes"  # 单位为分钟
        elif 144 <= tp_vp <= 167:
            result['TP-Validity Period'] = f"{12 + ((tp_vp - 143) * 30)} hours"  # 单位为小时
        elif 168 <= tp_vp <= 196:
            result['TP-Validity Period'] = f"{(tp_vp - 166)} days"  # 单位为小时
        elif 197 <= tp_vp <= 255:
            result['TP-Validity Period'] = f"{(tp_vp - 192)} weeks"  # 单位为小时
        
        # 获取TP-Data Coding Scheme
        result['TP-Data Coding Scheme'] = data[-4:-2]

        # 获取TP-Protocol Identifier
        result['TP-Protocol Identifier'] = data[-6:-4]

        # 获取TS-Service Centre Address (12 bytes)
        ts_addr = data[-30:-6]
        while ts_addr.endswith("FF"):
            ts_addr = ts_addr[:-2]  # 去掉最后两个字符
        length = len(ts_addr)
        swapped_pairs = []
        for i in range(0, length, 2):
            if i + 1 < length:  # 确保不会越界
                swapped = ts_addr[i + 1] + ts_addr[i]  # 交换每对字符
                swapped_pairs.append(swapped)   
        swapped_result = ''.join(swapped_pairs)    # 将结果合并为一个字符串
        ts_addr = swapped_result[4:]      # 提第5 到 最后 位字符 
        while ts_addr.endswith("F"):
            ts_addr = ts_addr[:-1]

        result['TS-Service Centre Address'] = ts_addr

        # 获取TP-Destination Address (12 bytes)
        tp_addr = data[-54:-30]
        while tp_addr.endswith("FF"):
            tp_addr = tp_addr[:-2]  # 去掉最后两个字符
        length = len(tp_addr)
        swapped_pairs = []
        for i in range(0, length, 2):
            if i + 1 < length:  # 确保不会越界
                swapped = tp_addr[i + 1] + tp_addr[i]  # 交换每对字符
                swapped_pairs.append(swapped)   
        swapped_result = ''.join(swapped_pairs)    # 将结果合并为一个字符串
        tp_addr = swapped_result[4:]      # 提取第5到最后
        result['TP-Destination Address'] = tp_addr

        # 获取Parameter Indicators
        result['Parameter Indicators'] = data[-56:-54]

        # 获取Alpha-Identifier
        Alpha_id = data[:-56]
        while Alpha_id.endswith("FF"):
            Alpha_id = Alpha_id[:-2]  # 去掉最后两个字符
        Alpha_id = ''.join(chr(int(Alpha_id[i:i+2], 16)) for i in range(0, len(Alpha_id), 2))
        result['Alpha-Identifier'] = Alpha_id

        # 将解析结果添加到结果列表中
        results.append(result)
    return results

def encode_data(user_data: dict, ef_file_len_decimal: int) -> str:
    if not user_data:
        return "error: user_data is empty"
    try:
        input_Alpha_id = user_data.get("Alpha-Identifier", "")       # fix value
        # input_Parameter_id = user_data.get("Parameter Indicators", "")          #Fixe value
        # input_Destination_addr = user_data.get("TP-Destination Address", "")    #Fixe value
        # input_Protocol_id = user_data.get("TP-Protocol Identifier", "")    #Fixe value   
        # input_Coding_Scheme = user_data.get("TP-Data Coding Scheme", "")    #Fixe value  
        # input_Validity_Period = user_data.get("TP-Validity Period", "")      #fix value
        input_SC_addr = user_data.get("TS-Service Centre Address", "")

        # 编码文件
        encoded_Parameter_id = "E2"       
        encoded_Destination_addr = "FFFFFFFFFFFFFFFFFFFFFFFF"
        encoded_Alpha_id = input_Alpha_id.encode('ascii', 'replace').hex().upper() 
        encoded_SC_addr = f_encode_SC_addr(input_SC_addr)
        if encoded_SC_addr.startswith("error"):
            return encoded_SC_addr
        encoded_Protocol_id = "00"        
        encoded_Coding_Scheme = "00"        
        encoded_Validity_Period = "FF"
        if len(encoded_Alpha_id) <= ef_file_len_decimal*2-56:
            encoded_Alpha_id += "F" * (ef_file_len_decimal*2 - 56 - len(encoded_Alpha_id))
        elif len(encoded_Alpha_id) > ef_file_len_decimal*2 - 56:
            logging.debug("SDN Alpha Identifier longer than record_len (%d > %d), resize in write_data()",
                      len(encoded_Alpha_id)//2, ef_file_len_decimal - 28)

        encode_userdata = encoded_Alpha_id + encoded_Parameter_id + encoded_Destination_addr + encoded_SC_addr + encoded_Protocol_id + encoded_Coding_Scheme + encoded_Validity_Period
   
   
        return encode_userdata

    except Exception as e:
        return "error: %s" % str(e)

    



def f_encode_SC_addr(input_SC_addr: str) -> str:
    encode_userdata = ""
    if len(input_SC_addr) > 20:    # 如果输入的SC地址长度大于10个字节，返回错误
        return "error: input_SC_addr is longer than 20"
    elif len(input_SC_addr) < 20:   # 如果输入的SC地址长度小于10个字节，补充F
        input_SC_addr += "F" * (20 - len(input_SC_addr))
    encode_userdata = swap_hex_string(input_SC_addr)
    
    #构建第一个第二个字节；第一个字节表示后面位数长度，为电话号码长度+1
    
    length = (len(input_SC_addr)+2-1)//2 + 1   #向上取整，然后+1 （91的字节长度)
    first_byte = f"{length:02X}"
    second_byte = "91"
    encode_userdata = first_byte + second_byte + encode_userdata
    return encode_userdata
    
    
