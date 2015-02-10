#!/usr/bin/env python
# -*- coding: utf8 -*-

""" ADHOC building API test suite"""
from framework import *
from util import *


class T0800_BuildingList(UnAuthTests):
    """ Test building listing """

    def do(self):
        with AssertAccessError(self):
            ret = self.proxy.building_dig({}, {"re": True, "info": True, "building": True})
            
            assert len(ret) > 0, "Too few buildings returned"
            # for ds in ret:
            #    print ds.re, ds.building, ds.info
  
  
class T0810_BuildingFetch(UnAuthTests):
    """ Test building_fetch """
    
    def do(self):
        buildings = [x.building for x in self.superuser.building_dig({}, {"building": True})]
        
        n = 0
        for building in buildings:
            ret = self.proxy.building_fetch(building, {"re": True, "info": True, "building": True})
            assert "re" in ret, "Key re missing in returned struct from building_fetch"
            assert "info" in ret, "Key info missing in returned struct from building_fetch"
            assert "building" in ret, "Key building missing in returned struct from building_fetch"
            n += 1
            if n > 50:  # There are too many buildings to check, 50 is enough
                break
            
            
class T0820_BuildingCreate(ServiceDeskTests):
    """ Test building_create """
    
    def do(self):  
        try:
            self.superuser.building_destroy("QZ1243A")
        except:
            pass
        try:
            with AssertAccessError(self): 
                preevents = self.superuser.event_dig({"type": "create", "building": "QZ1243A"}, {"building": True, "re": True, "info": True, "type": True, "event": True})
                self.proxy.building_create('QZ1243A', 'a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3', "TestBuilding")
                ret = self.superuser.building_fetch('QZ1243A', {"re": True, "info": True, "building": True})
                assert "re" in ret, "Key re missing in returned struct from building_fetch"
                assert "info" in ret, "Key info missing in returned struct from building_fetch"
                assert "building" in ret, "Key building missing in returned struct from building_fetch" 
                assert ret.building == "QZ1243A", "Bad building, is % should be %s" % (ret.building, "QZ1243A")
                assert ret.re == "a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3", "Re is " + ret.re + " but should be 'a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3'"
                assert ret.info == "TestBuilding", "Info is " + ret.info + "but should be 'TestBuilding'"
        
                events = self.superuser.event_dig({"type": "create", "building": "QZ1243A"}, {"building": True, "re": True, "info": True, "type": True, "event": True})
                # print events
                assert len(events) > len(preevents), "No relevent events generated"
        
        finally:
            try:
                self.superuser.building_destroy("QZ1243A")
            except:
                pass
        
        
class T0830_BuildingDestroy(ServiceDeskTests):
    """ Test building destroy """
    
    def do(self):
        self.superuser.building_create('QZ1243A', '.*', "No info")
        try:
            with AssertAccessError(self):
                self.proxy.building_destroy('QZ1243A')
                with AssertRPCCError("LookupError::NoSuchBuilding", True):
                    self.superuser.building_fetch('QZ1243A', {"building": True})
        finally:
            try:
                self.superuser.building_destroy("QZ1243A")
            except:
                pass
        
        
class T0840_BuildingSetName(ServiceDeskTests):
    """ Test renaming a building"""
    
    def do(self):
        self.superuser.building_create('QZ1243A', '.*', "No info")
        with AssertAccessError(self):
            try:
                self.proxy.building_update('QZ1243A', {"building": 'ZQ1296'})
                nd = self.superuser.building_fetch('ZQ1296', {"re": True, "info": True, "building": True})
                assert nd.building == "ZQ1296", "Bad building"
                assert nd.re == '.*', "Bad re"
                assert nd.info == "No info", "Bad info"
            finally:
                try:
                    self.superuser.building_destroy('ZQ1296')
                except:
                    pass
                try:
                    self.superuser.building_destroy('QZ1243A')
                except:
                    pass
                
                
class T0850_BuildingSetInfo(ServiceDeskTests):
    """ Test setting info on a building"""
    
    def do(self):
        self.superuser.building_create('QZ1243A', '.*', "TestBuilding")
        with AssertAccessError(self):
            try:
                self.proxy.building_update('QZ1243A', {"info": "ZQ1296 space"})
                nd = self.superuser.building_fetch('QZ1243A', {"re": True, "info": True, "building": True})
                assert nd.building == "QZ1243A", "Bad building"
                assert nd.re == '.*', "Bad re"
                assert nd.info == "ZQ1296 space", "Bad info"
            finally:
                self.superuser.building_destroy('QZ1243A')
                
                
class T0850_BuildingSetRe(ServiceDeskTests):
    """ Test setting re on a building"""
    
    def do(self):
        self.superuser.building_create('QZ1243A', '.*', "TestBuilding")
        with AssertAccessError(self):
            try:
                self.proxy.building_update('QZ1243A', {"re": ".+"})
                nd = self.superuser.building_fetch('QZ1243A', {"re": True, "info": True, "building": True})
                assert nd.building == "QZ1243A", "Bad building"
                assert nd.re == '.+', "Bad re"
                assert nd.info == "TestBuilding", "Bad info"
            finally:
                self.superuser.building_destroy('QZ1243A')
        
if __name__ == "__main__":
    sys.exit(main())
