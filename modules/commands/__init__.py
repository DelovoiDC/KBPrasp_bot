from enum import Enum
from ..client import client
from ..config import MESSAGES
from telethon import events, Button
from functools import wraps

def common_translit(text: str) -> str:
    return text.replace('t', 'т').replace('T', 'Т').replace('k', 'к').replace('K', 'К')

bot_username = client.loop.run_until_complete(client.get_me()).username

def command(command: str, parameters: int = 0, exact: bool = False) -> str:
    return r'^/{}(?>@{})?{}$'.format(command, bot_username, r'(?> (\S+)){}'.format('?' if not exact else '') * parameters)

def error_handler(func):
    @wraps(func)
    async def wrapper(event: events.NewMessage.Event | events.CallbackQuery.Event, *args, **kwargs):
        try:
            return await func(event, *args, **kwargs)
        except events.StopPropagation as stop:
            raise stop
        except Exception as e:
            logging.error(e, exc_info=True)
            await client.send_message(event.chat_id, MESSAGES['error'], parse_mode='md')
    return wrapper

class Action(Enum):
    FEEDBACK = 'feedback'
    SEND = 'send'
    EJ_SURNAME = 'ej_surname'
    EJ_GROUP = 'ej_group'
    EJ_BIRTHDAY = 'ej_birthday'

actions: dict[int, Action] = {}

async def cancel(chat_id: int):
    if chat_id in actions:
        await client.send_message(chat_id, MESSAGES['cancel'], parse_mode='md')
        actions.pop(chat_id)

cancel_button = Button.inline(MESSAGES['buttons']['cancel'], data='cancel')

@client.on(events.CallbackQuery(data='cancel'))
async def cancel_callback(event: events.CallbackQuery.Event):
    await event.answer()
    await cancel(event.chat_id)

@client.on(events.NewMessage(pattern=command('cancel')))
async def cancel_command(event: events.NewMessage.Event):
    await cancel(event.chat_id)

from . import general, rasp, admin, ej
