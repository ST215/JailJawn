import requests
from lxml import html
from firebase import firebase


non_interesting_data = ['#REF!', '[]', u'\xa0', '0']
page = requests.get('http://www.phila.gov/prisons/page.htm')
tree = html.fromstring(page.content)
default_value = '0'
keys = ['', 'Facility Name', 'Adult Male', 'Adult Female', 'Juvenile Male', 'Juvenile Female', 'In Out Male','In Out Female', 'Worker Male', 'Worker Female', 'Furlough Male', 'Furlough Female', 'Open Ward Male', 'Open Ward Female', 'Emergecy Room Trip Male', 'Emergecy Room Trip Female', 'Total Count']
FIREBASE_URL = "https://burning-heat-7610.firebaseio.com/"
fb = firebase.FirebaseApplication(FIREBASE_URL, None) # Create a reference to the Firebase Application


# Main
if __name__ == '__main__':
    def getxypath(columnNumber, rowNumber):
        value = tree.xpath('//tr[%i]/td[%i]/text()' % (columnNumber, rowNumber))
        print value
        if len(value) == 0:
            return default_value
        else:
            if value[0] in non_interesting_data:
                return default_value
            else:
                return value[0]

    


    argumentsArray = {}
    for individual_row_item in range(6, 40, 1):
        if not getxypath(individual_row_item, 1) in non_interesting_data:
            for individual_column_item in range(1, 17, 1):
                facilityCellData = getxypath(individual_row_item, individual_column_item)
                if facilityCellData.isdigit():
                    facilityCellData = int(facilityCellData) #argumentsArray.append(int(facilityCellData))
                else:
                    facilityCellData = facilityCellData.replace('\r\n', '')\
                        .replace('.', '') #argumentsArray.append(facilityCellData.replace('\r\n', ''))

                argumentsArray[keys[individual_column_item]] = facilityCellData
            data = {'Facility Name' : argumentsArray['Facility Name'],
                        'Adult Male' : argumentsArray['Adult Male'],
                        'Adult Female' : argumentsArray['Adult Female'],
                        'Juvenile Male' : argumentsArray['Juvenile Male'],
                        'Juvenile Female' : argumentsArray['Juvenile Female'],
                        'In Out Male' : argumentsArray['In Out Male'],
                        'In Out Female' : argumentsArray['In Out Female'],
                        'Worker Male' : argumentsArray['Worker Male'],
                        'Worker Female' : argumentsArray['Worker Female'],
                        'Furlough Male' : argumentsArray['Furlough Male'],
                        'Furlough Female' : argumentsArray['Furlough Female'],
                        'Open Ward Male' : argumentsArray['Open Ward Male'],
                        'Open Ward Female' : argumentsArray['Open Ward Female'],
                        'Emergecy Room Trip Male' : argumentsArray['Emergecy Room Trip Male'],
                        'Emergecy Room Trip Female' : argumentsArray['Emergecy Room Trip Female'],
                        'Total Count' : argumentsArray['Total Count']}

            fb.put('/test', argumentsArray['Facility Name'], data)
