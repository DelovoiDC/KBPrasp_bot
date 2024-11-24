from telethon import events, Button
from telethon.types import ReplyKeyboardMarkup
from telethon.errors import MessageNotModifiedError
from ..config import MESSAGES
from ..db_utils import with_user, User, get_subs, get_rasp_entity, find_rasp_entity, RaspEntity, RaspEntityType
from ..client import client, scheduler
from ..kbp import Rasp, Weekday, PairType
from . import command, common_translit, error_handler
import logging
from datetime import datetime, timezone, timedelta
from ..utils import MessagePane, MessagePaneDirection, TextMessageContent, MessageContentConstraint, MessageModifierFlag
from itertools import zip_longest
from functools import wraps

tz = timezone(timedelta(hours=3))
kbp_rasp = Rasp()

def format_rasp(weekday: Weekday, entity: RaspEntity, width: int, show_timestamps: bool = False) -> MessagePane:
    pane = MessagePane(MessagePaneDirection.VERTICAL)
    weekday_name = MessagePane(MessagePaneDirection.HORIZONTAL, size=width)
    weekday_name.add(TextMessageContent(weekday.name, MessageContentConstraint.FILL, MessageModifierFlag.BOLD))
    pane.add(weekday_name)
    pane.add(TextMessageContent(''))
    if weekday.zamena != '':
        weekday_zamena = MessagePane(MessagePaneDirection.HORIZONTAL, size=width)
        weekday_zamena.add(TextMessageContent(weekday.zamena, MessageContentConstraint.FILL, MessageModifierFlag.BOLD))
        pane.add(weekday_zamena)
    else:
        pane.add(TextMessageContent(''))
    
    for pair in weekday.pairs:
        pair_pane = MessagePane(MessagePaneDirection.HORIZONTAL, size=width)
        if show_timestamps:
            pair_pane.add(TextMessageContent('[{}]⠀{}|⠀'.format(pair.time, '⠀' * (5 - len(pair.time)))))
        pair_pane.add(TextMessageContent('{}⠀'.format(pair.number) + ('⠀' if len(str(pair.number)) == 1 else '')))

        name = pair.names.pop() if len(pair.names) > 0 else ''
        modifiers = MessageModifierFlag.NONE
        match pair.type:
            case PairType.ADDED:
                modifiers = MessageModifierFlag.BOLD
            case PairType.CHANGED:
                modifiers = MessageModifierFlag.BOLD | MessageModifierFlag.ITALIC
            case PairType.REMOVED:
                modifiers = MessageModifierFlag.STRIKETHROUGH
        pair_pane.add(TextMessageContent(name, MessageContentConstraint.FILL, modifiers))
        if len(pair.places) > 0:
            pair_pane.add(TextMessageContent('⠀[{}]'.format(pair.places.pop())))
        else:
            pair_pane.add(TextMessageContent('⠀' * 7))
        pane.add(pair_pane)

        match entity.type:
            case RaspEntityType.TEACHER:
                if len(pair.groups) > 0:
                    pair_pane = MessagePane(MessagePaneDirection.HORIZONTAL, size=width)
                    if not show_timestamps:
                        pair_pane.add(TextMessageContent('⠀' * 7))
                    pair_pane.add(TextMessageContent('', MessageContentConstraint.FILL))
                    pair_pane.add(TextMessageContent('', MessageContentConstraint.FILL))
                    pair_pane.add(TextMessageContent('', MessageContentConstraint.FILL))
                    pair_pane.add(TextMessageContent(pair.groups.pop(), MessageContentConstraint.FILL))
                    pane.add(pair_pane)
                if len(pair.teachers) > 0:
                    pair.teachers.pop()
            case RaspEntityType.SUBJECT | RaspEntityType.PLACE:
                if len(pair.teachers) > 0 and len(pair.groups) > 0:
                    pair_pane = MessagePane(MessagePaneDirection.HORIZONTAL, size=width)
                    if show_timestamps:
                        pair_pane.add(TextMessageContent('⠀' * 5))
                    pair_pane.add(TextMessageContent('', MessageContentConstraint.FILL))
                    pair_pane.add(TextMessageContent('', MessageContentConstraint.FILL))
                    pair_pane.add(TextMessageContent('', MessageContentConstraint.FILL))
                    pair_pane.add(TextMessageContent(pair.teachers.pop(), MessageContentConstraint.FILL))
                    pair_pane.add(TextMessageContent('⠀', MessageContentConstraint.FILL))
                    pair_pane.add(TextMessageContent(pair.groups.pop(), MessageContentConstraint.FILL))
                    pane.add(pair_pane)
            case RaspEntityType.GROUP:
                if len(pair.teachers) > 0:
                    pair.teachers.pop()
                if len(pair.groups) > 0:
                    pair.groups.pop()

        for name, place, teacher, group in zip_longest(pair.names, pair.places, pair.teachers, pair.groups, fillvalue=''):
            pair_pane = MessagePane(MessagePaneDirection.HORIZONTAL, size=width)
            if show_timestamps:
                pair_pane.add(TextMessageContent('⠀' * 4))
            pair_pane.add(TextMessageContent('', MessageContentConstraint.FILL))
            pair_pane.add(TextMessageContent('', MessageContentConstraint.FILL))
            pair_pane.add(TextMessageContent('', MessageContentConstraint.FILL))
            pair_pane.add(TextMessageContent(name, MessageContentConstraint.FILL))
            pair_pane.add(TextMessageContent('⠀[{}]'.format(place), MessageContentConstraint.FILL))
            pair_pane.add(TextMessageContent('', MessageContentConstraint.FILL))
            pane.add(pair_pane)
            match entity.type:
                case RaspEntityType.TEACHER:
                    pair_pane = MessagePane(MessagePaneDirection.HORIZONTAL, size=width)
                    if not show_timestamps:
                        pair_pane.add(TextMessageContent('⠀' * 7))
                    pair_pane.add(TextMessageContent('', MessageContentConstraint.FILL))
                    pair_pane.add(TextMessageContent('', MessageContentConstraint.FILL))
                    pair_pane.add(TextMessageContent('', MessageContentConstraint.FILL))
                    pair_pane.add(TextMessageContent(group, MessageContentConstraint.FILL))
                    pane.add(pair_pane)
                case RaspEntityType.SUBJECT | RaspEntityType.PLACE:
                    pair_pane = MessagePane(MessagePaneDirection.HORIZONTAL, size=width)
                    if show_timestamps:
                        pair_pane.add(TextMessageContent('⠀' * 5))
                    pair_pane.add(TextMessageContent('', MessageContentConstraint.FILL))
                    pair_pane.add(TextMessageContent('', MessageContentConstraint.FILL))
                    pair_pane.add(TextMessageContent('', MessageContentConstraint.FILL))
                    pair_pane.add(TextMessageContent(teacher, MessageContentConstraint.FILL))
                    pair_pane.add(TextMessageContent('⠀', MessageContentConstraint.FILL))
                    pair_pane.add(TextMessageContent(group, MessageContentConstraint.FILL))
                    pane.add(pair_pane)

    pane.add(TextMessageContent(''))
    entity_pane = MessagePane(MessagePaneDirection.HORIZONTAL, size=width)
    entity_pane.add(TextMessageContent(entity.name, MessageContentConstraint.FILL, MessageModifierFlag.BOLD))
    pane.add(entity_pane)
    
    return pane
        
