#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

import xmlrpclib

s = xmlrpclib.ServerProxy("http://venus.ita.chalmers.se:12121/RPC2", allow_none=True, encoding="UTF-8")

print s.account_fetch("viktor", {"account": True, "uid": True, "owner": True, "owner_data": {"person": True, "firstname": True, "lastname": True, "account_data": {"account": True}}})

print s.person_update("viktor", {"lastname": u"Foügstedt"})

print s.person_fetch("viktor", {"firstname": True, "lastname": True})

print s.person_update("viktor", {"firstname": "Vixtor", "lastname": u"Fougstedt"})
print s.person_fetch("viktor", {"firstname": True, "lastname": True})

print s.person_update("viktor", {"firstname": u"Viktor"})
print s.person_fetch("viktor", {"firstname": True, "lastname": True})

