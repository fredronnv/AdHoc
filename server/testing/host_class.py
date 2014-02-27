#!/usr/bin/env python
# -*- coding: utf8 -*-

""" ADHOC host_class API test suite"""
from framework import *
from util import *

data_template = {
                 "optionspace": True,
                 "vendor_class_id": True,
                 "info": True,
                 "host_class": True,
                 "changed_by": True,
                 "mtime": True,
                 "optionset_data": {'_': True, "_remove_nulls": True}
                 }


class T0100_HostClassList(UnAuthTests):
    """ Test host_class listing """

    def do(self):
        with AssertAccessError(self):
            ret = self.proxy.host_class_dig({}, data_template)
            
            assert len(ret) > 0, "Too few host_classs returned"
            #for ds in ret:
                #print ds.re, ds.host_class, ds.info
  
  
class T0110_HostClassFetch(UnAuthTests):
    """ Test host_class_fetch """
    
    def do(self):
        host_classs = [x.host_class for x in self.superuser.host_class_dig({}, data_template)]
        
        n = 0
        for host_class in host_classs:
            ret = self.proxy.host_class_fetch(host_class, data_template)
            self.assertindict(ret, data_template.keys(), exact=True)
            n += 1
            if n > 50:  # There are too many host_classs to check, 50 is enough
                break
            
            
class T0120_HostClassCreate(AuthTests):
    """ Test host_class_create """
    
    def do(self):
        try:
            self.superuser.host_class_destroy('QZ1243A')
        except:
            pass
        with AssertAccessError(self):
            try:
                self.proxy.host_class_create('QZ1243A', 'altiris', "TestHostClass", {})
                ret = self.superuser.host_class_fetch('QZ1243A', data_template)
                self.assertindict(ret, data_template.keys(), exact=True)
                
                assert ret.host_class == "QZ1243A", "Bad host_class host_class, is % should be %s" % (ret.host_class, "QZ1243A")
                assert ret.info == "TestHostClass", "Info is " + ret.info + "but should be 'TestHostClass'"
                assert ret.vendor_class_id == "altiris", "Bad vendor_class_id %s, should be 'altiris'" % ret.vendor_class_id
            finally:
                try:
                    self.superuser.host_class_destroy('QZ1243A')
                except:
                    pass
        
        
class T0130_HostClassDestroy(AuthTests):
    """ Test host_class destroy """
    
    def do(self):
        try:
            self.superuser.host_class_destroy('QZ1243A')
        except:
            pass
        self.superuser.host_class_create('QZ1243A', 'altiris', "TestHostClass", {})
        try:
            with AssertAccessError(self):
                self.proxy.host_class_destroy('QZ1243A')
                with AssertRPCCError("LookupError::NoSuchHostClass", True):
                    self.superuser.host_class_fetch('QZ1243A', data_template)
        finally:
            try:
                self.superuser.host_class_destroy('QZ1243A')
            except:
                pass
            
        
class T0140_HostClassSetName(AuthTests):
    """ Test setting the name of a host_class"""
    
    def do(self):
        self.superuser.host_class_create('QZ1243A', 'altiris', "TestHostClass", {})
        with AssertAccessError(self):
            try:
                self.proxy.host_class_update('QZ1243A', {"host_class": 'ZQ1296'})
                nd = self.superuser.host_class_fetch('ZQ1296', data_template)
                assert nd.host_class == "ZQ1296", "Bad host_class host_class"
                assert nd.info == "TestHostClass", "Bad info"
                assert nd.vendor_class_id == "altiris", "Bad vendor_class_id %s, should be 'altiris'" % nd.vendor_class_id
            finally:
                try:
                    self.superuser.host_class_destroy('ZQ1296')
                except:
                    pass
                try:    
                    self.superuser.host_class_destroy('QZ1243A')
                except:
                    pass
        
                
                
class T0150_HostClassSetInfo(AuthTests):
    """ Test setting info on a host_class"""
    
    def do(self):
        self.superuser.host_class_create('QZ1243A', 'altiris', "TestHostClass", {})
        with AssertAccessError(self):
            try:
                self.proxy.host_class_update('QZ1243A', {"info": "ZQ1296 option"})
                nd = self.superuser.host_class_fetch('QZ1243A', data_template)
                assert nd.host_class == "QZ1243A", "Bad host_class host_class"
                assert nd.info == "ZQ1296 option", "Bad info"
                assert nd.vendor_class_id == "altiris", "Bad vendor_class_id %s, should be 'altiris'" % nd.vendor_class_id
            finally:
                try:
                    self.superuser.host_class_destroy('QZ1243A')
                except:
                    pass
                
                
class T0150_HostClassSetVendorClassID(AuthTests):
    """ Test setting vendor_class_id on a host_class"""
    
    def do(self):
        self.superuser.host_class_create('QZ1243A', 'altiris', "TestHostClass", {})
        with AssertAccessError(self):
            try:
                self.proxy.host_class_update('QZ1243A', {"vendor_class_id": "plain"})
                nd = self.superuser.host_class_fetch('QZ1243A', data_template)
                assert nd.host_class == "QZ1243A", "Bad host_class host_class"
                assert nd.info == "TestHostClass", "Bad info"
                assert nd.vendor_class_id == "plain", "Bad vendor_class_id %s, should be 'plain'" % nd.vendor_class_id
            finally:
                try:
                    self.superuser.host_class_destroy('QZ1243A')
                except:
                    pass

               
class T0160_HostClassSetOption(AuthTests):
    """ Test setting options on a host_class"""
    
    def do(self):
        try:
            self.superuser.host_class_destroy('QZ1243A')
        except:
            pass

        self.superuser.host_class_create('QZ1243A', 'altiris', "TestHostClass", {})
        
        with AssertAccessError(self):
            try:
                #optset = self.proxy.host_class_fetch("QZ1243A", {"optionset": True}).optionset
                #self.proxy.optionset_update(optset, {"subnet-mask": "255.255.255.0"})
                self.proxy.host_class_options_update('QZ1243A', {"subnet-mask": "255.255.255.0"})
                
                nd = self.superuser.host_class_fetch('QZ1243A', data_template)
                assert nd.host_class == "QZ1243A", "Bad host_class id"
                assert nd.info == "TestHostClass", "Bad info"
                assert nd.optionset_data["subnet-mask"] == "255.255.255.0", "Bad subnet-mask in options"
                
            finally:
                try:
                    self.superuser.host_class_destroy('QZ1243A')
                except:
                    pass
                
                
class T0170_HostClassUnsetOption(AuthTests):
    """ Test unsetting options on a host_class"""
    
    def do(self):
        self.superuser.host_class_create('QZ1243A', 'altiris', "TestHostClass", {})
        
        with AssertAccessError(self):
            try:
                self.proxy.host_class_options_update('QZ1243A', {"subnet-mask": "255.255.255.0"})
                self.proxy.host_class_options_update('QZ1243A', {"subnet-mask": None})
                nd = self.superuser.host_class_fetch("QZ1243A", data_template)
                assert nd.host_class == "QZ1243A", "Bad host_class id"
                assert nd.info == "TestHostClass", "Bad info"
                assert "subnet-mask" not in nd.optionset_data, "Subnet-mask still in options"
                
            finally:
                try:
                    self.superuser.host_class_destroy('QZ1243A')
                except:
                    pass
        
        
if __name__ == "__main__":
    sys.exit(main())
