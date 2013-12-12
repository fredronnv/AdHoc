#!/usr/bin/env python
# -*- coding: utf8 -*-

""" ADHOC optionspace API test suite"""
from framework import *
from util import *


class T0500_OptionspaceList(UnAuthTests):
    """ Test optionspace listing """

    def do(self):
        with AssertAccessError(self):
            ret = self.proxy.optionspace_dig({}, {"type": True, "info": True, "name": True})
            
            #assert len(ret) > 0, "Too few optionspaces returned"
            #for ds in ret:
                #print ds.type, ds.name, ds.info
  
  
class T0510_OptionspaceFetch(UnAuthTests):
    """ Test optionspace_fetch """
    
    def do(self):
        optionspaces = [x.name for x in self.superuser.optionspace_dig({}, {"name":True})]
        
        for optionspace in optionspaces:
            ret = self.proxy.optionspace_fetch(optionspace, {"type": True, "info": True, "name": True})
            assert "type" in ret, "Key type missing in returned struct from optionspace_fetch"
            assert "info" in ret, "Key info missing in returned struct from optionspace_fetch"
            assert "name" in ret, "Key name missing in returned struct from optionspace_fetch"
            
            
class T0520_OptionspaceCreate(UnAuthTests):
    """ Test optionspace_create """
    
    def do(self):  
        if self.proxy != self.superuser:
            return
        with AssertAccessError(self):
            self.proxy.optionspace_create('ACME', 'vendor', "TestOptionspace")
            ret = self.superuser.optionspace_fetch('ACME', {"type": True, "info": True, "name": True})
            assert "type" in ret, "Key type missing in returned struct from optionspace_fetch"
            assert "info" in ret, "Key info missing in returned struct from optionspace_fetch"
            assert "name" in ret, "Key name missing in returned struct from optionspace_fetch" 
            assert ret.name == "ACME", "Bad optionspace, is % should be %s" % (ret.name, "ACME")
            assert ret.type == "vendor", "Type is " + ret.type + " but should be 'vendor'"
            assert ret.info == "TestOptionspace", "Info is " + ret.info + "but should be 'TestOptionspace'"
        
        
class T0530_OptionspaceDestroy(UnAuthTests):
    """ Test optionspace destroy """
    
    def do(self):
        if self.proxy != self.superuser:
            return
        with AssertAccessError(self):
            self.proxy.optionspace_destroy('ACME')
            with AssertRPCCError("LookupError::NoSuchOptionspace", True):
                self.superuser.optionspace_fetch('ACME', {"name": True})
        
        
class T0540_OptionspaceSetName(UnAuthTests):
    """ Test setting name of an optionspace"""
    
    def do(self):
        if self.proxy != self.superuser:
            return
        self.superuser.optionspace_create('ACME', 'vendor', "TestOptionspace")
        with AssertAccessError(self):
            try:
                self.proxy.optionspace_update('ACME', {"name": 'IKEA'})
                nd = self.superuser.optionspace_fetch('IKEA', {"type": True, "info": True, "name": True})
                assert nd.name == "IKEA", "Bad optionspace name"
                assert nd.type == 'vendor', "Bad type"
                assert nd.info == "TestOptionspace", "Bad info"
            finally:
                self.superuser.optionspace_destroy('IKEA')
                
                
class T0550_OptionspaceSetInfo(UnAuthTests):
    """ Test setting info on an optionspace"""
    
    def do(self):
        if self.proxy != self.superuser:
            return
        self.superuser.optionspace_create('ACME', 'vendor', "TestOptionspace")
        with AssertAccessError(self):
            try:
                self.proxy.optionspace_update('ACME', {"info": "IKEA space"})
                nd = self.superuser.optionspace_fetch('ACME', {"type": True, "info": True, "name": True})
                assert nd.name == "ACME", "Bad optionspace name"
                assert nd.type == 'vendor', "Bad type"
                assert nd.info == "IKEA space", "Bad info"
            finally:
                self.superuser.optionspace_destroy('ACME')
                
                
class T0550_OptionspaceSetType(UnAuthTests):
    """ Test setting type on an optionspace"""
    
    def do(self):
        if self.proxy != self.superuser:
            return
        self.superuser.optionspace_create('ACME', 'vendor', "TestOptionspace")
        with AssertAccessError(self):
            try:
                self.proxy.optionspace_update('ACME', {"type": "site"})
                nd = self.superuser.optionspace_fetch('ACME', {"type": True, "info": True, "name": True})
                assert nd.name == "ACME", "Bad optionspace name"
                assert nd.type == 'site', "Bad type"
                assert nd.info == "TestOptionspace", "Bad info"
            finally:
                self.superuser.optionspace_destroy('ACME')
        
if __name__ == "__main__":
    sys.exit(main())
