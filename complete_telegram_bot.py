"""
بوت تليجرام لتحميل الأغاني من يوتيوب - كود كامل شامل

هذا الملف يحتوي على جميع المكونات والأكواد اللازمة لتشغيل بوت تليجرام لتحميل الأغاني.
يمكن استخدام هذا الملف مباشرة لتشغيل البوت بدون الحاجة إلى ملفات إضافية.
"""

import os
import sys
import time
import json
import logging
import threading
import http.server
import socketserver
import requests
import urllib.parse
import tempfile
from datetime import datetime
from urllib.parse import parse_qs

# ==================== 
# إعدادات البوت الأساسية
# ====================

# توكن البوت - يجب استبداله بتوكن البوت الخاص بك
TELEGRAM_BOT_TOKEN = "7960911121:AAHyW15allvXcTBVGQAirsNZ4aE1ZwTae2U"

# معرف المشرف
ADMIN_USERNAME = "@Bilalja0"

# قناة الإشعارات
NOTIFICATION_CHANNEL = "@bilaljomaa551"

# مفتاح واجهة برمجة التطبيقات لليوتيوب (اختياري)
YOUTUBE_API_KEY = ""

# الحد الأقصى لمدة الفيديو بالدقائق
MAX_DURATION_MINUTES = 10

# الحد الأقصى لحجم الملف بالميغابايت
MAX_FILE_SIZE_MB = 50

# ملف قاعدة البيانات
DB_FILE = "users.json"

# ==================== 
# إعدادات التسجيل
# ====================

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("music_bot")

# ==================== 
# دوال مساعدة
# ====================

def create_db_if_not_exists():
    """إنشاء ملف قاعدة البيانات إذا لم يكن موجوداً"""
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w') as f:
            json.dump({"users": {}, "total_users": 0, "total_downloads": 0}, f)
        logger.info(f"Created new database file: {DB_FILE}")

def format_duration(seconds):
    """تنسيق الثواني إلى دقائق وثواني"""
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes}:{seconds:02d}"

