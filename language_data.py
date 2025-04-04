"""
Language data for multilingual support in the Telegram bot.
"""

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