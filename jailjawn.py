from lxml import html
import requests


class Facility:
    def __init__(self, facilityName, adultMaleCount, adultFemaleCount, juvenileMaleCount, juvenileFemaleCount,
                 inCountOutCountMale, inCountOutCountFemale, workersMale, workersFemale, furloughMale,
                 furloughFemale, openWardMale, openWardFemale, emergTripsMale, emergTripsFemale):

        self.facilityName = facilityName
        self.adultMaleCount = adultMaleCount
        self.adultFemaleCount = adultFemaleCount
        self.juvenileMaleCount = juvenileMaleCount
        self.juvenileFemaleCount = juvenileFemaleCount
        self.inCountOutCountMale = inCountOutCountMale
        self.inCountOutCountFemale = inCountOutCountFemale
        self.workersMale = workersMale
        self.workersFemale = workersFemale
        self.furloughMale = furloughMale
        self.furloughFemale = furloughFemale
        self.openWardMale = openWardMale
        self.openWardFemale = openWardFemale
        self.emergTripsMale = emergTripsMale
        self.emergTripsFemale = emergTripsFemale


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


