#!/usr/bin/env python
# -*- coding: utf8 -*-

""" ADHOC pool_range API test suite"""
from framework import *
from util import *

data_template = {"start_ip": True,
                 "end_ip": True,
                 "pool": True, 
                 "served_by": True,
                 "changed_by": True,
                 "mtime": True
                 }


class PoolRangeTests():
    testrange = "192.5.50.100"
    testrange_end = "192.5.50.150"
    testrange2 = "192.5.50.200"
    testrange2_end = "192.5.50.228"
    testpool = "testpool"
    testnetwork = "network_test"
    
    def setup_network(self):
        try:
            self.superuser.network_create(self.testnetwork, False, "Testnätverk 2")
        except:
            pass
        
    def teardown_network(self):
        try:
            self.superuser.network_destroy(self.testnetwork)
        except:
            pass
        
    def setup_pool(self, poolname="testpool"):  
        self.setup_network()
        # print "NETWORK READY"
        try:
            self.superuser.pool_create(poolname, self.testnetwork, "TestPool", {})
        except:
            pass
        
    def teardown_pool(self, poolname="testpool"):
        try:
            self.superuser.pool_destroy(poolname)
        except:
            pass
        self.teardown_network()
        
    def setup_dhcp_server(self):
        try:
            self.superuser.dhcp_server_create('Q', 'apa.bepa.chalmers.se', "TestDHCPServer")
        except:
            pass
        
    def teardown_dhcp_server(self):
        try:
            self.superuser.dhcp_server_destroy('Q')
        except:
            pass
        
    def setup_pool_range(self, start_ip=None, end_ip=None):
        
        if start_ip is None:
            start_ip = self.testrange
        if end_ip is None:
            end_ip = self.testrange_end
        # print "SETTING UP POOL RANGE ", start_ip, end_ip
        self.setup_dhcp_server()
        # print "DHCP SERVER READY"
        
        self.setup_pool()
        # print "POOL READY"
        self.superuser.pool_range_create(start_ip, end_ip, self.testpool, "Q")
        # print "POOL RANGE READY"

    def teardown_pool_range(self):
        
        try:
            self.superuser.pool_range_destroy(self.testrange)
        except:
            pass
        pass
    
        try:
            self.superuser.pool_range_destroy(self.testrange2)
        except:
            pass
        pass
    
        self.teardown_dhcp_server()
        self.teardown_pool()
        
    def assert_pool_data(self, ret, start_ip=None, end_ip=None, pool=None):
        
        if not start_ip:
            start_ip = self.testrange
            
        if not end_ip:
            end_ip = self.testrange_end
            
        if not pool:
            pool = self.testpool
        
        assert ret.start_ip == start_ip, "Bad start_ip, is % should be %s" % (ret.start_ip, start_ip)
        assert ret.end_ip == end_ip, "Bad end_ip, is % should be %s" % (ret.end_ip, end_ip)
        assert ret.pool == pool, "Bad pool %s, should be %s" % (ret.pool, pool)
        
    
class T1400_PoolRangeList(UnAuthTests, PoolRangeTests):
    """ Test pool_range listing """

    def dont(self):
        with AssertAccessError(self):
            ret = self.proxy.pool_range_dig({}, data_template)
            
            assert len(ret) > 0, "Too few pool_ranges returned"
#             for ds in ret:
#                 print ds.re, ds.pool_range, ds.info
  
  
class T1410_PoolRangeFetch(UnAuthTests, PoolRangeTests):
    """ Test pool_range_fetch """
    
    def do(self):
        pool_ranges = [x.start_ip for x in self.superuser.pool_range_dig({}, data_template)]
        
        n = 0
        for pool_range in pool_ranges:
            ret = self.proxy.pool_range_fetch(pool_range, data_template)
            self.assertindict(ret, data_template.keys(), exact=True)
            n += 1
            if n > 50:  # There are too many pool_ranges to check, 50 is enough
                break
            
            
class T1420_PoolRangeCreate(NetworkAdminTests, PoolRangeTests):
    """ Test pool_range_create """
    
    def do(self):  
        self.teardown_pool_range()
        self.setup_dhcp_server()
        self.setup_pool()
        try:
            with AssertAccessError(self):
                self.proxy.pool_range_create(self.testrange, self.testrange_end, self.testpool, "Q")
                ret = self.superuser.pool_range_fetch(self.testrange, data_template)
                self.assertindict(ret, data_template.keys(), exact=True)
                self.assert_pool_data(ret)
        finally:
            self.teardown_pool_range()
        
        
class T1430_PoolRangeDestroy(NetworkAdminTests, PoolRangeTests):
    """ Test pool_range destroy """
    
    def do(self):
        self.teardown_pool_range()
        self.setup_pool_range()
        
        try:
            with AssertAccessError(self):
                self.proxy.pool_range_destroy(self.testrange)
                with AssertRPCCError("LookupError::NoSuchPoolRange", True):
                    self.superuser.pool_range_fetch(self.testrange, data_template)
        finally:
            self.teardown_pool_range()
            
        
