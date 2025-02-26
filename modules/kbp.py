from lxml import html
from io import BytesIO
import requests
from functools import lru_cache
import time
from .utils import cache
from .db_utils import RaspEntity, RaspEntityType, Mark
from enum import Enum
from itertools import chain

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
}

zvonki = {'regular': ['8:00', '8:55', '9:50', '10:45', '12:00', '12:55', '14:00', '14:55', '15:50', '16:45', '17:40', '18:35', '19:30'],
          'thursday': ['8:00', '8:55', '9:50', '10:45', '12:00', '12:55', '14:40', '15:35', '16:30', '17:25', '18:20', '19:15', '20:10'],
          'saturday': ['8:00', '8:55', '9:50', '10:45', '11:40', '12:35', '13:40', '14:35', '15:30', '16:25', '17:20', '18:15', '19:10']}

class PairType(Enum):
    DEFAULT = 'default'
    REMOVED = 'removed'
    EMPTY = 'empty'
    ADDED = 'added'
    CHANGED = 'changed'

class Pair:
    def __init__(self):
        self.time: str = ''
        self.number: int = 0
        self.type: PairType = PairType.EMPTY
        self.names: list[str] = []
        self.places: list[str] = []
        self.teachers: list[str] = []
        self.groups: list[str] = []

class Weekday:
    __weeklabels = ['ПОНЕДЕЛЬНИК', 'ВТОРНИК', 'СРЕДА', 'ЧЕТВЕРГ', 'ПЯТНИЦА', 'СУББОТА']
    def __init__(self, number: int, zamena: str):
        self.number = number
        self.zamena = zamena
        self.pairs: list[Pair] = []

    @property
    def name(self) -> str:
        return self.__weeklabels[self.number]

class Rasp:
    __url = 'https://kbp.by/rasp/timetable/view_beta_kbp/?cat={}&id={}'
    __list_url = 'https://kbp.by/rasp/timetable/view_beta_kbp/?q='

    def check_rasp(self, weekday: int, left_week: bool = True) -> bool:
        html_page = requests.get(self.__url.format('group', '10'), headers=headers).content
        page = html.parse(BytesIO(html_page))
        zamena = page.getroot().get_element_by_id('left_week' if left_week else 'right_week').cssselect('tr')[1].cssselect('th')[weekday + 1].text_content()
        return zamena.find('Замен нет') != -1 or zamena.find('Показать замены') != -1

    def get_rasp_list(self) -> list[RaspEntity]:
        html_page = requests.get(self.__list_url, headers=headers).content
        page = html.parse(BytesIO(html_page))
        rasp_list = []

        container = page.getroot().find_class('block_back')[0]
        for entry in container.cssselect('div')[2:]:
            type = RaspEntityType.by_label(entry.find_class('type_find')[0].text_content())
            a = entry.cssselect('a')[0]
            name = str(a.text_content())
            id = int(a.get('href').split('=')[-1])
            entity = RaspEntity(id, type, name)
            rasp_list.append(entity)
        return rasp_list
    
    @cache(copy=True, ttl=60)
    def get_rasp(self, entity: RaspEntity) -> dict[str, list[Weekday]]:
        html_page = requests.get(self.__url.format(entity.type.value, entity.id), headers=headers).content
        page = html.parse(BytesIO(html_page))

        rasp = {}

        weekdiv = page.getroot().get_element_by_id('left_week')
        rasp['left'] = self.__get_week(weekdiv)
        weekdiv = page.getroot().get_element_by_id('right_week')
        rasp['right'] = self.__get_week(weekdiv)

        return rasp

    def __get_week(self, weekdiv: html.HtmlElement) -> list[Weekday]:
        rows = weekdiv.cssselect('tr')[1:-2]
        zamena_row = rows.pop(0)
        zamena_cells = zamena_row.cssselect('th')[1:-1]

        rasp: list[Weekday] = []

        for i, cell in enumerate(zamena_cells):
            zamena_label = cell.text_content().strip()
            if zamena_label == 'Показать замены':
                zamena_label = 'Замены:'
            rasp.append(Weekday(i, zamena_label))

        for row in rows:
            if len(row.find_class('pair')) == 0:
                continue
            cells = row.cssselect('td')[:-1]
            number_cell = cells.pop(0)
            pair_number = int(number_cell.text_content())
            for i, cell in enumerate(cells):
                pair = self.__extract_pair(cell)
                pair.number = pair_number
                match i:
                    case 3:
                        pair.time = zvonki['thursday'][pair_number - 1]
                    case 5:
                        pair.time = zvonki['saturday'][pair_number - 1]
                    case _:
                        pair.time = zvonki['regular'][pair_number - 1]
                rasp[i].pairs.append(pair)

        return rasp

    def __extract_pair(self, table_cell: html.HtmlElement) -> Pair:
        pair_divs = table_cell.find_class('pair')

        match len(pair_divs):
            case 0:
                return Pair()
            case 1:
                pair_div = pair_divs[0]
                pair = Pair()
                if 'removed' in pair_div.classes:
                    pair.type = PairType.REMOVED
                    pair.names.append('Урок снят')
                elif 'added' in pair_div.classes:
                    pair = self.__extract_pair_data(pair_div)
                    pair.type = PairType.ADDED
                else:
                    pair = self.__extract_pair_data(pair_div)
                    pair.type = PairType.DEFAULT
                return pair
            case _:
                classes = chain.from_iterable(pair_div.classes for pair_div in pair_divs)
                if 'removed' in classes:
                    for pair_div in pair_divs:
                        if 'added' in pair_div.classes:
                            pair = self.__extract_pair_data(pair_div)
                            if pair.names[0] == 'Урок снят':
                                pair.type = PairType.REMOVED
                                pair.places.pop()
                            else:
                                pair.type = PairType.CHANGED
                            return pair
                    pair = Pair()
                    pair.type = PairType.REMOVED
                    pair.names.append('Урок снят')
                    return pair
                else:
                    pair = Pair()
                    pair.type = PairType.DEFAULT
                    for pair_div in pair_divs:
                        pair_data = self.__extract_pair_data(pair_div)
                        pair.names.extend(pair_data.names)
                        pair.places.extend(pair_data.places)
                        pair.groups.extend(pair_data.groups)
                        pair.teachers.extend(pair_data.teachers)
                    return pair

    def __extract_pair_data(self, pair_div: html.HtmlElement) -> Pair:
        pair = Pair()

        pair.names.append(pair_div.find_class('subject')[0].text_content())
        pair.places.append(pair_div.find_class('place')[0].text_content())
        pair.groups.append(pair_div.find_class('group')[0].text_content())
        teachers = pair_div.find_class('teacher')
        pair.teachers.append(teachers[0].text_content())
        second_teacher = teachers[1].text_content()
        if second_teacher != '':
            pair.teachers.append(second_teacher)

        return pair

