@echo off
echo 正在打包 ADB Logcat 过滤工具...
echo 请耐心等待，这可能需要几分钟时间...
echo.

pyinstaller --icon "icon.ico" --onefile --windowed --name "ADB_Logcat_Filter" main.py

if exist "dist\ADB_Logcat_Filter.exe" (
    echo.
    echo 打包成功！
    echo 可执行文件位置: dist\ADB_Logcat_Filter.exe
    echo.
    dir "dist\ADB_Logcat_Filter.exe"
) else (
    echo.
    echo 打包失败！
)

echo.
pause
