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
        return tree.xpath('//tr[14]/td[%i]/text()' % (columnNumber))

f = Facility(getxpath(1),
                getxpath(2),
                getxpath(3),
                tree.xpath('//tr[14]/td[4]/text()'),
                tree.xpath('//tr[14]/td[5]/text()'),
                tree.xpath('//tr[14]/td[6]/text()'),
                tree.xpath('//tr[14]/td[7]/text()'),
                tree.xpath('//tr[14]/td[8]/text()'),
                tree.xpath('//tr[14]/td[9]/text()'),
                tree.xpath('//tr[14]/td[10]/text()'),
                tree.xpath('//tr[14]/td[11]/text()'),
                tree.xpath('//tr[14]/td[12]/text()'),
                tree.xpath('//tr[14]/td[13]/text()'),
                tree.xpath('//tr[14]/td[14]/text()'),
                tree.xpath('//tr[14]/td[15]/text()')
                )

print(f.facilityName, f.adultMaleCount, f.adultFemaleCount, f.juvenileMaleCount, f.juvenileFemaleCount,
      f.inCountOutCountMale, f.inCountOutCountFemale, f.workersMale, f.workersFemale, f.furloughMale, f.furloughFemale,
      f.openWardMale, f.openWardFemale, f.emergTripsMale, f.emergTripsFemale)


