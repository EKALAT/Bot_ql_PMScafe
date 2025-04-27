import os
from dotenv import load_dotenv

# Load biến môi trường
load_dotenv()

# Token của bot Telegram
BOT_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not BOT_TOKEN:
    # Fallback to direct token if not in environment variables
    BOT_TOKEN = '8111919258:AAGMe6AV3qOoqq3SVpMvpIR_9v7ja5MWApQ'

# ID của nhóm Telegram để gửi thông báo
GROUP_CHAT_ID = os.getenv('GROUP_CHAT_ID', '4770037508') 