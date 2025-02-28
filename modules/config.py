from dotenv import load_dotenv
import os
import json

def getenv(key: str) -> str:
    value = os.environ.get(key)
    if value is None:
        raise EnvironmentError('{} environmvet variable is missing'.format(key))
    return value

load_dotenv()

TELEGRAM_API_ID = getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = getenv('TELEGRAM_API_HASH')
TELEGRAM_BOT_TOKEN = getenv('TELEGRAM_BOT_TOKEN')

FEEDBACK_CHANNEL_ID = int(getenv('FEEDBACK_CHANNEL_ID'))

MYSQL_HOST = getenv('MYSQL_HOST')
MYSQL_USER = getenv('MYSQL_USER')
MYSQL_PASSWORD = getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = getenv('MYSQL_DATABASE')

MESSAGES = {}

def load_messages():
    with open('messages.json', 'r', encoding='utf-8') as f:
        for key, value in json.load(f).items():
            MESSAGES[key] = value if type(value) is not list else '\n'.join(value)

SCHEDULE = {}

def load_schedule():
    with open('schedule.json', 'r', encoding='utf-8') as f:
        SCHEDULE.update(json.load(f))

load_messages()
load_schedule()
