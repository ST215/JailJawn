from lxml import html
import requests

page = requests.get('http://www.phila.gov/prisons/page.htm')
tree = html.fromstring(page.content)

#Sample code to test implmentation
facility = tree.xpath('//tr[14]/td[1]/text()')
maleCount = tree.xpath('//tr[14]/td[2]/text()')
openWard = tree.xpath('//tr[14]/td[12]/text()')
total = tree.xpath('//tr[14]/td[16]/text()')
hospitals = tree.xpath('//tr[14]/td[17]/text()')

#Results
print 'Facility: ', facility
print 'maleCount: ', maleCount
print 'Open Ward: ', openWard
print 'Total: ', total
print 'Hospitals: ', hospitals
