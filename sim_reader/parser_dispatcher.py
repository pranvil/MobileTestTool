import pkgutil
import importlib
import logging
import parsers
from parsers.ef_default import encode_data as default_encoder, parse_data as default_parser

# 全局解析器映射字典，用于存储EF ID到对应解析器模块的映射
# 格式: { "6F07": <module对象>, ... }
PARSERS = {}

def default_parse_data(raw_data: list) -> list:
    """默认的数据解析函数
    当没有找到专门的解析器时使用此函数处理数据
    
    Args:
        raw_data (list): 原始数据列表
        
    Returns:
        list: 解析后的数据列表
    """
    return default_parser(raw_data)

def default_encode_data(user_data: dict, ef_file_len_decimal) -> str:
    """默认的数据编码函数
    当没有找到专门的编码器时使用此函数处理数据
    
    Args:
        user_data (dict): 用户输入的数据字典
        ef_file_len_decimal (int): EF文件长度（十进制）
        
    Returns:
        str: 编码后的数据字符串
    """
    return default_encoder(user_data, ef_file_len_decimal)  

def _register_all_parsers():
    """注册所有EF解析器
    扫描parsers目录下所有以ef_开头的模块，动态导入并注册到PARSERS字典中
    每个模块必须包含parse_data和encode_data两个函数才能被注册
    """
    # 获取parsers包路径
    parsers_path = parsers.__path__
    logging.info("开始扫描解析器目录: %s", parsers_path)

    # 遍历目录下的所有模块
    for _, module_name, ispkg in pkgutil.iter_modules(parsers_path):
        if module_name.startswith("ef_"):
            try:
                # 构建完整的模块路径并导入
                full_module_name = f"{parsers.__name__}.{module_name}"
                logging.debug("正在导入模块: %s", full_module_name)
                module = importlib.import_module(full_module_name)

                # 从模块名提取EF ID（例如：ef_6F07 -> 6F07）
                ef_id = module_name.split("_", 1)[1].upper()
                logging.debug("发现EF ID: %s", ef_id)

                # 验证模块是否包含必要的函数
                has_parse = hasattr(module, "parse_data")
                has_encode = hasattr(module, "encode_data")
                logging.debug("模块 %s 包含函数 - parse_data: %s, encode_data: %s", 
                            module_name, has_parse, has_encode)

                if has_parse and has_encode:
                    PARSERS[ef_id] = module
                    logging.info("成功注册EF解析器 - ID: %s, 模块: %s", ef_id, module_name)
                else:
                    logging.warning("模块 %s 缺少必要的解析函数(parse_data或encode_data)", module_name)
            except Exception as e:
                logging.error("导入解析器模块 %s 失败: %s", module_name, str(e))

# 初始化时注册所有解析器
_register_all_parsers()

def parse_ef_data(ef_id: str, raw_data) -> list:
    """解析EF文件数据
    根据EF ID调用对应的解析器处理数据，如果没有找到专门的解析器则使用默认解析器
    
    Args:
        ef_id (str): EF文件ID
        raw_data: 原始数据
        
    Returns:
        list: 解析后的数据列表，如果解析失败则返回空列表或错误信息
    """
    ef_id = ef_id.upper()
    parser_module = PARSERS.get(ef_id)
    
    if parser_module:
        try:
            logging.debug("使用专门解析器处理EF数据 - ID: %s", ef_id)
            result = parser_module.parse_data(raw_data)
            if isinstance(result, str) and result.startswith("error"):
                logging.error("解析EF数据失败 - ID: %s, 错误: %s", ef_id, result)
                return result
            logging.debug("EF数据解析成功 - ID: %s, 记录数: %d", ef_id, len(result) if isinstance(result, list) else 1)
            return result
        except Exception as e:
            logging.error("解析EF数据时发生异常 - ID: %s, 错误: %s", ef_id, str(e))
            return []
    else:
        logging.warning("未找到EF %s的专门解析器，使用默认解析器", ef_id)
        return default_parse_data(raw_data)

def encode_ef_data(ef_id: str, user_data: dict, ef_file_len_decimal: int) -> str:
    """编码EF文件数据
    根据EF ID调用对应的编码器处理数据，如果没有找到专门的编码器则使用默认编码器
    
    Args:
        ef_id (str): EF文件ID
        user_data (dict): 用户输入的数据字典
        ef_file_len_decimal (int): EF文件长度（十进制）
        
    Returns:
        str: 编码后的数据字符串，如果编码失败则返回错误信息
    """
    ef_id = ef_id.upper()
    parser_module = PARSERS.get(ef_id)
    
    if parser_module:
        try:
            logging.debug("使用专门编码器处理EF数据 - ID: %s", ef_id)
            result = parser_module.encode_data(user_data, ef_file_len_decimal)
            if isinstance(result, str) and result.startswith("error"):  
                logging.error("编码EF数据失败 - ID: %s, 错误: %s", ef_id, result)
                return result
            logging.debug("EF数据编码成功 - ID: %s, 结果: %s", ef_id, result)
            return result
        except Exception as e:
            logging.error("编码EF数据时发生异常 - ID: %s, 错误: %s", ef_id, str(e))
            return "error: parse error"
    else:
        logging.warning("未找到EF %s的专门编码器，使用默认编码器", ef_id)
        return default_encode_data(user_data, ef_file_len_decimal)
