from functools import wraps
from . import command, actions, Action, cancel_button, cancel
from ..config import MESSAGES
from ..db_utils import with_user, User, Status, get_all_users
from ..client import client
from telethon import events, Button

def admin(func):
    @wraps(func)
    def wrapper(event: events.NewMessage.Event, user: User, *args, **kwargs):
        if user.status != Status.ADMIN:
            return client.send_message(event.chat_id, MESSAGES['placeholder'])
        return func(event, user, *args, **kwargs)
    return wrapper

@client.on(events.NewMessage(pattern=command('send')))
@with_user
@admin
async def send(event: events.NewMessage.Event, user: User):
    await client.send_message(event.chat_id, MESSAGES['admin']['send']['init'], buttons=cancel_button)
    actions[event.chat_id] = Action.SEND
    raise events.StopPropagation

send_buffer: dict[int, str] = {}

yes_no_buttons = client.build_reply_markup([
    [Button.inline(MESSAGES['buttons']['yes'], 'send_yes')],
    [Button.inline(MESSAGES['buttons']['no'], 'send_no')]
])

@client.on(events.NewMessage())
async def new_message(event: events.NewMessage.Event):
    if event.chat_id in actions:
        action = actions[event.chat_id]
        match action:
            case Action.SEND:
                send_buffer[event.chat_id] = event.message.text
                await client.send_message(event.chat_id, MESSAGES['admin']['send']['sure'], buttons=yes_no_buttons)
                actions.pop(event.chat_id)
            case _:
                return

        raise events.StopPropagation

@client.on(events.CallbackQuery(data='send_yes'))
async def yes(event: events.CallbackQuery.Event):
    await event.answer()
    await client.edit_message(event.chat_id, event.message_id, MESSAGES['admin']['send']['done'])
    message = send_buffer.pop(event.chat_id)
    for user_id in get_all_users():
        try:
            await client.send_message(user_id, message)
        except:
            pass

@client.on(events.CallbackQuery(data='send_no'))
async def no(event: events.CallbackQuery.Event):
    await event.answer()
    if event.chat_id in send_buffer:
        send_buffer.pop(event.chat_id)
    await client.edit_message(event.chat_id, event.message_id, MESSAGES['cancel'])
