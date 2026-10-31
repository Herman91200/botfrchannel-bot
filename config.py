import os

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
PLACE_ID = int(os.getenv("PLACE_ID", "1962086868"))
