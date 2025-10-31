from .serial_comm import SerialComm 
import logging, time
import json
import os
from parsers.general import ascii_text_to_hex

JSON_DIR = "json_data" 
if not os.path.exists(JSON_DIR):
    os.makedirs(JSON_DIR)

# =====================
# data_handler.py
# SIM卡数据处理模块
# 主要功能：SIM卡文件的选择、读写、管理、JSON存取等
# =====================

def parse_sim_error(status_code: str) -> str:
    """解析SIM卡错误码（返回对应的中文/英文含义）"""
    error_codes = {
        "6700": "Wrong length",
        "67XX": "The interpretation of this status word is command dependent, except for SW2 = '00'",
        "6800": "No information given",
        "6881": "Logical channel not supported",
        "6882": "Secure messaging not supported",
        "6900": "No information given",
        "6981": "Command incompatible with file structure",
        "6982": "Security status not satisfied, need verify AMD",
        "6983": "Authentication/PIN method blocked",
        "6984": "Referenced data invalidated",
        "6985": "Conditions of use not satisfied",
        "6986": "Command not allowed (no EF selected)",
        "6989": "Command not allowed - secure channel - security not satisfied",
        "6A82": "卡文件不存在",
        "6A84": "文件空间不足",
        "6A86": "参数P1P2不正确",
        "6A89": "文件已存在",
        "6B00": "Wrong parameter(s) P1-P2",
        "6D00": "指令不支持",
        "6E00": "命令类不支持",
        "6F00": "Technical problem, no precise diagnosis",
        "6FXX": "The interpretation of this status word is command dependent, except for SW2 = '00'",
        "9000": "命令执行成功"
    }
    return error_codes.get(status_code, f"未知状态码: {status_code}")

def select_adf(comm: SerialComm, adf_type: str, ef_id: str = None) -> str:
    """选择USIM/ISIM/MF应用，返回响应内容"""
    logging.info("[select_adf] 选择ADF类型: %s, EF ID: %s", adf_type, ef_id)
    try:
        if ef_id.endswith("IST"):
            ef_id = ef_id[:-3]
        if adf_type == "USIM":
            if len(ef_id) == 4:
                cmd = f'AT+CSIM=18,"00A40804047FFF{ef_id}"'
            elif len(ef_id) == 8:
                cmd = f'AT+CSIM=22,"00A40804067FFF{ef_id}"'
            else:
                logging.error("[select_adf] select EF file length incorrect, ef_id: %s", ef_id)
                return "error: select EF file length incorrect"
            raw_data = comm.send_command(cmd)
        elif adf_type == "ISIM":
            if len(ef_id) == 4:
                comm.send_command('AT+CGLA=1,14,"01A40004027FFF"')
                cmd = f'AT+CGLA=1,14,"01A4000402{ef_id}"'
                raw_data = comm.send_command(cmd)
                if raw_data == "ERROR":
                    cmd = f'AT+CSIM=18,"01A40804047FFF{ef_id}"'
                    raw_data = comm.send_command(cmd)
            else:
                logging.error("[select_adf] select EF file length incorrect, ef_id: %s", ef_id)
                return "error: select EF file length incorrect"
        elif adf_type == "5G-EF":
            cmd = f'AT+CSIM=22,"00A40804067FFF5FC0{ef_id}"'.upper()
            raw_data = comm.send_command(cmd)  
        elif adf_type == "MF":
            cmd = f'AT+CSIM=14,"00A4080402{ef_id}"'
            raw_data = comm.send_command(cmd)  
            
        else:
            logging.error("[select_adf] 不支持的应用类型: %s", adf_type)
            return "error: unsupported ADF"
        
        response = response_format(raw_data=raw_data)
        logging.info("[select_adf] 选择ADF响应: %s", response)
        return response

    except Exception as e:
        logging.error("[select_adf] 选择%s应用失败: %s", adf_type, e)
        return "error: select ADF failed"

