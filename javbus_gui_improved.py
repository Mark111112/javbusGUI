import sys
import os
import re
import json
import time
import requests
import shutil
from datetime import datetime, timedelta
import threading
from PIL import Image, ImageQt
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem, QGridLayout, 
                            QTableWidget, QTableWidgetItem, QHeaderView, 
                            QMessageBox, QSplitter, QProgressBar, QMenu, QTextBrowser,
                            QDialog, QListView, QStackedWidget, QAction, QMenuBar, QAbstractItemView,
                            QGroupBox, QFrame, QSizePolicy, QComboBox, QFileDialog, QTabWidget, 
                            QCheckBox, QInputDialog, QStatusBar, QScrollArea, QSpinBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPoint, QEvent, QTimer, QObject
from PyQt5.QtGui import QPixmap, QImage, QCursor, QTextCursor, QIcon, QColor
import pyperclip  # 用于复制文本到剪贴板
import sqlite3
import queue
from javbus_db import JavbusDatabase
from movieinfo import FanzaScraper  # 导入FanzaScraper类
import tkinter as tk
from tkinter import messagebox

# 定义默认配置
DEFAULT_API_URL = ""  # 默认为空，要求用户必须设置
DEFAULT_WATCH_URL_PREFIX = "https://missav.ai"  # 默认观看URL前缀
CONFIG_FILE = "config.json"  # 配置文件名

# 加载配置
def load_config():
    """加载配置文件"""
    config = {
        "api_url": DEFAULT_API_URL,
        "watch_url_prefix": DEFAULT_WATCH_URL_PREFIX,
        "fanza_mappings": {}
    }
    
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                # 更新配置，但保留默认值作为备份
                config.update(loaded_config)
                print(f"已加载配置文件: {CONFIG_FILE}")
    except Exception as e:
        print(f"加载配置文件失败: {str(e)}")
    
    # 如果配置中没有fanza_mappings，尝试从原来的fanza_mappings.json加载
    if not config["fanza_mappings"] and os.path.exists("fanza_mappings.json"):
        try:
            with open("fanza_mappings.json", 'r', encoding='utf-8') as f:
                config["fanza_mappings"] = json.load(f)
                print("已从fanza_mappings.json加载番号映射")
                # 将映射保存到新的配置文件中
                save_config(config)
        except Exception as e:
            print(f"加载fanza_mappings.json失败: {str(e)}")
    
    return config

