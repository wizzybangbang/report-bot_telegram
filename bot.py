import os
import asyncio
import logging
import threading
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
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

ASKING_TYPE, ASKING_ISSUE = range(2)

web_app = Flask(__name__)

@web_app.route("/")
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Order Issue"], ["Other"]]

    await update.message.reply_text(
        "Welcome to the support form.\n\nChoose report type:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )

    return ASKING_TYPE

async def get_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report_type = update.message.text
    context.user_data["report_type"] = report_type

    if report_type == "Order Issue":
        await update.message.reply_text(
            "kindly fill this out:\n\n"
            "account availed:\n"
            "email/username:\n"
            "profile/pin if applicable:\n"
            "date availed:\n"
            "months availed:\n"
            "issue encountered:\n\n"
            "please attach screenshot of the issue + vouch",
            reply_markup=ReplyKeyboardRemove()
        )
        return ASKING_ISSUE

    await update.message.reply_text(
        "Please describe your concern.",
        reply_markup=ReplyKeyboardRemove()
    )

    return ASKING_ISSUE

async def get_issue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    report_type = context.user_data.get("report_type", "Unknown")

    if update.message.text:
        report_text = update.message.text
    else:
        report_text = "[non-text report submitted]"

    report = (
        "🚨 NEW REPORT\n\n"
        f"📂 Type: {report_type}\n"
        f"❗ Report:\n{report_text}\n\n"
        f"🔗 Username: @{user.username or 'no username'}\n"
        f"🆔 User ID: {user.id}"
    )

    await context.bot.send_message(chat_id=GROUP_ID, text=report)

    if update.message.photo:
        await context.bot.forward_message(
            chat_id=GROUP_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )

    await update.message.reply_text(
        "✅ Your report has been submitted successfully."
    )

    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "❌ Report cancelled.",
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASKING_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_type)
            ],
            ASKING_ISSUE: [
                MessageHandler(filters.ALL & ~filters.COMMAND, get_issue)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)

    print("Telegram bot is running...")
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    run_bot()
