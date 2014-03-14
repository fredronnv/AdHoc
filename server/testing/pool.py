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
                 "optionset_data": {"_": True, "_remove_nulls": True},
                 "allowed_hosts": True,
                 "allowed_groups": True,
                 "allowed_host_classes": True,
                 "literal_options": True
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
            
            
class T1220_PoolCreate(NetworkAdminTests):
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
        
        
class T1230_PoolDestroy(NetworkAdminTests):
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
            
        
class T1240_PoolSetName(SuperUserTests):
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
                
                
class T1250_PoolSetInfo(NetworkAdminTests):
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


class T1250_PoolSetNetwork(NetworkAdminTests):
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
  
  
class T1260_PoolSetOption(NetworkAdminTests):
    """ Test setting options on a pool"""
    
    def do(self):  
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        
        with AssertAccessError(self):
            try:
                self.proxy.pool_options_update('QZ1243A', {"subnet-mask": "255.255.255.0"})
                nd = self.superuser.pool_fetch('QZ1243A', data_template)
                assert nd.pool == "QZ1243A", "Bad pool id"
                assert nd.network == 'network_test', "Bad network"
                assert nd.info == "TestPool", "Bad info"
                assert nd.optionset_data["subnet-mask"] == "255.255.255.0", "Bad subnet-mask in optionset_data"
                
            finally:
                try:
                    self.superuser.pool_destroy('QZ1243A')
                except:
                    pass
                self.superuser.network_destroy('network_test')
                
                
class T1270_PoolUnsetOption(NetworkAdminTests):
    """ Test unsetting options on a pool"""
    
    def do(self):
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        
        with AssertAccessError(self):
            try:
                self.proxy.pool_options_update('QZ1243A', {"subnet-mask": "255.255.255.0"})
                self.proxy.pool_options_update('QZ1243A', {"subnet-mask": None})
                nd = self.superuser.pool_fetch('QZ1243A', data_template)
                assert nd.pool == "QZ1243A", "Bad pool id"
                assert nd.network == 'network_test', "Bad network"
                assert nd.info == "TestPool", "Bad info"
                assert "subnet-mask" not in nd.optionset_data, "Subnet-mask still in optionset_data"
                
            finally:
                try:
                    self.superuser.pool_destroy('QZ1243A')
                except:
                    pass
                self.superuser.network_destroy('network_test')
                
class T1280_PoolAllowHost(NetworkAdminTests):
    """ Test allowing two hosts into the pool"""
    
    
    def do(self):
        self.sufficient_privs=["admin_all_pools","write_all_pools"]
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        
        with AssertAccessError(self):
            try:
                pass
                self.proxy.pool_allow_host('QZ1243A', 'sol_ita_chalmers_se')
                self.proxy.pool_allow_host('QZ1243A', 'nile_its_chalmers_se')
                
                ret = self.proxy.pool_fetch('QZ1243A', data_template)
                assert len(ret.allowed_hosts)==2, "Wrong number of allowed hosts"
                assert "sol_ita_chalmers_se" in ret.allowed_hosts, "No sol_ita_chalmers_se in allowed hosts"
                assert "nile_its_chalmers_se" in ret.allowed_hosts, "No nile_its_chalmers_sein allowed hosts"
                
            finally:
                try:
                    self.superuser.pool_destroy('QZ1243A')
                except:
                    pass
                self.superuser.network_destroy('network_test')
                   
class T1281_PoolAllowGroup(NetworkAdminTests):
    """ Test allowing a group into the pool"""
    
    def do(self):
        self.sufficient_privs=["admin_all_pools","write_all_pools"]
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        
        with AssertAccessError(self):
            try:
                pass
                self.proxy.pool_allow_group('QZ1243A', 'altiris')
                
                ret = self.proxy.pool_fetch('QZ1243A', data_template)
                assert len(ret.allowed_groups)==1, "Wrong number of allowed groups"
                assert "altiris" in ret.allowed_groups, "No altiris in allowed groups"
                
            finally:
                try:
                    self.superuser.pool_destroy('QZ1243A')
                except:
                    pass
                self.superuser.network_destroy('network_test')
                
class T1282_PoolAllowHostClass(NetworkAdminTests):
    """ Test allowing a host_class into the pool"""
    
    def do(self):
        self.sufficient_privs=["admin_all_pools","write_all_pools"]
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        
        with AssertAccessError(self):
            try:
                pass
                self.proxy.pool_allow_host_class('QZ1243A', 'Pxe-IA64-PC-linux')
                
                ret = self.proxy.pool_fetch('QZ1243A', data_template)
                assert len(ret.allowed_host_classes)==1, "Wrong number of allowed host classes"
                assert "Pxe-IA64-PC-linux" in ret.allowed_host_classes, "No Pxe-IA64-PC-linux in allowed host classes"
                
            finally:
                try:
                    self.superuser.pool_destroy('QZ1243A')
                except:
                    pass
                self.superuser.network_destroy('network_test')

