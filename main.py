#!/usr/bin/env python
import os
import logging
import datetime
import json
import requests
import time

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# API Keys - مفاتيح واجهة برمجة التطبيقات
TELEGRAM_TOKEN = "7744505004:AAHg3bPPl2Cy_sD_yP1COePMBKHDjn3aEbk"  # توكن البوت من BotFather
GEMINI_API_KEY = "AIzaSyBb2nDNkhnQJf2R1fd0nmTZEs63NFN3Sis"  # مفتاح API لخدمة Gemini
ADMIN_ID = "7971415230"  # معرف المسؤول على تيليجرام
ADMIN_USERNAME = "Bilalja0"  # اسم المستخدم للمسؤول

# Telegram API URLs
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
GET_UPDATES_URL = f"{TELEGRAM_API_URL}/getUpdates"
SEND_MESSAGE_URL = f"{TELEGRAM_API_URL}/sendMessage"
SEND_CHAT_ACTION_URL = f"{TELEGRAM_API_URL}/sendChatAction"

# Gemini API URL - تحديث للنموذج الجديد
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"

# In-memory storage for user data
users = {}
last_update_id = 0

# Available languages
AVAILABLE_LANGUAGES = {
    "en": "English",
    "ar": "العربية"
}

# Text translations for bot messages
TRANSLATIONS = {
    "welcome_message": {
        "en": "*Welcome to Gemini AI Bot! 🤖*\n\nI'm your AI assistant powered by Google's Gemini AI. I can help answer questions, have conversations, and assist with various tasks.\n\nCommands:\n/start - Start the bot\n/help - Show help information\n/clear - Clear conversation context\n/admin - Contact admin\n/language - Switch language (English/Arabic)\n\n_Developed by @Bilalja0_",
        "ar": "*مرحباً بك في بوت جيميني للذكاء الاصطناعي! 🤖*\n\nأنا مساعدك الذكي المدعوم بواسطة جيميني من Google. يمكنني مساعدتك في الإجابة على الأسئلة وإجراء المحادثات والمساعدة في مختلف المهام.\n\nالأوامر:\n/start - بدء البوت\n/help - عرض معلومات المساعدة\n/clear - مسح سياق المحادثة\n/admin - الاتصال بالمسؤول\n/language - تغيير اللغة (الإنجليزية/العربية)\n\n_طُور بواسطة @Bilalja0_"
    },
    "help_text": {
        "en": "*Help Information 📚*\n\nHere's how to use this bot:\n\n1. Simply type your message to chat with the AI\n2. Use /clear to start a fresh conversation\n3. Use /language to switch between English and Arabic\n4. Use /admin to get admin contact information\n\nThis bot remembers your conversation history to provide contextual responses.",
        "ar": "*معلومات المساعدة 📚*\n\nإليك كيفية استخدام هذا البوت:\n\n1. ما عليك سوى كتابة رسالتك للدردشة مع الذكاء الاصطناعي\n2. استخدم /clear لبدء محادثة جديدة\n3. استخدم /language للتبديل بين اللغتين الإنجليزية والعربية\n4. استخدم /admin للحصول على معلومات الاتصال بالمسؤول\n\nيتذكر هذا البوت سجل محادثتك لتقديم ردود سياقية."
    },
    "context_cleared": {
        "en": "🧹 Conversation context has been cleared. Let's start fresh!",
        "ar": "🧹 تم مسح سياق المحادثة. لنبدأ من جديد!"
    },
    "contact_admin": {
        "en": "📞 To contact the admin, please reach out to @{admin}",
        "ar": "📞 للتواصل مع المسؤول، يرجى التواصل مع @{admin}"
    },
    "language_changed": {
        "en": "🌐 Language changed to English",
        "ar": "🌐 تم تغيير اللغة إلى العربية"
    },
    "unauthorized": {
        "en": "⛔ Sorry, you are not authorized to use this command.",
        "ar": "⛔ عذراً، غير مصرح لك باستخدام هذا الأمر."
    },
    "error_message": {
        "en": "❌ Sorry, something went wrong while generating a response. Please try again later.",
        "ar": "❌ عذراً، حدث خطأ أثناء إنشاء الرد. الرجاء المحاولة مرة أخرى لاحقاً."
    },
    "system_prompt": {
        "en": "You are an AI assistant named Gemini, powered by Google's Gemini AI technology. Be helpful, accurate, and friendly. Always respect user privacy. Don't make up information. If you don't know, say so. Respond in the same language the user is using.",
        "ar": "أنت مساعد ذكاء اصطناعي يسمى جيميني، مدعوم بتقنية جيميني من Google. كن مفيداً ودقيقاً وودوداً. احترم دائماً خصوصية المستخدم. لا تختلق معلومات. إذا كنت لا تعرف، قل ذلك. رد بنفس اللغة التي يستخدمها المستخدم."
    }
}

