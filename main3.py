from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackContext, ContextTypes
import datetime
import asyncio

# Define exam dates
EXAMS = {
    "😖JEE MAIN APRIL ATTEMPT": datetime.date(2025, 4, 1),
    "🥵JEE ADVANCED 2025": datetime.date(2025, 5, 18),
    "😐BITSAT 2025": datetime.date(2025, 5, 26),
    "🙄COMEDK 2025": datetime.date(2025, 5, 10),
    "🥺NEET 2025": datetime.date(2025, 5, 4),
    "😢CUET 2025": datetime.date(2025, 5, 15),
}

CHANNEL_ID = "@HIDDEN_OFFICIALS_3"  # Replace with your actual channel username


def days_left(exam_date):
    today = datetime.date.today()
    delta = exam_date - today
    return delta.days


def get_exam_countdown():
    countdown_text = "<b>🥶 𝔼𝕏𝔸𝕄 ℂ𝕆𝕌ℕ𝕋𝔻𝕆𝕎ℕ 😨\n⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆\n⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆⋆</b>\n"
    for exam, date in EXAMS.items():
        days = days_left(date)
        if days >= 0:
            countdown_text += f"<b>{exam}</b>\n<b>🏅 𝗗𝗮𝘆𝘀 »» <i>{days} left </i>\n-------------------------------------</b>\n"
    return countdown_text


async def send_countdown(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    await bot.send_message(chat_id=CHANNEL_ID, text=get_exam_countdown(), parse_mode="HTML")


async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(text=get_exam_countdown(), parse_mode="HTML")
    await send_countdown(context)


async def daily_update(context: ContextTypes.DEFAULT_TYPE):
    while True:
        await send_countdown(context)
        now = datetime.datetime.now()
        tomorrow = datetime.datetime.combine(now.date() + datetime.timedelta(days=1), datetime.time(0, 0))
        sleep_time = (tomorrow - now).total_seconds()
        await asyncio.sleep(sleep_time)  # Sleep until midnight


def main():
    TOKEN = "6811502626:AAG9xT3ZQUmg6CrdIPvQ0kCRJ3W5QL-fuZs"
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    
    # Run the daily update job every 24 hours, starting from 5 seconds after the bot starts
    application.job_queue.run_once(daily_update, when=datetime.timedelta(seconds=54000))
    
    # Send immediate countdown message when the bot starts
    application.job_queue.run_once(lambda context: send_countdown(context), when=datetime.timedelta(seconds=2))
    
    application.run_polling()


if __name__ == "__main__":
    main()
