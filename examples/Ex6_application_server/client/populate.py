#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

from rpcc_client import *


def createperson(proxy, person_id, fname, lname, email, password):
    try:
        proxy.user_create(person_id, fname, lname, email, password)
    except RPCCLookupError:
        pass

if __name__ == "__main__":
    proxy = RPCC("http://localhost:12121", 0, attrdicts=True)
    
    proxy.session_auth_login("#root#", "gurkburk")

    createperson(proxy, "nissehul", "Nisse", "Hult", "nisse.hult@hotmail.com", "qasdrt44")
    createperson(proxy, "nilshult", "Nils", "Hult", "nils.hult@hotmail.com", "myPassword")
    createperson(proxy, "barryo", "Barack", "Obama", "prezident@yellowhouse.gov", "myPassword")
    createperson(proxy, "arnie", "Arnold", "Schwarzenegger", "terminator@future.movie", "B0dYbU1LdEr")
    
    proxy.session_deauth()
    
    proxy.session_auth_login("nissehul", "qasdrt44")
    
    mails = proxy.user_dig({"user": "nissehul"}, {"email": True})
    for m in mails:
        print m.email
