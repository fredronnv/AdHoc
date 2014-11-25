#!/usr/bin/env python
# -*- coding: utf8 -*-

""" ADHOC subnetwork API test suite"""
from framework import *
from util import *


class T0200_SubnetworkList(UnAuthTests):
    """ Test subnetwork listing """

    def do(self):
        with AssertAccessError(self):
            ret = self.proxy.subnetwork_dig({}, {"network": True, "info": True, "subnetwork": True, "changed_by": True, "mtime": True})
            
            assert len(ret) > 0, "Too few subnetworks returned"
            #for ds in ret:
                #print ds.id, ds.network, ds.info, ds.changed_by, ds.mtime
  
  
class T0210_SubnetworkFetch(UnAuthTests):
    """ Test subnetwork_fetch """
    
    def do(self):
        subnetworks = [x.subnetwork for x in self.superuser.subnetwork_dig({}, {"subnetwork":True})]
        
        n = 0
        for subnetwork in subnetworks:
            ret = self.proxy.subnetwork_fetch(subnetwork, {"network": True, "info": True, "subnetwork": True})
            assert "network" in ret, "Key network missing in returned struct from subnetwork_fetch"
            assert "info" in ret, "Key info missing in returned struct from subnetwork_fetch"
            assert "subnetwork" in ret, "Key subnetwork missing in returned struct from subnetwork_fetch"
            n += 1
            if n > 50:  # There are too many subnetworks to check, 50 is enough
                break
            
            
class T0220_SubnetworkCreate(NetworkAdminTests):
    """ Test subnetwork_create """
    wip=True
    def do(self):  
        try:
            self.superuser.network_destroy('network_test')
        except:
            pass
        try:
            self.superuser.subnetwork_destroy('192.5.55.0/24')
        except rpcc_client.RPCCError, e:
            if e[0].name.startswith("LookupError"):
                pass
            else:
                raise
    
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        with AssertAccessError(self):
            try:
                self.proxy.subnetwork_create('192.5.55.0/24', 'network_test', "TestSubnetwork")
                template = {"subnetwork": True, 
                            "network": True,
                            "info": True,
                            "changed_by": True,
                            "mtime": True
                          }
                ret = self.superuser.subnetwork_fetch('192.5.55.0/24', template)
                
                self.assertindict(ret, template.keys(), exact=True)
                
                assert ret.subnetwork == "192.5.55.0/24", "Bad subnetwork, is % should be %s" % (ret.id, "192.5.55.0/24")
                assert ret.network == "network_test", "network is " + ret.network + " but should be 'network_test'"
                assert ret.info == "TestSubnetwork", "Info is " + ret.info + "but should be 'TestSubnetwork'"
            finally:
                try:
                    self.superuser.subnetwork_destroy('192.5.55.0/24')
                except:
                    pass
                self.superuser.network_destroy('network_test')
        
        
class T0230_SubnetworkDestroy(NetworkAdminTests):
    """ Test subnetwork destroy """
    wip=True
    def do(self):
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.subnetwork_create('192.5.55.0/24', 'network_test', "TestSubnetwork")
        try:
            with AssertAccessError(self):
                self.proxy.subnetwork_destroy('192.5.55.0/24')
                with AssertRPCCError("LookupError::NoSuchSubnetwork", True):
                    self.superuser.subnetwork_fetch('192.5.55.0/24', {"id": True})
        finally:
            try:
                self.superuser.subnetwork_destroy('192.5.55.0/24')
            except:
                pass
            try:
                self.superuser.network_destroy('network_test')
            except:
                pass
        
        
class T0240_SubnetworkSetID(NetworkAdminTests):
    """ Test setting id of a subnetwork"""
    
    def do(self):
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.subnetwork_create('192.5.55.0/24', 'network_test', "TestSubnetwork")
        with AssertAccessError(self):
            try:
                self.proxy.subnetwork_update('192.5.55.0/24', {"subnetwork": '192.5.60.0/24'})
                nd = self.superuser.subnetwork_fetch('192.5.60.0/24', {"network": True, "info": True, "subnetwork": True})
                assert nd.subnetwork == "192.5.60.0/24", "Bad subnetwork"
                assert nd.network == 'network_test', "Bad network"
                assert nd.info == "TestSubnetwork", "Bad info"
            finally:
                try:
                    self.superuser.subnetwork_destroy('192.5.55.0/24')
                except:
                    pass
                try:
                    self.superuser.subnetwork_destroy('192.5.60.0/24')
                except:
                    pass
                self.superuser.network_destroy('network_test')
                
                
