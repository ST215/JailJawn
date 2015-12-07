from lxml import html
import requests

class Facility:
    def __init__(self, facilityName, adultMaleCount, adultFemaleCount):
        self.facilityName =  facilityName
        self.adultMaleCount =  adultMaleCount
        self.adultFemaleCount =  adultFemaleCount


page = requests.get('http://www.phila.gov/prisons/page.htm')
tree = html.fromstring(page.content)

f = Facility(tree.xpath('//tr[14]/td[1]/text()'),
                tree.xpath('//tr[14]/td[2]/text()'),
                tree.xpath('//tr[14]/td[3]/text()')
                )


print(f.facilityName, f.adultMaleCount, f.adultFemaleCount)


