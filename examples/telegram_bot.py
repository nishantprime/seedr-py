"""
Seedr.cc Telegram Bot Example
==============================
A feature-complete Telegram bot that allows users to:
- Send magnet links or upload .torrent files to queue downloads on Seedr.
- Check real-time cloud storage quota.
- List cloud folders and files with direct CDN download & streaming links.
- Generate one-click folder ZIP download links (zero mCaptcha).

Requirements:
    pip install seedr-py pyTelegramBotAPI python-dotenv

Usage:
    1. Set your credentials in environment variables or a .env file:
       TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
       SEEDR_EMAIL="your_seedr_email@example.com"
       SEEDR_PASSWORD="your_seedr_password"

    2. Run the bot:
       python telegram_bot.py
"""

import os
import time
import telebot
from telebot import types
from dotenv import load_dotenv

from seedr_py import (
    SeedrClient,
    AuthenticationError,
    TorrentError,
    NotFoundError,
    format_bytes
)

load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
SEEDR_EMAIL = os.getenv("SEEDR_EMAIL", "YOUR_SEEDR_EMAIL_HERE")
SEEDR_PASSWORD = os.getenv("SEEDR_PASSWORD", "YOUR_SEEDR_PASSWORD_HERE")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# Helper to maintain an active Seedr client
_seedr_client = None
_last_auth_time = 0

def get_seedr() -> SeedrClient:
    """Returns or refreshes the SeedrClient connection."""
    global _seedr_client, _last_auth_time
    now = time.time()
    # Re-authenticate every 2 hours to keep session fresh
    if _seedr_client is None or (now - _last_auth_time > 7200):
        _seedr_client = SeedrClient.from_password(SEEDR_EMAIL, SEEDR_PASSWORD)
        _last_auth_time = now
    return _seedr_client


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "⚡ <b>Seedr Cloud Downloader Bot</b>\n\n"
        "Send me any <b>magnet link</b> or upload a <b>.torrent file</b>, "
        "and I will fetch it to your Seedr cloud instantly!\n\n"
        "<b>Available Commands:</b>\n"
        "• /storage - Check cloud storage and bandwidth\n"
        "• /list - Browse cloud folders, files, and active transfers\n"
        "• /zip &lt;folder_id&gt; - Get instant folder ZIP download link\n"
        "• /help - Show this guide"
    )
    bot.reply_to(message, welcome_text)


@bot.message_handler(commands=['storage'])
def check_storage(message):
    try:
        client = get_seedr()
        quota = client.get_quota()
        
        reply = (
            "📊 <b>Seedr Cloud Storage</b>\n\n"
            f"• <b>Used:</b> {quota.space_used_formatted} / {quota.space_max_formatted} ({quota.space_pct}%)\n"
            f"• <b>Bandwidth:</b> {format_bytes(quota.bandwidth_used)}\n"
            f"• <b>Account:</b> {'Premium 🌟' if quota.is_premium else 'Free'}"
        )
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, f"❌ <b>Error checking quota:</b> {e}")


@bot.message_handler(commands=['list'])
def list_files(message):
    try:
        client = get_seedr()
        folder = client.get_folder(0)  # Root folder
        
        lines = ["📂 <b>Seedr Cloud Directory</b>\n"]
        
        # 1. Active downloading torrents
        if folder.tasks:
            lines.append("⚡ <b>Active Transfers:</b>")
            for t in folder.tasks:
                speed = f"{t.download_rate / 1024:.1f} KB/s" if t.download_rate else "Queued"
                lines.append(f"  • {t.name} [{t.progress}% @ {speed}]")
            lines.append("")

        # 2. Subfolders
        if folder.folders:
            lines.append("📁 <b>Folders:</b>")
            for fo in folder.folders:
                lines.append(f"  • <b>{fo.name}</b> ({fo.size_formatted}) — ID: <code>{fo.id}</code>")
                lines.append(f"    👉 Get ZIP: <code>/zip {fo.id}</code>")
            lines.append("")

        # 3. Individual files
        if folder.files:
            lines.append("📄 <b>Files:</b>")
            for fi in folder.files:
                icon = "🎬" if fi.is_video else "📄"
                lines.append(f"  • {icon} <b>{fi.name}</b> ({fi.size_formatted})")
                lines.append(f"    👉 Download: <code>/dl {fi.id}</code>")
            lines.append("")

        if not folder.folders and not folder.files and not folder.tasks:
            lines.append("<i>Your cloud storage is currently empty.</i>")

        bot.reply_to(message, "\n".join(lines))
    except Exception as e:
        bot.reply_to(message, f"❌ <b>Error listing files:</b> {e}")