# 保存配置
def save_config(config):
    """保存配置到文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
            print(f"已保存配置到: {CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"保存配置失败: {str(e)}")
        return False

# 获取当前配置
CURRENT_CONFIG = load_config()
CURRENT_API_URL = CURRENT_CONFIG.get("api_url", DEFAULT_API_URL)
CURRENT_WATCH_URL_PREFIX = CURRENT_CONFIG.get("watch_url_prefix", DEFAULT_WATCH_URL_PREFIX)

# 添加这个函数来检查video_player2.py是否存在
def check_video_player_module():
    if not os.path.exists("video_player2.py"):
        QMessageBox.warning(None, "警告", "未找到video_player2.py模块，无法使用播放功能")
        return False
    return True

# 添加导入video_player2模块的函数，通过动态导入避免直接依赖
def import_video_player():
    if not check_video_player_module():
        return None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("video_player2", "video_player2.py")
        video_player = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(video_player)
        return video_player
    except Exception as e:
        QMessageBox.critical(None, "错误", f"无法导入video_player2模块: {str(e)}")
        return None

# 导入翻译模块
from translator import get_translator

class OptionsDialog(QDialog):
    """选项设置对话框"""
    
    def __init__(self, parent=None, current_api_url=CURRENT_API_URL, current_watch_url_prefix=CURRENT_WATCH_URL_PREFIX):
        super().__init__(parent)
        self.parent = parent
        self.current_api_url = current_api_url
        self.current_watch_url_prefix = current_watch_url_prefix
        
        # 获取翻译器实例
        self.translator = get_translator()
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("选项")
        self.setMinimumSize(500, 300)
        self.resize(600, 800)  # 设置默认窗口大小为600x800
        
        # 创建主布局
        main_layout = QHBoxLayout(self)
        
        # 左侧列表
        self.option_list = QListWidget()
        self.option_list.setMinimumWidth(150)  # 增加左侧列表的最小宽度
        self.option_list.setStyleSheet("""
            QListWidget {
                background-color: #f5f5f5;
                border-right: 1px solid #ddd;
            }
            QListWidget::item {
                padding: 10px;
            }
            QListWidget::item:selected {
                background-color: #e0e0e0;
                color: #000;
            }
        """)
        main_layout.addWidget(self.option_list)
        
        # 添加选项到列表
        self.option_list.addItem("一般选项")
        self.option_list.addItem("Fanza对应")  # 新增Fanza对应选项
        self.option_list.addItem("翻译设置")  # 新增翻译设置选项
        self.option_list.setCurrentRow(0)  # 选中第一项
        
        # 右侧堆叠窗口
        self.option_stack = QStackedWidget()
        main_layout.addWidget(self.option_stack)
        
        # 创建一般选项页面
        self.create_general_options_page()
        
        # 创建Fanza对应页面
        self.create_fanza_mapping_page()
        
        # 创建翻译设置页面
        self.create_translation_settings_page()
        
        # 底部按钮
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.ok_button.setMinimumWidth(100)
        self.ok_button.setMinimumHeight(36)
        self.ok_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.setMinimumHeight(36)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        # 将按钮布局添加到右侧布局
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.option_stack)
        right_layout.addLayout(button_layout)
        
        main_layout.addLayout(right_layout)
        
        # 连接信号和槽
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.option_list.currentRowChanged.connect(self.option_stack.setCurrentIndex)
    
    def create_general_options_page(self):
        """创建一般选项页面"""
        general_page = QWidget()
        layout = QVBoxLayout(general_page)
        layout.setSpacing(15)  # 增加间距
        
        # API设置
        api_section = QGroupBox("API设置")
        api_layout = QVBoxLayout(api_section)
        
        # 说明文字
        api_desc = QLabel("请在下方输入API地址，此项必须设置，否则程序无法正常运行。")
        api_desc.setWordWrap(True)
        api_desc.setStyleSheet("color: #FF0000; font-weight: bold;")  # 红色加粗文字提示必须设置
        api_layout.addWidget(api_desc)
        
        # 显示输入框
        placeholder_text = "输入API地址"
        self.api_input = QLineEdit(self.current_api_url)
        self.api_input.setPlaceholderText(placeholder_text)
        self.api_input.setMinimumHeight(30)  # 增加高度使其更易点击
        api_layout.addWidget(self.api_input)
        
        # API操作按钮
        api_button_layout = QHBoxLayout()
        self.apply_api_button = QPushButton("应用")
        self.apply_api_button.setMinimumWidth(80)
        self.reset_api_button = QPushButton("重置")
        self.reset_api_button.setMinimumWidth(80)
        
        api_button_layout.addWidget(self.apply_api_button)
        api_button_layout.addWidget(self.reset_api_button)
        api_button_layout.addStretch()
        
        api_layout.addLayout(api_button_layout)
        layout.addWidget(api_section)
        
        # 视频站点设置
        watch_section = QGroupBox("视频站点设置")
        watch_layout = QVBoxLayout(watch_section)
        
        # 说明文字
        watch_desc = QLabel("设置观看视频的网站地址前缀，默认为https://missav.ai，仅在网站地址变更时需要修改。")
        watch_desc.setWordWrap(True)
        watch_layout.addWidget(watch_desc)
        
        # 网站前缀输入框
        self.watch_url_prefix_input = QLineEdit(self.current_watch_url_prefix)
        self.watch_url_prefix_input.setPlaceholderText("输入视频网站地址前缀")
        self.watch_url_prefix_input.setMinimumHeight(30)
        watch_layout.addWidget(self.watch_url_prefix_input)
        
        # 按钮布局
        watch_button_layout = QHBoxLayout()
        self.apply_watch_button = QPushButton("应用")
        self.apply_watch_button.setMinimumWidth(80)
        self.reset_watch_button = QPushButton("重置")
        self.reset_watch_button.setMinimumWidth(80)
        
        watch_button_layout.addWidget(self.apply_watch_button)
        watch_button_layout.addWidget(self.reset_watch_button)
        watch_button_layout.addStretch()
        
        watch_layout.addLayout(watch_button_layout)
        layout.addWidget(watch_section)
        
        # 添加一些附加信息
        info_label = QLabel("注意：修改以上设置后，需要点击应用按钮才能生效。如遇问题，请尝试重置为默认设置。")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        # 添加到堆叠窗口
        self.option_stack.addWidget(general_page)
        
        # 连接信号和槽
        self.apply_api_button.clicked.connect(self.apply_api)
        self.reset_api_button.clicked.connect(self.reset_api)
        self.apply_watch_button.clicked.connect(self.apply_watch_url_prefix)
        self.reset_watch_button.clicked.connect(self.reset_watch_url_prefix)
    
    def create_fanza_mapping_page(self):
        """创建Fanza对应页面"""
        fanza_page = QWidget()
        layout = QVBoxLayout(fanza_page)
        
        # 标题
        title_label = QLabel("番号对应关系")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        # 说明文字
        description_label = QLabel("此处管理JavBus番号与Fanza番号的对应关系，修改后点击保存。")
        description_label.setWordWrap(True)
        layout.addWidget(description_label)
        
        # 创建表格
        self.mapping_table = QTableWidget()
        self.mapping_table.setColumnCount(2)
        self.mapping_table.setHorizontalHeaderLabels(["JavBus番号", "Fanza番号"])
        self.mapping_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.mapping_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.mapping_table.setAlternatingRowColors(True)  # 交替行颜色
        self.mapping_table.setStyleSheet("alternate-background-color: #f0f0f0;")
        self.mapping_table.verticalHeader().setDefaultSectionSize(30)  # 行高
        self.mapping_table.setSelectionBehavior(QAbstractItemView.SelectRows)  # 整行选择
        layout.addWidget(self.mapping_table)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 添加按钮
        add_button = QPushButton("添加")
        add_button.clicked.connect(self.add_mapping)
        add_button.setMinimumWidth(80)
        
        # 删除按钮
        delete_button = QPushButton("删除")
        delete_button.clicked.connect(self.delete_mapping)
        delete_button.setMinimumWidth(80)
        
        # 保存按钮
        save_button = QPushButton("保存")
        save_button.clicked.connect(self.save_mappings)
        save_button.setMinimumWidth(80)
        save_button.setStyleSheet("background-color: #4CAF50; color: white;")
        
        button_layout.addWidget(add_button)
        button_layout.addWidget(delete_button)
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        
        layout.addLayout(button_layout)
        
        # 添加到堆叠窗口
        self.option_stack.addWidget(fanza_page)
        
        # 加载现有映射
        self.load_mappings()
    
    def load_mappings(self):
        """加载番号对应关系"""
        try:
            # 从配置文件中读取映射关系
            from movieinfo import FanzaScraper
            scraper = FanzaScraper()
            mappings = scraper.get_mappings()
            
            # 设置表格行数
            self.mapping_table.setRowCount(len(mappings))
            
            # 填充数据
            for i, (javbus_id, fanza_id) in enumerate(mappings.items()):
                self.mapping_table.setItem(i, 0, QTableWidgetItem(javbus_id))
                self.mapping_table.setItem(i, 1, QTableWidgetItem(fanza_id))
        except Exception as e:
            QMessageBox.warning(self, "警告", f"加载番号对应关系失败: {str(e)}")
    
    def add_mapping(self):
        """添加新的番号对应关系"""
        row = self.mapping_table.rowCount()
        self.mapping_table.insertRow(row)
    
    def delete_mapping(self):
        """删除选中的番号对应关系"""
        current_row = self.mapping_table.currentRow()
        if current_row >= 0:
            self.mapping_table.removeRow(current_row)
    
    def save_mappings(self):
        """保存番号对应关系"""
        try:
            # 收集所有映射关系
            mappings = {}
            for row in range(self.mapping_table.rowCount()):
                javbus_id = self.mapping_table.item(row, 0).text().strip()
                fanza_id = self.mapping_table.item(row, 1).text().strip()
                if javbus_id and fanza_id:
                    mappings[javbus_id] = fanza_id
            
            # 保存到新的配置文件
            config = load_config()
            config["fanza_mappings"] = mappings
            if save_config(config):
                # 同时更新FanzaScraper
                from movieinfo import FanzaScraper
                scraper = FanzaScraper()
                scraper.set_mappings(mappings)
                
                QMessageBox.information(self, "成功", "番号对应关系已保存到配置文件")
            else:
                QMessageBox.warning(self, "警告", "保存番号对应关系失败")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存番号对应关系失败: {str(e)}")
    
    def apply_api(self):
        """应用新的API设置"""
        new_api_url = self.api_input.text().strip()
        if not new_api_url:
            QMessageBox.warning(self, "警告", "API地址不能为空，必须设置!")
            return
        
        self.current_api_url = new_api_url
        if self.parent:
            self.parent.api_base_url = new_api_url
            self.parent.statusBar().showMessage(f"已应用API地址: {new_api_url}", 3000)
            
            # 更新配置
            config = load_config()
            config["api_url"] = new_api_url
            save_config(config)
            
            # 检测API连接
            self.parent.check_api_connection()
    
    def reset_api(self):
        """重置API设置"""
        self.api_input.setText(DEFAULT_API_URL)
        self.current_api_url = DEFAULT_API_URL
        if self.parent:
            self.parent.api_base_url = DEFAULT_API_URL
            self.parent.statusBar().showMessage("已重置API地址，请设置有效的API地址", 3000)
            
            # 更新配置
            config = load_config()
            config["api_url"] = DEFAULT_API_URL
            save_config(config)
            
            # 检测API连接
            self.parent.check_api_connection()
    
    def apply_watch_url_prefix(self):
        """应用新的观看链接前缀"""
        new_prefix = self.watch_url_prefix_input.text().strip()
        if not new_prefix:
            QMessageBox.warning(self, "警告", "视频网站地址前缀不能为空")
            return
        
        self.current_watch_url_prefix = new_prefix
        if self.parent:
            self.parent.watch_url_prefix = new_prefix
            self.parent.statusBar().showMessage(f"已应用视频网站地址前缀: {new_prefix}", 3000)
            
            # 更新配置
            config = load_config()
            config["watch_url_prefix"] = new_prefix
            save_config(config)
    
    def reset_watch_url_prefix(self):
        """重置观看链接前缀为默认值"""
        self.watch_url_prefix_input.setText(DEFAULT_WATCH_URL_PREFIX)
        self.current_watch_url_prefix = DEFAULT_WATCH_URL_PREFIX
        if self.parent:
            self.parent.watch_url_prefix = DEFAULT_WATCH_URL_PREFIX
            self.parent.statusBar().showMessage(f"已重置视频网站地址前缀为: {DEFAULT_WATCH_URL_PREFIX}", 3000)
            
            # 更新配置
            config = load_config()
            config["watch_url_prefix"] = DEFAULT_WATCH_URL_PREFIX
            save_config(config)
    
    @staticmethod
    def get_options(parent=None, current_api_url=CURRENT_API_URL, current_watch_url_prefix=CURRENT_WATCH_URL_PREFIX):
        """静态方法，打开选项对话框并返回结果"""
        dialog = OptionsDialog(parent, current_api_url, current_watch_url_prefix)
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            return dialog.current_api_url, dialog.current_watch_url_prefix
        return current_api_url, current_watch_url_prefix

    def create_translation_settings_page(self):
        """创建翻译设置页面"""
        translation_page = QWidget()
        layout = QVBoxLayout(translation_page)
        layout.setSpacing(15)  # 增加间距
        
        # API类型选择
        api_type_section = QGroupBox("API类型")
        api_type_layout = QVBoxLayout(api_type_section)
        
        self.api_type_combo = QComboBox()
        self.api_type_combo.addItem("OpenAI兼容API", "openai")
        self.api_type_combo.addItem("Ollama本地API", "ollama")
        self.api_type_combo.addItem("SiliconFlow API", "siliconflow")
        
        # 根据当前API URL自动选择API类型
        current_api_url = self.translator.api_url.lower()
        if "localhost:11434" in current_api_url or "127.0.0.1:11434" in current_api_url:
            self.api_type_combo.setCurrentIndex(1)  # Ollama
        elif "siliconflow.cn" in current_api_url:
            self.api_type_combo.setCurrentIndex(2)  # SiliconFlow
        else:
            self.api_type_combo.setCurrentIndex(0)  # OpenAI兼容
            
        # 连接信号
        self.api_type_combo.currentIndexChanged.connect(self.on_api_type_changed)
        
        api_type_layout.addWidget(self.api_type_combo)
        layout.addWidget(api_type_section)
        
        # 翻译API设置
        api_section = QGroupBox("翻译API设置")
        api_layout = QGridLayout(api_section)
        
        # API URL
        api_url_label = QLabel("API URL:")
        self.api_url_input = QLineEdit(self.translator.api_url)
        self.api_url_input.setPlaceholderText("输入API地址，如https://api.openai.com/v1/chat/completions")
        api_layout.addWidget(api_url_label, 0, 0)
        api_layout.addWidget(self.api_url_input, 0, 1)
        
        # 源语言
        source_lang_label = QLabel("源语言:")
        self.source_lang_input = QLineEdit(self.translator.source_lang)
        self.source_lang_input.setPlaceholderText("输入源语言，如日语")
        api_layout.addWidget(source_lang_label, 1, 0)
        api_layout.addWidget(self.source_lang_input, 1, 1)
        
        # 目标语言
        target_lang_label = QLabel("目标语言:")
        self.target_lang_input = QLineEdit(self.translator.target_lang)
        self.target_lang_input.setPlaceholderText("输入目标语言，如中文")
        api_layout.addWidget(target_lang_label, 2, 0)
        api_layout.addWidget(self.target_lang_input, 2, 1)
        
        # API Token
        api_token_label = QLabel("API Token:")
        self.api_token_input = QLineEdit(self.translator.api_token)
        self.api_token_input.setPlaceholderText("输入API密钥")
        self.api_token_input.setEchoMode(QLineEdit.Password)
        api_layout.addWidget(api_token_label, 3, 0)
        api_layout.addWidget(self.api_token_input, 3, 1)
        
        # 模型
        model_label = QLabel("模型:")
        self.model_input = QComboBox()
        api_layout.addWidget(model_label, 4, 0)
        api_layout.addWidget(self.model_input, 4, 1)
        
        # 获取模型列表按钮
        self.get_models_button = QPushButton("获取可用模型")
        self.get_models_button.clicked.connect(self.get_available_models)
        api_layout.addWidget(self.get_models_button, 5, 1)
        
        # 初始化模型列表
        self.init_model_list()
        
        layout.addWidget(api_section)
        
        # 说明
        desc_label = QLabel("翻译设置用于将影片简介翻译成目标语言。设置支持OpenAI兼容API、SiliconFlow API和本地Ollama API。")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666;")
        layout.addWidget(desc_label)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        apply_button = QPushButton("应用设置")
        apply_button.setMinimumWidth(100)
        apply_button.clicked.connect(self.apply_translation_settings)
        
        test_button = QPushButton("测试连接")
        test_button.setMinimumWidth(100)
        test_button.clicked.connect(self.test_translation_api)
        
        button_layout.addWidget(test_button)
        button_layout.addWidget(apply_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        # 添加到堆叠窗口
        self.option_stack.addWidget(translation_page)
    
    def init_model_list(self):
        """初始化模型列表"""
        self.model_input.clear()
        
        # 根据当前选中的API类型设置模型列表
        api_type = self.api_type_combo.currentData()
        
        if api_type == "ollama":
            # Ollama默认模型
            default_models = ["llama3", "mistral", "gemma", "qwen", "codellama", "phi", "llama2", "llama2-uncensored"]
        elif api_type == "siliconflow":
            # SiliconFlow 模型
            default_models = [
                "THUDM/glm-4-9b-chat", 
                "Qwen/QwQ-32B", 
                "Qwen/Qwen2-72B-Instruct",
                "Meta-Llama-3-8B-Instruct",
                "Meta-Llama-3-70B-Instruct"
            ]
        else:
            # OpenAI兼容模型
            default_models = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-3.5-turbo-16k"]
        
        # 添加默认模型
        for model in default_models:
            self.model_input.addItem(model)
        
        # 设置当前选中的模型
        current_index = self.model_input.findText(self.translator.model)
        if current_index >= 0:
            self.model_input.setCurrentIndex(current_index)
        else:
            # 如果当前模型不在预设列表中，添加它
            self.model_input.addItem(self.translator.model)
            self.model_input.setCurrentText(self.translator.model)
            
        # 设置为可编辑，允许用户输入自定义模型名称
        self.model_input.setEditable(True)
    
    def on_api_type_changed(self, index):
        """当API类型改变时更新UI"""
        api_type = self.api_type_combo.currentData()
        
        if api_type == "ollama":
            # 设置Ollama默认URL
            self.api_url_input.setText("http://localhost:11434/api/generate")
            # Ollama通常不需要token
            self.api_token_input.setEnabled(False)
            self.api_token_input.setPlaceholderText("Ollama通常不需要API Token")
        elif api_type == "siliconflow":
            # 设置SiliconFlow默认URL
            self.api_url_input.setText("https://api.siliconflow.cn/v1/chat/completions")
            # SiliconFlow需要token
            self.api_token_input.setEnabled(True)
            self.api_token_input.setPlaceholderText("输入SiliconFlow API密钥")
        else:
            # OpenAI兼容API
            self.api_url_input.setText("https://api.openai.com/v1/chat/completions")
            self.api_token_input.setEnabled(True)
            self.api_token_input.setPlaceholderText("输入API密钥")
        
        # 更新模型列表
        self.init_model_list()
    
    def get_available_models(self):
        """获取可用模型列表"""
        api_type = self.api_type_combo.currentData()
        api_url = self.api_url_input.text().strip()
        api_token = self.api_token_input.text().strip()
        
        if not api_url:
            QMessageBox.warning(self, "警告", "请先输入API URL")
            return
        
        # 对于非Ollama API，需要验证token
        if api_type != "ollama" and not api_token:
            QMessageBox.warning(self, "警告", "请先输入API Token")
            return
        
        # 设置等待光标
        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        try:
            if api_type == "ollama":
                # 获取Ollama模型列表
                models = self.translator.get_ollama_models(api_url, api_token)
                
                if models:
                    # 清空并更新模型下拉列表
                    self.model_input.clear()
                    for model in models:
                        self.model_input.addItem(model)
                    QMessageBox.information(self, "成功", f"成功获取到{len(models)}个Ollama模型")
                else:
                    QMessageBox.warning(self, "警告", "未能获取到Ollama模型，请确认Ollama服务已启动")
            else:
                QMessageBox.information(self, "提示", "当前API类型不支持获取模型列表，请手动输入模型名称")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"获取模型列表失败: {str(e)}")
        finally:
            # 恢复正常光标
            QApplication.restoreOverrideCursor()
            
    def apply_translation_settings(self):
        """应用翻译设置"""
        api_url = self.api_url_input.text().strip()
        source_lang = self.source_lang_input.text().strip()
        target_lang = self.target_lang_input.text().strip()
        api_token = self.api_token_input.text().strip()
        model = self.model_input.currentText()
        
        # 验证输入
        if not api_url:
            QMessageBox.warning(self, "警告", "API URL不能为空")
            return
            
        if not source_lang:
            QMessageBox.warning(self, "警告", "源语言不能为空")
            return
            
        if not target_lang:
            QMessageBox.warning(self, "警告", "目标语言不能为空")
            return
            
        # 对于非Ollama API，需要验证token
        api_type = self.api_type_combo.currentData()
        if api_type != "ollama" and not api_token:
            QMessageBox.warning(self, "警告", "API Token不能为空")
            return
            
        # 保存设置
        if self.translator.save_config(api_url, source_lang, target_lang, api_token, model):
            QMessageBox.information(self, "成功", "翻译设置已保存")
        else:
            QMessageBox.warning(self, "错误", "保存翻译设置失败")
    
    def test_translation_api(self):
        """测试翻译API连接"""
        # 获取当前输入的设置
        api_url = self.api_url_input.text().strip()
        api_token = self.api_token_input.text().strip()
        model = self.model_input.currentText()
        api_type = self.api_type_combo.currentData()
        
        # 验证输入
        if not api_url:
            QMessageBox.warning(self, "警告", "API URL不能为空")
            return
            
        # 对于非Ollama API，需要验证token
        if api_type != "ollama" and not api_token:
            QMessageBox.warning(self, "警告", "API Token不能为空")
            return
            
        # 设置等待光标
        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        try:
            # 准备请求头
            headers = {
                "Content-Type": "application/json"
            }
            
            if api_token:
                headers["Authorization"] = f"Bearer {api_token}"
            
            # 根据API类型构建不同的请求负载和URL
            test_api_url = api_url
            
            if api_type == "ollama":
                # Ollama API - 修改URL使用generate接口
                ollama_url = api_url
                if "/api/chat" in ollama_url:
                    # 将chat改为generate
                    ollama_url = ollama_url.replace("/api/chat", "/api/generate")
                elif not "/api/generate" in ollama_url:
                    # 确保URL指向generate接口
                    base_url = ollama_url
                    if base_url.endswith("/"):
                        base_url = base_url[:-1]
                    if not "/api" in base_url:
                        ollama_url = f"{base_url}/api/generate"
                    else:
                        ollama_url = f"{base_url}/generate"
                        
                test_api_url = ollama_url
                print(f"使用Ollama生成API: {ollama_url}")
                
                # Ollama API格式
                payload = {
                    "model": model,
                    "prompt": "Say 'Translation API works!' in Chinese.",
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9
                    }
                }
            elif api_type == "siliconflow":
                # SiliconFlow API格式
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Say 'Translation API works!' in Chinese."}
                    ],
                    "temperature": 0.3,
                    "stream": False,
                    "max_tokens": 512,
                    "top_p": 0.7,
                    "top_k": 50,
                    "response_format": {"type": "text"}
                }
            else:
                # OpenAI兼容API
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Say 'Translation API works!' in Chinese."}
                    ],
                    "temperature": 0.3
                }
            
            print(f"测试API: {test_api_url}, 模型: {model}")
            print(f"请求头: {headers}")
            print(f"请求数据: {payload}")
            
            # 发送请求
            response = requests.post(
                test_api_url,
                headers=headers,
                json=payload,
                timeout=60  # 增加超时时间到60秒
            )
            
            # 恢复正常光标
            QApplication.restoreOverrideCursor()
            
            if response.status_code == 200:
                result = response.json()
                print(f"API响应: {result}")
                
                # 尝试从不同格式的响应中提取内容
                message = ""
                
                # Ollama API格式 - 处理generate接口的响应
                if api_type == "ollama":
                    if "response" in result:
                        message = result["response"]
                    elif "message" in result and isinstance(result["message"], dict):
                        if "content" in result["message"] and result["message"]["content"]:
                            message = result["message"]["content"]
                    
                    # 如果响应为空但done_reason为load，表示模型正在加载
                    if not message and "done_reason" in result and result["done_reason"] == "load":
                        QMessageBox.warning(self, "模型加载中", "模型正在加载中，请稍后重试")
                        return
                # 标准OpenAI格式
                elif "choices" in result and len(result["choices"]) > 0:
                    choice = result["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        message = choice["message"]["content"]
                    elif "text" in choice:
                        message = choice["text"]
                
                if message:
                    QMessageBox.information(self, "测试成功", f"API响应成功: {message}")
                else:
                    QMessageBox.warning(self, "警告", "API响应成功，但无法提取内容，请检查响应格式")
            else:
                error_detail = ""
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        if isinstance(error_data["error"], dict):
                            error_detail = error_data["error"].get("message", "")
                        else:
                            error_detail = str(error_data["error"])
                except:
                    error_detail = response.text[:200]
                
                error_message = f"API连接失败: HTTP {response.status_code}"
                if error_detail:
                    error_message += f"\n{error_detail}"
                
                QMessageBox.critical(self, "错误", error_message)
        except Exception as e:
            # 恢复正常光标
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "错误", f"连接测试失败: {str(e)}")

class StarSearchThread(QThread):
    """用于在后台搜索演员的线程"""
    search_complete = pyqtSignal(list)
    search_error = pyqtSignal(str)
    
    def __init__(self, api_base_url, keyword, db):
        super().__init__()
        self.api_base_url = api_base_url
        self.keyword = keyword
        self.db = db
        
    def run(self):
        try:
            # 先从数据库中搜索
            db_stars = self.db.search_stars(self.keyword)
            if db_stars:
                print(f"从数据库中找到 {len(db_stars)} 个匹配的演员")
                self.search_complete.emit(db_stars)
                return
            
            # 如果数据库中没有，则使用演员搜索API
            # 由于API可能没有直接搜索演员的端点，使用带magnet=all参数搜索影片
            response = requests.get(f"{self.api_base_url}/movies/search", params={
                "keyword": self.keyword,
                "page": "1",
            })
            
            if response.status_code != 200:
                self.search_error.emit(f"API请求失败: {response.status_code}")
                return
            
            data = response.json()
            movies = data.get("movies", [])
            
            # 如果没有找到影片，尝试直接通过api端点搜索演员
            if not movies:
                try:
                    # 尝试直接查询演员端点
                    response = requests.get(f"{self.api_base_url}/stars", params={
                        "keyword": self.keyword,
                    })
                    
                    if response.status_code == 200:
                        stars_data = response.json()
                        stars = stars_data.get("stars", [])
                        if stars:
                            # 只保留基本信息
                            simplified_stars = [
                                {"id": star.get("id"), "name": star.get("name", "未知")}
                                for star in stars
                            ]
                            self.search_complete.emit(simplified_stars)
                            return
                except Exception as e:
                    print(f"尝试获取演员列表失败: {str(e)}")
            
            # 从影片中提取演员信息
            # 获取前30部影片中的详细信息来提取演员
            all_stars = []
            unique_star_ids = set()
            
            for movie in movies[:30]:
                movie_id = movie.get("id")
                if movie_id:
                    try:
                        movie_response = requests.get(f"{self.api_base_url}/movies/{movie_id}")
                        if movie_response.status_code == 200:
                            movie_data = movie_response.json()
                            stars = movie_data.get("stars", [])
                            
                            for star in stars:
                                star_id = star.get("id")
                                if star_id and star_id not in unique_star_ids:
                                    unique_star_ids.add(star_id)
                                    # 只保存基本信息，不获取详细资料
                                    simplified_star = {
                                        "id": star_id,
                                        "name": star.get("name", "未知")
                                    }
                                    all_stars.append(simplified_star)
                    except Exception as e:
                        print(f"获取影片 {movie_id} 详情失败: {str(e)}")
            
            # 只保留名称中包含关键词的演员
            keyword_lower = self.keyword.lower()
            filtered_stars = [
                star for star in all_stars 
                if keyword_lower in star.get("name", "").lower()
            ]
            
            # 返回结果
            self.search_complete.emit(filtered_stars)
            
        except Exception as e:
            self.search_error.emit(f"搜索失败: {str(e)}")

class MovieLoadThread(QThread):
    """用于在后台加载影片的线程"""
    load_complete = pyqtSignal(list, dict)
    load_error = pyqtSignal(str)
    
    def __init__(self, api_base_url, star_id, page, db, star_name="", title_search=False, magnet_only=True):
        super().__init__()
        self.api_base_url = api_base_url
        self.star_id = star_id
        self.page = page
        self.star_name = star_name
        self.title_search = title_search
        self.db = db
        self.magnet_only = magnet_only
        
    def run(self):
        try:
            # 先从数据库中获取演员的影片
            if not self.title_search:
                db_movies = self.db.get_star_movies(self.star_id)
                if db_movies:
                    print(f"从数据库中找到 {len(db_movies)} 部演员影片")
                    # 创建分页信息
                    pagination = {
                        "currentPage": 1,
                        "hasNextPage": False,
                        "nextPage": None
                    }
                    self.load_complete.emit(db_movies, pagination)
                    return
            
            # 如果数据库中没有或者是按名称搜索，则从API获取
            params = {}
            if self.title_search and self.star_name:
                # 搜索影片名称中包含演员名称的影片
                params = {
                    "keyword": self.star_name,
                    "page": str(self.page)
                }
                # 只有当需要包含无磁力影片时才添加magnet参数
                if not self.magnet_only:
                    params["magnet"] = "all"
                response = requests.get(f"{self.api_base_url}/movies/search", params=params)
            else:
                # 搜索演员参演的所有影片
                params = {
                    "filterType": "star",
                    "filterValue": self.star_id,
                    "page": str(self.page)
                }
                # 只有当需要包含无磁力影片时才添加magnet参数
                if not self.magnet_only:
                    params["magnet"] = "all"
                response = requests.get(f"{self.api_base_url}/movies", params=params)
            
            if response.status_code != 200:
                self.load_error.emit(f"获取影片列表失败: {response.status_code}")
                return
            
            data = response.json()
            movies = data.get("movies", [])
            pagination = data.get("pagination", {})
            
            # 如果是按名称搜索，直接使用API返回的结果
            if self.title_search and self.star_name:
                # 不再创建filtered_movies列表，直接使用API返回的movies
                # 不再检查数据库中是否已有该影片
                # 不再获取每个影片的详细信息
                
                # 更新分页信息
                pagination["currentPage"] = self.page
                pagination["hasNextPage"] = len(movies) >= 30  # 假设每页30个结果
                pagination["nextPage"] = self.page + 1 if pagination["hasNextPage"] else None
            else:
                # 检查数据库中是否已有这些影片
                for i, movie in enumerate(movies):
                    movie_id = movie.get("id")
                    if movie_id:
                        # 检查数据库中是否已有该影片
                        db_movie = self.db.get_movie(movie_id)
                        if db_movie:
                            # 如果数据库中有，用数据库中的数据替换
                            movies[i] = db_movie
                        # 不再主动获取详情，减少API请求
            
            self.load_complete.emit(movies, pagination)
            
        except Exception as e:
            self.load_error.emit(f"获取影片列表失败: {str(e)}")

class ImageDownloadThread(QThread):
    """用于在后台下载图片的线程"""
    image_downloaded = pyqtSignal(str, str)  # 参数：(图片路径, 图片类型)
    download_complete = pyqtSignal()
    download_error = pyqtSignal(str)
    
    def __init__(self, movie_id, api_base_url, movie_data, save_dir):
        super().__init__()
        self.movie_id = movie_id
        self.api_base_url = api_base_url
        self.movie_data = movie_data
        self.save_dir = save_dir
        
    def run(self):
        try:
            # 设置请求头，模拟浏览器行为
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Referer": "https://www.javbus.com/",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
            
            # 下载封面图
            cover_url = self.movie_data.get("img")
            if cover_url:
                # 下载封面图
                image_response = requests.get(cover_url, headers=headers, timeout=10)
                if image_response.status_code != 200:
                    # 尝试使用另一种方法
                    session = requests.Session()
                    session.headers.update(headers)
                    # 先访问影片页面建立会话
                    session.get(f"https://www.javbus.com/{self.movie_id}")
                    # 再次尝试下载图片
                    image_response = session.get(cover_url, timeout=10)
                
                if image_response.status_code == 200:
                    # 保存封面图
                    file_extension = os.path.splitext(cover_url)[1] or ".jpg"
                    cover_path = os.path.join(self.save_dir, f"cover{file_extension}")
                    with open(cover_path, "wb") as f:
                        f.write(image_response.content)
                    
                    # 发送信号通知已下载封面
                    self.image_downloaded.emit(cover_path, "cover")
            
            # 下载预览图
            samples = self.movie_data.get("samples", [])
            for i, sample in enumerate(samples):
                sample_url = sample.get("src")
                if not sample_url:
                    continue
                
                try:
                    # 下载预览图
                    sample_response = requests.get(sample_url, headers=headers, timeout=10)
                    if sample_response.status_code != 200:
                        # 尝试使用另一种方法
                        session = requests.Session()
                        session.headers.update(headers)
                        # 先访问影片页面建立会话
                        session.get(f"https://www.javbus.com/{self.movie_id}")
                        # 再次尝试下载图片
                        sample_response = session.get(sample_url, timeout=10)
                    
                    if sample_response.status_code == 200:
                        # 保存预览图
                        file_extension = os.path.splitext(sample_url)[1] or ".jpg"
                        sample_path = os.path.join(self.save_dir, f"sample_{i+1}{file_extension}")
                        with open(sample_path, "wb") as f:
                            f.write(sample_response.content)
                        
                        # 发送信号通知已下载预览图
                        self.image_downloaded.emit(sample_path, "sample")
                except Exception as e:
                    print(f"下载预览图 {sample_url} 失败: {str(e)}")
            
            # 发送下载完成信号
            self.download_complete.emit()
            
        except Exception as e:
            self.download_error.emit(f"下载图片失败: {str(e)}")

class SummaryWorker(QObject):
    """用于在后台获取影片简介的工作类"""
    summary_ready = pyqtSignal(str, str)  # 参数：(movie_id, summary)
    summary_error = pyqtSignal(str, str)  # 参数：(movie_id, error_message)
    translation_ready = pyqtSignal(str, str, str)  # 参数：(movie_id, original_summary, translated_summary)
    translation_error = pyqtSignal(str, str)  # 参数：(movie_id, error_message)
    title_translation_ready = pyqtSignal(str, str)  # 参数：(movie_id, translated_title)
    
    def __init__(self, movie_id, movie_data, db=None):
        super().__init__()
        self.movie_id = movie_id
        self.movie_data = movie_data
        self.db = db
        
        # 获取翻译器实例
        self.translator = get_translator()
        
    def get_summary(self):
        """获取影片简介"""
        try:
            # 首先启动标题翻译，不需要等待简介结果
            title = self.movie_data.get("title", "")
            if title:
                # 立即开始标题翻译，不等待简介结果
                QTimer.singleShot(100, lambda: self.translate_title(title))
            
            # 检查movie_data是否已有摘要信息
            summary = self.movie_data.get("summary", "")
            
            # 如果没有摘要，则通过FanzaScraper获取
            if not summary:
                # 创建FanzaScraper实例并获取摘要
                scraper = FanzaScraper()
                summary_result = scraper.get_movie_summary(self.movie_id)
                
                if "error" not in summary_result:
                    summary = summary_result.get("summary", "")
                    # 更新数据库中的影片信息
                    self.movie_data["summary"] = summary
                    # 保存到数据库
                    if self.db:
                        self.db.save_movie(self.movie_data)
                else:
                    error = summary_result.get("error", "未知错误")
                    self.summary_error.emit(self.movie_id, error)
                    # 即使获取简介失败，也不影响后续逻辑
            
            # 发射信号通知获取到的摘要
            self.summary_ready.emit(self.movie_id, summary)
            
            # 如果有摘要，尝试翻译
            if summary:
                # 连接翻译器的信号
                self.translator.translation_ready.connect(self.on_translation_ready)
                self.translator.translation_error.connect(self.on_translation_error)
                
                # 发送翻译请求
                QTimer.singleShot(1000, lambda: self.translator.translate(self.movie_id, summary))
                
        except Exception as e:
            print(f"获取影片摘要失败: {str(e)}")
            self.summary_error.emit(self.movie_id, str(e))
            
            # 即使获取简介出错，仍然尝试翻译标题
            title = self.movie_data.get("title", "")
            if title:
                try:
                    QTimer.singleShot(100, lambda: self.translate_title(title))
                except Exception as title_error:
                    print(f"安排标题翻译时出错: {str(title_error)}")
    
    def translate_title(self, title):
        """翻译影片标题"""
        try:
            print(f"开始翻译标题: {title}")
            # 使用translator发送翻译请求
            # 创建一个临时ID用于标题翻译，避免与摘要翻译混淆
            temp_id = f"{self.movie_id}_title"
            
            # 使用自定义连接器
            try:
                self.translator.translation_ready.connect(self.on_title_translation_ready)
                self.translator.translation_error.connect(self.on_title_translation_error)
            except Exception as e:
                print(f"连接标题翻译信号时出错: {str(e)}")
            
            # 发送翻译请求
            self.translator.translate(temp_id, title)
        except Exception as e:
            print(f"翻译标题失败: {str(e)}")
            # 即使出错也不中断其他处理
    
    def on_title_translation_ready(self, temp_id, original_text, translated_text):
        """处理标题翻译完成的回调"""
        # 检查是否是标题翻译的临时ID
        if temp_id.endswith("_title") and temp_id.split("_title")[0] == self.movie_id:
            # 断开连接，避免重复接收信号
            self.translator.translation_ready.disconnect(self.on_title_translation_ready)
            self.translator.translation_error.disconnect(self.on_title_translation_error)
            
            # 发射标题翻译完成信号
            self.title_translation_ready.emit(self.movie_id, translated_text)
    
    def on_title_translation_error(self, temp_id, error_message):
        """处理标题翻译错误的回调"""
        # 检查是否是标题翻译的临时ID
        if temp_id.endswith("_title") and temp_id.split("_title")[0] == self.movie_id:
            # 断开连接，避免重复接收信号
            self.translator.translation_ready.disconnect(self.on_title_translation_ready)
            self.translator.translation_error.disconnect(self.on_title_translation_error)
            
            print(f"标题翻译错误: {error_message}")
    
    def on_translation_ready(self, movie_id, original_summary, translated_summary):
        """处理翻译完成的回调"""
        if movie_id == self.movie_id:
            # 发射翻译完成信号
            print(f"SummaryWorker: 收到翻译结果，长度 {len(translated_summary)}")
            self.translation_ready.emit(movie_id, original_summary, translated_summary)
            
            # 断开信号连接，避免重复接收
            try:
                self.translator.translation_ready.disconnect(self.on_translation_ready)
                self.translator.translation_error.disconnect(self.on_translation_error)
                print("已断开翻译信号连接")
            except Exception as e:
                print(f"断开翻译信号连接时出错: {str(e)}")
    
    def on_translation_error(self, movie_id, error_message):
        """处理翻译错误的回调"""
        if movie_id == self.movie_id:
            # 发射翻译错误信号
            print(f"SummaryWorker: 翻译出错: {error_message}")
            self.translation_error.emit(movie_id, error_message)
            
            # 断开信号连接，避免重复接收
            try:
                self.translator.translation_ready.disconnect(self.on_translation_ready)
                self.translator.translation_error.disconnect(self.on_translation_error)
            except Exception as e:
                print(f"断开翻译信号连接时出错: {str(e)}")

class JavbusGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        # 从配置文件获取API地址和视频网站前缀
        self.api_base_url = CURRENT_API_URL
        self.watch_url_prefix = CURRENT_WATCH_URL_PREFIX
        self.current_page = 1
        self.current_star_id = None
        self.current_movie_keyword = None  # 新增变量，保存当前搜索的影片关键字
        self.search_thread = None
        self.movie_load_thread = None
        self.db = JavbusDatabase()  # 初始化数据库
        
        # 设置应用程序图标
        icon_path = "fb.ico"
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.init_ui()
        
        # 检查API连接
        self.check_api_connection()
        
    def closeEvent(self, event):
        """应用程序关闭时的处理"""
        # 清理所有线程
        self._cleanup_threads()
        
        # 关闭数据库连接
        self.db.close()
        super().closeEvent(event)
    
    def check_api_connection(self):
        """检查API连接状态"""
        if not self.api_base_url:
            self.statusBar().showMessage("请设置API地址", 0)  # 0表示永久显示
            # 设置状态栏文字颜色为红色
            self.statusBar().setStyleSheet("QStatusBar{color:red;font-weight:bold;}")
            
            # 弹出警告
            QMessageBox.warning(self, "警告", "请在选项中设置API地址，否则程序无法正常工作！")
            return False
            
        try:
            # 尝试连接API
            url = f"{self.api_base_url}/stars/1"  # 尝试请求第一页演员数据
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                self.statusBar().showMessage("API连接正常", 3000)
                # 恢复状态栏默认样式
                self.statusBar().setStyleSheet("")
                return True
            else:
                error_msg = f"API连接错误: HTTP {response.status_code}"
                self.statusBar().showMessage(error_msg, 0)
                self.statusBar().setStyleSheet("QStatusBar{color:red;font-weight:bold;}")
                return False
                
        except Exception as e:
            error_msg = f"API连接失败: {str(e)}"
            self.statusBar().showMessage(error_msg, 0)
            self.statusBar().setStyleSheet("QStatusBar{color:red;font-weight:bold;}")
            return False
    
    def init_ui(self):
        self.setWindowTitle('JavBus简易版')  # 修改窗口标题
        self.setGeometry(100, 100, 1680, 900)  # 增加窗口宽度以适应更宽的中间栏
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        
        # 创建三列分割器
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # 左侧面板 - 搜索和演员列表
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        
        # 搜索模式选择 - 移至顶部
        search_mode_frame = QFrame()
        search_mode_frame.setFrameShape(QFrame.StyledPanel)
        search_mode_frame.setStyleSheet("QFrame { background-color: #f5f5f5; border-radius: 4px; }")
        search_mode_layout = QVBoxLayout(search_mode_frame)
        
        search_mode_title = QLabel("搜索模式:")
        search_mode_title.setStyleSheet("font-weight: bold;")
        search_mode_layout.addWidget(search_mode_title)
        
        search_mode_buttons = QHBoxLayout()
        self.title_search_radio = QPushButton("影片名称包含演员名")
        self.title_search_radio.setCheckable(True)
        self.title_search_radio.setChecked(True)
        self.all_movies_radio = QPushButton("演员参演的所有影片")
        self.all_movies_radio.setCheckable(True)
        
        # 设置按钮组，确保只有一个按钮被选中
        self.title_search_radio.clicked.connect(lambda: self.all_movies_radio.setChecked(False))
        self.all_movies_radio.clicked.connect(lambda: self.title_search_radio.setChecked(False))
        
        search_mode_buttons.addWidget(self.title_search_radio)
        search_mode_buttons.addWidget(self.all_movies_radio)
        search_mode_layout.addLayout(search_mode_buttons)
        
        left_layout.addWidget(search_mode_frame)
        
        # 添加一般查询功能（原影片编号查询）
        movie_search_layout = QVBoxLayout()
        movie_search_layout.setSpacing(5)
        
        movie_search_title = QLabel("一般查询:")
        movie_search_title.setStyleSheet("font-weight: bold;")
        movie_search_layout.addWidget(movie_search_title)
        
        movie_search_input_layout = QHBoxLayout()
        self.movie_search_input = QLineEdit()
        self.movie_search_input.setPlaceholderText("输入编号、厂牌、演员等关键词")
        self.movie_search_input.returnPressed.connect(self.search_movie_by_id)
        
        self.movie_search_button = QPushButton("查询")
        self.movie_search_button.clicked.connect(self.search_movie_by_id)
        
        movie_search_input_layout.addWidget(self.movie_search_input)
        movie_search_input_layout.addWidget(self.movie_search_button)
        
        movie_search_layout.addLayout(movie_search_input_layout)
        
        # 添加只包含有磁力影片选项
        self.magnet_only_checkbox = QPushButton("只包含有磁力影片")
        self.magnet_only_checkbox.setCheckable(True)
        self.magnet_only_checkbox.setChecked(True)  # 默认选中
        movie_search_layout.addWidget(self.magnet_only_checkbox)
        
        left_layout.addLayout(movie_search_layout)
        
        # 添加间隔 - 在一般查询和演员查询之间
        spacer = QFrame()
        spacer.setFrameShape(QFrame.HLine)
        spacer.setFrameShadow(QFrame.Sunken)
        spacer.setStyleSheet("background-color: #e0e0e0;")
        left_layout.addSpacing(10)
        left_layout.addWidget(spacer)
        left_layout.addSpacing(10)
        
        # 演员查询功能
        star_search_layout = QVBoxLayout()
        star_search_layout.setSpacing(5)
        
        # 添加演员查询标题
        star_search_title = QLabel("演员查询:")
        star_search_title.setStyleSheet("font-weight: bold;")
        star_search_layout.addWidget(star_search_title)
        
        # 搜索框
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入演员名称")
        self.search_input.returnPressed.connect(self.search_stars)
        self.search_button = QPushButton("搜索")
        self.search_button.clicked.connect(self.search_stars)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        star_search_layout.addLayout(search_layout)
        
        left_layout.addLayout(star_search_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)
        
        # 演员列表 - 减小高度
        left_layout.addWidget(QLabel("演员列表:"))
        self.stars_list = QListWidget()
        self.stars_list.setMaximumHeight(200)  # 减小演员列表的高度
        self.stars_list.itemClicked.connect(self.on_star_selected)
        left_layout.addWidget(self.stars_list)
        
        # 演员信息 - 放在演员列表下方
        self.star_info_widget = QWidget()
        self.star_info_layout = QGridLayout()
        self.star_info_widget.setLayout(self.star_info_layout)
        
        # 演员头像
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(150, 150)  # 减小头像尺寸
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.star_info_layout.addWidget(self.avatar_label, 0, 0, 6, 1)
        
        # 演员基本信息
        self.name_label = QLabel("姓名: ")
        self.birthday_label = QLabel("生日: ")
        self.age_label = QLabel("年龄: ")
        self.height_label = QLabel("身高: ")
        self.bust_label = QLabel("胸围: ")
        self.waistline_label = QLabel("腰围: ")
        self.hipline_label = QLabel("臀围: ")
        self.birthplace_label = QLabel("出生地: ")
        self.hobby_label = QLabel("爱好: ")
        
        self.star_info_layout.addWidget(self.name_label, 0, 1)
        self.star_info_layout.addWidget(self.birthday_label, 1, 1)
        self.star_info_layout.addWidget(self.age_label, 2, 1)
        self.star_info_layout.addWidget(self.height_label, 3, 1)
        self.star_info_layout.addWidget(self.bust_label, 0, 2)
        self.star_info_layout.addWidget(self.waistline_label, 1, 2)
        self.star_info_layout.addWidget(self.hipline_label, 2, 2)
        self.star_info_layout.addWidget(self.birthplace_label, 3, 2)
        self.star_info_layout.addWidget(self.hobby_label, 4, 1, 1, 2)
        
        left_layout.addWidget(self.star_info_widget)
        
        # 添加批量下载功能
        batch_download_layout = QVBoxLayout()
        batch_download_layout.setSpacing(5)
        
        batch_download_title = QLabel("批量下载:")
        batch_download_title.setStyleSheet("font-weight: bold;")
        batch_download_layout.addWidget(batch_download_title)
        
        batch_download_input_layout = QHBoxLayout()
        
        # 前X页输入框
        prev_pages_label = QLabel("前")
        self.prev_pages_input = QLineEdit()
        self.prev_pages_input.setFixedWidth(40)
        self.prev_pages_input.setPlaceholderText("1")
        prev_pages_unit = QLabel("页")
        
        # 后X页输入框
        next_pages_label = QLabel("后")
        self.next_pages_input = QLineEdit()
        self.next_pages_input.setFixedWidth(40)
        self.next_pages_input.setPlaceholderText("1")
        next_pages_unit = QLabel("页")
        
        # 下载按钮
        self.batch_download_button = QPushButton("下载页面内影片图片")
        self.batch_download_button.clicked.connect(self.start_batch_download)
        
        # 添加到布局
        batch_download_input_layout.addWidget(prev_pages_label)
        batch_download_input_layout.addWidget(self.prev_pages_input)
        batch_download_input_layout.addWidget(prev_pages_unit)
        batch_download_input_layout.addWidget(next_pages_label)
        batch_download_input_layout.addWidget(self.next_pages_input)
        batch_download_input_layout.addWidget(next_pages_unit)
        batch_download_input_layout.addWidget(self.batch_download_button)
        
        batch_download_layout.addLayout(batch_download_input_layout)
        left_layout.addLayout(batch_download_layout)
        
        # 在左侧面板底部（批量下载区域后面）添加播放按钮
        # 添加播放功能
        play_layout = QVBoxLayout()
        play_layout.setSpacing(5)
        
        play_title = QLabel("视频播放:")
        play_title.setStyleSheet("font-weight: bold;")
        play_layout.addWidget(play_title)
        
        play_button_layout = QHBoxLayout()
        self.play_video_button = QPushButton("播放选中影片")
        self.play_video_button.setStyleSheet("""
            QPushButton {
                background-color: #ff4500;
                color: white;
                border-radius: 4px;
                padding: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff6347;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #888888;
            }
        """)
        self.play_video_button.setEnabled(False)  # 初始状态禁用，直到选中影片
        self.play_video_button.clicked.connect(self.play_selected_video)
        
        play_button_layout.addWidget(self.play_video_button)
        play_layout.addLayout(play_button_layout)
        
        # 添加说明文本
        play_note = QLabel("注意: 需要安装VLC播放器和python-vlc模块")
        play_note.setStyleSheet("color: #888888; font-size: 10px;")
        play_layout.addWidget(play_note)
        
        left_layout.addSpacing(15)
        left_layout.addLayout(play_layout)
        
        # 为了确保布局正确，最后添加一个弹性空间
        left_layout.addStretch()
        
        # 中间面板 - 影片列表
        middle_panel = QWidget()
        middle_layout = QVBoxLayout()
        middle_panel.setLayout(middle_layout)
        
        # 影片列表控制区
        movies_control_layout = QHBoxLayout()
        movies_label = QLabel("影片列表:")
        self.refresh_button = QPushButton("刷新数据")
        self.refresh_button.setToolTip("清除当前演员的缓存数据并重新加载")
        self.refresh_button.clicked.connect(self.refresh_star_data)
        self.refresh_button.setEnabled(False)
        movies_control_layout.addWidget(movies_label)
        movies_control_layout.addStretch()
        movies_control_layout.addWidget(self.refresh_button)
        middle_layout.addLayout(movies_control_layout)
        
        # 影片列表 - 增加高度以占满中间栏
        self.movies_table = QTableWidget(0, 3)
        self.movies_table.setHorizontalHeaderLabels(["影片编号", "影片名称", "发行日期"])
        self.movies_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        
        # 设置影片名称列宽，使其能显示约18个汉字
        self.movies_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.movies_table.setColumnWidth(1, 270)  # 设置固定宽度，一个汉字约15像素
        
        # 设置发行日期列宽
        self.movies_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.movies_table.setColumnWidth(2, 100)  # 设置日期列固定宽度，确保完全显示10个字符
        
        self.movies_table.itemClicked.connect(self.on_movie_selected)
        middle_layout.addWidget(self.movies_table, 1)  # 添加拉伸因子1，使表格占满剩余空间
        
        # 分页控制
        pagination_layout = QHBoxLayout()
        self.page_label = QLabel("第1页")
        self.prev_page_button = QPushButton("上一页")
        self.prev_page_button.clicked.connect(self.load_prev_page)
        self.prev_page_button.setEnabled(False)
        self.next_page_button = QPushButton("下一页")
        self.next_page_button.clicked.connect(self.load_next_page)
        self.next_page_button.setEnabled(False)
        pagination_layout.addWidget(self.prev_page_button)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_page_button)
        pagination_layout.addStretch()
        
        middle_layout.addLayout(pagination_layout)
        
        # 右侧面板 - 图片预览区
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        
        # 图片预览区
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(600, 400)  # 修改为600*400
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px solid #cccccc;")
        self.preview_label.setText("选择影片查看图片")
        
        # 预览图控制按钮
        preview_control_layout = QHBoxLayout()
        self.prev_image_button = QPushButton("上一页")
        self.prev_image_button.clicked.connect(self.show_prev_image)
        self.prev_image_button.setEnabled(False)
        
        self.image_index_label = QLabel("0/0")
        
        self.next_image_button = QPushButton("下一页")
        self.next_image_button.clicked.connect(self.show_next_image)
        self.next_image_button.setEnabled(False)
        
        preview_control_layout.addWidget(self.prev_image_button)
        preview_control_layout.addWidget(self.image_index_label)
        preview_control_layout.addWidget(self.next_image_button)
        
        # 添加厂牌和类别信息区域 - 使用可选择的文本标签
        movie_info_layout = QVBoxLayout()
        movie_info_layout.setSpacing(2)  # 减少垂直间距
        
        # 使用QTextBrowser而不是QLabel，使文本可复制和点击
        self.producer_text = QTextBrowser()
        self.producer_text.setMaximumHeight(30)  # 限制高度
        self.producer_text.setOpenLinks(False)  # 不自动打开链接
        self.producer_text.setText("厂牌: ")
        self.producer_text.setStyleSheet("background-color: transparent; border: none;")
        self.producer_text.mousePressEvent = lambda e: self.handle_text_click(e, self.producer_text)
        
        self.genres_text = QTextBrowser()
        self.genres_text.setMaximumHeight(60)  # 多行类别可能需要更多空间
        self.genres_text.setOpenLinks(False)
        self.genres_text.setText("类别: ")
        self.genres_text.setStyleSheet("background-color: transparent; border: none;")
        self.genres_text.mousePressEvent = lambda e: self.handle_text_click(e, self.genres_text)
        
        # 添加影片简介组件
        self.summary_text = QTextBrowser()
        self.summary_text.setMaximumHeight(100)  # 给摘要分配较多空间
        self.summary_text.setOpenLinks(False)
        self.summary_text.setText("简介: ")
        self.summary_text.setStyleSheet("background-color: transparent; border: none;")
        
        self.stars_text = QTextBrowser()
        self.stars_text.setMaximumHeight(30)
        self.stars_text.setOpenLinks(False)
        self.stars_text.setText("演员: ")
        self.stars_text.setStyleSheet("background-color: transparent; border: none;")
        self.stars_text.mousePressEvent = lambda e: self.handle_text_click(e, self.stars_text)
        
        # 添加title_text控件来显示影片标题
        self.title_text = QTextBrowser()
        self.title_text.setMaximumHeight(30)  # 限制高度
        self.title_text.setOpenLinks(False)   # 不自动打开链接
        self.title_text.setText("片名: ")
        self.title_text.setStyleSheet("background-color: transparent; border: none;")
        
        movie_info_layout.addWidget(self.title_text)
        movie_info_layout.addWidget(self.producer_text)
        movie_info_layout.addWidget(self.genres_text)
        movie_info_layout.addWidget(self.summary_text)  # 添加简介组件到布局中
        movie_info_layout.addWidget(self.stars_text)
        
        # 磁力链接列表区域
        magnet_layout = QVBoxLayout()
        magnet_layout.setSpacing(2)  # 减少垂直间距
        magnet_label = QLabel("磁力链接:")
        self.magnet_list = QListWidget()
        self.magnet_list.setFixedHeight(200)  # 设置高度可容纳约10行文字
        self.magnet_list.itemDoubleClicked.connect(self.copy_magnet_link)  # 添加双击事件
        self.magnet_list.setContextMenuPolicy(Qt.CustomContextMenu)  # 设置自定义右键菜单
        self.magnet_list.customContextMenuRequested.connect(self.show_magnet_context_menu)  # 连接右键菜单事件
        
        # 添加复制按钮
        magnet_button_layout = QHBoxLayout()
        self.copy_magnet_button = QPushButton("复制选中的磁力链接")
        self.copy_magnet_button.clicked.connect(self.copy_selected_magnet)
        self.copy_magnet_button.setEnabled(False)  # 初始禁用
        magnet_button_layout.addWidget(self.copy_magnet_button)
        magnet_button_layout.addStretch()
        
        # 连接选择变化事件
        self.magnet_list.itemSelectionChanged.connect(self.on_magnet_selection_changed)
        
        magnet_layout.addWidget(magnet_label)
        magnet_layout.addWidget(self.magnet_list)
        magnet_layout.addLayout(magnet_button_layout)
        
        right_layout.addWidget(self.preview_label)
        right_layout.addLayout(preview_control_layout)
        right_layout.addLayout(movie_info_layout)  # 添加厂牌和类别信息
        right_layout.addLayout(magnet_layout)
        
        # 添加面板到分割器
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(middle_panel)
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([300, 780, 600])  # 调整初始分割比例，增加中间栏的宽度
        
        # 初始化图片预览相关变量
        self.current_images = []
        self.current_image_index = 0
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 添加"选项"菜单
        options_menu = menubar.addMenu("选项")
        
        # 添加系统设置菜单项
        option1_action = QAction("系统设置", self)
        option1_action.triggered.connect(self.open_options_dialog)
        options_menu.addAction(option1_action)
    
    def open_options_dialog(self):
        """打开选项设置对话框"""
        api_url, watch_url_prefix = OptionsDialog.get_options(self, self.api_base_url, self.watch_url_prefix)
        self.api_base_url = api_url
        self.watch_url_prefix = watch_url_prefix
    
    def search_stars(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "警告", "请输入演员名称")
            return
        
        # 清理批量下载状态，防止搜索时触发批量下载
        self.cleanup_batch_download_state()
        
        # 保存搜索历史
        self.db.save_search_history(keyword)
        
        # 禁用搜索按钮，显示进度条
        self.search_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 设置为不确定模式
        
        # 创建并启动搜索线程
        self.search_thread = StarSearchThread(self.api_base_url, keyword, self.db)
        self.search_thread.search_complete.connect(self.on_search_complete)
        self.search_thread.search_error.connect(self.on_search_error)
        self.search_thread.finished.connect(self.on_search_finished)
        self.search_thread.start()
    
    def on_search_complete(self, stars):
        # 更新列表
        self.stars_list.clear()
        for star in stars:
            self.stars_list.addItem(f"{star.get('name', '')} ({star.get('id', '')})")
        
        if not stars:
            QMessageBox.information(self, "提示", "未找到匹配的演员")
    
    def on_search_error(self, error_msg):
        QMessageBox.critical(self, "错误", error_msg)
    
    def on_search_finished(self):
        # 恢复搜索按钮，隐藏进度条
        self.search_button.setEnabled(True)
        self.progress_bar.setVisible(False)
    
    def on_star_selected(self, item):
        # 从列表项中提取演员ID
        text = item.text()
        star_id = text.split("(")[-1].strip(")")
        self.current_star_id = star_id
        self.current_page = 1
        
        # 清空上一次的影片演员信息
        self.stars_text.setText("演员: ")
        
        # 显示加载中状态
        self.avatar_label.setText("加载中...")
        self.name_label.setText("姓名: 正在加载...")
        self.birthday_label.setText("生日: ")
        self.age_label.setText("年龄: ")
        self.height_label.setText("身高: ")
        self.bust_label.setText("胸围: ")
        self.waistline_label.setText("腰围: ")
        self.hipline_label.setText("臀围: ")
        self.birthplace_label.setText("出生地: ")
        self.hobby_label.setText("爱好: ")
                
        # 获取演员影片（先加载影片列表，提高响应速度）
        self.load_star_movies(star_id, self.current_page)
        
        # 获取演员详情（在加载影片后再获取详情，避免阻塞）
        QTimer.singleShot(100, lambda: self.load_star_info(star_id))
        
        # 启用刷新按钮
        self.refresh_button.setEnabled(True)

    def on_movie_selected(self, item):
        """当选择影片时的处理"""
        # 清理之前的异步线程
        self._cleanup_threads()
        
        # 获取选中的行
        row = item.row()
        
        # 获取影片ID
        movie_id = self.movies_table.item(row, 0).text()
        self.current_movie_id = movie_id
        
        # 启用播放按钮
        self.play_video_button.setEnabled(True)
        
        # 显示加载指示器，但为异步加载设置为小进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(10)
        
        # 清空磁力链接列表
        self.magnet_list.clear()
        
        # 重置视图组件
        self.title_text.setText("片名: 加载中...")
        self.producer_text.setText("厂牌: 加载中...")
        self.genres_text.setText("类别: 加载中...")
        self.summary_text.setText("简介: 加载中...")
        self.stars_text.setText("演员: 加载中...")
        
        # 重置图片预览
        self.preview_label.setText("正在加载图片...")
        self.current_images = []
        self.current_image_index = 0
        self.image_index_label.setText("0/0")
        self.prev_image_button.setEnabled(False)
        self.next_image_button.setEnabled(False)
        
        try:
            # 创建保存目录
            save_dir = os.path.join("buspic", movie_id)
            os.makedirs(save_dir, exist_ok=True)
            
            # 第一步：立即显示本地已有的封面图片（如果有的话）
            local_images = self.get_local_images(save_dir)
            if local_images:
                # 找到封面（通常是文件名以cover开头的图片）
                cover_images = [img for img in local_images if os.path.basename(img).startswith('cover')]
                if cover_images:
                    # 先显示封面
                    self.current_images = cover_images
                    self.current_image_index = 0
                    self.display_current_image()
                    
                    # 添加其他预览图到图片列表
                    other_images = [img for img in local_images if not os.path.basename(img).startswith('cover')]
                    self.current_images.extend(other_images)
                    
                    # 更新图片计数
                    self.image_index_label.setText(f"1/{len(self.current_images)}")
                    self.next_image_button.setEnabled(len(self.current_images) > 1)
            
            # 第二步：从数据库或API获取基础影片信息并立即显示
            # 先从数据库中获取影片信息
            movie_data = self.db.get_movie(movie_id)
            
            # 如果数据库中没有，则从API获取
            if not movie_data:
                self.progress_bar.setValue(20)
                response = requests.get(f"{self.api_base_url}/movies/{movie_id}")
                
                if response.status_code != 200:
                    QMessageBox.warning(self, "错误", f"获取影片详情失败: {response.status_code}")
                    self.progress_bar.setVisible(False)
                    return
                
                movie_data = response.json()
                # 保存到数据库
                self.db.save_movie(movie_data)
            
            self.progress_bar.setValue(40)
            
            # 立即显示基础信息：片名、厂牌、类别、演员信息
            # 设置片名信息
            title = movie_data.get("title", "未知标题")
            
            # 更新片名显示
            self.title_text.setText(f'片名: {title}')
            
            # 设置厂牌信息
            producer = movie_data.get("producer", {})
            producer_name = producer.get("name", "未知厂牌")
            producer_id = producer.get("id", "")
            
            # 更新厂牌信息
            self.producer_text.setText(f'厂牌: <a href="{producer_id}">{producer_name}</a>')
            
            # 设置类别信息
            genres = movie_data.get("genres", [])
            genres_text = "类别: "
            for i, genre in enumerate(genres):
                genre_name = genre.get("name", "")
                genre_id = genre.get("id", "")
                if i > 0:
                    genres_text += ", "
                genres_text += f'<a href="{genre_id}">{genre_name}</a>'
            
            self.genres_text.setText(genres_text)
            
            # 设置演员信息
            stars = movie_data.get("stars", [])
            stars_text = "演员: "
            for i, star in enumerate(stars):
                star_name = star.get("name", "")
                star_id = star.get("id", "")
                if i > 0:
                    stars_text += ", "
                stars_text += f'<a href="{star_id}">{star_name}</a>'
            
            self.stars_text.setText(stars_text)
            
            # 显示磁力链接（从API获取，不需要网站爬取）
            self.display_magnets_from_movie_data(movie_data)
            
            # 进度条更新
            self.progress_bar.setValue(60)
            
            # 重置复制按钮状态
            self.copy_magnet_button.setEnabled(False)
            
            # 第三步：异步加载需要从网站爬取的信息
            
            # 简介信息加载（异步）
            self.summary_thread = QThread()
            self.scraper_worker = SummaryWorker(movie_id, movie_data, self.db)
            self.scraper_worker.moveToThread(self.summary_thread)
            self.summary_thread.started.connect(self.scraper_worker.get_summary)
            self.scraper_worker.summary_ready.connect(self.on_summary_loaded)
            self.scraper_worker.summary_error.connect(self.on_summary_error)
            
            # 连接翻译信号
            self.scraper_worker.translation_ready.connect(self.on_translation_ready)
            self.scraper_worker.translation_error.connect(self.on_translation_error)
            self.scraper_worker.title_translation_ready.connect(self.on_title_translation_ready)
            
            self.summary_thread.start()
            
            # 图片下载（异步，如果没有本地图片）
            if not local_images:
                # 创建并启动图片下载线程
                self.image_download_thread = ImageDownloadThread(movie_id, self.api_base_url, movie_data, save_dir)
                self.image_download_thread.image_downloaded.connect(self.on_image_downloaded)
                self.image_download_thread.download_complete.connect(self.on_images_download_complete)
                self.image_download_thread.download_error.connect(self.on_images_download_error)
                self.image_download_thread.start()
            else:
                # 已经完成所有任务，隐藏进度条
                self.progress_bar.setValue(100)
                self.progress_bar.setVisible(False)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取影片详情时出错: {str(e)}")
            self.progress_bar.setVisible(False)
    
    def load_star_info(self, star_id):
        try:
            # 先从数据库中获取演员信息
            star_info = self.db.get_star(star_id)
            
            # 如果数据库中没有，则从API获取
            if not star_info:
                response = requests.get(f"{self.api_base_url}/stars/{star_id}")
                
                if response.status_code != 200:
                    QMessageBox.warning(self, "错误", f"获取演员信息失败: {response.status_code}")
                    return
                
                star_info = response.json()
                # 保存到数据库
                self.db.save_star(star_info)
            
            # 更新演员信息
            self.name_label.setText(f"姓名: {star_info.get('name', '')}")
            self.birthday_label.setText(f"生日: {star_info.get('birthday', '')}")
            self.age_label.setText(f"年龄: {star_info.get('age', '')}")
            self.height_label.setText(f"身高: {star_info.get('height', '')}")
            self.bust_label.setText(f"胸围: {star_info.get('bust', '')}")
            self.waistline_label.setText(f"腰围: {star_info.get('waistline', '')}")
            self.hipline_label.setText(f"臀围: {star_info.get('hipline', '')}")
            self.birthplace_label.setText(f"出生地: {star_info.get('birthplace', '')}")
            self.hobby_label.setText(f"爱好: {star_info.get('hobby', '')}")
            
            # 加载头像
            avatar_url = star_info.get('avatar')
            if avatar_url:
                try:
                    # 保存头像的目录和文件路径
                    save_dir = os.path.join("buspic", "stars")
                    os.makedirs(save_dir, exist_ok=True)
                    file_extension = os.path.splitext(avatar_url)[1] or ".jpg"
                    save_path = os.path.join(save_dir, f"{star_id}{file_extension}")
                    
                    # 检查本地是否已有头像文件
                    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                        # 如果本地已有头像文件，直接加载
                        pixmap = QPixmap(save_path).scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        self.avatar_label.setPixmap(pixmap)
                        print(f"从本地加载演员头像: {save_path}")
                    else:
                        # 设置请求头，模拟浏览器行为
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                            "Referer": "https://www.javbus.com/",
                            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                            "Cache-Control": "no-cache",
                            "Pragma": "no-cache"
                        }
                        
                        # 下载头像
                        image_response = requests.get(avatar_url, headers=headers, timeout=10)
                        if image_response.status_code != 200:
                            # 尝试使用另一种方法
                            session = requests.Session()
                            session.headers.update(headers)
                            # 先访问演员页面建立会话
                            session.get(f"https://www.javbus.com/star/{star_id}")
                            # 再次尝试下载图片
                            image_response = session.get(avatar_url, timeout=10)
                            
                            if image_response.status_code != 200:
                                self.avatar_label.setText("头像加载失败")
                                return
                        
                        # 显示头像
                        image = QImage()
                        image.loadFromData(image_response.content)
                        pixmap = QPixmap(image).scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        self.avatar_label.setPixmap(pixmap)
                        
                        # 保存头像
                        with open(save_path, "wb") as f:
                            f.write(image_response.content)
                        print(f"下载并保存演员头像: {save_path}")
                    
                except Exception as e:
                    self.avatar_label.setText("头像加载失败")
                    print(f"加载头像失败: {str(e)}")
            else:
                self.avatar_label.setText("无头像")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取演员信息失败: {str(e)}")
    
    def load_star_movies(self, star_id, page):
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 设置为不确定模式
        
        # 根据搜索模式决定搜索参数
        if self.title_search_radio.isChecked():
            # 获取演员名称
            for i in range(self.stars_list.count()):
                item = self.stars_list.item(i)
                if star_id in item.text():
                    star_name = item.text().split(" (")[0]
                    break
            else:
                # 如果没有找到演员名称，直接获取演员信息
                star_info = self.db.get_star(star_id)
                if not star_info:
                    try:
                        response = requests.get(f"{self.api_base_url}/stars/{star_id}")
                        if response.status_code == 200:
                            star_info = response.json()
                            self.db.save_star(star_info)
                            star_name = star_info.get('name', '')
                        else:
                            star_name = ""
                    except Exception:
                        star_name = ""
                else:
                    star_name = star_info.get('name', '')
            
            # 创建并启动加载线程 - 搜索影片名称中包含演员名称的影片
            self.movie_load_thread = MovieLoadThread(self.api_base_url, star_id, page, self.db, star_name, True, self.magnet_only_checkbox.isChecked())
        else:
            # 创建并启动加载线程 - 搜索演员参演的所有影片
            self.movie_load_thread = MovieLoadThread(self.api_base_url, star_id, page, self.db, "", False, self.magnet_only_checkbox.isChecked())
            
        self.movie_load_thread.load_complete.connect(self.on_movies_loaded)
        self.movie_load_thread.load_error.connect(self.on_movies_load_error)
        self.movie_load_thread.finished.connect(self.on_movies_load_finished)
        self.movie_load_thread.start()
    
    def on_movies_loaded(self, movies, pagination):
        # 更新影片表格
        self.movies_table.setRowCount(0)
        
        # 按发行日期排序（新的在前）
        sorted_movies = sorted(movies, key=lambda x: x.get("date", ""), reverse=True)
        
        for movie in sorted_movies:
            row = self.movies_table.rowCount()
            self.movies_table.insertRow(row)
            
            # 设置影片编号
            movie_id = movie.get("id", "")
            self.movies_table.setItem(row, 0, QTableWidgetItem(movie_id))
            
            # 设置影片名称 - 去除与影片编号重复的部分
            title = movie.get("title", "")
            # 如果标题以影片编号开头，则去除这部分
            if movie_id and title.startswith(movie_id):
                title = title[len(movie_id):].strip()
            title_item = QTableWidgetItem(title)
            title_item.setToolTip(title)
            self.movies_table.setItem(row, 1, title_item)
            
            # 设置发行日期
            self.movies_table.setItem(row, 2, QTableWidgetItem(movie.get("date", "")))
        
        # 更新分页信息
        current_page = pagination.get("currentPage", 1)
        
        # 获取总页数 - 智能判断
        total_pages = self.calculate_total_pages(pagination, current_page)
        
        # 更新页码显示
        self.page_label.setText(f"第{current_page}页/共{total_pages}页")
        
        has_next_page = pagination.get("hasNextPage", False)
        self.next_page_button.setEnabled(has_next_page)
        self.prev_page_button.setEnabled(current_page > 1)
        
        # 更新窗口标题
        if self.current_star_id:
            # 获取演员名称
            star_name = ""
            for i in range(self.stars_list.count()):
                item = self.stars_list.item(i)
                if self.current_star_id in item.text():
                    star_name = item.text().split(" (")[0]
                    break
            if star_name:
                magnet_filter = "（仅含磁力）" if self.magnet_only_checkbox.isChecked() else ""
                self.setWindowTitle(f'JavBus简易版 - 演员: {star_name} {magnet_filter}')
        
        # 在方法最后添加对批量下载的支持
        # 检查是否处于批量下载模式
        if hasattr(self, 'batch_download_pages') and hasattr(self, 'batch_download_current_page_index') and not hasattr(self, 'batch_download_finished'):
            self.process_batch_download_page_loaded()

    def calculate_total_pages(self, pagination, current_page):
        """智能计算总页数"""
        # 默认至少有1页
        total_pages = 1
        
        # 从pages数组获取
        if "pages" in pagination and pagination["pages"]:
            pages = pagination["pages"]
            # 获取pages数组中的最大值
            max_page_in_array = max(pages)
            
            # 如果当前页小于6，直接使用最大值
            if current_page < 6:
                total_pages = max_page_in_array
            else:
                # 如果当前页大于等于6，使用pages数组中的最大值作为总页数
                # 这样可以避免总页数在浏览过程中出现先增加后减少的情况
                total_pages = max_page_in_array
        
        # 如果没有pages数组但有nextPage
        elif "nextPage" in pagination and pagination["nextPage"] is not None:
            if current_page < pagination["nextPage"]:
                total_pages = pagination["nextPage"]  # 至少有nextPage页
        
        # 如果current_page存在，总页数至少是current_page
        if current_page > total_pages:
            total_pages = current_page
        
        return total_pages
    
    def on_movies_load_error(self, error_msg):
        QMessageBox.critical(self, "错误", error_msg)
    
    def on_movies_load_finished(self):
        # 隐藏进度条
        self.progress_bar.setVisible(False)
    
    def load_next_page(self):
        """加载下一页结果"""
        # 清理批量下载状态，防止翻页时触发批量下载
        self.cleanup_batch_download_state()
        
        if self.current_star_id:
            # 演员查询模式
            self.current_page += 1
            self.load_star_movies(self.current_star_id, self.current_page)
        elif hasattr(self, 'current_movie_keyword') and self.current_movie_keyword:
            # 影片查询模式
            self.current_page += 1
            self.load_movie_search_results(self.current_movie_keyword, self.current_page)
    
    def load_prev_page(self):
        """加载上一页结果"""
        # 清理批量下载状态，防止翻页时触发批量下载
        self.cleanup_batch_download_state()
        
        if self.current_page > 1:
            self.current_page -= 1
            if self.current_star_id:
                # 演员查询模式
                self.load_star_movies(self.current_star_id, self.current_page)
            elif hasattr(self, 'current_movie_keyword') and self.current_movie_keyword:
                # 影片查询模式
                self.load_movie_search_results(self.current_movie_keyword, self.current_page)
    
    def show_prev_image(self):
        if self.current_images and self.current_image_index > 0:
            self.current_image_index -= 1
            self.display_current_image()
            
    def show_next_image(self):
        if self.current_images and self.current_image_index < len(self.current_images) - 1:
            self.current_image_index += 1
            self.display_current_image()
            
    def display_current_image(self):
        if not self.current_images:
            return
        
        image_path = self.current_images[self.current_image_index]
        pixmap = QPixmap(image_path)
        
        # 保持宽高比例缩放到固定区域
        scaled_pixmap = pixmap.scaled(600, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # 修改为600*400
        self.preview_label.setPixmap(scaled_pixmap)
        
        # 更新图片索引标签
        self.image_index_label.setText(f"{self.current_image_index + 1}/{len(self.current_images)}")
        
        # 更新按钮状态
        self.prev_image_button.setEnabled(self.current_image_index > 0)
        self.next_image_button.setEnabled(self.current_image_index < len(self.current_images) - 1)
    
    def on_summary_loaded(self, movie_id, summary):
        """处理异步加载的简介数据"""
        if movie_id == self.current_movie_id:  # 确保仍然是当前选中的影片
            self.summary_text.setText(f"简介: {summary if summary else '无简介信息'}")
            self.progress_bar.setValue(80)
            
            # 保存原始简介，以便在翻译后使用
            self.original_summary = summary
            
            # 检查是否所有异步任务都完成了
            if not hasattr(self, 'image_download_thread') or not self.image_download_thread.isRunning():
                self.progress_bar.setValue(100)
                self.progress_bar.setVisible(False)
                
    def on_summary_error(self, movie_id, error):
        """处理异步加载简介出错的情况"""
        if movie_id == self.current_movie_id:  # 确保仍然是当前选中的影片
            self.summary_text.setText(f"简介: 获取失败 ({error})")
            # 进度条继续，因为其他内容可能仍在加载
            self.progress_bar.setValue(80)
            
            # 检查是否所有异步任务都完成了
            if not hasattr(self, 'image_download_thread') or not self.image_download_thread.isRunning():
                self.progress_bar.setValue(100)
                self.progress_bar.setVisible(False)
    
    def on_translation_ready(self, movie_id, original_summary, translated_summary):
        """处理翻译完成的回调"""
        if movie_id == self.current_movie_id:  # 确保仍然是当前选中的影片
            # 显示原文和翻译
            print(f"GUI: 收到翻译结果，movie_id={movie_id}, 原文长度={len(original_summary)}, 翻译长度={len(translated_summary)}")
            combined_text = f"简介:\n\n【原文】\n{original_summary}\n\n【翻译】\n{translated_summary}"
            print(f"GUI: 设置文本区域，总长度={len(combined_text)}")
            
            # 确保QTextBrowser能够显示换行符
            self.summary_text.setPlainText(combined_text)
            
            # 自动调整高度以显示完整内容
            document_size = self.summary_text.document().size().toSize()
            # 最小100，最大300像素高度
            new_height = max(100, min(300, document_size.height() + 20))
            self.summary_text.setMaximumHeight(new_height)
            
            print(f"GUI: 显示翻译结果完成")
    
    def on_translation_error(self, movie_id, error_message):
        """处理翻译错误的回调"""
        if movie_id == self.current_movie_id:  # 确保仍然是当前选中的影片
            # 如果有原始简介，仍然显示，并附上翻译错误信息
            if hasattr(self, 'original_summary') and self.original_summary:
                self.summary_text.setText(f"简介: {self.original_summary}\n\n【翻译失败: {error_message}】")
            print(f"翻译错误: {error_message}")
                
    def on_images_download_complete(self):
        """处理图片下载完成的信号"""
        # 已有实现，但增加进度条更新
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
        
    def on_images_download_error(self, error_msg):
        """处理图片下载出错的情况"""
        print(f"图片下载错误: {error_msg}")
        # 即使图片下载失败，也不影响其他功能使用
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
    
    def display_magnets_from_movie_data(self, movie_data):
        """从影片数据中提取并显示磁力链接"""
        try:
            # 获取并显示磁力链接
            # 从影片详情中获取gid和uc参数
            gid = movie_data.get("gid", "")
            uc = movie_data.get("uc", "")
            movie_id = movie_data.get("id", "")
            
            if gid and uc:
                # 使用新的API获取磁力链接
                magnet_response = requests.get(f"{self.api_base_url}/magnets/{movie_id}", params={
                    "gid": gid,
                    "uc": uc,
                    "sortBy": "date",
                    "sortOrder": "desc"
                })
                
                if magnet_response.status_code == 200:
                    magnets_data = magnet_response.json()
                    # 修改这里：API返回的是直接的磁力链接数组，而不是包含magnets字段的对象
                    magnets = magnets_data if isinstance(magnets_data, list) else magnets_data.get("magnets", [])
                    
                    if magnets:
                        for magnet in magnets:
                            magnet_title = magnet.get("title", "")
                            magnet_link = magnet.get("link", "")
                            magnet_size = magnet.get("size", "")
                            # 兼容两种可能的日期字段名
                            magnet_date = magnet.get("shareDate", magnet.get("date", ""))
                            has_subtitle = magnet.get("hasSubtitle", False)
                            is_hd = magnet.get("isHD", False)
                            
                            # 创建列表项，添加更多信息和标记
                            subtitle_mark = "[中字]" if has_subtitle else ""
                            hd_mark = "[HD]" if is_hd else ""
                            item_text = f"{magnet_title} {subtitle_mark} {hd_mark} [{magnet_size}] ({magnet_date})"
                            item = QListWidgetItem(item_text)
                            item.setToolTip(magnet_link)  # 设置工具提示为完整链接
                            item.setData(Qt.UserRole, magnet_link)  # 存储链接数据
                            
                            # 设置不同类型的磁力链接的颜色
                            if has_subtitle:
                                item.setForeground(QColor(0, 128, 0))  # 绿色表示有字幕
                            elif is_hd:
                                item.setForeground(QColor(0, 0, 255))  # 蓝色表示高清
                            
                            self.magnet_list.addItem(item)
                        return
            
            # 如果没有gid和uc参数，或者API获取失败，使用旧的获取方式
            magnets = movie_data.get("magnets", [])
            if magnets:
                for magnet in magnets:
                    magnet_title = magnet.get("title", "")
                    magnet_link = magnet.get("link", "")
                    magnet_size = magnet.get("size", "")
                    # 兼容两种可能的日期字段名
                    magnet_date = magnet.get("shareDate", magnet.get("date", ""))
                    has_subtitle = magnet.get("hasSubtitle", False)
                    is_hd = magnet.get("isHD", False)
                    
                    # 创建列表项，添加更多信息和标记
                    subtitle_mark = "[中字]" if has_subtitle else ""
                    hd_mark = "[HD]" if is_hd else ""
                    item_text = f"{magnet_title} {subtitle_mark} {hd_mark} [{magnet_size}] ({magnet_date})"
                    item = QListWidgetItem(item_text)
                    item.setToolTip(magnet_link)  # 设置工具提示为完整链接
                    item.setData(Qt.UserRole, magnet_link)  # 存储链接数据
                    
                    # 设置不同类型的磁力链接的颜色
                    if has_subtitle:
                        item.setForeground(QColor(0, 128, 0))  # 绿色表示有字幕
                    elif is_hd:
                        item.setForeground(QColor(0, 0, 255))  # 蓝色表示高清
                    
                    self.magnet_list.addItem(item)
        except Exception as e:
            print(f"显示磁力链接失败: {str(e)}")
    
    def get_local_images(self, directory):
        """获取目录中的所有图片文件"""
        if not os.path.exists(directory):
            return []
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        images = []
        
        # 查找所有图片文件
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path) and os.path.getsize(file_path) > 0:
                ext = os.path.splitext(filename)[1].lower()
                if ext in image_extensions:
                    images.append(file_path)
        
        # 对图片进行排序：封面图放在第一位，其他按文件名排序
        cover_images = [img for img in images if os.path.basename(img).startswith('cover')]
        sample_images = [img for img in images if not os.path.basename(img).startswith('cover')]
        sample_images.sort(key=lambda x: os.path.basename(x))
        
        return cover_images + sample_images

    def refresh_star_data(self):
        """清除当前演员的数据库缓存并重新加载数据"""
        if not self.current_star_id:
            return
        
        # 显示确认对话框
        reply = QMessageBox.question(
            self, 
            "确认刷新", 
            f"确定要清除当前演员的缓存数据并重新加载吗？\n这将从API重新获取所有数据。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 设置为不确定模式
        
        try:
            # 清除数据库中的演员数据
            success, deleted_count = self.db.clear_star_data(self.current_star_id)
            
            if success:
                # 重置页码
                self.current_page = 1
                
                # 重新加载演员信息
                self.load_star_info(self.current_star_id)
                
                # 重新加载演员影片
                self.load_star_movies(self.current_star_id, self.current_page)
                
                # 清空上一次的影片演员信息
                self.stars_text.setText("演员: ")
                
                # 显示成功消息
                self.statusBar().showMessage(f"成功清除缓存并重新加载数据，删除了 {deleted_count} 条相关记录", 5000)
            else:
                QMessageBox.warning(self, "警告", "清除缓存数据失败")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"刷新数据时发生错误: {str(e)}")
        finally:
            self.progress_bar.setVisible(False)

    def on_magnet_selection_changed(self):
        """当磁力链接选择变化时更新按钮状态"""
        self.copy_magnet_button.setEnabled(len(self.magnet_list.selectedItems()) > 0)
    
    def copy_magnet_link(self, item):
        """双击磁力链接时复制到剪贴板"""
        magnet_link = item.data(Qt.UserRole)
        if magnet_link:
            try:
                pyperclip.copy(magnet_link)
                self.statusBar().showMessage(f"已复制磁力链接: {magnet_link[:30]}...", 3000)
            except Exception as e:
                QMessageBox.warning(self, "复制失败", f"无法复制到剪贴板: {str(e)}")
    
    def copy_selected_magnet(self):
        """复制选中的磁力链接"""
        selected_items = self.magnet_list.selectedItems()
        if selected_items:
            magnet_link = selected_items[0].data(Qt.UserRole)
            if magnet_link:
                try:
                    pyperclip.copy(magnet_link)
                    self.statusBar().showMessage(f"已复制磁力链接: {magnet_link[:30]}...", 3000)
                except Exception as e:
                    QMessageBox.warning(self, "复制失败", f"无法复制到剪贴板: {str(e)}")
    
    def show_magnet_context_menu(self, position):
        """显示磁力链接右键菜单"""
        menu = QMenu()
        copy_action = menu.addAction("复制磁力链接")
        
        # 获取点击位置的项目
        item = self.magnet_list.itemAt(position)
        if item:
            action = menu.exec_(QCursor.pos())
            if action == copy_action:
                magnet_link = item.data(Qt.UserRole)
                if magnet_link:
                    try:
                        pyperclip.copy(magnet_link)
                        self.statusBar().showMessage(f"已复制磁力链接: {magnet_link[:30]}...", 3000)
                    except Exception as e:
                        QMessageBox.warning(self, "复制失败", f"无法复制到剪贴板: {str(e)}")
    
    def search_movie_by_id(self):
        """通过影片编号搜索影片"""
        movie_id = self.movie_search_input.text().strip()
        if not movie_id:
            QMessageBox.warning(self, "警告", "请输入影片编号")
            return
        
        # 清理批量下载状态，防止搜索时触发批量下载
        self.cleanup_batch_download_state()
        
        # 保存搜索历史
        self.db.save_search_history(movie_id)
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 设置为不确定模式
        
        # 重置当前状态并设置为影片搜索模式
        self.current_star_id = None
        self.current_movie_keyword = movie_id  # 新增变量，保存当前搜索的影片关键字
        self.current_page = 1
        
        # 执行第一页搜索
        self.load_movie_search_results(movie_id, self.current_page)

    def load_movie_search_results(self, keyword, page):
        """加载影片搜索结果，支持分页"""
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 设置为不确定模式
        
        try:
            # 根据"只包含有磁力影片"选项的状态决定参数
            magnet_param = None if self.magnet_only_checkbox.isChecked() else "all"
            
            # 构建API请求参数
            params = {
                "keyword": keyword,
                "page": str(page)
            }
            
            # 只有当需要包含无磁力影片时才添加magnet参数
            if magnet_param:
                params["magnet"] = magnet_param
            
            # 从API获取数据
            response = requests.get(f"{self.api_base_url}/movies/search", params=params)
            
            if response.status_code != 200:
                QMessageBox.warning(self, "警告", f"搜索失败: {response.status_code}")
                self.progress_bar.setVisible(False)
                return
            
            data = response.json()
            movies = data.get("movies", [])
            pagination = data.get("pagination", {})
            
            if not movies and page == 1:  # 只在第一页没有结果时显示提示
                QMessageBox.information(self, "提示", "未找到匹配的影片")
                self.progress_bar.setVisible(False)
                return
            
            # 显示搜索结果
            self.display_movie_search_result(movies, pagination, keyword)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"搜索影片失败: {str(e)}")
        finally:
            self.progress_bar.setVisible(False)

    def display_movie_search_result(self, movies, pagination, keyword=None):
        """显示影片搜索结果，支持分页"""
        # 清空当前影片列表
        self.movies_table.setRowCount(0)
        
        # 按发行日期排序（新的在前）
        sorted_movies = sorted(movies, key=lambda x: x.get("date", ""), reverse=True)
        
        for movie in sorted_movies:
            row = self.movies_table.rowCount()
            self.movies_table.insertRow(row)
            
            # 设置影片编号
            movie_id = movie.get("id", "")
            self.movies_table.setItem(row, 0, QTableWidgetItem(movie_id))
            
            # 设置影片名称 - 去除与影片编号重复的部分
            title = movie.get("title", "")
            # 如果标题以影片编号开头，则去除这部分
            if movie_id and title.startswith(movie_id):
                title = title[len(movie_id):].strip()
            title_item = QTableWidgetItem(title)
            title_item.setToolTip(title)
            self.movies_table.setItem(row, 1, title_item)
            
            # 设置发行日期
            self.movies_table.setItem(row, 2, QTableWidgetItem(movie.get("date", "")))
        
        # 更新分页信息
        current_page = pagination.get("currentPage", self.current_page)
        
        # 使用同样的智能计算总页数
        total_pages = self.calculate_total_pages(pagination, current_page)
        
        # 更新页码显示
        self.page_label.setText(f"第{current_page}页/共{total_pages}页")
        
        has_next_page = pagination.get("hasNextPage", False)
        self.next_page_button.setEnabled(has_next_page)
        self.prev_page_button.setEnabled(current_page > 1)
        
        # 更新标题提示搜索模式
        if keyword:
            magnet_filter = "（仅含磁力）" if self.magnet_only_checkbox.isChecked() else ""
            self.setWindowTitle(f'JavBus简易版 - 影片搜索: {keyword} {magnet_filter}')
        
        # 在方法最后添加对批量下载的支持
        # 检查是否处于批量下载模式
        if hasattr(self, 'batch_download_pages') and hasattr(self, 'batch_download_current_page_index') and not hasattr(self, 'batch_download_finished'):
            self.process_batch_download_page_loaded()

    def process_batch_download_page_loaded(self):
        """处理批量下载页面加载完成后的操作"""
        # 获取当前页面的所有影片ID
        current_page_movies = []
        for row in range(self.movies_table.rowCount()):
            movie_id = self.movies_table.item(row, 0).text()
            if movie_id:
                current_page_movies.append(movie_id)
        
        # 添加到下载队列
        self.batch_download_movies.extend(current_page_movies)
        
        # 进入下一页
        self.batch_download_current_page_index += 1
        if self.batch_download_current_page_index < len(self.batch_download_pages):
            # 加载下一页
            next_page = self.batch_download_pages[self.batch_download_current_page_index]
            # 更新状态栏
            self.statusBar().showMessage(f"正在加载第{next_page}页影片列表...")
            # 切换到下一页
            self.current_page = next_page
            if self.current_star_id:
                # 演员查询模式
                self.load_star_movies(self.current_star_id, next_page)
            elif hasattr(self, 'current_movie_keyword') and self.current_movie_keyword:
                # 影片查询模式
                self.load_movie_search_results(self.current_movie_keyword, next_page)
        else:
            # 所有页面加载完毕，开始下载影片
            self.batch_movie_download_queue = self.batch_download_movies.copy()
            self.batch_movie_download_completed = 0
            self.batch_movie_download_errors = []
            self.batch_download_finished = False
            
            # 设置进度条
            self.progress_bar.setRange(0, len(self.batch_movie_download_queue))
            self.progress_bar.setValue(0)
            
            # 保存当前页码，以便下载完成后恢复
            self.batch_download_previous_page = self.current_page
            # 保存当前磁力过滤设置，以便下载完成后恢复
            self.batch_download_previous_magnet_only = self.magnet_only_checkbox.isChecked()
            
            # 开始下载
            QTimer.singleShot(0, self.download_next_movie)

    def handle_text_click(self, event, text_browser):
        """处理文本点击事件"""
        if event.type() == QEvent.MouseButtonDblClick:
            # 获取所选文本，如果没有选择则获取所有文本
            cursor = text_browser.textCursor()
            selected_text = cursor.selectedText()
            
            if not selected_text:
                # 如果没有选择文本，则获取标签后的内容
                full_text = text_browser.toPlainText()
                label_parts = full_text.split(": ", 1)
                if len(label_parts) > 1:
                    selected_text = label_parts[1]
            
            # 提取单个条目（如果点击的是逗号分隔的列表）
            if "," in selected_text:
                # 检查是否在特定的逗号附近点击
                cursor_pos = text_browser.cursorForPosition(event.pos())
                cursor_pos.select(QTextCursor.WordUnderCursor)
                word_under_cursor = cursor_pos.selectedText()
                
                if word_under_cursor and not word_under_cursor.isspace():
                    selected_text = word_under_cursor
                else:
                    # 如果点击位置不是文字，使用整个选择
                    pass
            
            # 设置搜索输入框并执行搜索
            if selected_text and not selected_text.isspace():
                self.movie_search_input.setText(selected_text.strip())
                self.search_movie_by_id()
                
        # 继承默认处理方法
        QTextBrowser.mousePressEvent(text_browser, event)

    def on_image_downloaded(self, image_path, image_type):
        """当图片下载完成时被调用"""
        if image_type == "cover" and not self.current_images:
            # 如果是封面且当前没有显示图片，则立即显示
            self.current_images = [image_path]
            self.current_image_index = 0
            self.display_current_image()
        else:
            # 将新图片添加到列表中
            if image_path not in self.current_images:
                self.current_images.append(image_path)
                # 更新图片计数
                self.image_index_label.setText(f"{self.current_image_index + 1}/{len(self.current_images)}")
                self.next_image_button.setEnabled(self.current_image_index < len(self.current_images) - 1)
        
        # 显示下载进度状态
        self.statusBar().showMessage(f"已下载 {len(self.current_images)} 张图片", 2000)

    def on_images_download_complete(self):
        """当所有图片下载完成时被调用"""
        # 隐藏进度条
        self.progress_bar.setVisible(False)
        
        # 显示完成消息
        self.statusBar().showMessage(f"图片下载完成，共 {len(self.current_images)} 张", 3000)

    def on_images_download_error(self, error_msg):
        """当图片下载出错时被调用"""
        # 隐藏进度条
        self.progress_bar.setVisible(False)
        
        # 显示错误消息
        self.statusBar().showMessage(error_msg, 5000)
        print(error_msg)

    def start_batch_download(self):
        """开始批量下载页面内影片图片"""
        # 检查当前是否有查询结果
        if self.movies_table.rowCount() == 0:
            QMessageBox.warning(self, "警告", "当前没有影片可下载")
            return
        
        # 获取当前页和总页数
        current_page_text = self.page_label.text()
        try:
            # 从 "第X页/共Y页" 中提取X和Y
            parts = current_page_text.split("/")
            current_page = int(parts[0].replace("第", "").replace("页", ""))
            total_pages = int(parts[1].replace("共", "").replace("页", ""))
        except Exception:
            QMessageBox.warning(self, "警告", "无法解析当前页面信息")
            return
        
        # 解析前X页输入
        try:
            prev_pages = int(self.prev_pages_input.text()) if self.prev_pages_input.text() else 1
            # 调整前X页的数量，不能超过当前页数
            prev_pages = min(prev_pages, current_page - 1) if prev_pages > 0 else 0
        except ValueError:
            prev_pages = 0  # 如果输入无效，则默认不下载前面的页
        
        # 解析后X页输入
        try:
            next_pages = int(self.next_pages_input.text()) if self.next_pages_input.text() else 1
            # 调整后X页的数量，不能超过剩余页数，且不能超过5
            remaining_pages = total_pages - current_page
            next_pages = min(next_pages, remaining_pages, 5) if next_pages > 0 else 0
        except ValueError:
            next_pages = 0  # 如果输入无效，则默认不下载后面的页
        
        # 计算需要下载的页面范围
        start_page = current_page - prev_pages
        end_page = current_page + next_pages
        
        # 确认对话框
        msg = f"将下载第{start_page}页到第{end_page}页的所有影片图片，共{end_page - start_page + 1}页。\n"
        msg += "下载过程可能需要较长时间，确定继续吗？"
        reply = QMessageBox.question(self, "确认下载", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply != QMessageBox.Yes:
            return
        
        # 初始化批量下载相关的属性
        self.batch_download_pages = list(range(start_page, end_page + 1))
        self.batch_download_current_page_index = 0
        self.batch_download_movies = []
        self.batch_movie_download_queue = []  # 初始化下载队列
        self.batch_movie_download_completed = 0  # 初始化完成计数
        self.batch_movie_download_errors = []  # 初始化错误列表
        self.batch_download_finished = False  # 初始化完成标志
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定模式
        
        # 获取当前页面的所有影片ID
        current_page_movies = []
        for row in range(self.movies_table.rowCount()):
            movie_id = self.movies_table.item(row, 0).text()
            if movie_id:
                current_page_movies.append(movie_id)
        
        # 将当前页面的影片添加到下载队列
        self.batch_movie_download_queue = current_page_movies
        
        # 设置进度条的最大值
        self.progress_bar.setRange(0, len(current_page_movies))
        self.progress_bar.setValue(0)
        
        # 开始下载第一个影片
        self.download_next_movie()

    def download_next_movie(self):
        """从队列中下载下一个影片的图片"""
        try:
            # 检查是否所有影片都已经下载完成，并且没有显示过完成提示
            if not self.batch_movie_download_queue and not self.batch_download_finished:
                # 设置完成标志
                self.batch_download_finished = True
                
                # 下载完成
                self.progress_bar.setVisible(False)
                
                # 清除状态栏消息
                self.statusBar().clearMessage()
                
                # 显示下载结果
                errors_count = len(self.batch_movie_download_errors)
                if errors_count > 0:
                    error_msg = "\n".join(self.batch_movie_download_errors[:10])
                    if errors_count > 10:
                        error_msg += f"\n... 及其他 {errors_count - 10} 个错误"
                    
                    QMessageBox.warning(self, "下载完成",
                                       f"已完成 {self.batch_movie_download_completed} 个影片的图片下载，"
                                       f"但有 {errors_count} 个影片下载失败。\n\n"
                                       f"错误信息:\n{error_msg}")
                else:
                    QMessageBox.information(self, "下载完成",
                                          f"已成功下载 {self.batch_movie_download_completed} 个影片的图片。")
                
                # 清理批量下载相关的状态，防止重复触发批量下载
                self.cleanup_batch_download_state()
                
                # 恢复之前的页面和设置
                if hasattr(self, 'batch_download_previous_page'):
                    # 恢复之前的查询页面
                    previous_page = self.batch_download_previous_page
                    self.current_page = previous_page
                    
                    # 恢复之前的磁力过滤设置
                    if hasattr(self, 'batch_download_previous_magnet_only'):
                        self.magnet_only_checkbox.setChecked(self.batch_download_previous_magnet_only)
                    
                    # 重新加载对应页面的数据
                    if self.current_star_id:
                        self.load_star_movies(self.current_star_id, previous_page)
                    elif hasattr(self, 'current_movie_keyword') and self.current_movie_keyword:
                        self.load_movie_search_results(self.current_movie_keyword, previous_page)
                
                return
            elif not self.batch_movie_download_queue:
                # 如果队列为空但已经显示过完成提示，直接返回
                return
            
            # 获取下一个要下载的影片ID
            movie_id = self.batch_movie_download_queue.pop(0)
            
            # 更新状态栏
            self.statusBar().showMessage(f"正在处理影片 {movie_id} 的图片...")
            
            # 创建保存目录
            save_dir = os.path.join("buspic", movie_id)
            os.makedirs(save_dir, exist_ok=True)
            
            # 检查本地是否已有图片
            local_images = self.get_local_images(save_dir)
            if local_images:
                # 已有本地图片，更新计数并继续下一个
                self.batch_movie_download_completed += 1
                self.progress_bar.setValue(self.batch_movie_download_completed)
                # 使用 QTimer 延迟调用下一个下载，避免递归
                QTimer.singleShot(0, self.download_next_movie)
                return
            
            # 获取影片详情
            movie_data = self.db.get_movie(movie_id)
            
            # 如果数据库中没有，则从API获取
            if not movie_data:
                response = requests.get(f"{self.api_base_url}/movies/{movie_id}")
                
                if response.status_code != 200:
                    # 记录错误
                    self.batch_movie_download_errors.append(f"{movie_id}: 获取影片详情失败 ({response.status_code})")
                    # 更新计数
                    self.batch_movie_download_completed += 1
                    self.progress_bar.setValue(self.batch_movie_download_completed)
                    # 使用 QTimer 延迟调用下一个下载，避免递归
                    QTimer.singleShot(0, self.download_next_movie)
                    return
                
                movie_data = response.json()
                # 保存到数据库
                self.db.save_movie(movie_data)
            
            # 创建批量下载线程
            self.batch_image_download_thread = ImageDownloadThread(movie_id, self.api_base_url, movie_data, save_dir)
            self.batch_image_download_thread.download_complete.connect(self.on_batch_image_download_complete)
            self.batch_image_download_thread.download_error.connect(self.on_batch_image_download_error)
            self.batch_image_download_thread.start()
            
        except Exception as e:
            # 记录错误
            self.batch_movie_download_errors.append(f"{movie_id}: {str(e)}")
            # 更新计数
            self.batch_movie_download_completed += 1
            self.progress_bar.setValue(self.batch_movie_download_completed)
            # 使用 QTimer 延迟调用下一个下载，避免递归
            QTimer.singleShot(0, self.download_next_movie)

    def on_batch_image_download_complete(self):
        """批量下载某个影片图片完成的回调"""
        # 更新计数器
        self.batch_movie_download_completed += 1
        self.progress_bar.setValue(self.batch_movie_download_completed)
        
        # 继续下载下一个
        self.download_next_movie()

    def on_batch_image_download_error(self, error_msg):
        """批量下载某个影片图片出错的回调"""
        # 记录错误
        self.batch_movie_download_errors.append(error_msg)
        
        # 更新计数器
        self.batch_movie_download_completed += 1
        self.progress_bar.setValue(self.batch_movie_download_completed)
        
        # 继续下载下一个
        self.download_next_movie()

    def cleanup_batch_download_state(self):
        """清理批量下载的状态变量"""
        if hasattr(self, 'batch_download_pages'):
            delattr(self, 'batch_download_pages')
        if hasattr(self, 'batch_download_current_page_index'):
            delattr(self, 'batch_download_current_page_index')
        if hasattr(self, 'batch_download_movies'):
            delattr(self, 'batch_download_movies')
        if hasattr(self, 'batch_movie_download_queue'):
            delattr(self, 'batch_movie_download_queue')
        if hasattr(self, 'batch_download_finished'):
            delattr(self, 'batch_download_finished')
        # 不删除batch_download_previous_page，因为它可能在后面还需要用到
        # 不删除batch_download_previous_magnet_only，因为它可能在后面还需要用到

    # 添加播放视频的功能
    def play_selected_video(self):
        if not hasattr(self, 'current_movie_id') or not self.current_movie_id:
            QMessageBox.warning(self, "警告", "请先选择要播放的影片")
            return
        
        movie_id = self.current_movie_id
        
        # 动态导入video_player2模块
        video_player = import_video_player()
        if not video_player:
            return
        
        try:
            # 构建观看URL，使用配置的前缀
            watch_url = f"{self.watch_url_prefix}/{movie_id}"
            
            # 使用线程启动播放器，避免阻塞主GUI
            def start_player():
                try:
                    # 创建Tkinter根窗口
                    root = tk.Tk()
                    root.withdraw()  # 暂时隐藏，由VideoPlayerGUI来显示
                    
                    # 创建HTTP客户端
                    http_client = video_player.HttpClient()
                    
                    # 直接创建播放器GUI
                    try:
                        app = video_player.VideoPlayerGUI(root)
                        
                        # 设置URL
                        app.url_entry.insert(0, watch_url)
                        
                        # 显示窗口并进入主循环
                        # 通过捕获异常来处理可能的tkinter线程问题
                        try:
                            root.deiconify()
                            # 保持所有tkinter操作在同一线程内
                            root.mainloop()
                        except Exception as e:
                            print(f"Tkinter main loop error: {str(e)}")
                        finally:
                            # 确保在主线程完成后正确清理tkinter资源
                            try:
                                # 销毁所有窗口小部件
                                for widget in root.winfo_children():
                                    widget.destroy()
                                # 在退出前停止所有挂起的事件和回调
                                root.after_cancel("all")
                                # 退出mainloop (如果还在运行)
                                if root.winfo_exists():
                                    root.quit()
                                # 销毁根窗口
                                root.destroy()
                                # 显式地删除引用，帮助垃圾回收
                                del app
                            except Exception as cleanup_error:
                                print(f"Tkinter cleanup error: {str(cleanup_error)}")
                    except Exception as e:
                        messagebox.showerror("错误", f"播放器初始化失败: {str(e)}")
                        if root.winfo_exists():
                            root.destroy()
                except Exception as e:
                    QMessageBox.critical(None, "错误", f"播放器启动失败: {str(e)}")
            
            # 将tkinter的部分完全隔离在一个单独的线程中
            player_thread = threading.Thread(target=start_player, daemon=True)
            player_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法启动播放器: {str(e)}")

    def _cleanup_threads(self):
        """清理所有正在运行的异步线程"""
        # 清理简介线程
        if hasattr(self, 'summary_thread') and self.summary_thread.isRunning():
            self.summary_thread.quit()
            self.summary_thread.wait(1000)  # 最多等待1秒
            
        # 清理图片下载线程
        if hasattr(self, 'image_download_thread') and self.image_download_thread.isRunning():
            # 图片下载线程可能需要更多时间来完成
            self.image_download_thread.quit()
            self.image_download_thread.wait(1000)  # 最多等待1秒
            
    def on_title_translation_ready(self, movie_id, translated_title):
        """处理标题翻译完成的回调"""
        if movie_id == self.current_movie_id:  # 确保仍然是当前选中的影片
            # 获取当前标题
            current_title_text = self.title_text.toPlainText()
            # 添加翻译标题
            if "片名:" in current_title_text:
                updated_title = f"片名: {current_title_text.replace('片名: ', '')}（{translated_title}）"
                self.title_text.setText(updated_title)

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序图标
    icon_path = "fb.ico"
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = JavbusGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 