def get_text(key, language="en"):
    """Get text in the specified language."""
    if key not in TRANSLATIONS:
        # Fallback to a default message if key is not found
        return "Message not found"
    
    if language in TRANSLATIONS[key]:
        return TRANSLATIONS[key][language]
    else:
        # Fallback to English if the requested language is not available
        return TRANSLATIONS[key]["en"]

def get_user_data(users, user_id):
    """Get user data from the in-memory storage."""
    if user_id not in users:
        # Initialize with default values if user not found
        users[user_id] = {
            "name": "Unknown",
            "username": None,
            "language": "en",
            "context": [],
            "join_date": None
        }
    return users[user_id]

def clear_user_context(users, user_id):
    """Clear the conversation context for a user."""
    user_data = get_user_data(users, user_id)
    user_data["context"] = []
    return True

def add_message_to_context(users, user_id, role, content):
    """Add a message to the user's conversation context."""
    user_data = get_user_data(users, user_id)
    
    # Add the message to the context
    user_data["context"].append({
        "role": role,
        "content": content
    })
    
    # Limit context to the last 10 messages to avoid token limits
    if len(user_data["context"]) > 10:
        user_data["context"] = user_data["context"][-10:]
    
    return True

def get_user_count(users):
    """Get the total number of unique users."""
    return len(users)

def format_user_list(users):
    """Format the user list for display."""
    formatted_list = ""
    for user_id, user_data in users.items():
        name = user_data["name"] or "Unknown"
        username = user_data["username"] or "N/A"
        join_date = user_data["join_date"] or "Unknown"
        formatted_list += f"- *{name}* (@{username})\n  ID: `{user_id}`\n  Joined: {join_date}\n\n"
    return formatted_list

def send_message(chat_id, text, parse_mode=None):
    """Send a message to a specific chat."""
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    
    if parse_mode:
        payload["parse_mode"] = parse_mode
    
    response = requests.post(SEND_MESSAGE_URL, json=payload)
    return response.json()

def send_typing_action(chat_id):
    """Send a typing action to indicate the bot is generating a response."""
    payload = {
        "chat_id": chat_id,
        "action": "typing"
    }
    response = requests.post(SEND_CHAT_ACTION_URL, json=payload)
    return response.json()

