#!/usr/bin/python
# coding: utf8

from xml.etree.ElementTree import ElementTree as ET
from opening_hours import OpeningHours as OH
import datetime as dt
import dateutil.parser
import json
import math
import os
import pandas as pd
import pytz
import sys
import yaml


###############################
#  LOADING DATAS
###############################

def json_from_file(relative_path):
    with open(relative_path) as fs:
        return json.load(fs)

weather = json_from_file('../data/weather.json')
tides = json_from_file('../data/tides.json')
places = json_from_file("../data/sensors/all_places_infos.json")

roads = pd.read_json("../data/scrappers/ordered.json")
roads['date'] = roads.apply(lambda row: str(row['date'] - dt.timedelta(minutes = row['date'].minute % 30)), axis = 1)
roads = roads.groupby('date').max()

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


###############################
#  INITIALIZING VARS
###############################

allsensors = []
base = dt.datetime.today()
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

paris = pytz.timezone('Europe/Paris')
utc = pytz.utc

try:
    os.stat("data")
except:
    os.mkdir("data")



###############################
#  AVAILABLE FEATURES
################################

adder = {}

adder["Day_of_week"]         = lambda a, p: a.apply(lambda row: week_day[row.name.strftime("%a")], axis = 1)
adder["Holidays"]            = lambda a, p: a.apply(lambda row: 2 + hd.is_open(row.name + dt.timedelta(days = int(p))) if hd.is_open(row.name) else hd.is_open(row.name + dt.timedelta(days = int(p))), axis = 1)
adder["Hour_of_day"]         = lambda a, p: a.apply(lambda row: row.name.hour + float(row.name.minute) / 60.0, axis = 1)
adder["Level"]               = lambda a, p: a.apply(lambda row: (get_level(int(p), row["Nb_measured"])), axis = 1)
adder["Month"]               = lambda a, p: a.apply(lambda row: row.name.month, axis = 1)
adder["Previous"]            = lambda a, p: a.apply(lambda row: get_prev(df, row.name, int(p)), axis = 1)
adder["Roads"]               = lambda a, p: a.apply(lambda row: get_roads_affluence(row), axis = 1)
adder["Simple_hour"]         = lambda a, p: a.apply(lambda row: row.name.hour, axis = 1)
adder["Simple_mins"]         = lambda a, p: a.apply(lambda row: row.name.minute, axis = 1)
adder["Tide"]                = lambda a, p: a.apply(lambda row: tides[str(row.name.year)][str(row.name.month)][str(row.name.day)][str(row.name.hour)][int(row.name.minute / 15)], axis = 1)
adder["Weather"]             = lambda a, p: a.apply(lambda row: get_weather(placeid, row.name, row.name.hour, p if len(p) else "weather"), axis = 1)


###############################
#  DEFINING FUNCTIONS
###############################

def retrieve_hour(measure):
    date = dateutil.parser.parse(measure["date"])
    date = date - dt.timedelta(minutes = date.minute % cfg["range"], seconds = date.second, microseconds = date.microsecond)
    return date

def retrieve_nb_measured(measure):
    try:
        return len(measure["value"])
    except:
        return measure["value"]

def get_level(median, nb):
    if (nb <= median):
        return (0)
    if (nb <= 2 * median):
        return (1)
    return (2)

def get_weather(id, date, hour, what):
    try:
        return weather[id][str(date.year)][str(date.month)][str(date.day)][what][str(hour)]
    except:
        return 0

def get_prev(df, date, nb_hours):
    date = date - dt.timedelta(hours = nb_hours)
    if (date in df.index):
        return df.loc[date]["Nb_measured"]
    return 0

def get_roads_affluence(row):
    try:
        date = str(row.name - dt.timedelta(hours = 1, minutes = 0))
        date = date[:10] + ' ' + date[11:19]
        val = roads.affluence[date]
        return val
    except:
        return 0

def set_shift(row):
    dt = row["Date"] - dt.timedelta(minutes = row["Date"].minute % 30)
    return dt.strftime("%Y%M%d%H%m")



################################
#  RETRIVING HOLIDAYS
################################

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



################################
#  PROCESSING DATA
################################

data = pd.DataFrame()

for placeid, sensor in enumerate(places):
    skipped = False
    measures = json_from_file("../data/sensors/sensor-" + str(sensor["id"]) + "_wifi.json")

    print "[0;2mProcessing sensor: [0;1m" + sensor["name"].encode("utf-8") + "[0m"
    if (len(measures) < 150):
        print "                    [31m↪️ [33mNo measures acquired, aborting process.[0m\n"
        continue

    sys.stdout.write('\r     [33m1 [0;1m/ [0;32m' + str(len(features) + 3) + " [0;37m▶️ [0mRetrieving measures...")
    sys.stdout.flush()
    df = pd.DataFrame(data = list(zip(map(retrieve_hour, measures), map(retrieve_nb_measured, measures))), columns = ["Date", "Nb_measured"])

    sys.stdout.write('\r     [33m2 [0;1m/ [0;32m' + str(len(features) + 3) + " [0;37m▶️ [0mEliminating days under a threshold of [31;1m" + str(cfg["invalid_day_threshold"]) + "[0m")
    sys.stdout.flush()
    df["Day"]                 = df.apply(lambda row: row["Date"].date(), axis = 1)
    days_df = df.groupby("Day").max()
    days_df = days_df[days_df["Nb_measured"] < cfg["invalid_day_threshold"]]
    for i in days_df.index:
        df = df[df["Day"] != i]
    del df["Day"]

    # Grouping duplicates:
    sys.stdout.write('\r     [33m3 [0;1m/ [0;32m' + str(len(features) + 3) + " [0;37m▶️ [0mGrouping duplicates measures by age                              ")
    sys.stdout.flush()
    df = df.groupby("Date").mean()

    # Adding features
    for i, feature in enumerate(features):
        sys.stdout.write('\r     [33m' + str(i + 4) + ' [0;1m/ [0;32m' + str(len(features) + 3) + " [0;37m▶️ [0mProcessing feature [31;1m" + feature + "[0m                             \b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b")
        sys.stdout.flush()
        feature = feature.split('.')
        feature.append('')
        feature_name = feature[0]
        opt = feature[1]
        try:
            adder[feature_name]
        except:
            #print "\n\n[31mFATAL ERROR[0m: unknown feature [37;1m" + feature + "[0m."
            sys.stdout.write(': [33msuch a feature not found, skipping it...\r   [31m✖ ' + str(i + 4) + '\n')
            sys.stdout.flush()
            del features[i]
            skipped = True
            continue
        df[feature_name + "_" + opt] = adder[feature_name](df, opt)
    sys.stdout.write('\r                                                                                                                  \r')
    if skipped: sys.stdout.write('\n')

    df["id"]                  = sensor["sensor_ids"][0]
    data = data.append(df)

print
print
print " ↪ [0mSaving file at [0;37;1m./data/dataset_sensors." + (sys.argv[1] if len(sys.argv) > 1 else "default") + ".csv[0m"
print
data.to_csv("data/dataset_sensors." + (sys.argv[1] if len(sys.argv) > 1 else "default") + ".csv")
