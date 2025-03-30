#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import requests
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from javbus_db import JavbusDatabase
from translator import get_translator
import logging
import traceback
import movieinfo  # Import the movieinfo module

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Flask application
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)  # Enable CORS

# Configuration file path
CONFIG_FILE = "config/config.json"
DB_FILE = "data/javbus.db"

# Directory setup
os.makedirs("data", exist_ok=True)
os.makedirs("buspic/covers", exist_ok=True)
os.makedirs("buspic/actor", exist_ok=True)

# Initialize database
db = JavbusDatabase(db_file=DB_FILE)

# Initialize translator
translator = get_translator()

# Create a FanzaScraper instance
fanza_scraper = movieinfo.FanzaScraper()

# Load configuration
def load_config():
    """Load configuration file"""
    config = {
        "api_url": "http://192.168.1.246:8922/api",
        "watch_url_prefix": "https://missav.ai",
        "fanza_mappings": {
            "abf": "118abf",
            "abp": "118abp",
            "atom": "1atom",
            "bazx": "7bazx",
            "bdd": "1BDD",
            "dandy": "1Dandy",
            "dph": "33dph",
            "dphn": "33dphn",
            "fcp": "h_001fcp",
            "fsdss": "1fsdss",
            "fset": "1FSET",
            "gar": "1GAR",
            "gesu": "49gesu",
            "glod": "196glod",
            "gvg": "13gvg",
            "gvh": "13gvh",
            "hbad": "1HBAD",
            "hunt": "1HUNT",
            "hvad": "1HVAD",
            "ibw": "504ibw",
            "idol": "1IDOL",
            "iene": "1IENE",
            "iesp": "1IESP",
            "ksd": "5421ksd",
            "ktds": "h_094ktds",
            "lol": "12lol",
            "midv": "48midv",
            "mjad": "h_402mjad",
            "mxgs": "h_068mxgs",
            "natr": "h_067natr",
            "need": "h_198need",
            "nhdt": "1NHDT",
            "nhdta": "1NHDTA",
            "nxg": "h_254nxg",
            "okad": "84okad",
            "open": "1open",
            "ped": "24ped",
            "r": "h_093r",
            "rct": "1rct",
            "rctd": "1rctd",
            "sace": "1SACE",
            "sama": "h_244sama",
            "sdde": "1SDDE",
            "sddm": "1SDDM",
            "sdmt": "1SDMT",
            "sma": "83sma",
            "star": "1STAR",
            "stars": "1stars",
            "svdvd": "1SVDVD",
            "sw": "h_635SW",
            "t": "55t",
            "tkbn": "h_254tkbn",
            "vspdr": "1VSPDR",
            "vspds": "1VSPDS",
            "wnz": "3wnz"
        },
        "fanza_suffixes": {
            "ibw": "z"
        },
        "translation": {
            "api_url": "https://api.siliconflow.cn/v1/chat/completions",
            "source_lang": "日语",
            "target_lang": "中文",
            "api_token": "",
            "model": "THUDM/glm-4-9b-chat"
        }
    }
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                config.update(loaded_config)
                logging.info(f"Loaded configuration file: {CONFIG_FILE}")
        else:
            # Create config directory if it doesn't exist
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            # Save default config
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
                logging.info(f"Created default configuration file: {CONFIG_FILE}")
    except Exception as e:
        logging.error(f"Failed to load configuration file: {str(e)}")
    
    return config

# Get current configuration
CURRENT_CONFIG = load_config()
CURRENT_API_URL = CURRENT_CONFIG.get("api_url", "")
# Fall back to environment variable only if api_url is not set in config
if not CURRENT_API_URL:
    CURRENT_API_URL = os.environ.get("API_URL", "")
    if CURRENT_API_URL:
        logging.info(f"Using API URL from environment: {CURRENT_API_URL}")
        # Update the config file with the API URL from environment
        CURRENT_CONFIG["api_url"] = CURRENT_API_URL
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(CURRENT_CONFIG, f, ensure_ascii=False, indent=2)
                logging.info(f"Updated configuration file with API URL from environment")
        except Exception as e:
            logging.error(f"Failed to update configuration file: {str(e)}")
CURRENT_WATCH_URL_PREFIX = CURRENT_CONFIG.get("watch_url_prefix", "https://missav.ai")

# Favorites management
FAVORITES_FILE = "data/favorites.json"

def load_favorites():
    """Load favorites from file"""
    favorites = []
    try:
        if os.path.exists(FAVORITES_FILE):
            with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                favorites = json.load(f)
                logging.info(f"Loaded favorites file: {FAVORITES_FILE}")
    except Exception as e:
        logging.error(f"Failed to load favorites file: {str(e)}")
    
    return favorites

