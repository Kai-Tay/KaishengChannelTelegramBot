import datetime
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackContext, MessageHandler, filters
import os
import boto3
import json
from dotenv import load_dotenv
import requests
import random
import os

# Load environment variables
load_dotenv()

daysSinceDrunk = 0
europeCountdown = 0
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Add AWS configuration with debugging
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
SQS_QUEUE_URL = os.getenv('SQS_QUEUE_URL')

# Create SQS client with credentials
sqs = boto3.client(
    'sqs',
    region_name="ap-southeast-1",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


# Helper functions
def get_info():
    daysSinceDrunk = 0
    if not os.path.exists('daysSinceDrunk.txt'):
        with open('daysSinceDrunk.txt', 'w') as file:
            file.write(str(daysSinceDrunk))
    else:
        with open('daysSinceDrunk.txt', 'r') as file:
            line = file.readline()
            daysSinceDrunk = int(line.strip()) if line else 0
    return daysSinceDrunk

def get_europe_countdown():
    europe_target_date = datetime.date(2026, 1, 26)
    singapore_tz = datetime.timezone(datetime.timedelta(hours=8))
    today = datetime.datetime.now(singapore_tz).date()
    europeCountdown = (europe_target_date - today).days
    return europeCountdown

async def get_qotd():
    response = sqs.receive_message(
        QueueUrl=SQS_QUEUE_URL,
        MaxNumberOfMessages=1,
        VisibilityTimeout=60
    )

    if 'Messages' in response:
        message = response['Messages'][0]
        quote = json.loads(message['Body'])['quote']
        user = json.loads(message['Body'])['added_by']
        sqs.delete_message(
            QueueUrl=SQS_QUEUE_URL,
            ReceiptHandle=message['ReceiptHandle']
        )
        return quote, user
    else:
        # # Retrieve the quote from api
        # response = requests.get('https://api.quotable.io/quotes/random?tags=motivational%7Csuccess',verify=False)
        # body = response.json()[0]
        # user = body['author']
        # quote = body['content']
        # RANDOMLY CHOOSE FROM lany.txt
        with open('lany.txt', 'r') as file:
            lines = file.readlines()
        quote = random.choice(lines)
        user = 'LANY'

        return quote, user
    

# Scheduled message
async def send_scheduled_message(context: CallbackContext):
    global daysSinceDrunk

    # Get the quote of the day
    qotd, user   = await get_qotd()
    europeCountdown = get_europe_countdown()

    # Send the message to the channel
    channel_username = '-1002157531667'  
    message = f"Good Morning Everyone! I am sober for {daysSinceDrunk} days! Cheers to that! 🍻 \n\n 🥦 T-{europeCountdown} DAYS TO EUROPE 🥳 - GET YO ASS READY FOR BROCOLLI UNIVERISITY 🥦 \n\n{qotd} - {user}"
    await context.bot.send_message(chat_id=channel_username, text=message)

    # Update the daysSinceDrunk.txt file
    with open('daysSinceDrunk.txt', 'w') as file:
        file.write(str(daysSinceDrunk))

    # Increment the daysSinceDrunk
    daysSinceDrunk += 1

# Commands
async def send_drunk_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    qotd, user   = await get_qotd()
    message = f"Good Morning Everyone! I am sober for {daysSinceDrunk} days! Cheers to that! 🍻 \n\n{qotd} - {user}"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Bot is running! Amen 😇")

async def drunk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global daysSinceDrunk
    if update.effective_chat.id == 716853175:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are drunk 🍾 Resetting back to 0 days...")
        with open('daysSinceDrunk.txt', 'w') as file:
            file.write(str(0))
        daysSinceDrunk = 0
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not Kai Sheng.. wya doing here.... 😡")

async def qotd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please provide a quote after the command. Example: /qotd Your quote here"
        )
        return

    quote = ' '.join(context.args)
    user = update.effective_user.username or str(update.effective_user.id)
    
    quote_entry = {
        'quote': quote,
        'added_by': user,
    }

    try:
        # Send message to SQS
        logging.info(f"Attempting to send message to SQS: {quote_entry}")
        
        response = sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(quote_entry),
            MessageAttributes={
                'MessageType': {
                    'DataType': 'String',
                    'StringValue': 'qotd'
                }
            }
        )
        
        logging.info(f"Successfully sent message to SQS. MessageId: {response.get('MessageId')}")
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Quote added successfully! Thank you for your contribution! 📝 Amen! 😇"
        )
    except Exception as e:
        logging.error(f"Error sending message to SQS: {str(e)}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, there was an error saving your quote. Please try again later."
        )

async def set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # set the daysSinceDrunk to the number provided
    daysSinceDrunk = int(context.args[0])
    with open('daysSinceDrunk.txt', 'w') as file:
        file.write(str(daysSinceDrunk))
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Days since drunk set to {daysSinceDrunk}! 🍻")



def main():
    global daysSinceDrunk
    global europeCountdown
    daysSinceDrunk = get_info()

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Command handlers
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)  

    set_handler = CommandHandler('set', set)
    application.add_handler(set_handler)

    drunk_handler = CommandHandler('drunk', drunk)
    application.add_handler(drunk_handler)

    send_drunk_message_handler = CommandHandler('sendDrunk', send_drunk_message)
    application.add_handler(send_drunk_message_handler)

    qotd_handler = CommandHandler('qotd', qotd)
    application.add_handler(qotd_handler)

    # Schedule the job to run at a specific time
    application.job_queue.run_daily(send_scheduled_message, time=datetime.time(hour=10, minute=0, tzinfo=datetime.timezone(offset=datetime.timedelta(hours=8))))

    application.run_polling(poll_interval=5.0)

if __name__ == '__main__':
    main()