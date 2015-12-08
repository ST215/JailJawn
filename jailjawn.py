from lxml import html
import requests

class Facility:
    def __init__(self, facilityName, adultMaleCount, adultFemaleCount, juvenileMaleCount, juvenileFemaleCount,
                 inCountOutCountMale, inCountOutCountFemale, workersMale, workersFemale, furloughMale,
                 furloughFemale, openWardMale, openWardFemale):

        self.facilityName =  facilityName
        self.adultMaleCount =  adultMaleCount
        self.adultFemaleCount =  adultFemaleCount
        self.juvenileMaleCount =  juvenileMaleCount
        self.juvenileFemaleCount =  juvenileFemaleCount
        self.inCountOutCountMale =  inCountOutCountMale
        self.inCountOutCountFemale =  inCountOutCountFemale
        self.workersMale =  workersMale
        self.workersFemale =  workersFemale
        self.FurloughMale =  furloughMale
        self.FurloughFemale =  furloughFemale
        self.openWardMale =  openWardMale
        self.openWardFemale =  openWardFemale


page = requests.get('http://www.phila.gov/prisons/page.htm')
tree = html.fromstring(page.content)

f = Facility(tree.xpath('//tr[14]/td[1]/text()'),
                tree.xpath('//tr[14]/td[2]/text()'),
                tree.xpath('//tr[14]/td[3]/text()'),
                tree.xpath('//tr[14]/td[4]/text()'),
                tree.xpath('//tr[14]/td[5]/text()'),
                tree.xpath('//tr[14]/td[6]/text()'),
                tree.xpath('//tr[14]/td[7]/text()'),
                tree.xpath('//tr[14]/td[8]/text()'),
                tree.xpath('//tr[14]/td[9]/text()'),
                tree.xpath('//tr[14]/td[10]/text()'),
                tree.xpath('//tr[14]/td[11]/text()'),
                tree.xpath('//tr[14]/td[12]/text()'),
                tree.xpath('//tr[14]/td[13]/text()')
                )


print(f.facilityName, f.adultMaleCount, f.adultFemaleCount, f.juvenileMaleCount, f.juvenileFemaleCount,
      f.inCountOutCountMale, f.inCountOutCountFemale, f.workersMale, f.workersFemale, f.FurloughMale, f.FurloughFemale,
      f.openWardMale, f.openWardFemale)


