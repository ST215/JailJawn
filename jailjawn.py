import requests
from bs4 import BeautifulSoup

url = "http://www.phila.gov/prisons/page.htm"
r = requests.get(url)

soup = BeautifulSoup(r.content)

prison_data = soup.find_all("tr")

for item in prison_data:
    print item.get_text()