def get_date_rasp(rasp: dict[str, list[Weekday]], entity: RaspEntity, date: datetime, show_timestamps: bool = False) -> str:
    width = 32 if show_timestamps else 24
    today = datetime.now(tz)
    week = 'left'
    delta = (today - date).days
    if delta < today.weekday() - 5:
        week = 'right'
    datestr = '{}.{}'.format(('0' if len(str(date.day)) == 1 else '') + str(date.day), ('0' if len(str(date.month)) == 1 else '') + str(date.month))
    message = format_rasp(rasp[week][date.weekday()], entity, width, show_timestamps)
    date_pane = MessagePane(MessagePaneDirection.HORIZONTAL, size=width)
    date_pane.add(TextMessageContent(datestr, MessageContentConstraint.FILL, MessageModifierFlag.BOLD))
    message.prepend(date_pane)
    text = ''
    for line in message.render().split('\n'):
        text += line.rstrip('⠀') + '\n'
    return text
 
rasp_buttons: ReplyKeyboardMarkup = client.build_reply_markup([
    Button.inline(MESSAGES['buttons']['rasp']['prev'], data='rasp[prev]'),
    Button.inline(MESSAGES['buttons']['rasp']['update'], data='rasp[update]'),
    Button.inline(MESSAGES['buttons']['rasp']['next'], data='rasp[next]')
])

class RaspMessage:
    def __init__(self, chat_id: int, message_id: int):
        self.chat_id = chat_id
        self.message_id = message_id

    def __eq__(self, other):
        if not isinstance(other, type(self)): return NotImplemented
        return self.chat_id == other.chat_id and self.message_id == other.message_id
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __hash__(self):
        return hash((self.chat_id, self.message_id))

    def __str__(self):
        return 'RaspMessage(chat_id={}, message_id={})'.format(self.chat_id, self.message_id)

class RaspMessageData:
    def __init__(self, rasp_entity: RaspEntity, date: datetime):
        self.rasp_entity = rasp_entity
        self.date = date

__rasp_messages: dict[RaspMessage, RaspMessageData] = {}

