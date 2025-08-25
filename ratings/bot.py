from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from django.conf import settings
from .models import RoadRating

ASK_NAME, ASK_RATING, ASK_COMMENT = range(3)

# init application
application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Which road do you want to rate?")
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["road_name"] = update.message.text
    reply_keyboard = [["1", "2", "3", "4", "5"]]
    await update.message.reply_text(
        "Please rate the road (1-5):",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return ASK_RATING

async def ask_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["rating"] = int(update.message.text)
    await update.message.reply_text("Any comments?")
    return ASK_COMMENT

async def ask_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comment = update.message.text
    road_name = context.user_data["road_name"]
    rating = context.user_data["rating"]

    RoadRating.objects.create(
        road_name=road_name,
        rating=rating,
        comment=comment,
        # user_id=update.effective_user.id,
    )

    await update.message.reply_text("✅ Thanks! Your feedback has been saved.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
        ASK_RATING: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_rating)],
        ASK_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_comment)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

application.add_handler(conv_handler)
