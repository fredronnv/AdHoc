#!/usr/bin/env python
# -*- coding: utf8 -*-

""" ADHOC building API test suite"""
from framework import *
from util import *


class T0800_BuildingList(UnAuthTests):
    """ Test building listing """

    def do(self):
        with AssertAccessError(self):
            ret = self.proxy.building_dig({}, {"re": True, "info": True, "id": True})
            
            assert len(ret) > 0, "Too few buildings returned"
            #for ds in ret:
                #print ds.re, ds.id, ds.info
  
  
class T0810_BuildingFetch(UnAuthTests):
    """ Test building_fetch """
    
    def do(self):
        buildings = [x.id for x in self.superuser.building_dig({}, {"id":True})]
        
        n = 0
        for building in buildings:
            ret = self.proxy.building_fetch(building, {"re": True, "info": True, "id": True})
            assert "re" in ret, "Key re missing in returned struct from building_fetch"
            assert "info" in ret, "Key info missing in returned struct from building_fetch"
            assert "id" in ret, "Key id missing in returned struct from building_fetch"
            n += 1
            if n > 50:  # There are too many buildings to check, 50 is enough
                break
            
            
class T0820_BuildingCreate(UnAuthTests):
    """ Test building_create """
    
    def do(self):  
        if self.proxy != self.superuser:
            return
        with AssertAccessError(self):
            self.proxy.building_create('QZ1243A', 'a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3', "TestBuilding")
            ret = self.superuser.building_fetch('QZ1243A', {"re": True, "info": True, "id": True})
            assert "re" in ret, "Key re missing in returned struct from building_fetch"
            assert "info" in ret, "Key info missing in returned struct from building_fetch"
            assert "id" in ret, "Key id missing in returned struct from building_fetch" 
            assert ret.id == "QZ1243A", "Bad building, is % should be %s" % (ret.id, "QZ1243A")
            assert ret.re == "a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3", "Re is " + ret.re + " but should be 'a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3'"
            assert ret.info == "TestBuilding", "Info is " + ret.info + "but should be 'TestBuilding'"
        
        
class T0830_BuildingDestroy(UnAuthTests):
    """ Test building destroy """
    
    def do(self):
        if self.proxy != self.superuser:
            return
        with AssertAccessError(self):
            self.proxy.building_destroy('QZ1243A')
            with AssertRPCCError("LookupError::NoSuchBuilding", True):
                self.superuser.building_fetch('QZ1243A', {"id": True})
        
        
class T0840_BuildingSetID(UnAuthTests):
    """ Test setting id of a building"""
    
    def do(self):
        if self.proxy != self.superuser:
            return
        self.superuser.building_create('QZ1243A', '.*', "No info")
        with AssertAccessError(self):
            try:
                self.proxy.building_update('QZ1243A', {"id": 'ZQ1296'})
                nd = self.superuser.building_fetch('ZQ1296', {"re": True, "info": True, "id": True})
                assert nd.id == "ZQ1296", "Bad building id"
                assert nd.re == '.*', "Bad re"
                assert nd.info == "No info", "Bad info"
            finally:
                self.superuser.building_destroy('ZQ1296')
                
                
class T0850_BuildingSetInfo(UnAuthTests):
    """ Test setting info on a building"""
    
    def do(self):
        if self.proxy != self.superuser:
            return
        self.superuser.building_create('QZ1243A', '.*', "TestBuilding")
        with AssertAccessError(self):
            try:
                self.proxy.building_update('QZ1243A', {"info": "ZQ1296 space"})
                nd = self.superuser.building_fetch('QZ1243A', {"re": True, "info": True, "id": True})
                assert nd.id == "QZ1243A", "Bad building id"
                assert nd.re == '.*', "Bad re"
                assert nd.info == "ZQ1296 space", "Bad info"
            finally:
                self.superuser.building_destroy('QZ1243A')
                
                
class T0850_BuildingSetRe(UnAuthTests):
    """ Test setting re on a building"""
    
    def do(self):
        if self.proxy != self.superuser:
            return
        self.superuser.building_create('QZ1243A', '.*', "TestBuilding")
        with AssertAccessError(self):
            try:
                self.proxy.building_update('QZ1243A', {"re": ".+"})
                nd = self.superuser.building_fetch('QZ1243A', {"re": True, "info": True, "id": True})
                assert nd.id == "QZ1243A", "Bad building id"
                assert nd.re == '.+', "Bad re"
                assert nd.info == "TestBuilding", "Bad info"
            finally:
                self.superuser.building_destroy('QZ1243A')
        
if __name__ == "__main__":
    sys.exit(main())
