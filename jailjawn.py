import requests
from lxml import html

from Facility import Facility

unicode_whitespace = "[u"+"'\\"+"xa0']"
page = requests.get('http://www.phila.gov/prisons/page.htm')
tree = html.fromstring(page.content)

def getxpath(columnNumber):
    return tree.xpath('//tr[7]/td[%i]/text()' % columnNumber)

def getxypath( columnNumber):
    return tree.xpath('//tr[j]/td[%i]/text()' % columnNumber)

argumentsArray = []
for j in range (7, 30, 1):
    for i in range(1, 16, 1):


        temp=str(getxypath(i))
        print temp
        if temp==unicode_whitespace:
            argumentsArray.append(0)
            #print True
        else:
            argumentsArray.append(getxypath(i))
            #print False

    f = Facility(* argumentsArray)
    print(f.facilityName, f.adultMaleCount, f.adultFemaleCount, f.juvenileMaleCount, f.juvenileFemaleCount,
      f.inCountOutCountMale, f.inCountOutCountFemale, f.workersMale, f.workersFemale, f.furloughMale, f.furloughFemale,
      f.openWardMale, f.openWardFemale, f.emergTripsMale, f.emergTripsFemale)
    argumentsArray = []



#Return string from the list created by getxpath.
#Can't access items in list of things
#Check to see if there is anything in the list FIRS
#If there is pull that out and return it
#IF empty return a empty string