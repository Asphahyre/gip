"use strict";

var http = require('http');

var options = {
    host: "data.bordeaux-metropole.fr",
    path: '/wfs?key=G3TZNROCU3&service=wfs&version=1.1.0&request=GetFeature&typeName=CI_TRAFI_L&srsName=urn:ogc:def:crs:EPSG::4326',
    method: 'GET'
}
var request = http.request(options, function (res) {
    var data = '';
    res.on('data', function (chunk) {
        data += chunk;
    });
    res.on('end', function () {
        console.log(data);

    });
});
request.on('error', function (e) {
    console.log(e.message);
});
request.end();