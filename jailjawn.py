import requests
from lxml import html
from Facility import Facility

non_interesting_data = ["[u" + "'\\" + "xa0']", "['#REF!']", "[]"]
page = requests.get('http://www.phila.gov/prisons/page.htm')
tree = html.fromstring(page.content)


def getxypath(columnNumber, rowNumber):
    return tree.xpath('//tr[%i]/td[%i]/text()' % (columnNumber, rowNumber))

argumentsArray = []
for individual_row_item in range(1, 40, 1):
    if str(getxypath(individual_row_item, 1)) in non_interesting_data:
        continue
    for individual_column_item in range(1, 16, 1):
        facilityCellData = str(getxypath(individual_row_item, individual_column_item))
        if facilityCellData in non_interesting_data:
            argumentsArray.append(['0'])
        else:
            argumentsArray.append(getxypath(individual_row_item, individual_column_item))

    f = Facility(*argumentsArray)
    print(f.facilityName, f.adultMaleCount, f.adultFemaleCount, f.juvenileMaleCount, f.juvenileFemaleCount,
          f.inCountOutCountMale, f.inCountOutCountFemale, f.workersMale, f.workersFemale, f.furloughMale,
          f.furloughFemale,
          f.openWardMale, f.openWardFemale, f.emergTripsMale, f.emergTripsFemale)
    argumentsArray = []
