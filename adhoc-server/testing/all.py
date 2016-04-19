#!/usr/bin/env python
""" ADHOC API test suite 
    This suite of tests are designed to test the ADHOC API."""

from basic import *
from building import *
from dhcp_server import *
from dhcpd import *
from framework import *
from global_option import *
from group import *
from host import *
from host_class import *
from option_def import *
from optionspace import *
from pool import *
from pool_range import *
from room import *
from shared_network import *
from subnetwork import *


# from mutex import *
if __name__ == "__main__":
    sys.exit(main())
