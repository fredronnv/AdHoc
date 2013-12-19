#!/usr/bin/env python
# -*- coding: utf8 -*-

""" ADHOC room API test suite"""
from framework import *
from util import *


class T0700_RoomList(UnAuthTests):
    """ Test room listing """

    def do(self):
        with AssertAccessError(self):
            ret = self.proxy.room_dig({}, {"printers": True, "info": True, "room": True})
            
            #assert len(ret) > 0, "Too few rooms returned"
            #for ds in ret:
                #print ds.printers, ds.room, ds.info
  
  
class T0710_RoomFetch(UnAuthTests):
    """ Test room_fetch """
    
    def do(self):
        rooms = [x.room for x in self.superuser.room_dig({}, {"room":True})]
        
        n=0
        for room in rooms:
            ret = self.proxy.room_fetch(room, {"printers": True, "info": True, "room": True})
            assert "printers" in ret, "Key printers missing in returned struct from room_fetch"
            assert "info" in ret, "Key info missing in returned struct from room_fetch"
            assert "room" in ret, "Key room missing in returned struct from room_fetch"
            n += 1
            if n > 50:  # There are too many rooms to check, 50 is enough
                break
            
            
class T0720_RoomCreate(UnAuthTests):
    """ Test room_create """
    
    def do(self):  
        if self.proxy != self.superuser:
            return
        with AssertAccessError(self):
            try:
                self.proxy.room_destroy('QZ1243A')
            except:
                pass
            self.proxy.room_create('QZ1243A', 'a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3,a-3223-laser1', "TestRoom")
            ret = self.superuser.room_fetch('QZ1243A', {"printers": True, "info": True, "room": True})
            assert "printers" in ret, "Key printers missing in returned struct from room_fetch"
            assert "info" in ret, "Key info missing in returned struct from room_fetch"
            assert "room" in ret, "Key room missing in returned struct from room_fetch" 
            assert ret.room == "QZ1243A", "Bad room, is % should be %s" % (ret.room, "QZ1243A")
            assert ret.printers == "a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3,a-3223-laser1", "Printers is " + ret.printers + " but should be 'a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3,a-3223-laser1'"
            assert ret.info == "TestRoom", "Info is " + ret.info + "but should be 'TestRoom'"
        
        
class T0730_RoomDestroy(UnAuthTests):
    """ Test room destroy """
    
    def do(self):
        if self.proxy != self.superuser:
            return
        with AssertAccessError(self):
            self.proxy.room_destroy('QZ1243A')
            with AssertRPCCError("LookupError::NoSuchRoom", True):
                self.superuser.room_fetch('QZ1243A', {"room": True})
        
        
class T0740_RoomSetName(UnAuthTests):
    """ Test setting name of a room"""
    
    def do(self):
        if self.proxy != self.superuser:
            return
        self.superuser.room_create('QZ1243A', 'a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3,a-3223-laser1', "TestRoom")
        with AssertAccessError(self):
            try:
                self.proxy.room_update('QZ1243A', {"room": 'ZQ1296'})
                nd = self.superuser.room_fetch('ZQ1296', {"printers": True, "info": True, "room": True})
                assert nd.room == "ZQ1296", "Bad room"
                assert nd.printers == 'a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3,a-3223-laser1', "Bad printers"
                assert nd.info == "TestRoom", "Bad info"
            finally:
                self.superuser.room_destroy('ZQ1296')
                
                
class T0750_RoomSetInfo(UnAuthTests):
    """ Test setting info on a room"""
    
    def do(self):
        if self.proxy != self.superuser:
            return
        self.superuser.room_create('QZ1243A', 'a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3,a-3223-laser1', "TestRoom")
        with AssertAccessError(self):
            try:
                self.proxy.room_update('QZ1243A', {"info": "ZQ1296 space"})
                nd = self.superuser.room_fetch('QZ1243A', {"printers": True, "info": True, "room": True})
                assert nd.room == "QZ1243A", "Bad room"
                assert nd.printers == 'a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3,a-3223-laser1', "Bad printers"
                assert nd.info == "ZQ1296 space", "Bad info"
            finally:
                self.superuser.room_destroy('QZ1243A')
                
                
class T0750_RoomSetPrinters(UnAuthTests):
    """ Test setting printers on a room"""
    
    def do(self):
        if self.proxy != self.superuser:
            return
        self.superuser.room_create('QZ1243A', 'a-2234-color2,a-2234-plot2,a-2234-plot1,a-2234-color3,a-3223-laser1', "TestRoom")
        with AssertAccessError(self):
            try:
                self.proxy.room_update('QZ1243A', {"printers": "a-4208-color1,a-4264-color1"})
                nd = self.superuser.room_fetch('QZ1243A', {"printers": True, "info": True, "room": True})
                assert nd.room == "QZ1243A", "Bad room"
                assert nd.printers == 'a-4208-color1,a-4264-color1', "Bad printers"
                assert nd.info == "TestRoom", "Bad info"
            finally:
                self.superuser.room_destroy('QZ1243A')
        
if __name__ == "__main__":
    sys.exit(main())
