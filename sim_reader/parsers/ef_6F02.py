"""
    数据结构:
        {
            "IMPI": ""
        }
"""
from parsers.general import ascii_text_to_hex, TLV_parser, TLV_encode
import logging
from core.serial_comm import SerialComm
import time
def parse_data(raw_data: str) -> None:
    results = []    
    raw_data = raw_data[0]
    encode_userdata = TLV_parser(raw_data)
    results.append({"IMPI": encode_userdata})
    return results


def encode_data(user_data: dict, ef_file_len_decimal: int) -> str:
    try:
        encode_userdata = user_data.get('IMPI', '')
        encode_userdata = ascii_text_to_hex(encode_userdata)        #TLV 结构Value部分
        encode_userdata = TLV_encode(encode_userdata)
        if len(encode_userdata) <= ef_file_len_decimal * 2:
            encode_userdata = encode_userdata.ljust(ef_file_len_decimal * 2, 'F')
        else:
            data_len = len(encode_userdata) // 2
            hex_data_len = f"{data_len:02X}"
            # 保证是偶数位 hex（避免长度>0xFF 时出现奇数位）
            if len(hex_data_len) % 2 != 0:
                hex_data_len = "0" + hex_data_len

            logging.debug(
                "IMPI longer than current EF (%d > %d), try resize via D4 first (6F02)",
                data_len, ef_file_len_decimal
            )

            comm = SerialComm()

            # ① 先尝试 AT+CGLA 走 80D4
            cmd1 = f'AT+CGLA=1,30,"80D400000A620883026F02800200{hex_data_len}"'
            resp1 = comm.send_command(cmd1)
            time.sleep(1)
            resp1_u = (resp1 or "").upper()
            logging.debug("[6F02][resize] cmd1=%s resp1=%s", cmd1, resp1_u)
            if resp1_u.endswith("9000"):
                return f"RESIZED:{encode_userdata}"

            # ② 只要不是 9000（包含 6A82 / ERROR / error:...），再尝试 AT+CSIM 走 81D4
            cmd2 = f'AT+CSIM=30,"81D400000A620883026F02800200{hex_data_len}"'
            resp2 = comm.send_command(cmd2)
            time.sleep(1)
            resp2_u = (resp2 or "").upper()
            logging.debug("[6F02][resize] cmd2=%s resp2=%s", cmd2, resp2_u)
            if resp2_u.endswith("9000"):
                return f"RESIZED:{encode_userdata}"

            # 两条都失败：不拦截，继续走后续流程（上层 write_data() 可能会走 delete/create 扩容）
            logging.debug("[6F02][resize] D4 resize failed, fallback to normal flow (resp1=%s, resp2=%s)", resp1_u, resp2_u)
              
        return encode_userdata
            
    except Exception as e:
        encode_userdata = f"error: 未知错误 - {str(e)}"
        return encode_userdata    

