#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手机测试辅助工具 - CLI 入口
纯粹的 CLI 模式启动逻辑
"""

import sys
import os


def main():
    """CLI 入口函数"""
    try:
        # 延迟导入 sim_reader.cli，确保在导入前调整 sys.path 并清理模块缓存
        # 需要确保 sim_reader 目录的优先级高于项目根目录
        project_root = os.path.dirname(os.path.abspath(__file__))
        sim_reader_path = os.path.join(project_root, 'sim_reader')
        
        # 保存原始状态
        original_path = sys.path.copy()
        saved_modules = {}
        
        try:
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            # 确保 sim_reader 路径在项目根目录之前
            if sim_reader_path in sys.path:
                sys.path.remove(sim_reader_path)
            sys.path.insert(0, sim_reader_path)
            
            # 清除可能冲突的模块缓存（只清除项目根目录的 core，保留 sim_reader 的）
            normalized_project_root = os.path.normpath(os.path.abspath(project_root))
            normalized_sim_reader_path = os.path.normpath(os.path.abspath(sim_reader_path))
            
            # 清除顶层模块
            for mod_name in ['core', 'tree_manager', 'parser_dispatcher']:
                if mod_name in sys.modules:
                    mod = sys.modules[mod_name]
                    if hasattr(mod, '__file__') and mod.__file__:
                        mod_file = os.path.normpath(os.path.abspath(mod.__file__))
                        if normalized_project_root in mod_file and normalized_sim_reader_path not in mod_file:
                            saved_modules[mod_name] = mod
                            del sys.modules[mod_name]
            
            # 清除 core 的子模块缓存
            modules_to_remove = [mod for mod in list(sys.modules.keys()) if mod.startswith('core.')]
            for mod in modules_to_remove:
                mod_obj = sys.modules[mod]
                if hasattr(mod_obj, '__file__') and mod_obj.__file__:
                    mod_file = os.path.normpath(os.path.abspath(mod_obj.__file__))
                    if normalized_project_root in mod_file and normalized_sim_reader_path not in mod_file:
                        saved_modules[mod] = mod_obj
                        del sys.modules[mod]
            
            # 现在导入 sim_reader.cli
            from sim_reader.cli import main as sim_reader_main
            
            # 调用 CLI 功能
            sim_reader_main()
        finally:
            # 恢复原始状态
            for mod_name, mod in saved_modules.items():
                sys.modules[mod_name] = mod
            sys.path = original_path
            
    except SystemExit:
        # argparse 在显示帮助信息后会抛出 SystemExit(0)，这是正常行为
        raise
    except Exception as e:
        # 如果有日志记录器，记录错误
        try:
            from core.debug_logger import logger
            logger.exception("CLI 模式执行失败")
        except:
            pass
        
        # 输出错误信息到控制台
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

