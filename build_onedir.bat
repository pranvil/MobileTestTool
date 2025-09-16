@echo off
echo ========================================
echo    ADB Logcat 过滤工具 - onedir 打包
echo ========================================
echo.

REM 检查Python环境
python --version
if errorlevel 1 (
    echo 错误：未找到Python环境！
    pause
    exit /b 1
)

REM 检查并安装依赖
echo 检查依赖包...
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo 正在安装 PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo 安装 PyInstaller 失败！
        pause
        exit /b 1
    )
)

REM 清理之前的构建文件
echo 清理之前的构建文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo.
echo 开始打包（onedir模式）...
echo 这可能需要几分钟时间，请耐心等待...
echo.

REM 执行打包命令
pyinstaller ^
    --onedir ^
    --windowed ^
    --name "ADB_Logcat_Filter" ^
    --add-data "README.md;." ^
    --hidden-import "tkinter" ^
    --hidden-import "tkinter.ttk" ^
    --hidden-import "tkinter.messagebox" ^
    --hidden-import "tkinter.filedialog" ^
    --hidden-import "tkinter.simpledialog" ^
    --hidden-import "subprocess" ^
    --hidden-import "threading" ^
    --hidden-import "queue" ^
    --hidden-import "re" ^
    --hidden-import "os" ^
    --hidden-import "sys" ^
    --hidden-import "datetime" ^
    --clean ^
    adb_logcat_filter.py

if errorlevel 1 (
    echo.
    echo 打包失败！请检查错误信息。
    pause
    exit /b 1
)

echo.
echo ========================================
echo           打包完成！
echo ========================================
echo.
echo 可执行文件位置: dist\ADB_Logcat_Filter\ADB_Logcat_Filter.exe
echo 目录大小: 
dir "dist\ADB_Logcat_Filter" | find "个文件"
echo.
echo 使用说明：
echo 1. 确保已安装 Android SDK 并配置 adb 命令
echo 2. 连接 Android 设备并启用 USB 调试
echo 3. 运行 dist\ADB_Logcat_Filter\ADB_Logcat_Filter.exe
echo.
echo onedir 模式优势：
echo - 启动速度更快
echo - 文件结构清晰
echo - 便于调试和修改
echo - 可以单独更新某些文件
echo.
pause
