import requests
from lxml import html
from Facility import Facility

non_interesting_data = ['#REF!', '[]', u'\xa0', '0']
page = requests.get('http://www.phila.gov/prisons/page.htm')
tree = html.fromstring(page.content)
default_value = '0'
keys = ['', '''Facility Name''', '''Adult Male''', '''Adult Female''', '''Juvenile Male''', '''Juvenile Female''', '''In/Out Count Male''','''In/Out Count Female''', '''Worker Male''', '''Worker Female''', '''Furlough Male''', '''Furlough Female''', '''Open Ward Male''', '''Open Ward Female''', '''Emergecy Room Trip Male''', '''Emergecy Room Trip Female''', '''Total''']

def getxypath(columnNumber, rowNumber):
    value = tree.xpath('//tr[%i]/td[%i]/text()' % (columnNumber, rowNumber))
    if len(value) == 0:
        return default_value
    else:
        if value[0] in non_interesting_data:
            return default_value
        else:
            return value[0]


argumentsArray = {}
for individual_row_item in range(6, 40, 1):
    if not getxypath(individual_row_item, 1) in non_interesting_data:
        for individual_column_item in range(1, 16, 1):
            facilityCellData = getxypath(individual_row_item, individual_column_item)
            if facilityCellData.isdigit():
                facilityCellData = int(facilityCellData) #argumentsArray.append(int(facilityCellData))
            else:
                facilityCellData = facilityCellData.replace('\r\n', '') #argumentsArray.append(facilityCellData.replace('\r\n', ''))

            argumentsArray[keys[individual_column_item]] = facilityCellData
        print(argumentsArray)

        f = Facility(*argumentsArray)
        #f.print_description()
