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
                 "mtime": True,
                 "options": True
                 }


class T1300_HostList(UnAuthTests):
    """ Test host listing """

    def dont(self):
        with AssertAccessError(self):
            ret = self.proxy.host_dig({}, data_template)
            
            assert len(ret) > 0, "Too few hosts returned"
            #for ds in ret:
                #print ds.re, ds.host, ds.info
  
  
class T1310_HostFetch(UnAuthTests):
    """ Test host_fetch """
    
    def dont(self):
        hosts = [x.host for x in self.superuser.host_dig({}, data_template)]
        
        n = 0
        for host in hosts:
            ret = self.proxy.host_fetch(host, data_template)
            self.assertindict(ret, data_template.keys(), exact=True)
            n += 1
            if n > 50:  # There are too many hosts to check, 50 is enough
                break
            
            
class T1320_HostCreate(AuthTests):
    """ Test host_create """
    
    def do(self):
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
                assert ret.group == "plain", "Bad group %s, should be 'plain'" % ret.group
                assert ret.mac == '00:01:02:03:04:05', "BAd mac %s, should be '00:01:02:03:04:05'"%(ret.mac)
            finally:
                try:
                    self.superuser.host_destroy('QZ1243A')
                except:
                    pass
        
        
class T1330_HostDestroy(AuthTests):
    """ Test host destroy """
    
    def do(self):
        self.superuser.host_create('QZ1243A', '00:01:02:03:04:05', {})
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
            
        
class T1340_HostSetName(AuthTests):
    """ Test setting name of a host"""
    
    def do(self):
        self.superuser.host_create('QZ1243A', '00:01:02:03:04:05', {})
        with AssertAccessError(self):
            try:
                self.proxy.host_update('QZ1243A', {"host": 'ZQ1296'})
                nd = self.superuser.host_fetch('ZQ1296', data_template)
                assert nd.host == "ZQ1296", "Bad host"
                assert nd.mac == "00:01:02:03:04:05", "Bad mac"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
            finally:
                try:
                    self.superuser.host_destroy('QZ1243A')
                except:
                    pass
                try:
                    self.superuser.host_destroy('ZQ1296')
                except:
                    pass
                
                
class T1350_HostSetInfo(AuthTests):
    """ Test setting info on a host"""
    
    def do(self):
        self.superuser.host_create('QZ1243A', '00:01:02:03:04:05', {})
        with AssertAccessError(self):
            try:
                self.proxy.host_update('QZ1243A', {"info": "ZQ1296 option"})
                nd = self.superuser.host_fetch('QZ1243A', data_template)
                assert nd.host == "QZ1243A", "Bad host"
                assert nd.info == "ZQ1296 option", "Bad info"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
            finally:
                try:
                    self.superuser.host_destroy('QZ1243A')
                except:
                    pass
                
                
class T1360_HostSetGroup(AuthTests):
    """ Test setting group on a host"""
    
    def do(self):
        self.superuser.host_create('QZ1243A', '00:01:02:03:04:05', {})
        with AssertAccessError(self):
            try:
                self.proxy.host_update('QZ1243A', {"group": "altiris"})
                nd = self.superuser.host_fetch('QZ1243A', data_template)
                assert nd.host == "QZ1243A", "Bad host"
                assert nd.mac == "00:01:02:03:04:05", "Bad mac"
                assert nd.group == "altiris", "Bad group %s, should be 'altiris'" % nd.group
            finally:
                try:
                    self.superuser.host_destroy('QZ1243A')
                except:
                    pass


class T1370_HostSetMac(AuthTests):
    """ Test setting mac on a host"""
    
    def do(self):
        self.superuser.host_create('QZ1243A', '00:01:02:03:04:05', {})
        with AssertAccessError(self):
            try:
                self.proxy.host_update('QZ1243A', {"mac": "05:04:03:c0:ff:ee"})
                nd = self.superuser.host_fetch('QZ1243A', data_template)
                assert nd.host == "QZ1243A", "Bad host"
                assert nd.mac == "05:04:03:c0:ff:ee", "Bad mac"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
            finally:
                try:
                    self.superuser.host_destroy('QZ1243A')
                except:
                    pass
                
                
class T1380_HostSetRoom(AuthTests):
    """ Test setting room on a host"""
    
    def do(self):
        self.superuser.host_create('QZ1243A', '00:01:02:03:04:05', {})
        with AssertAccessError(self):
            try:
                roomtoset = "SV373"
                self.proxy.host_update('QZ1243A', {"room": roomtoset})
                nd = self.superuser.host_fetch('QZ1243A', data_template)
                assert nd.host == "QZ1243A", "Bad host"
                assert nd.mac == "00:01:02:03:04:05", "Bad mac"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
                assert nd.room == roomtoset, "Bad room %s, should be '%s'" % (nd.room, roomtoset)
            finally:
                try:
                    self.superuser.host_destroy('QZ1243A')
                except:
                    pass
                
                