def format_file_size(size_bytes):
    """تنسيق حجم الملف ليكون مقروءاً"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def get_current_time():
    """الحصول على الوقت الحالي بتنسيق مقروء"""
    return time.strftime("%Y-%m-%d %H:%M:%S")

def truncate_string(text, max_length=50):
    """اقتطاع النص إلى طول معين"""
    if len(text) > max_length:
        return text[:max_length-3] + "..."
    return text

def sanitize_filename(filename):
    """إزالة الأحرف غير المسموح بها من اسم الملف"""
    illegal_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in illegal_chars:
        filename = filename.replace(char, '_')
    return filename.strip()

# ==================== 
# فئة خدمة إدارة المستخدمين
# ====================

class UserService:
    def __init__(self):
        create_db_if_not_exists()
        self.load_db()

    def load_db(self):
        """تحميل قاعدة بيانات المستخدمين من الملف"""
        try:
            with open(DB_FILE, 'r') as f:
                self.db = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error loading database: {e}")
            self.db = {"users": {}, "total_users": 0, "total_downloads": 0}
            self.save_db()

    def save_db(self):
        """حفظ قاعدة بيانات المستخدمين إلى الملف"""
        try:
            with open(DB_FILE, 'w') as f:
                json.dump(self.db, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving database: {e}")

    def user_exists(self, user_id):
        """التحقق مما إذا كان المستخدم موجوداً في قاعدة البيانات"""
        return str(user_id) in self.db["users"]

    def add_user(self, user):
        """إضافة مستخدم جديد إلى قاعدة البيانات"""
        user_id = str(user.id)
        
        # إذا كان المستخدم موجوداً، فقط تحديث وقت آخر ظهور له
        if self.user_exists(user_id):
            self.db["users"][user_id]["last_seen"] = get_current_time()
            self.save_db()
            return False  # ليس مستخدماً جديداً
        
        # إضافة مستخدم جديد
        self.db["users"][user_id] = {
            "id": user_id,
            "first_name": user.first_name,
            "last_name": user.last_name if hasattr(user, 'last_name') else "",
            "username": user.username if hasattr(user, 'username') else "",
            "joined_date": get_current_time(),
            "last_seen": get_current_time(),
            "downloads": 0,
            "searches": 0
        }
        
        self.db["total_users"] += 1
        self.save_db()
        return True  # مستخدم جديد

    def update_user_stats(self, user_id, action_type):
        """تحديث إحصائيات المستخدم"""
        user_id = str(user_id)
        if not self.user_exists(user_id):
            logger.warning(f"Attempted to update stats for non-existent user: {user_id}")
            return
        
        if action_type == "download":
            self.db["users"][user_id]["downloads"] += 1
            self.db["total_downloads"] += 1
        elif action_type == "search":
            self.db["users"][user_id]["searches"] += 1
        
        self.db["users"][user_id]["last_seen"] = get_current_time()
        self.save_db()

    def get_user_info(self, user_id):
        """الحصول على معلومات حول مستخدم معين"""
        user_id = str(user_id)
        if not self.user_exists(user_id):
            return None
        return self.db["users"][user_id]

    def get_stats(self):
        """الحصول على الإحصائيات العامة"""
        active_users = 0
        for user_id, user_data in self.db["users"].items():
            # اعتبار المستخدم نشطاً إذا استخدم البوت في آخر 30 يوماً (مبسطة لهذا التنفيذ)
            active_users += 1
        
        return {
            "total_users": self.db["total_users"],
            "active_users": active_users,
            "total_downloads": self.db["total_downloads"]
        }

    def format_user_info(self, user_data):
        """تنسيق بيانات المستخدم للعرض"""
        if not user_data:
            return "User not found"
        
        info = [
            f"👤 <b>User ID:</b> {user_data['id']}",
            f"📛 <b>Name:</b> {user_data['first_name']} {user_data['last_name']}",
        ]
        
        if user_data.get('username'):
            info.append(f"🔖 <b>Username:</b> @{user_data['username']}")
        
        info.extend([
            f"📅 <b>Joined:</b> {user_data['joined_date']}",
            f"🔍 <b>Searches:</b> {user_data['searches']}",
            f"⬇️ <b>Downloads:</b> {user_data['downloads']}",
            f"⏱️ <b>Last seen:</b> {user_data['last_seen']}"
        ])
        
        return "\n".join(info)

# ==================== 
# فئة خدمة يوتيوب
# ====================

class YouTubeService:
    def __init__(self):
        self.api_key = YOUTUBE_API_KEY

    def search_songs(self, query, max_results=5):
        """البحث عن الأغاني على يوتيوب"""
        if not self.api_key:
            # إذا لم يكن هناك مفتاح واجهة برمجة التطبيقات، استخدم طريقة أبسط
            return self.search_songs_without_api(query, max_results)

        try:
            # استخدام مكتبة Google API للبحث
            from googleapiclient.discovery import build
            from googleapiclient.errors import HttpError
            
            youtube = build('youtube', 'v3', developerKey=self.api_key)
            search_response = youtube.search().list(
                q=query,
                part='id,snippet',
                maxResults=max_results,
                type='video',
                videoCategoryId='10'  # فئة الموسيقى
            ).execute()

            results = []
            for item in search_response.get('items', []):
                if item['id']['kind'] == 'youtube#video':
                    video_id = item['id']['videoId']
                    title = item['snippet']['title']
                    channel = item['snippet']['channelTitle']
                    
                    # الحصول على تفاصيل الفيديو
                    video_response = youtube.videos().list(
                        part='contentDetails,statistics',
                        id=video_id
                    ).execute()
                    
                    if video_response['items']:
                        content_details = video_response['items'][0]['contentDetails']
                        statistics = video_response['items'][0]['statistics']
                        
                        # تحليل المدة
                        duration = content_details['duration']
                        # تحويل مدة ISO 8601 إلى ثوانٍ
                        # تنفيذ مبسط
                        minutes = 0
                        seconds = 0
                        if 'M' in duration:
                            minutes = int(duration.split('M')[0].split('T')[1])
                        if 'S' in duration:
                            seconds = int(duration.split('S')[0].split('M')[-1])
                        
                        duration_seconds = minutes * 60 + seconds
                        
                        # تخطي الفيديوهات الطويلة جداً
                        if minutes > MAX_DURATION_MINUTES:
                            continue
                        
                        # الحصول على عدد المشاهدات
                        view_count = int(statistics.get('viewCount', 0))
                        
                        results.append({
                            'video_id': video_id,
                            'title': title,
                            'channel': channel,
                            'duration': duration_seconds,
                            'duration_str': format_duration(duration_seconds),
                            'views': view_count,
                            'url': f"https://www.youtube.com/watch?v={video_id}"
                        })
            
            return results
        
        except Exception as e:
            logger.error(f"YouTube API error: {e}")
            # الرجوع إلى الطريقة البديلة في حالة وجود خطأ
            return self.search_songs_without_api(query, max_results)

    def search_songs_without_api(self, query, max_results=5):
        """البحث عن الأغاني دون استخدام واجهة برمجة تطبيقات يوتيوب"""
        try:
            import yt_dlp
            
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
                'force_generic_extractor': True,
                'ignoreerrors': True,
                'format': 'best',
                'max_downloads': max_results,
                'sleep_interval': 1,
                'playlistend': max_results,
                'default_search': 'ytsearch'
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
                
                if 'entries' not in result:
                    return []
                
                videos = []
                for entry in result['entries']:
                    if entry:
                        # الحصول على المزيد من التفاصيل حول الفيديو
                        try:
                            video_info = ydl.extract_info(entry['url'], download=False)
                            
                            # تخطي الفيديوهات الطويلة جداً
                            if video_info.get('duration', 0) > MAX_DURATION_MINUTES * 60:
                                continue
                                
                            videos.append({
                                'video_id': entry.get('id', ''),
                                'title': entry.get('title', 'Unknown Title'),
                                'channel': entry.get('uploader', 'Unknown Channel'),
                                'duration': video_info.get('duration', 0),
                                'duration_str': format_duration(video_info.get('duration', 0)),
                                'views': video_info.get('view_count', 0),
                                'url': entry.get('url', '')
                            })
                        except Exception as e:
                            logger.error(f"Error extracting video info: {e}")
                            continue
                
                return videos
                
        except Exception as e:
            logger.error(f"Error searching YouTube without API: {e}")
            return []

    def download_song(self, video_url, progress_callback=None):
        """تنزيل أغنية من يوتيوب"""
        try:
            import yt_dlp
            
            temp_dir = tempfile.mkdtemp()
            output_file = os.path.join(temp_dir, 'audio')
            
            # تحديد مسار ملف ffmpeg للتأكد من استخدام النسخة المثبتة
            ffmpeg_location = "/nix/store/3zc5jbvqzrn8zmva4fx5p0nh4yy03wk4-ffmpeg-6.1.1-bin/bin"
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_file + '.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'progress_hooks': [self._create_progress_hook(progress_callback)],
                'quiet': True,
                'no_warnings': True,
                'ffmpeg_location': ffmpeg_location,  # تحديد مسار ملف ffmpeg
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                
                title = info.get('title', 'Unknown')
                artist = info.get('artist', info.get('uploader', 'Unknown Artist'))
                
                # ملف الإخراج المتوقع بناءً على معالج البوست
                mp3_file = output_file + '.mp3'
                if not os.path.exists(mp3_file):
                    # محاولة العثور على الملف بامتداد مختلف
                    for file in os.listdir(temp_dir):
                        if file.endswith('.mp3'):
                            mp3_file = os.path.join(temp_dir, file)
                            break
                
                # الحصول على حجم الملف
                file_size = os.path.getsize(mp3_file)
                
                # التحقق مما إذا كان حجم الملف يتجاوز الحد
                if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                    os.remove(mp3_file)
                    return None, "File size exceeds the limit"
                
                return {
                    'file_path': mp3_file,
                    'title': title,
                    'artist': artist,
                    'duration': info.get('duration', 0),
                    'file_size': file_size,
                    'file_size_str': format_file_size(file_size)
                }, None
        
        except Exception as e:
            logger.error(f"Error downloading song: {e}")
            if os.path.exists(output_file):
                os.remove(output_file)
            return None, f"Error downloading the song: {str(e)}"

    def _create_progress_hook(self, callback):
        """إنشاء دالة تتبع التقدم لـ youtube-dl"""
        def hook(d):
            if callback and d['status'] == 'downloading':
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                
                if total > 0:
                    percent = (downloaded / total) * 100
                    callback(percent, downloaded, total)
        
        return hook

# ==================== 
# فئة خادم Keep-Alive
# ====================

# نص صفحة الحالة
KEEP_ALIVE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Music Bot - Status Page</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f0f0f0;
            margin: 0;
            padding: 20px;
            text-align: center;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
        }
        .status {
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
            background-color: #d4edda;
            color: #155724;
            font-weight: bold;
        }
        .info {
            text-align: left;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .footer {
            margin-top: 30px;
            font-size: 12px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Telegram Music Bot</h1>
        <div class="status">🟢 Bot is running!</div>
        <div class="info">
            <p>This page helps keep the bot awake. Do not close this page if you want to keep the bot running continuously.</p>
            <p>Features:</p>
            <ul>
                <li>Search and download songs from YouTube</li>
                <li>High quality MP3 format</li>
                <li>User statistics tracking</li>
                <li>User-friendly Arabic interface</li>
            </ul>
        </div>
        <div class="footer">
            Powered by Replit - Last ping: <span id="timestamp"></span>
            <script>
                document.getElementById('timestamp').textContent = new Date().toLocaleString();
                // تحديث الوقت كل دقيقة
                setInterval(function() {
                    document.getElementById('timestamp').textContent = new Date().toLocaleString();
                }, 60000);
            </script>
        </div>
    </div>
</body>
</html>
"""

