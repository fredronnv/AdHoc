#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-

from rpcc_client import *

proxy = RPCC("http://localhost:12121", 0, attrdicts=True)


plist = proxy.person_dig({"lastname": "Hult"}, {"firstname": True, "lastname": True, "age": True})
for p in plist:
    print p.firstname, p.lastname, p.age
    
proxy.person_update("nilshult", {"age": 13})

plist = proxy.person_dig({"person": "nilshult"}, {"firstname": True, "lastname": True, "age": True})

p = plist[0]

print p.firstname, p.lastname, p.age
