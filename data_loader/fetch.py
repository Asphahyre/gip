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

def parse_weather(day, month, year):
    soup = BeautifulSoup(urllib2.urlopen("http://www.meteociel.fr/temps-reel/obs_villes.php?code2=7500&jour2=%s&mois2=%s&annee2=%s&envoyer=OK" % (day, month-1, year)).read())

    a = soup('table', {'width': '100%', "border":"1", "cellpadding":"1" ,"cellspacing":"0", "bordercolor":"#C0C8FE" ,"bgcolor":"#EBFAF7"})[0]

    b = a.findAll("tr")

    output = pandas.DataFrame(columns=['windchill', 'humidex', 'visibility', 'pressure', 'precipitation', 'temperature', 'hour', 'gust', 'humidity', 'nebulosity', 'wind'])
    for line in b[1:]:
        rows = line.findAll("td")
        values = map(lambda x: x.text, rows)


        if values[11] == "aucune":
            precipitation = 0.0
        else:
            try:
                precipitation = float(values[11].split(" ")[0])
            except:
                precipitation = 0.0

        try:
            nebulosity = int(values[1].split("/")[0])
        except:
            nebulosity = 0

        weather = 0
        if " faible" in values[2]:
            weather = 1
        if u" modéré" in values[2]:
            weather = 2
        if " fort" in values[2]:
            weather = 3

        weather_type = 0
        if " pluie" in values[2]:
            weather_type = 1
        if " neige" in values[2]:
            weather_type = 2

        try:
            visibility = float(values[3].split(" ")[0])
        except:
            visibility = 0.

        try:
            temperature = float(values[4].split(" ")[0])
        except:
            temperature = 0.

        try:
            humidity = float(values[5][:2])
        except:
            humidity = 0.

        try:
            humidex = float(values[6])
        except:
            humidex = 0.

        try:
            windchill = float(values[7].split(" ")[0])
        except:
            windchill = 0.

        try:
            wind = float(values[9].split(" ")[0])
        except:
            wind = 0.

        try:
            gust = float(values[9].split("(")[1].split(" ")[0])
        except:
            gust = 0.

        try:
            pressure = float(values[10].split(" ")[0])
        except:
            pressure = 0.

        output = output.append({"hour": int(values[0].split(" ")[0]),
            "nebulosity": nebulosity,
            "visibility": visibility,
            "temperature": temperature,
            "humidity": humidity,
            "humidex": humidex,
            "windchill": windchill,
            "wind": wind,
            "gust": gust,
            "pressure": pressure,
            "precipitation": precipitation,
            "weather": weather + weather_type,
            "weather_quality": weather,
            "weather_type": weather_type
        }, ignore_index=True)

    return output.sort_values(by = "hour")


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
print "Retrieving datas of openinging hours of all places"
opening_hours_url = configuration["data_source"] + "/sensor/getAll?s=" + configuration["secret"]
print "  Saving..."
save_to_file("../data/sensors/opening_hours.json", urllib2.urlopen(opening_hours_url).read())

json_places = json.loads(places)


print
print "Fetching measures for each places..."
requests = map(lambda place: grequests.get(configuration["data_source"] + "/measurements/places?ids=" + str(place["id"]) + "&types=measurement,wifi"), json_places)
results = grequests.map(requests)
print "  Saving..."
map(lambda (index, result): save_to_file("../data/sensors/sensor-" + str(json_places[index]["id"]) + "_wifi.json", order_data(result.content)), enumerate(results))

print
print "Fetching infos of each places..."
places_infos_requests = map(lambda place: grequests.get("http://6element.fr/place/" + str(place["id"])), json_places)
places_infos = grequests.map(places_infos_requests)
print "  Saving..."
map(lambda (index, result): save_to_file("../data/sensors/opening_hours-" + str(json_places[index]["id"]) + ".json", result.content), enumerate(places_infos))

print
print "Fetching weather"
startdate = datetime.date(2015,10,1)
enddate = datetime.datetime.now().date()
delta = enddate - startdate
days = [startdate + datetime.timedelta(days=i) for i in range(delta.days + 1)]
weather = {}

for i, mydate in enumerate(days):
    sys.stdout.write('\r  ' + str(i * 100 / len(days) + 1) + '%')
    sys.stdout.flush()
    try:
        res = parse_weather(mydate.day, mydate.month, mydate.year)
    except:
        continue
    try:
        weather[mydate.year]
    except:
        weather[mydate.year] = {}
    try:
        weather[mydate.year][mydate.month]
    except:
        weather[mydate.year][mydate.month] = {}
    res["day"]= mydate.day
    res["month"] = mydate.month
    res["year"] = mydate.year
    res.set_index("hour")
    weather[mydate.year][mydate.month][mydate.day] = json.loads(res.to_json())

sys.stdout.write('\r')
sys.stdout.flush()
save_to_file("../data/weather.json", json.dumps(weather))

###############################################################################

print
print "Fetching tides height"

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
    tides[mydate.year][mydate.month][mydate.day] = parse_tide(mydate.day, mydate.month, mydate.year)

sys.stdout.write('\r')
sys.stdout.flush()
save_to_file("../data/tides.json", json.dumps(tides))

print
print "Done!"
