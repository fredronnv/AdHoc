#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

import sys

from rpcc_client import RPCCValueError, RPCCLookupError
import rpcc_client
sys.path.append("/home/viktor/AdHoc/trunk/client")


rpcc = rpcc_client.RPCC("http://localhost:7310", 0)

tmpl = {"b1": True, "b2": True, "i1": True, "i2": True, "s1": True, "s2": True}
print rpcc.optionset_fetch(2, tmpl)

print rpcc.optionset_fetch(1, tmpl)

print rpcc.optionset_update(1, {"b1": False, "i1": 2, "s1": "3", "b2": True})
print rpcc.optionset_fetch(1, tmpl)

print rpcc.optionset_update(1, {"b1": True, "i1": 1, "s1": "foo", "b2": None})
print rpcc.optionset_fetch(1, tmpl)

print rpcc.server_documentation("optionset_dig")

print "[1]", rpcc.optionset_dig({"s1_pattern": "fo*"}, {"optionset": True})
print "[]", rpcc.optionset_dig({"s1_pattern": "bo*"}, {"optionset": True})
rpcc.optionset_update(1, {"b2": None})
print "[]", rpcc.optionset_dig({"b2_is_set": True}, {"optionset": True})
rpcc.optionset_update(1, {"b2": True})
rpcc.optionset_update(2, {"b2": None})
print "[1]", rpcc.optionset_dig({"b2_is_set": True}, {"optionset": True})
print "[2]", rpcc.optionset_dig({"b2_is_not_set": True}, {"optionset": True})

rpcc.optionset_update(1, {"b2": True})
rpcc.optionset_update(2, {"b2": False})
print "[1]", rpcc.optionset_dig({"b2": True}, {"optionset": True})
print "[2]", rpcc.optionset_dig({"b2": False}, {"optionset": True})