def normalize_date(date: datetime, forward: bool = True) -> datetime:
    today = datetime.now(tz)
    if date.weekday() == 6:
        if forward:
            date = date + timedelta(days=1)
        else:
            date = date - timedelta(days=1)
    delta = (today - date).days
    if delta >= 0:
        if delta > today.weekday():
            date = today - timedelta(days=today.weekday())
    elif delta < today.weekday() - 13:
        date = today + timedelta(days=12 - today.weekday())
    return date

async def ensure_rasp_entity(user: User, rasp_entity_name: str | None, action: str) -> RaspEntity | None:
    if rasp_entity_name is not None:
        try:
            rasp_entity = get_rasp_entity(name=rasp_entity_name)
            return rasp_entity
        except NameError:
            entities = find_rasp_entity(rasp_entity_name)
            if len(entities) == 0:
                await client.send_message(user.chat_id, MESSAGES['rasp_entity_dialog']['entity_not_found'], parse_mode='md')
                return
            entities_buttons = [[Button.inline(e.name, data=f'{action}[{e.type.value}][{e.id}]')] for e in entities[:5]]
            if len(entities) > 5:
                entities_buttons.append([Button.inline('...', data='None')])
            await client.send_message(user.chat_id, MESSAGES['rasp_entity_dialog']['entity_list'], parse_mode='md', buttons=entities_buttons)
    return

def parse_entity_name_from_pattern(func):
    @wraps(func)
    def wrapper(event: events.NewMessage.Event, user: User) -> str | None:
        rasp_entity_name = None
        if event.pattern_match.group(1) is not None:
            rasp_entity_name = common_translit(event.pattern_match.group(1))
        if event.pattern_match.group(2) is not None:
            rasp_entity_name += ' ' + common_translit(event.pattern_match.group(2))
        if event.pattern_match.group(3) is not None:
            rasp_entity_name += ' ' + common_translit(event.pattern_match.group(3))
        return func(event, user, rasp_entity_name)
    return wrapper

async def rasp_with_params(user: User, rasp_entity_name: str | None):
    if rasp_entity_name is not None:
        rasp_entity = await ensure_rasp_entity(user, rasp_entity_name, 'rasp_data')
        if rasp_entity is None:
            return
    else:
        rasp_entity = user.rasp_entity
        if rasp_entity is None:
            await client.send_message(user.chat_id, MESSAGES['rasp']['no_entity'], parse_mode='md')
            return
    message = await client.send_message(user.chat_id, MESSAGES['rasp']['pending'], parse_mode='md')
    today = normalize_date(datetime.now(tz))
    await client.edit_message(user.chat_id, message, get_date_rasp(kbp_rasp.get_rasp(rasp_entity), rasp_entity, today, user.show_timestamps), parse_mode='md', buttons=rasp_buttons)
    __rasp_messages[RaspMessage(user.chat_id, message.id)] = RaspMessageData(rasp_entity, today)

async def set_entity_with_params(user: User, rasp_entity_name: str | None):
    if rasp_entity_name is not None:
        rasp_entity = await ensure_rasp_entity(user, rasp_entity_name, 'set_entity')
        if rasp_entity is None:
            return
        user.rasp_entity = rasp_entity
        await client.send_message(user.chat_id, MESSAGES['set_entity']['success'].format(rasp_entity.type.alias(), rasp_entity.name), parse_mode='md')
    else:
        message = MESSAGES['set_entity']['no_entity']
        rasp_entity = user.rasp_entity
        if rasp_entity is not None:
            message = MESSAGES['set_entity']['current_entity'].format(rasp_entity.type.alias(), rasp_entity.name) + '\n' + message
        await client.send_message(user.chat_id, message, parse_mode='md')

async def sub_with_params(user: User, rasp_entity_name: str | None):
    if rasp_entity_name is not None:
        rasp_entity = await ensure_rasp_entity(user, rasp_entity_name, 'sub')
        if rasp_entity is None:
            return
        user.sub_entity = rasp_entity
        await client.send_message(user.chat_id, MESSAGES['sub']['success'].format(rasp_entity.type.alias(), rasp_entity.name), parse_mode='md')
    else:
        message = MESSAGES['sub']['no_entity']
        rasp_entity = user.sub_entity
        if rasp_entity is not None:
            message = MESSAGES['sub']['current_entity'].format(rasp_entity.type.alias(), rasp_entity.name) + '\n' + message
        await client.send_message(user.chat_id, message, parse_mode='md')

@client.on(events.NewMessage(pattern=command('rasp', 3)))
@error_handler
@with_user
@parse_entity_name_from_pattern
async def rasp(event: events.NewMessage.Event, user: User, rasp_entity_name: str | None):
    await rasp_with_params(user, rasp_entity_name)

