#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

import sys
sys.path.append("/home/viktor/AdHoc/trunk/client")

import rpcc_client

rpcc = rpcc_client.RPCC("http://venus.ita.chalmers.se:12121")
rpcc.login("#root#", "#root#")
assert rpcc._auth == "#root#"

mutex = "test-mutex"

try:
    rpcc.mutex_create(mutex)
except ValueError:
    pass

rpcc2 = rpcc_client.RPCC("http://venus.ita.chalmers.se:12121")
rpcc.login("viktor", "viktor")

rpcc.mutex_acquire(mutex, "rpcc", True)
print rpcc.mutex_info(mutex)

try:
    rpcc2.mutex_acquire(mutex, "rpcc2", False)
except RuntimeError:
    pass

print rpcc2.mutex_info(mutex)

try:
    rpcc.mutex_create_string(mutex, "svar")
except ValueError:
    pass

print rpcc.mutex_string_get(mutex, "svar")
rpcc.mutex_string_set(mutex, "svar", "Value!")
print rpcc.mutex_string_get(mutex, "svar")
rpcc.mutex_string_unset(mutex, "svar")
print rpcc.mutex_string_get(mutex, "svar")
rpcc.mutex_string_destroy(mutex, "svar")

try:
    rpcc.mutex_stringset_create(mutex, "sset")
except ValueError:
    pass

print rpcc.mutex_stringset_get(mutex, "sset")
rpcc.mutex_stringset_add(mutex, "sset", "apa")
print rpcc.mutex_stringset_get(mutex, "sset")
rpcc.mutex_stringset_add(mutex, "sset", "bepa")
print rpcc.mutex_stringset_get(mutex, "sset")
rpcc.mutex_stringset_add(mutex, "sset", "apa")
print rpcc.mutex_stringset_get(mutex, "sset")

rpcc.mutex_stringset_destroy(mutex, "sset")

try:
    rpcc2.mutex_release(mutex, False)
except RuntimeError:
    pass

rpcc.mutex_release(mutex, False)

raise SystemExit()


print rpcc.event_dig("min_event:#0,function:session_start#0", "event,created,function,params")

rpcc.login("viktor", "viktor")

#print rpcc.event_dig("min_event:#0,function:session_start#0", "event,created,function,params")


print rpcc.person_dig("firstname:Viktor")
rpcc.stop()


def worked(r):
    return "result" in r

def failed(r, witherr=None):
    if "error" not in r:
        return False
    if witherr and r["error"]["name"] != witherr:
        return False
    return True

import xmlrpclib

s = xmlrpclib.ServerProxy("http://venus.ita.chalmers.se:12121/RPC2", allow_none=True, encoding="UTF-8")

sesn = s.session_start()['result']
print s.session_info(sesn)['result']['authuser']
assert failed(s.session_auth_login(sesn, "viktor", "2viktor"))
assert worked(s.session_auth_login(sesn, "viktor", "viktor"))
print s.session_info(sesn)['result']['authuser']
assert worked(s.session_deauth(sesn))
print s.session_info(sesn)['result']["authuser"]
assert worked(s.session_stop(sesn))
assert failed(s.session_info(sesn))

print s.server_list_functions()["result"]

sesn = s.session_start()["result"]
s.session_auth_login(sesn, "viktor", "viktor")

assert failed(s.mutex_acquire(sesn, "gurka", "Mr. Cucumber", True))
assert failed(s.mutex_acquire(sesn, "gurka", "Mr. Cucumber", False))
assert worked(s.mutex_acquire(sesn, "tester", "Mr. Cucumber", True))
assert failed(s.mutex_acquire(sesn, "tester", "Mr. Cucumber", False))

print s.mutex_info(sesn, "tester")

sesn = s.session_start()["result"]
s.session_auth_login(sesn, "viktor", "viktor")

assert failed(s.mutex_release(sesn, "tester", False))
assert worked(s.mutex_release(sesn, "tester", True))

assert worked(s.mutex_acquire(sesn, "tester", "Got it!", False))
assert s.mutex_info(sesn, "tester")["result"]["state"] == "held"
assert worked(s.mutex_release(sesn, "tester", False))
assert s.mutex_info(sesn, "tester")["result"]["state"] == "free"

raise SystemExit()

print s.server_function_definition("server_function_definition")["result"]

print s.server_documentation("server_function_definition")["result"]

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

print s.account_fetch("viktor", {"account": True, "uid": True, "owner": True, "owner_data": {"person": True, "firstname": True, "lastname": True, "account_data": {"account": True}}})

print s.person_update("viktor", {"lastname": u"Foügstedt"})

print s.person_fetch("viktor", {"firstname": True, "lastname": True})

print s.person_update("viktor", {"firstname": "Vixtor", "lastname": u"Fougstedt"})
print s.person_fetch("viktor", {"firstname": True, "lastname": True})

print s.person_update("viktor", {"firstname": u"Viktor"})
print s.person_fetch("viktor", {"firstname": True, "lastname": True})

print s.person_get_name("viktor")