def read_ef_data(comm: SerialComm, fcp_data, adf_type) -> list:
    """读取EF文件数据，支持transparent/linear/cyclic结构"""
    # time.sleep(0.1)
    if isinstance(fcp_data, str) and fcp_data.startswith("error"):
        logging.error("[read_ef_data] FCP数据错误: %s", fcp_data)
        return fcp_data
    """读取EF文件数据"""
    data_list = [] 
    try:
         # 用于存储读取到的数据 
        ef_structure = fcp_data.get("ef_structure", "")
        if ef_structure == "transparent":
            file_length_hex = fcp_data.get("file_length", "00")
            if not file_length_hex or file_length_hex == "none":
                logging.error("[read_ef_data] 文件长度无效: %s", file_length_hex)
                return "error: invalid file length"
            
            # 转成实际字节长度（10进制）
            file_size = int(file_length_hex, 16)
            if file_size <= 0:
                logging.error("[read_ef_data] 文件大小无效: %s", file_size)
                return "error: invalid file size"

            # 分段读取
            chunk_size = 0xFF  # 最多 255
            offset = 0
            result_hex = ""  # 用来拼接所有读取到的 hex 数据

            while offset < file_size:
                this_chunk_size = min(chunk_size, file_size - offset)
                
                # P1P2 = 偏移量（高位、低位）
                p1 = (offset >> 8) & 0xFF
                p2 = offset & 0xFF

                # Le = 这次要读多少字节
                le_hex = f"{this_chunk_size:02X}"
                p1_hex = f"{p1:02X}"
                p2_hex = f"{p2:02X}"

                if adf_type in ["USIM", "MF"]:
                    # 例如 AT+CSIM=10,"00B0p1p2le"
                    read_cmd = f'AT+CSIM=10,"00B0{p1_hex}{p2_hex}{le_hex}"'
                    raw_data = comm.send_command(read_cmd)
                elif adf_type == "ISIM":
                    # 例如 AT+CGLA=1,10,"01B0p1p2le"
                    read_cmd = f'AT+CGLA=1,10,"01B0{p1_hex}{p2_hex}{le_hex}"'
                    raw_data = comm.send_command(read_cmd)
                    if raw_data == "ERROR":
                        read_cmd = f'AT+CSIM=10,"01B0{p1_hex}{p2_hex}{le_hex}"'
                        raw_data = comm.send_command(read_cmd)
                else:
                    return "error: undefined adf type"

                
                logging.debug("[read_ef_data] 发送读取命令: %s, 返回: %s", read_cmd, raw_data)
                # 下面的 response_format( ) 根据你的逻辑，能拿到纯 payload
                payload = response_format(raw_data, le_hex)

                if payload is None or payload.startswith("error:"):
                    logging.error("[read_ef_data] 读取分段失败: %s", payload)
                    return payload  # 或者可以继续读其他分段，但一般是直接报错退出

                # 累加到我们的拼接字符串
                result_hex += payload
                offset += this_chunk_size

            # 最后，把整个文件（若需要的话）当做数组的第一个元素传回
            data_list.append(result_hex)

        elif ef_structure in ["linear", "cyclic"]:
            ins = "B2"
            recorder = hex(int(fcp_data["recorder"], 16))
            #p1 = "00"
            p2 = "04"  #02: read next,03: read previous; 04: read current
            length = fcp_data["record_length"].lstrip("0").zfill(2)
            if len(length) > 2:
                length = "FF"         
            max_p1 = int(fcp_data["recorder"], 16)  # p1=0的时候循环次数，P1 非0时候，P1最大数  
            logging.info('[read_ef_data] record 个数: %s =>数据读取中...', max_p1)
            ffff_count = 0

            for p1_value in range(1, max_p1 + 1):  # 从 1 循环到 max_p1
                p1 = hex(p1_value)[2:].zfill(2)  # 当P1非0的时候使用，转换为十六进制并填充为两位
                if adf_type == "USIM" or adf_type == "MF":                   
                    read_cmd = f'AT+CSIM=10,"00{ins}{p1}{p2}{length}"'.upper()
                    raw_data = comm.send_command(read_cmd)    
                elif adf_type == "ISIM":                    
                    read_cmd = f'AT+CGLA=1,10,"01{ins}{p1}{p2}{length}"'.upper()
                    raw_data = comm.send_command(read_cmd)    
                    if raw_data == "ERROR":
                        read_cmd = f'AT+CSIM=10,"01{ins}{p1}{p2}{length}"'.upper()
                        raw_data = comm.send_command(read_cmd)

                logging.debug("[read_ef_data] 发送读取命令: %s, 返回: %s", read_cmd, raw_data)
                response = response_format(raw_data, length)

                if response is None:                
                    ffff_count += 1   
                else:  # 仅在响应不为 None 时添加                   
                    data_list.append(response)
        else:
            logging.error("[read_ef_data] 未知EF结构: %s", ef_structure)
            return "error: unknown EF structure"

        if data_list and isinstance(data_list[0], str) and data_list[0].startswith("error"):
            return data_list[0]
        logging.info("[read_ef_data] EF文件读取完毕, 数据条数: %s", len(data_list))
        return data_list
        

    except Exception as e:
        logging.error("[read_ef_data] 读取文件失败: %s", e)
        return "error: read file failed"
        
