#!/usr/bin/env python
# -*- coding: utf8 -*-

""" ADHOC global_option API test suite"""
from framework import *
from util import *


class T0900_GlobalOptionList(UnAuthTests):
    """ Test global_option listing """

    def do(self):
        with AssertAccessError(self):
            ret = self.proxy.global_option_dig({}, {"global_option": True, "value": True, "name": True})
            
            assert len(ret) > 0, "Too few global_options returned"
           
           
class T0910_GlobalOptionFetch(UnAuthTests):
    """ Test global_option_fetch """
    
    def do(self):
        global_options = [x.global_option for x in self.superuser.global_option_dig({}, {"global_option": True})]
        
        n = 0
        for global_option in global_options:
            ret = self.proxy.global_option_fetch(global_option, {"global_option": True, "value": True, "name": True})
            assert "value" in ret, "Key value missing in returned struct from global_option_fetch"
            assert "name" in ret, "Key name missing in returned struct from global_option_fetch"
            assert "global_option" in ret, "Kay global_option  missing in returned struct from global_option_fetch" 
            n += 1
            if n > 50:  # There are too many global_options to check, 50 is enough
                break
            
            
class T0920_GlobalOptionCreate(NetworkAdminTests):
    """ Test global_option_create """
    
    def do(self):
        try:
            goid = None
            with AssertAccessError(self):
                goid = self.proxy.global_option_create('finger-server', '192.5.50.11', False)
                ret = self.superuser.global_option_fetch(goid, {"global_option": True, "value": True, "name": True})
                assert "value" in ret, "Key value missing in returned struct from global_option_fetch"
                assert "name" in ret, "Key name missing in returned struct from global_option_fetch" 
                assert "global_option" in ret, "Kay global_option  missing in returned struct from global_option_fetch" 
                assert ret.global_option == goid, "Bad global_option id, is %d should be %s" % (ret.global_option, goid)
                assert ret.name == "finger-server", "Bad global_option, is % should be %s" % (ret.name, "QZ1243A")
                assert ret.value == "192.5.50.11", "Value is " + ret.value + " but should be 'a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3'"
        finally:
            if goid:
                self.superuser.global_option_destroy(goid)
                
        
class T0930_GlobalOptionDestroy(NetworkAdminTests):
    """ Test global_option destroy """
    
    def do(self):
        goid = self.superuser.global_option_create('finger-server', '192.5.50.11', False)
        try:
            with AssertAccessError(self):
                # print "DESTROYING GO", self.proxy.goid
                self.proxy.global_option_destroy(goid)
                with AssertRPCCError("LookupError::NoSuchGlobalOption", True):
                    self.superuser.global_option_fetch(goid, {"global_option": True, "name": True})
                goid = None
        finally:
            if goid:
                try:
                    self.superuser.global_option_destroy(goid)
                except:
                    pass
        
        
class T0940_GlobalOptionSetName(NetworkAdminTests):
    """ Test setting name of a global_option"""
    
    def do(self):
        self.proxy.goid = self.superuser.global_option_create('finger-server', '192.5.50.11', False)
        with AssertAccessError(self):
            try:
                self.proxy.global_option_update(self.proxy.goid, {"name": 'irc-server'})
                nd = self.superuser.global_option_fetch(self.proxy.goid, {"value": True, "name": True})
                assert nd.name == "irc-server", "Bad global_option name"
                assert nd.value == '192.5.50.11', "Bad value"
            finally:
                self.superuser.global_option_destroy(self.proxy.goid)
                
                
class T0950_GlobalOptionSetValue(NetworkAdminTests):
    """ Test setting value on a global_option"""
    
    def do(self):
        self.proxy.goid = self.superuser.global_option_create('finger-server', '192.5.50.11', False)
        with AssertAccessError(self):
            try:
                self.proxy.global_option_update(self.proxy.goid, {"value": "192.5.50.34"})
                nd = self.superuser.global_option_fetch(self.proxy.goid, {"value": True, "name": True})
                assert nd.name == "finger-server", "Bad global_option name"
                assert nd.value == '192.5.50.34', "Bad value"
            finally:
                self.superuser.global_option_destroy(self.proxy.goid)
        
if __name__ == "__main__":
    sys.exit(main())
