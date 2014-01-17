#!/usr/bin/env python
# -*- coding: utf8 -*-

""" ADHOC pool API test suite"""
from framework import *
from util import *

data_template = {
                 "optionspace": True,
                 "network": True,
                 "info": True, 
                 "pool": True,
                 "changed_by": True,
                 "mtime": True,
                 "options": True
                 }


class T1200_PoolList(UnAuthTests):
    """ Test pool listing """

    def do(self):
        with AssertAccessError(self):
            ret = self.proxy.pool_dig({}, data_template)
            
            assert len(ret) > 0, "Too few pools returned"
            #for ds in ret:
                #print ds.re, ds.pool, ds.info
  
  
class T1210_PoolFetch(UnAuthTests):
    """ Test pool_fetch """
    
    def do(self):
        pools = [x.pool for x in self.superuser.pool_dig({}, data_template)]
        
        n = 0
        for pool in pools:
            ret = self.proxy.pool_fetch(pool, data_template)
            self.assertindict(ret, data_template.keys(), exact=True)
            n += 1
            if n > 50:  # There are too many pools to check, 50 is enough
                break
            
            
class T1220_PoolCreate(AuthTests):
    """ Test pool_create """
    
    def do(self):  
        try:
            self.superuser.pool_destroy('QZ1243A')
        except:
            pass
        try:
            self.superuser.network_destroy('network_test')
        except:
            pass
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        
        try:
            with AssertAccessError(self):
                self.proxy.pool_create('QZ1243A', 'network_test', "TestPool", {})
                ret = self.superuser.pool_fetch('QZ1243A', data_template)
                self.assertindict(ret, data_template.keys(), exact=True)
                
                assert ret.pool == "QZ1243A", "Bad pool, is % should be %s" % (ret.pool, "QZ1243A")
                assert ret.info == "TestPool", "Info is " + ret.info + "but should be 'TestPool'"
                assert ret.network == "network_test", "Bad network %s, should be 'network_test'" % ret.network
        finally:
            try:
                self.superuser.pool_destroy('QZ1243A')
            except:
                pass
            self.superuser.network_destroy('network_test')
        
        
class T1230_PoolDestroy(AuthTests):
    """ Test pool destroy """
    
    def do(self):
        try:
            self.superuser.pool_destroy('QZ1243A')
        except:
            pass
        try:
            self.superuser.network_destroy('network_test')
        except:
            pass
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        try:
            with AssertAccessError(self):
                self.proxy.pool_destroy('QZ1243A')
                with AssertRPCCError("LookupError::NoSuchPool", True):
                    self.superuser.pool_fetch('QZ1243A', data_template)
        finally:
            try:
                self.superuser.pool_destroy('QZ1243A')
            except:
                pass
        self.superuser.network_destroy('network_test')
            
        
class T1240_PoolSetName(AuthTests):
    """ Test setting the name of a pool"""
    
    def do(self):
        try:
            self.superuser.network_destroy('network_test')
        except:
            pass
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        try:
            with AssertAccessError(self):
                self.proxy.pool_update('QZ1243A', {"pool": 'ZQ1296'})
                nd = self.superuser.pool_fetch('ZQ1296', data_template)
                assert nd.pool == "ZQ1296", "Bad pool"
                assert nd.info == "TestPool", "Bad info"
                assert nd.network == "network_test", "Bad network %s, should be 'network_test'" % nd.network
        finally:
            try:
                self.superuser.pool_destroy('ZQ1296')
            except:
                pass
            try:
                self.superuser.pool_destroy('QZ1243A')
            except:
                pass
        self.superuser.network_destroy('network_test')
                
                
class T1250_PoolSetInfo(AuthTests):
    """ Test setting info on a pool"""
    
    def do(self):
        try:
            self.superuser.network_destroy('network_test')
        except:
            pass
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        try:   
            with AssertAccessError(self):
                self.proxy.pool_update('QZ1243A', {"info": "ZQ1296 option"})
                nd = self.superuser.pool_fetch('QZ1243A', data_template)
                assert nd.pool == "QZ1243A", "Bad pool"
                assert nd.info == "ZQ1296 option", "Bad info"
                assert nd.network == "network_test", "Bad network %s, should be 'network_test'" % nd.network
        finally:
            try:
                self.superuser.pool_destroy('QZ1243A')
            except:
                pass
        self.superuser.network_destroy('network_test')


class T1250_PoolSetNetwork(AuthTests):
    """ Test setting network on a pool"""
    
    def do(self):
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.network_create('network_othertest', False, "Testnätverk 3")
        self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        try:
            with AssertAccessError(self):
                self.proxy.pool_update('QZ1243A', {"network": "network_othertest"})
                nd = self.superuser.pool_fetch('QZ1243A', data_template)
                assert nd.pool == "QZ1243A", "Bad pool"
                assert nd.info == "TestPool", "Bad info"
                assert nd.network == "network_othertest", "Bad network"
        finally:
            try:
                self.superuser.pool_destroy('QZ1243A')
            except:
                pass
            self.superuser.network_destroy('network_test')
            self.superuser.network_destroy('network_othertest')                
  
  
class T1260_PoolSetOption(AuthTests):
    """ Test setting options on a pool"""
    
    def do(self):  
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        
        with AssertAccessError(self):
            try:
                self.proxy.pool_option_set("QZ1243A", "subnet-mask", "255.255.255.0")
                nd = self.superuser.pool_fetch('QZ1243A', data_template)
                assert nd.pool == "QZ1243A", "Bad pool id"
                assert nd.network == 'network_test', "Bad network"
                assert nd.info == "TestPool", "Bad info"
                assert nd.options["subnet-mask"] == "255.255.255.0", "Bad subnet-mask in options"
                
            finally:
                try:
                    self.superuser.pool_destroy('QZ1243A')
                except:
                    pass
                self.superuser.network_destroy('network_test')
                
                
class T1270_PoolUnsetOption(AuthTests):
    """ Test unsetting options on a pool"""
    
    def do(self):
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        
        with AssertAccessError(self):
            try:
                self.superuser.pool_option_set("QZ1243A", "subnet-mask", "255.255.255.0")
                self.proxy.pool_option_unset("QZ1243A", "subnet-mask")
                nd = self.superuser.pool_fetch('QZ1243A', data_template)
                assert nd.pool == "QZ1243A", "Bad pool id"
                assert nd.network == 'network_test', "Bad network"
                assert nd.info == "TestPool", "Bad info"
                assert "subnet-info" not in nd.options, "Subnet-mask still in options"
                
            finally:
                try:
                    self.superuser.pool_destroy('QZ1243A')
                except:
                    pass
                self.superuser.network_destroy('network_test')
        
if __name__ == "__main__":
    sys.exit(main())
