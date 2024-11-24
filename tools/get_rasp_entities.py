import requests
from lxml import html
from io import BytesIO

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
}

url = 'https://kbp.by/rasp/timetable/view_beta_kbp/?q='

page = html.parse(BytesIO(requests.get(url, headers=headers).content))
block = page.getroot().find_class('block_back')[0]

print('INSERT INTO rasp_entities (`entity_id`, `type`, `name`) VALUES')
first = True
for entity_link in block.xpath('.//div/a'):
    if first:
        first = False
    else:
        print(',')
    name = entity_link.text_content()
    href = entity_link.get('href').split('=')
    entity_id = href[2]
    type = href[1].split('&')[0]
    print(f'({entity_id}, {type}, "{name}")', end='')
print(';')
