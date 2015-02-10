#!/usr/bin/env python
# -*- coding: utf8 -*-

""" ADHOC optionspace API test suite"""
from framework import *
from util import *


class T0600_OptionspaceList(UnAuthTests):
    """ Test optionspace listing """

    def do(self):
        with AssertAccessError(self):
            #ret = 
            self.proxy.optionspace_dig({}, {"type": True, "info": True, "optionspace": True})
            
            #assert len(ret) > 0, "Too few optionspaces returned"
            #for ds in ret:
                #print ds.type, ds.optionspace, ds.info
  
  
class T0610_OptionspaceFetch(UnAuthTests):
    """ Test optionspace_fetch """
    
    def do(self):
        optionspaces = [x.optionspace for x in self.superuser.optionspace_dig({}, {"optionspace":True})]
        
        for optionspace in optionspaces:
            ret = self.proxy.optionspace_fetch(optionspace, {"type": True, "info": True, "optionspace": True})
            assert "type" in ret, "Key type missing in returned struct from optionspace_fetch"
            assert "info" in ret, "Key info missing in returned struct from optionspace_fetch"
            assert "optionspace" in ret, "Key optionspace missing in returned struct from optionspace_fetch"
            
            
class T0620_OptionspaceCreate(NetworkAdminTests):
    """ Test optionspace_create """
    
    def do(self):
        try:
            self.superuser.optionspace_destroy('ACME')
        except:
            pass
        try:
            with AssertAccessError(self):
                self.proxy.optionspace_create('ACME', 'vendor', "TestOptionspace")
                ret = self.superuser.optionspace_fetch('ACME', {"type": True, "info": True, "optionspace": True})
                assert "type" in ret, "Key type missing in returned struct from optionspace_fetch"
                assert "info" in ret, "Key info missing in returned struct from optionspace_fetch"
                assert "optionspace" in ret, "Key optionspace missing in returned struct from optionspace_fetch" 
                assert ret.optionspace == "ACME", "Bad optionspace, is % should be %s" % (ret.optionspace, "ACME")
                assert ret.type == "vendor", "Type is " + ret.type + " but should be 'vendor'"
                assert ret.info == "TestOptionspace", "Info is " + ret.info + "but should be 'TestOptionspace'"
        finally:
            try:
                self.superuser.optionspace_destroy('ACME')
            except:
                pass
            
        
class T0630_OptionspaceDestroy(NetworkAdminTests):
    """ Test optionspace destroy """
    
    def do(self):
        
        self.superuser.optionspace_create('ACME', 'vendor', "TestOptionspace")
        try:
            with AssertAccessError(self):
                self.proxy.optionspace_destroy('ACME')
                with AssertRPCCError("LookupError::NoSuchOptionspace", True):
                    self.superuser.optionspace_fetch('ACME', {"optionspace": True})
        finally:
            try:
                self.superuser.optionspace_destroy('ACME')
            except:
                pass
        
        
class T0640_OptionspaceSetName(NetworkAdminTests):
    """ Test setting optionspace of an optionspace"""
    
    def do(self):
        self.superuser.optionspace_create('ACME', 'vendor', "TestOptionspace")
        with AssertAccessError(self):
            try:
                self.proxy.optionspace_update('ACME', {"optionspace": 'IKEA'})
                nd = self.superuser.optionspace_fetch('IKEA', {"type": True, "info": True, "optionspace": True})
                assert nd.optionspace == "IKEA", "Bad optionspace optionspace"
                assert nd.type == 'vendor', "Bad type"
                assert nd.info == "TestOptionspace", "Bad info"
            finally:
                try:
                    self.superuser.optionspace_destroy('IKEA')
                except:
                    pass
                try:
                    self.superuser.optionspace_destroy('ACME')
                except:
                    pass
                
                
class T0650_OptionspaceSetInfo(NetworkAdminTests):
    """ Test setting info on an optionspace"""
    
    def do(self):
        self.superuser.optionspace_create('ACME', 'vendor', "TestOptionspace")
        with AssertAccessError(self):
            try:
                self.proxy.optionspace_update('ACME', {"info": "IKEA space"})
                nd = self.superuser.optionspace_fetch('ACME', {"type": True, "info": True, "optionspace": True})
                assert nd.optionspace == "ACME", "Bad optionspace optionspace"
                assert nd.type == 'vendor', "Bad type"
                assert nd.info == "IKEA space", "Bad info"
            finally:
                self.superuser.optionspace_destroy('ACME')
                
                
class T0650_OptionspaceSetType(NetworkAdminTests):
    """ Test setting type on an optionspace"""
    
    def do(self):
        self.superuser.optionspace_create('ACME', 'vendor', "TestOptionspace")
        with AssertAccessError(self):
            try:
                self.proxy.optionspace_update('ACME', {"type": "site"})
                nd = self.superuser.optionspace_fetch('ACME', {"type": True, "info": True, "optionspace": True})
                assert nd.optionspace == "ACME", "Bad optionspace optionspace"
                assert nd.type == 'site', "Bad type"
                assert nd.info == "TestOptionspace", "Bad info"
            finally:
                self.superuser.optionspace_destroy('ACME')
        
if __name__ == "__main__":
    sys.exit(main())
