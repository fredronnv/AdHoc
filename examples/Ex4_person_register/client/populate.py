#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

from rpcc_client import *

proxy = RPCC("http://localhost:12121", 0, attrdicts=True)


def createperson(proxy, person_id, fname, lname, age):
    try:
        proxy.person_create(person_id, fname, lname, age)
    except RPCCLookupError:
        pass

createperson(proxy, "nissehul", "Nisse", "Hult", 46)
createperson(proxy, "nilshult", "Nils", "Hult", 5)
createperson(proxy, "barryo", "Barack", "Obama", 53)
createperson(proxy, "arnie", "Arnold", "Schwarzenegger", 63)
