#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

import xmlrpclib

s = xmlrpclib.ServerProxy("http://venus.ita.chalmers.se:12121/RPC2", allow_none=True)

print s.account_fetch("acc-viktor", {"account": True, "uid": True})

print s.account_fetch("acc-viktor", {"account": True, "uid": True, "owner": True, "owner-data": {"person": True, "firstname": True, "account-data": {"account": True}}})

