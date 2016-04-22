#!/usr/bin/env python
""" ADHOC basic API test suite"""
from framework import *
from testutil import *


class T0100_DhcpXfer(SuperUserTests):
    """ Test dhcpd data transfer from old database"""
    
    def do(self):
        with AssertAccessError(self):
            self.proxy.dhcp_xfer()


class T0110_DhcpdConf(AuthTests):
    """ Test dhcpd configuration"""
    
    def do(self):
        if self.proxy != self.superuser:
            return
        with AssertAccessError(self):
            of = open('/Users/bernerus/tmp/dhcpd.conf', 'w')
            ret = self.proxy.dhcpd_config("A")
            of.write(ret.encode('utf-8'))

if __name__ == "__main__":
    sys.exit(main())
