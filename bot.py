import datetime
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackContext, MessageHandler, filters
import os
import boto3
import json
from dotenv import load_dotenv
import requests
from google import genai
from google.genai import types

import os

# Load environment variables
load_dotenv()

daysSinceDrunk = 0
longestStreak = 0
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
    longestStreak = 0
    if not os.path.exists('daysSinceDrunk.txt'):
        with open('daysSinceDrunk.txt', 'w') as file:
            file.write(str(0))
    else:
        with open('daysSinceDrunk.txt', 'r') as file:
            daysSinceDrunk = int(file.read())
    return daysSinceDrunk

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
        # Retrieve the quote from api
        response = requests.get('https://api.quotable.io/quotes/random?tags=motivational%7Csuccess',verify=False)
        body = response.json()[0]
        user = body['author']
        quote = body['content']
        return quote, user
    

# Scheduled message
async def send_scheduled_message(context: CallbackContext):
    global daysSinceDrunk

    # Get the quote of the day
    qotd, user   = await get_qotd()

    # Send the message to the channel
    channel_username = '-1002157531667'  
    message = f"Good Morning Everyone! I am sober for {daysSinceDrunk} days! Cheers to that! 🍻 \n\n{qotd} - {user}"
    await context.bot.send_message(chat_id=channel_username, text=message)

    # Update the daysSinceDrunk.txt file
    with open('daysSinceDrunk.txt', 'w') as file:
        file.write(str(daysSinceDrunk))

    # Increment the daysSinceDrunk
    daysSinceDrunk += 1

# Commands
async def send_drunk_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    qotd, user   = await get_qotd()
    message = f"Good Morning Everyone! I am sober for {daysSinceDrunk} days! Cheers to that! 🍻 \n\n Longest streak sober: {longestStreak}\n\n{qotd} - {user}"
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

# Tools
def get_events():
    # Call Google Calendar API to get all events
    # Return the events
    return "Events"

def add_event(date: str, time: str, description: str):
    # Call Google Calendar API to add an event
    # Return the event
    return "Event added"

def remove_event(event_id: str):
    # Call Google Calendar API to remove an event
    # Return the event
    return "Event removed"

def reschedule_event(event_id: str, new_date: str, new_time: str):
    # Call Google Calendar API to reschedule an event
    # Return the event
    return "Event rescheduled"

# Initialize Gemini
gemini = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Define function schemas for Gemini tools
function_declarations = [
    {
        "name": "add_event",
        "description": "Add a new event to the calendar",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "The date of the event (YYYY-MM-DD format)"
                },
                "time": {
                    "type": "string", 
                    "description": "The time of the event (HH:MM format)"
                },
                "description": {
                    "type": "string",
                    "description": "Description of the event"
                }
            },
            "required": ["date", "time", "description"]
        }
    },
    {
        "name": "remove_event",
        "description": "Remove an event from the calendar",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "The ID of the event to remove"
                }
            },
            "required": ["event_id"]
        }
    },
    {
        "name": "reschedule_event",
        "description": "Reschedule an existing event",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "The ID of the event to reschedule"
                },
                "new_date": {
                    "type": "string",
                    "description": "The new date for the event (YYYY-MM-DD format)"
                },
                "new_time": {
                    "type": "string",
                    "description": "The new time for the event (HH:MM format)"
                }
            },
            "required": ["event_id", "new_date", "new_time"]
        }
    }
]

tools = types.Tool(function_declarations=function_declarations)
config = types.GenerateContentConfig(tools=[tools])

async def schedule_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == 716853175:
        user_message = update.message.text
        context.user_data.setdefault('history', []).append({"role": "user", "content": user_message})

        instructions = """
                        You are a helpful calendar scheduler. You are given a event date and you need to check if the date is available. 
                        Use the tools to call Google Calendar API to check if the date is available on my calendar. 
                        
                        If it is, help me schedule the event.
                        If it is not, you need to tell me that the date is not available, and if I would like to schedule it on a different date or change the current date.
                        If I am rescheduling the event, you need to ask me for the new date and time.

                        You will be given a list of events that are already scheduled.
                    """
        response = gemini.models.generate_content(
                system_instruction=instructions,
                model="gemini-2.0-flash",
                contents=context.user_data['history'],
                config=config
            )
        
        assistant = response.text
        context.user_data['history'].append({"role": "assistant", "content": assistant})
        await update.message.reply_text(assistant)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not Kai Sheng.. wya doing here.... 😡")



def main():
    global daysSinceDrunk
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

    # Message handlers
    schedule_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, schedule_event)
    application.add_handler(schedule_handler)

    # Schedule the job to run at a specific time
    application.job_queue.run_daily(send_scheduled_message, time=datetime.time(hour=10, minute=0, tzinfo=datetime.timezone(offset=datetime.timedelta(hours=8))))

    application.run_polling(poll_interval=5.0)

if __name__ == '__main__':
    main()