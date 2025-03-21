Inspired by the nice work of "https://github.com/ovnrain/javbus-api". Really convenience especially when you are in a limited network environment. 

!!! YOU HAVE TO SETUP YOUR OWN API AND ADD IN THE API LINK IN JSON FILE TO FUNCTION NORMALLY!!! 

Refer to the repo above. Koyeb is also one of the options. 

I take the trouble to spider a little bit more extra movie info from DMM 'cause I always feel like to read them while javbus does not include such info. The original code is from the wonderful work of "https://github.com/metatube-community/jellyfin-plugin-metatube". I have been using this so long and never dreamed of programming with it oneday. 

An extra online player was added in to the request of a net friend. I also tried the great accomplishment of MIYUKI Downloader. (It's gone now and we all know why) 
Spec file to pack is also included. 

Thanks a lot to all the great opensource. And Cursor. 

# JavBus Lite

A simplified graphical interface program for JavBus, featuring video search and playback functionality.

## Features

- Search actors and videos
- View detailed actor information
- Obtain video magnet links
- Built-in video player (VLC-based)
- Support video downloads
- Local data caching

## System Requirements

- Windows 7/8/10/11 64-bit OS
- [VLC Media Player](https://www.videolan.org/vlc/) (required for video playback)
- Internet connection (for data retrieval and video playback)

## Packaging Instructions

This project uses PyInstaller to package into executable files, requiring no Python environment to run.

### Packaging Steps

1. Ensure Python 3.7+ and pip are installed
2. Install required libraries:
   ```
   pip install pyinstaller pillow pyqt5 python-vlc curl_cffi requests beautifulsoup4 pyperclip
   ```
3. Run packaging script:
   ```
   build_exe.bat
   ```
4. Two versions will be generated in the dist directory after packaging:
   - `JavBusGUI` folder (Directory Edition)
   - `JavBus All-in-One.exe` file (All-in-One Edition)

## Version Description

- **Directory Edition**: Separated files, smaller footprint, faster startup
- **All-in-One Edition**: Single EXE file, easy distribution, larger size, slower startup

## User Guide

1. Ensure VLC Media Player is installed
2. Run the program:
   - Directory Edition: Run `JavBusGUI\JavBusGUI.exe`
   - All-in-One Edition: Directly run `JavBus All-in-One.exe`
3. Use the search box in the top-left corner to search for actors or videos
4. Select an actor to view their works list
5. Select a video to view details, obtain magnet links, or play previews

## Playback & Download

1. Click "Play" button to use built-in player after selecting a video
2. Player supports basic functions: pause, volume adjustment, fullscreen
3. Click "Download" button to save video to local downloads directory

## Notes

- Necessary directories and database files will be automatically created on first run
- Caches viewed actor/video information to reduce network requests
- VLC Media Player required for playback functionality
- Stable internet connection required for downloads

## FAQ

**Q: Videos cannot play after program launch**  
A: Ensure VLC Media Player is installed and properly recognized

**Q: Errors occur during playback/download**  
A: Could be network issues or resource access restrictions - check connection or use proxy

**Q: Packaging errors**  
A: Verify all required Python libraries are installed and follow packaging instructions

灵感来源于 "https://github.com/ovnrain/javbus-api" 的优秀作品。该方案在网络受限环境下尤其便利。

!!! 您必须自行搭建API并将接口链接添加到JSON文件中才能正常使用!!! 

请参考上述仓库，Koyeb也是可选部署方案之一。

我特意从DMM抓取了更多影片元数据——还挺有意思的，而javbus本身并不包含此类内容。原始代码来自 "https://github.com/metatube-community/jellyfin-plugin-metatube" 这一杰出项目。我长期使用该插件，却从未想过有朝一日会基于它进行二次开发。
应网友要求新增了在线播放功能。尝试集成了MIYUKI下载器的卓越方案（现在去哪了……）。
项目包含打包配置文件（.spec file）和.bat。

感谢所有伟大的开源项目，以及Cursor智能编辑器。


# JavBus简易版

这是一个简易的JavBus图形界面程序，包含影片搜索和播放功能。

## 功能特点

- 搜索演员和影片
- 查看演员详细信息
- 获取影片磁力链接
- 内置视频播放器（基于VLC）
- 支持影片下载
- 本地数据缓存

## 系统需求

- Windows 7/8/10/11 64位操作系统
- [VLC媒体播放器](https://www.videolan.org/vlc/)（用于视频播放）
- 网络连接（用于获取数据和播放视频）

## 打包说明

本项目使用PyInstaller打包为可执行文件，无需安装Python环境即可运行。

### 打包步骤

1. 确保已安装Python 3.7+和pip
2. 安装所需的库：
   ```
   pip install pyinstaller pillow pyqt5 python-vlc curl_cffi requests beautifulsoup4 pyperclip
   ```
3. 运行打包脚本：
   ```
   build_exe.bat
   ```
4. 打包完成后，在dist目录下会生成两个版本：
   - `JavBusGUI`文件夹（目录版）
   - `JavBus一体版.exe`文件（一体版）

## 版本说明

- **目录版**：文件分离，占用空间较小，启动较快
- **一体版**：单个EXE文件，便于分发，但体积较大，启动较慢

## 使用说明

1. 确保已安装VLC媒体播放器
2. 运行程序：
   - 目录版：运行`JavBusGUI\JavBusGUI.exe`
   - 一体版：直接运行`JavBus一体版.exe`
3. 使用界面左上方的搜索框搜索演员或影片
4. 选择演员后可查看其作品列表
5. 选择影片后可查看详情、获取磁力链接或播放预览

## 播放和下载

1. 选择影片后，点击"播放"按钮可使用内置播放器播放视频
2. 播放器支持暂停、调整音量、全屏等基本功能
3. 点击"下载"按钮可下载视频到本地downloads目录

## 注意事项

- 首次运行时会自动创建必要的目录和数据库文件
- 软件会缓存已浏览的演员和影片信息，减少网络请求
- 播放功能需要安装VLC媒体播放器
- 下载功能需要网络连接稳定

## 常见问题

**Q: 程序打开后无法播放视频**
A: 请确保已安装VLC媒体播放器并正确识别

**Q: 播放或下载时出现错误**
A: 可能是网络问题或资源访问限制，请检查网络连接或使用代理

**Q: 打包时出现错误**
A: 请确保已安装所有必要的Python库，并按照打包说明操作
