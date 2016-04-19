#!/usr/bin/env python2.6

# $Id$

from rpcc import *
from util import *


g_write = AnyGrants(AllowUserWithPriv("write_all_rooms"), AdHocSuperuserGuard)


class ExtNoSuchRoomError(ExtLookupError):
    desc = "No such room exists."
    
    
class ExtNoMatchingBuildingError(ExtLookupError):
    desc = "There is no building defined that matches the room name"


class ExtRoomAlreadyExistsError(ExtLookupError):
    desc = "The room name is already in use"
    
    
class ExtRoomInUseError(ExtValueError):
    desc = "The room is referred to by other objects. It cannot be destroyed"    


class ExtRoomName(ExtString):
    name = "room-name"
    desc = "Name of a room"
    regexp = "^[-a-zA-Z0-9_]+$"
    
    def lookup(self, fun, cval):
        q = "SELECT re FROM buildings"
        for rexp in fun.db.get_all(q):
            if re.match(rexp[0], cval):
                return cval
        raise ExtNoMatchingBuildingError()


class ExtRoomPrinters(ExtString):
    name = "room-printers"
    desc = "Printers. A comma separated list of DNS names"
    regexp = "^[-a-z0-9_., ]*$"


class ExtRoom(ExtRoomName):
    name = "room"
    desc = "A room instance"

    def lookup(self, fun, cval):
        return fun.room_manager.get_room(cval)

    def output(self, fun, obj):
        return obj.oid
    
    
class RoomFunBase(SessionedFunction):  
    params = [("id", ExtRoomName, "Room name to create")]
    
    
class RoomCreate(SessionedFunction):
    extname = "room_create"
    params = [("room_name", ExtRoomName, "Room name to create"),
              ("printers", ExtRoomPrinters, "The printers located nearby the room"),
              ("info", ExtString, "Room description")]
    desc = "Creates a room"
    returns = (ExtNull)

    def do(self):
        self.room_manager.create_room(self, self.room_name, self.printers, self.info)


class RoomDestroy(SessionedFunction):
    extname = "room_destroy"
    params = [("room", ExtRoom, "Room to destroy")]
    desc = "Destroys a room"
    returns = (ExtNull)

    def do(self):
        self.room_manager.destroy_room(self, self.room)


class Room(AdHocModel):
    name = "room"
    exttype = ExtRoom
    id_type = unicode

    def init(self, *args, **kwargs):
        a = list(args)
        # print "Room.init", a
        self.oid = a.pop(0)
        self.printers = a.pop(0)
        self.info = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)

    @template("room", ExtRoom)
    def get_room(self):
        return self

    @template("printers", ExtRoomPrinters)
    def get_printers(self):
        if self.printers is None:
            return ""
        return self.printers

    @template("info", ExtString)
    def get_info(self):
        return self.info
    
    @template("mtime", ExtDateTime)
    def get_mtime(self):
        return self.mtime
    
    @template("changed_by", ExtString)
    def get_changed_by(self):
        return self.changed_by
    
    @update("room", ExtString)
    @entry(g_write)
    def set_room(self, newid):
        nn = str(newid)
        q = "UPDATE rooms SET id=:newid WHERE id=:id LIMIT 1"
        self.db.put(q, id=self.oid, newid=nn)
        
        # print "Room %s changed ID to %s" % (self.oid, nn)
        self.manager.rename_object(self, nn)
        self.event_manager.add("rename", room=self.oid, newstr=nn, authuser=self.function.session.authuser)
        
    @update("info", ExtString)
    @entry(g_write)
    def set_info(self, value):
        q = "UPDATE rooms SET info=:info WHERE id=:id"
        self.db.put(q, id=self.oid, info=value)
        self.event_manager.add("update", room=self.oid, info=value, authuser=self.function.session.authuser)
              
    @update("printers", ExtRoomPrinters)
    @entry(g_write)
    def set_printers(self, value):
        q = "UPDATE rooms SET printers=:printers WHERE id=:id"
        self.db.put(q, id=self.oid, printers=value)
        self.event_manager.add("update", room=self.oid, printers=value, authuser=self.function.session.authuser)
        

class RoomManager(AdHocManager):
    name = "room_manager"
    manages = Room

    model_lookup_error = ExtNoSuchRoomError
    
    def init(self):
        self._model_cache = {}
        
    @classmethod
    def base_query(cls, dq):
        dq.select("r.id", "r.printers", "r.info", "r.mtime", "r.changed_by")
        dq.table("rooms r")
        return dq

    def get_room(self, room_name):
        return self.model(room_name)

    def search_select(self, dq):
        dq.table("rooms r")
        dq.select("r.id")
    
    @search("room", StringMatch)
    def s_id(self, dq):
        dq.table("rooms r")
        return "r.id"
    
    @search("info", NullableStringMatch)
    def s_info(self, dq):
        dq.table("rooms r")
        return "r.info"
    
    @search("printers", NullableStringMatch)
    def s_sprinters(self, dq):
        dq.table("rooms r")
        return "r.printers"
    
    @entry(g_write)
    def create_room(self, fun, room_name, printers, info):
        q = "INSERT INTO rooms (id, printers, info, changed_by) VALUES (:id, :printers, :info, :changed_by)"
        try:
            self.db.put(q, id=room_name, printers=printers, info=info, changed_by=fun.session.authuser)
        except IntegrityError:
            raise ExtRoomAlreadyExistsError()
        self.event_manager.add("create", room=room_name, printers=printers, authuser=fun.session.authuser, info=info)
        # print "Room created, id=", id
                  
    @entry(g_write)
    def destroy_room(self, fun, room):
        try:
            q = "DELETE FROM rooms WHERE id=:id LIMIT 1"
            self.db.put(q, id=room.oid)
        except IntegrityError:
            raise ExtRoomInUseError()
        self.event_manager.add("destroy", room=room.oid, authuser=fun.session.authuser)