class T1283_PoolDisallowHost(NetworkAdminTests):
    """ Test disallowing two hosts from the pool"""
    
    def do(self):
        self.sufficient_privs=["admin_all_pools","write_all_pools"]
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        
        with AssertAccessError(self):
            try:
                pass
                self.superuser.pool_allow_host('QZ1243A', 'sol_ita_chalmers_se')
                self.superuser.pool_allow_host('QZ1243A', 'nile_its_chalmers_se')
                self.proxy.pool_disallow_host('QZ1243A', 'sol_ita_chalmers_se')
                self.proxy.pool_disallow_host('QZ1243A', 'nile_its_chalmers_se')
                
                ret = self.proxy.pool_fetch('QZ1243A', data_template)
                assert len(ret.allowed_hosts)==0, "Wrong number of allowed hosts"
                assert "sol_ita_chalmers_se" not in ret.allowed_hosts, "sol_ita_chalmers_se still in allowed hosts"
                assert "nile_its_chalmers_se" not in ret.allowed_hosts, "nile_its_chalmers_se still in allowed hosts"
                
            finally:
                try:
                    self.superuser.pool_destroy('QZ1243A')
                except:
                    pass
                self.superuser.network_destroy('network_test')
 
class T1284_PoolDisallowGroup(NetworkAdminTests):
    """ Test disallowing a group from the pool"""
    
    def do(self):
        self.sufficient_privs=["admin_all_pools","write_all_pools"]
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        
        with AssertAccessError(self):
            try:
                pass
                self.superuser.pool_allow_group('QZ1243A', 'altiris')
                self.proxy.pool_disallow_group('QZ1243A', 'altiris')
                
                ret = self.proxy.pool_fetch('QZ1243A', data_template)
                assert len(ret.allowed_groups)==0, "Wrong number of allowed groups"
                assert "altiris" not in ret.allowed_groups, "altiris still in allowed groups"
                
            finally:
                try:
                    self.superuser.pool_destroy('QZ1243A')
                except:
                    pass
                self.superuser.network_destroy('network_test')
                
class T1285_PoolDisallowHostClass(NetworkAdminTests):
    """ Test disallowing a host_class from the pool"""
    
    def do(self):
        self.sufficient_privs=["admin_all_pools","write_all_pools"]
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        
        with AssertAccessError(self):
            try:
                pass
                self.superuser.pool_allow_host_class('QZ1243A', 'Pxe-IA64-PC-linux')
                self.proxy.pool_disallow_host_class('QZ1243A', 'Pxe-IA64-PC-linux')
                
                ret = self.proxy.pool_fetch('QZ1243A', data_template)
                assert len(ret.allowed_host_classes)==0, "Wrong number of allowed host classes"
                assert "Pxe-IA64-PC-linux" not in ret.allowed_host_classes, "Pxe-IA64-PC-linux still in allowed host classes"
                
            finally:
                try:
                    self.superuser.pool_destroy('QZ1243A')
                except:
                    pass
                self.superuser.network_destroy('network_test')
                
class T1290_PoolAddLiteralOption(SuperUserTests):
    """ Test adding a literal option to a pool"""

    def do(self):
        try:
            self.superuser.network_create('network_test', False, "Testnätverk 2")
            self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        
            with AssertAccessError(self):
                try:
                    pass
                    literal_value = "#This is a literal option"
                    id = self.proxy.pool_literal_option_add('QZ1243A', literal_value)
                    print "Literal option ID=%d" % id
                    opts = self.proxy.pool_fetch('QZ1243A', data_template).literal_options
                    #print opts
                    assert id in [x.id for x in opts], "The returned id is not returned in when fetching the pool"
                    assert "#This is a literal option" in [x.value for x in opts], "The literal value is not returned in when fetching the pool"
                    
                    for opt in opts:
                        if opt.id == id:
                            assert opt.value == literal_value, "Returned literal option has the wrong value"
                finally:
                    try:
                        self.superuser.pool_destroy('QZ1243A')
                    except:
                        pass
                    self.superuser.network_destroy('network_test')
        finally:
                try:
                    self.superuser.pool_destroy('QZ1243A')
                except:
                    pass
                try:
                    self.superuser.network_destroy('network_test')
                except:
                    pass
                
class T1291_PoolDestroyLiteralOption(SuperUserTests):
    """ Test destroying a literal option from a pool"""

    def do(self):
        try:
            self.superuser.network_create('network_test', False, "Testnätverk 2")
            self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        
            with AssertAccessError(self):
                try:
                    pass
                    literal_value = "#This is a literal option"
                    id = self.superuser.pool_literal_option_add('QZ1243A', literal_value)
                    #print "Literal option ID=%d" % id
                    opts = self.superuser.pool_fetch('QZ1243A', data_template).literal_options
                    #print opts
                    assert id in [x.id for x in opts], "The returned id is not returned in when fetching the pool"
                    assert "#This is a literal option" in [x.value for x in opts], "The literal value is not returned in when fetching the pool"
                    
                    for opt in opts:
                        if opt.id == id:
                            assert opt.value == literal_value, "Returned literal option has the wrong value"
                    
                    self.proxy.pool_literal_option_destroy('QZ1243A', id)
                    opts = self.superuser.pool_fetch('QZ1243A', data_template).literal_options
                    assert id not in [x.id for x in opts], "The returned id is still returned in when fetching the pool"
                    assert "#This is a literal option" not in [x.value for x in opts], "The literal value is still returned in when fetching the pool"
                    
                   
                finally:
                    try:
                        self.superuser.pool_destroy('QZ1243A')
                    except:
                        pass
                    self.superuser.network_destroy('network_test')
        finally:
                try:
                    self.superuser.pool_destroy('QZ1243A')
                except:
                    pass
                try:
                    self.superuser.network_destroy('network_test')
                except:
                    pass
        
if __name__ == "__main__":
    sys.exit(main())
