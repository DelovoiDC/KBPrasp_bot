import mysql.connector as mysql
from contextlib import closing
from .config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE, MESSAGES
from telethon import events
from typing import Callable
from enum import Enum
from functools import wraps

__config = {
    'host': MYSQL_HOST,
    'user': MYSQL_USER,
    'password': MYSQL_PASSWORD,
    'database': MYSQL_DATABASE
}

pool = mysql.pooling.MySQLConnectionPool(pool_name='mysql', **__config)

class Status(Enum):
    USER = 'user'
    GROUP = 'group'
    ADMIN = 'admin'

class RaspEntityType(Enum):
    GROUP = 'group'
    TEACHER = 'teacher'
    PLACE = 'place'
    SUBJECT = 'subject'

    def alias(self) -> str:
        match self:
            case self.GROUP:
                return MESSAGES['rasp_entity_aliases']['group']
            case self.TEACHER:
                return MESSAGES['rasp_entity_aliases']['teacher']
            case self.PLACE:
                return MESSAGES['rasp_entity_aliases']['place']
            case self.SUBJECT:
                return MESSAGES['rasp_entity_aliases']['subject']

    @classmethod
    def by_label(cls, label: str):
        if label == MESSAGES['rasp_entity_labels']['group']:
            return cls.GROUP
        if label == MESSAGES['rasp_entity_labels']['place']:
            return cls.PLACE
        if label == MESSAGES['rasp_entity_labels']['subject']:
            return cls.SUBJECT
        if label == MESSAGES['rasp_entity_labels']['teacher']:
            return cls.TEACHER

class RaspEntity:
    def __init__(self, id: int, type: RaspEntityType, name: str):
        self.id = id
        self.type = type
        self.name = name

    def __eq__(self, other):
        if not isinstance(other, type(self)): return NotImplemented
        return self.id == other.id and self.type == other.type and self.name == other.name

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.id, self.type.value, self.name))

def get_rasp_entity(name: str | None = None, id: int | None = None, type: RaspEntityType | None = None) -> RaspEntity:
    with closing(pool.get_connection()) as con:
        with closing(con.cursor()) as cur:
            data = {}
            if name is not None:
                data['name'] = name
            if id is not None:
                data['entity_id'] = id
            if type is not None:
                data['type'] = type.value
            if len(data) == 0:
                raise NameError('No data provided')
            condition = ' AND '.join(map(lambda key: f'{key} = %({key})s', data))
            cur.execute(f'SELECT `entity_id`, `type`, `name` FROM `rasp_entities` WHERE {condition}', data)
            res = cur.fetchone()
            if res is None:
                raise NameError('No such entity')
            return RaspEntity(res[0], RaspEntityType(res[1]), res[2])

def update_rasp_entities(entities: list[RaspEntity]):
    with closing(pool.get_connection()) as con:
        with closing(con.cursor()) as cur:
            for entity in entities:
                try:
                    get_rasp_entity(name=entity.name, type=entity.type)
                    cur.execute('UPDATE `rasp_entities` SET `entity_id` = %s WHERE `type` = %s AND `name` = %s', (entity.id, entity.type.value, entity.name))
                except NameError:
                    cur.execute('INSERT INTO `rasp_entities` (`entity_id`, `type`, `name`) VALUES (%s, %s, %s)', (entity.id, entity.type.value, entity.name))
                con.commit()

def find_rasp_entity(name: str) -> list[RaspEntity] | None:
    with closing(pool.get_connection()) as con:
        with closing(con.cursor()) as cur:
            search_string = name.replace('*', '').replace(' ', '*') + '*'
            cur.execute('SELECT `entity_id`, `type`, `name`, MATCH (name) AGAINST (%(search_string)s IN BOOLEAN MODE) AS prob FROM `rasp_entities` WHERE MATCH (name) AGAINST (%(search_string)s IN BOOLEAN MODE) > 0 ORDER BY prob DESC LIMIT 6', {'search_string': search_string})
            res = cur.fetchall()
            return [RaspEntity(r[0], RaspEntityType(r[1]), r[2]) for r in res]

