#!/usr/bin/env python2.6

import json
import urllib2

print urllib2.urlopen("http://localhost:12121/json", json.dumps({"function": "hello", "params": []})).read()


