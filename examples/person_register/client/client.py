#!/usr/bin/env python2.6

import rpcc_client

proxy=rpcc_client.RPCC("http://localhost:12121", 0, attrdicts=True)

for fn in proxy.server_list_functions():
    print fn
    
proxy.person_create("nissehul", "Nisse","Hult", 46)