class KeepAliveHandler(http.server.SimpleHTTPRequestHandler):
    """معالج HTTP المخصص للحفاظ على تشغيل البوت"""
    
    def log_message(self, format, *args):
        # تعطيل سجلات HTTP لتجنب ازدحام وحدة التحكم
        pass
    
    def do_GET(self):
        """التعامل مع طلبات GET"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(KEEP_ALIVE_HTML.encode())
        return

def start_keep_alive_server():
    """بدء خادم HTTP في خيط منفصل"""
    handler = KeepAliveHandler
    
    with socketserver.TCPServer(("", 8080), handler) as httpd:
        logger.info("Keep-alive server started on port 8080")
        httpd.serve_forever()

def keep_alive():
    """تشغيل خادم الـ keep-alive في خيط منفصل"""
    server_thread = threading.Thread(target=start_keep_alive_server)
    server_thread.daemon = True  # هذا يضمن إغلاق الخيط عند إغلاق البرنامج الرئيسي
    server_thread.start()
    logger.info("Keep-alive thread started")

# ==================== 
# فئة بوت التلغرام
# ====================

# حاول استيراد مكتبة التلغرام
try:
    import telegram
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
    )
except ImportError as e:
    logger.error(f"Failed to import python-telegram-bot: {e}")

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.youtube_service = YouTubeService()
        self.user_service = UserService()
        
        # قاموس لتخزين التنزيلات النشطة
        self.active_downloads = {}
        
        # رسالة الترحيب
        self.welcome_message = (
            "👋 *مرحباً بك في بوت البحث وتنزيل الأغاني!*\n\n"
            "هذا البوت يساعدك على البحث وتنزيل أغانيك المفضلة من يوتيوب بكل سهولة.\n\n"
            "*كيفية الاستخدام:*\n"
            "1️⃣ أرسل لي اسم الأغنية أو الفنان مباشرة (بدون أوامر)\n"
            "2️⃣ اختر من نتائج البحث\n"
            "3️⃣ انتظر حتى يتم تنزيل الأغنية وإرسالها لك\n\n"
            "*قواعد الاستخدام:*\n"
            "• يرجى احترام حقوق الملكية الفكرية\n"
            "• هذا البوت مخصص للاستخدام الشخصي فقط\n"
            "• المحتوى المنزل من يوتيوب يخضع لشروط استخدام يوتيوب\n\n"
            "للمساعدة، استخدم الأمر /help\n"
            "للتواصل مع المشرف: " + ADMIN_USERNAME
        )
        
        # رسالة المساعدة
        self.help_message = (
            "🆘 *مساعدة وتعليمات الاستخدام*\n\n"
            "*الأوامر المتاحة:*\n"
            "/start - بدء البوت وعرض رسالة الترحيب\n"
            "/help - عرض هذه المساعدة\n"
            "/contact - التواصل مع مشرف البوت\n\n"
            "*للبحث عن أغنية:*\n"
            "اكتب اسم الأغنية أو الفنان مباشرة بدون أي أوامر\n\n"
            "*مشاكل شائعة:*\n"
            "• إذا لم يجد البوت الأغنية، حاول كتابة اسمها بطريقة مختلفة\n"
            "• قد يستغرق تنزيل الملفات الكبيرة وقتاً أطول\n"
            "• الحد الأقصى لمدة الأغنية هو 10 دقائق\n\n"
            "*للتواصل مع المشرف:*\n"
            "يمكنك التواصل مباشرة مع " + ADMIN_USERNAME
        )

    def start(self, update, context):
        """معالجة أمر /start"""
        user = update.effective_user
        is_new_user = self.user_service.add_user(user)
        
        if is_new_user:
            self.notify_admin_new_user(user)
        
        update.message.reply_text(
            self.welcome_message, 
            parse_mode='Markdown'
        )

    def help(self, update, context):
        """معالجة أمر /help"""
        update.message.reply_text(
            self.help_message,
            parse_mode='Markdown'
        )

    def contact_admin(self, update, context):
        """معالجة أمر /contact"""
        update.message.reply_text(
            f"للتواصل مع مشرف البوت، يرجى إرسال رسالة إلى {ADMIN_USERNAME}",
            parse_mode='Markdown'
        )

    def stats(self, update, context):
        """معالجة أمر /stats"""
        user = update.effective_user
        if user.username and user.username == ADMIN_USERNAME.lstrip('@'):
            stats = self.user_service.get_stats()
            message = (
                f"📊 *إحصائيات البوت*\n\n"
                f"👥 *إجمالي المستخدمين:* {stats['total_users']}\n"
                f"🔍 *مستخدمون نشطون:* {stats['active_users']}\n"
                f"⬇️ *إجمالي التنزيلات:* {stats['total_downloads']}\n"
            )
            update.message.reply_text(message, parse_mode='Markdown')
        else:
            update.message.reply_text("⛔ هذا الأمر متاح فقط للمشرفين.")

    def notify_admin_new_user(self, user):
        """إرسال إشعار إلى قناة المشرف عن المستخدم الجديد"""
        stats = self.user_service.get_stats()
        message = (
            f"👤 *مستخدم جديد*\n\n"
            f"🆔 *معرّف المستخدم:* `{user.id}`\n"
            f"📛 *الاسم:* {user.first_name}"
        )
        
        if user.last_name:
            message += f" {user.last_name}"
        
        if user.username:
            message += f"\n🔖 *اسم المستخدم:* @{user.username}"
        
        message += f"\n\n📊 *إجمالي المستخدمين:* {stats['total_users']}"
        
        try:
            self.updater.bot.send_message(
                chat_id=NOTIFICATION_CHANNEL,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error sending notification to admin channel: {e}")

    def search_song(self, update, context):
        """معالجة رسالة المستخدم كبحث عن أغنية"""
        query = update.message.text.strip()
        
        # تحديث إحصائيات المستخدم
        user = update.effective_user
        self.user_service.add_user(user)  # ضمان وجود المستخدم
        self.user_service.update_user_stats(user.id, "search")
        
        # إرسال رسالة "جارٍ البحث"
        searching_message = update.message.reply_text(
            f"🔍 جارٍ البحث عن: *{query}*...",
            parse_mode='Markdown'
        )
        
        # البحث عن الأغاني
        songs = self.youtube_service.search_songs(query)
        
        if not songs:
            searching_message.edit_text(
                "❌ لم يتم العثور على نتائج. يرجى المحاولة بكلمات بحث مختلفة."
            )
            return
        
        # إنشاء لوحة مفاتيح مضمنة مع نتائج البحث
        keyboard = []
        for i, song in enumerate(songs):
            title = truncate_string(song['title'], 35)
            button_text = f"{i+1}. {title} ({song['duration_str']})"
            keyboard.append([
                InlineKeyboardButton(
                    button_text, 
                    callback_data=f"download_{song['video_id']}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # تعديل رسالة "جارٍ البحث" بالنتائج
        searching_message.edit_text(
            f"🎵 نتائج البحث لـ *{query}*\n"
            "اختر أغنية للتنزيل:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    def button_callback(self, update, context):
        """معالجة استجابات الأزرار"""
        query = update.callback_query
        query.answer()
        
        data = query.data
        
        if data.startswith("download_"):
            video_id = data.split("_")[1]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # تحديث الرسالة لإظهار أن التنزيل يبدأ
            try:
                query.edit_message_text(
                    "⏳ جارٍ بدء التنزيل، يرجى الانتظار..."
                    # لا نستخدم parse_mode هنا لتجنب أخطاء التنسيق
                )
            except Exception as e:
                logger.error(f"Error updating message: {e}")
            
            # إضافة إلى التنزيلات النشطة
            self.active_downloads[query.message.message_id] = {
                'user_id': query.from_user.id,
                'video_id': video_id,
                'progress': 0,
                'start_time': datetime.now(),
                'chat_id': query.message.chat_id
            }
            
            # إنشاء دالة رد الاتصال للتقدم
            message_id = query.message.message_id
            chat_id = query.message.chat_id
            
            def progress_callback(percent, downloaded, total):
                self.active_downloads[message_id]['progress'] = percent
            
            # بدء التنزيل في خيط منفصل
            def download_thread():
                try:
                    song_info, error = self.youtube_service.download_song(
                        video_url,
                        progress_callback
                    )
                    
                    # إزالة من التنزيلات النشطة
                    if message_id in self.active_downloads:
                        del self.active_downloads[message_id]
                    
                    if error:
                        try:
                            context.bot.edit_message_text(
                                chat_id=chat_id,
                                message_id=message_id,
                                text=f"❌ حدث خطأ أثناء التنزيل: {error}"
                                # لا نستخدم parse_mode هنا لتجنب أخطاء التنسيق
                            )
                        except Exception as e:
                            logger.error(f"Error updating error message: {e}")
                        return
                    
                    if not song_info or not os.path.exists(song_info['file_path']):
                        try:
                            context.bot.edit_message_text(
                                chat_id=chat_id,
                                message_id=message_id,
                                text="❌ فشل التنزيل. يرجى المحاولة مرة أخرى لاحقاً."
                                # لا نستخدم parse_mode هنا لتجنب أخطاء التنسيق
                            )
                        except Exception as e:
                            logger.error(f"Error updating failure message: {e}")
                        return
                    
                    # تجهيز النص مع تجنب الرموز الخاصة التي قد تسبب مشاكل في التنسيق
                    title_safe = song_info['title'].replace("*", "").replace("_", "").replace("`", "")
                    artist_safe = song_info['artist'].replace("*", "").replace("_", "").replace("`", "")
                    
                    # تحديث الرسالة لإظهار اكتمال التنزيل
                    try:
                        context.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text=f"✅ تم التنزيل بنجاح! جارٍ إرسال الملف...\n"
                                f"🎵 {title_safe}\n"
                                f"👤 الفنان: {artist_safe}\n"
                                f"⏱️ المدة: {format_duration(song_info['duration'])}\n"
                                f"📦 حجم الملف: {song_info['file_size_str']}"
                            # لا نستخدم parse_mode هنا لتجنب أخطاء التنسيق
                        )
                    except Exception as e:
                        logger.error(f"Error updating completion message: {e}")
                    
                    # إرسال ملف الصوت
                    try:
                        with open(song_info['file_path'], 'rb') as audio:
                            context.bot.send_audio(
                                chat_id=chat_id,
                                audio=audio,
                                title=title_safe,
                                performer=artist_safe,
                                caption=f"🎵 {title_safe}\n"
                                       f"👤 {artist_safe}\n\n"
                                       f"تم التنزيل بواسطة @{context.bot.username}"
                            )
                        
                        # تحديث إحصائيات المستخدم
                        self.user_service.update_user_stats(query.from_user.id, "download")
                        
                    except Exception as e:
                        logger.error(f"Error sending audio: {e}")
                        try:
                            context.bot.send_message(
                                chat_id=chat_id,
                                text=f"❌ حدث خطأ أثناء إرسال الملف، يرجى المحاولة مرة أخرى."
                            )
                        except Exception as send_error:
                            logger.error(f"Error sending error message: {send_error}")
                    
                    # حذف الملف المؤقت
                    try:
                        if os.path.exists(song_info['file_path']):
                            os.remove(song_info['file_path'])
                    except Exception as e:
                        logger.error(f"Error removing temp file: {e}")
                        
                except Exception as main_error:
                    logger.error(f"Critical error in download thread: {main_error}")
                    try:
                        context.bot.send_message(
                            chat_id=chat_id,
                            text="❌ حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى لاحقًا."
                        )
                    except:
                        pass
            
            # بدء التنزيل في خيط منفصل
            thread = threading.Thread(target=download_thread)
            thread.start()

    def update_download_progress(self, context):
        """تحديث رسائل تقدم التنزيل بشكل دوري"""
        for message_id, download in list(self.active_downloads.items()):
            try:
                # حساب الوقت المنقضي
                elapsed = (datetime.now() - download['start_time']).total_seconds()
                
                # تحديث رسالة التقدم كل 3 ثواني
                if download['progress'] > 0 and elapsed > 3:
                    try:
                        context.bot.edit_message_text(
                            chat_id=download['chat_id'],
                            message_id=message_id,
                            text=f"⏳ جارٍ التنزيل... {download['progress']:.1f}%"
                        )
                        # إعادة تعيين المؤقت
                        self.active_downloads[message_id]['start_time'] = datetime.now()
                    except Exception as edit_error:
                        # قد تكون هذه أخطاء شائعة، لا داعي لتسجيلها دائمًا
                        if "Message is not modified" not in str(edit_error):
                            logger.error(f"Error updating download progress: {edit_error}")
            except Exception as e:
                logger.error(f"Error in progress updater: {e}")

    def run(self):
        """تشغيل البوت"""
        try:
            # إنشاء المحدث وتمرير توكن البوت الخاص بك
            self.updater = Updater(self.token)
            
            # الحصول على المرسل لتسجيل المعالجات
            dp = self.updater.dispatcher
            
            # إضافة معالجات
            dp.add_handler(CommandHandler("start", self.start))
            dp.add_handler(CommandHandler("help", self.help))
            dp.add_handler(CommandHandler("contact", self.contact_admin))
            dp.add_handler(CommandHandler("stats", self.stats))
            
            # معالجة الرسائل كعمليات بحث عن الأغاني
            dp.add_handler(MessageHandler(Filters.text & ~Filters.command, self.search_song))
            
            # معالجة ردود الأزرار
            dp.add_handler(CallbackQueryHandler(self.button_callback))
            
            # إضافة مهمة لتحديث تقدم التنزيل
            self.updater.job_queue.run_repeating(self.update_download_progress, interval=3, first=0)
            
            # بدء البوت
            logger.info("Starting the bot...")
            self.updater.start_polling()
            
            # تشغيل البوت حتى الضغط على Ctrl-C
            self.updater.idle()
            
        except Exception as e:
            logger.error(f"Error starting the bot: {e}")

# ==================== 
# الدالة الرئيسية
# ====================

def main():
    """تشغيل بوت التلغرام."""
    logger.info("Starting Telegram music bot...")
    logger.info("Bot token: " + TELEGRAM_BOT_TOKEN[:5] + "..." + TELEGRAM_BOT_TOKEN[-5:])
    
    # بدء خادم keep-alive للحفاظ على تشغيل البوت
    keep_alive()
    logger.info("Keep-alive server activated")
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("No Telegram bot token provided. Please set the TELEGRAM_BOT_TOKEN environment variable.")
        sys.exit(1)
    
    retry_count = 0
    max_retries = 10
    retry_delay = 5  # ثوانٍ
    
    while True:
        try:
            # إنشاء وتشغيل البوت
            logger.info(f"Starting the bot. Attempt {retry_count + 1}/{max_retries if retry_count < max_retries else '∞'}")
            bot = TelegramBot(TELEGRAM_BOT_TOKEN)
            bot.run()
            # إذا وصلنا هنا، فهذا يعني أن البوت توقف بشكل طبيعي (مثل Ctrl+C)
            logger.info("Bot stopped normally.")
            break
            
        except Exception as e:
            retry_count += 1
            logger.error(f"Error running the bot: {e}")
            
            if retry_count < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds... ({retry_count}/{max_retries})")
                time.sleep(retry_delay)
                # زيادة فترة الانتظار تدريجيًا لتجنب الضغط على الخادم
                retry_delay = min(retry_delay * 1.5, 60)  # بحد أقصى 60 ثانية
            else:
                logger.info("Max retries reached. Switching to infinite retry mode with 60s delay.")
                # في حالة استنفاد محاولات إعادة المحاولة، نستمر بالمحاولة كل دقيقة
                time.sleep(60)
                # إعادة تعيين عداد المحاولات
                retry_count = max_retries

if __name__ == "__main__":
    main()