def save_favorites(favorites):
    """Save favorites to file"""
    try:
        os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True)
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
            json.dump(favorites, f, ensure_ascii=False, indent=4)
            logging.info(f"Saved favorites to file: {FAVORITES_FILE}")
        return True
    except Exception as e:
        logging.error(f"Failed to save favorites file: {str(e)}")
        return False

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 Not Found errors"""
    return render_template('error.html', 
                          error_title="Page Not Found", 
                          error_message="The page you are looking for does not exist."), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Handle 500 Internal Server Error"""
    return render_template('error.html', 
                          error_title="Internal Server Error", 
                          error_message="An unexpected error occurred on the server."), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle uncaught exceptions"""
    # Log the error
    app.logger.error(f"Uncaught exception: {str(e)}")
    app.logger.error(traceback.format_exc())
    
    # Return error page
    return render_template('error.html', 
                          error_title="Application Error", 
                          error_message="An unexpected error occurred.", 
                          error_details=str(e)), 500

# Routes: Web pages
@app.route('/')
def index():
    """Show homepage"""
    # Get the 4 most recently viewed movies
    recent_movies = []
    try:
        # Ensure DB is initialized
        if db and db.local:
            # Query database for recently viewed movies
            recent_movies_data = db.get_recent_movies(limit=4)
            if recent_movies_data:
                recent_movies = [format_movie_data(movie) for movie in recent_movies_data]
    except Exception as e:
        logging.error(f"Failed to get recent movies: {str(e)}")
    
    return render_template('index.html', recent_movies=recent_movies)

@app.route('/search')
def search():
    """Search for movie by ID"""
    movie_id = request.args.get('id', '')
    if not movie_id:
        return render_template('search.html', search_query='')
    
    movie_data = get_movie_data(movie_id)
    if movie_data:
        formatted_movie = format_movie_data(movie_data)
        return render_template('search.html', movie=formatted_movie, search_query=movie_id)
    else:
        return render_template('search.html', search_query=movie_id)

@app.route('/search_keyword')
def search_keyword():
    """关键字搜索电影"""
    keyword = request.args.get('keyword', '')
    page = request.args.get('page', '1')
    magnet = request.args.get('magnet', '')  # Get magnet parameter
    movie_type = request.args.get('type', '')  # Get type parameter
    filter_type = request.args.get('filterType', '')  # Get filterType parameter
    filter_value = request.args.get('filterValue', '')  # Get filterValue parameter
    
    # 确保页码是整数
    try:
        page = int(page)
    except ValueError:
        page = 1
    
    try:
        # 构建搜索URL和参数
        search_params = {"page": page}
        
        # Add optional parameters
        if magnet:
            search_params["magnet"] = magnet
        if movie_type:
            search_params["type"] = movie_type
            
        # Determine which API endpoint to use based on parameters
        if keyword:
            # When we have a keyword, use search endpoint
            search_url = f"{CURRENT_API_URL}/movies/search"
            search_params["keyword"] = keyword
        else:
            # When no keyword, use base endpoint
            search_url = f"{CURRENT_API_URL}/movies"
            
            # Add filter parameters if provided (only valid for base endpoint)
            if filter_type and filter_value:
                search_params["filterType"] = filter_type
                search_params["filterValue"] = filter_value
        
        # Call the API
        response = requests.get(search_url, params=search_params)
        
        if response.status_code == 200:
            data = response.json()
            movies_list = data.get("movies", [])
            pagination = data.get("pagination", {})
            
            # 格式化电影列表数据
            formatted_movies = []
            for movie in movies_list:
                formatted_movies.append({
                    "id": movie.get("id", ""),
                    "title": movie.get("title", ""),
                    "image_url": movie.get("img", ""),
                    "date": movie.get("date", ""),
                    "tags": movie.get("tags", []),
                    "translated_title": movie.get("translated_title", "")
                })
            
            # 构建分页数据
            page_info = {
                "current_page": pagination.get("currentPage", 1),
                "total_pages": len(pagination.get("pages", [])),
                "has_next": pagination.get("hasNextPage", False),
                "next_page": pagination.get("nextPage", 1),
                "pages": pagination.get("pages", [])
            }
            
            return render_template('search.html', 
                                  keyword_results=formatted_movies,
                                  keyword_query=keyword,
                                  pagination=page_info,
                                  filter_type=filter_type,
                                  filter_value=filter_value)
        else:
            logging.error(f"搜索失败: HTTP {response.status_code}")
            return render_template('search.html', 
                                 keyword_query=keyword,
                                 filter_type=filter_type,
                                 filter_value=filter_value,
                                 error_message=f"搜索失败: HTTP {response.status_code}")
    except Exception as e:
        logging.error(f"搜索失败: {str(e)}")
        return render_template('search.html', 
                             keyword_query=keyword,
                             filter_type=filter_type,
                             filter_value=filter_value,
                             error_message=f"搜索出错: {str(e)}")

@app.route('/search_actor')
def search_actor():
    """Search for actor by name"""
    actor_name = request.args.get('name', '')
    if not actor_name:
        return render_template('search.html', actor_query='')
    
    # First try to find actor by name in database
    actors = db.search_stars(actor_name)
    
    # If not found in DB, search via API
    if not actors:
        try:
            response = requests.get(f"{CURRENT_API_URL}/stars/search", params={"keyword": actor_name})
            if response.status_code == 200:
                data = response.json()
                actors = data.get("stars", [])
                
                # Save actors to database
                for actor in actors:
                    db.save_star(actor)
        except Exception as e:
            logging.error(f"Failed to search actor by API: {str(e)}")
    
    # If we found exactly one actor, show their details
    if len(actors) == 1:
        actor = actors[0]
        actor_id = actor.get("id", "")
        
        # Format actor data
        formatted_actor = {
            "name": actor.get("name", ""),
            "image_url": actor.get("avatar", ""),
            "birthdate": actor.get("birthday", ""),
            "age": actor.get("age", ""),
            "height": actor.get("height", ""),
            "measurements": f"{actor.get('bust', '')} - {actor.get('waistline', '')} - {actor.get('hipline', '')}" if actor.get('bust') else "",
            "birthplace": actor.get("birthplace", ""),
            "hobby": actor.get("hobby", "")
        }
        
        # Get actor's movies
        actor_movies = get_actor_movies(actor_id)
        formatted_movies = [format_movie_data(movie) for movie in actor_movies]
        
        return render_template('search.html', actor=formatted_actor, actor_movies=formatted_movies, actor_query=actor_name)
    
    # If multiple actors found, show a list of them
    elif len(actors) > 1:
        formatted_actors = []
        for actor in actors:
            formatted_actors.append({
                "id": actor.get("id", ""),
                "name": actor.get("name", ""),
                "image_url": actor.get("avatar", "")
            })
        return render_template('search.html', actors=formatted_actors, actor_query=actor_name)
    
    # No actors found
    return render_template('search.html', actor_query=actor_name)

@app.route('/actor/<actor_id>')
def actor_detail(actor_id):
    """Show actor detail page"""
    # Get actor information
    actor_data = get_actor_data(actor_id)
    if not actor_data:
        return redirect(url_for('index'))
    
    # Format actor data
    formatted_actor = {
        "name": actor_data.get("name", ""),
        "image_url": actor_data.get("avatar", ""),
        "birthdate": actor_data.get("birthday", ""),
        "age": actor_data.get("age", ""),
        "height": actor_data.get("height", ""),
        "measurements": f"{actor_data.get('bust', '')} - {actor_data.get('waistline', '')} - {actor_data.get('hipline', '')}" if actor_data.get('bust') else "",
        "birthplace": actor_data.get("birthplace", ""),
        "hobby": actor_data.get("hobby", "")
    }
    
    # Get actor's movies
    actor_movies = get_actor_movies(actor_id)
    formatted_movies = [format_movie_data(movie) for movie in actor_movies]
    
    return render_template('actor.html', actor=formatted_actor, actor_movies=formatted_movies)

@app.route('/movie/<movie_id>')
def movie_detail(movie_id):
    """Show movie detail page"""
    movie_data = get_movie_data(movie_id)
    if movie_data:
        formatted_movie = format_movie_data(movie_data)
        
        # Check if movie is in favorites
        favorites = load_favorites()
        formatted_movie["is_favorite"] = movie_id in favorites
        
        # Note: We'll fetch summary asynchronously if it's missing
        has_summary = bool(formatted_movie.get("summary") or movie_data.get("description"))
        
        # Get magnet links for this movie
        try:
            # Extract gid and uc from movie data if available
            gid = movie_data.get("gid", "")
            uc = movie_data.get("uc", "0")
            
            # Call the API to get magnet links
            magnet_url = f"{CURRENT_API_URL}/magnets/{movie_id}"
            params = {}
            if gid:
                params["gid"] = gid
            if uc:
                params["uc"] = uc
            
            response = requests.get(magnet_url, params=params)
            if response.status_code == 200:
                magnets = response.json()
                # Format and sort magnets (HD first, then by size)
                formatted_magnets = []
                for magnet in magnets:
                    formatted_magnets.append({
                        "name": magnet.get("title", ""),
                        "size": magnet.get("size", ""),
                        "link": magnet.get("link", ""),
                        "date": magnet.get("shareDate", ""),
                        "is_hd": magnet.get("isHD", False),
                        "has_subtitle": magnet.get("hasSubtitle", False)
                    })
                
                # Sort magnets: HD first, then with subtitles, then by size
                formatted_magnets.sort(key=lambda x: (
                    not x["is_hd"],  # HD first
                    not x["has_subtitle"],  # Subtitles second
                    -float(x["size"].replace("GB", "").replace("MB", "").strip()) if x["size"] else 0  # Size third (descending)
                ))
                
                formatted_movie["magnet_links"] = formatted_magnets
        except Exception as e:
            logging.error(f"Failed to get magnet links: {str(e)}")
        
        return render_template('movie.html', 
                              movie=formatted_movie, 
                              movie_data=movie_data, 
                              has_summary=has_summary, 
                              movie_id=movie_id,
                              watch_url_prefix=CURRENT_WATCH_URL_PREFIX)
    else:
        return redirect(url_for('index'))

@app.route('/video_player/<movie_id>')
def video_player(movie_id):
    """Show ad-free video player page"""
    try:
        # Get movie data to display title
        movie_data = get_movie_data(movie_id)
        if not movie_data:
            return render_template('error.html', 
                              error_title="Movie Not Found", 
                              error_message=f"Could not find movie data for {movie_id}"), 404
        
        formatted_movie = format_movie_data(movie_data)
        
        # Try to find video URL or magnet link
        video_url = ""
        magnet_link = ""
        
        # Check if we have magnet links first
        if formatted_movie.get("magnet_links") and len(formatted_movie["magnet_links"]) > 0:
            # Get the best quality magnet link (first one after sorting)
            magnet_link = formatted_movie["magnet_links"][0]["link"]
        
        return render_template('video_player.html', 
                              movie=formatted_movie,
                              video_url=video_url,
                              magnet_link=magnet_link,
                              movie_id=movie_id)
    except Exception as e:
        logging.error(f"Error in video player route: {str(e)}")
        return render_template('error.html', 
                          error_title="Video Player Error", 
                          error_message=f"An error occurred loading the video player: {str(e)}"), 500

@app.route('/favorites')
def favorites():
    """Show favorites page"""
    favorites_list = load_favorites()
    favorite_movies = []
    
    for movie_id in favorites_list:
        movie_data = get_movie_data(movie_id)
        if movie_data:
            formatted_movie = format_movie_data(movie_data)
            favorite_movies.append(formatted_movie)
    
    return render_template('favorites.html', favorites=favorite_movies)

@app.route('/refresh_movie/<movie_id>')
def refresh_movie(movie_id):
    """Force refresh movie data from API"""
    try:
        # Get the movie data directly from API
        response = requests.get(f"{CURRENT_API_URL}/movies/{movie_id}")
        if response.status_code == 200:
            movie_data = response.json()
            # Save to database
            db.save_movie(movie_data)
            logging.info(f"Refreshed movie data for {movie_id}")
            return redirect(url_for('movie_detail', movie_id=movie_id))
        else:
            logging.error(f"Failed to refresh movie data: HTTP {response.status_code}")
            return render_template('error.html', 
                                  error_title="Refresh Failed", 
                                  error_message=f"Failed to refresh movie data: HTTP {response.status_code}"), 400
    except Exception as e:
        logging.error(f"Failed to refresh movie data: {str(e)}")
        return render_template('error.html', 
                              error_title="Refresh Error", 
                              error_message=f"An error occurred: {str(e)}"), 500

# Routes: API endpoints
@app.route('/api/check_connection', methods=['GET'])
def check_api_connection():
    """Check API connection status"""
    api_url = request.args.get('api_url', CURRENT_API_URL)
    
    if not api_url:
        return jsonify({"status": "error", "message": "API URL is not set"}), 400
    
    try:
        # Try to connect to the API
        url = f"{api_url}/stars/1"  # Try to request the first page of stars
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            return jsonify({"status": "success", "message": "API connection successful"})
        else:
            return jsonify({"status": "error", "message": f"API connection error: HTTP {response.status_code}"}), 400
    
    except Exception as e:
        return jsonify({"status": "error", "message": f"API connection failed: {str(e)}"}), 400

@app.route('/api/translate', methods=['POST'])
def translate_text():
    """Translate text using the configured translation service"""
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"status": "error", "message": "Missing text to translate"}), 400
    
    text = data.get('text')
    translate_summary = data.get('translate_summary', False)
    movie_id = data.get('movie_id', '')
    
    try:
        # Use the translator to translate the text
        # Since the translator uses signals, we need to implement a synchronous version
        api_url = CURRENT_CONFIG.get("translation", {}).get("api_url", "")
        api_token = CURRENT_CONFIG.get("translation", {}).get("api_token", "")
        model = CURRENT_CONFIG.get("translation", {}).get("model", "gpt-3.5-turbo")
        source_lang = CURRENT_CONFIG.get("translation", {}).get("source_lang", "日语")
        target_lang = CURRENT_CONFIG.get("translation", {}).get("target_lang", "中文")
        
        # Check if API URL and token are set
        if not api_url:
            return jsonify({"status": "error", "message": "Translation API URL is not set"}), 400
        
        # Check if API token is set (not needed for local Ollama)
        is_ollama = "localhost:11434" in api_url or "127.0.0.1:11434" in api_url
        if not api_token and not is_ollama:
            return jsonify({"status": "error", "message": "Translation API token is not set"}), 400
        
        # Prepare request headers
        headers = {
            "Content-Type": "application/json"
        }
        
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"
        
        # Prepare request data
        prompt = f"Translate the following {source_lang} text to {target_lang}. Only return the translated text, no explanations:\n\n{text}"
        
        # Add debugging
        logging.info(f"Translation request: API URL = {api_url}, Model = {model}")
        logging.info(f"Text to translate: {text}")
        
        # Build request payload based on API type
        if is_ollama:
            # Ollama API format
            payload = {
                "model": model,
                "prompt": f"You are a professional {source_lang} to {target_lang} translator.\n{prompt}",
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9
                }
            }
        else:
            # Standard OpenAI-compatible format
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": f"You are a professional {source_lang} to {target_lang} translator."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            }
        
        # Send request
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        # Log the response for debugging
        logging.info(f"Translation API response status: {response.status_code}")
        try:
            response_text = response.text[:500]  # Limit log size
            logging.info(f"Translation API response: {response_text}")
        except:
            logging.info("Could not log response text")
        
        # Parse response
        if response.status_code == 200:
            result = response.json()
            
            # Extract translated text from different response formats
            translated_text = ""
            
            # Ollama API format
            if is_ollama:
                if "response" in result:
                    translated_text = result["response"].strip()
                elif "message" in result and isinstance(result["message"], dict):
                    if "content" in result["message"] and result["message"]["content"]:
                        translated_text = result["message"]["content"].strip()
            
            # Standard OpenAI format
            elif "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    translated_text = choice["message"]["content"].strip()
                elif "text" in choice:  # Some APIs may use text field directly
                    translated_text = choice["text"].strip()
            
            logging.info(f"Extracted translated text: {translated_text}")
            
            if translated_text:
                return jsonify({"status": "success", "translated_text": translated_text})
            else:
                return jsonify({"status": "error", "message": "Could not extract translated text from API response"}), 500
        else:
            return jsonify({"status": "error", "message": f"Translation request failed: HTTP {response.status_code}"}), 500
    
    except Exception as e:
        logging.error(f"Translation process error: {str(e)}")
        return jsonify({"status": "error", "message": f"Translation process error: {str(e)}"}), 500

@app.route('/api/save_translation/<movie_id>', methods=['POST'])
def save_translation(movie_id):
    """Save the translated title and summary to the database"""
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Missing translation data"}), 400
    
    translated_title = data.get('translated_title')
    translated_summary = data.get('translated_summary')
    
    try:
        # Get the movie data
        movie_data = get_movie_data(movie_id)
        if not movie_data:
            return jsonify({"status": "error", "message": "Movie not found"}), 404
        
        # Update the movie data with the translated information
        if translated_title:
            movie_data['translated_title'] = translated_title
        
        if translated_summary:
            movie_data['translated_description'] = translated_summary
        
        # Save to database
        db.save_movie(movie_data)
        
        return jsonify({"status": "success"})
    except Exception as e:
        logging.error(f"Failed to save translation: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to save translation: {str(e)}"}), 500

@app.route('/api/toggle_favorite/<movie_id>', methods=['POST'])
def toggle_favorite(movie_id):
    """Toggle a movie's favorite status"""
    favorites = load_favorites()
    
    if movie_id in favorites:
        favorites.remove(movie_id)
        is_favorite = False
    else:
        favorites.append(movie_id)
        is_favorite = True
    
    save_favorites(favorites)
    
    return jsonify({"status": "success", "is_favorite": is_favorite})

