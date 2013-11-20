#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

import xmlrpclib

s = xmlrpclib.ServerProxy("http://venus.ita.chalmers.se:12121/RPC2", allow_none=True, encoding="UTF-8")

print s.server_function_definition("server_function_definition")["result"]

print s.server_documentation("server_function_definition")["result"]

raise SystemExit()

sesn = s.session_start()["result"]
s.session_auth_login(sesn, "mort", "mort")

assert "personnummer" in s.person_fetch(sesn, "mort", {"personnummer": True, "firstname": True})["result"]

assert "error" in s.person_fetch(sesn, "viktor", {"personnummer": True, "firstname": True})

update_count = 0
for noop in range(1, 5):
    if "result" in s.person_update(sesn, "viktor", {"noop%d" % (noop,): True}):
        update_count += 1
assert update_count == 2

print s.person_dig({"account_in": {"account": "viktor"}}, {"person": True, "account_data": {"account": True}})

print s.person_dig({"firstname_maxlen": 4, "firstname_like": "V%", "account_in": {"account_maxlen": 4}}, {"firstname": True, "account": True, "account_data": {"account": True, "uid": True}})

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

