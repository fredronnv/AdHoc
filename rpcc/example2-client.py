#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

import xmlrpclib

s = xmlrpclib.ServerProxy("http://venus.ita.chalmers.se:12121/RPC2", allow_none=True, encoding="UTF-8")

print s.person_dig({"firstname_maxlen": 4, "firstname_like": "V%", "account_in": {"account_maxlen": 4}}, {"firstname": True, "account": True, "account_data": {"account": True, "uid": True}})

raise SystemExit()

print s.account_fetch("viktor", {"account": True, "uid": True, "owner": True, "owner_data": {"person": True, "firstname": True, "lastname": True, "account_data": {"account": True}}})

sesn = s.session_start()['result']
print s.session_info(sesn)
print s.session_auth_login(sesn, "viktor", "2viktor")
print s.session_info(sesn)
print s.session_auth_login(sesn, "viktor", "viktor")
print s.session_info(sesn)

print s.account_fetch("viktor", {"account": True, "uid": True, "owner": True, "owner_data": {"person": True, "firstname": True, "lastname": True, "account_data": {"account": True}}})

print s.person_update("viktor", {"lastname": u"Foügstedt"})

print s.person_fetch("viktor", {"firstname": True, "lastname": True})

print s.person_update("viktor", {"firstname": "Vixtor", "lastname": u"Fougstedt"})
print s.person_fetch("viktor", {"firstname": True, "lastname": True})

print s.person_update("viktor", {"firstname": u"Viktor"})
print s.person_fetch("viktor", {"firstname": True, "lastname": True})

print s.person_get_name("viktor")

