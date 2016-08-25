#!/usr/bin/ipython
# coding: utf8

from BeautifulSoup import BeautifulSoup
from PIL import Image
import datetime
import cookielib
import mechanize
import grequests
import json
import os
import pandas
import re
import sys
import urllib2
import zipfile

cookjar = cookielib.CookieJar()
urllib2.build_opener(urllib2.HTTPCookieProcessor(cookjar)).open(urllib2.Request("http://maree.info/"))

maree_cookie = dict((cookie.name, cookie.value) for cookie in cookjar)['PHPSESSID']

def parse_tide(day, month, year):
    opener = urllib2.build_opener()
    opener.addheaders.append(('Cookie', 'PHPSESSID=' + maree_cookie))

    image = Image.open(opener.open("http://maree.info/maree-graph.php?p=135&d=%d%02d%02d&ut=2" % (year, month, day)))
    pix = image.load()

    height = {}
    pos = (61, 445)
    for index, i in enumerate(range(pos[0], pos[1], 4)):
        for j in range(5, 240):
            color = pix[i, j]
            if (color[2] > (color[1] + 20) and color[2] > (color[0] + 20) and color[3]):
                try:
                    height[index / 4][index % 4] = (1 - ((j - 5) / 234.0)) * 4.5
                except:
                    height[index / 4] = [0] * 4
                    height[index / 4][index % 4] = (1 - ((j - 5) / 234.0)) * 4.5
                break
    return height

def save_to_file(relative_path, data):
    print "   - Saving into " + relative_path
    fs = open(os.path.dirname(os.path.abspath(__file__)) + "/" + relative_path, 'w+')
    fs.write(data)

def order_data(res):
    data = json.loads(res)
    data.sort(key = lambda arr: arr["date"])
    return json.dumps(data)

# Loading configuration, needed for data_source and secret
secret_json = os.path.dirname(os.path.abspath(__file__)) + "/../PRIVATE.json"
with open(secret_json) as configuration_json:
    configuration = json.load(configuration_json)

print
print "Fetching infos of all places..."
places_url = configuration["data_source"] + "/allPlacesInfos"
places = urllib2.urlopen(places_url).read()
print "  Saving..."
save_to_file("../data/sensors/all_places_infos.json", places)

print
print "Fetching weather"
weather = urllib2.urlopen("https://api.forecast.io/forecast/c981b0c8c612767197de22589175c656/44.8404400,-0.5805000?units=si").read()

sys.stdout.write('\r')
sys.stdout.flush()
save_to_file("../data/weather_forecast.json", weather)

###############################################################################

print
print "Fetching tides height"

startdate = datetime.datetime.now().date()
enddate = datetime.date(2018,1,1)
delta = enddate - startdate
days = [startdate + datetime.timedelta(days=i) for i in range(delta.days + 1)]
tides = {}

for i, mydate in enumerate(days):
    sys.stdout.write('\r  ' + str(i * 100 / len(days) + 1) + '%')
    sys.stdout.flush()

    try:
        tides[mydate.year]
    except:
        tides[mydate.year] = {}
    try:
        tides[mydate.year][mydate.month]
    except:
        tides[mydate.year][mydate.month] = {}
    try:
        tides[mydate.year][mydate.month][mydate.day] = parse_tide(mydate.day, mydate.month, mydate.year)
    except:
        pass

sys.stdout.write('\r')
sys.stdout.flush()
save_to_file("../data/predict_tides.json", json.dumps(tides))

print
print "Done!"
