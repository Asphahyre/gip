#!/bin/python
# coding: utf8

from opening_hours import OpeningHours as OH
from sklearn import cross_validation
from sklearn import metrics
from sklearn import svm
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
from subprocess import call
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

places = json_from_file("../data/sensors/all_places_infos.json")



################################
#  INITIALIZATION
################################

algorithms = {
        "decision tree": DecisionTreeRegressor,
        "random forest": RandomForestRegressor
        }

try:
    clf = algorithms[cfg["algorithm"]](**cfg["parameters"])
except KeyError:
    print "[33mWarning: [0mPlease specify a [1mparameters[0m field in the [1mconfig.yml[0m file"
    clf = algorithms[cfg["algorithm"]]()
except Exception:
    print "[31mError: [0mInvalid parameters in the [1mparameters[0m field in the [1mconfig.yml[0m file; please update it"
    clf = algorithms[cfg["algorithm"]]()

name = sys.argv[1] if len(sys.argv) > 1 else "default"



###############################
#  RETRIEVING DATA
###############################

sys.stdout.write("[0mReading from [0;37;1m./data/dataset_sensors." + name + ".csv[0m...")
sys.stdout.flush()
try:
    df = pd.read_csv("data/dataset_sensors." + name + ".csv", index_col = "Date", parse_dates = True)
except Exception as e:
    sys.stdout.write("  [31;1mFAILED[0m\n")
    try:
        print "\n\n[4;37mAggregation:[0m\n"
        call(["./aggregate.py", name])
        print "\n[4;37mRetrying fitting:[0m\n"
        call(["./fit_model.py", name])
    except:
        raise Exception(e)
    sys.exit(0)
sys.stdout.write("  [32;1mOK[0m\n")

y = df["Nb_measured"]
X = df
del X["Nb_measured"]

sys.stdout.write("[0mFitting[0m...")
sys.stdout.flush()
try:
    clf.fit(X, y)
except Exception as e:
    sys.stdout.write("  [31;1mFAILED[0m\n")
    raise Exception(e)
sys.stdout.write("  [32;1mOK[0m\n")

print
print
print " ↪ [0mSaving model at [0;37;1m./data/" + name + ".clf.plk[0m"
print

with open("./data/" + name + ".clf.pkl", 'w') as save:
    pickle.dump(clf, save)
