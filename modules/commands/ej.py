from . import command, Action, actions, cancel_button, cancel, common_translit, error_handler
from telethon import events, Button
from ..db_utils import User, get_ej_group_id, get_ej_group_name, add_marks, get_marks, with_user, Status, get_average_data, replace_average_data, get_ej_subs, Mark
from ..client import client, scheduler
from ..config import MESSAGES
from ..kbp import Journal
from re import fullmatch
from itertools import zip_longest
import logging
from ..utils import MessagePane, MessagePaneDirection, TextMessageContent, MessageContentConstraint, MessageModifierFlag

kbp_ej = Journal()

def users_only(func):
    def wrapper(event: events.NewMessage.Event, user: User, *args, **kwargs):
        if user.status == Status.GROUP:
            return client.send_message(event.chat_id, MESSAGES['placeholder'])
        return func(event, user, *args, **kwargs)
    return wrapper

async def check_ej(user: User, surname: str, group: str, birth: str) -> list[Mark]:
    marks = kbp_ej.get_ej(surname, group, birth)
    if marks is None:
        raise ValueError('Invalid ej data')
    old_marks = get_marks(user)
    new_marks = list(set(marks).difference(old_marks))
    add_marks(user, new_marks)
    return new_marks

yes_no_ej_buttons = [
    Button.inline(MESSAGES['buttons']['yes'], data='ej_data_yes'),
    Button.inline(MESSAGES['buttons']['no'], data='ej_data_no')
]

yes_no_del_ej_buttons = [
    Button.inline(MESSAGES['buttons']['yes'], data='del_ej_data_yes'),
    Button.inline(MESSAGES['buttons']['no'], data='del_ej_data_no')
]

def format_marks(marks: list[Mark]):
    message = MessagePane(MessagePaneDirection.VERTICAL)
    for mark in marks:
        mark_pane = MessagePane(MessagePaneDirection.HORIZONTAL, size=25)
        mark_pane.add(TextMessageContent('{}.{}'.format(mark.day, mark.month)))
        mark_pane.add(TextMessageContent(mark.name, MessageContentConstraint.FILL))
        mark_pane.add(TextMessageContent(mark.mark))
        message.add(mark_pane)
        title_pane = MessagePane(MessagePaneDirection.HORIZONTAL, size=25)
        title_pane.add(TextMessageContent(mark.title, MessageContentConstraint.FILL))
        message.add(title_pane)
        message.add(TextMessageContent(''))
    return message.render()

@client.on(events.NewMessage(pattern=command("ej")))
@error_handler
@with_user
@users_only
async def ej(event: events.NewMessage.Event, user: User):
    login_data = {'surname': user.surname, 'group': user.ej_group, 'birth': user.birth}
    if login_data['surname'] is not None and login_data['group'] is not None and login_data['birth'] is not None:
        message = await client.send_message(event.chat_id, MESSAGES['ej']['pending'])
        marks = await check_ej(user, login_data['surname'], login_data['group'], login_data['birth'])
        if len(marks) == 0:
            await message.edit(MESSAGES['ej']['no_marks'])
            return
        await message.edit(format_marks(marks))
        return
    await client.send_message(event.chat_id, MESSAGES['ej']['privacy'], buttons=yes_no_ej_buttons)

ej_data_buffer: dict[int, dict[str, str]] = {}

@client.on(events.CallbackQuery(data='ej_data_yes'))
@error_handler
async def ej_yes(event: events.CallbackQuery.Event):
    await event.answer()
    actions[event.chat_id] = Action.EJ_SURNAME
    await client.edit_message(event.chat_id, event.message_id, MESSAGES['ej']['enter_data'], buttons=cancel_button)
    await client.send_message(event.chat_id, MESSAGES['ej']['enter_surname'])
    ej_data_buffer[event.chat_id] = {}

@client.on(events.CallbackQuery(data='ej_data_no'))
@error_handler
async def ej_no(event: events.CallbackQuery.Event):
    await event.answer()
    if event.chat_id in actions:
        actions.pop(event.chat_id)
    await client.edit_message(event.chat_id, event.message_id, MESSAGES['cancel'])

@client.on(events.NewMessage())
@error_handler
async def new_message(event: events.NewMessage.Event):
    if event.chat_id in actions:
        action = actions[event.chat_id]
        match action:
            case Action.EJ_SURNAME:
                ej_data_buffer[event.chat_id]['surname'] = event.message.text
                await client.send_message(event.chat_id, MESSAGES['ej']['enter_group'])
                actions[event.chat_id] = Action.EJ_GROUP
            case Action.EJ_GROUP:
                try:
                    group = common_translit(event.message.text)
                    group = get_ej_group_id(group)
                    ej_data_buffer[event.chat_id]['group'] = group
                    await client.send_message(event.chat_id, MESSAGES['ej']['enter_birth'])
                    actions[event.chat_id] = Action.EJ_BIRTHDAY
                except NameError:
                    await client.send_message(event.chat_id, MESSAGES['ej']['group_invalid'])
            case Action.EJ_BIRTHDAY:
                birth = event.message.text.replace('-', '.').replace('/', '.')
                if not fullmatch('[0-3][0-9].[0-1][0-9].[1-2][09][06-9][0-9]', birth):
                    await client.send_message(event.chat_id, MESSAGES['ej']['birth_invalid'])
                else:
                    ej_data_buffer[event.chat_id]['birth'] = birth
                    message = await client.send_message(event.chat_id, MESSAGES['ej']['checking'])
                    try:
                        actions.pop(event.chat_id)
                        ej_data = ej_data_buffer.pop(event.chat_id)
                        user = User(event.chat_id)
                        await check_ej(user, ej_data['surname'], ej_data['group'], ej_data['birth'])
                        user.surname = ej_data['surname']
                        user.ej_group = ej_data['group']
                        user.birth = ej_data['birth']
                        await message.edit(MESSAGES['ej']['data_saved'])
                    except ValueError:
                        await message.edit(MESSAGES['ej']['invalid'])
            case _:
                return

        raise events.StopPropagation