@app.route('/api/clear_favorites', methods=['POST'])
def clear_favorites():
    """Clear all favorites"""
    save_favorites([])
    
    return jsonify({"status": "success"})

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve images from the buspic directory"""
    # Split the path to get the movie ID and actual filename
    parts = filename.split('/')
    if len(parts) < 2:
        return "Invalid path", 400
    
    # Check if this is an actor image from the unified actor directory
    if parts[0] == 'actor':
        actor_id = parts[1].split('.')[0]  # Extract actor_id from filename
        directory = os.path.join("buspic", "actor")
        
        # Check if the directory exists
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        # Check if the file exists
        file_path = os.path.join(directory, parts[1])
        if not os.path.exists(file_path):
            # Try to download the image
            try:
                actor_data = get_actor_data(actor_id)
                if actor_data:
                    image_url = actor_data.get("avatar", "")
                    if image_url:
                        download_image(image_url, file_path)
            except Exception as e:
                logging.error(f"Failed to download actor image: {str(e)}")
        
        # If file exists now, serve it
        if os.path.exists(file_path):
            return send_from_directory(directory, parts[1])
        
        # Otherwise return a default image
        return send_from_directory('static/img', 'no_image.jpg')
    
    # Check if this is a cover image
    if parts[0] == 'covers':
        movie_id = parts[1].split('.')[0]  # Extract movie_id from filename
        directory = os.path.join("buspic", "covers")
        
        # Check if the directory exists
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        # Check if the file exists
        file_path = os.path.join(directory, parts[1])
        if not os.path.exists(file_path):
            # Try to download the image
            try:
                movie_data = get_movie_data(movie_id)
                if movie_data:
                    image_url = movie_data.get("img", "")
                    if image_url:
                        success = download_image(image_url, file_path)
                        if not success and "sample" in movie_data:
                            # 如果主图下载失败且有样本图，尝试使用第一个样本图
                            samples = movie_data.get("samples", [])
                            if samples and len(samples) > 0:
                                sample_url = samples[0].get("src", "")
                                if sample_url:
                                    download_image(sample_url, file_path)
            except Exception as e:
                logging.error(f"Failed to download cover image: {str(e)}")
        
        # If file exists now, serve it
        if os.path.exists(file_path):
            return send_from_directory(directory, parts[1])
        
        # Otherwise return a default image
        return send_from_directory('static/img', 'no_image.jpg')
    
    # Regular movie image handling (sample images and movie-specific covers)
    movie_id = parts[0]
    image_name = parts[-1]
    directory = os.path.join("buspic", movie_id)
    
    # Check if the directory exists
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    
    # Check if the file exists
    file_path = os.path.join(directory, image_name)
    if not os.path.exists(file_path):
        # Try to download the image
        try:
            movie_data = get_movie_data(movie_id)
            if movie_data:
                if "cover" in image_name:
                    # First check if the cover exists in covers directory
                    cover_path = os.path.join("buspic", "covers", f"{movie_id}.jpg")
                    if os.path.exists(cover_path):
                        # Copy the file from covers directory
                        import shutil
                        shutil.copy2(cover_path, file_path)
                    else:
                        # Download directly
                        image_url = movie_data.get("img", "")
                        if image_url:
                            success = download_image(image_url, file_path)
                            # Also save to covers directory
                            if success:
                                os.makedirs(os.path.dirname(cover_path), exist_ok=True)
                                shutil.copy2(file_path, cover_path)
                            elif "sample" in movie_data:
                                # 如果主图下载失败且有样本图，尝试使用第一个样本图
                                samples = movie_data.get("samples", [])
                                if samples and len(samples) > 0:
                                    sample_url = samples[0].get("src", "")
                                    if sample_url:
                                        if download_image(sample_url, file_path):
                                            shutil.copy2(file_path, cover_path)
                elif "actor_" in image_name:
                    # Extract actor ID from filename (e.g., actor_123.jpg)
                    actor_id = image_name.split('_')[1].split('.')[0]
                    
                    # First check if the actor image exists in the actor directory
                    actor_path = os.path.join("buspic", "actor", f"{actor_id}.jpg")
                    if os.path.exists(actor_path):
                        # Copy the file from actor directory
                        import shutil
                        shutil.copy2(actor_path, file_path)
                    else:
                        # Download actor image to both locations
                        actor_data = get_actor_data(actor_id)
                        if actor_data:
                            image_url = actor_data.get("avatar", "")
                            if image_url:
                                # Download to unified actor directory first
                                os.makedirs(os.path.dirname(actor_path), exist_ok=True)
                                if download_image(image_url, actor_path):
                                    # Copy to movie-specific location
                                    shutil.copy2(actor_path, file_path)
                elif "sample_" in image_name:
                    # Extract sample index from filename (e.g., sample_1.jpg)
                    try:
                        sample_index = int(image_name.split('_')[1].split('.')[0]) - 1
                        samples = movie_data.get("samples", [])
                        if samples and 0 <= sample_index < len(samples):
                            sample_url = samples[sample_index].get("src", "")
                            if sample_url:
                                download_image(sample_url, file_path)
                    except (ValueError, IndexError):
                        logging.error(f"Invalid sample index in filename: {image_name}")
        except Exception as e:
            logging.error(f"Failed to download image: {str(e)}")
    
    # If file exists now, serve it
    if os.path.exists(file_path):
        return send_from_directory(directory, image_name)
    
    # Otherwise return a default image
    return send_from_directory('static/img', 'no_image.jpg')

# Helper functions
def get_movie_data(movie_id):
    """Get movie data from database or API"""
    # Try to get from database first
    movie_data = db.get_movie(movie_id)
    
    # If not in database, try to get from API
    if not movie_data:
        try:
            response = requests.get(f"{CURRENT_API_URL}/movies/{movie_id}")
            if response.status_code == 200:
                movie_data = response.json()
                # Save to database
                db.save_movie(movie_data)
        except Exception as e:
            logging.error(f"Failed to get movie data from API: {str(e)}")
    
    return movie_data

def get_actor_data(actor_id):
    """Get actor data from database or API"""
    # Try to get from database first
    actor_data = db.get_star(actor_id)
    
    # If not in database, try to get from API
    if not actor_data:
        try:
            response = requests.get(f"{CURRENT_API_URL}/stars/{actor_id}")
            if response.status_code == 200:
                actor_data = response.json()
                # Save to database
                db.save_star(actor_data)
        except Exception as e:
            logging.error(f"Failed to get actor data from API: {str(e)}")
    
    return actor_data

def get_actor_movies(actor_id):
    """Get actor's movies from database or API"""
    # Try to get from database first
    movies = db.get_star_movies(actor_id)
    
    # If not in database, try to get from API
    if not movies:
        try:
            all_movies = []
            page = 1
            max_pages = 3  # Limit to 3 pages for performance
            
            while page <= max_pages:
                response = requests.get(
                    f"{CURRENT_API_URL}/movies",
                    params={
                        "filterType": "star",
                        "filterValue": actor_id,
                        "page": str(page),
                        "magnet": "all"
                    }
                )
                
                if response.status_code != 200:
                    break
                
                data = response.json()
                movies_list = data.get("movies", [])
                pagination = data.get("pagination", {})
                
                if not movies_list:
                    break
                
                # Get detailed movie info for each movie
                for movie in movies_list:
                    movie_id = movie.get("id")
                    if movie_id:
                        movie_data = get_movie_data(movie_id)
                        if movie_data:
                            all_movies.append(movie_data)
                
                # Check if there's a next page
                has_next_page = pagination.get("hasNextPage", False)
                if not has_next_page:
                    break
                
                page += 1
            
            movies = all_movies
        except Exception as e:
            logging.error(f"Failed to get actor movies from API: {str(e)}")
    
    return movies