class T1440_PoolRangeSetRange(NetworkAdminTests, PoolRangeTests):
    """ Test setting the range of a pool_range"""

    def do(self):
        
        self.teardown_pool_range()
        self.setup_pool_range()
        
        try:
            with AssertAccessError(self):
                self.proxy.pool_range_update(self.testrange, {"start_ip": self.testrange2, "end_ip": self.testrange2_end})
                ret = self.superuser.pool_range_fetch(self.testrange2, data_template)
                self.assert_pool_data(ret, start_ip=self.testrange2, end_ip=self.testrange2_end)
        finally:
            try:
                self.superuser.pool_range_destroy(self.testrange)
            except:
                pass
            try:
                self.superuser.pool_range_destroy(self.testrange2)
            except:
                pass
            self.teardown_pool_range()
            
            
class T1441_PoolRangeSetReversedRange(NetworkAdminTests, PoolRangeTests):
    """ Test reversing the range of a pool_range"""

    def do(self):
        self.teardown_pool_range()
        self.setup_pool_range()
        try:
            with AssertAccessError(self):
                with AssertRPCCError("ValueError::PoolRangeReversed", True):
                    self.proxy.pool_range_update(self.testrange, {"start_ip": self.testrange2_end, "end_ip": self.testrange2})
                ret = self.superuser.pool_range_fetch(self.testrange, data_template)
                self.assert_pool_data(ret, start_ip=self.testrange, end_ip=self.testrange_end)
        finally:
            try:
                self.superuser.pool_range_destroy(self.testrange)
            except:
                pass
            try:
                self.superuser.pool_range_destroy(self.testrange2_end)
            except:
                pass
            self.teardown_pool_range()
            
            
class T1442_PoolRangeSetOverlappingRange(NetworkAdminTests, PoolRangeTests):
    """ Test setting the range of a pool_range, possibly overlapping"""
    
    wip = True
    
    def do(self):
        self.teardown_pool_range()
        self.setup_pool_range()  # 192.5.50.100 - 192.5.50.150
        self.setup_pool_range(start_ip=self.testrange2, end_ip=self.testrange2_end)   # 192.5.50.200 - 192.5.50.228
        try:
            with AssertAccessError(self):
                # New:192.5.50.150 - 192.5.50.228 Overlaps 192.5.50.100 - 192.5.50.150
                with AssertRPCCError("ValueError::PoolRangeOverlap", True):
                    self.proxy.pool_range_update(self.testrange2, {"start_ip": "192.5.50.150"}) 
                    
                # New: 192.5.50.100 - 192.5.50.228 Overlaps 192.5.50.200 - 192.5.50.228
                with AssertRPCCError("ValueError::PoolRangeOverlap", True):
                    self.proxy.pool_range_update(self.testrange, {"end_ip": self.testrange2})  
                    
                # New: 192.5.50.202 - 192.5.50.210 overlaps  192.5.50.200 - 192.5.50.228
                with AssertRPCCError("ValueError::PoolRangeOverlap", True):
                    self.proxy.pool_range_update(self.testrange, {"start_ip": "192.5.50.202", "end_ip": "192.5.50.210"})  
                    
                # New: 192.5.50.99 - 192.5.50.180 overlaps 192.5.50.100 - 192.5.50.150
                with AssertRPCCError("ValueError::PoolRangeOverlap", True):
                    self.proxy.pool_range_update(self.testrange2, {"start_ip": "192.5.50.99", "end_ip": "192.5.50.180"})  
                    
                # New: 192.5.50.110 - 192.5.50.115 overlaps 192.5.50.100 - 192.5.50.150
                with AssertRPCCError("ValueError::PoolRangeOverlap", True):
                    self.proxy.pool_range_update(self.testrange2, {"start_ip": "192.5.50.110", "end_ip": "192.5.50.115"})  
                
                # New 192.5.50.200 - 192.5.50.233, No overlap
                self.proxy.pool_range_update(self.testrange2, {"end_ip": "192.5.50.233"})
                
                # New 192.5.50.2151 - 192.5.50.233, No overlap  
                self.proxy.pool_range_update(self.testrange2, {"start_ip": "192.5.50.151"})
                
                # reset testrange2 no overlap
                self.proxy.pool_range_update("192.5.50.151", {"start_ip": self.testrange2})
                
                ret = self.superuser.pool_range_fetch(self.testrange, data_template)
                self.assert_pool_data(ret, start_ip=self.testrange, end_ip=self.testrange_end)
                
                ret = self.superuser.pool_range_fetch(self.testrange2, data_template)
                self.assert_pool_data(ret, start_ip=self.testrange2, end_ip=self.testrange2_end)
        finally:
            pass
            self.teardown_pool_range()


class T1450_PoolRangeSetPool(NetworkAdminTests, PoolRangeTests):
    """ Test setting pool on a pool_range"""
    
    def dont(self):
        otherpool = "ZQ1324B"
        self.setup()
        self.setup_pool(poolname=otherpool)
        try:
            with AssertAccessError(self):
                self.proxy.pool_range_update(self.testrange, {"pool": otherpool})
                ret = self.superuser.pool_range_fetch(self.testrange, data_template)
                self.assert_pool_data(ret, pool=otherpool)
        finally:
            self.teardown_pool(poolname=otherpool)
            self.teardown()               

        
if __name__ == "__main__":
    sys.exit(main())