class T0250_SubnetworkSetInfo(NetworkAdminTests):
    """ Test setting info on a subnetwork"""
    
    def do(self):
        
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.subnetwork_create('192.5.55.0/24', 'network_test', "TestSubnetwork")
        with AssertAccessError(self):
            try:
                self.proxy.subnetwork_update('192.5.55.0/24', {"info": "ZQ1296 option"})
                nd = self.superuser.subnetwork_fetch('192.5.55.0/24', {"network": True, "info": True, "subnetwork": True})
                assert nd.subnetwork == "192.5.55.0/24", "Bad subnetwork"
                assert nd.network == 'network_test', "Bad network"
                assert nd.info == "ZQ1296 option", "Bad info"
            finally:
                try:
                    self.superuser.subnetwork_destroy('192.5.55.0/24')
                except:
                    pass
                self.superuser.network_destroy('network_test')
                
                
class T0250_SubnetworkSetNetwork(NetworkAdminTests):
    """ Test setting network on a subnetwork"""
    
    def do(self):
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.network_create('network_othertest', False, "Testnätverk 3")
        self.superuser.subnetwork_create('192.5.55.0/24', 'network_test', "TestSubnetwork")
        with AssertAccessError(self):
            try:
                self.proxy.subnetwork_update('192.5.55.0/24', {"network": "network_othertest"})
                nd = self.superuser.subnetwork_fetch('192.5.55.0/24', {"network": True, "info": True, "subnetwork": True})
                assert nd.subnetwork == "192.5.55.0/24", "Bad subnetwork"
                assert nd.network == 'network_othertest', "Bad network"
                assert nd.info == "TestSubnetwork", "Bad info"
            finally:
                try:
                    self.superuser.subnetwork_destroy('192.5.55.0/24')
                except:
                    pass
                self.superuser.network_destroy('network_test')
                self.superuser.network_destroy('network_othertest')
        

class T0260_SubnetworkSetOption(NetworkAdminTests):
    """ Test setting options on a subnetwork"""
    
    def do(self):
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.subnetwork_create('192.5.55.0/24', 'network_test', "TestSubnetwork")
        
        with AssertAccessError(self):
            try:
                self.proxy.subnetwork_options_update('192.5.55.0/24', {"subnet-mask": "255.255.255.0"})
                nd = self.superuser.subnetwork_fetch('192.5.55.0/24', {"network": True, "info": True, 
                                                                       "subnetwork": True, 
                                                                       "optionset_data": {"_": True, "_remove_nulls": True}})
                assert nd.subnetwork == "192.5.55.0/24", "Bad subnetwork "
                assert nd.network == 'network_test', "Bad network"
                assert nd.info == "TestSubnetwork", "Bad info"
                assert nd.optionset_data["subnet-mask"] == "255.255.255.0", "Bad subnet-mask in options"
                
            finally:
                try:
                    self.superuser.subnetwork_destroy('192.5.55.0/24')
                except:
                    pass
                self.superuser.network_destroy('network_test')
                
                
class T0270_SubnetworkUnsetOption(NetworkAdminTests):
    """ Test unsetting options on a subnetwork"""
    
    def do(self):
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.subnetwork_create('192.5.55.0/24', 'network_test', "TestSubnetwork")
        
        with AssertAccessError(self):
            try:
                self.proxy.subnetwork_options_update('192.5.55.0/24', {"subnet-mask": "255.255.255.0"})
                self.proxy.subnetwork_options_update('192.5.55.0/24', {"subnet-mask": None})
                nd = self.superuser.subnetwork_fetch('192.5.55.0/24', {"network": True, "info": True, 
                                                                       "subnetwork": True, 
                                                                       "optionset_data": {"_": True, "_remove_nulls": True}})
                assert nd.subnetwork == "192.5.55.0/24", "Bad subnetwork"
                assert nd.network == 'network_test', "Bad network"
                assert nd.info == "TestSubnetwork", "Bad info"
                assert "subnet-mask" not in nd.optionset_data, "Subnet-mask still in options"
                
            finally:
                try:
                    self.superuser.subnetwork_destroy('192.5.55.0/24')
                except:
                    pass
                self.superuser.network_destroy('network_test')


class T0280_SubnetworkSearchCovering(UnAuthTests):
    """ Test searching a subnetwork that covers a certain IPv4 address"""
    
    def do(self):
        
        with AssertAccessError(self):
            res = self.proxy.subnetwork_dig({"subnetwork_covers": "129.16.107.72"}, {"subnetwork": True})
            assert len(res) == 1, "There should be exactly one answer"
            assert res[0].subnetwork == "129.16.107.64/26", "Wrong subnetwork matched 129.16.107.72"
            res2 = self.proxy.subnetwork_dig({"subnetwork_covers": "244.136.117.72"}, {"subnetwork": True})
            assert len(res2) == 0, "There should be exactly zero answers to 244.136.117.72"
            
if __name__ == "__main__":
    sys.exit(main())
