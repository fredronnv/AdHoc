#!/usr/bin/env python
# -*- coding: utf8 -*-

""" ADHOC dhcp_server API test suite"""
from framework import *
from util import *


class T0500_DHCPServerList(UnAuthTests):
    """ Test dhcp_server listing """

    def do(self):
        with AssertAccessError(self):
            # ret = \
            self.proxy.dhcp_server_dig({}, {"dhcp_server": True, "info": True, "dns": True})
            
#             assert len(ret) > 0, "Too few dhcp_servers returned"
#             for ds in ret:
#                 print ds.dhcp_server, ds.dns, ds.info
  
  
class T0510_DHCPServerFetch(UnAuthTests):
    """ Test dhcp_server_fetch """
    
    def do(self):
        dhcp_servers = [x.dhcp_server for x in self.superuser.dhcp_server_dig({}, {"dhcp_server": True})]
        
        for dhcp_server in dhcp_servers:
            ret = self.proxy.dhcp_server_fetch(dhcp_server, {"dhcp_server": True, "info": True, "dns": True})
            assert "dhcp_server" in ret, "Key dhcp_server missing in returned struct from dhcp_server_fetch"
            assert "info" in ret, "Key info missing in returned struct from dhcp_server_fetch"
            assert "dns" in ret, "Key dns missing in returned struct from dhcp_server_fetch"
            
            
class T0520_DHCPServerCreate(SuperUserTests):
    """ Test dhcp_server_create """
    
    def do(self):
        try:
            self.superuser.dhcp_server_destroy('Q')
        except:
            pass
        with AssertAccessError(self):
            self.proxy.dhcp_server_create('Q', 'apa.bepa.chalmers.se', "TestDHCPServer")
            ret = self.superuser.dhcp_server_fetch('Q', {"dhcp_server": True, "info": True, "dns": True})
            assert "dhcp_server" in ret, "Key dhcp_server missing in returned struct from dhcp_server_fetch"
            assert "info" in ret, "Key info missing in returned struct from dhcp_server_fetch"
            assert "dns" in ret, "Key dns missing in returned struct from dhcp_server_fetch" 
            assert ret.dhcp_server == "Q", "Bad DHCP server ID, is % should be %s" % (ret.dhcp_server, "Q")
            assert ret.dns == "apa.bepa.chalmers.se", "DNS is " + ret.dns + " but should be 'apa.bepa.chalmers.se'"
        
        
class T0530_DHCPServerDestroy(SuperUserTests):
    """ Test dhcp_server destroy """
    
    def do(self):
        try:
            self.superuser.dhcp_server_create('Q', 'apa.bepa.chalmers.se', "TestDHCPServer")
        except:
            pass
        try:
            with AssertAccessError(self):
                self.proxy.dhcp_server_destroy('Q')
                with AssertRPCCError("LookupError::NoSuchDHCPServer", True):
                    self.superuser.dhcp_server_fetch('Q', {"dhcp_server": True})
        finally:
            try:
                self.superuser.dhcp_server_destroy('Q')
            except:
                pass
        
        
class T0540_DHCPServerSetDNS(SuperUserTests):
    """ Test setting dns  of a dhcp_server"""
    
    def do(self):
        self.superuser.dhcp_server_create('Q', 'apa.chalmers.se', "Testserver 2")
        with AssertAccessError(self):
            try:
                self.proxy.dhcp_server_update('Q', {"dns": 'apa.bepa.chalmers.se'})
                nd = self.superuser.dhcp_server_fetch('Q', {"dhcp_server": True, "info": True, "dns": True})
                assert nd.dhcp_server == "Q", "Bad dhcp_server id"
                assert nd.dns == 'apa.bepa.chalmers.se', "Bad dns"
                assert nd.info == "Testserver 2", "Bad info"
            finally:
                self.superuser.dhcp_server_destroy('Q')
                
                
class T0550_DHCPServerSetInfo(SuperUserTests):
    """ Test setting info on a dhcp_server"""
    
    def do(self):
        self.superuser.dhcp_server_create('Q', 'apa.chalmers.se', "Testserver 2")
        with AssertAccessError(self):
            try:
                self.proxy.dhcp_server_update('Q', {"info": "Provserver 1"})
                nd = self.superuser.dhcp_server_fetch('Q', {"dhcp_server": True, "info": True, "dns": True})
                assert nd.dhcp_server == "Q", "Bad dhcp_server id"
                assert nd.dns == 'apa.chalmers.se', "Bad dns"
                assert nd.info == "Provserver 1", "Bad info"
            finally:
                self.superuser.dhcp_server_destroy('Q')
        
if __name__ == "__main__":
    sys.exit(main())
