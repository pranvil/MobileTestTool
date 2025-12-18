# cli.py
import argparse
import logging
import json
import os
import sys
from core.sim_service import SimService
from core.data_handler import admin
from tree_manager import TreeManager
from core.utils import setup_logging

def validate_raw_json(json_file: str) -> tuple[bool, list[dict]]:
    """
    验证 JSON 文件是否适合 raw 模式
    返回: (is_valid, error_records)
    - is_valid: 是否所有记录都包含 raw_data 字段
    - error_records: 缺少 raw_data 字段的记录列表
    """
    if not os.path.isfile(json_file):
        logging.error("[validate_raw_json] 文件不存在: %s", json_file)
        return False, []
    
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            json_data = json.load(f)
    except Exception as e:
        logging.error("[validate_raw_json] 加载JSON失败: %s", e)
        return False, []
    
    # 检查整体结构
    if not isinstance(json_data, dict) or "EF_list" not in json_data:
        logging.error("[validate_raw_json] JSON格式无效，缺少EF_list")
        return False, []
    
    ef_list = json_data.get("EF_list", [])
    if not isinstance(ef_list, list):
        logging.error("[validate_raw_json] EF_list不是列表")
        return False, []
    
    error_records = []
    
    # 遍历所有 EF 和记录
    for ef_obj in ef_list:
        adf_type = ef_obj.get("adf_type", "").strip().upper()
        ef_id = ef_obj.get("ef_id", "").upper()
        records = ef_obj.get("records", [])
        
        if not isinstance(records, list):
            continue
        
        # 检查每条记录
        for idx, record_data in enumerate(records):
            if not isinstance(record_data, dict):
                continue
            
            # 检查是否包含 raw_data 字段
            if "raw_data" not in record_data:
                error_records.append({
                    "ef_id": ef_id,
                    "adf_type": adf_type,
                    "record_index": idx + 1,
                    "record_data": record_data
                })
    
    is_valid = len(error_records) == 0
    return is_valid, error_records

