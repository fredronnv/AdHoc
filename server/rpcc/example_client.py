#!/usr/bin/env python2.6

import json
import urllib2

print urllib2.urlopen("http://venus.ita.chalmers.se:12121/json", json.dumps({"function": "add", "params": [1, 2]})).read()

print urllib2.urlopen("http://venus.ita.chalmers.se:12121/json", json.dumps({"function": "add", "params": [1, "apa"]})).read()

print urllib2.urlopen("http://venus.ita.chalmers.se:12121/json?v1", json.dumps({"function": "add", "params": [1, 2]})).read()

print urllib2.urlopen("http://venus.ita.chalmers.se:12121/json?v1", json.dumps({"function": "add", "params": [1, 2, 3]})).read()
