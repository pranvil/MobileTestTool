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
    config_auto_created = False  # 标记配置文件是否被自动创建

    # ------------------------------------------------------------------
    # 优先尝试读取主程序的 debug 日志配置（用于"同步受控"的日志等级）
    # 说明：
    # - 主程序配置文件：<project_root>/logs/debug_log_config.json
    # - sim_reader 自己的配置文件：<sim_reader_base>/log_config.json
    # - 为避免 core 包名冲突（主程序 core vs sim_reader/core），这里用文件路径读取，不做 import。
    # ------------------------------------------------------------------
    try:
        # 计算项目根目录（兼容打包环境）
        # 在打包环境中：base_path 已经是 exe 所在目录（项目根目录）
        # 在开发环境中：base_path 是 sim_reader 目录，需要上跳一级到项目根目录
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # 打包环境：base_path 就是项目根目录（exe 所在目录）
            project_root = base_path
        else:
            # 非打包环境：base_path 是 sim_reader 目录，需要上跳一级
            project_root = os.path.dirname(base_path)
        
        debug_cfg_path = os.path.join(project_root, "logs", "debug_log_config.json")
        if os.path.exists(debug_cfg_path):
            with open(debug_cfg_path, "r", encoding="utf-8") as f:
                debug_cfg = json.load(f) or {}
            # 过滤掉注释字段（以下划线开头的字段被视为注释）
            debug_cfg = {k: v for k, v in debug_cfg.items() if not k.startswith("_")}
            # 主程序字段：enabled / log_level
            enable_log = bool(debug_cfg.get("enabled", True))
            level_str = str(debug_cfg.get("log_level", "INFO")).upper()
            log_level = getattr(logging, level_str, logging.INFO)
            # show_console：主程序配置里没有该字段，沿用 sim_reader 的默认/自有配置
        else:
            # 配置文件不存在，使用默认配置并自动生成配置文件
            # 默认配置与 core/log_config.py 保持一致
            default_config = {
                "_comment": "日志配置文件使用说明：\n"
                           "1. enabled: 是否启用日志记录 (true/false)\n"
                           "2. log_level: 日志级别，可选值: DEBUG, INFO, WARNING, ERROR, EXCEPTION\n"
                           "   - DEBUG: 显示所有日志（最详细）\n"
                           "   - INFO: 显示信息、警告和错误日志\n"
                           "   - WARNING: 只显示警告和错误日志\n"
                           "   - ERROR/EXCEPTION: 只显示错误日志\n"
                           "3. max_file_size_mb: 单个日志文件最大大小（MB），超过此大小会轮转\n"
                           "4. max_files: 保留的最大日志文件数量\n"
                           "5. retention_days: 日志文件保留天数，超过此天数的日志会被自动删除\n"
                           "6. buffer_size: 日志缓冲队列大小\n"
                           "7. flush_interval: 日志刷新间隔（秒）\n"
                           "8. enable_rotation: 是否启用日志轮转\n"
                           "9. rotation_by_size: 是否按文件大小轮转\n"
                           "10. rotation_by_date: 是否按日期轮转\n"
                           "11. include_module: 日志中是否包含模块名\n"
                           "12. include_function: 日志中是否包含函数名\n"
                           "13. include_line: 日志中是否包含行号\n"
                           "\n"
                           "修改配置后，重启程序即可生效。",
                "enabled": True,
                "log_level": "DEBUG",
                "max_file_size_mb": 10,
                "max_files": 5,
                "retention_days": 7,
                "buffer_size": 100,
                "flush_interval": 1.0,
                "enable_rotation": True,
                "rotation_by_size": True,
                "rotation_by_date": True,
                "include_module": True,
                "include_function": True,
                "include_line": True
            }
            
            # 确保 logs 目录存在
            os.makedirs(os.path.dirname(debug_cfg_path), exist_ok=True)
            
            # 保存默认配置到文件
            try:
                with open(debug_cfg_path, "w", encoding="utf-8") as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
                config_auto_created = True  # 标记配置文件已自动创建
            except Exception as e:
                # 如果保存失败，静默处理（不影响程序运行）
                try:
                    print(f"[Logging] 无法创建配置文件 {debug_cfg_path}: {e}")
                except Exception:
                    pass
            
            # 使用默认配置
            enable_log = default_config["enabled"]
            level_str = default_config["log_level"].upper()
            log_level = getattr(logging, level_str, logging.INFO)
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
    
    # 如果配置文件是自动创建的，在日志系统初始化后输出提示信息
    if config_auto_created:
        try:
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                project_root = base_path
            else:
                project_root = os.path.dirname(base_path)
            debug_cfg_path = os.path.join(project_root, "logs", "debug_log_config.json")
            logging.info(f"[Logging] 已自动创建默认配置文件: {debug_cfg_path}")
        except Exception:
            pass  # 静默处理，不影响主流程

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
            # 避免返回 None 导致上层出现 'in' / '.startswith' 等二次异常，
            # 统一返回可识别的 error 字符串，便于业务层判断与重试。
            return f"error: {func.__name__} exception => {e}"
    return wrapper


# 示例用法
if __name__ == "__main__":
    setup_logging()

    @handle_exception
    def test_func():
        logging.info("This is a test log message.")
        raise ValueError("This is a test exception!")

    test_func()
