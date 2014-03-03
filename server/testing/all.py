#!/usr/bin/env python
""" ADHOC API test suite
    This suite of tests are designed to test the ADHOC API."""

from framework import *
from basic import *
from dhcpd import *
from shared_network import *
from dhcp_server import *
from optionspace import *
from room import *
from building import *
from global_option import *
from option_def import *
from subnetwork import *
from group import *
from host_class import *
from pool import *
from host import *
from pool_range import *
#from mutex import *

if __name__ == "__main__":
    sys.exit(main())
