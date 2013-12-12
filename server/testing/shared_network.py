#!/usr/bin/env python
# -*- coding: utf8 -*-

""" ADHOC network API test suite"""
from framework import *
from util import *


class T0400_networkList(UnAuthTests):
    """ Test network listing """

    def do(self):
        with AssertAccessError(self):
            ret = self.proxy.network_dig({}, {"network": True, "info": True, "authoritative": True})
            
            assert len(ret) > 90, "Too few networks returned"
            #for n in ret:
                #print n
                #print n.authoritative, n.network, n.info
  
  
class T0410_networkFetch(UnAuthTests):
    """ Test network_fetch """
    
    def do(self):
        networks = [x.network for x in self.superuser.network_dig({}, {"network":True})]
        
        for network in networks:
            ret = self.proxy.network_fetch(network, {"network": True, "info": True, "authoritative": True})
            assert "network" in ret, "Key network missing in returned struct from network_fetch"
            assert "info" in ret, "Key authoritative missing in returned struct from network_fetch"
            assert "authoritative" in ret, "Key authoritative missing in returned struct from network_fetch"
            
            
class T0420_networkCreate(UnAuthTests):
    """ Test network_create """
    
    def do(self):  
        if self.proxy != self.superuser:
            return
        with AssertAccessError(self):
            self.proxy.network_create('network_test', False, "Testnätverk")
            ret = self.superuser.network_fetch('network_test', {"network": True, "info": True, "authoritative": True})
            assert "network" in ret, "Key network missing in returned struct from network_fetch"
            assert "info" in ret, "Key authoritative missing in returned struct from network_fetch"
            assert "authoritative" in ret, "Key authoritative missing in returned struct from network_fetch" 
            assert ret.network == "network_test", "Bad netid, is % should be %s" % (ret.network, "network_test")
            assert ret.authoritative == False, "Authoritative is " + ret.authoritative + " but should be False"
        
        
class T0430_networkDestroy(UnAuthTests):
    """ Test network destroy """
    
    def do(self):
        if self.proxy != self.superuser:
            return
        with AssertAccessError(self):
            self.proxy.network_destroy('network_test')
            with AssertRPCCError("LookupError::NoSuchNetwork", True):
                self.superuser.network_fetch('network_test', {"network": True})
        
        
class T0440_networkSetAuthoritative(UnAuthTests):
    """ Test setting authoritative flag on a network"""
    
    def do(self):
        if self.proxy != self.superuser:
            return
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        with AssertAccessError(self):
            try:
                self.proxy.network_update('network_test', {"authoritative": True})
                nd = self.superuser.network_fetch('network_test', {"network": True, "info": True, "authoritative": True})
                assert nd.network == "network_test", "Bad network id"
                assert nd.authoritative, "Bad autoritativity"
                assert nd.info == "Testnätverk 2", "Bad info"
            finally:
                self.superuser.network_destroy('network_test')
                
                
class T0450_networkSetInfo(UnAuthTests):
    """ Test setting info on a network"""
    
    def do(self):
        if self.proxy != self.superuser:
            return
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        with AssertAccessError(self):
            try:
                self.proxy.network_update('network_test', {"info": "Provnät 1"})
                nd = self.superuser.network_fetch('network_test', {"network": True, "info": True, "authoritative": True})
                assert nd.network == "network_test", "Bad network id"
                assert not nd.authoritative, "Bad autoritativity"
                assert nd.info == "Provnät 1", "Bad info"
            finally:
                self.superuser.network_destroy('network_test')
        
if __name__ == "__main__":
    sys.exit(main())
