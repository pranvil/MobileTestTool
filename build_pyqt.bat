@echo off
echo ========================================
echo PyQt5版本打包脚本 (onedir模式)
echo ========================================
echo.

REM 清理旧的构建文件
echo 清理旧的构建文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo 开始打包 (onedir模式 - 文件夹形式)...
pyinstaller --clean MobileTestTool_pyqt.spec

echo.
echo ========================================
echo 打包完成！
echo ========================================
echo.
echo 程序文件夹位置: dist\MobileTestTool_PyQt5\
echo 可执行文件位置: dist\MobileTestTool_PyQt5\MobileTestTool_PyQt5.exe
echo.
echo 注意：onedir模式会生成一个包含所有依赖的文件夹
echo 请将整个 MobileTestTool_PyQt5 文件夹分发给用户
echo.
pause

