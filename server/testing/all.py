#!/usr/bin/env python
""" ADHOC API test suite
    This suite of tests are designed to test the ADHOC API."""

from framework import *
from basic import *
#from dhcpd import *
from shared_network import *
from dhcp_server import *
from optionspace import *
#from mutex import *

if __name__ == "__main__":
    sys.exit(main())