def main():
    # 在打包的exe环境中，主程序的日志系统已经初始化，不需要再初始化SIM reader的日志系统
    # 这样可以避免生成两个日志文件（debug_YYYYMMDD.log 和 log.txt）
    if not (getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')):
        # 只在非打包环境（Python直接运行）中初始化SIM reader的日志系统
        setup_logging()
    
    parser = argparse.ArgumentParser(
        description="SIM File Writer - CLI",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        '-w', 
        metavar='<json_file>',
        help="Batch write from JSON file.\n"
             "Json format: {\n"
             "  \"EF_list\": [\n"
             "    {\n"
             "      \"ef_id\": \"6F07\",\n"
             "      \"adf_type\": \"USIM\",\n"
             "      \"records\": [ {...}, {...} ]\n"
             "    }\n"
             "  ]\n"
             "}\n"
             "When using --raw, records must contain \"raw_data\" field.",
        type=str
    )
    parser.add_argument(
        '-p', 
        metavar='<pin_code>',
        help="PIN code required for SIM authentication before writing.\n"
             "Test SIM usually is 55555555.\n"
             "or 11111111.\n"
             "or 22222222.\n"
             "AT&T test SIM is uuuuuuuu", 
        type=str
    )
    parser.add_argument(
        '--raw', '-r',
        action='store_true',
        help="Enable raw mode for all records.\n"
             "When enabled, all records must contain 'raw_data' field with hexadecimal data.\n"
             "This corresponds to the 'Raw' checkbox in GUI mode.\n"
             "Example JSON format for raw mode:\n"
             "  {\n"
             "    \"EF_list\": [\n"
             "      {\n"
             "        \"ef_id\": \"6F07\",\n"
             "        \"adf_type\": \"USIM\",\n"
             "        \"records\": [\n"
             "          {\"raw_data\": \"083901140021436536\"}\n"
             "        ]\n"
             "      }\n"
             "    ]\n"
             "  }"
    )
    parser.add_argument(
        '--skip-confirm',
        action='store_true',
        help="Skip confirmation prompts. Use with caution.\n"
             "When used with --raw, skips validation warnings and confirmation.\n"
             "Recommended for automated scripts only."
    )
    parser.add_argument(
        '--port', '-P',
        metavar='<port>',
        help="Specify the serial port to use (e.g., COM3, COM4).\n"
             "If not specified, the program will automatically find the first available port that supports AT commands.\n"
             "Use this option when you have multiple ports and want to select a specific one.",
        type=str
    )

    args = parser.parse_args()
    sim_service = SimService()
    
    # 如果指定了端口，先测试并连接该端口
    if args.port:
        port = args.port.strip().upper()
        # 确保端口格式正确（如 COM3）
        if not port.startswith('COM'):
            port = f'COM{port.lstrip("COM")}'
        
        print(f"正在测试指定端口: {port}")
        if sim_service.comm.test_port(port):
            print(f"端口 {port} 测试通过，正在连接...")
            if sim_service.comm.switch_port(port):
                sim_service.comm.initialized = True
                print(f"已成功连接到端口 {port}")
            else:
                print(f"错误: 无法连接到端口 {port}", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"错误: 端口 {port} 不支持AT命令或不可用", file=sys.stderr)
            print(f"提示: 请确认端口是否正确，或使用 --help 查看如何列出可用端口", file=sys.stderr)
            sys.exit(1)
    else:
        # 未指定端口，使用自动查找
        print("正在自动查找支持AT命令的端口...")
        available_ports = sim_service.comm.get_all_ports()
        if len(available_ports) > 1:
            print(f"警告: 检测到多个可用端口: {', '.join(available_ports)}")
            print(f"提示: 将使用第一个支持AT命令的端口。如需指定端口，请使用 --port 参数")
        
        if not sim_service.comm.initialize(show_popup=False):
            print("错误: 未找到支持AT命令的串口设备", file=sys.stderr)
            print(f"可用端口: {', '.join(available_ports) if available_ports else '无'}", file=sys.stderr)
            sys.exit(1)
        print(f"已自动连接到端口: {sim_service.comm.port}")
    
    tree_manager = TreeManager(None)

    # 如果提供了 -p PIN，就先验证
    if args.p:
        pin_result = admin(sim_service.comm, args.p)
        if pin_result == "6982":
            logging.error("Failed to verify PIN, please verify PIN and try again. Response: %s", pin_result)
            return
        elif pin_result != "9000":
            logging.error("Failed to verify PIN. Response: %s", pin_result)
            return
        logging.info("PIN verification successful.")

    # 如果提供 -w <json_file> => 批量写
    if args.w:
        force_raw = args.raw
        
        # 如果使用 --raw，先验证 JSON 格式
        if force_raw:
            is_valid, error_records = validate_raw_json(args.w)
            
            if not is_valid:
                # 有错误记录，显示详细错误信息
                error_msg = "错误：使用 --raw 模式，但检测到以下记录缺少 raw_data 字段：\n\n"
                for err_rec in error_records:
                    error_msg += f"- EF {err_rec['ef_id']} ({err_rec['adf_type']}), 记录 {err_rec['record_index']}: {err_rec['record_data']}\n"
                
                error_msg += "\n使用 --raw 模式时，所有记录必须包含 raw_data 字段。\n"
                error_msg += "请检查 JSON 文件格式，或移除 --raw 参数使用正常模式。"
                
                logging.error(error_msg)
                
                # 除非使用 --skip-confirm，否则退出
                if not args.skip_confirm:
                    print(error_msg, file=sys.stderr)
                    sys.exit(1)
                else:
                    logging.warning("使用 --skip-confirm，跳过验证错误，继续执行（可能导致写入失败）")
            else:
                # 验证通过，显示警告
                warning_msg = "警告：选择了 raw 模式写入数据。\n"
                warning_msg += "确保 JSON 文件数据全都是 raw data，否则写入数据可能损坏 SIM 卡。\n"
                
                # 除非使用 --skip-confirm，否则等待确认
                if not args.skip_confirm:
                    print(warning_msg)
                    try:
                        response = input("是否继续？(y/n): ").strip().lower()
                        if response not in ['y', 'yes']:
                            logging.info("用户取消操作")
                            return
                    except (EOFError, OSError, KeyboardInterrupt):
                        # 如果无法读取输入（如从非交互式环境调用），默认取消
                        logging.info("无法读取用户输入，取消操作")
                        print("无法读取用户输入，操作已取消", file=sys.stderr)
                        return
                else:
                    logging.info("使用 --skip-confirm，跳过确认，直接执行")
        
        # 读取 JSON 文件获取总文件数（用于显示进度）
        try:
            with open(args.w, "r", encoding="utf-8") as f:
                json_data = json.load(f)
            total_files = len(json_data.get("EF_list", []))
        except Exception:
            total_files = 0
        
        # 定义进度回调函数，实时显示进度
        def progress_callback(current):
            if total_files > 0:
                progress_percent = int((current / total_files) * 100)
                print(f"\r进度: [{current}/{total_files}] {progress_percent}%", end="", flush=True)
        
        # 执行批量写入
        print(f"\n开始批量写入，共 {total_files} 个 EF 文件...")
        result = sim_service.load_and_write_from_json(args.w, progress_callback=progress_callback, force_raw=force_raw)
        
        # 完成进度显示
        if total_files > 0:
            print(f"\r进度: [{total_files}/{total_files}] 100%")
        
        # 输出结果到控制台（同时也会记录到日志）
        print("\n" + "=" * 60)
        if result.startswith("success"):
            print("批量写入成功！")
            logging.info("Batch write success:\n%s", result)
        elif result.startswith("error"):
            print("批量写入失败！")
            logging.error("Batch write error: %s", result)
        else:
            print("批量写入完成（部分成功/部分失败）")
            logging.warning("Batch write partial or fail:\n%s", result)
        
        # 打印详细结果
        print(result)
        print("=" * 60)
        
        # 在打包的exe中，等待用户按键以避免控制台窗口立即关闭
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            try:
                input("\n按 Enter 键退出...")
            except (EOFError, OSError):
                pass  # 如果无法读取输入，直接退出

if __name__ == "__main__":
    main()
