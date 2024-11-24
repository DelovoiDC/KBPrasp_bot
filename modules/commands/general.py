from telethon import events, Button
from ..config import MESSAGES, FEEDBACK_CHANNEL_ID
from ..db_utils import with_user, User, Status
from ..client import client
from . import Action, actions, command, cancel_button, cancel, error_handler

@client.on(events.NewMessage(pattern=command('start')))
@error_handler
async def start(event: events.NewMessage.Event):
    await client.send_message(event.chat_id, MESSAGES['start'], parse_mode='md')

@client.on(events.NewMessage(pattern=command('help')))
@error_handler
async def help(event: events.NewMessage.Event):
    await client.send_message(event.chat_id, MESSAGES['help'], parse_mode='md')

settings_list = [
    'show_timestamps',
    'show_extended_info'
]

user_only_settings = [
    'show_extended_info'
]

settings_buttons = client.build_reply_markup([
    [Button.inline(MESSAGES['buttons']['settings']['show_timestamps'], data='settings[show_timestamps]')],
    [Button.inline(MESSAGES['buttons']['settings']['show_extended_info'], data='settings[show_extended_info]')],
])

back_button = Button.inline(MESSAGES['buttons']['back'], data='back')

enable_buttons = client.build_reply_markup([
    [Button.inline(MESSAGES['buttons']['enable'], data='enable')],
    [back_button]
])

disable_buttons = client.build_reply_markup([
    [Button.inline(MESSAGES['buttons']['disable'], data='disable')],
    [back_button]
])

@client.on(events.NewMessage(pattern=command('settings')))
@error_handler
@with_user
async def settings(event: events.NewMessage.Event, user: User):
    await client.send_message(event.chat_id, MESSAGES['settings']['general'], buttons=settings_buttons)

@client.on(events.CallbackQuery(pattern=r'^settings\[(.*)\]$'))
@error_handler
@with_user
async def get_setting(event: events.CallbackQuery.Event, user: User):
    await event.answer()
    setting = event.pattern_match.group(1).decode()
    if setting in user_only_settings and user.status == Status.GROUP:
        await client.edit_message(event.chat_id, event.message_id, MESSAGES['settings']['user_only'], buttons=back_button, parse_mode='md')
        return
    enabled = user[setting]
    text = MESSAGES['settings'][setting] + '\n' + (MESSAGES['settings']['enabled'] if enabled else MESSAGES['settings']['disabled'])
    buttons = disable_buttons if enabled else enable_buttons
    await client.edit_message(event.chat_id, event.message_id, text, buttons=buttons, parse_mode='md')

@client.on(events.CallbackQuery(data='back'))
@error_handler
async def back(event: events.CallbackQuery.Event):
    await event.answer()
    await client.edit_message(event.chat_id, event.message_id, MESSAGES['settings']['general'], buttons=settings_buttons, parse_mode='md')

@client.on(events.CallbackQuery(data='enable'))
@error_handler
@with_user
async def enable(event: events.CallbackQuery.Event, user: User):
    await event.answer()

    text = ''

    message: str = (await event.get_message()).text
    for setting in settings_list:
        if message.find(MESSAGES['settings'][setting]) != -1:
            user[setting] = True
            text = MESSAGES['settings'][setting] + '\n' + MESSAGES['settings']['enabled']
            break

    await client.edit_message(event.chat_id, event.message_id, text, buttons=disable_buttons, parse_mode='md')

@client.on(events.CallbackQuery(data='disable'))
@error_handler
@with_user
async def disable(event: events.CallbackQuery.Event, user: User):
    await event.answer()

    text = ''

    message: str = (await event.get_message()).text
    for setting in settings_list:
        if message.find(MESSAGES['settings'][setting]) != -1:
            user[setting] = False
            text = MESSAGES['settings'][setting] + '\n' + MESSAGES['settings']['disabled']
            break

    await client.edit_message(event.chat_id, event.message_id, text, buttons=enable_buttons, parse_mode='md')

yes_no_buttons = client.build_reply_markup([
    [Button.inline(MESSAGES['buttons']['yes'], data='feedback_yes')],
    [Button.inline(MESSAGES['buttons']['no'], data='feedback_no')]
])

feedback_buffer: dict[int, str] = {}

@client.on(events.NewMessage())
@error_handler
async def new_message(event: events.NewMessage.Event):
    if event.chat_id in actions:
        action = actions[event.chat_id]
        match action:
            case Action.FEEDBACK:
                feedback_buffer[event.chat_id] = event.message.text
                await client.send_message(event.chat_id, MESSAGES['feedback']['sure'], buttons=yes_no_buttons, parse_mode='md')
                actions.pop(event.chat_id)
            case _:
                return

        raise events.StopPropagation

@client.on(events.NewMessage(pattern=command('feedback')))
@error_handler
@with_user
async def feedback(event: events.NewMessage.Event, user: User):
    if user.status == Status.GROUP:
        await client.send_message(event.chat_id, MESSAGES['placeholder'], parse_mode='md')
        return
    await client.send_message(event.chat_id, MESSAGES['feedback']['init'], buttons=cancel_button, parse_mode='md')
    actions[event.chat_id] = Action.FEEDBACK
    raise events.StopPropagation

@client.on(events.CallbackQuery(data='feedback_yes'))
@error_handler
async def yes(event: events.CallbackQuery.Event):
    await event.answer()
    await client.edit_message(event.chat_id, event.message_id, MESSAGES['feedback']['thanks'], parse_mode='md')
    feedback_message = feedback_buffer.pop(event.chat_id)
    user = '@{}'.format(event.sender.username) if event.sender.username else '[{}](tg://user?id={})'.format(event.sender.first_name, event.sender.id)
    await client.send_message(FEEDBACK_CHANNEL_ID, '{}\n\n{}'.format(feedback_message, user))

@client.on(events.CallbackQuery(data='feedback_no'))
@error_handler
async def no(event: events.CallbackQuery.Event):
    await event.answer()
    if event.chat_id in feedback_buffer:
        feedback_buffer.pop(event.chat_id)
    await client.edit_message(event.chat_id, event.message_id, MESSAGES['cancel'], parse_mode='md')
