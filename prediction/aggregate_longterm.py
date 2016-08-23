#!/usr/bin/python

from multiprocessing import Pool
import datetime
import dateutil.parser
import json
import math
import os
import pandas as pd
import pytz
import sys

# Help message
if (len(sys.argv) == 1 or sys.argv[1] == "-h") and 0 == 1:
    print "Usage: " + sys.argv[0] + " json_output [csv_output]"
    print
    print " `-> Print the analysis as json into the json_output file, and,"
    print "     if another file is given, write as CSV the informations concerning"
    print "     the maximum amount of WiFi devices measured by day, by sensor, into"
    print "     the csv_output file."
    print
    exit()

def json_from_file(relative_path):
    with open(os.path.dirname(os.path.abspath(__file__)) + "/" + relative_path) as fs:
        return json.load(fs)

# Loading all sensors' datas
weather = json_from_file('../data/weather.json')
tides = json_from_file('../data/tides.json')
places = json_from_file("../data/sensors/all_places_infos.json")

roads = pd.read_json("../data/scrappers/ordered.json")
#roads['date'] = roads.apply(lambda row: dateutil.parser.parse(row['date']), axis = 1)
roads['date'] = roads.apply(lambda row: str(row['date'] - datetime.timedelta(minutes = row['date'].minute % 30)), axis = 1)
roads = roads.groupby('date').max()

my_table = None
allsensors = []
base = datetime.datetime.today()
week_day = {"Mon": 0,
        "Tue": 1,
        "Wed": 2,
        "Thu": 3,
        "Fri": 4,
        "Sat": 5,
        "Sun": 6}

# Initializing timezone
paris = pytz.timezone('Europe/Paris')
utc = pytz.utc

# Analyzing dates up to 300 days back
date_list = {}
for x in range(0, 300):
    date_list[(base - datetime.timedelta(days = x)).strftime("%Y-%m-%d")] = []

   #if (month > 3) or (month == 3 and day > 27):

def retrieve_hour(measure):
    date = dateutil.parser.parse(measure["date"])
    date = date - datetime.timedelta(minutes = date.minute % 30, seconds = date.second, microseconds = date.microsecond)
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

def get_weather(date, hour, what):
    try:
        return weather[str(date.year)][str(date.month)][str(date.day)][what][str(hour)]
    except:
        return 0

def get_prev(df, date, nb_hours):
    date = date - datetime.timedelta(hours = nb_hours)
    if (date in df.index):
        return df.loc[date]["Nb_measured"]
    return 0

def get_roads_affluence(row):
    try:
        date = str(row.name - datetime.timedelta(hours = 1, minutes = 0))
        date = date[:10] + ' ' + date[11:19]
        val = roads.affluence[date]
        return val
    except:
        return 0

def retrieve_mean(mean, row):
    try:
        mes = mean.loc[int(datetime.datetime.utcfromtimestamp(row.name.tolist() / 1e9).hour)]["Nb_measured"]
    except Exception as e:
        print e
        print "WRONG"
        mes = 0
    mes += 1
    res = float(row["Nb_measured"]) / float(mes)
    return res

def set_shift(row):
    dt = row["Date"]# - datetime.timedelta(minutes = row["Date"].minute % 30)
    return dt.strftime("%Y%m%d%H")

