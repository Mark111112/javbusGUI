import re
import json
import requests
import os
from bs4 import BeautifulSoup
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 配置文件路径
CONFIG_FILE = "config.json"

class FanzaScraper:
    def __init__(self):
        self.base_url = "https://www.dmm.co.jp/"
        # FANZA使用的几种不同URL模板
        self.url_templates = [
            "https://www.dmm.co.jp/mono/dvd/-/detail/=/cid={}/",
            "https://www.dmm.co.jp/digital/videoa/-/detail/=/cid={}/",
            "https://www.dmm.co.jp/digital/videoc/-/detail/=/cid={}/",
            "https://www.dmm.co.jp/digital/anime/-/detail/=/cid={}/",
            "https://www.dmm.co.jp/mono/anime/-/detail/=/cid={}/",
            "https://www.dmm.co.jp/digital/nikkatsu/-/detail/=/cid={}/"
        ]
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        # FANZA需要的cookie
        self.cookies = {'age_check_done': '1'}
        
        # 从配置文件加载前缀映射规则
        self.prefix_mappings = self.load_mappings_from_file()
        
    def load_mappings_from_file(self):
        """从配置文件加载映射关系"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 从整合的配置文件中获取fanza_mappings字段
                    mappings = config.get("fanza_mappings", {})
                    logging.info(f"已从配置文件加载 {len(mappings)} 条番号映射")
                    return mappings
            elif os.path.exists('fanza_mappings.json'):
                # 兼容旧版本，如果有老的fanza_mappings.json文件
                with open('fanza_mappings.json', 'r', encoding='utf-8') as f:
                    mappings = json.load(f)
                    logging.info(f"从旧版映射文件加载 {len(mappings)} 条番号映射，将迁移到新配置文件")
                    # 迁移到新的配置文件
                    self.set_mappings(mappings)
                    return mappings
            else:
                # 如果配置文件不存在，使用默认的映射规则
                logging.warning("映射配置文件不存在，使用默认映射")
                return {}
        except Exception as e:
            logging.error(f"加载映射关系失败: {str(e)}")
            return {}
    
    def get_mappings(self):
        """获取所有番号映射关系"""
        return self.prefix_mappings
    
    def set_mappings(self, mappings):
        """设置番号映射关系并保存到配置文件"""
        self.prefix_mappings = mappings
        
        try:
            # 读取现有配置
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            # 按字母顺序排序映射
            sorted_mappings = {k: mappings[k] for k in sorted(mappings, key=str.lower)}
            
            # 更新配置
            config["fanza_mappings"] = sorted_mappings
            
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            logging.info(f"映射关系已保存到 {CONFIG_FILE}")
            return True
        except Exception as e:
            logging.error(f"保存映射关系失败: {str(e)}")
            return False
    
    # 保持兼容性的方法
    def save_mappings(self, mappings):
        """保存番号映射关系到配置文件"""
        return self.set_mappings(mappings)
    
    def normalize_movie_id(self, movie_id):
        """将电影ID标准化为FANZA使用的格式"""
        # 将ID转为小写
        id_lower = movie_id.lower()
        
        # 移除非字母数字字符(如连字符)
        cleaned_id = re.sub(r'[^a-z0-9]', '', id_lower)
        
        # 从ID中提取前缀和数字部分
        match = re.match(r'^([a-z]+)(\d+)$', cleaned_id)
        if match:
            prefix = match.group(1)
            number = match.group(2)
            
            # 检查是否有已知的前缀映射
            if prefix in self.prefix_mappings:
                # 使用映射的前缀
                mapped_prefix = self.prefix_mappings[prefix]
                
                # 保持映射前缀的大小写
                # 处理不同的模式
                if '00' in mapped_prefix:
                    # 如果映射前缀已包含00，直接使用数字
                    return f"{mapped_prefix}{number.zfill(3)}"
                elif re.match(r'^\d+[a-zA-Z]+$', mapped_prefix):
                    # 如果是数字+字母格式(如118abp)，添加00
                    return f"{mapped_prefix}00{number.zfill(3)}"
                else:
                    # 其他情况(如h_068mxgs)，直接附加数字
                    return f"{mapped_prefix}{number}"
            
            # 对于没有映射的普通编号，使用默认格式
            formatted_number = number.zfill(3)
            return f"{prefix}00{formatted_number}"
        
        # 如果已经符合FANZA格式，直接返回
        if re.search(r'(?:\d+[a-z]+\d+|[a-z]_\d+[a-z]+\d+)', cleaned_id):
            return cleaned_id
        
        # 尝试处理可能带有前缀数字的格式
        match = re.match(r'^(\d+)?([a-z]+)(\d+)(.+)?$', cleaned_id)
        if match:
            prefix_num = match.group(1) or ""
            prefix = match.group(2)
            number = match.group(3)
            suffix = match.group(4) or ""
            
            # 如果数字已包含00，保持原样
            if "00" in cleaned_id:
                return cleaned_id
            
            # 确保数字部分至少为3位数，不足补0
            formatted_number = number.zfill(3)
            return f"{prefix_num}{prefix}00{formatted_number}{suffix}"
        
        # 如果无法匹配任何已知模式，返回原始ID（小写）
        return id_lower
    
    def get_urls_by_id(self, movie_id):
        """返回所有可能的URL"""
        movie_id = self.normalize_movie_id(movie_id)
        urls = [template.format(movie_id) for template in self.url_templates]
        
        # 如果ID符合特定模式，优先尝试digital videoa URL
        if re.match(r'(?i)[a-z]+00\d{3,}', movie_id):
            urls[0], urls[1] = urls[1], urls[0]
        
        return urls
    
    def get_summary_from_json_ld(self, soup):
        """从JSON-LD脚本标签中提取摘要"""
        script_tag = soup.find('script', {'type': 'application/ld+json'})
        if not script_tag:
            return None
        
        try:
            data = json.loads(script_tag.string)
            if 'description' in data:
                return data['description']
        except (json.JSONDecodeError, AttributeError) as e:
            logging.warning(f"无法解析JSON-LD: {e}")
        
        return None
    
    def get_summary_from_html(self, soup):
        """从HTML内容中提取摘要"""
        # 尝试从class为"mg-b20 lh4"的div中提取
        summary_div = soup.select_one('div.mg-b20.lh4')
        if summary_div:
            # 先尝试从p.mg-b20获取
            p_tag = summary_div.select_one('p.mg-b20')
            if p_tag and p_tag.text.strip():
                return p_tag.text.strip()
            
            # 再尝试从任何p标签获取
            any_p = summary_div.select_one('p')
            if any_p and any_p.text.strip():
                return any_p.text.strip()
            
            # 最后获取整个div的文本
            if summary_div.text.strip():
                return summary_div.text.strip()
        
        return None
    
    def get_summary_from_meta(self, soup):
        """从meta标签中提取摘要"""
        meta_tag = soup.find('meta', {'property': 'og:description'})
        if meta_tag and 'content' in meta_tag.attrs:
            return meta_tag['content']
        
        return None
    
    def get_movie_summary(self, movie_id):
        """获取电影摘要信息"""
        normalized_id = self.normalize_movie_id(movie_id)
        logging.info(f"影片编号 {movie_id} 已被标准化为 {normalized_id}")
        urls = self.get_urls_by_id(movie_id)
        
        for url in urls:
            logging.info(f"尝试URL: {url}")
            try:
                response = requests.get(
                    url, 
                    headers=self.headers, 
                    cookies=self.cookies,
                    timeout=10
                )
                
                if not response.ok:
                    logging.warning(f"请求失败: {response.status_code}")
                    continue
                
                # 检查是否地区限制
                if "not-available-in-your-region" in response.url:
                    logging.warning("该地区不可用")
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 按优先级尝试不同的摘要获取方法
                summary = self.get_summary_from_json_ld(soup)
                if summary:
                    logging.info("从JSON-LD获取摘要")
                    return {
                        "movie_id": movie_id,
                        "fanza_id": normalized_id,
                        "url": url,
                        "summary": summary,
                        "source": "json-ld"
                    }
                
                summary = self.get_summary_from_html(soup)
                if summary:
                    logging.info("从HTML内容获取摘要")
                    return {
                        "movie_id": movie_id,
                        "fanza_id": normalized_id,
                        "url": url,
                        "summary": summary,
                        "source": "html"
                    }
                
                summary = self.get_summary_from_meta(soup)
                if summary:
                    logging.info("从Meta标签获取摘要")
                    return {
                        "movie_id": movie_id,
                        "fanza_id": normalized_id,
                        "url": url,
                        "summary": summary,
                        "source": "meta"
                    }
                
                logging.warning("在页面中找不到摘要信息")
                
            except Exception as e:
                logging.error(f"请求出错: {str(e)}")
        
        return {"movie_id": movie_id, "fanza_id": normalized_id, "error": "找不到电影信息或摘要"}

# 使用示例
def main():
    movie_id = input("请输入电影编号: ")
    scraper = FanzaScraper()
    result = scraper.get_movie_summary(movie_id)
    
    print("\n结果:")
    if "error" in result:
        print(f"错误: {result['error']}")
    else:
        print(f"电影ID: {result['movie_id']}")
        print(f"FANZA ID: {result['fanza_id']}")
        print(f"网址: {result['url']}")
        print(f"数据来源: {result['source']}")
        print(f"摘要: {result['summary']}")

if __name__ == "__main__":
    main() 