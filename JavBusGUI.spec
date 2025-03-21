# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# 收集VLC的数据文件
vlc_binaries = []
vlc_datas = []

# 尝试检测VLC安装位置并收集其DLL文件
if sys.platform.startswith('win'):
    # Windows系统上VLC的可能安装位置
    vlc_paths = [
        os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'VideoLAN', 'VLC'),
        os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'VideoLAN', 'VLC'),
        # 用户可能将VLC安装到其他位置，比如D盘
        'D:\\Program Files\\VideoLAN\\VLC',
        'D:\\Program Files (x86)\\VideoLAN\\VLC',
    ]
    
    for vlc_path in vlc_paths:
        if os.path.exists(vlc_path):
            print(f"找到VLC安装目录: {vlc_path}")
            
            # 添加plugins目录
            plugins_path = os.path.join(vlc_path, 'plugins')
            if os.path.exists(plugins_path):
                for root, dirs, files in os.walk(plugins_path):
                    for file in files:
                        if file.endswith('.dll'):
                            rel_dir = os.path.relpath(root, vlc_path)
                            vlc_datas.append((os.path.join(root, file), os.path.join('plugins', rel_dir)))
            
            # 添加主要的VLC DLL文件
            for file in os.listdir(vlc_path):
                if file.endswith('.dll'):
                    vlc_binaries.append((os.path.join(vlc_path, file), '.'))
            
            break
    else:
        print("警告: 未找到VLC安装目录，程序可能无法正常工作！")

# 检查是否有curl_cffi数据文件
curl_cffi_datas = collect_data_files('curl_cffi')

a = Analysis(
    ['javbus_gui_improved.py'],  # 主程序入口
    pathex=[],
    binaries=vlc_binaries,  # 添加VLC二进制文件
    datas=[
        ('fb.ico', '.'),  # 图标文件
        ('fanza_mappings.json', '.'),  # Fanza映射配置文件
        ('movieinfo.py', '.'),  # 电影信息处理模块
        ('javbus_db.py', '.'),  # 数据库操作模块
        ('video_player2.py', '.'),  # 影片搜索播放模块
        ('video_player2_stub.py', '.'),  # VideoPlayer2的存根文件
    ] + vlc_datas + curl_cffi_datas,  # 合并VLC数据文件和curl_cffi数据文件
    hiddenimports=[
        'sqlite3',
        'json',
        'os',
        're',
        'requests',
        'bs4',
        'PyQt5',
        'PyQt5.QtWidgets',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'PIL',
        'PIL.Image',
        'PIL.ImageQt',
        'vlc',
        'curl_cffi',
        'curl_cffi.requests',
        'winreg',  # Windows注册表访问（用于系统代理检测）
        'platform',
        'subprocess',
        'threading',
        'argparse',
        'traceback',
        'logging',
        'shutil',
        'time',
        'datetime',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['create_directories.py'],  # 使用create_directories.py设置环境
    excludes=[],
    noarchive=False,
    optimize=0,
)

# 将所有内容压缩为PYZ归档
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 创建可执行文件
exe = EXE(
    pyz,
    a.scripts,
    [],  # 不要将所有内容包含在EXE中，而是使用外部的PKG文件
    exclude_binaries=True,  # 排除二进制文件，单独包装
    name='JavBusGUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 设置为False以隐藏控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='fb.ico',
)

# 创建整个包，包含所有依赖
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='JavBusGUI',
)

# 创建一键式独立可执行文件（所有内容都包含在一个EXE中）
onefile_exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='JavBus一体版',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='fb.ico',
)
