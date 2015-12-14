import requests
from lxml import html

from Facility import Facility

page = requests.get('http://www.phila.gov/prisons/page.htm')
tree = html.fromstring(page.content)


def getxpath(columnNumber):
        return tree.xpath('//tr[14]/td[%i]/text()' % columnNumber)

f = Facility(getxpath(1),
             getxpath(2),
             getxpath(3),
             getxpath(4),
             getxpath(5),
             getxpath(6),
             getxpath(7),
             getxpath(8),
             getxpath(9),
             getxpath(10),
             getxpath(11),
             getxpath(12),
             getxpath(13),
             getxpath(14),
             getxpath(15))

print(f.facilityName, f.adultMaleCount, f.adultFemaleCount, f.juvenileMaleCount, f.juvenileFemaleCount,
      f.inCountOutCountMale, f.inCountOutCountFemale, f.workersMale, f.workersFemale, f.furloughMale, f.furloughFemale,
      f.openWardMale, f.openWardFemale, f.emergTripsMale, f.emergTripsFemale)