def response_format(raw_data, length=1):
    """格式化SIM卡响应数据，处理错误码和数据截取"""
    try:

        length = int(length, 16) * 2 if isinstance(length, str) and all(c in '0123456789abcdefABCDEF' for c in length) else 0 


        if raw_data.endswith('9000'):
            response = raw_data[:-4]
        else:
            error_msg = parse_sim_error(raw_data)
            logging.error("[response_format] 当前读取失败 - 错误码: %s, 含义: %s", raw_data, error_msg) 
            return f"error: {error_msg}"

        if length != 0:
            response = response[:length]
        logging.info("[response_format] 格式化AT返回的数据: %s", response)

        return response

    except Exception as e:
        logging.error("[response_format] 处理响应失败: %s", e) 
        return "error: process response failed"  # 抛出错误时返回 None
    
def write_ef_data(comm: SerialComm, encoded_user_data, adf_type, ef_structure, record_index) -> str:
    """写入EF文件数据，支持transparent/linear/cyclic结构"""
    logging.info("[write_ef_data] 写入EF数据, 类型: %s, 结构: %s, 记录索引: %s", adf_type, ef_structure, record_index)
    # ---------- ① encoded_user_data 合法性 ----------
    if not encoded_user_data or any(c not in "0123456789ABCDEFabcdef" for c in encoded_user_data):
        logging.error("[write_ef_data] encoded_user_data 不是合法的十六进制串: %s", encoded_user_data)
        return "error: encoded_user_data not hex"
    if len(encoded_user_data) % 2 != 0:
        logging.error("[write_ef_data] encoded_user_data 长度必须为偶数 (字节对): %s", encoded_user_data)
        return "error: encoded_user_data length odd"

    # ---------- ② record_index 合法性 ----------
    try:
        record_index_int = int(record_index)
    except (TypeError, ValueError):
        logging.error("[write_ef_data] record_index 不是有效整数: %s", record_index)
        return "error: record_index must be int"
    if not 1 <= record_index_int <= 255:
        logging.error("[write_ef_data] record_index 超出范围: %s", record_index)
        return "error: record_index out of range (1-255)"

    encoded_user_data = encoded_user_data.upper()
    length = len(encoded_user_data)
    hex_length = f"{(length // 2):02X}"
    cmd_length = length + 10
    record_index = f"{record_index_int:02X}"

    
    try:
        if adf_type == "USIM" or adf_type == "MF":
            if ef_structure == "transparent":
                if len(encoded_user_data) > 510:
                     # 分段写
                    return _chunked_write_transparent(comm, encoded_user_data, adf_type)
                else:
                    cmd = f'AT+CSIM={cmd_length},"00D60000{hex_length}{encoded_user_data}"'.upper()
                    response = comm.send_command(cmd)
            elif ef_structure == "linear" or ef_structure == "cyclic":
                cmd = f'AT+CSIM={cmd_length},"00DC{record_index}04{hex_length}{encoded_user_data}"'.upper()
                response = comm.send_command(cmd)
            else:
                logging.error("[write_ef_data] unknown ef_structure")
                return "error: unknown ef_structure"

        elif adf_type == "ISIM":
            if ef_structure == "transparent":
                if len(encoded_user_data) > 510:
                    # 分段写
                    return _chunked_write_transparent(comm, encoded_user_data, adf_type)
                else:
                    cmd = f'AT+CGLA=1,{cmd_length},"00D60000{hex_length}{encoded_user_data}"'.upper()
                    response = comm.send_command(cmd)
                    if response == "ERROR":
                        cmd = f'AT+CSIM={cmd_length},"01D60000{hex_length}{encoded_user_data}"'.upper()
                        response = comm.send_command(cmd)
            elif ef_structure == "linear" or ef_structure == "cyclic":
                cmd = f'AT+CGLA=1,{cmd_length},"00DC{record_index}04{hex_length}{encoded_user_data}"'.upper()
                response = comm.send_command(cmd)
                if response == "ERROR":
                    cmd = f'AT+CSIM={cmd_length},"01DC{record_index}04{hex_length}{encoded_user_data}"'.upper()
                    response = comm.send_command(cmd)
            else:
                logging.error("[write_ef_data] unknown ef_structure")
                return "error: unknown ef_structure"
            
        else:
            logging.error("[write_ef_data] 不支持的应用类型: %s", adf_type)
            return "error: unsupported ADF"
        logging.info("[write_ef_data] 写入文件结果: %s", response)
        return response        
        
    except Exception as e:
        logging.error("[write_ef_data] 写入文件失败: %s", e)
        return "error: write file failed"



