#!/bin/python
# coding: utf8

from PIL import Image
from opening_hours import OpeningHours as OH
from sklearn import cross_validation
from sklearn import metrics
from sklearn import svm
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
from subprocess import call
from xml.etree.ElementTree import ElementTree as ET
import cookielib
import datetime as dt
import dateutil.parser
import json
import math
import matplotlib.dates as mdates
import os
import pandas as pd
import pickle
import pylab as plt
import pytz
import scipy
import sys
import urllib2
import yaml

################################
#  RETRIEVING CONFIGURATION
################################

def json_from_file(relative_path):
    with open(relative_path) as fs:
        return json.load(fs)

with open("config.yml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile)
if len(sys.argv) > 1:
    try:
        cfg = cfg[sys.argv[1]]
    except:
	print "[33mWarning: [0mNo scope found for \"" + sys.argv[1] + "\", switching back to default scope..."
        cfg = cfg["default"]
else:
    cfg = cfg["default"]
features = cfg["features_enabled"]

places = json_from_file("../data/sensors/all_places_infos.json")



###############################
#  INITIALIZING VARS
###############################

week_day = {
        "Mon" : 0,
        "lun.": 0,
        "Tue" : 1,
        "mar.": 1,
        "Wed" : 2,
        "mer.": 2,
        "Thu" : 3,
        "jeu.": 3,
        "Fri" : 4,
        "ven.": 4,
        "Sat" : 5,
        "sam.": 5,
        "Sun" : 6,
        "dim.": 6
        }

months = {
    "01": "Jan",
    "02": "Feb",
    "03": "Mar",
    "04": "Apr",
    "05": "May",
    "06": "Jun",
    "07": "Jul",
    "08": "Aug",
    "09": "Sep",
    "10": "Oct",
    "11": "Nov",
    "12": "Dec"
}

name = sys.argv[1] if len(sys.argv) > 1 else "default"
now = dt.datetime.now()

ranges = [now + dt.timedelta(minutes = mins) for mins in range(cfg["prediction"]["start"], cfg["prediction"]["stop"], cfg["prediction"]["step"])]

X   = pd.DataFrame()
row = pd.DataFrame()

cookjar = cookielib.CookieJar()
urllib2.build_opener(urllib2.HTTPCookieProcessor(cookjar)).open(urllib2.Request("http://maree.info/"))

maree_cookie = dict((cookie.name, cookie.value) for cookie in cookjar)['PHPSESSID']



################################
#  SCRAPPED DATAS
################################

print
print "Fetching tides height"

dates = [dt.datetime.now() + dt.timedelta(hours = i) for i in range(2 * 24 * 7)]
days  = [dt.datetime.now().date() + dt.timedelta(days = i) for i in range(7)]
tides = {}

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

for mydate in days:
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
    except Exception as e:
        pass

print
print "Retrieving holidays"
xml = ET(file = '../data/holidays.xml')
oh = ""
for node in xml.findall('./calendrier/zone[@libelle="A"]/*'):
    begin = node.get('debut').split('/')
    end = node.get('fin').split('/')
    if (begin[0] == end[0]):
        oh += begin[0] + " " + months[begin[1]] + " " + begin[2] + " - " + months[end[1]] + " " + end[2] + " ; "
    else:
        oh += begin[0] + " " + months[begin[1]] + " " + begin[2] + " - Dec 31 ; " + end[0] + " Jan 01 - " + months[end[1]] + " " + end[2] + " ; "

hd = OH(oh[:len(oh) - 3])

print
print "Weather forecast"
weather = [{} for i in range(0, len(places))]
loading = ['-', '\\', '|', '/']
icons = {
        "clear-day"             : 0,
        "clear-night"           : 0,
        "rain"                  : 2,
        "snow"                  : 3,
        "sleet"                 : 3,
        "wind"                  : 1,
        "fog"                   : 2,
        "cloudy"                : 1,
        "partly-cloudy-day"     : 1,
        "partly-cloudy-night"   : 1
    }

for j, sensor in enumerate(places):
    raw = json.loads(urllib2.urlopen("https://api.forecast.io/forecast/c981b0c8c612767197de22589175c656/" + str(sensor["lat"]) + "," + str(sensor["lon"]) + "?units=si").read())
    res = pd.read_json(json.dumps(raw["hourly"]["data"]))
    res["humidex"]         = res["apparentTemperature"]
    res["wind"]            = res["windSpeed"]
    res["precipitation"]   = res["precipIntensity"]
    res["weather_type"]    = res.apply(lambda row: icons[row["icon"]], axis = 1)
    res["weather_quality"] = res.apply(lambda row: row["wind"] / 15, axis = 1)
    res["weather"]         = res.apply(lambda row: row["weather_type"] + row["weather_quality"], axis = 1)
    res["date"]            = res.apply(lambda row: now + dt.timedelta(hours = row.name, minutes = -now.minute, seconds = -now.second, microseconds = -now.microsecond), axis = 1)
    res["hour"]            = res.apply(lambda row: row["date"].hour, axis = 1)
    res["day"]             = res.apply(lambda row: row["date"].date(), axis = 1)
    res["month"]           = res.apply(lambda row: row["date"].month, axis = 1)
    res["year"]            = res.apply(lambda row: row["date"].year, axis = 1)

    res = res.set_index("hour")
    res["hour"] = res.index

    for mydate in res[["day"]].groupby("day").max().index:
        try:
            weather[j][mydate.year]
        except:
            weather[j][mydate.year] = {}
        try:
            weather[j][mydate.year][mydate.month]
        except:
            weather[j][mydate.year][mydate.month] = {}
        try:
            weather[j][mydate.year][mydate.month][mydate.day]
        except:
            weather[j][mydate.year][mydate.month][mydate.day] = {}

        weather[j][mydate.year][mydate.month][mydate.day] = json.loads(res[res["day"] == mydate].to_json())



################################
#  USEFUL FUNCTIONS
################################

def from_timestamp(ts):
    utc_tz = pytz.timezone('UTC')
    utc_dt = utc_tz.localize(dt.datetime.utcfromtimestamp(ts))
    return utc_dt

def get_weather(id, date, hour, what):
    hour = str(hour)
    try:
        return weather[id][date.year][date.month][date.day][what][hour]
    except Exception as e:
        return 0



################################
#  AVAILABLE FEATURES
################################

adder = {}

adder["Day_of_week"]         = lambda date, p: week_day[date.strftime("%a")]
adder["Holidays"]            = lambda date, p: 2 + hd.is_open(date + dt.timedelta(days = int(p))) if hd.is_open(date) else hd.is_open(date + dt.timedelta(days = int(p)))
adder["Hour_of_day"]         = lambda date, p: date.hour + float(date.minute) / 60.0
adder["Month"]               = lambda date, p: date.month
adder["Previous"]            = lambda date, p: get_prev(date, int(p))
adder["Roads"]               = lambda date, p: get_roads_affluence(date, p)
adder["Simple_hour"]         = lambda date, p: date.hour
adder["Simple_mins"]         = lambda date, p: date.minute
adder["Tide"]                = lambda date, p: tides[date.year][date.month][date.day][date.hour][int(date.minute / 15)]
adder["Weather"]             = lambda date, p: get_weather(placeid, date, date.hour, p if len(p) else "weather")



################################
#  PROCESSING
################################

with open("./data/" + name + ".clf.pkl", 'ro') as save:
    clf = pickle.loads(save.read())

date_list = []
sensor_id = []

for placeid, sensor in enumerate(places):
    if not sensor["sensor_ids"][0]:
        continue
    for date in ranges:
        for i, feature in enumerate(features):

            feature = feature.split('.')
            feature.append('')
            feature_name = feature[0]
            opt = feature[1]

            row[feature_name + ('_' + opt if len(opt) else '')] = [adder[feature_name](date, opt)]
            row["id"] = [int(sensor["sensor_ids"][0])]
        date_list.append(date)
        sensor_id.append(int(sensor["sensor_ids"][0]))
        X = X.append(row)

data = {"Sensor": sensor_id, "Date": date_list, "Prediction": clf.predict(X)}
results = pd.DataFrame(data = data).set_index(["Sensor", "Date"])
print results

with open("./data/" + name + ".prediction.json", 'w') as save:
    json.dump(results.to_json(), save)
