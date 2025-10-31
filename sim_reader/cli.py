# cli.py
import argparse
import logging
import json
from core.sim_service import SimService
from core.data_handler import admin
from tree_manager import TreeManager
from core.utils import setup_logging

def main():
    setup_logging()
    parser = argparse.ArgumentParser(
        description="SIM File Writer - CLI",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        '-w', 
        metavar='<json_file>',
        help="Batch write from JSON file.\nJson format: {\n  \"EF_list\": [\n    {\n      \"ef_id\": \"6F07\",\n      \"adf_type\": \"USIM\",\n      \"records\": [ {...}, {...} ]\n    }\n  ]\n}",
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

    args = parser.parse_args()
    sim_service = SimService()
    sim_service.comm.initialize() 
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
        result = sim_service.load_and_write_from_json(args.w)
        if result.startswith("success"):
            logging.info("Batch write success:\n%s", result)
        elif result.startswith("error"):
            logging.error("Batch write error: %s", result)
        else:
            # 可能是部分成功/部分失败
            logging.warning("Batch write partial or fail:\n%s", result)

if __name__ == "__main__":
    main()
