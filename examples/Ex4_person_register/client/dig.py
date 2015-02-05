#!/usr/bin/env python2.6

from rpcc_client import *

proxy = RPCC("http://localhost:12121", 0, attrdicts=True)

plist = proxy.person_dig({"lastname": "Hult"}, {"firstname": True, "lastname": True, "age": True})
for p in plist:
    print p.firstname, p.lastname, p.age