# Processing statistics from the JSON got from the API
def process_sensor(sensor, measures):

    # If no measures were retrieved
    if (len(measures) < 150):
        print "No measures acquired for " + sensor["name"].encode("utf-8") + ", aborting process for the sensor..."
        return (None)

    print "Processing sensor: \"" + sensor["name"].encode("utf-8") + "\"..."

    # Building dataset
    df = pd.DataFrame(data = list(zip(map(retrieve_hour, measures), map(retrieve_nb_measured, measures))), columns = ["Date", "Nb_measured"])

    # Cleaning low maxs for each day
    df["Day"]                 = df.apply(lambda row: row["Date"].date(), axis = 1)
    days_df                   = df.groupby("Day").max()
    days_df                   = days_df[days_df["Nb_measured"] < 50]
    for i in days_df.index:
        df                    = df[df["Day"] != i]
    del df["Day"]

    # Grouping duplicates:
    df["Hour_of_day"]         = df.apply(lambda row: row["Date"].hour, axis = 1)
    mean = df[df["Nb_measured"] > 5][["Hour_of_day", "Nb_measured"]].groupby("Hour_of_day").mean()
    for i in range(0, 24):
        try:
            mean.loc[i]
        except:
            mean.loc[i] = 10
    mean.to_csv("dataset_sensor-" + str(sensor["id"]) + "-mean.csv")

    df = df.groupby("Date").mean()

    # Adding features

    #df["Roads"]               = df.apply(lambda row: get_roads_affluence(row), axis = 1)
    #df["Previous"]            = df.apply(lambda row: get_prev(df, row.name, 1), axis = 1)          # Reduces mean error by 10, actually it may avoid too large breaks between two predictions
    #df["Before"]              = df.apply(lambda row: get_prev(df, row.name, 2), axis = 1)         # Actually, it seems to be useless
    #df["Before_before"]       = df.apply(lambda row: get_prev(df, row.name, 3), axis = 1)          # Reduces mean error a little, may be giving a direction to the curve (increasing, decreasing)
    #df["Differential"]        = df.apply(lambda row: get_prev(df, row.name, 1) - get_prev(df, row.name, 3), axis = 1)          # Reduces mean error by 10, actually it may avoid too large breaks between two predictions

    df["Day_of_week"]         = df.apply(lambda row: week_day[row.name.strftime("%a")], axis = 1)
    #df["Month"]               = df.apply(lambda row: row.name.month, axis = 1)

    df["Weather_Temperature"] = df.apply(lambda row: get_weather(row.name, row.name.hour, "temperature"), axis = 1)
    #df["Weather_Rain"] = df.apply(lambda row: not not get_weather(row.name, row.name.hour, "precipitation"), axis = 1)
    df["Weather_Humidity"]    = df.apply(lambda row: get_weather(row.name, row.name.hour, "humidity"), axis = 1)

    df["Tide"]                = df.apply(lambda row: tides[str(row.name.year)][str(row.name.month)][str(row.name.day)][str(row.name.hour)][row.name.minute / 15], axis = 1)

    # Additionnal features (disabled by default due to decreasing of accuracy):

    df["Weather_Quality"]     = df.apply(lambda row: get_weather(row.name, row.name.hour, "weather_quality"), axis = 1)
    #df["Weather_Type"]        = df.apply(lambda row: get_weather(row.name, row.name.hour, "weather_type"), axis = 1)
    df["Weather"]             = df.apply(lambda row: int(weather[str(row.name.year)][str(row.name.month)][str(row.name.day)]["weather"][str(row.name.hour - 1 if row.name.hour else 0)]), axis = 1)


    # Get the level of the number of people measured, depending on the median of the list
    #  - The first one set the lower level to each measures got on closed hours of the place
    #  - The second one set the level for each hours including closed ones
    #
    # Please comment out the method you want to use

    #df["Level"]               = df.apply(lambda row: (get_level(100, row["Nb_measured"])), axis = 1)

    df["Coeff"]                = df.apply(lambda row: retrieve_mean(mean, row), axis = 1)

    # Output the mean number of people spotted by hour:
    df.to_csv("dataset_sensor-" + str(sensor["id"]) + ".csv")

    return (df)

# This function will be given as parameter to the thread pool
def parallelize(sensor):
    return process_sensor(sensor, json_from_file("../data/sensors/sensor-" + str(sensor["id"]) + "_wifi.json"))

# Processing datas in multithread
#Pool(len(places) / 2 if len(places) > 10 else 4).map(parallelize, places)
map(parallelize, places)