def format_movie_data(movie_data):
    """Format movie data for template rendering"""
    formatted_movie = {
        "id": movie_data.get("id", ""),
        "title": movie_data.get("title", ""),
        "translated_title": movie_data.get("translated_title", ""),
        "image_url": movie_data.get("img", ""),
        "date": movie_data.get("date", ""),
        "producer": movie_data.get("publisher", {}).get("name", "") if isinstance(movie_data.get("publisher"), dict) else movie_data.get("publisher", ""),
        "summary": movie_data.get("description", ""),
        "translated_summary": movie_data.get("translated_description", ""),
        "genres": [genre.get("name", "") for genre in movie_data.get("genres", [])] if isinstance(movie_data.get("genres"), list) else [],
        "actors": [],
        "magnet_links": [],
        "sample_images": []
    }
    
    # Format actors
    for actor in movie_data.get("stars", []):
        actor_id = actor.get("id", "")
        formatted_movie["actors"].append({
            "id": actor_id,
            "name": actor.get("name", ""),
            "image_url": actor.get("avatar", "")
        })
    
    # Format magnet links
    for magnet in movie_data.get("magnets", []):
        formatted_movie["magnet_links"].append({
            "name": magnet.get("name", ""),
            "size": magnet.get("size", ""),
            "link": magnet.get("link", ""),
            "date": magnet.get("date", ""),
            "is_hd": magnet.get("isHD", False),
            "has_subtitle": magnet.get("hasSubtitle", False)
        })
    
    # Format sample images
    for i, sample in enumerate(movie_data.get("samples", [])):
        formatted_movie["sample_images"].append({
            "index": i + 1,
            "src": sample.get("src", ""),
            "thumbnail": sample.get("thumbnail", sample.get("src", "")),
            "url": f"/images/{formatted_movie['id']}/sample_{i+1}.jpg"
        })
    
    return formatted_movie