def generate_gemini_response(prompt):
    """Generate a response using Gemini API."""
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }
    
    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 1024,
        }
    }
    
    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=data)
        
        if response.status_code != 200:
            logger.error(f"Gemini API error: {response.text}")
            # Fallback to basic responses if API fails
            has_arabic = any(ord(c) > 127 for c in prompt)
            if has_arabic:
                return "مرحباً! أنا مساعد الذكاء الاصطناعي جيميني. نواجه بعض المشاكل التقنية حالياً، لكنني سأحاول مساعدتك."
            else:
                return "Hello! I am Gemini AI assistant. We're experiencing some technical issues at the moment, but I'll try to help you."
        
        response_json = response.json()
        
        # Extract the text from the response
        if "candidates" in response_json and len(response_json["candidates"]) > 0:
            candidate = response_json["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                parts = candidate["content"]["parts"]
                if len(parts) > 0 and "text" in parts[0]:
                    return parts[0]["text"]
                    
        # If we reach here, something went wrong with parsing the response
        logger.error(f"Failed to extract text from Gemini API response: {response_json}")
        return "I'm having trouble generating a proper response right now. Please try again later."
    
    except Exception as e:
        logger.error(f"Exception while calling Gemini API: {e}")
        # Fallback response
        has_arabic = any(ord(c) > 127 for c in prompt)
        if has_arabic:
            return "عذراً، حدث خطأ أثناء محاولة التواصل مع خدمة الذكاء الاصطناعي. الرجاء المحاولة مرة أخرى لاحقاً."
        else:
            return "Sorry, an error occurred while trying to communicate with the AI service. Please try again later."

def process_update(update):
    """Process a single update from Telegram."""
    global users
    
    # Skip updates without messages
    if "message" not in update:
        return
    
    message = update["message"]
    
    # Skip messages without text
    if "text" not in message:
        return
    
    chat_id = message["chat"]["id"]
    user = message["from"]
    user_id = str(user["id"])
    text = message["text"]
    
    # Initialize user data if it doesn't exist
    if user_id not in users:
        first_name = user.get("first_name", "Unknown")
        username = user.get("username", None)
        users[user_id] = {
            "name": first_name,
            "username": username,
            "language": "en",  # Default language
            "context": [],
            "join_date": datetime.datetime.now().isoformat()
        }
        logger.info(f"New user: {first_name} (ID: {user_id})")
    
    # Handle commands
    if text.startswith("/"):
        command = text.split()[0].lower()
        
        if command == "/start":
            handle_start(user_id, chat_id)
        elif command == "/help":
            handle_help(user_id, chat_id)
        elif command == "/clear":
            handle_clear(user_id, chat_id)
        elif command == "/admin":
            handle_admin(user_id, chat_id)
        elif command == "/language":
            handle_language(user_id, chat_id)
        elif command == "/stats":
            handle_stats(user_id, chat_id)
        else:
            # Unknown command, treat as normal message
            handle_normal_message(user_id, chat_id, text)
    else:
        # Normal message
        handle_normal_message(user_id, chat_id, text)

def handle_start(user_id, chat_id):
    """Handle /start command."""
    user_language = users[user_id]["language"]
    welcome_message = get_text("welcome_message", user_language)
    send_message(chat_id, welcome_message, parse_mode="Markdown")

def handle_help(user_id, chat_id):
    """Handle /help command."""
    user_data = get_user_data(users, user_id)
    help_text = get_text("help_text", user_data["language"])
    send_message(chat_id, help_text, parse_mode="Markdown")

def handle_clear(user_id, chat_id):
    """Handle /clear command."""
    clear_user_context(users, user_id)
    user_language = users[user_id]["language"]
    clear_message = get_text("context_cleared", user_language)
    send_message(chat_id, clear_message)

def handle_admin(user_id, chat_id):
    """Handle /admin command."""
    user_language = users[user_id]["language"]
    admin_message = get_text("contact_admin", user_language).format(admin=ADMIN_USERNAME)
    send_message(chat_id, admin_message)

def handle_language(user_id, chat_id):
    """Handle /language command."""
    user_data = get_user_data(users, user_id)
    
    # Toggle between English and Arabic
    current_language = user_data["language"]
    new_language = "ar" if current_language == "en" else "en"
    
    # Update the user's language preference
    users[user_id]["language"] = new_language
    
    language_changed_message = get_text("language_changed", new_language)
    send_message(chat_id, language_changed_message)

def handle_stats(user_id, chat_id):
    """Handle /stats command (admin only)."""
    # Check if the user is the admin
    if user_id != ADMIN_ID:
        user_language = users[user_id]["language"]
        unauthorized_message = get_text("unauthorized", user_language)
        send_message(chat_id, unauthorized_message)
        return
    
    # Admin-only statistics
    total_users = get_user_count(users)
    user_list = format_user_list(users)
    
    stats_message = f"📊 *User Statistics*\n\n"
    stats_message += f"Total Users: {total_users}\n\n"
    stats_message += "User List:\n"
    stats_message += user_list
    
    send_message(chat_id, stats_message, parse_mode="Markdown")

def handle_normal_message(user_id, chat_id, text):
    """Handle normal (non-command) messages."""
    user_data = get_user_data(users, user_id)
    
    # Add message to context
    add_message_to_context(users, user_id, "user", text)
    
    # Prepare conversation context
    conversation_history = "\n".join([
        f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
        for msg in user_data["context"]
    ])
    
    # Set system prompt based on user's language
    system_prompt = get_text("system_prompt", user_data["language"])
    
    try:
        # Send typing action
        send_typing_action(chat_id)
        
        # Generate response using Gemini API
        prompt = f"{system_prompt}\n\nConversation history:\n{conversation_history}\n\nUser: {text}\nAssistant:"
        response_text = generate_gemini_response(prompt)
        
        # Add response to context
        add_message_to_context(users, user_id, "assistant", response_text)
        
        # Send response
        send_message(chat_id, response_text)
        
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        error_message = get_text("error_message", user_data["language"])
        send_message(chat_id, error_message)

def main():
    """Main bot function."""
    global last_update_id
    
    logger.info("Starting Gemini AI Telegram Bot...")
    
    # بدء عملية البوت - لا حاجة للتحقق من المتغيرات لأنها موجودة بالفعل في الكود
    
    # Main bot loop
    while True:
        try:
            # Get updates from Telegram
            params = {
                "offset": last_update_id + 1,
                "timeout": 30
            }
            response = requests.get(GET_UPDATES_URL, params=params)
            
            if response.status_code != 200:
                logger.error(f"Error getting updates: {response.text}")
                time.sleep(5)
                continue
            
            updates = response.json()
            
            if not updates.get("ok", False):
                logger.error(f"Error in Telegram API: {updates}")
                time.sleep(5)
                continue
            
            # Process updates
            for update in updates.get("result", []):
                process_update(update)
                last_update_id = max(last_update_id, update["update_id"])
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error: {e}")
            time.sleep(5)
        
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            time.sleep(5)

# تعليمات التشغيل
'''
كيفية استخدام هذا البوت:

1. البوت جاهز للاستخدام مباشرة، جميع المفاتيح مضمنة في الكود
2. ببساطة قم بتشغيل البوت باستخدام: python main.py
3. للتواصل مع البوت، افتح تطبيق تيليجرام وابحث عن @GeminiAI_Bot_by_bilal

الأوامر المتاحة:
- /start - بدء استخدام البوت
- /help - عرض المساعدة
- /clear - مسح سياق المحادثة
- /admin - الاتصال بالمسؤول
- /language - تغيير اللغة (الإنجليزية/العربية)
- /stats - عرض إحصائيات المستخدمين (للمسؤول فقط)

ملاحظات:
- لا تحتاج إلى تثبيت أي مكتبات إضافية، فقط المكتبات القياسية المضمنة مع Python (requests, json, time, logging)
- يتم تخزين بيانات المستخدمين في الذاكرة، لذا ستفقد هذه البيانات عند إعادة تشغيل البوت
- يدعم البوت اللغتين العربية والإنجليزية، ويمكن تغيير اللغة باستخدام أمر /language
'''

if __name__ == "__main__":
    print("=================================================================================")
    print("Gemini AI Telegram Bot - by @Bilalja0")
    print("=================================================================================")
    print("Bot is configured with the following:")
    print(f"- TELEGRAM_TOKEN: {TELEGRAM_TOKEN[:5]}...{TELEGRAM_TOKEN[-5:]}")
    print(f"- GEMINI_API_KEY: {GEMINI_API_KEY[:5]}...{GEMINI_API_KEY[-5:]}")
    print(f"- ADMIN_ID: {ADMIN_ID}")
    print("=================================================================================")
    print("Starting bot... Press Ctrl+C to stop.")
    print("=================================================================================")
    main()