def _chunked_write_transparent(comm, encoded_hex_data: str, adf_type: str) -> str:
    """分块写 Transparent EF 文件（每次最多255字节）"""
    # 数据总字节数
    total_length = len(encoded_hex_data) // 2
    offset = 0
    CHUNK_SIZE = 255  # 每次最多写255字节
    while offset < total_length:
        this_chunk_size = min(CHUNK_SIZE, total_length - offset)
        # 取子串(对应 this_chunk_size 字节)
        chunk_hex = encoded_hex_data[offset*2 : offset*2 + this_chunk_size*2]

        # 计算 P1P2 = 偏移量（高位, 低位）
        p1 = (offset >> 8) & 0xFF
        p2 = offset & 0xFF
        p1_hex = f"{p1:02X}"
        p2_hex = f"{p2:02X}"
        lc_hex = f"{this_chunk_size:02X}"

        # 组装 APDU
        apdu_hex = f"00D6{p1_hex}{p2_hex}{lc_hex}{chunk_hex}".upper()

        # 对于 USIM/MF：AT+CSIM
        # 对于 ISIM：AT+CGLA
        if adf_type.upper() in ["USIM", "MF"]:
            cmd_length = 10 + this_chunk_size * 2
            cmd = f'AT+CSIM={cmd_length},"{apdu_hex}"'
        elif adf_type.upper() == "ISIM":
            cmd_length = 10 + this_chunk_size * 2
            cmd = f'AT+CGLA=1,{cmd_length},"{apdu_hex}"'
            response = comm.send_command(cmd)
            if response == "ERROR":
                modified_apdu = "01" + apdu_hex[2:]
                cmd = f'AT+CSIM={cmd_length},"{modified_apdu}"'
                response = comm.send_command(cmd)
        else:
            return f"error: unsupported ADF => {adf_type}"

        response = comm.send_command(cmd)
        logging.debug("[_chunked_write_transparent] 写入分块: offset=%s, size=%s, 返回: %s", offset, this_chunk_size, response)
        if not response.endswith("9000"):
            logging.error("[_chunked_write_transparent] 分块写入失败: %s", response)
            return f"error: write chunk fail => {response}"
        
        # 偏移量前移
        offset += this_chunk_size

    return "9000"


def admin(comm: SerialComm, pin):
    """输入管理员PIN码，进行权限验证"""
    if len(pin) != 8:
        logging.error("[admin] admin pin 长度必须是8位: %s", pin)
        return "error: admin pin 长度必须是8位"
    pin = ascii_text_to_hex(pin)
    logging.info("[admin] 管理员PIN已转换: %s", pin)
    pin_length = len(pin) + 10

    cmd_len = f"{int(len(pin)/2):02X}"  # 转换为16进制并补足2位
    cmd = f'AT+CSIM={pin_length},"0020000A{cmd_len}{pin}"'
    response = comm.send_command(cmd)
    logging.info("[admin] 管理员PIN验证响应: %s", response)
    return response

def reset_sim(comm: SerialComm):
    """重置SIM卡，关闭/重启Modem并检测SIM状态"""
    logging.info("[reset_sim] 开始重置SIM卡...")
    # 判断是高通还是MTK平台
    cmd = 'AT+CGLA=?'
    response = comm.send_command(cmd)
    if response == "ERROR":
        comm.send_command('AT+CFUN=1,1')  # 重新打开 Modem，用于高通平台
        time.sleep(15)
    else:
        comm.send_command('AT+CSIM=14,"00A4000C023F00"')  # reset SIM，用于MTK平台
        time.sleep(20)

        # 轮询等待 SIM 卡恢复
        for i in range(10):  # 最多等待 10 秒
            time.sleep(1)
            response = comm.send_command('AT+CPIN?')
            logging.info("[reset_sim] 检查SIM状态 (%s/10): %s", i+1, response)
            if "READY" in response:
                logging.info("[reset_sim] SIM卡已准备好！")
                return
            else:
                logging.error("[reset_sim] SIM卡未检测到，response: %s", response)
                return
        logging.warning("[reset_sim] 警告: SIM reset timeout, 但继续执行。")

        
