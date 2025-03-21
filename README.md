Inspired by the nice work of "https://github.com/ovnrain/javbus-api". Really convenience especially when you are in a limited network environment. 
##!!! YOU HAVE TO SETUP YOUR OWN API AND ADD IN THE API LINK IN JSON FILE TO FUNCTION NORMALLY!!! Refer to the repo above. Koyeb is also one of the options. 

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
