# JailJawn
Data Source: (http://www.phila.gov/prisons/page.htm)

##What is Jail Jawn and Why?
Jail Jawn is a project for me to get better a programming in general and provide some good in the process.
The Philadelphia Prisons System updates a daily census (Human Generated not automated) of the count of all inmates at each facility, their status, and location location within the prison system. NOTE: This static page is sometimes updated in frequently. Largest Gap noticated was from December 29th 2015 to January 10th 2016

Whoever in the Philadelphia Prisions System is publishing the data using Microsoft Excel Publish as a Webpage Wizard (AWFUL AWFUL HTML OUTPUT). I tried my best to parse the data to dictionaries so I can export to CSV or JSON but with my current skill level and the state of that HTML OUTPUT that isn't happening. I wanted to use Beautiful Soup and lxml in Python which proved to be very hard and time wasting.

I am going to covert the data I want to strings and build my own system of getting the text into CSV or JSON.

##Team
###Core
Stanley H. Griggs II<br />
@st215 Twitter/Instagram<br />
StanleyGriggs.com<br />

###Advisors
Mike<br />
Dan<br />
Ivan<br />

##Goal
Historical Inmate Data, Beautiful Charts, and The Ability see trends over time.

## Tech:
Python Requests (http://docs.python-requests.org/en/latest/)
Python lxml (http://lxml.de/)


##Steps to run on Windows
####Download Python

	1. http://docs.python-requests.org/en/latest/user/install/#install

####Set up Python Path

	1. Open Control Panel
	2. Go To Security and Systems
	3. Go to System
	4. Open Advanced System Settings
	5. Go to the "Advanced" tab and open Environmental Variables
	6. Scoll down to "Path" in System Variables and then double-click
	7. Add the local address of your Python library to the Variable Value field (For example: C:\Python27)
		-If there are any other paths in the field then seperate them with a semicolon (For example C:\Java_lib;C:\Python27)
####Download Requests

	1. clone git://github.com/kennethreitz/requests.git
	2. Open terminal and run python setup.py install

####Download lxml

	1. https://pypi.python.org/pypi/lxml/3.2.3


