#!/usr/bin/python

from matplotlib.pyplot import figure, show
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from random import random
from opening_hours import OpeningHours
import datetime
import dateutil.parser
import json
import os
import sys

if (len(sys.argv) < 2):
    print "Usage: " + sys.argv[0] + " place_id"
    print
    print " `-> Prints the hours when too many measures were took for the place whose id was given in argument."
    print "     A graph is built with one curve by day displaying the number of measures by hour"
    print
    exit()

place_id = sys.argv[1]

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

# Loading measures for the selected place
with open(os.path.dirname(os.path.abspath(__file__)) + "/../data/sensors/sensor-" + place_id + "_wifi.json") as fs:
    measures = json.load(fs)

def json_from_file(relative_path):
    with open(os.path.dirname(os.path.abspath(__file__)) + "/" + relative_path) as fs:
        return json.load(fs)

weather = json_from_file('../data/weather.json')

def get_weather(date, hour, what):
    try:
        return weather[str(date.year)][str(date.month)][str(date.day)][what][str(hour)]
    except:
        return 0

X = []
y = []
last = datetime.datetime.fromtimestamp(0)
before = last
try:
    oh = OpeningHours(json_from_file("../data/sensors/opening_hours-" + place_id + ".json")[0]['opening_hours'])
except:
    oh = 0
tides = json_from_file('../data/tides.json')

# Processing for each measure
for i, measure in enumerate(measures):
    sys.stdout.write('\r  ' + str(i * 100 / len(measures) + 1) + '%')
    sys.stdout.flush()

    measure_date = dateutil.parser.parse(measure["date"]) + datetime.timedelta(hours = 2)

    # If the date has changed, we have to process the last day's data
    if ((measure_date.day > last.day) or (measure_date.month > last.month)):
        # Displays X and y depending on the temperature (Z) and humidity (colors)
        #scat = ax.scatter(X, y, map(lambda x: float(get_weather(last, int(x), "temperature")), X), c = map(lambda x: 1 - float(get_weather(last, int(x), "humidex")), X))

        # Displays X and y depending on the temperature (Z) and tide (colors)
        scat = ax.scatter(X, y, map(lambda x: float(get_weather(last, int(x), "temperature")), X), c = map(lambda x: float(tides[str(last.year)][str(last.month)][str(last.day)][str(int(x))][int(x * 4.0) % 4]), X))

        if (measure_date.month > last.month) and len(X) and 0:
            plt.colorbar()
            plt.figure()

        X = []
        y = []

    if (not oh or oh.is_open(measure_date)):
        # Counting the measure on the current day, in the concerned hour
        X.append(float(measure_date.strftime("%H")) + float(measure_date.strftime("%M")) / 60.0)
        try:
            y.append(len(measure['value']))
        except:
            y.append(measure['value'])

        before = last
        last = measure_date

sys.stdout.write('\r')
sys.stdout.flush()

fig.colorbar(scat)
plt.show()
