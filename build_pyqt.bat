@echo off
echo ========================================
echo PyQt5版本打包脚本
echo ========================================
echo.

REM 清理旧的构建文件
echo 清理旧的构建文件...
if exist build_pyqt rmdir /s /q build_pyqt
if exist dist_pyqt rmdir /s /q dist_pyqt
if exist MobileTestTool_PyQt5.exe del /q MobileTestTool_PyQt5.exe

echo.
echo 开始打包...
pyinstaller --clean MobileTestTool_pyqt.spec

echo.
echo ========================================
echo 打包完成！
echo ========================================
echo.
echo 可执行文件位置: dist_pyqt\MobileTestTool_PyQt5.exe
echo.
pause

