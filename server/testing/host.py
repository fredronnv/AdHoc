#!/usr/bin/env python
# -*- coding: utf8 -*-

""" ADHOC host API test suite"""
from framework import *
from util import *

from datetime import date

data_template = {"optionspace": True,
                 "host": True,
                 "mac": True,
                 "dns": True,
                 "room": True,
                 'cid': True,
                 "status": True,
                 "info": True, 
                 "group": True,
                 "changed_by": True,
                 "mtime": True,
                 "optionset_data": {"_": True, "_remove_nulls": True},
                 "literal_options": True
                 }


class T1300_HostList(UnAuthTests):
    """ Test host listing """

    def dont(self):
        with AssertAccessError(self):
            ret = self.proxy.host_dig({}, data_template)
            
            assert len(ret) > 0, "Too few hosts returned"
            # for ds in ret:
            #     print ds.re, ds.host, ds.info
  
  
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
            
            
class T1315_HostCreate(FloorAdminTests):
    """ Test host_create """
   
    def do(self):
        
        today = date.today().strftime("%Y%m%d")
        try:
            for h in self.superuser.host_dig({"host_pattern": today + "-*"}, {"host": True}):
                self.superuser.host_destroy(h.host)
        except Exception as e:
            pass
        
        with AllowRPCCError("LookupError"): 
            self.superuser.host_destroy(today + "-001A")
        with AllowRPCCError("LookupError"): 
            self.superuser.host_destroy(today + "-001B")
        with AllowRPCCError("LookupError"): 
            self.superuser.host_destroy(today + "-002A")
        with AllowRPCCError("LookupError"): 
            self.superuser.host_destroy(today + "-002B")
        with AllowRPCCError("LookupError"): 
            self.superuser.host_destroy(today + "-001C")
        with AllowRPCCError("LookupError"): 
            self.superuser.host_destroy(today + "-001D")
        with AllowRPCCError("LookupError"): 
            self.superuser.host_destroy(today + "-001E")
        with AllowRPCCError("LookupError"): 
            self.superuser.host_destroy(today + "-001F")
        with AllowRPCCError("LookupError"): 
            self.superuser.host_destroy(today + "-001G")
        with AllowRPCCError("LookupError"): 
            self.superuser.host_destroy(today + "-001H")
            
        # Remove all hosts whose mac starts with 00:00:00:00.00 because the following test assumes
        # that there will be no connections to hosts sharing the mac address
        
        for host in self.superuser.host_dig({"mac_pattern": "00:00:00:00:00:*"}, {"host": True}):
            self.superuser.host_destroy(host.host)
            
        with AssertAccessError(self):
            try:
                hostid = self.proxy.host_create("00:00:00:00:00:01", {})
                assert hostid == today + "-001A", "Returned hostid=" + hostid
                hostid = self.proxy.host_create("00:00:00:00:00:01", {})
                assert hostid == today + "-001B", "Returned hostid=" + hostid
                hostid = self.proxy.host_create("00:00:00:00:00:02", {})
                assert hostid == today + "-002A", "Returned hostid=" + hostid
                hostid = self.proxy.host_create("00:00:00:00:00:01", {})
                assert hostid == today + "-001C", "Returned hostid=" + hostid
                hostid = self.proxy.host_create("00:00:00:00:00:19", {"same_as": today + "-002A"})
                assert hostid == today + "-002B", "Returned hostid=" + hostid
            finally:
                pass
        
                
