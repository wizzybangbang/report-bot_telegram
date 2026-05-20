import os
import logging
import threading
from flask import Flask
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROUP_ID_RAW = os.environ.get("GROUP_ID")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing")

if not GROUP_ID_RAW:
    raise ValueError("GROUP_ID is missing")

GROUP_ID = int(GROUP_ID_RAW)

ASKING_NAME, ASKING_ORDER, ASKING_ISSUE = range(3)

web_app = Flask(__name__)

@web_app.route("/")
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! I'm here to help with order issues.\n\nWhat's your name?"
    )
    return ASKING_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("What's your order ID or product name?")
    return ASKING_ORDER

async def get_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["order"] = update.message.text
    await update.message.reply_text("What's the issue with your order?")
    return ASKING_ISSUE

async def get_issue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["issue"] = update.message.text
    user = update.effective_user

    report = (
        "🚨 NEW ORDER REPORT\n\n"
        f"👤 Name: {context.user_data['name']}\n"
        f"📦 Order/Product: {context.user_data['order']}\n"
        f"❗ Issue: {context.user_data['issue']}\n"
        f"🔗 Telegram: @{user.username or 'no username'}\n"
        f"🆔 User ID: {user.id}"
    )

    await context.bot.send_message(chat_id=GROUP_ID, text=report)

    await update.message.reply_text(
        "✅ Your report has been submitted! We'll get back to you soon."
    )

    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Cancelled.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASKING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)
            ],
            ASKING_ORDER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_order)
            ],
            ASKING_ISSUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_issue)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)

    print("Telegram bot is running...")
    app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    run_bot()
