
import datetime
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackContext
import os

daysSinceDrunk = 0
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def send_scheduled_message(context: CallbackContext):
    global daysSinceDrunk
    channel_username = '-1002157531667'  
    message = f"Good Morning Everyone! I am sober for {daysSinceDrunk} days! Cheers to that! 🍻 "
    await context.bot.send_message(chat_id=channel_username, text=message)
    daysSinceDrunk += 1

async def send_drunk_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel_username = '-1002157531667'  
    message = f"Good Morning Everyone! I am sober for {daysSinceDrunk} days! Cheers to that! 🍻 "
    await context.bot.send_message(chat_id=channel_username, text=message)
    
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Bot is running! Amen 😇")

async def drunk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global daysSinceDrunk
    if update.effective_chat.id == 716853175:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are drunk 🍾 Resetting back to 0 days...")
        daysSinceDrunk = 0
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not Kai Sheng.. wya doing here.... 😡")

def main():
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)  

    drunk_handler = CommandHandler('drunk', drunk)
    application.add_handler(drunk_handler)

    send_drunk_message_handler = CommandHandler('sendDrunk', send_drunk_message)
    application.add_handler(send_drunk_message_handler)

    # Schedule the job to run at a specific time
    application.job_queue.run_daily(send_scheduled_message, time=datetime.time(hour=10, minute=10, tzinfo=datetime.timezone(offset=datetime.timedelta(hours=8))))

    application.run_polling(poll_interval=10.0)

if __name__ == '__main__':
    main()