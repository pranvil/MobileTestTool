@echo off
chcp 65001 >nul
echo ========================================
echo PyQt5版本打包脚本 (onedir模式)
echo ========================================
echo.

REM 检查Python环境
echo 检查Python环境...
python --version
if %errorlevel% neq 0 (
    echo 错误：未找到Python环境，请确保Python已安装并添加到PATH
    pause
    exit /b 1
)

REM 检查PyInstaller
echo 检查PyInstaller...
python -c "import PyInstaller; print('PyInstaller版本:', PyInstaller.__version__)"
if %errorlevel% neq 0 (
    echo 错误：未找到PyInstaller，请运行: pip install pyinstaller
    pause
    exit /b 1
)

REM 清理旧的构建文件
echo.
echo 清理旧的构建文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo 开始打包 (onedir模式 - 文件夹形式)...
pyinstaller --clean --noconfirm MobileTestTool_pyqt.spec

if %errorlevel% neq 0 (
    echo.
    echo 错误：打包失败！
    echo 请检查错误信息并重试
    pause
    exit /b 1
)

echo.
echo ========================================
echo 打包完成！
echo ========================================
echo.
echo 程序文件夹位置: dist\MobileTestTool_PyQt5\
echo 可执行文件位置: dist\MobileTestTool_PyQt5\MobileTestTool_PyQt5.exe
echo.
echo 注意：
echo 1. onedir模式会生成一个包含所有依赖的文件夹
echo 2. 请将整个 MobileTestTool_PyQt5 文件夹分发给用户
echo 3. 此版本已优化exe环境下的MTKlogger兼容性
echo.


