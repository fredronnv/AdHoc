#!/usr/bin/env python2.6

from rpcc_client import *

proxy = RPCC("http://localhost:12121", 0, attrdicts=True)
print proxy.hello()
print proxy.hello_to(os.environ["USER"])