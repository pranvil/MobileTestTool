"""
    根据spec 31.102(chapter:4.2.2)解析IMSI数据
    1. 移除填充位F
    2. 两两互换
    3. IMSI从第3位开始取值
    数据结构:
        {
            "IMSI": ""
        }
"""
import logging

def parse_data(raw_data: list) -> list:
    logging.debug("ef_6F07 parse_data: %s", raw_data)
    results = []
    try:
        if not raw_data:  # 检查空列表
            logging.debug("警告: 接收到了空数据")

        # 取列表第一个元素并移除所有的 F
        clean_data = raw_data[0].replace('F', '') 
        # 两两互换
        swapped = ''
        for i in range(0, len(clean_data), 2):
            if i + 1 < len(clean_data):
                swapped += clean_data[i+1] + clean_data[i]
        # 移除开头的3位数字
        result = swapped[3:]
        # 将结果包装成字典
        results.append({"IMSI": result})
        return results
        
    except Exception as e:
        logging.debug("解析IMSI数据时出错: %s", str(e))
        return "error: failed to parse IMSI data: %s" % e

def prompt():
    return "IMSI输入格式，如:3114809123456789" 

def encode_data(user_data: dict,ef_file_len_decimal: int) -> str:
    try:
        imsi = user_data.get('IMSI', '')

        # 检查是否为空
        if not imsi:
            encode_userdata = "error: IMSI不能为空"
            return encode_userdata
            
        # 检查是否包含空格
        if ' ' in imsi:
            encode_userdata = "error: IMSI不能包含空格"
            return encode_userdata
            
        # 检查是否为纯数字
        if not imsi.isdigit():
            encode_userdata = "error: IMSI必须为数字"
            return encode_userdata
            
        # 检查长度是否小于15
        if len(imsi) < 15:
            encode_userdata = "error: IMSI长度不能小于15位"
            return encode_userdata
            
        # 检查长度是否大于15
        if len(imsi) > 15:
            encode_userdata = "error: IMSI长度不能大于15位"
            return encode_userdata
        
        # 同时满足纯数字且长度为15时，执行数据处理
        if imsi.isdigit() and len(imsi) == 15:
            data_with_prefix = '809' + imsi
            encode_userdata = ''.join(data_with_prefix[i:i+2][::-1] for i in range(0, len(data_with_prefix), 2))
            logging.debug("编码后的数据: %s", encode_userdata)   
            return encode_userdata
        else:
            encode_userdata = "error: 未知错误"
            return encode_userdata
            
    except Exception as e:
        encode_userdata = f"error: 未知错误 - {str(e)}"
        return encode_userdata    