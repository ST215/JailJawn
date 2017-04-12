# Jail Jawn
Data Source: (http://www.phila.gov/prisons/page.htm)

## What is Jail Jawn and Why?
This is the repository for the JailJawn.com scraper code written in Python. This started as a project to learn Python and Serverless deployment.

The following code in the repository accesses the static page provided by The City of Philadelphia Department of Prisons Census page (http://www.phila.gov/prisons/page.htm). This web page is generated internally possible by a human at infrequent times using Excel to HTML which doesn't create clean tables for scraping which requires a custom solution which as been implemented.

The Python code is deployed to Amazon Web Services Lambda running on a daily CRON job. Once the data is scraped via AWS Lambda it is pushed to our Google Firebase instance for permanent storage.

From the Google Firebase instance, we use Heroku to push the data API to the web using Javascript to render the charts on the client side.

The repositories for the those are located here:
API: https://github.com/JailJawn/JailJawnAPI 
WebApp / Site: https://github.com/JailJawn/jailjawnapp

Any questions I can be found on
Website: http://www.StanleyGriggs.com/

Twitter: http://www.twitter.com/ST215

Feel free to make issue tickets and suggestions.


## Goal
Historical Inmate Data, Beautiful Charts, and The Ability see trends over time.

## Tech:
Python Requests (http://docs.python-requests.org/en/latest/)
Python lxml (http://lxml.de/)


## Steps to run on Windows
#### Download Python

	1. http://docs.python-requests.org/en/latest/user/install/#install

#### Set up Python Path

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

#### Download lxml

	1. https://pypi.python.org/pypi/lxml/3.2.3
