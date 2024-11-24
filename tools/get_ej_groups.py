import requests
from lxml import html
from io import BytesIO

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
}

url = 'http://ej.kbp.by/templates/login_parent.php'

page = html.parse(BytesIO(requests.get(url, headers=headers).content), parser=html.HTMLParser(encoding='utf-8'))
select = page.getroot().get_element_by_id('group_id')

print('INSERT INTO ej_groups (`id`, `name`) VALUES')
first = True
for option in select.xpath('.//option'):
    if first:
        first = False
    else:
        print(',')
    print(f'({option.get("value")}, "{option.text}")', end='')
print(';')
