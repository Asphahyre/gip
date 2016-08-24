> *Groupement d'Intérêt Public*

# GIP

GIP is a project based on the beaches affluences.

Its goal is to predict future affluences for each of the beaches we placed sensors. It will let people know when it'll be fine going to the beach depending on the targeted place.


## Dashboard

![](dashboard.png)

[The dasboard](http://gip.ants.builders/dashboard) can show real-time affluence measured by our sensors.

## Features

### Prerequisites:

You will need to fetch all of the needed data first. For this purpose, please have a look at the `data_loader/` directory.

### Usage

To prepare the learning, you *have* to call the `aggregate.py` script in the `prediction/` directory, without argument.

This script have to aggregate all the downloaded data into interesting features for GIP.

Then, you can initiate a `learn-classification.py` or a `learn-regression.py`, depending on the learning method you want to use. A graph will be opened so you can see how the model fitted to the measures, and allow you to see how the model is predicting the 20% of the last measures, didn't use for learning.