@client.on(events.NewMessage(pattern=command("del_ej")))
@error_handler
@with_user
@users_only
async def del_ej(event: events.NewMessage.Event, user: User):
    if user.surname is not None and user.ej_group is not None and user.birth is not None:
        await client.send_message(event.chat_id, MESSAGES['del_ej']['sure'], buttons=yes_no_del_ej_buttons)
    else:
        await client.send_message(event.chat_id, MESSAGES['del_ej']['no_data'])

@client.on(events.CallbackQuery(data='del_ej_data_yes'))
@error_handler
@with_user
async def del_ej_yes(event: events.CallbackQuery.Event, user: User):
    await event.answer()
    user.surname = None
    user.ej_group = None
    user.birth = None
    user.ej_sub = False
    await client.edit_message(event.chat_id, event.message_id, MESSAGES['del_ej']['success'])

@client.on(events.CallbackQuery(data='del_ej_data_no'))
@error_handler
async def del_ej_no(event: events.CallbackQuery.Event):
    await event.answer()
    await client.edit_message(event.chat_id, event.message_id, MESSAGES['cancel'])

def format_average(marks: list[Mark], extended_info: bool = False, average_data: list[Mark] = []):
    message = MessagePane(MessagePaneDirection.VERTICAL)
    title_pane = MessagePane(MessagePaneDirection.HORIZONTAL, size=23)
    title_pane.add(TextMessageContent(MESSAGES['average']['title'], MessageContentConstraint.FILL, MessageModifierFlag.BOLD))
    message.add(title_pane)
    for mark, last_mark in zip_longest(marks, average_data):
        mark_pane = MessagePane(MessagePaneDirection.HORIZONTAL, size=25)
        mark_pane.add(TextMessageContent(mark.name))
        mark_pane.add(TextMessageContent('', MessageContentConstraint.FILL))
        mark_text = mark.mark
        mark = float(mark.mark.replace('-', '0'))
        if extended_info:
            color_mark = '⠀'
            match mark:
                case _ if mark > 7:
                    color_mark = '🟢'
                case _ if mark > 5:
                    color_mark = '🟡'
                case _ if mark > 3:
                    color_mark = '🟠'
                case _:
                    color_mark = '🔴'
            mark_text += '⠀' + color_mark
            if last_mark is not None:
                dynamics_mark = '⠀'
                last_mark = float(last_mark.mark.replace('-', '0'))
                if mark < last_mark:
                    dynamics_mark = '📉'
                elif mark > last_mark:
                    dynamics_mark = '📈'
                mark_text += dynamics_mark
        else:
            warning = '⠀⠀'
            if mark < 3:
                warning = '⠀❗️'
            mark_text += warning
        mark_pane.add(TextMessageContent(mark_text, MessageContentConstraint.FILL))
        message.add(mark_pane)
    text = ''
    for line in message.render().split('\n'):
        text += line.rstrip('⠀') + '\n'
    return text

@client.on(events.NewMessage(pattern=command("average")))
@error_handler
@with_user
@users_only
async def average(event: events.NewMessage.Event, user: User):
    login_data = {'surname': user.surname, 'group': user.ej_group, 'birth': user.birth}
    if login_data['surname'] is None or login_data['group'] is None or login_data['birth'] is None:
        await client.send_message(event.chat_id, MESSAGES['average']['no_data'])
        return
    message = await client.send_message(event.chat_id, MESSAGES['average']['pending'])
    average = kbp_ej.get_average(login_data['surname'], login_data['group'], login_data['birth'])
    text = format_average(average, user.show_extended_info, get_average_data(user))
    await message.edit(text)
    replace_average_data(user, average)

@client.on(events.NewMessage(pattern=command("sub_ej")))
@error_handler
@with_user
@users_only
async def sub_ej(event: events.NewMessage.Event, user: User):
    if user.surname is None or user.ej_group is None or user.birth is None:
        await client.send_message(event.chat_id, MESSAGES['sub_ej']['no_data'])
        return
    if user.ej_sub:
        await client.send_message(event.chat_id, MESSAGES['sub_ej']['already'])
        return
    user.ej_sub = True
    await client.send_message(event.chat_id, MESSAGES['sub_ej']['success'])

@client.on(events.NewMessage(pattern=command("unsub_ej")))
@error_handler
@with_user
@users_only
async def unsub_ej(event: events.NewMessage.Event, user: User):
    if not user.ej_sub:
        await client.send_message(event.chat_id, MESSAGES['unsub_ej']['not_subbed'])
        return
    user.ej_sub = False
    await client.send_message(event.chat_id, MESSAGES['unsub_ej']['success'])

@scheduler.scheduled_job('cron', hour=13, minute=50, id='send_ej', misfire_grace_time=3600)
async def send_ej():
    subs = get_ej_subs()
    for sub in subs:
        try:
            message = await client.send_message(sub.chat_id, MESSAGES['ej']['pending'])
            marks = await check_ej(sub, sub.surname, sub.ej_group, sub.birth)
            if len(marks) == 0:
                await message.edit(MESSAGES['ej']['no_marks'])
                continue
            await message.edit(format_marks(marks))
        except Exception as e:
            logging.error(e, exc_info=True)
