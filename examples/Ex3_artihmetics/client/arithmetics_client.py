#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-
import json
import urllib2

url = "http://localhost:12121/json"

print urllib2.urlopen(url, json.dumps({"function": "add2", "params": [1, 2]})).read()

print urllib2.urlopen(url, json.dumps({"function": "sub2", "params": [7, 2]})).read()

print urllib2.urlopen(url, json.dumps({"function": "mul2", "params": [5, 8]})).read()

print urllib2.urlopen(url, json.dumps({"function": "div2", "params": [8, 3]})).read()

