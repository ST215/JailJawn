import requests
from bs4 import BeautifulSoup

url = "http://www.phila.gov/prisons/page.htm"
r = requests.get(url)

soup = BeautifulSoup(r.content)

print soup
