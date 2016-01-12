import requests
from lxml import html
from Facility import Facility

non_interesting_data = ['#REF!', '[]', u'\xa0', '0']
page = requests.get('http://www.phila.gov/prisons/page.htm')
tree = html.fromstring(page.content)
default_value = '0'

def getxypath(columnNumber, rowNumber):
    value = tree.xpath('//tr[%i]/td[%i]/text()' % (columnNumber, rowNumber))
    if len(value) == 0:
        return default_value
    else:
        return value[0]

argumentsArray = []
for individual_row_item in range(1, 40, 1):
    if not getxypath(individual_row_item, 1) in non_interesting_data:
        for individual_column_item in range(1, 16, 1):
            facilityCellData = getxypath(individual_row_item, individual_column_item)
            if facilityCellData in non_interesting_data:
                argumentsArray.append(default_value)
            else:
                if facilityCellData.isdigit():
                    argumentsArray.append(float(facilityCellData))
                else:
                    argumentsArray.append(facilityCellData.replace('\r\n', ''))

        f = Facility(*argumentsArray)
        print(f.facilityName, f.adultMaleCount, f.adultFemaleCount, f.juvenileMaleCount, f.juvenileFemaleCount,
              f.inCountOutCountMale, f.inCountOutCountFemale, f.workersMale, f.workersFemale, f.furloughMale,
              f.furloughFemale,
              f.openWardMale, f.openWardFemale, f.emergTripsMale, f.emergTripsFemale)
        argumentsArray = []
