import os
import sys
import logging
import shutil

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_environment():
    """设置应用环境，创建必要的目录和文件"""
    try:
        # 确定应用程序路径
        if getattr(sys, 'frozen', False):
            # 运行在打包环境
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller的_MEIPASS是临时目录
                application_path = os.path.dirname(sys.executable)
            else:
                application_path = os.path.dirname(sys.executable)
        else:
            # 运行在开发环境
            application_path = os.path.dirname(os.path.abspath(__file__))
        
        # 确保工作目录设置正确
        os.chdir(application_path)
        logging.info(f"应用路径: {application_path}")
        logging.info(f"当前工作目录: {os.getcwd()}")
        
        # 创建视频相关目录
        video_dirs = [
            'buspic',
            'buspic/stars',
            'downloads',  # 用于保存下载的视频
            'temp'
        ]
        
        for directory in video_dirs:
            dir_path = os.path.join(application_path, directory)
            os.makedirs(dir_path, exist_ok=True)
            logging.info(f"确保目录存在: {dir_path}")

        # 确保配置文件存在
        fanza_mapping_file = os.path.join(application_path, 'fanza_mappings.json')
        if not os.path.exists(fanza_mapping_file):
            # 如果在打包环境中，可能需要从资源文件复制
            if hasattr(sys, '_MEIPASS'):
                source_file = os.path.join(sys._MEIPASS, 'fanza_mappings.json')
                if os.path.exists(source_file):
                    shutil.copy2(source_file, fanza_mapping_file)
                    logging.info(f"从资源复制Fanza映射文件: {source_file} -> {fanza_mapping_file}")
                else:
                    # 创建空映射文件
                    with open(fanza_mapping_file, 'w', encoding='utf-8') as f:
                        f.write('{}')
                    logging.info(f"创建空的Fanza映射文件: {fanza_mapping_file}")
            else:
                # 创建空映射文件
                with open(fanza_mapping_file, 'w', encoding='utf-8') as f:
                    f.write('{}')
                logging.info(f"创建空的Fanza映射文件: {fanza_mapping_file}")
            
        # 确保数据库文件存在
        db_file = os.path.join(application_path, 'javbus_data.db')
        if not os.path.exists(db_file):
            # 创建一个空的SQLite数据库
            import sqlite3
            conn = sqlite3.connect(db_file)
            logging.info(f"创建新的数据库文件: {db_file}")
            
            # 创建必要的表
            cursor = conn.cursor()
            
            # 创建演员表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS stars (
                id TEXT PRIMARY KEY,
                name TEXT,
                data TEXT,
                last_updated INTEGER
            )
            ''')
            
            # 创建影片表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS movies (
                id TEXT PRIMARY KEY,
                title TEXT,
                data TEXT,
                last_updated INTEGER
            )
            ''')
            
            # 创建搜索历史表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                keyword TEXT PRIMARY KEY,
                last_search INTEGER
            )
            ''')
            
            conn.commit()
            conn.close()
            logging.info("数据库表创建完成")
        
        # 确保VLC配置存在（如果有自定义的配置）
        vlc_config_file = os.path.join(application_path, 'vlc_config.py')
        if hasattr(sys, '_MEIPASS') and not os.path.exists(vlc_config_file):
            source_file = os.path.join(sys._MEIPASS, 'vlc_config.py')
            if os.path.exists(source_file):
                shutil.copy2(source_file, vlc_config_file)
                logging.info(f"从资源复制VLC配置文件: {source_file} -> {vlc_config_file}")
        
        # 确保video_player2.py存在（如果需要动态加载）
        player_file = os.path.join(application_path, 'video_player2.py')
        if hasattr(sys, '_MEIPASS') and not os.path.exists(player_file):
            source_file = os.path.join(sys._MEIPASS, 'video_player2.py')
            if os.path.exists(source_file):
                shutil.copy2(source_file, player_file)
                logging.info(f"从资源复制视频播放器模块: {source_file} -> {player_file}")
            
    except Exception as e:
        logging.error(f"设置环境时出错: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())

# 程序启动时立即执行
setup_environment() 