class T1390_HostSetBadRoom(UnAuthTests):
    """ Test setting a bad room on a host"""
    
    def do(self):
        self.superuser.host_create('QZ1243A', '00:01:02:03:04:05', {})
        with AssertAccessError(self):
            with AssertRPCCError("LookupError::NoMatchingBuilding"):
                self.proxy.host_update('QZ1243A', {"room": "QSY372"})

        try:
            self.superuser.host_destroy('QZ1243A')
        except:
            pass
        
        
class T1391_HostSetDNS(AuthTests):
    """ Test setting DNS name on a host"""
    
    def do(self):
        self.superuser.host_create('QZ1243A', '00:01:02:03:04:05', {})
        with AssertAccessError(self):
            try:
                dnstoset = "www.chalmers.se"
                self.proxy.host_update('QZ1243A', {"dns": dnstoset})
                nd = self.superuser.host_fetch('QZ1243A', data_template)
                assert nd.host == "QZ1243A", "Bad host"
                assert nd.mac == "00:01:02:03:04:05", "Bad mac"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
                assert nd.dns == dnstoset, "Bad dns %s, should be '%s'" % (nd.dns, dnstoset)
            finally:
                try:
                    self.superuser.host_destroy('QZ1243A')
                except:
                    pass
                
                
class T1392_HostSetBadDNS(UnAuthTests):
    """ Test setting a bad DNS name on a host"""
    
    def do(self):
        self.superuser.host_create('QZ1243A', '00:01:02:03:04:05', {})
        with AssertAccessError(self):
            with AssertRPCCError("LookupError::NoSuchDNSName"):
                self.proxy.host_update('QZ1243A', {"dns": "QSY372.se"})

        try:
            self.superuser.host_destroy('QZ1243A')
        except:
            pass              


class T1393_HostSetStatus(AuthTests):
    """ Test setting status on a host"""
    
    def do(self):
        self.superuser.host_create('QZ1243A', '00:01:02:03:04:05', {})
        with AssertAccessError(self):
            try:
                toset = "Inactive"
                self.proxy.host_update('QZ1243A', {"status": toset})
                nd = self.superuser.host_fetch('QZ1243A', data_template)
                assert nd.host == "QZ1243A", "Bad host"
                assert nd.mac == "00:01:02:03:04:05", "Bad mac"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
                assert nd.status == toset, "Bad status %s, should be '%s'" % (nd.status, toset)
                
                toset = "Active"
                self.proxy.host_update('QZ1243A', {"status": toset})
                nd = self.superuser.host_fetch('QZ1243A', data_template)
                assert nd.host == "QZ1243A", "Bad host"
                assert nd.mac == "00:01:02:03:04:05", "Bad mac"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
                assert nd.status == toset, "Bad status %s, should be '%s'" % (nd.status, toset)
                
                toset = "Dead"
                self.proxy.host_update('QZ1243A', {"status": toset})
                nd = self.superuser.host_fetch('QZ1243A', data_template)
                assert nd.host == "QZ1243A", "Bad host"
                assert nd.mac == "00:01:02:03:04:05", "Bad mac"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
                assert nd.status == toset, "Bad status %s, should be '%s'" % (nd.status, toset)
            finally:
                try:
                    self.superuser.host_destroy('QZ1243A')
                except:
                    pass
                
                
class T1394_HostSetOption(AuthTests):
    """ Test setting options on a host"""
    
    def do(self):
        try:
            self.superuser.host_destroy('QZ1243A')
        except:
            pass

        self.superuser.host_create('QZ1243A', '00:01:02:03:04:05', {})
        
        with AssertAccessError(self):
            try:
                self.proxy.host_option_set("QZ1243A", "subnet-mask", "255.255.255.0")
                nd = self.superuser.host_fetch('QZ1243A', data_template)
                assert nd.host == "QZ1243A", "Bad host"
                assert nd.mac == "00:01:02:03:04:05", "Bad mac"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
                assert nd.options["subnet-mask"] == "255.255.255.0", "Bad subnet-mask in options"
                
            finally:
                try:
                    self.superuser.host_destroy('QZ1243A')
                except:
                    pass
                
                
class T1395_HostUnsetOption(AuthTests):
    """ Test unsetting options on a host"""
    
    def do(self):
        self.superuser.host_create('QZ1243A', '00:01:02:03:04:05', {})
        
        with AssertAccessError(self):
            try:
                self.proxy.host_option_set("QZ1243A", "subnet-mask", "255.255.255.0")
                self.proxy.host_option_unset("QZ1243A", "subnet-mask")
                nd = self.superuser.host_fetch("QZ1243A", data_template)
                assert nd.host == "QZ1243A", "Bad host"
                assert nd.mac == "00:01:02:03:04:05", "Bad mac"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
                assert "subnet-mask" not in nd.options, "Subnet-mask still in options"
                
            finally:
                try:
                    self.superuser.host_destroy('QZ1243A')
                except:
                    pass
                
if __name__ == "__main__":
    sys.exit(main())