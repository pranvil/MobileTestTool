from core.serial_comm import SerialComm
from core.data_handler import read_ef_data, write_ef_data, select_adf, save_json
from core.data_handler import delete_ef as delete_ef_cmd, create_file as create_file_cmd

from parsers.fcp_parser import parse_fcp_data
import os
import json
import logging
from parser_dispatcher import parse_ef_data, encode_ef_data
import time
from tree_manager import TreeManager


def resize_ef(
        sim: "SimService",              # 直接复用现有实例
        ef_id: str,
        new_len: int,                   # 目标长度(字节)
        adf: str,
        structure: str = "transparent",
        record_num: int = 1,
        security_attrs: str = "",
        sfi: str = ""
) -> str:
    """
    调整 EF 大小（先删后建）。
    - 自动探测旧文件属性；若探测失败则使用形参。
    - 仅当 delete / create 均返回 '9000' 才算成功。
    """
    logging.info("[resize_ef] 开始调整EF大小: ef_id=%s, new_len=%d,record_num=%d, adf=%s", ef_id, new_len, record_num, adf)
    # ---------- ① 获取旧文件信息 ----------
    ef_info = sim.get_ef_structure(adf, ef_id)
    if ef_info:
        structure      = ef_info.get("ef_structure", structure)
        security_attrs = ef_info.get("sec_attr",     security_attrs)
        sfi_from_card  = ef_info.get("sfi", "")
        if sfi_from_card:
            sfi = sfi_from_card
        if structure.lower() == "linear":
            # recorder 返回十六进制个数
            record_num_hex = format(int(record_num), '02X')  # 将record_num转换为两位16进制字符串
            # 仅当 recorder 是合法十六进制串时才转换
            if record_num_hex and record_num_hex.lower() != "none":
                try:
                    record_num = int(record_num_hex, 16)
                except ValueError:
                    logging.warning("[resize_ef] recorder 字段异常 (%s)，已回退为 1", record_num_hex)
                    record_num = 1
            else:
                record_num = 1        # 没写 / =none → 默认 1            

    # ---------- ② 删除旧文件 ----------
    del_rsp = delete_ef_cmd(sim.comm, ef_id, adf)
    if not del_rsp.endswith("9000") and not del_rsp.endswith("6A82"):
        # 6A82 = 文件不存在，可忽略
        logging.error("[resize_ef] delete_ef %s failed => %s", ef_id, del_rsp)
        return del_rsp

    # ---------- ③ 创建新文件 ----------
    file_len = new_len

    crt_rsp = create_file_cmd(
        sim.comm, ef_id, file_len, adf,
        structure, record_num, security_attrs, sfi
    )
    if not crt_rsp.endswith("9000"):
        logging.error("[resize_ef] create_file %s failed => %s", ef_id, crt_rsp)
        return crt_rsp

    logging.info("[resize_ef] resize_ef %s to %d bytes success", ef_id, new_len)
    return "9000"



