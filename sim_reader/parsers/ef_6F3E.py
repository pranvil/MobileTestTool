"""
    根据spec 31.102(chapter:4.2.9)解析Group Identifier Level 1数据
    1. 移除填充位F
    2. 两两互换
    3. Group Identifier Level 1从第3位开始取值
    数据结构:
        {   
            "Group Identifier Level 1": ""
        }
"""
import logging
from core.serial_comm import SerialComm
import time

def parse_data(raw_data: str) -> None:
    logging.debug("收到的数据：%s", raw_data)
    results = []
    gid1 = ""
    for data in raw_data:
        gid1 = data
        result = {
            "Group Identifier Level 1": gid1
        }
        results.append(result)
    return results

def encode_data(user_data: dict, ef_file_len_decimal: int) -> str:
    try:
        # Step 1: 获取原始字段
        raw_data = user_data.get('Group Identifier Level 1', '')
        if not raw_data:
            return "error: user_data['Group Identifier Level 1'] is empty"

        # Step 2: 补F（如果奇数字符）
        encode_userdata = raw_data
        if len(encode_userdata) % 2 != 0:
            encode_userdata += 'F'

        # Step 3: 判断是否需要 resize
        if len(encode_userdata) != ef_file_len_decimal * 2:
            # 需要 resize，执行 resize 过程
            comm = SerialComm()


            # 重新设置长度
            data_len = len(encode_userdata) // 2
            hex_data_len = f"{data_len:02X}"

            cmd = f'AT+CSIM=30,"80D400000A620883026F3E800200{hex_data_len}"'
            response = comm.send_command(cmd)
            time.sleep(1)

            # 检查80D4是否成功，如果成功则标记已resize
            if response and "9000" in response:
                logging.debug("EF数据编码成功 - ID: 6F3E, 结果: %s", encode_userdata)
                # 返回特殊标记，表示已通过80D4完成resize，避免write_data重复处理
                return f"RESIZED:{encode_userdata}"

        # Step 4: 最后统一返回原始 Group Identifier Level 1 字段
        return encode_userdata

    except Exception as e:
        return f"error: 未知错误 - {str(e)}"