class T1320_HostCreateWithName(FloorAdminTests):
    """ Test host_create_with_name """
    
    def do(self):
        
        with AllowRPCCError("LookupError"): 
            self.superuser.host_destroy('20111113-007A')
            
        with AssertAccessError(self):
            try:
                pre_hostcount = self.proxy.group_fetch('plain', {'hostcount': True}).hostcount
                self.proxy.host_create_with_name('20111113-007A', '00:01:02:03:04:05', {})
                ret = self.superuser.host_fetch('20111113-007A', data_template)
                self.assertindict(ret, data_template.keys(), exact=True)
                post_hostcount = self.proxy.group_fetch('plain', {'hostcount': True}).hostcount
                
                assert ret.host == "20111113-007A", "Bad host, is % should be %s" % (ret.host, "20111113-007A")
                assert ret.group == "plain", "Bad group %s, should be 'plain'" % ret.group
                assert ret.mac == '00:01:02:03:04:05', "Bad mac %s, should be '00:01:02:03:04:05'" % (ret.mac)
                assert pre_hostcount + 1 == post_hostcount, "Host count of group plain inaccurate. Was %d, id %d, but should be %d" % (pre_hostcount, post_hostcount, pre_hostcount + 1)
            finally:
                try:
                    self.superuser.host_destroy('20111113-007A')
                except:
                    pass
            try:
                self.superuser.group_destroy('20111113-007A')
            except:
                pass
            try:
                self.superuser.group_create('QZ1243A', 'altiris', "TestGroup", {})
                pre_hostcount_plain = self.proxy.group_fetch('plain', {'hostcount': True}).hostcount
                pre_hostcount_altiris = self.proxy.group_fetch('altiris', {'hostcount': True}).hostcount
                pre_hostcount_QZ1243A = self.proxy.group_fetch('QZ1243A', {'hostcount': True}).hostcount
                self.proxy.host_create_with_name('20111113-007A', '00:01:02:03:04:05', {'group': 'QZ1243A'})
                
                post_hostcount_plain = self.proxy.group_fetch('plain', {'hostcount': True}).hostcount
                post_hostcount_altiris = self.proxy.group_fetch('altiris', {'hostcount': True}).hostcount
                post_hostcount_QZ1243A = self.proxy.group_fetch('QZ1243A', {'hostcount': True}).hostcount
                
                assert pre_hostcount_plain + 1 == post_hostcount_plain, "Host count of group plain inaccurate. Was %d, id %d, but should be %d" % (pre_hostcount_plain, post_hostcount_plain, post_hostcount_plain + 1)
                assert pre_hostcount_altiris + 1 == post_hostcount_altiris, "Host count of group altiris inaccurate. Was %d, id %d, but shoucd be %d" % (pre_hostcount_altiris, post_hostcount_altiris, pre_hostcount_altiris + 1)
                assert pre_hostcount_QZ1243A + 1 == post_hostcount_QZ1243A, "Host count of group QZ1243A inaccurate. Was %d, id %d, but shoucd be %d" % (pre_hostcount_QZ1243A, post_hostcount_QZ1243A, pre_hostcount_QZ1243A + 1)
            
            finally:
                try:
                    self.superuser.host_destroy('20111113-007A')
                    self.superuser.group_destroy('QZ1243A')
                except:
                    pass
        
        
class T1330_HostDestroy(FloorAdminTests):
    """ Test host destroy """
    
    def do(self):
        self.superuser.host_create_with_name('20111113-007A', '00:01:02:03:04:05', {})
        try:
            with AssertAccessError(self):
                self.proxy.host_destroy('20111113-007A')
                with AssertRPCCError("LookupError::NoSuchHost", True):
                    self.superuser.host_fetch('20111113-007A', data_template)
        finally:
            try:
                self.superuser.host_destroy('20111113-007A')
            except:
                pass
            
        
class T1340_HostSetName(FloorAdminTests):
    """ Test setting name of a host"""
    
    def do(self):
        
        with AllowRPCCError("LookupError"): 
            self.superuser.host_destroy("20111111-009A")
        
        self.superuser.host_create_with_name('20111113-007A', '00:01:02:03:04:05', {})
        with AssertAccessError(self):
            try:
                self.proxy.host_update('20111113-007A', {"host": '20111111-009A'})
                nd = self.superuser.host_fetch('20111111-009A', data_template)
                assert nd.host == "20111111-009A", "Bad host"
                assert nd.mac == "00:01:02:03:04:05", "Bad mac"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
            finally:
                try:
                    self.superuser.host_destroy('20111113-007A')
                except:
                    pass
                try:
                    self.superuser.host_destroy('20111111-009A')
                except:
                    pass
                
                
