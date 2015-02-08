#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

from rpcc_client import *

proxy = RPCC("http://localhost:12121", 0, attrdicts=True)
print proxy.add2(1,2)
print proxy.sub2(7,2)
print proxy.mul2(5, 8)
print proxy.div2(8, 3)