def download_image(url, save_path):
    """Download an image from URL and save it to path"""
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
        
        # 首先尝试直接下载图片
        response = requests.get(url, headers=headers, stream=True, timeout=10)
        
        # 如果直接下载失败，使用更复杂的会话方法
        if response.status_code != 200:
            # 确定来源域名
            domain = ""
            if "javbus" in url:
                domain = "javbus.com"
                referer = "https://www.javbus.com/"
            elif "dmm.co.jp" in url:
                domain = "dmm.co.jp"
                referer = "https://www.dmm.co.jp/"
            else:
                domain = url.split('/')[2]
                referer = f"https://{domain}/"
            
            # 更新请求头中的Referer
            headers["Referer"] = referer
            
            # 创建一个会话来保持cookies
            session = requests.Session()
            session.headers.update(headers)
            
            # 对于DMM，需要先访问其主页面以获取必要的cookies
            if "dmm.co.jp" in url:
                session.get("https://www.dmm.co.jp/")
            
            # 重新尝试下载图片
            response = session.get(url, stream=True, timeout=10)
        
        # 如果下载成功，保存图片
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        
        logging.error(f"Failed to download image from {url}, status code: {response.status_code}")
        return False
    except Exception as e:
        logging.error(f"Failed to download image from {url}: {str(e)}")
        return False

