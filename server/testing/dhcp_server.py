#!/usr/bin/env python
# -*- coding: utf8 -*-

""" ADHOC dhcp_server API test suite"""
from framework import *
from util import *


class T0500_DHCPServerList(UnAuthTests):
    """ Test dhcp_server listing """

    def do(self):
        with AssertAccessError(self):
            ret = self.proxy.dhcp_server_dig({}, {"dhcp_server_id": True, "info": True, "name": True})
            
            #assert len(ret) > 0, "Too few dhcp_servers returned"
            #for ds in ret:
                #print ds.dhcp_server_id, ds.name, ds.info
  
  
class T0510_DHCPServerFetch(UnAuthTests):
    """ Test dhcp_server_fetch """
    
    def do(self):
        dhcp_servers = [x.dhcp_server_id for x in self.superuser.dhcp_server_dig({}, {"dhcp_server_id":True})]
        
        for dhcp_server in dhcp_servers:
            ret = self.proxy.dhcp_server_fetch(dhcp_server, {"dhcp_server_id": True, "info": True, "name": True})
            assert "dhcp_server_id" in ret, "Key dhcp_server missing in returned struct from dhcp_server_fetch"
            assert "info" in ret, "Key info missing in returned struct from dhcp_server_fetch"
            assert "name" in ret, "Key name missing in returned struct from dhcp_server_fetch"
            
            
class T0520_DHCPServerCreate(UnAuthTests):
    """ Test dhcp_server_create """
    
    def do(self):  
        if self.proxy != self.superuser:
            return
        with AssertAccessError(self):
            self.proxy.dhcp_server_create('Q', 'apa.bepa.chalmers.se', "TestDHCPServer")
            ret = self.superuser.dhcp_server_fetch('Q', {"dhcp_server_id": True, "info": True, "name": True})
            assert "dhcp_server_id" in ret, "Key dhcp_server_id missing in returned struct from dhcp_server_fetch"
            assert "info" in ret, "Key info missing in returned struct from dhcp_server_fetch"
            assert "name" in ret, "Key name missing in returned struct from dhcp_server_fetch" 
            assert ret.dhcp_server_id == "Q", "Bad DHCP server ID, is % should be %s" % (ret.dhcp_server_id, "Q")
            assert ret.name == "apa.bepa.chalmers.se", "Name is " + ret.name + " but should be 'apa.bepa.chalmers.se'"
        
        
class T0530_DHCPServerDestroy(UnAuthTests):
    """ Test dhcp_server destroy """
    
    def do(self):
        if self.proxy != self.superuser:
            return
        with AssertAccessError(self):
            self.proxy.dhcp_server_destroy('Q')
            with AssertRPCCError("LookupError::NoSuchDHCPServer", True):
                self.superuser.dhcp_server_fetch('Q', {"dhcp_server_id": True})
        
        
class T0540_DHCPServerSetName(UnAuthTests):
    """ Test setting name  of a dhcp_server"""
    
    def do(self):
        if self.proxy != self.superuser:
            return
        self.superuser.dhcp_server_create('Q', 'apa.chalmers.se', "Testserver 2")
        with AssertAccessError(self):
            try:
                self.proxy.dhcp_server_update('Q', {"name": 'apa.bepa.chalmers.se'})
                nd = self.superuser.dhcp_server_fetch('Q', {"dhcp_server_id": True, "info": True, "name": True})
                assert nd.dhcp_server_id == "Q", "Bad dhcp_server id"
                assert nd.name == 'apa.bepa.chalmers.se', "Bad name"
                assert nd.info == "Testserver 2", "Bad info"
            finally:
                self.superuser.dhcp_server_destroy('Q')
                
                
class T0550_DHCPServerSetInfo(UnAuthTests):
    """ Test setting info on a dhcp_server"""
    
    def do(self):
        if self.proxy != self.superuser:
            return
        self.superuser.dhcp_server_create('Q', 'apa.chalmers.se', "Testserver 2")
        with AssertAccessError(self):
            try:
                self.proxy.dhcp_server_update('Q', {"info": "Provserver 1"})
                nd = self.superuser.dhcp_server_fetch('Q', {"dhcp_server_id": True, "info": True, "name": True})
                assert nd.dhcp_server_id == "Q", "Bad dhcp_server id"
                assert nd.name == 'apa.chalmers.se', "Bad name"
                assert nd.info == "Provserver 1", "Bad info"
            finally:
                self.superuser.dhcp_server_destroy('Q')
        
if __name__ == "__main__":
    sys.exit(main())