def save_json(file_path, data):
    """将读取的SIM卡数据保存为JSON文件"""
    json_path = os.path.join(JSON_DIR, f"{file_path}.json")
    
    try:
        # **确保数据格式为 { "EF_ID": [ {...} ] }**
        if not isinstance(data, list):
            data = [data]

        json_data = {file_path: data}

        with open(json_path, "w", encoding="utf-8") as json_file:
            json.dump(json_data, json_file, ensure_ascii=False, indent=4)
        logging.info("[save_json] 保存JSON成功: %s", json_path)    
    except Exception as e:
        logging.error("[save_json] 保存JSON失败: %s", e)


def load_json(file_path):
    """从JSON文件加载数据，返回字典结构"""
    json_path = os.path.join(JSON_DIR, f"{file_path}.json")
    if not os.path.exists(json_path):
        logging.warning("[load_json] JSON文件不存在: %s", json_path)
        return None

    try:
        with open(json_path, "r", encoding="utf-8") as json_file:
            json_data = json.load(json_file)
            
        # 校验json结构:EF_ID必须为字符串，EF_ID 的值是否是 list，list 内的每个元素是否是 dict，EF_ID 是否是合法的 16 进制
        if not isinstance(json_data, dict):
            logging.error("[load_json] JSON结构不是字典")
            return "error: JSON structure is not a dict"

        for k, v in json_data.items():
            if not isinstance(k, str) or not k.isalnum():
                logging.error("[load_json] EF_ID无效: %s", k)
                return f"error: Invalid EF_ID '{k}'."
            if not isinstance(v, list):
                logging.error("[load_json] EF_ID '%s' 必须为记录列表", k)
                return f"error: EF_ID '{k}' must have a list of records."
            if not all(isinstance(i, dict) for i in v):
                logging.error("[load_json] EF_ID '%s' 的记录必须为字典", k)
                return f"error: EF_ID '{k}' must contain a list of dictionaries."

        logging.info("[load_json] 加载JSON成功: %s", json_path)
        return json_data  # 正确返回 JSON 数据

    except Exception as e:
        logging.error("[load_json] 加载JSON失败: %s", e)
        return "error: load JSON failed"

    
def delete_ef(comm: SerialComm, ef_id, adf):
    """删除EF文件，支持多种ADF类型"""
    try:
        # 检查是否为受保护的 EF ID
        protected_ef_ids = ["6F06", "2F00", "2F06"]
        if ef_id in protected_ef_ids:
            logging.error("[delete_ef] 不允许删除受保护的EF文件: %s", ef_id)
            return "error: protected EF file cannot be deleted"

        if adf == "5G-EF":
            cmd = f'AT+CSIM=14,"00A40004025FC0"'
            comm.send_command(cmd)
            time.sleep(0.5)
            if len(ef_id) == 4:
                cmd = f'AT+CSIM=14,"00E4000002{ef_id}"'.upper()  
            elif len(ef_id) == 8:
                cmd = f'AT+CSIM=18,"00E4000004{ef_id}"'.upper()
            else:
                return "error: unsupported EF ID length"
        elif adf == "USIM" or adf == "DF":
            if len(ef_id) == 4:
                cmd = f'AT+CSIM=14,"00E4000002{ef_id}"'.upper()
            elif len(ef_id) == 8 and ef_id.startswith("5FC0"):
                cmd = f'AT+CSIM=14,"00A40004025FC0"'
                comm.send_command(cmd)
                time.sleep(0.5)
                ef_id = ef_id[4:]
                cmd = f'AT+CSIM=14,"00E4000002{ef_id}"'.upper()

            else:
                return "error: unsupported EF ID length"
        elif adf == "ISIM":
            cmd = f'AT+CGLA=1,14,"00E4000002{ef_id}"'.upper()
        else:
            return "error: unsupported ADF"

        response = comm.send_command(cmd)
        logging.info("[delete_ef] 删除文件%s结果: %s", ef_id, response)
        return response
    except Exception as e:
        logging.error("[delete_ef] 删除EF %s异常: %s", ef_id, e)
        return "error: exception"


