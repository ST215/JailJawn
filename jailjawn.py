import requests
from lxml import html
from firebase import firebase
from datetime import datetime


non_interesting_data = ['#REF!', '[]', u'\xa0', '0']
page = requests.get('http://www.phila.gov/prisons/page.htm')
tree = html.fromstring(page.content)
default_value = '0'
keys = ['', 'Facility Name', 'Adult Male', 'Adult Female', 'Juvenile Male', 'Juvenile Female', 'In Out Male','In Out Female', 'Worker Male', 'Worker Female', 'Furlough Male', 'Furlough Female', 'Open Ward Male', 'Open Ward Female', 'Emergecy Room Trip Male', 'Emergecy Room Trip Female', 'Total Count']
FIREBASE_URL = "https://jailjawndev.firebaseio.com/"
fb = firebase.FirebaseApplication(FIREBASE_URL, None) # Create a reference to the Firebase Application


# Main
if __name__ == '__main__':


    def readValue(element):
        value = element.text
        if not value: return default_value
        if len(value) == 0:
            return default_value
        else:
            if value[0] in non_interesting_data:
                return default_value
            else:
                return value[0]

    def getxypath(columnNumber, rowNumber):
        value = tree.xpath('//tr[%i]/td[%i]/text()' % (columnNumber, rowNumber))
        # print value
        if len(value) == 0:
            return default_value
        else:
            if value[0] in non_interesting_data:
                return default_value
            else:
                return value[0]


    def getRows():
        rows = tree.xpath('//tr')
        return rows[6:40]


    dateOnPrisonCensus = datetime.strptime(getxypath(2, 2), "%B %d, %Y").date()

    print dateOnPrisonCensus

    def prisonParser(acc, row):
        facilityname = row[0].text
        columnElements = row[1:16]
        columnTexts = [row[0].text] + map(readValue, columnElements)

        acc[facilityname] = { key: value for key,value in zip(keys[1:], columnTexts) }
        return acc


    def parseTable():
        rows = getRows()
        prisons = reduce(prisonParser, rows, {})
        print prisons
        fb.post(str(dateOnPrisonCensus), 'ASD Cannery', prisons)
        # iterate over all the rows and call prisonParser on them
        # Aggregate all PrisonParsers' results and create a bigger object
        # Return
    parseTable()