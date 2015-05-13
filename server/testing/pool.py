#!/usr/bin/env python
# -*- coding: utf8 -*-

""" ADHOC pool API test suite"""
from framework import *
from util import *

data_template = {"optionspace": True,
                 "network": True,
                 "info": True, 
                 "pool": True,
                 "changed_by": True,
                 "mtime": True,
                 "optionset_data": {"_": True, "_remove_nulls": True},
                 "granted_hosts": True,
                 "granted_groups": True,
                 "granted_host_classes": True,
                 "literal_options": True
                 }


class T1200_PoolList(UnAuthTests):
    """ Test pool listing """

    def do(self):
        with AssertAccessError(self):
            ret = self.proxy.pool_dig({}, data_template)
            
            assert len(ret) > 0, "Too few pools returned"
#             for ds in ret:
#                 print ds.re, ds.pool, ds.info
  
  
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
                self.proxy.pool_option_update('QZ1243A', {"subnet-mask": "255.255.255.0"})
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
                self.proxy.pool_option_update('QZ1243A', {"subnet-mask": "255.255.255.0"})
                self.proxy.pool_option_update('QZ1243A', {"subnet-mask": None})
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
                
                
class T1280_PoolGrantHost(NetworkAdminTests):
    """ Test granting two hosts into the pool"""
    
    def do(self):
        self.sufficient_privs = ["admin_all_pools", "write_all_pools"]
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        self.superuser.host_create_with_name('20111113-007A', '00:01:02:03:04:05', {})
        self.superuser.host_create_with_name('20111113-008A', '00:01:02:03:04:08', {})
        
        with AssertAccessError(self):
            try:
                pass
                self.proxy.pool_grant_host('QZ1243A', '20111113-007A')
                self.proxy.pool_grant_host('QZ1243A', '20111113-008A')
                
                ret = self.proxy.pool_fetch('QZ1243A', data_template)
                assert len(ret.granted_hosts) == 2, "Wrong number of granted hosts"
                assert "20111113-007A" in ret.granted_hosts, "No 20111113-007A in granted hosts"
                assert "20111113-008A" in ret.granted_hosts, "No 20111113-008A in granted hosts"
                
            finally:
                try:
                    self.superuser.pool_destroy('QZ1243A')
                except:
                    pass
                self.superuser.host_destroy('20111113-007A')
                self.superuser.host_destroy('20111113-008A')
                self.superuser.network_destroy('network_test')
                   

class T1281_PoolGrantGroup(NetworkAdminTests):
    """ Test granting a group into the pool"""
    
    def do(self):
        self.sufficient_privs = ["admin_all_pools", "write_all_pools"]
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        
        with AssertAccessError(self):
            try:
                pass
                self.proxy.pool_grant_group('QZ1243A', 'altiris')
                
                ret = self.proxy.pool_fetch('QZ1243A', data_template)
                assert len(ret.granted_groups) == 1, "Wrong number of granted groups"
                assert "altiris" in ret.granted_groups, "No altiris in granted groups"
                
            finally:
                try:
                    self.superuser.pool_destroy('QZ1243A')
                except:
                    pass
                self.superuser.network_destroy('network_test')
                
                
class T1282_PoolGrantHostClass(NetworkAdminTests):
    """ Test granting a host_class into the pool"""
    
    def do(self):
        self.sufficient_privs = ["admin_all_pools", "write_all_pools"]
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        
        with AssertAccessError(self):
            try:
                pass
                self.proxy.pool_grant_host_class('QZ1243A', 'Pxe-IA64-PC-linux')
                
                ret = self.proxy.pool_fetch('QZ1243A', data_template)
                assert len(ret.granted_host_classes) == 1, "Wrong number of granted host classes"
                assert "Pxe-IA64-PC-linux" in ret.granted_host_classes, "No Pxe-IA64-PC-linux in granted host classes"
                
            finally:
                try:
                    self.superuser.pool_destroy('QZ1243A')
                except:
                    pass
                self.superuser.network_destroy('network_test')


class T1283_PoolRevokeHost(NetworkAdminTests):
    """ Test revoking two hosts from the pool"""
    
    def do(self):
        self.sufficient_privs = ["admin_all_pools", "write_all_pools"]
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        self.superuser.host_create_with_name('20111113-007A', '00:01:02:03:04:05', {})
        self.superuser.host_create_with_name('20111113-008A', '00:01:02:03:04:08', {})
        
        with AssertAccessError(self):
            try:
                pass
                self.superuser.pool_grant_host('QZ1243A', '20111113-007A')
                self.superuser.pool_grant_host('QZ1243A', '20111113-008A')
                self.proxy.pool_revoke_host('QZ1243A', '20111113-007A')
                self.proxy.pool_revoke_host('QZ1243A', '20111113-008A')
                
                ret = self.proxy.pool_fetch('QZ1243A', data_template)
                assert len(ret.granted_hosts) == 0, "Wrong number of granted hosts"
                assert "20111113-007A " not in ret.granted_hosts, "20111113-007A still in granted hosts"
                assert "20111113-007A" not in ret.granted_hosts, "20111113-007A still in granted hosts"
                
            finally:
                try:
                    self.superuser.pool_destroy('QZ1243A')
                except:
                    pass
                self.superuser.host_destroy('20111113-007A')
                self.superuser.host_destroy('20111113-008A')
                self.superuser.network_destroy('network_test')
 
 
