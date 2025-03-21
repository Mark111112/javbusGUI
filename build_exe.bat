@echo off
echo ========================================
echo JavBusGUI 可执行文件打包工具
echo ========================================
echo.

REM 检查环境
python --version
if %ERRORLEVEL% neq 0 (
    echo 错误: 未找到Python，请确保已安装Python并添加到PATH中
    goto :END
)

REM 安装/更新必要的库
echo 正在确保所需的Python库已安装...
pip install -U pyinstaller pillow pyqt5 python-vlc curl_cffi requests beautifulsoup4 pyperclip

REM 清理旧的构建文件
echo 正在清理旧的构建文件...
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
if exist "__pycache__" rd /s /q "__pycache__"

REM 确保工作目录存在
if not exist "buspic" mkdir "buspic"
if not exist "buspic\stars" mkdir "buspic\stars"
if not exist "temp" mkdir "temp"
if not exist "downloads" mkdir "downloads"

REM 确保fanza_mappings.json存在
if not exist "fanza_mappings.json" (
    echo {}> fanza_mappings.json
    echo 创建了空的fanza_mappings.json文件
)

REM 检查必须的文件
if not exist "javbus_gui_improved.py" (
    echo 错误: 未找到主程序文件 javbus_gui_improved.py
    goto :END
)

if not exist "video_player2.py" (
    echo 错误: 未找到视频播放器模块 video_player2.py
    goto :END
)

if not exist "javbus_db.py" (
    echo 错误: 未找到数据库模块 javbus_db.py
    goto :END
)

if not exist "movieinfo.py" (
    echo 错误: 未找到影片信息模块 movieinfo.py
    goto :END
)

REM 创建JavBusGUI.spec文件（如果需要更新）
REM 我们使用已更新的spec文件，无需重新生成

REM 执行PyInstaller打包
echo 开始打包...
pyinstaller --clean JavBusGUI.spec

echo.
if exist "dist\JavBusGUI" (
    echo 目录版打包成功! 输出目录: dist\JavBusGUI
) else (
    echo 目录版打包失败!
)

if exist "dist\JavBus一体版.exe" (
    echo 一体版打包成功! 输出文件: dist\JavBus一体版.exe
) else (
    echo 一体版打包失败!
)

echo.
echo 打包完成!
echo.
echo ========================================
echo 注意事项:
echo 1. 运行软件前请确保已安装VLC媒体播放器
echo 2. 目录版运行JavBusGUI\JavBusGUI.exe即可
echo 3. 一体版直接运行JavBus一体版.exe
echo ========================================

:END
pause 