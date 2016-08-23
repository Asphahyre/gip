#!/usr/bin/python

from matplotlib.pyplot import figure, show
from sklearn import cross_validation
from sklearn import metrics
from sklearn import svm
from sklearn.tree import DecisionTreeRegressor
from sklearn.tree import export_graphviz
import datetime
import dateutil.parser
import json
import math
import matplotlib.dates as mdates
import os
import pandas as pd
import pylab as plt
import scipy
import sys

def json_from_file(relative_path):
    with open(os.path.dirname(os.path.abspath(__file__)) + "/" + relative_path) as fs:
        return json.load(fs)

# Loading sensors' datas
places = json_from_file("../data/sensors/all_places_infos.json")

try:
    nb_it = int(sys.argv[1])
except:
    nb_it = 100

depth = int(sys.argv[2])

X             = pd.DataFrame()
y             = pd.DataFrame()
future_X      = pd.DataFrame()
future_y      = pd.DataFrame()
predict_X     = pd.DataFrame()
means         = {}
clf           = DecisionTreeRegressor(max_depth = depth)

for place in places:
    try:
        df = pd.read_csv("dataset_sensor-" + str(place["id"]) + ".csv", index_col = "Date")
    except:
        continue

    df["id"] = place["id"]
    X = X.append(df)
    y = y.append(df[["Coeff"]])
    means[place["id"]] = pd.read_csv("./dataset_sensor-" + str(place["id"]) + "-mean.csv")

    future_X  = future_X.append(df[:len(df) * 4 / 6])
    future_y  = future_y.append(df[["Coeff"]][:len(df) * 4 / 6])
    predict_X = predict_X.append(df[len(df) * 4 / 6:])

print "Scoring..."

real = X["Nb_measured"]

#del X["Level"]
del X["Coeff"]
del X["Nb_measured"]

cv = cross_validation.ShuffleSplit(X.shape[0], test_size = 0.2, random_state = 0, n_iter = nb_it)
scores = cross_validation.cross_val_score(clf, X, y["Coeff"], scoring = "mean_squared_error", cv = cv)
print("   Mean error of %0.2f (+/- %0.2f)" % (math.sqrt(-scores.mean()), math.sqrt(scores.std() if scores.std() >= 0 else -scores.std())))

#del future_X ["Level"]
#del predict_X["Level"]

del future_X ["Coeff"]
del predict_X["Coeff"]
del future_X ["Nb_measured"]
del predict_X["Nb_measured"]

clf.fit(future_X, future_y)

print
print "Features importance: "
for i, feature in enumerate(X.columns):
    print "   " + feature + ": " + str(clf.feature_importances_[i])

X["learned"] = X.apply(lambda row: 0 if (row.name in future_X.index) else 1, axis = 1)
X = X.reset_index()
new_X = X[:]
del X["Date"]
learned = X[X["learned"] == 0]
predicted = X[X["learned"] == 1]

del learned["learned"]
del predicted["learned"]
predictions = clf.predict(predicted)
learning = clf.predict(learned)

plt.scatter(range(0, len(X.index)), y)
#plt.plot(map(lambda (i, j): i, enumerate(predict_X.index)), predictions)

plt.plot(predicted.index, predictions, c = "#00ff00")
plt.plot(learned.index, learning, c = "#0000ff")

plt.figure()

predictions_windex = pd.Series(predictions, index = predicted.index)
predictions_windex = pd.concat([predictions_windex, new_X[["Date", "id"]]], axis = 1)
#predictions_windex["Hour"] = predictions_windex.apply(lambda row: dateutil.parser.parse(row["Date"]).hour, axis = 1)
predictions_windex["Date"] = predictions_windex.apply(lambda row: dateutil.parser.parse(row["Date"]).date(), axis = 1)
#predictions_windex_maxs = predictions_windex[pd.Series(predictions_windex["Hour"]).isin(range(9, 19))].groupby(["Date", "id"], as_index = False).median()
predictions_windex_maxs = predictions_windex.groupby(["Date", "id"], as_index = False).median()
predictions_windex = pd.merge(predictions_windex, predictions_windex_maxs, how = "left", on = ["Date", "id"])["0_y"]
#del predictions_windex["Hour"]

learning_windex    = pd.Series(learning,    index = learned.index)
learning_windex = pd.concat([learning_windex, new_X[["Date", "id"]]], axis = 1)
#learning_windex["Hour"] = learning_windex.apply(lambda row: dateutil.parser.parse(row["Date"]).hour, axis = 1)
learning_windex["Date"] = learning_windex.apply(lambda row: dateutil.parser.parse(row["Date"]).date(), axis = 1)
#learning_windex_maxs = learning_windex[pd.Series(learning_windex["Hour"]).isin(range(9, 19))].groupby(["Date", "id"], as_index = False).median()
learning_windex_maxs = learning_windex.groupby(["Date", "id"], as_index = False).median()
learning_windex = pd.merge(learning_windex, learning_windex_maxs, how = "left", on = ["Date", "id"])["0_y"]
#del learning_windex["Hour"]

print
print "Pearson for prediction: " + str(scipy.stats.pearsonr(real.iloc[predicted.index[:-10]], map(lambda i: predictions_windex.loc[i] * means[int(new_X.loc[i]["id"])].loc[dateutil.parser.parse(new_X.loc[i]["Date"]).hour]["Nb_measured"], predicted.index)[:-10]))
print "Pearson for learning: " + str(scipy.stats.pearsonr(real.iloc[learned.index[:-10]], map(lambda i: learning_windex.loc[i] * means[int(new_X.loc[i]["id"])].loc[dateutil.parser.parse(new_X.loc[i]["Date"]).hour]["Nb_measured"], learned.index)[:-10]))


measures, = plt.plot(X.index, real, c = "#ff0000")
pred = plt.scatter(predicted.index[7:], map(lambda i: predictions_windex.loc[i] * means[int(new_X.loc[i]["id"])].loc[dateutil.parser.parse(new_X.loc[i]["Date"]).hour]["Nb_measured"], predicted.index)[:-7], c = "#ffff00")
lern = plt.scatter(learned.index[7:], map(lambda i: learning_windex.loc[i] * means[int(new_X.loc[i]["id"])].loc[dateutil.parser.parse(new_X.loc[i]["Date"]).hour]["Nb_measured"], learned.index)[:-7], c = "#ff00ff")

plt.ylabel("Counted")
plt.xlabel("Id of the measure")
plt.legend([measures, pred, lern], ["Measured", "Predicted", "Learned"], loc = "best")
plt.show()