class T1284_PoolRevokeGroup(NetworkAdminTests):
    """ Test revoking a group from the pool"""
    
    def do(self):
        self.sufficient_privs = ["admin_all_pools", "write_all_pools"]
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        
        with AssertAccessError(self):
            try:
                pass
                self.superuser.pool_grant_group('QZ1243A', 'altiris')
                self.proxy.pool_revoke_group('QZ1243A', 'altiris')
                
                ret = self.proxy.pool_fetch('QZ1243A', data_template)
                assert len(ret.granted_groups) == 0, "Wrong number of granted groups"
                assert "altiris" not in ret.granted_groups, "altiris still in granted groups"
                
            finally:
                try:
                    self.superuser.pool_destroy('QZ1243A')
                except:
                    pass
                self.superuser.network_destroy('network_test')
                
                
class T1285_PoolRevokeHostClass(NetworkAdminTests):
    """ Test revoking a host_class from the pool"""
    
    def do(self):
        self.sufficient_privs = ["admin_all_pools", "write_all_pools"]
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        
        with AssertAccessError(self):
            try:
                pass
                self.superuser.pool_grant_host_class('QZ1243A', 'Pxe-IA64-PC-linux')
                self.proxy.pool_revoke_host_class('QZ1243A', 'Pxe-IA64-PC-linux')
                
                ret = self.proxy.pool_fetch('QZ1243A', data_template)
                assert len(ret.granted_host_classes) == 0, "Wrong number of granted host classes"
                assert "Pxe-IA64-PC-linux" not in ret.granted_host_classes, "Pxe-IA64-PC-linux still in granted host classes"
                
            finally:
                try:
                    self.superuser.pool_destroy('QZ1243A')
                except:
                    pass
                self.superuser.network_destroy('network_test')
            
                
class T1286_HostGrantCreate(NetworkAdminTests):
    """ Test creating a host grant using the host_grant model"""
    skip = True
    
    def do(self):
        self.sufficient_privs = ["admin_all_pools", "write_all_pools"]
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.pool_create('QZ1243A', 'network_test', "TestPool", {})
        self.superuser.host_create_with_name('20111113-007A', '00:01:02:03:04:05', {})
        self.superuser.host_create_with_name('20111113-008A', '00:01:02:03:04:08', {})
        
        with AssertAccessError(self):
            try:
                pass
                self.proxy.host_grant_create('QZ1243A', '20111113-007A')
                self.proxy.host_grant_create('QZ1243A', '20111113-008A')
                
                ret = self.proxy.pool_fetch('QZ1243A', data_template)
                assert len(ret.granted_hosts) == 2, "Wrong number of granted hosts"
                assert "20111113-007A" in ret.granted_hosts, "No 20111113-007A in granted hosts"
                assert "20111113-008A" in ret.granted_hosts, "No 20111113-008A in granted hosts"
                
            finally:
                try:
                    self.superuser.pool_destroy('QZ1243A')
                except:
                    pass
                self.superuser.host_destroy('20111113-007A')
                self.superuser.host_destroy('20111113-008A')
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
                    opt_id = self.proxy.pool_literal_option_add('QZ1243A', literal_value)
                    print "Literal option ID=%d" % opt_id
                    opts = self.proxy.pool_fetch('QZ1243A', data_template).literal_options
#                   print opts
                    assert opt_id in [x.id for x in opts], "The returned id is not returned in when fetching the pool"
                    assert "#This is a literal option" in [x.value for x in opts], "The literal value is not returned in when fetching the pool"
                    
                    for opt in opts:
                        if opt.id == opt_id:
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
                    opt_id = self.superuser.pool_literal_option_add('QZ1243A', literal_value)
                    # print "Literal option ID=%d" % opt_id
                    opts = self.superuser.pool_fetch('QZ1243A', data_template).literal_options
                    # print opts
                    assert opt_id in [x.id for x in opts], "The returned opt_id is not returned in when fetching the pool"
                    assert "#This is a literal option" in [x.value for x in opts], "The literal value is not returned in when fetching the pool"
                    
                    for opt in opts:
                        if opt.id == opt_id:
                            assert opt.value == literal_value, "Returned literal option has the wrong value"
                    
                    self.proxy.pool_literal_option_destroy('QZ1243A', opt_id)
                    opts = self.superuser.pool_fetch('QZ1243A', data_template).literal_options
                    assert opt_id not in [x.id for x in opts], "The returned opt_id is still returned in when fetching the pool"
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
