# -*- mode: python ; coding: utf-8 -*-
# 更新器打包配置文件 - 单文件模式（不依赖 _internal 目录）

block_cipher = None

a = Analysis(
    ['core/updater.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'psutil',  # 可选依赖，用于进程检查
        'zipfile',
        'shutil',
        'argparse',
        'tempfile',
        'subprocess',
        'os',
        'sys',
        'time',
        'pathlib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块，减小体积
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='updater',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # 显示控制台窗口，方便查看更新进度
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 更新器不需要图标
    uac_admin=False,  # 不需要管理员权限
    uac_uiaccess=False,
)

