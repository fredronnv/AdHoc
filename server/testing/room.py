#!/usr/bin/env python
# -*- coding: utf8 -*-

""" ADHOC room API test suite"""
from framework import *
from testutil import *


class T0700_RoomList(UnAuthTests):
    """ Test room listing """
    skip = True
    
    def do(self):
        with AssertAccessError(self):
            # ret = 
            self.proxy.room_dig({}, {"printers": True, "info": True, "room": True})
            
#             assert len(ret) > 0, "Too few rooms returned"
#             for ds in ret:
#                 print ds.printers, ds.room, ds.info
  
  
class T0710_RoomFetch(UnAuthTests):
    """ Test room_fetch """
    
    def do(self):
        rooms = [x.room for x in self.superuser.room_dig({}, {"room": True})]
        
        n = 0
        for room in rooms:
            ret = self.proxy.room_fetch(room, {"printers": True, "info": True, "room": True})
            assert "printers" in ret, "Key printers missing in returned struct from room_fetch"
            assert "info" in ret, "Key info missing in returned struct from room_fetch"
            assert "room" in ret, "Key room missing in returned struct from room_fetch"
            n += 1
            if n > 50:  # There are too many rooms to check, 50 is enough
                break
            
            
class T0720_RoomCreate(FloorAdminTests):
    """ Test room_create """
    
    def do(self):
        try:
            
            with AssertAccessError(self):
                try:
                    self.proxy.room_destroy('CA9876H')
                except:
                    pass
                self.proxy.room_create('CA9876H', 'a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3,a-3223-laser1', "TestRoom")
                ret = self.superuser.room_fetch('CA9876H', {"printers": True, "info": True, "room": True})
                assert "printers" in ret, "Key printers missing in returned struct from room_fetch"
                assert "info" in ret, "Key info missing in returned struct from room_fetch"
                assert "room" in ret, "Key room missing in returned struct from room_fetch" 
                assert ret.room == "CA9876H", "Bad room, is % should be %s" % (ret.room, "CA9876H")
                assert ret.printers == "a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3,a-3223-laser1", "Printers is " + ret.printers + " but should be 'a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3,a-3223-laser1'"
                assert ret.info == "TestRoom", "Info is " + ret.info + "but should be 'TestRoom'"
        finally:
            try:
                self.superuser.room_destroy('CA9876H')
            except:
                pass
        
        
class T0730_RoomDestroy(FloorAdminTests):
    """ Test room destroy """
    
    def do(self):
        self.superuser.room_create('CA9876H', 'a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3,a-3223-laser1', "TestRoom")
        try:
            with AssertAccessError(self):
                self.proxy.room_destroy('CA9876H')
                with AssertRPCCError("LookupError::NoSuchRoom", True):
                    self.superuser.room_fetch('CA9876H', {"room": True})
        finally:   
            try:
                self.superuser.room_destroy('CA9876H')
            except:
                pass
            
        
class T0740_RoomSetName(FloorAdminTests):
    """ Test setting name of a room"""
    
    def do(self):
        self.superuser.room_create('CA9876H', 'a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3,a-3223-laser1', "TestRoom")
        with AssertAccessError(self):
            try:
                self.proxy.room_update('CA9876H', {"room": 'ZQ1296'})
                nd = self.superuser.room_fetch('ZQ1296', {"printers": True, "info": True, "room": True})
                assert nd.room == "ZQ1296", "Bad room"
                assert nd.printers == 'a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3,a-3223-laser1', "Bad printers"
                assert nd.info == "TestRoom", "Bad info"
            finally:
                try:
                    self.superuser.room_destroy('ZQ1296')
                except:
                    pass
                try:
                    self.superuser.room_destroy('CA9876H')
                except:
                    pass
                
                
class T0750_RoomSetInfo(FloorAdminTests):
    """ Test setting info on a room"""
    
    def do(self):
        self.superuser.room_create('CA9876H', 'a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3,a-3223-laser1', "TestRoom")
        with AssertAccessError(self):
            try:
                self.proxy.room_update('CA9876H', {"info": "ZQ1296 space"})
                nd = self.superuser.room_fetch('CA9876H', {"printers": True, "info": True, "room": True})
                assert nd.room == "CA9876H", "Bad room"
                assert nd.printers == 'a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3,a-3223-laser1', "Bad printers"
                assert nd.info == "ZQ1296 space", "Bad info"
            finally:
                self.superuser.room_destroy('CA9876H')
                
                
class T0750_RoomSetPrinters(FloorAdminTests):
    """ Test setting printers on a room"""
    
    def do(self):
        self.superuser.room_create('CA9876H', 'a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3,a-3223-laser1', "TestRoom")
        with AssertAccessError(self):
            try:
                self.proxy.room_update('CA9876H', {"printers": "a-4208-color1,a-4264-color1"})
                nd = self.superuser.room_fetch('CA9876H', {"printers": True, "info": True, "room": True})
                assert nd.room == "CA9876H", "Bad room"
                assert nd.printers == 'a-4208-color1,a-4264-color1', "Bad printers"
                assert nd.info == "TestRoom", "Bad info"
            finally:
                self.superuser.room_destroy('CA9876H')
        
if __name__ == "__main__":
    sys.exit(main())
