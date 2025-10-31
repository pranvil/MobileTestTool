# PyInstaller hook for pyserial
# This hook ensures that PyInstaller includes all necessary pyserial modules and dependencies

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# Collect all pyserial modules
datas, binaries, hiddenimports = collect_all('serial')

# Ensure serial.tools.list_ports is included
hiddenimports += [
    'serial',
    'serial.tools',
    'serial.tools.list_ports',
    'serial.tools.list_ports_windows',
    'serial.tools.list_ports_linux',
    'serial.tools.list_ports_osx',
]