@app.route('/config')
def config_page():
    """Show configuration page"""
    # Load the current configuration
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config_json = f.read()
        
        return render_template('config.html', config_json=config_json)
    except Exception as e:
        error_message = f"Failed to load configuration file: {str(e)}"
        logging.error(error_message)
        return render_template('config.html', error_message=error_message, config_json="{}")

@app.route('/api/save_config', methods=['POST'])
def save_config_api():
    """API endpoint to save configuration"""
    try:
        data = request.get_json()
        if not data or 'config' not in data:
            return jsonify({"status": "error", "message": "Missing configuration data"}), 400
        
        config_str = data.get('config')
        
        # Validate JSON format
        try:
            config_data = json.loads(config_str)
        except json.JSONDecodeError as e:
            return jsonify({"status": "error", "message": f"Invalid JSON format: {str(e)}"}), 400
        
        # Save to file
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(config_str)
        
        # Update current configuration
        global CURRENT_CONFIG, CURRENT_API_URL, CURRENT_WATCH_URL_PREFIX
        CURRENT_CONFIG = config_data
        CURRENT_API_URL = config_data.get("api_url", "")
        CURRENT_WATCH_URL_PREFIX = config_data.get("watch_url_prefix", "https://missav.ai")
        
        logging.info(f"Configuration saved successfully")
        
        return jsonify({"status": "success"})
    except Exception as e:
        error_message = f"Failed to save configuration: {str(e)}"
        logging.error(error_message)
        return jsonify({"status": "error", "message": error_message}), 500