def get_ej_group_id(group_name: str) -> int:
    group_name = group_name.upper()
    with closing(pool.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('SELECT `id` FROM `ej_groups` WHERE `name` = %s', (group_name,))
            result = cur.fetchone()
            if result is None:
                raise NameError('Group {} not found'.format(group_name))
            return result[0]

def get_ej_group_name(group_id: int) -> str:
    with closing(pool.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('SELECT `name` FROM `ej_groups` WHERE `id` = %s', (group_id,))
            result = cur.fetchone()
            if result is None:
                raise NameError('Group {} not found'.format(group_id))
            return result[0]
    
class User:
    def __init__(self, chat_id: int):
        with closing(pool.get_connection()) as con:
            with closing(con.cursor()) as cur:
                cur.execute('SELECT EXISTS(SELECT * FROM `users` WHERE `chat_id` = %s)', (chat_id,))
                result = cur.fetchone()[0]
                if result == False:
                    cur.execute('INSERT INTO `users` (`chat_id`, `status`) VALUES (%s, %s)', (chat_id, 'user' if chat_id > 0 else 'group'))
                    con.commit()
        self.chat_id = chat_id

    @property
    def show_timestamps(self) -> bool:
        with closing(pool.get_connection()) as con:
            with closing(con.cursor()) as cur:
                cur.execute('SELECT `show_timestamps` FROM `users` WHERE `chat_id` = %s', (self.chat_id,))
                result: int = cur.fetchone()[0]
                return bool(result)

    @show_timestamps.setter
    def show_timestamps(self, value: bool):
        with closing(pool.get_connection()) as con:
            with closing(con.cursor()) as cur:
                cur.execute('UPDATE `users` SET `show_timestamps` = %s WHERE `chat_id` = %s', (value, self.chat_id))
                con.commit()

    @property
    def show_extended_info(self) -> bool:
        with closing(pool.get_connection()) as con:
            with closing(con.cursor()) as cur:
                cur.execute('SELECT `show_extended_info` FROM `users` WHERE `chat_id` = %s', (self.chat_id,))
                result: int = cur.fetchone()[0]
                return bool(result)

    @show_extended_info.setter
    def show_extended_info(self, value: bool):
        with closing(pool.get_connection()) as con:
            with closing(con.cursor()) as cur:
                cur.execute('UPDATE `users` SET `show_extended_info` = %s WHERE `chat_id` = %s', (value, self.chat_id))
                con.commit()

    @property
    def rasp_entity(self) -> RaspEntity | None:
        with closing(pool.get_connection()) as con:
            with closing(con.cursor()) as cur:
                cur.execute('SELECT e.`entity_id`, e.`type`, e.`name` FROM `users` JOIN `rasp_entities` AS e ON `rasp_entity` = e.`id` WHERE `chat_id` = %s', (self.chat_id,))
                result = cur.fetchone()
                if result is None:
                    return None
                return RaspEntity(result[0], RaspEntityType(result[1]), result[2])
        
    @rasp_entity.setter
    def rasp_entity(self, value: RaspEntity | None):
        with closing(pool.get_connection()) as con:
            with closing(con.cursor()) as cur:
                rasp_entity_id: int = None
                if value is not None:
                    cur.execute('SELECT `id` FROM `rasp_entities` WHERE `entity_id` = %s AND `type` = %s AND `name` = %s', (value.id, value.type.value, value.name))
                    rasp_entity_id = cur.fetchone()[0]
                cur.execute('UPDATE `users` SET `rasp_entity` = %s WHERE `chat_id` = %s', (rasp_entity_id, self.chat_id))
                con.commit()

    @property
    def sub_entity(self) -> RaspEntity | None:
        with closing(pool.get_connection()) as con:
            with closing(con.cursor()) as cur:
                cur.execute('SELECT e.`entity_id`, e.`type`, e.`name` FROM `users` JOIN `rasp_entities` AS e ON `sub_entity` = e.`id` WHERE `chat_id` = %s', (self.chat_id,))
                result = cur.fetchone()
                if result is None:
                    return None
                return RaspEntity(result[0], RaspEntityType(result[1]), result[2])
        
    @sub_entity.setter
    def sub_entity(self, value: RaspEntity | None):
        with closing(pool.get_connection()) as con:
            with closing(con.cursor()) as cur:
                sub_entity_id: int = None
                if value is not None:
                    cur.execute('SELECT `id` FROM `rasp_entities` WHERE `entity_id` = %s AND `type` = %s AND `name` = %s', (value.id, value.type.value, value.name))
                    sub_entity_id = cur.fetchone()[0]
                cur.execute('UPDATE `users` SET `sub_entity` = %s WHERE `chat_id` = %s', (sub_entity_id, self.chat_id))
                con.commit()
            
    @property
    def surname(self) -> str | None:
        with closing(pool.get_connection()) as con:
            with closing(con.cursor()) as cur:
                cur.execute('SELECT `surname` FROM `users` WHERE `chat_id` = %s', (self.chat_id,))
                result: str = cur.fetchone()[0]
                return result

    @surname.setter
    def surname(self, value: str | None):
        with closing(pool.get_connection()) as con:
            with closing(con.cursor()) as cur:
                cur.execute('UPDATE `users` SET `surname` = %s WHERE `chat_id` = %s', (value, self.chat_id))
                con.commit()

    @property
    def ej_group(self) -> int | None:
        with closing(pool.get_connection()) as con:
            with closing(con.cursor()) as cur:
                cur.execute('SELECT `ej_group` FROM `users` WHERE `chat_id` = %s', (self.chat_id,))
                result: int = cur.fetchone()[0]
                return result

    @ej_group.setter
    def ej_group(self, value: int | None):
        with closing(pool.get_connection()) as con:
            with closing(con.cursor()) as cur:
                cur.execute('UPDATE `users` SET `ej_group` = %s WHERE `chat_id` = %s', (value, self.chat_id))
                con.commit()

    @property
    def ej_sub(self) -> bool:
        with closing(pool.get_connection()) as con:
            with closing(con.cursor()) as cur:
                cur.execute('SELECT `ej_sub` FROM `users` WHERE `chat_id` = %s', (self.chat_id,))
                result: int = cur.fetchone()[0]
                return bool(result)
    
    @ej_sub.setter
    def ej_sub(self, value: bool):
        with closing(pool.get_connection()) as con:
            with closing(con.cursor()) as cur:
                cur.execute('UPDATE `users` SET `ej_sub` = %s WHERE `chat_id` = %s', (value, self.chat_id))
                con.commit()

    @property
    def birth(self) -> str | None:
        with closing(pool.get_connection()) as con:
            with closing(con.cursor()) as cur:
                cur.execute('SELECT `birth` FROM `users` WHERE `chat_id` = %s', (self.chat_id,))
                result: str = cur.fetchone()[0]
                return result
        
    @birth.setter
    def birth(self, value: str | None):
        with closing(pool.get_connection()) as con:
            with closing(con.cursor()) as cur:
                cur.execute('UPDATE `users` SET `birth` = %s WHERE `chat_id` = %s', (value, self.chat_id))
                con.commit()

    @property
    def status(self) -> Status:
        with closing(pool.get_connection()) as con:
            with closing(con.cursor()) as cur:
                cur.execute('SELECT `status` FROM `users` WHERE `chat_id` = %s', (self.chat_id,))
                result: str = cur.fetchone()[0]
                return Status(result)
        
    @status.setter
    def status(self, value: Status):
        with closing(pool.get_connection()) as con:
            with closing(con.cursor()) as cur:
                cur.execute('UPDATE `users` SET `status` = %s WHERE `chat_id` = %s', (value.value, self.chat_id))
                con.commit()

    def __getitem__(self, item: str):
        match item:
            case 'show_timestamps':
                return self.show_timestamps
            case 'show_extended_info':
                return self.show_extended_info
            case 'rasp_entity':
                return self.rasp_entity
            case 'status':
                return self.status
            case 'sub_entity':
                return self.sub_entity
            case 'surname':
                return self.surname
            case 'ej_group':
                return self.ej_group
            case 'birth':
                return self.birth
            case 'ej_sub':
                return self.ej_sub
            case _:
                raise KeyError('Invalid key: {}'.format(item))
    
    def __setitem__(self, key: str, value: any):
        match key:
            case 'show_timestamps':
                self.show_timestamps = value
            case 'show_extended_info':
                self.show_extended_info = value
            case 'mark_entity':
                self.mark_entity = value
            case 'status':
                self.status = value
            case 'sub_entity':
                self.sub_entity = value
            case 'surname':
                self.surname = value
            case 'ej_group':
                self.ej_group = value
            case 'birth':
                self.birth = value
            case 'ej_sub':
                self.ej_sub = value
            case _:
                raise KeyError('Invalid key: {}'.format(key))
    
def get_subs() -> dict[RaspEntity, list[User]]:
    with closing(pool.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('SELECT DISTINCT(`sub_entity`) FROM `users` WHERE `sub_entity` IS NOT NULL')
            result = cur.fetchall()
            rasp_entities_ids = [r[0] for r in result]
            subs = {}
            for rasp_entity_id in rasp_entities_ids:
                cur.execute('SELECT `entity_id`, `type`, `name` FROM `rasp_entities` WHERE `id` = %s', (rasp_entity_id,))
                result = cur.fetchone()
                rasp_entity = RaspEntity(result[0], RaspEntityType(result[1]), result[2])
                cur.execute('SELECT `chat_id` FROM `users` WHERE `sub_entity` = %s', (rasp_entity_id,))
                result = cur.fetchall()
                subs[rasp_entity] = [User(int(r[0])) for r in result]
            return subs

def get_ej_subs() -> list[User]:
    with closing(pool.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('SELECT `chat_id` FROM `users` WHERE `ej_sub` = 1')
            result = cur.fetchall()
            return [User(int(r[0])) for r in result]

def get_all_users() -> list[int]:
    with closing(pool.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('SELECT `chat_id` FROM `users`')
            result = cur.fetchall()
            return [int(r[0]) for r in result]

def with_user(f: Callable):
    @wraps(f)
    def wrapper(event: events.NewMessage.Event | events.CallbackQuery.Event, *args, **kwargs):        
        return f(event, User(event.chat_id), *args, **kwargs)
    return wrapper

class Mark:
    def __init__(self, mark: str = '', name: str = '', month: str = '', day: str = '', title: str = ''):
        self.mark = mark
        self.name = name
        self.month = month
        self.day = day
        self.title = title

    def __hash__(self):
        return hash((self.mark, self.name, self.month, self.day, self.title))

    def __eq__(self, other):
        if not isinstance(other, type(self)): return NotImplemented
        return self.mark == other.mark and self.name == other.name and self.month == other.month and self.day == other.day and self.title == other.title
    
def get_marks(user: User) -> list[Mark]:
    with closing(pool.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('SELECT `mark`, `name`, `month`, `day`, `title` FROM `ej_marks` WHERE `chat_id` = %s', (user.chat_id,))
            result = cur.fetchall()
            return [Mark(*r) for r in result]

def add_marks(user: User, marks: list[Mark]):
    with closing(pool.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.executemany('INSERT INTO `ej_marks` (`chat_id`, `mark`, `name`, `month`, `day`, `title`) VALUES (%s, %s, %s, %s, %s, %s)', [(user.chat_id,)+tuple(mark.__dict__.values()) for mark in marks])
            con.commit()

def get_average_data(user: User) -> list[Mark]:
    with closing(pool.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('SELECT `mark`, `name` FROM `ej_average_data` WHERE `chat_id` = %s', (user.chat_id,))
            result = cur.fetchall()
            return [Mark(*r) for r in result]

def replace_average_data(user: User, marks: list[Mark]):
    with closing(pool.get_connection()) as con:
        with closing(con.cursor()) as cur:
            cur.execute('DELETE FROM `ej_average_data` WHERE `chat_id` = %s', (user.chat_id,))
            cur.executemany('INSERT INTO `ej_average_data` (`chat_id`, `mark`, `name`) VALUES (%s, %s, %s)', [(user.chat_id, mark.mark, mark.name) for mark in marks])
            con.commit()
