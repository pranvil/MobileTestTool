import logging
import os
import sys
from datetime import datetime
import traceback
from logging.handlers import TimedRotatingFileHandler
import json

def get_base_path():
    """获取基础路径，兼容exe环境"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # exe环境：使用exe所在目录
        return os.path.dirname(sys.executable)
    else:
        # Python环境：使用脚本目录
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 设置日志记录配置
def setup_logging():
    # 使用基础路径来确定日志目录
    base_path = get_base_path()
    log_dir = os.path.join(base_path, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_filename = os.path.join(log_dir, "log.txt")

    # 默认配置
    enable_log = True
    log_level = logging.INFO
    show_console = True

    # ------------------------------------------------------------------
    # 优先尝试读取主程序的 debug 日志配置（用于“同步受控”的日志等级）
    # 说明：
    # - 主程序配置文件：<project_root>/logs/debug_log_config.json
    # - sim_reader 自己的配置文件：<sim_reader_base>/log_config.json
    # - 为避免 core 包名冲突（主程序 core vs sim_reader/core），这里用文件路径读取，不做 import。
    # ------------------------------------------------------------------
    try:
        # utils.py 位于 sim_reader/core/utils.py
        # 两级上跳到项目根目录（MobileTestTool）
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        debug_cfg_path = os.path.join(project_root, "logs", "debug_log_config.json")
        if os.path.exists(debug_cfg_path):
            with open(debug_cfg_path, "r", encoding="utf-8") as f:
                debug_cfg = json.load(f) or {}
            # 主程序字段：enabled / log_level
            enable_log = bool(debug_cfg.get("enabled", True))
            level_str = str(debug_cfg.get("log_level", "INFO")).upper()
            log_level = getattr(logging, level_str, logging.INFO)
            # show_console：主程序配置里没有该字段，沿用 sim_reader 的默认/自有配置
    except Exception as e:
        # 读不到主程序配置就回退到 sim_reader 自己的配置，不影响使用
        try:
            print(f"[Logging] Failed to read debug_log_config.json. Reason: {e}")
        except Exception:
            pass

    config_path = os.path.join(base_path, "log_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                enable_log = config.get("enable_log", True)
                level_str = config.get("log_level", "INFO").upper()
                log_level = getattr(logging, level_str, logging.INFO)
                show_console = config.get("show_console", True)
        except Exception as e:
            print(f"[Logging] Failed to read log_config.json. Reason: {e}")

    # === 如果明确配置为关闭日志 ===
    if not enable_log:
        logging.disable(logging.CRITICAL)
        return

    # 日志格式器
    class CustomFormatter(logging.Formatter):
        def formatTime(self, record, datefmt=None):
            ct = datetime.fromtimestamp(record.created)
            return ct.strftime('%Y-%m-%d %H:%M:%S') + f".{int(record.msecs):03d}"

    formatter = CustomFormatter('%(asctime)s - %(levelname)s - %(message)s')

    file_handler = TimedRotatingFileHandler(
        log_filename, when="midnight", interval=1, backupCount=7, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    handlers = [file_handler]
    if show_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    logging.root.handlers.clear()
    logging.basicConfig(level=log_level, handlers=handlers)

    logging.info("Logging initialized. Level=%s Console=%s", logging.getLevelName(log_level), show_console)

# 禁用所有日志
def disable_logging():
    """禁用所有日志"""
    logging.disable(logging.CRITICAL)


# 捕获异常并记录日志
def handle_exception(func):
    """装饰器: 捕获异常并记录日志"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_message = f"Error in {func.__name__}: {e}"
            logging.error(error_message)
            logging.error(traceback.format_exc())  # 记录完整的异常堆栈信息
            return None
    return wrapper


# 示例用法
if __name__ == "__main__":
    setup_logging()

    @handle_exception
    def test_func():
        logging.info("This is a test log message.")
        raise ValueError("This is a test exception!")

    test_func()
