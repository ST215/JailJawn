from lxml import html
import requests

class Facility:
    def __init__(self, facilityName, adultMaleCount):
        self.facilityName =  facilityName
        self.adultMaleCount =  adultMaleCount


page = requests.get('http://www.phila.gov/prisons/page.htm')
tree = html.fromstring(page.content)

f = Facility(tree.xpath('//tr[14]/td[1]/text()'),
                tree.xpath('//tr[14]/td[2]/text()')
                )


print(f.facilityName, f.adultMaleCount)


