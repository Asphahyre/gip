"use strict";

var http = require('http');
var fs = require('fs');

var KEY = process.env.CUB_KEY;
var DATA_PATH = process.env.CUB_DATA_PATH;

var to_get = [
    {"protocole": "wfs", "version": "1.1.0", "features": ["CI_TRAFI_L", "CI_PARK_P"], "options": '&srsName=urn:ogc:def:crs:EPSG::4326'},
    {"protocole": "wps", "version": "1.0.0", "features": ["CI_TPSTJ_A", "SV_HORAI_A"]}
]

to_get.forEach(function(obj){

    obj.features.forEach(function(feature){

        if (obj.protocole == "wfs") {

            var options = {
                host: "data.bordeaux-metropole.fr",
                path: '/wfs?key=' + KEY + '&service=wfs&version=' + obj.version +'&request=GetFeature&typeName='+ feature + obj.options,
                method: 'GET'
            }
        } else {

            var options = {
                host: "data.bordeaux-metropole.fr",
                path: '/wps?key=' + KEY + '&service=wps&version=' + obj.version +'&request=Execute&identifier='+ feature,
                method: 'GET'
            }
        }
        var request = http.request(options, function (res) {
            var data = '';
            res.on('data', function (chunk) {
                data += chunk;
            });
            res.on('end', function () {
                var now = new Date();
                var file_name = feature + "-" + now.toISOString() + '.xml';
                fs.writeFile(DATA_PATH + file_name, data);
            });
        });
        request.on('error', function (e) {
            console.log(e.message);
        });
        request.end();

    })



})