class T1350_HostSetInfo(FloorAdminTests):
    """ Test setting info on a host"""
    
    def do(self):
        self.superuser.host_create_with_name('20111113-007A', '00:01:02:03:04:05', {})
        with AssertAccessError(self):
            try:
                self.proxy.host_update('20111113-007A', {"info": "ZQ1296 option"})
                nd = self.superuser.host_fetch('20111113-007A', data_template)
                assert nd.host == "20111113-007A", "Bad host"
                assert nd.info == "ZQ1296 option", "Bad info"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
            finally:
                try:
                    self.superuser.host_destroy('20111113-007A')
                except:
                    pass
                
                
class T1360_HostSetGroup(FloorAdminTests):
    """ Test setting group on a host"""
    
    def do(self):
        self.superuser.host_create_with_name('20111113-007A', '00:01:02:03:04:05', {})
        with AssertAccessError(self):
            try:
                self.proxy.host_update('20111113-007A', {"group": "altiris"})
                nd = self.superuser.host_fetch('20111113-007A', data_template)
                assert nd.host == "20111113-007A", "Bad host"
                assert nd.mac == "00:01:02:03:04:05", "Bad mac"
                assert nd.group == "altiris", "Bad group %s, should be 'altiris'" % nd.group
            finally:
                try:
                    self.superuser.host_destroy('20111113-007A')
                except:
                    pass


class T1370_HostSetMac(FloorAdminTests):
    """ Test setting mac on a host"""
    
    def do(self):
        self.superuser.host_create_with_name('20111113-007A', '00:01:02:03:04:05', {})
        with AssertAccessError(self):
            try:
                self.proxy.host_update('20111113-007A', {"mac": "05:04:03:c0:ff:ee"})
                nd = self.superuser.host_fetch('20111113-007A', data_template)
                assert nd.host == "20111113-007A", "Bad host"
                assert nd.mac == "05:04:03:c0:ff:ee", "Bad mac"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
            finally:
                try:
                    self.superuser.host_destroy('20111113-007A')
                except:
                    pass
                
                
class T1380_HostSetRoom(FloorAdminTests):
    """ Test setting room on a host"""
    
    def do(self):
        self.superuser.host_create_with_name('20111113-007A', '00:01:02:03:04:05', {})
        with AssertAccessError(self):
            try:
                roomtoset = "SV373"
                self.proxy.host_update('20111113-007A', {"room": roomtoset})
                nd = self.superuser.host_fetch('20111113-007A', data_template)
                assert nd.host == "20111113-007A", "Bad host"
                assert nd.mac == "00:01:02:03:04:05", "Bad mac"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
                assert nd.room == roomtoset, "Bad room %s, should be '%s'" % (nd.room, roomtoset)
            finally:
                try:
                    self.superuser.host_destroy('20111113-007A')
                except:
                    pass
                
                
class T1385_HostSetCid(FloorAdminTests):
    """ Test setting cid on a host"""

    def do(self):
        self.superuser.host_create_with_name('20111113-007A', '00:01:02:03:04:05', {})
        with AssertAccessError(self):
            try:
                cidtoset = "srvadhoc"
                self.proxy.host_update('20111113-007A', {"cid": cidtoset})
                nd = self.superuser.host_fetch('20111113-007A', data_template)
                assert nd.host == "20111113-007A", "Bad host"
                assert nd.mac == "00:01:02:03:04:05", "Bad mac"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
                assert nd.cid == cidtoset, "Bad cid %s, should be '%s'" % (nd.room, cidtoset)
            finally:
                try:
                    self.superuser.host_destroy('20111113-007A')
                except:
                    pass
 
                
class T1386_HostSetBadCid(UnAuthTests):
    """ Test setting a bad cid on a host"""
    
    def do(self):
        self.superuser.host_create_with_name('20111113-007A', '00:01:02:03:04:05', {})
        with AssertAccessError(self):
            with AssertRPCCError("LookupError::NoSuchAccount"):
                self.proxy.host_update('20111113-007A', {"cid": "hlduwnd5"})

        try:
            self.superuser.host_destroy('20111113-007A')
        except:
            pass                
                
                
class T1390_HostSetBadRoom(UnAuthTests):
    """ Test setting a bad room on a host"""
    
    def do(self):
        self.superuser.host_create_with_name('20111113-007A', '00:01:02:03:04:05', {})
        with AssertAccessError(self):
            with AssertRPCCError("LookupError::NoMatchingBuilding"):
                self.proxy.host_update('20111113-007A', {"room": "QSY372"})

        try:
            self.superuser.host_destroy('20111113-007A')
        except:
            pass
        
        
