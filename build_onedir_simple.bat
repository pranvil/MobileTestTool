@echo off
echo 正在以 onedir 模式打包 ADB Logcat 过滤工具...

REM 安装PyInstaller（如果未安装）
pip install pyinstaller

REM 执行打包
pyinstaller --onedir --windowed --name "ADB_Logcat_Filter" adb_logcat_filter.py

echo 打包完成！
echo 可执行文件在 dist\ADB_Logcat_Filter\ 目录中
echo 运行文件: dist\ADB_Logcat_Filter\ADB_Logcat_Filter.exe
pause