@app.route('/api/restart_application', methods=['POST'])
def restart_application():
    """API endpoint to restart the application"""
    try:
        import os
        import signal
        import threading
        
        def delayed_restart():
            # Wait a short time to allow the response to be sent
            import time
            time.sleep(1)
            # Send SIGTERM to the application process
            os.kill(os.getpid(), signal.SIGTERM)
        
        # Start a thread to restart the application
        threading.Thread(target=delayed_restart).start()
        
        return jsonify({"status": "success", "message": "Application restart initiated"})
    except Exception as e:
        error_message = f"Failed to restart application: {str(e)}"
        logging.error(error_message)
        return jsonify({"status": "error", "message": error_message}), 500

@app.route('/api/get_movie_summary/<movie_id>', methods=['GET'])
def get_movie_summary(movie_id):
    """API endpoint to fetch movie summary from FANZA asynchronously"""
    try:
        # Get movie data
        movie_data = get_movie_data(movie_id)
        if not movie_data:
            return jsonify({"status": "error", "message": "Movie not found"}), 404
            
        # If summary already exists, return it
        if movie_data.get("description"):
            return jsonify({
                "status": "success", 
                "summary": movie_data.get("description"),
                "translated_summary": movie_data.get("translated_description", "")
            })
            
        # Try to fetch summary from FANZA
        logging.info(f"Fetching summary from FANZA for movie ID: {movie_id}")
        
        # Use the FanzaScraper to get the summary
        # Note that get_movie_summary internally calls normalize_movie_id and uses it correctly
        summary_data = fanza_scraper.get_movie_summary(movie_id)
        
        if summary_data:
            # If the summary is a dictionary, extract just the 'summary' field
            if isinstance(summary_data, dict) and 'summary' in summary_data:
                summary = summary_data['summary']
                logging.info(f"Found summary for {movie_id} from source: {summary_data.get('source', 'unknown')}")
                logging.info(f"Summary URL: {summary_data.get('url', 'unknown')}")
                logging.info(f"FANZA ID used: {summary_data.get('fanza_id', 'unknown')}")
            else:
                summary = summary_data
                
            logging.info(f"Found summary for {movie_id} from FANZA")
            
            # Update movie data with the summary
            movie_data["description"] = summary
            # Save to database
            db.save_movie(movie_data)
            
            return jsonify({
                "status": "success", 
                "summary": summary,
                "translated_summary": ""
            })
        else:
            # Get the normalized ID for logging purposes
            try:
                normalized_id = fanza_scraper.normalize_movie_id(movie_id)
                logging.warning(f"Could not find summary for {movie_id} (normalized as {normalized_id})")
            except:
                logging.warning(f"Could not find summary for {movie_id}")
                
            return jsonify({"status": "error", "message": "Could not find summary"}), 404
    except Exception as e:
        logging.error(f"Failed to get summary from FANZA: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Start the server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False) 