class T1391_HostSetDNS(FloorAdminTests):
    """ Test setting DNS name on a host"""
    
    def do(self):
        self.superuser.host_create_with_name('20111113-007A', '00:01:02:03:04:05', {})
        with AssertAccessError(self):
            try:
                dnstoset = "www.chalmers.se"
                self.proxy.host_update('20111113-007A', {"dns": dnstoset})
                nd = self.superuser.host_fetch('20111113-007A', data_template)
                assert nd.host == "20111113-007A", "Bad host"
                assert nd.mac == "00:01:02:03:04:05", "Bad mac"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
                assert nd.dns == dnstoset, "Bad dns %s, should be '%s'" % (nd.dns, dnstoset)
            finally:
                try:
                    self.superuser.host_destroy('20111113-007A')
                except:
                    pass
                
                
class T1392_HostSetBadDNS(UnAuthTests):
    """ Test setting a bad DNS name on a host"""
    
    def do(self):
        self.superuser.host_create_with_name('20111113-007A', '00:01:02:03:04:05', {})
        with AssertAccessError(self):
            with AssertRPCCError("LookupError::NoSuchDNSName"):
                self.proxy.host_update('20111113-007A', {"dns": "QSY372.se"})

        try:
            self.superuser.host_destroy('20111113-007A')
        except:
            pass              


class T1393_HostSetStatus(FloorAdminTests):
    """ Test setting status on a host"""

    def do(self):
        pre_hostcount = self.superuser.group_fetch('plain', {'hostcount': True}).hostcount
        self.superuser.host_create_with_name('20111113-007A', '00:01:02:03:04:05', {})
        post_hostcount = self.superuser.group_fetch('plain', {'hostcount': True}).hostcount
        assert post_hostcount == pre_hostcount + 1, "Host count did not increment"
        pre_hostcount = post_hostcount
        with AssertAccessError(self):
            try:
                toset = "Inactive"
                self.proxy.host_update('20111113-007A', {"status": toset})
                nd = self.superuser.host_fetch('20111113-007A', data_template)
                assert nd.host == "20111113-007A", "Bad host"
                assert nd.mac == "00:01:02:03:04:05", "Bad mac"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
                assert nd.status == toset, "Bad status %s, should be '%s'" % (nd.status, toset)
                post_hostcount = self.superuser.group_fetch('plain', {'hostcount': True}).hostcount
                assert post_hostcount == pre_hostcount - 1, "Host count did not decrement"
                pre_hostcount = post_hostcount
                
                toset = "Active"
                self.proxy.host_update('20111113-007A', {"status": toset})
                nd = self.superuser.host_fetch('20111113-007A', data_template)
                assert nd.host == "20111113-007A", "Bad host"
                assert nd.mac == "00:01:02:03:04:05", "Bad mac"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
                assert nd.status == toset, "Bad status %s, should be '%s'" % (nd.status, toset)
                post_hostcount = self.superuser.group_fetch('plain', {'hostcount': True}).hostcount
                assert post_hostcount == pre_hostcount + 1, "Host count did not increment"
                pre_hostcount = post_hostcount
                
                toset = "Dead"
                self.proxy.host_update('20111113-007A', {"status": toset})
                nd = self.superuser.host_fetch('20111113-007A', data_template)
                assert nd.host == "20111113-007A", "Bad host"
                assert nd.mac == "00:01:02:03:04:05", "Bad mac"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
                assert nd.status == toset, "Bad status %s, should be '%s'" % (nd.status, toset)
                post_hostcount = self.superuser.group_fetch('plain', {'hostcount': True}).hostcount
                assert post_hostcount == pre_hostcount - 1, "Host count did not decrement"
                pre_hostcount = post_hostcount
            finally:
                try:
                    self.superuser.host_destroy('20111113-007A')
                except:
                    pass
                
                
