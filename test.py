"""
import re

def get_image_id(iterable):
    for each in iterable:
        yield re.search(pattern=pattern, string=each).group(1)



from gsheet import GoogleSheet
gs = GoogleSheet(token='token_swan.pickle')
SS = '1lTaA0MnfDcsDxI0N1fqld8-ZJKg4mZwN0sEoNX_YJ3E'
R = 'ASINs!A:F'

pattern = '^.+/I/(.+)\._'
pattern = 'I/(.+?)\.'
master_data = gs.get_values(SPREADSHEET_ID=SS, RANGE_NAME=R)['values'][1:]
asins = [x[1] for x in master_data]
images = [x[5].split('\n') for x in master_data]

ids_list = list(get_image_id(images[0]))
print(ids_list)
"""
"""
final_data = zip(asins, images_id)
from pprint import pprint
pprint(list(final_data))


browser_dict = {'chrome': 0, 'firefox': 0}

for a in range(0, 5):
    if list(browser_dict.values()).count(0) == 2:
        print('chrome')
        browser_dict['chrome'] = 1
    elif browser_dict['chrome'] == 1:
        print('firefox')
        browser_dict['chrome'] = 0
        browser_dict['firefox'] = 1
    elif browser_dict['firefox'] == 1:
        print('chrome')
        browser_dict['chrome'] = 1
        browser_dict['firefox'] = 0

print(browser_dict)
for each in browser_dict:
    if browser_dict[each] == 1:
        print(each)
"""
from collections import namedtuple
Ticket = namedtuple('Ticket', [
         'id',
          123,
          23])

result = []
ticket = Ticket('123', 'amz', 'Igor')
result.append(Ticket('123', 'amz', 'Igor'))
result.append(Ticket('221', 'ebay', 'Sasha'))
print(result)
