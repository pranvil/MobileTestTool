# -*- coding: utf-8 -*-
"""
PyInstaller hook for uiautomator2
确保UIAutomator2在exe环境中正常工作
"""

import os
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# 收集所有UIAutomator2相关的模块
datas, binaries, hiddenimports = collect_all('uiautomator2')

# 手动添加uiautomator2的assets目录
try:
    import uiautomator2
    u2_path = os.path.dirname(uiautomator2.__file__)
    assets_path = os.path.join(u2_path, 'assets')
    
    if os.path.exists(assets_path):
        # 添加assets目录下的所有文件
        for root, dirs, files in os.walk(assets_path):
            for file in files:
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, u2_path)
                datas.append((src_path, os.path.dirname(rel_path)))
                print(f"[HOOK] 添加uiautomator2资源: {src_path} -> {os.path.dirname(rel_path)}")
except ImportError:
    pass

# 添加额外的隐藏导入（只添加确实存在的模块）
try:
    import uiautomator2
    # 动态检查哪些模块实际存在
    u2_modules = []
    potential_modules = [
        'uiautomator2.exceptions',
        'uiautomator2.utils',
        'uiautomator2.version',
    ]
    
    for module_name in potential_modules:
        try:
            __import__(module_name)
            u2_modules.append(module_name)
        except ImportError:
            pass
    
    hiddenimports += u2_modules
    print(f"[HOOK] 添加的uiautomator2模块: {u2_modules}")
    
except ImportError:
    pass

# 添加确实存在的依赖
optional_deps = ['requests', 'urllib3', 'websocket', 'lxml']
for dep in optional_deps:
    try:
        __import__(dep)
        hiddenimports.append(dep)
    except ImportError:
        pass

# 收集数据文件
datas += collect_data_files('uiautomator2')

# 收集子模块
hiddenimports += collect_submodules('uiautomator2')
