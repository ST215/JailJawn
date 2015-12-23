import requests
from lxml import html

from Facility import Facility

unicode_whitespace= u'\xa0'
page = requests.get('http://www.phila.gov/prisons/page.htm')
tree = html.fromstring(page.content)

def getxpath(columnNumber):
    return tree.xpath('//tr[16]/td[%i]/text()' % columnNumber)

argumentsArray = []
for i in range(1, 16, 1):
    argumentsArray.append(getxpath(i))

f = Facility(* argumentsArray)

print(f.facilityName, f.adultMaleCount, f.adultFemaleCount, f.juvenileMaleCount, f.juvenileFemaleCount,
      f.inCountOutCountMale, f.inCountOutCountFemale, f.workersMale, f.workersFemale, f.furloughMale, f.furloughFemale,
      f.openWardMale, f.openWardFemale, f.emergTripsMale, f.emergTripsFemale)


