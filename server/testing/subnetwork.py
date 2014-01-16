#!/usr/bin/env python
# -*- coding: utf8 -*-

""" ADHOC subnetwork API test suite"""
from framework import *
from util import *


class T1100_SubnetworkList(UnAuthTests):
    """ Test subnetwork listing """

    def do(self):
        with AssertAccessError(self):
            ret = self.proxy.subnetwork_dig({}, {"network": True, "info": True, "id": True, "changed_by": True, "mtime": True})
            
            assert len(ret) > 0, "Too few subnetworks returned"
            #for ds in ret:
                #print ds.id, ds.network, ds.info, ds.changed_by, ds.mtime
  
  
class T1110_SubnetworkFetch(UnAuthTests):
    """ Test subnetwork_fetch """
    
    def do(self):
        subnetworks = [x.id for x in self.superuser.subnetwork_dig({}, {"id":True})]
        
        n = 0
        for subnetwork in subnetworks:
            ret = self.proxy.subnetwork_fetch(subnetwork, {"network": True, "info": True, "id": True})
            assert "network" in ret, "Key network missing in returned struct from subnetwork_fetch"
            assert "info" in ret, "Key info missing in returned struct from subnetwork_fetch"
            assert "id" in ret, "Key id missing in returned struct from subnetwork_fetch"
            n += 1
            if n > 50:  # There are too many subnetworks to check, 50 is enough
                break
            
            
class T1120_SubnetworkCreate(AuthTests):
    """ Test subnetwork_create """
    
    def do(self):  
        try:
            self.superuser.network_destroy('network_test')
        except:
            pass
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        with AssertAccessError(self):
            try:
                self.proxy.subnetwork_create('192.5.55.0/24', 'network_test', "TestSubnetwork")
                template = {"id": True, 
                            "network": True,
                            "info": True,
                            "changed_by": True,
                            "mtime": True
                          }
                ret = self.superuser.subnetwork_fetch('192.5.55.0/24', template)
                
                self.assertindict(ret, template.keys(), exact=True)
                
                assert ret.id == "192.5.55.0/24", "Bad subnetwork id, is % should be %s" % (ret.id, "192.5.55.0/24")
                assert ret.network == "network_test", "network is " + ret.network + " but should be 'network_test'"
                assert ret.info == "TestSubnetwork", "Info is " + ret.info + "but should be 'TestSubnetwork'"
            finally:
                try:
                    self.proxy.subnetwork_destroy('192.5.55.0/24')
                except:
                    pass
                self.superuser.network_destroy('network_test')
        
        
class T1130_SubnetworkDestroy(AuthTests):
    """ Test subnetwork destroy """
    
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
        
        
class T1140_SubnetworkSetID(AuthTests):
    """ Test setting id of a subnetwork"""
    
    def do(self):
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.subnetwork_create('192.5.55.0/24', 'network_test', "TestSubnetwork")
        with AssertAccessError(self):
            try:
                self.proxy.subnetwork_update('192.5.55.0/24', {"id": '192.5.60.0/24'})
                nd = self.superuser.subnetwork_fetch('192.5.60.0/24', {"network": True, "info": True, "id": True})
                assert nd.id == "192.5.60.0/24", "Bad subnetwork id"
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
                
                
class T1150_SubnetworkSetInfo(AuthTests):
    """ Test setting info on a subnetwork"""
    
    def do(self):
        
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.subnetwork_create('192.5.55.0/24', 'network_test', "TestSubnetwork")
        with AssertAccessError(self):
            try:
                self.proxy.subnetwork_update('192.5.55.0/24', {"info": "ZQ1296 option"})
                nd = self.superuser.subnetwork_fetch('192.5.55.0/24', {"network": True, "info": True, "id": True})
                assert nd.id == "192.5.55.0/24", "Bad subnetwork id"
                assert nd.network == 'network_test', "Bad network"
                assert nd.info == "ZQ1296 option", "Bad info"
            finally:
                try:
                    self.superuser.subnetwork_destroy('192.5.55.0/24')
                except:
                    pass
                self.superuser.network_destroy('network_test')
                
                
class T1150_SubnetworkSetNetwork(AuthTests):
    """ Test setting network on a subnetwork"""
    
    def do(self):
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.network_create('network_othertest', False, "Testnätverk 3")
        self.superuser.subnetwork_create('192.5.55.0/24', 'network_test', "TestSubnetwork")
        with AssertAccessError(self):
            try:
                self.proxy.subnetwork_update('192.5.55.0/24', {"network": "network_othertest"})
                nd = self.superuser.subnetwork_fetch('192.5.55.0/24', {"network": True, "info": True, "id": True})
                assert nd.id == "192.5.55.0/24", "Bad subnetwork id"
                assert nd.network == 'network_othertest', "Bad network"
                assert nd.info == "TestSubnetwork", "Bad info"
            finally:
                try:
                    self.superuser.subnetwork_destroy('192.5.55.0/24')
                except:
                    pass
                self.superuser.network_destroy('network_test')
                self.superuser.network_destroy('network_othertest')
        

class T1160_SubnetworkSetOption(AuthTests):
    """ Test setting options on a subnetwork"""
    
    def do(self):
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.subnetwork_create('192.5.55.0/24', 'network_test', "TestSubnetwork")
        
        with AssertAccessError(self):
            try:
                self.proxy.subnetwork_option_set("192.5.55.0/24", "subnet-mask", "255.255.255.0")
                nd = self.superuser.subnetwork_fetch('192.5.55.0/24', {"network": True, "info": True, "id": True, "options": True})
                assert nd.id == "192.5.55.0/24", "Bad subnetwork id"
                assert nd.network == 'network_test', "Bad network"
                assert nd.info == "TestSubnetwork", "Bad info"
                assert nd.options["subnet-mask"] == "255.255.255.0", "Bad subnet-mask in options"
                
            finally:
                try:
                    self.superuser.subnetwork_destroy('192.5.55.0/24')
                except:
                    pass
                self.superuser.network_destroy('network_test')
                
                
class T1170_SubnetworkUnsetOption(AuthTests):
    """ Test unsetting options on a subnetwork"""
    
    def do(self):
        self.superuser.network_create('network_test', False, "Testnätverk 2")
        self.superuser.subnetwork_create('192.5.55.0/24', 'network_test', "TestSubnetwork")
        
        with AssertAccessError(self):
            try:
                self.superuser.subnetwork_option_set("192.5.55.0/24", "subnet-mask", "255.255.255.0")
                self.proxy.subnetwork_option_unset("192.5.55.0/24", "subnet-mask")
                nd = self.superuser.subnetwork_fetch('192.5.55.0/24', {"network": True, "info": True, "id": True, "options": True})
                assert nd.id == "192.5.55.0/24", "Bad subnetwork id"
                assert nd.network == 'network_test', "Bad network"
                assert nd.info == "TestSubnetwork", "Bad info"
                assert "subnet-info" not in nd.options, "Subnet-mask still in options"
                
            finally:
                try:
                    self.superuser.subnetwork_destroy('192.5.55.0/24')
                except:
                    pass
                self.superuser.network_destroy('network_test')

if __name__ == "__main__":
    sys.exit(main())
