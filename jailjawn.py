import requests
from lxml import html

from Facility import Facility

unicode_whitespace = "[u"+"'\\"+"xa0']"
#print unicode_whitespace
#ws_array = [unicode_whitespace]
#print ws_array[0];
page = requests.get('http://www.phila.gov/prisons/page.htm')
tree = html.fromstring(page.content)

def getxpath(columnNumber):
    return tree.xpath('//tr[14]/td[%i]/text()' % columnNumber)

argumentsArray = []
for i in range(1, 16, 1):
    argumentsArray.append(getxpath(i))
    #print getxpath(i)
    temp=str(getxpath(i))
    print temp
    if temp==unicode_whitespace:
        print True
    else:
        print False
    # return temp == unicode_whitespace

    # if temp == unicode_whitespace:
    #     print True
    # else:
    #     #print type(temp)
    #     #print type(unicode_whitespace)
    #     #print(getxpath(i))
    #     print False

f = Facility(* argumentsArray)

print(f.facilityName, f.adultMaleCount, f.adultFemaleCount, f.juvenileMaleCount, f.juvenileFemaleCount,
      f.inCountOutCountMale, f.inCountOutCountFemale, f.workersMale, f.workersFemale, f.furloughMale, f.furloughFemale,
      f.openWardMale, f.openWardFemale, f.emergTripsMale, f.emergTripsFemale)


#Return string from the list created by getxpath.
#Can't access items in list of things
#Check to see if there is anything in the list FIRS
#If there is pull that out and return it
#IF empty return a empty string