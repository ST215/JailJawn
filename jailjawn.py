import requests
from lxml import html
from Facility import Facility

non_interesting_data = "[u" + "'\\" + "xa0']"
page = requests.get('http://www.phila.gov/prisons/page.htm')
tree = html.fromstring(page.content)


def getxypath(columnNumber, rowNumber):
    return tree.xpath('//tr[%i]/td[%i]/text()' % (columnNumber, rowNumber))


argumentsArray = []
for individual_row_item in range(1, 30, 1):
    if str(getxypath(individual_row_item, 1)) == '[]' or str(getxypath(individual_row_item, 1)) == non_interesting_data:
        print "DEBUGGING ....... loop removed the " + str(getxypath(individual_row_item, 1))
        continue
    for individual_column_item in range(1, 16, 1):
        facilityCellData = str(getxypath(individual_row_item, individual_column_item))
        if facilityCellData == non_interesting_data:
            argumentsArray.append(['0'])
        else:
            argumentsArray.append(getxypath(individual_row_item, individual_column_item))

    f = Facility(*argumentsArray)
    print(f.facilityName, f.adultMaleCount, f.adultFemaleCount, f.juvenileMaleCount, f.juvenileFemaleCount,
          f.inCountOutCountMale, f.inCountOutCountFemale, f.workersMale, f.workersFemale, f.furloughMale,
          f.furloughFemale,
          f.openWardMale, f.openWardFemale, f.emergTripsMale, f.emergTripsFemale)
    argumentsArray = []



# Dynamic Row checkers
# Go through Every signle row, start adding things to list of Non interesting shit i.e. Unicode white space, totals, etc.
# Update the checker (loop) if we encounter non interesting shit do not perform the inner loop, move on to the next one.
