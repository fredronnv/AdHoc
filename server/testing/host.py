#!/usr/bin/env python
# -*- coding: utf8 -*-

""" ADHOC host API test suite"""
from framework import *
from util import *

data_template = {
                 "optionspace": True,
                 "host": True,
                 "mac": True,
                 "dns": True,
                 "room": True,
                 "status": True,
                 "info": True, 
                 "group": True,
                 "changed_by": True,
                 "mtime": True
                 }


class T1300_HostList(UnAuthTests):
    """ Test host listing """

    def do(self):
        with AssertAccessError(self):
            ret = self.proxy.host_dig({}, data_template)
            
            assert len(ret) > 0, "Too few hosts returned"
            #for ds in ret:
                #print ds.re, ds.host, ds.info
  
  
class T1310_HostFetch(UnAuthTests):
    """ Test host_fetch """
    
    def do(self):
        hosts = [x.host for x in self.superuser.host_dig({}, data_template)]
        
        n = 0
        for host in hosts:
            ret = self.proxy.host_fetch(host, data_template)
            self.assertindict(ret, data_template.keys(), exact=True)
            n += 1
            if n > 50:  # There are too many hosts to check, 50 is enough
                break
            
            
class T1320_HostCreate(UnAuthTests):
    """ Test host_create """
    
    def do(self):  
        if self.proxy != self.superuser:
            return
        try:
            self.superuser.host_destroy('QZ1243A')
        except:
            pass
        with AssertAccessError(self):
            try:
                self.proxy.host_create('QZ1243A', '00:01:02:03:04:05', {})
                ret = self.superuser.host_fetch('QZ1243A', data_template)
                self.assertindict(ret, data_template.keys(), exact=True)
                
                assert ret.host == "QZ1243A", "Bad host, is % should be %s" % (ret.host, "QZ1243A")
                assert ret.info == "TestHost", "Info is " + ret.info + "but should be 'TestHost'"
                assert ret.group == "altiris", "Bad group %s, should be 'altiris'" % ret.group
            finally:
                try:
                    self.superuser.host_destroy('QZ1243A')
                except:
                    pass
        
        
class T1330_HostDestroy(UnAuthTests):
    """ Test host destroy """
    
    def do(self):
        if self.proxy != self.superuser:
            return
        self.superuser.host_create('QZ1243A', 'altiris', "TestHost", {})
        try:
            with AssertAccessError(self):
                self.proxy.host_destroy('QZ1243A')
                with AssertRPCCError("LookupError::NoSuchHost", True):
                    self.superuser.host_fetch('QZ1243A', data_template)
        finally:
            try:
                self.superuser.host_destroy('QZ1243A')
            except:
                pass
            
        
class T1340_HostSetName(UnAuthTests):
    """ Test setting name of a host"""
    
    def do(self):
        if self.proxy != self.superuser:
            return
        self.superuser.host_create('QZ1243A', 'altiris', "TestHost", {})
        with AssertAccessError(self):
            try:
                self.proxy.host_update('QZ1243A', {"host": 'ZQ1296'})
                nd = self.superuser.host_fetch('ZQ1296', data_template)
                assert nd.host == "ZQ1296", "Bad host"
                assert nd.info == "TestHost", "Bad info"
                assert nd.group == "altiris", "Bad group %s, should be 'altiris'" % nd.group
            finally:
                try:
                    self.superuser.host_destroy('ZQ1296')
                except:
                    pass
                
                
class T1350_HostSetInfo(UnAuthTests):
    """ Test setting info on a host"""
    
    def do(self):
        if self.proxy != self.superuser:
            return
        self.superuser.host_create('QZ1243A', 'altiris', "TestHost", {})
        with AssertAccessError(self):
            try:
                self.proxy.host_update('QZ1243A', {"info": "ZQ1296 option"})
                nd = self.superuser.host_fetch('QZ1243A', data_template)
                assert nd.host == "QZ1243A", "Bad host"
                assert nd.info == "ZQ1296 option", "Bad info"
                assert nd.group == "altiris", "Bad group %s, should be 'altiris'" % nd.group
            finally:
                try:
                    self.superuser.host_destroy('QZ1243A')
                except:
                    pass
                
                
class T1350_HostSetParent(UnAuthTests):
    """ Test setting group on a host"""
    
    def do(self):
        if self.proxy != self.superuser:
            return
        self.superuser.host_create('QZ1243A', 'altiris', "TestHost", {})
        with AssertAccessError(self):
            try:
                self.proxy.host_update('QZ1243A', {"group": "plain"})
                nd = self.superuser.host_fetch('QZ1243A', data_template)
                assert nd.host == "QZ1243A", "Bad host"
                assert nd.info == "TestHost", "Bad info"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
            finally:
                try:
                    self.superuser.host_destroy('QZ1243A')
                except:
                    pass
        
if __name__ == "__main__":
    sys.exit(main())