@bot.message_handler(commands=['zip'])
def get_zip_link(message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ Usage: <code>/zip &lt;folder_id&gt;</code>\nExample: <code>/zip 1438069</code>")
        return

    folder_id = parts[1].strip()
    if not folder_id.isdigit():
        bot.reply_to(message, "❌ Invalid folder ID. Must be a number.")
        return

    status_msg = bot.reply_to(message, "⏳ Generating signed ZIP link from Seedr CDN...")
    try:
        client = get_seedr()
        archive = client.get_folder_zip_url(int(folder_id))
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📦 Download Full ZIP", url=archive.url))
        
        bot.edit_message_text(
            f"✅ <b>Folder ZIP Ready!</b>\n\nZero-mCaptcha direct link generated from Seedr CDN.\nClick below to download:",
            chat_id=status_msg.chat.id,
            message_id=status_msg.message_id,
            reply_markup=markup
        )
    except Exception as e:
        bot.edit_message_text(f"❌ <b>Failed to create archive:</b> {e}", chat_id=status_msg.chat.id, message_id=status_msg.message_id)


@bot.message_handler(commands=['dl'])
def get_file_link(message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        bot.reply_to(message, "⚠️ Usage: <code>/dl &lt;file_id&gt;</code>")
        return

    file_id = int(parts[1])
    try:
        client = get_seedr()
        dl = client.get_file_url(file_id)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬇️ Direct Download", url=dl.url))
        
        # Check if video streaming is available
        try:
            stream = client.get_video_stream(file_id)
            if stream.hls_url:
                markup.add(types.InlineKeyboardButton("▶️ HLS Stream URL", url=stream.hls_url))
        except Exception:
            pass

        bot.reply_to(message, f"📄 <b>{dl.name}</b>\nDirect high-speed CDN link ready:", reply_markup=markup)
    except Exception as e:
        bot.reply_to(message, f"❌ <b>Error:</b> {e}")


@bot.message_handler(func=lambda msg: msg.text and msg.text.strip().startswith("magnet:?"))
def handle_magnet(message):
    magnet = message.text.strip()
    status_msg = bot.reply_to(message, "⏳ Connecting to Seedr and queuing magnet...")

    try:
        client = get_seedr()
        res = client.add_magnet(magnet)
        
        title = res.get("title") or "Torrent"
        bot.edit_message_text(
            f"⚡ <b>Magnet Queued Successfully!</b>\n\n"
            f"• <b>Title:</b> {title}\n"
            f"• Seedr is fetching and caching the files in the cloud.\n"
            f"• Use /list to check transfer progress.",
            chat_id=status_msg.chat.id,
            message_id=status_msg.message_id
        )
    except TorrentError as e:
        bot.edit_message_text(f"❌ <b>Torrent Error:</b> {e}", chat_id=status_msg.chat.id, message_id=status_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ <b>Unexpected Error:</b> {e}", chat_id=status_msg.chat.id, message_id=status_msg.message_id)


@bot.message_handler(content_types=['document'])
def handle_torrent_document(message):
    if not message.document.file_name.lower().endswith(".torrent"):
        return

    status_msg = bot.reply_to(message, "⏳ Downloading `.torrent` file and extracting magnet...")
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_bytes = bot.download_file(file_info.file_path)

        client = get_seedr()
        res = client.add_torrent_file(downloaded_bytes)
        
        title = res.get("title") or message.document.file_name
        bot.edit_message_text(
            f"⚡ <b>Torrent Uploaded & Queued!</b>\n\n"
            f"• <b>File:</b> {title}\n"
            f"• Seedr is downloading the torrent to your cloud.\n"
            f"• Use /list to inspect progress and download completed files.",
            chat_id=status_msg.chat.id,
            message_id=status_msg.message_id
        )
    except Exception as e:
        bot.edit_message_text(f"❌ <b>Failed to process torrent file:</b> {e}", chat_id=status_msg.chat.id, message_id=status_msg.message_id)


if __name__ == "__main__":
    print("Seedr Telegram Bot is running...")
    bot.infinity_polling()
