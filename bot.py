import os
import asyncio
import logging
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

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

ORDER_FORM = (
    "kindly fill this out:\n\n"
    "account availed:\n"
    "email/username:\n"
    "profile/pin if applicable:\n"
    "date availed:\n"
    "months availed:\n"
    "issue encountered:\n\n"
    "please attach screenshot of the issue + vouch"
)

OTHER_FORM = (
    "Please describe your concern using this format:\n\n"
    "subject:\n"
    "details:\n"
    "proof/screenshots if applicable:\n\n"
    "Please be as detailed as possible."
)

REQUIRED_ORDER_FIELDS = [
    "account availed:",
    "email/username:",
    "profile/pin if applicable:",
    "date availed:",
    "months availed:",
    "issue encountered:",
]

class Ping(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"alive")

    def log_message(self, *args):
        pass

def start_ping_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("", port), Ping)
    server.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Order Issue"], ["Other"]]

    await update.message.reply_text(
        "Welcome to the support form.\n\nChoose report type:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )

    return ASKING_TYPE

async def get_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report_type = update.message.text

    if report_type not in ["Order Issue", "Other"]:
        await update.message.reply_text(
            "Please choose one of the buttons: Order Issue or Other."
        )
        return ASKING_TYPE

    context.user_data["report_type"] = report_type

    if report_type == "Order Issue":
        await update.message.reply_text(
            ORDER_FORM,
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await update.message.reply_text(
            OTHER_FORM,
            reply_markup=ReplyKeyboardRemove(),
        )

    return ASKING_ISSUE

async def get_issue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    report_type = context.user_data.get("report_type", "Unknown")

    report_text = update.message.text or update.message.caption or ""

    if report_type == "Order Issue":
        missing_fields = [
            field for field in REQUIRED_ORDER_FIELDS
            if field.lower() not in report_text.lower()
        ]

        if missing_fields:
            await update.message.reply_text(
                "❌ Please copy and fill out the full form before submitting:\n\n"
                f"{ORDER_FORM}"
            )
            return ASKING_ISSUE

    if not report_text and not (
        update.message.photo or update.message.video or update.message.document
    ):
        await update.message.reply_text(
            "❌ Please send a written report or attach proof."
        )
        return ASKING_ISSUE

    report = (
        "🚨 NEW REPORT\n\n"
        f"📂 Type: {report_type}\n"
        f"❗ Report:\n{report_text or '[media/proof attached]'}\n\n"
        f"🔗 Username: @{user.username or 'no username'}\n"
        f"🆔 User ID: {user.id}"
    )

    await context.bot.send_message(chat_id=GROUP_ID, text=report)

    if update.message.photo or update.message.video or update.message.document:
        await context.bot.forward_message(
            chat_id=GROUP_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
        )

    await update.message.reply_text("✅ Your report has been submitted successfully.")

    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "❌ Report cancelled.",
        reply_markup=ReplyKeyboardRemove(),
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
        allow_reentry=True,
    )

    app.add_handler(conv)

    print("Telegram bot is running...")
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    Thread(target=start_ping_server, daemon=True).start()
    run_bot()
