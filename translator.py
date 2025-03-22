import json
import os
import requests
from PyQt5.QtCore import QObject, pyqtSignal

# 配置文件路径，与主应用保持一致
CONFIG_FILE = "config.json"

class Translator(QObject):
    """用于翻译文本的类"""
    translation_ready = pyqtSignal(str, str, str)  # 参数：(movie_id, original_text, translated_text)
    translation_error = pyqtSignal(str, str)  # 参数：(movie_id, error_message)
    
    def __init__(self):
        super().__init__()
        # 加载配置
        self.load_config()
    
    def load_config(self):
        """从配置文件加载翻译相关设置"""
        self.api_url = "https://api.openai.com/v1/chat/completions"  # 默认OpenAI API URL
        self.source_lang = "日语"  # 默认源语言
        self.target_lang = "中文"  # 默认目标语言
        self.api_token = ""  # API Token
        self.model = "gpt-3.5-turbo"  # 默认模型
        
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 从配置文件中获取翻译相关设置
                    translation_config = config.get("translation", {})
                    self.api_url = translation_config.get("api_url", self.api_url)
                    self.source_lang = translation_config.get("source_lang", self.source_lang)
                    self.target_lang = translation_config.get("target_lang", self.target_lang)
                    self.api_token = translation_config.get("api_token", self.api_token)
                    self.model = translation_config.get("model", self.model)
                    print(f"已加载翻译配置")
        except Exception as e:
            print(f"加载翻译配置失败: {str(e)}")
    
    def save_config(self, api_url, source_lang, target_lang, api_token, model):
        """保存翻译配置到配置文件"""
        try:
            # 更新当前实例的配置
            self.api_url = api_url
            self.source_lang = source_lang
            self.target_lang = target_lang
            self.api_token = api_token
            self.model = model
            
            # 读取现有配置
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            # 更新配置
            if "translation" not in config:
                config["translation"] = {}
                
            config["translation"]["api_url"] = api_url
            config["translation"]["source_lang"] = source_lang
            config["translation"]["target_lang"] = target_lang
            config["translation"]["api_token"] = api_token
            config["translation"]["model"] = model
            
            # 保存配置
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
                print(f"已保存翻译配置到: {CONFIG_FILE}")
            return True
        except Exception as e:
            print(f"保存翻译配置失败: {str(e)}")
            return False
    
    def get_ollama_models(self, api_url="http://localhost:11434", api_token=""):
        """
        获取Ollama可用的模型列表
        
        Args:
            api_url (str): Ollama API URL
            api_token (str): API令牌(Ollama通常不需要)
            
        Returns:
            list: 可用模型列表
        """
        try:
            # 从API URL中提取基础URL
            base_url = api_url
            if "/api" in api_url:
                base_url = api_url.split("/api")[0]
            if not base_url.endswith("/"):
                base_url += "/"
            
            # 构建获取模型列表的URL
            models_url = f"{base_url}api/tags"
            
            # 准备请求头
            headers = {"Content-Type": "application/json"}
            if api_token:
                headers["Authorization"] = f"Bearer {api_token}"
            
            print(f"正在从{models_url}获取Ollama模型列表")
            
            # 发送请求
            response = requests.get(
                models_url,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"Ollama API响应: {result}")
                
                if "models" in result:
                    # 提取模型名称
                    models = [model["name"] for model in result["models"]]
                    return models
                else:
                    print("未找到模型列表")
                    return []
            else:
                print(f"获取Ollama模型列表失败: HTTP {response.status_code}")
                return []
        except Exception as e:
            print(f"获取Ollama模型列表出错: {str(e)}")
            return []
    
    def translate(self, movie_id, text):
        """翻译文本
        
        Args:
            movie_id (str): 当前影片ID
            text (str): 要翻译的文本
            
        Returns:
            None: 翻译结果通过信号发送
        """
        if not text or not text.strip():
            self.translation_ready.emit(movie_id, text, "")
            return
            
        # 检查API Token - 本地Ollama可以不需要token
        is_ollama = "localhost:11434" in self.api_url or "127.0.0.1:11434" in self.api_url
        if not self.api_token and not is_ollama:
            self.translation_error.emit(movie_id, "翻译API Token未设置，请在设置中配置")
            return
            
        try:
            # 准备请求头
            headers = {
                "Content-Type": "application/json"
            }
            
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"
            
            # 准备请求数据
            prompt = f"将以下{self.source_lang}文本翻译成{self.target_lang}，只返回翻译结果，不要解释：\n\n{text}"
            
            # 根据API类型构建不同的请求负载和URL
            api_url = self.api_url
            
            if is_ollama:
                # Ollama API - 使用generate接口
                ollama_url = self.api_url
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
                
                api_url = ollama_url
                print(f"使用Ollama生成API: {ollama_url}")
                
                # Ollama格式
                payload = {
                    "model": self.model,
                    "prompt": f"你是一个专业的{self.source_lang}到{self.target_lang}翻译器。\n{prompt}",
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9
                    }
                }
                
            elif "siliconflow.cn" in self.api_url:
                # SiliconFlow API格式
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": f"你是一个专业的{self.source_lang}到{self.target_lang}翻译器。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "stream": False,
                    "max_tokens": 1024,
                    "top_p": 0.7,
                    "top_k": 50,
                    "response_format": {"type": "text"}
                }
            else:
                # 标准OpenAI兼容格式
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": f"你是一个专业的{self.source_lang}到{self.target_lang}翻译器。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3
                }
            
            print(f"使用API: {api_url}, 模型: {self.model}")
            print(f"请求头: {headers}")
            print(f"请求数据: {payload}")
            
            # 发送请求
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            # 解析响应
            if response.status_code == 200:
                result = response.json()
                print(f"API响应: {result}")
                
                # 尝试从不同格式的响应中提取翻译文本
                translated_text = ""
                
                # Ollama API格式
                if is_ollama:
                    if "response" in result:
                        translated_text = result["response"].strip()
                    elif "message" in result and isinstance(result["message"], dict):
                        if "content" in result["message"] and result["message"]["content"]:
                            translated_text = result["message"]["content"].strip()
                    
                    # 如果响应为空但done_reason为load，表示模型正在加载
                    if not translated_text and "done_reason" in result and result["done_reason"] == "load":
                        error_msg = "模型正在加载中，请稍后重试"
                        print(f"错误: {error_msg}")
                        self.translation_error.emit(movie_id, error_msg)
                        return
                
                # 标准OpenAI格式
                elif "choices" in result and len(result["choices"]) > 0:
                    choice = result["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        translated_text = choice["message"]["content"].strip()
                    # SiliconFlow可能在message中包含reasoning_content
                    elif "message" in choice and "reasoning_content" in choice["message"]:
                        reasoning = choice["message"]["reasoning_content"]
                        print(f"找到reasoning_content: {reasoning[:100]}...")
                        # 从reasoning_content中尝试提取最终结果
                        # 通常最终结果会在最后一部分或包含特定模式
                        lines = reasoning.strip().split('\n')
                        # 尝试查找引号中的中文内容作为翻译结果
                        import re
                        # 简化正则表达式，查找包含中文的短语
                        chinese_patterns = [
                            r'"([^"]*[\u4e00-\u9fa5]+[^"]*)"',  # 双引号中包含中文的内容
                            r"'([^']*[\u4e00-\u9fa5]+[^']*)'",  # 单引号中包含中文的内容
                        ]
                        
                        for pattern in chinese_patterns:
                            matches = re.findall(pattern, reasoning)
                            if matches:
                                # 取最后一个匹配项作为可能的翻译结果
                                print(f"从reasoning中找到可能的翻译: {matches[-1]}")
                                translated_text = matches[-1]
                                break
                                
                        # 如果上面的方法没找到结果，尝试取最后几行非空文本
                        if not translated_text:
                            non_empty_lines = [line.strip() for line in lines if line.strip()]
                            if non_empty_lines:
                                # 取最后几行并检查哪一行包含中文
                                last_lines = non_empty_lines[-5:] if len(non_empty_lines) > 5 else non_empty_lines
                                for line in reversed(last_lines):
                                    if re.search(r'[\u4e00-\u9fa5]', line):  # 包含中文字符
                                        print(f"从reasoning最后几行找到可能的翻译: {line}")
                                        translated_text = line
                                        break
                    elif "text" in choice:  # 某些API可能直接使用text字段
                        translated_text = choice["text"].strip()
                
                if translated_text:
                    self.translation_ready.emit(movie_id, text, translated_text)
                else:
                    error_msg = "无法从API响应中提取翻译文本"
                    print(f"错误: {error_msg}, 响应: {result}")
                    self.translation_error.emit(movie_id, error_msg)
            else:
                error_msg = f"翻译请求失败: HTTP {response.status_code}"
                try:
                    error_details = response.json()
                    error_msg_details = ""
                    if "error" in error_details:
                        if isinstance(error_details["error"], dict):
                            error_msg_details = error_details["error"].get("message", "")
                        else:
                            error_msg_details = str(error_details["error"])
                    
                    if error_msg_details:
                        error_msg += f" - {error_msg_details}"
                    
                    print(f"错误响应详情: {error_details}")
                except Exception as json_err:
                    print(f"解析错误响应失败: {str(json_err)}, 原始响应: {response.text[:200]}")
                
                self.translation_error.emit(movie_id, error_msg)
                
        except Exception as e:
            print(f"翻译过程出错: {str(e)}")
            self.translation_error.emit(movie_id, f"翻译过程出错: {str(e)}")

# 工厂函数，用于获取共享的翻译器实例
_translator_instance = None
def get_translator():
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = Translator()
    return _translator_instance