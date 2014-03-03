#!/usr/bin/env python
""" ADHOC basic API test suite"""
from framework import *
from util import *
import tempfile


class T0300_DhcpXfer(SuperUserTests):
    """ Test dhcpd data transfer from old database"""
    
    def do(self):
        with AssertAccessError(self):
            self.proxy.dhcp_xfer()


class T0310_DhcpdConf(AuthTests):
    """ Test dhcpd configuration"""
    
    def do(self):
        if self.proxy != self.superuser:
            return
        with AssertAccessError(self):
            ret = self.proxy.dhcpd_config("A")
            of = tempfile.NamedTemporaryFile(mode='w+b')
            of.write(ret)

if __name__ == "__main__":
    sys.exit(main())