def create_file(comm: SerialComm, ef_id, length, adf, structure, record_num, security_Attributes, sfi):
    """创建EF文件，支持transparent/linear结构"""
    try:
        if not ef_id:
            return "error: EF ID cannot be empty"
        length_int = int(length)
        if length_int <= 0 or length_int > 0xFFFF:
            return "error: length out of range"
        length_hex = f"{length_int:04X}"

        if not security_Attributes:
            security_Attributes = "6F0606"  # 默认值

        if not sfi or not sfi.isdigit():
            sfi = "8800"
        else:
            sfi = f"8801{sfi}"

        life_cycle = "05"       
        # proprietary = "C00100"  
        length_ef_id = len(ef_id)
        cmd = None  # 先初始化 cmd，避免后续使用未定义        
        if adf == "DF":
            apdu_hex = f"00E0000021621F820278218302{ef_id}8A01058B03{security_Attributes}8102{length_hex}C609900180830181830101"
        else:
            if structure == "transparent":
                if length_ef_id == 8:
                    ef_id = ef_id[4:]
                if sfi == "8800":
                    apdu_hex = f"00E00000186216820241218302{ef_id}8A01{life_cycle}8B03{security_Attributes}8002{length_hex}8800"
                else:
                    apdu_hex = f"00E00000196217820241218302{ef_id}8A01{life_cycle}8B03{security_Attributes}8002{length_hex}{sfi}"
            
            elif structure == "linear":
                if length_ef_id == 8:
                    ef_id = ef_id[4:]
                logging.info("[create_file] linear structure, length: %s, record_num: %s, length_hex: %s", length, record_num, length_hex)
                file_size = int(length) * int(record_num)
                logging.info("[create_file] file_size: %s", file_size)
                file_size_hex = f"{file_size:04X}"		
                if sfi == "8800":
                    apdu_hex = f"00E000001A621882044221{length_hex}8302{ef_id}8A01{life_cycle}8B03{security_Attributes}8002{file_size_hex}8800"
                else:
                    apdu_hex = f"00E000001B621982044221{length_hex}8302{ef_id}8A01{life_cycle}8B03{security_Attributes}8002{file_size_hex}{sfi}"	
        
            

        if adf == "USIM":
            if length_ef_id == 8:
                cmd = f'AT+CSIM=14,"00A40004025FC0"'
                response = comm.send_command(cmd)
                if "9000" not in response:
                    error_msg = parse_sim_error(response)
                    logging.info("[create_file] DF 5FC0文件不存在%s", error_msg)
                    return f"error: {error_msg}"
            cmd = f'AT+CSIM={len(apdu_hex)},"{apdu_hex}"'.upper()
        elif adf == "DF":
            cmd = f'AT+CSIM={len(apdu_hex)},"{apdu_hex}"'.upper()
            time.sleep(0.5)
        elif adf == "5G-EF":
            cmd = f'AT+CSIM=14,"00A40004025FC0"'
            response = comm.send_command(cmd)
            if "9000" not in response:
                error_msg = parse_sim_error(response)
                logging.info("[create_file] DF 5FC0文件不存在%s", error_msg)
                return f"error: {error_msg}"
            time.sleep(0.5)
            cmd = f'AT+CSIM={len(apdu_hex)},"{apdu_hex}"'.upper()
        elif adf == "ISIM":
            cmd = f'AT+CGLA=1,{len(apdu_hex)},"{apdu_hex}"'.upper() 
        elif adf == "MF":
            return "error: MF is not supported"
        if cmd:
            response = comm.send_command(cmd)
            if "9000" not in response:
                error_msg = parse_sim_error(response)
                logging.info("[create_file] 创建文件%s失败: %s", ef_id, error_msg)
                return f"error: {error_msg}"
            else:
                if adf == "DF":
                    time.sleep(1)
                    reset_sim(comm)
                logging.info("[create_file] 创建文件%s成功: %s", ef_id, response)

                return response
        else:
            logging.error("[create_file] 创建文件%s失败: 未生成有效命令", ef_id)
            return "error: no valid command generated"

    except Exception as e:
        logging.error("[create_file] 创建文件%s异常: %s", ef_id, e)
        return "error: exception"





