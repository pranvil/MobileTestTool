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
