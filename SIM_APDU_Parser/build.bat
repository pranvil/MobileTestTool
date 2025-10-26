@echo off
echo 正在安装打包依赖...
pip install -r requirements_build.txt
rem pyinstaller --noconfirm SIM_APDU_Viewer.spec

echo.
echo 正在打包应用...
pyinstaller --noconfirm --onefile --icon "icon.ico" --windowed --name "SIM APDU Viewer" --collect-submodules app --collect-submodules core --collect-submodules data_io --collect-submodules parsers --collect-submodules classify --collect-submodules render --hidden-import pipeline --hidden-import asn1crypto --collect-all asn1crypto main.py
echo.
echo 打包完成！exe文件位于 dist/SIM APDU Viewer.exe
pause
