#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

from rpcc_client import *

# Create a proxy. The attrdicts=True will cause the proxy to convert returned dictionaries
# from teh server as attributes of the returned objects
proxy = RPCC("http://localhost:12121", 0, attrdicts=True)

plist = proxy.person_dig({"lastname": "Hult"}, {"firstname": True, "lastname": True, "age": True})
for p in plist:
    print p.firstname, p.lastname, p.age
    # print p["firstname"], p["lastname"], p["age"] # Use this if attrdicts is not set to True