@client.on(events.NewMessage(pattern=command('set_entity', 3)))
@error_handler
@with_user
@parse_entity_name_from_pattern
async def set_entity(event: events.NewMessage.Event, user: User, rasp_entity_name: str | None):
    await set_entity_with_params(user, rasp_entity_name)

@client.on(events.NewMessage(pattern=command('sub', 3)))
@error_handler
@with_user
@parse_entity_name_from_pattern
async def sub(event: events.NewMessage.Event, user: User, rasp_entity_name: str | None):
    await sub_with_params(user, rasp_entity_name)

@client.on(events.NewMessage(pattern=command('unsub')))
@error_handler
@with_user
async def unsub(event: events.NewMessage.Event, user: User):
    if user.sub_entity is None:
        await client.send_message(event.chat_id, MESSAGES['unsub']['no_group'], parse_mode='md')
    else:
        rasp_entity = user.sub_entity
        user.sub_entity = None
        await client.send_message(event.chat_id, MESSAGES['unsub']['success'].format(rasp_entity.type.alias(), rasp_entity.name), parse_mode='md')

async def send_subs():
    subs = get_subs()
    today = datetime.now(tz)
    tomorrow = normalize_date(today + timedelta(days=1))
    for rasp_entity, users in subs.items():
        rasp_without_timestamps = get_date_rasp(kbp_rasp.get_rasp(rasp_entity), rasp_entity, tomorrow, False)
        rasp_with_timestamps = get_date_rasp(kbp_rasp.get_rasp(rasp_entity), rasp_entity, tomorrow, True)
        for user in users:
            try:
                if user.show_timestamps:
                    await client.send_message(user.chat_id, rasp_with_timestamps, parse_mode='md')
                else:
                    await client.send_message(user.chat_id, rasp_without_timestamps, parse_mode='md')
            except Exception as e:
                logging.error(e, exc_info=True)

@scheduler.scheduled_job('cron', hour=21, minute=0, day_of_week='mon-sat', id='stop_checking_rasp', misfire_grace_time=3600)
async def stop_checking_rasp():
    if scheduler.get_job('check_rasp') is not None:
        scheduler.remove_job('check_rasp')

async def check_rasp():
    today = datetime.now(tz)
    tomorrow = normalize_date(today + timedelta(days=1))
    if (kbp_rasp.check_rasp(tomorrow.weekday(), left_week=(today.weekday() != 5))):
        await stop_checking_rasp()
        await send_subs()

@scheduler.scheduled_job('cron', hour=9, minute=0, day_of_week='mon-sat', id='start_checking_rasp', misfire_grace_time=3600)
async def start_checking_rasp():
    scheduler.add_job(check_rasp, 'interval', minutes=1, id='check_rasp')
    await check_rasp()

@client.on(events.CallbackQuery(pattern=r'^rasp\[(.*)\]$'))
@error_handler
@with_user
async def rasp_callback(event: events.CallbackQuery.Event, user: User):
    rasp_message = RaspMessage(event.chat_id, event.message_id)
    if rasp_message not in __rasp_messages:
        await event.answer(MESSAGES['rasp']['data_not_found'], alert=True)
        return
    else:
        await event.answer()
    query = event.pattern_match.group(1).decode()
    rasp_data = __rasp_messages[rasp_message]
    match query:
        case 'prev':
            rasp_data.date = normalize_date(rasp_data.date - timedelta(days=1), forward=False)
        case 'next':
            rasp_data.date = normalize_date(rasp_data.date + timedelta(days=1), forward=True)
    
    text = get_date_rasp(kbp_rasp.get_rasp(rasp_data.rasp_entity), rasp_data.rasp_entity, rasp_data.date, user.show_timestamps)
    try:
        await client.edit_message(event.chat_id, event.message_id, text, buttons=rasp_buttons, parse_mode='md')
    except MessageNotModifiedError as e:
        return

@client.on(events.CallbackQuery(data='None'))
async def none_button(event: events.CallbackQuery.Event):
    await event.answer()

@client.on(events.CallbackQuery(pattern=r'^(rasp_data|set_entity|sub)\[(.*)\]\[(.*)\]$'))
@error_handler
@with_user
async def rasp_entity_button(event: events.CallbackQuery.Event, user: User):
    await event.answer()
    action_type = event.pattern_match.group(1).decode()
    rasp_entity_type = event.pattern_match.group(2).decode()
    rasp_entity_id = int(event.pattern_match.group(3).decode())
    rasp_entity = get_rasp_entity(type=RaspEntityType(rasp_entity_type), id=rasp_entity_id)
    
    match action_type:
        case 'rasp_data':
            await rasp_with_params(user, rasp_entity.name)
        case 'set_entity':
            await set_entity_with_params(user, rasp_entity.name)
        case 'sub':
            await sub_with_params(user, rasp_entity.name)