class T1394_HostSetOption(FloorAdminTests):
    """ Test setting options on a host"""
    
    def do(self):
        try:
            self.superuser.host_destroy('20111113-007A')
        except:
            pass

        self.superuser.host_create_with_name('20111113-007A', '00:01:02:03:04:05', {})
        
        with AssertAccessError(self):
            try:
                self.proxy.host_option_update("20111113-007A", {"subnet-mask": "255.255.255.0"})
                nd = self.superuser.host_fetch('20111113-007A', data_template)
                assert nd.host == "20111113-007A", "Bad host"
                assert nd.mac == "00:01:02:03:04:05", "Bad mac"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
                assert nd.optionset_data["subnet-mask"] == "255.255.255.0", "Bad subnet-mask in options"
                
            finally:
                try:
                    self.superuser.host_destroy('20111113-007A')
                except:
                    pass
                
                
class T1395_HostUnsetOption(FloorAdminTests):
    """ Test unsetting options on a host"""
    
    def do(self):
        self.superuser.host_create_with_name('20111113-007A', '00:01:02:03:04:05', {})
        
        with AssertAccessError(self):
            try:
                self.proxy.host_option_update("20111113-007A", {"subnet-mask": "255.255.255.0"})
                self.proxy.host_option_update("20111113-007A", {"subnet-mask": None})
                nd = self.superuser.host_fetch("20111113-007A", data_template)
                assert nd.host == "20111113-007A", "Bad host"
                assert nd.mac == "00:01:02:03:04:05", "Bad mac"
                assert nd.group == "plain", "Bad group %s, should be 'plain'" % nd.group
                assert "subnet-mask" not in nd.optionset_data, "Subnet-mask still in optionset_data"
                
            finally:
                try:
                    self.superuser.host_destroy('20111113-007A')
                except:
                    pass
              
              
class T1396_HostAddLiteralOption(SuperUserTests):
    """ Test adding a literal option to a host"""

    def do(self):
        try:
            self.superuser.host_create_with_name('20111113-007A', '00:01:02:03:04:05', {})
        
            with AssertAccessError(self):
                try:
                    pass
                    literal_value = "#This is a literal option"
                    id = self.proxy.host_literal_option_add('20111113-007A', literal_value)
                    print "Literal option ID=%d" % id
                    opts = self.proxy.host_fetch('20111113-007A', data_template).literal_options
                    # print opts
                    assert id in [x.id for x in opts], "The returned id is not returned in when fetching the host"
                    assert "#This is a literal option" in [x.value for x in opts], "The literal value is not returned in when fetching the host"
                    
                    for opt in opts:
                        if opt.id == id:
                            assert opt.value == literal_value, "Returned literal option has the wrong value"
                finally:
                    try:
                        self.superuser.host_destroy('20111113-007A')
                    except:
                        pass
        finally:
                try:
                    self.superuser.host_destroy('20111113-007A')
                except:
                    pass
                
                
class T1397_HostDestroyLiteralOption(SuperUserTests):
    """ Test destroying a literal option from a host"""
    def do(self):
        try:
            self.superuser.host_create_with_name('20111113-007A', '00:01:02:03:04:05', {})
        
            with AssertAccessError(self):
                try:
                    pass
                    literal_value = "#This is a literal option"
                    id = self.superuser.host_literal_option_add('20111113-007A', literal_value)
                    # print "Literal option ID=%d" % id
                    opts = self.superuser.host_fetch('20111113-007A', data_template).literal_options
                    # print opts
                    assert id in [x.id for x in opts], "The returned id is not returned in when fetching the host"
                    assert "#This is a literal option" in [x.value for x in opts], "The literal value is not returned in when fetching the host"
                    
                    for opt in opts:
                        if opt.id == id:
                            assert opt.value == literal_value, "Returned literal option has the wrong value"
                    
                    self.proxy.host_literal_option_destroy('20111113-007A', id)
                    opts = self.superuser.host_fetch('20111113-007A', data_template).literal_options
                    assert id not in [x.id for x in opts], "The returned id is still returned in when fetching the host"
                    assert "#This is a literal option" not in [x.value for x in opts], "The literal value is still returned in when fetching the host"
                    
                finally:
                    try:
                        self.superuser.host_destroy('20111113-007A')
                    except:
                        pass
        finally:
                try:
                    self.superuser.host_destroy('20111113-007A')
                except:
                    pass
                       
if __name__ == "__main__":
    sys.exit(main())
