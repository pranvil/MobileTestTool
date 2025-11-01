# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # UI 资源文件
        ('ui/resources/themes/*.qss', 'ui/resources/themes'),
        ('ui/resources/icons/*.png', 'ui/resources/icons'),
        # APK 资源文件
        ('resources/apk/*.apk', 'resources/apk'),
        # 模板文件
        ('resources/template/*', 'resources/template'),
        # 图标文件
        ('icon.ico', '.'),
        # Manifest 文件
        ('MobileTestTool.manifest', '.'),
        # 翻译文件
        ('translations.json', '.'),
        ('config/language.conf', 'config'),
        # SIM APDU Parser 模块文件
        ('SIM_APDU_Parser', 'SIM_APDU_Parser'),
        # SIM Reader 模块文件
        ('sim_reader', 'sim_reader'),
        ('sim_reader/parsers', 'sim_reader/parsers'),
        # UIAutomator2 资源文件由 hook-uiautomator2.py 自动处理
    ],
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.QtNetwork',
        # UI 模块
        'ui.widgets.shadow_utils',
        'ui.widgets.animations',
        'ui.widgets.log_viewer',
        # UIAutomator2 相关模块（由hook文件自动处理）
        'uiautomator2',
        # 核心模块
        'core.mtklog_manager',
        'core.device_manager',
        'core.language_manager',
        'core.debug_logger',
        'core.tmo_cc_manager',
        'core.echolocate_manager',
        'core.hera_config_manager',
        # SIM APDU Parser 相关模块
        'SIM_APDU_Parser.main',
        'SIM_APDU_Parser.pipeline',
        'SIM_APDU_Parser.core',
        'SIM_APDU_Parser.data_io',
        'SIM_APDU_Parser.classify',
        'SIM_APDU_Parser.parsers',
        'SIM_APDU_Parser.render',
        # SIM Reader 相关模块
        'sim_reader',
        'sim_reader.core',
        'sim_reader.core.sim_service',
        'sim_reader.core.serial_comm',
        'sim_reader.core.data_handler',
        'sim_reader.core.utils',
        'sim_reader.parser_dispatcher',
        'sim_reader.tree_manager',
        'sim_reader.parsers',
        'sim_reader.cli',
        'sim_reader.ui',
        # 串口通信依赖（pyserial）
        'serial',
        'serial.serialutil',
        'serial.serialwin32',
        'serial.tools',
        'serial.tools.list_ports',
        'serial.tools.list_ports_windows',
        'serial.tools.list_ports_linux',
        'serial.tools.list_ports_osx',
        # 标准库但PyInstaller需要显式导入
        'importlib',
        'importlib.util',
        'concurrent',
        'concurrent.futures',
    ],
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的 PyQt5 模块，减小体积
        'PyQt5.QtMultimedia',
        'PyQt5.QtMultimediaWidgets',
        'PyQt5.QtQml',
        'PyQt5.QtQuick',
        'PyQt5.QtQuickWidgets',
        'PyQt5.QtWebKit',
        'PyQt5.QtWebKitWidgets',
        'PyQt5.QtWebSockets',
        'PyQt5.QtBluetooth',
        'PyQt5.QtNfc',
        'PyQt5.QtPositioning',
        'PyQt5.QtSensors',
        'PyQt5.QtLocation',
        'PyQt5.Qt3DCore',
        'PyQt5.Qt3DRender',
        'PyQt5.Qt3DInput',
        'PyQt5.Qt3DLogic',
        'PyQt5.Qt3DAnimation',
        'PyQt5.Qt3DExtras',
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
    [],
    exclude_binaries=True,  # onedir 模式：排除二进制文件，放到单独的文件夹
    name='MobileTestTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 不显示控制台窗口
    windowed=True,  # Windows GUI模式，无控制台
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
    manifest='MobileTestTool.manifest',  # 集成DPI感知manifest
    uac_admin=False,  # 不需要管理员权限
    uac_uiaccess=False,
)

# COLLECT 用于 onedir 模式，将所有文件收集到一个文件夹中
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MobileTestTool'
)