class SimService:
    def __init__(self):
        self.comm = SerialComm()
        self.tree_manager = TreeManager(None)

    def get_ef_structure(self, adf_type, ef_id):
        """获取 EF 文件的结构信息，返回字典"""
        logging.info("[get_ef_structure] 获取EF结构: adf_type=%s, ef_id=%s", adf_type, ef_id)
        try:
            fcp_data = select_adf(self.comm, adf_type, ef_id)

            if not fcp_data:
                logging.error("[get_ef_structure] Select EF %s 返回空响应", ef_id)
                return None
        # ---------- (1) 仅 4 字节 SW 的场景 ----------
            import re
            from core.data_handler import parse_sim_error
            if re.fullmatch(r"[0-9A-Fa-f]{4}", fcp_data):
                # 纯状态字，如 6A82
                logging.error("[get_ef_structure] Select EF %s 失败 → SW=%s (%s)",
                            ef_id, fcp_data, parse_sim_error(fcp_data))
                return None  # 上层可按 None 处理
            # ef_info = parse_fcp_data(fcp_data)

            # # 确保 fcp_data 是字典
            
            # if not isinstance(ef_info, dict):
            #     logging.error("Unexpected data format for EF %s: %s", ef_id, ef_info)
            #     return None
            ef_info = parse_fcp_data(fcp_data)

            # ---------- (2) parse_fcp_data 异常格式 ----------
            if not isinstance(ef_info, dict):
                logging.error("[get_ef_structure] parse_fcp_data 返回非 dict，EF %s。raw=%s", ef_id, fcp_data)
                return None

            logging.debug("[get_ef_structure] EF结构: %s", ef_info)
            return ef_info  # 返回字典
        except Exception as e:
            logging.error("[get_ef_structure] error getting EF structure: %s", e)
            return None


    def read_data(self, adf_type, ef_id, save_single=False, force_raw=False):
        """
        读取指定 EF，并解析。
        如果 save_single=True，则额外保存一个类似 { "EF_list": [ { "ef_id":..., "adf_type":..., "records":[...]} ] } 的单EF文件。
        """
        logging.info("[read_data] 读取EF数据: adf_type=%s, ef_id=%s", adf_type, ef_id)
        try:
            fcp_data = select_adf(self.comm, adf_type, ef_id)
            ef_info = parse_fcp_data(fcp_data)
            if isinstance(ef_info, str) and ef_info.startswith("error"):
                logging.error("[read_data] 解析FCP失败: %s", ef_info)
                return ef_info

            raw_data = read_ef_data(self.comm, ef_info, adf_type)
            if isinstance(raw_data, str) and raw_data.startswith("error"):
                logging.error("[read_data] 读取原始数据失败: %s", raw_data)
                return raw_data

            if force_raw:  
                from parsers.ef_default import parse_data as raw_parser
                parsed_data = raw_parser(raw_data)
            else:
                parsed_data = parse_ef_data(ef_id, raw_data)
            if isinstance(parsed_data, str) and parsed_data.startswith("error"):
                logging.error("[read_data] 解析EF数据失败: %s", parsed_data)
                return parsed_data

            # 如果是单次读取场景，需要输出一个单EF文件 => 采用新的 EF_list 结构
            if save_single:
                self._save_ef_list_after_single_read(adf_type, ef_id, parsed_data)

            logging.info("[read_data] 读取并解析EF数据成功: ef_id=%s", ef_id)
            return parsed_data

        except Exception as e:
            logging.error("[read_data] 读取数据失败: %s", e)
            return f"error: exception => {e}"



    def _save_ef_list_after_single_read(self, adf_type: str, ef_id: str, records_list: list):
        """
        将单次读取的 EF 数据，保存为 { "EF_list": [ { "ef_id":..., "adf_type":..., "records":[...] } ] }
        文件名: "json_data/USIM_6F07_IMSI.json"  (或 ISIM_6F07_IMSI.json 等)
        """
        # 获取 EF 文件名称
        ef_name = ""
        for name, id in self.tree_manager.file_paths.items():
            if id == ef_id:
                ef_name = name
                break

        # 构造文件名，如果找到 EF 名称则添加，否则保持原样
        file_name = f"{adf_type}_{ef_id}".upper()
        if ef_name:
            file_name = f"{file_name}_{ef_name}"
        json_path = os.path.join("json_data", file_name + ".json")

        # 构造一个 EF_list，只包含当前这个 EF
        ef_obj = {
            "ef_id": ef_id.upper(),
            "adf_type": adf_type.upper(),
            "records": records_list   # 这里 parsed_data 一般是 list[dict]
        }
        final_data = {
            "EF_list": [ef_obj]
        }

        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(final_data, f, ensure_ascii=False, indent=4)
            logging.info("[_save_ef_list_after_single_read] 单次读取, EF:%s => 数据已保存到 %s", ef_id, json_path)
        except Exception as e:
            logging.error("[_save_ef_list_after_single_read] 保存单次读取结果失败: %s", e)




    def write_data(self, user_data, ef_info, adf_type, ef_id, record_index=1, force_raw=False):
        """
        写卡的统一入口：
        · 先调用对应 parser 的 encode_data() 得到编码串
        · 如果长度超出 →  resize_ef()  →  重新补齐到新长度
        · 最终调用 data_handler.write_ef_data() 写入
        """
        logging.info("[write_data] 写入EF数据: ef_id=%s, adf_type=%s, record_index=%s", ef_id, adf_type, record_index)
        try:
            # ---------- ① 基本信息 ----------
            ef_structure = ef_info.get("ef_structure", "transparent")
            if ef_structure == "transparent":
                file_size_hex = ef_info.get("file_length", "00")
                ef_number_of_records = 1
            else:  # linear / cyclic
                file_size_hex = ef_info.get("record_length", "00")
                ef_number_of_records = int(ef_info.get("recorder", "01"), 16)

            ef_file_len_decimal = int(file_size_hex, 16)

            # ---------- ② 首次编码 ----------
        
            if force_raw:
                from parsers.ef_default import encode_data as raw_encoder
                encode_userdata = raw_encoder(user_data, ef_file_len_decimal)
            else:
                encode_userdata = encode_ef_data(ef_id, user_data, ef_file_len_decimal)

            if isinstance(encode_userdata, str) and encode_userdata.startswith("error"):
                logging.error("[write_data] 编码数据失败: %s", encode_userdata)
                return encode_userdata

            # ---------- ③ 检查是否已通过80D4完成resize ----------
            already_resized = False
            if isinstance(encode_userdata, str) and encode_userdata.startswith("RESIZED:"):
                # 已通过80D4完成resize，提取实际数据
                encode_userdata = encode_userdata[8:]  # 移除"RESIZED:"前缀
                already_resized = True
                logging.info("[write_data] 检测到80D4已成功resize，跳过重复resize操作")

            # ---------- ④ 判断是否需要 resize ----------
            if not already_resized and len(encode_userdata) > ef_file_len_decimal * 2:
                # 需要扩容，新长度 = 实际字节数
                new_len = len(encode_userdata) // 2
                security_attributes = ef_info.get("sec_attr", "")
                logging.info("[write_data] 数据超长，自动扩容EF: ef_id=%s, new_len=%d", ef_id, new_len)
                resize_result = resize_ef(self, ef_id, new_len, adf_type, ef_structure,
                    ef_number_of_records, security_attributes, sfi=""
                )
                if resize_result != "9000":
                    logging.error("[write_data] resize_ef失败: %s", resize_result)
                    return f"error: resize_ef failed → {resize_result}"

                # 重新获取最新 EF 结构 / 长度
                ef_info = self.get_ef_structure(adf_type, ef_id)
                if not ef_info:
                    logging.error("[write_data] 获取新EF信息失败")
                    return "error: 获取新 EF 信息失败"

                if ef_structure == "transparent":
                    ef_file_len_decimal = int(ef_info["file_length"], 16)
                else:
                    ef_file_len_decimal = int(ef_info["record_length"], 16)

                # 重新右补 F 到新长度
                encode_userdata = encode_userdata.ljust(ef_file_len_decimal * 2, "F")

            # ---------- ⑤ 最终写卡 ----------
            logging.debug("[write_data] 最终写入数据: %s", encode_userdata)
            return write_ef_data(
                self.comm, encode_userdata, adf_type, ef_structure, record_index
            )

        except Exception as e:
            logging.error("[write_data] exception: %s", e)
            return "error: exception"



    # 更新单条记录
    def update_single_record(self, adf_type: str, ef_id: str, row_index: int, input_values: dict, force_raw=False) -> str:
        """
        更新某个 EF 的单条记录:
        1. 获取 EF 结构
        2. 判断 transparent / linear / cyclic
        3. 分发到相应的私有方法
        4. 在保存到 JSON 时，使用 {"EF_list":[ {...} ]} 结构
        """
        logging.info("[update_single_record] 更新单条记录: ef_id=%s, row_index=%d", ef_id, row_index)
        ef_info = self.get_ef_structure(adf_type, ef_id)
        if not ef_info:
            logging.error("[update_single_record] 卡文件不存在: ef_id=%s", ef_id)
            return "error: 卡文件不存在"

        ef_structure = ef_info.get("ef_structure", "transparent")

        if ef_structure in ["transparent"]:
            # 透明 EF
            return self._update_transparent_ef(adf_type, ef_id, input_values, ef_info, force_raw)
        elif ef_structure in ["linear", "cyclic"]:
            # 线性或循环文件
            return self._update_linear_ef(adf_type, ef_id, row_index, input_values, ef_info, force_raw)
        else:
            logging.error("[update_single_record] 未知EF结构: %s", ef_structure)
            return f"error: unknown EF structure '{ef_structure}'"

    def _update_transparent_ef(self, adf_type: str, ef_id: str, input_values: dict, ef_info: dict, force_raw=False) -> str:
        """
        透明 EF:
          - row_index 恒定1(仅1条记录)
          - 不需要 JSON 里多条记录，但仍然用相同结构 { "EF_list":[ { "ef_id":"...", "adf_type":"...", "records":[ {...} ] } ] }
        """
        logging.info("[_update_transparent_ef] 更新透明EF: ef_id=%s", ef_id)
        # 直接写入 SIM
        result = self.write_data(input_values, ef_info, adf_type, ef_id, record_index=1, force_raw=force_raw)
        return result

    def _update_linear_ef(self, adf_type: str, ef_id: str, row_index: int, input_values: dict, ef_info: dict, force_raw=False) -> str:
        """
        线性/循环 EF:
          - 有多条记录 => row_index 指定要更新哪一条
          - 同样使用 EF_list 结构的 JSON
        """
        logging.info("[_update_linear_ef] 更新线性/循环EF: ef_id=%s, row_index=%d", ef_id, row_index)
        # 1) 检查记录数
        recorder_value = ef_info.get("recorder", "1")
        if not recorder_value or recorder_value.lower() == "none":
            recorder_value = "1"
        max_records = int(recorder_value, 16)
        if row_index < 0 or row_index >= max_records:
            logging.error("[_update_linear_ef] row_index %d 超出范围 (max %d)", row_index, max_records)
            return f"error: row_index {row_index} out of range (max {max_records})"

        # 直接写入 SIM
        result = self.write_data(input_values, ef_info, adf_type, ef_id, record_index=row_index + 1, force_raw=force_raw)
        return result

    def _load_or_create_file_list(self, adf_type: str, ef_id: str):
        """
        读取 { "EF_list": [...] } JSON，如果不存在或不合法则创建新的
        文件名示例:  "json_data/USIM_6F07.json"
        """
        file_name = f"{adf_type}_{ef_id}.json".upper()
        json_path = os.path.join("json_data", file_name)

        if not os.path.exists(json_path):
            # 文件不存在 => 新建
            ef_obj = {
                "ef_id": ef_id.upper(),
                "adf_type": adf_type.upper(),
                "records": []
            }
            logging.info("[_load_or_create_file_list] 新建EF_list文件: %s", json_path)
            return [ef_obj]  # ef_list 只有1个对象
        else:
            # 文件已存在 => 读取
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                logging.error("[_load_or_create_file_list] 加载EF文件失败 %s: %s", json_path, e)
                # 如果损坏/无效 => 新建
                return []

            if not isinstance(data, dict) or "EF_list" not in data:
                logging.warning("[_load_or_create_file_list] 文件 %s 格式不正确, 重新初始化", json_path)
                return []

            ef_list = data["EF_list"]
            if not isinstance(ef_list, list):
                ef_list = []
            logging.info("[_load_or_create_file_list] 加载EF_list成功: %s", json_path)
            return ef_list

    def _save_ef_list_file(self, adf_type: str, ef_id: str, ef_list: list):
        """
        把 EF_list 写回 JSON 文件 => "json_data/USIM_6F07.json"
        """
        file_name = f"{adf_type}_{ef_id}.json".upper()
        json_path = os.path.join("json_data", file_name)

        final_data = {
            "EF_list": ef_list
        }
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(final_data, f, ensure_ascii=False, indent=4)
            logging.info("[_save_ef_list_file] 保存EF_list成功: %s", json_path)
        except Exception as e:
            logging.error("[_save_ef_list_file] 保存EF_list文件失败 %s => %s", json_path, e)

    def _find_or_create_file_obj(self, ef_list: list, adf_type: str, ef_id: str):
        """
        在 ef_list 找到  { "ef_id":..., "adf_type":..., "records":[...] } 
        如果没有就新建并 append
        """
        for item in ef_list:
            if (item.get("ef_id") == ef_id.upper() 
                and item.get("adf_type") == adf_type.upper()):
                logging.debug("[_find_or_create_file_obj] 找到EF对象: ef_id=%s", ef_id)
                return item

        # 不存在 => 创建
        new_obj = {
            "ef_id": ef_id.upper(),
            "adf_type": adf_type.upper(),
            "records": []
        }
        ef_list.append(new_obj)
        logging.info("[_find_or_create_file_obj] 新建EF对象: ef_id=%s", ef_id)
        return new_obj





    # 批量导入
    def load_and_write_from_json(self, json_file: str, progress_callback=None, force_raw=False) -> str:
        """
        批量导入：从JSON文件批量写入EF数据
        Args:
            json_file: JSON文件路径
            progress_callback: 进度回调函数，接收当前进度值
        """
        logging.info("[load_and_write_from_json] 批量导入: %s", json_file)
                # ---------- 小工具：计算一条记录编码后的字节数 ----------
        def _encoded_len(ef_id: str, one_record: dict, cur_len: int) -> int:
            """用当前 record_len 做 encode，返回编码后的字节数（出错返 0）"""
            enc = encode_ef_data(ef_id, one_record, cur_len)
            if isinstance(enc, str) and enc.startswith("error"):
                return 0          # 让主流程把它当失败
            return len(enc) // 2
        
        if not os.path.isfile(json_file):
            logging.error("[load_and_write_from_json] 文件不存在: %s", json_file)
            return f"error: file {json_file} not found."

        # 读取 JSON
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                json_data = json.load(f)
        except Exception as e:
            logging.error("[load_and_write_from_json] 加载JSON失败: %s", e)
            return f"error: failed to load JSON => {e}"

        # 检查整体结构
        if not isinstance(json_data, dict) or "EF_list" not in json_data:
            logging.error("[load_and_write_from_json] JSON格式无效，缺少EF_list")
            return "error: invalid JSON format. Must have EF_list as a list."

        ef_list = json_data["EF_list"]
        if not isinstance(ef_list, list):
            logging.error("[load_and_write_from_json] EF_list不是列表")
            return "error: EF_list must be a list."

        total_files = len(ef_list)
        success_count = 0
        fail_count = 0
        fail_details = {}

        # 批量写
        for idx, ef_obj in enumerate(ef_list):
            # 更新进度
            if progress_callback:
                progress_callback(idx)

            # 解析 adf_type, ef_id, records
            adf_type = ef_obj.get("adf_type", "").strip().upper()
            ef_id = ef_obj.get("ef_id", "").upper()
            records = ef_obj.get("records", [])

            # 基础校验
            if not adf_type or not ef_id or not isinstance(records, list):
                fail_count += 1
                fail_details[f"{adf_type}:{ef_id}"] = "Missing adf_type/ef_id/records"
                logging.error("[load_and_write_from_json] 缺少adf_type/ef_id/records: %s", ef_obj)
                continue

            # 调用 get_ef_structure (可选, 如果需要知道 EF 长度/文件结构)
            ef_info = self.get_ef_structure(adf_type, ef_id)
            if not ef_info:
                fail_count += 1
                fail_details[f"{adf_type}:{ef_id}"] = "卡文件不存在"
                logging.error("[load_and_write_from_json] 卡文件不存在: %s", ef_id)
                continue

            ef_structure = ef_info.get("ef_structure", "transparent")
            recorder_value = ef_info.get("recorder", "0")
            if not recorder_value or recorder_value.lower() == "none":
                recorder_value = "1"
            max_records = int(recorder_value, 16)
            # 提前扩容（仅 linear/cyclic 才需要）
            resize_done = False
            if ef_structure in ("linear", "cyclic"):
                cur_rec_len   = int(ef_info.get("record_length", "00"), 16)   # 卡上 record_len
                sec_attr      = ef_info.get("sec_attr", "")
                sfi           = ef_info.get("sfi", "")

                # —— 计算「JSON 里最长编码后长度」&「需要的记录数」 ——
                want_rec_len  = max(
                    _encoded_len(ef_id, rec, cur_rec_len) for rec in records
                )
                want_rec_num  = len(records)

                resize_by_len = want_rec_len  > cur_rec_len
                resize_by_num = want_rec_num  > max_records

                if resize_by_len or resize_by_num:
                    logging.info(
                        "[load_and_write_from_json] %s:%s 触发 resize, "
                        "want_len=%d(> %d?), want_num=%d(> %d?)",
                        adf_type, ef_id, want_rec_len, cur_rec_len,
                        want_rec_num, max_records
                    )
                    resize_result = resize_ef(
                        self, ef_id,
                        new_len   = want_rec_len,
                        adf       = adf_type,
                        structure = ef_structure,
                        record_num= want_rec_num,
                        security_attrs = sec_attr,
                        sfi = sfi
                    )
                    if resize_result != "9000":
                        fail_count += 1
                        fail_details[f"{adf_type}:{ef_id}"] = f"resize_ef 失败: {resize_result}"
                        logging.error("[load_and_write_from_json] 扩容失败: %s", resize_result)
                        continue

                    # 扩容成功 → 刷新 EF 结构 & 最大记录数
                    ef_info = self.get_ef_structure(adf_type, ef_id)
                    max_records= want_rec_num
                    resize_done = True  # ✅ 标记本 EF 文件已扩容

            file_write_ok = True

            # ---------- 写多条记录 ----------
            for idx, record_data in enumerate(records):
                record_index = idx + 1  # ✅ 总是从第 1 条写起
                if ef_structure in ["linear", "cyclic"] and not resize_done:
                    if idx >= max_records:
                        logging.warning(f"[load_and_write_from_json] {adf_type}:{ef_id}: index {idx} out of range (max {max_records})")
                        break

                result = self.write_data(record_data, ef_info, adf_type, ef_id, record_index, force_raw=force_raw)

                # 避免写入中再触发 resize，因为你已手动 resize
                if result != "9000":
                    fail_count += 1
                    file_write_ok = False
                    fail_reason = f"Write fail => {result}"

                    if result == "6A82":
                        fail_reason = "File not exist on card (6A82)"
                    elif result == "6982":
                        fail_reason = "Security status not satisfied (6982)."

                    fail_details[f"{adf_type}:{ef_id}"] = fail_reason
                    logging.error("[load_and_write_from_json] 写入失败: %s, 原因: %s", ef_id, fail_reason)
                    break

            if file_write_ok:
                success_count += 1


        # 汇总统计信息
        msg_lines = [
            f"Total EF to write: {total_files}",
            f"Success: {success_count}",
            f"Fail: {fail_count}",
        ]
        if fail_details:
            msg_lines.append("Fail details:")
            for key, reason in fail_details.items():
                msg_lines.append(f"  - {key}: {reason}")

        final_report = "\n".join(msg_lines)

        if fail_count == 0:
            logging.info("[load_and_write_from_json] 批量导入全部成功")
            return "success\n" + final_report
        else:
            logging.warning("[load_and_write_from_json] 批量导入有失败")
            return final_report

    def delete_ef(self, ef_id, adf):
        return delete_ef_cmd(self.comm, ef_id, adf)

    def create_file(self, ef_id, length, adf, structure, record_num, security_Attributes, sfi):
 
        return create_file_cmd(self.comm, ef_id, length, adf, structure, record_num, security_Attributes, sfi)

