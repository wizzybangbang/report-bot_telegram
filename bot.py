import os
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("8777636577:AAFgMVErnjcqHzRL36YYUkeJq6oAVhleA-c")
GROUP_ID = int(os.environ.get("-5122038345"))

ASKING_NAME, ASKING_ORDER, ASKING_ISSUE = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I'm here to help with order issues.\n\nWhat's your name?")
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
    user = update.message.from_user

    report = (
        f"🚨 NEW ORDER REPORT\n\n"
        f"👤 Name: {context.user_data['name']}\n"
        f"📦 Order: {context.user_data['order']}\n"
        f"❗ Issue: {context.user_data['issue']}\n"
        f"🔗 Telegram: @{user.username or 'no username'}\n"
        f"🆔 User ID: {user.id}"
    )

    await context.bot.send_message(chat_id=GROUP_ID, text=report)
    await update.message.reply_text("✅ Your report has been submitted! We'll get back to you soon.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

app = ApplicationBuilder().token(BOT_TOKEN).build()

conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        ASKING_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_order)],
        ASKING_ISSUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_issue)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app.add_handler(conv)
app.run_polling()