class Journal:
    __login_page = 'http://ej.kbp.by/templates/login_parent.php'
    __ajax_page = 'http://ej.kbp.by/ajax.php'
    __journal_page = 'http://ej.kbp.by/templates/parent_journal.php'
    __logout_page = 'http://ej.kbp.by/index.php?logout'

    monthlabels = {'январь': '01', 'февраль': '02', 'март': '03', 'апрель': '04', 'май': '05', 'июнь': '06', 'июль': '07', 'август': '08', 'сентябрь': '09', 'октябрь': '10', 'ноябрь': '11', 'декабрь': '12'}

    def __login(self, surname: str, group: str | int, birth: str) -> dict[str, str] | None:
        res = requests.get(self.__login_page, headers=headers)
        cookie = {'Cookie': res.headers['Set-Cookie'].split(';')[0]}
        s_code = html.parse(BytesIO(res.content)).getroot().get_element_by_id('S_Code').value
        data = {'action': 'login_parent', 'student_name': surname, 'group_id': group, 'birth_day': birth, 'S_Code': s_code}
        res = requests.post(self.__ajax_page, data=data, headers=headers|cookie)
        if res.text == 'good':
            return cookie
        else:
            return None

    def get_ej(self, surname, group, birth) -> list[Mark] | None:
        cookie = self.__login(surname, group, birth)
        if cookie is None:
            return None
        marks = []
        with open('ej.html', 'wb') as f:
            f.write(requests.get(self.__journal_page, headers=headers|cookie|{'Referer': self.__journal_page}).content)
        page = html.parse(BytesIO(requests.get(self.__journal_page, headers=headers|cookie|{'Referer': self.__journal_page}).content), parser=html.HTMLParser(encoding='utf-8'))
        names = page.getroot().find_class('leftColumn').pop()
        names_rows = names.cssselect('tr')[2:-1]
        mark_table = page.getroot().find_class('rightColumn').pop()
        months = mark_table.get_element_by_id('months').cssselect('td')[:-1]
        months_nums = [int(m.get('colspan')) for m in months]
        days = mark_table.get_element_by_id('dateOfMonth').cssselect('div')
        mark_rows = mark_table.cssselect('tr')[2:-1]

        for i in range(len(names_rows)):
            name = names_rows[i].cssselect('div').pop().text_content().strip()
            mark_columns = mark_rows[i].cssselect('td')[:-1]
            for j in range(len(mark_columns)):
                div = mark_columns[j].cssselect('div').pop()
                spans = div.cssselect('span')
                if len(spans) == 0:
                    continue
                mark = Mark()
                mark.title = div.get('title')
                mark.name = name
                mark.day = str(days[j].text_content())
                for k in range(len(months)):
                    if j in range(sum(months_nums[:k+1])):
                        mark.month = self.monthlabels[months[k].cssselect('div').pop().text_content()]
                        break
                for span in spans:
                    mark.mark += ' ' + span.text_content()
                mark.mark = mark.mark[1:]
                marks.append(mark)

        requests.get(self.__logout_page, headers=headers|cookie)
        return marks

    def get_average(self, surname, group, birth) -> list[Mark] | None:
        cookie = self.__login(surname, group, birth)
        if cookie is None:
            return None
        marks = []
        page = html.parse(BytesIO(requests.get(self.__journal_page, headers=headers|cookie|{'Referer': self.__journal_page}).content), parser=html.HTMLParser(encoding='utf-8'))
        names = page.getroot().find_class('leftColumn').pop()
        names_rows = names.cssselect('tr')[2:-1]
        mark_table = page.getroot().find_class('rightColumn').pop()
        mark_rows = mark_table.cssselect('tr')[2:-1]
        mark_columns = [row.cssselect('td').pop() for row in mark_rows]

        sum = 0
        count = 0
        for i in range(len(names_rows)):
            mark = Mark()
            mark.name = names_rows[i].cssselect('div').pop().text_content().strip()
            mark.mark = mark_columns[i].cssselect('div').pop().text_content().strip()
            marks.append(mark)
            if mark.mark != '-':
                sum += float(mark.mark)
                count += 1

        general = Mark()
        general.name = '\n**Общий**'
        general.mark = str(round(sum / count, 1))
        marks.append(general)

        requests.get(self.__logout_page, headers=headers|cookie)
        return marks
