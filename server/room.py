#!/usr/bin/env python2.6

from rpcc.model import *
from rpcc.exttype import *
from rpcc.function import Function, SessionedFunction


class ExtNoSuchRoomError(ExtLookupError):
    desc = "No such room exists."


class ExtRoomID(ExtString):
    name = "room-name"
    desc = "ID of a room"
    regexp = "^[-a-zA-Z0-9_]+$"


class ExtRoomPrinters(ExtString):
    name = "room-printers"
    desc = "Printers. A comma separated list of DNS names"
    regexp = "^[-a-z0-9_., ]*$"


class ExtRoom(ExtRoomID):
    name = "room"
    desc = "A room instance"

    def lookup(self, fun, cval):
        return fun.room_manager.get_room(cval)

    def output(self, fun, obj):
        return obj.oid
    
    
class RoomFunBase(SessionedFunction):  
    params = [("id", ExtRoomID, "Room name to create")]
    
    
class RoomCreate(RoomFunBase):
    extname = "room_create"
    params = [("printers", ExtRoomPrinters, "The printers located nearby the room"),
              ("info", ExtString, "Room description")]
    desc = "Creates a room"
    returns = (ExtNull)

    def do(self):
        self.room_manager.create_room(self, self.id, self.printers, self.info)


class RoomDestroy(RoomFunBase):
    extname = "room_destroy"
    desc = "Destroys a room"
    returns = (ExtNull)

    def do(self):
        self.room_manager.destroy_room(self, self.id)


class Room(Model):
    name = "room"
    exttype = ExtRoom
    id_type = unicode

    def init(self, id, printers, info):
        #print "Room.init", id, printers, info
        self.oid = id
        self.printers = printers
        self.info = info

    @template("id", ExtRoom)
    def get_id(self):
        return self

    @template("printers", ExtRoomPrinters)
    def get_printers(self):
        if self.printers == None:
            return ""
        return self.printers

    @template("info", ExtString)
    def get_info(self):
        return self.info
    
    @update("id", ExtString)
    def set_id(self, newid):
        nn = str(newid)
        q = "UPDATE rooms SET id=:newid WHERE id=:id LIMIT 1"
        self.db.put(q, id=self.oid, newid=nn)
        self.db.commit()
        print "Room %s changed ID to %s" % (self.oid, nn)
        self.manager.rename_room(self, nn)
        
    @update("info", ExtString)
    def set_info(self, newinfo):
        q = "UPDATE rooms SET info=:info WHERE id=:id"
        self.db.put(q, id=self.oid, info=newinfo)
        self.db.commit()
        
    @update("printers", ExtRoomPrinters)
    def set_printers(self, newprinters):
        q = "UPDATE rooms SET printers=:printers WHERE id=:id"
        self.db.put(q, id=self.oid, printers=newprinters)
        self.db.commit()


class RoomManager(Manager):
    name = "room_manager"
    manages = Room

    model_lookup_error = ExtNoSuchRoomError

    def init(self):
        self._model_cache = {}

    def base_query(self, dq):
        dq.select("r.id", "r.printers", "r.info")
        dq.table("rooms r")
        return dq

    def get_room(self, id):
        return self.model(id)

    def search_select(self, dq):
        dq.table("rooms r")
        dq.select("r.id")
    
    @search("id", StringMatch)
    def s_id(self, dq):
        dq.table("rooms r")
        return "r.id"
    
    def create_room(self, fun, id, printers, info):
        q = "INSERT INTO rooms (id, printers, info, changed_by) VALUES (:id, :printers, :info, :changed_by)"
        self.db.put(q, id=id, printers=printers, info=info, changed_by=fun.session.authuser)
        print "Room created, id=", id
        self.db.commit()
        
    def destroy_room(self, fun, id):
        q = "DELETE FROM rooms WHERE id=:id LIMIT 1"
        self.db.put(q, id=id)
        print "Room destroyed, id=", id
        self.db.commit()
        
    def rename_room(self, obj, newid):
        oid = obj.oid
        obj.oid = newid
        del(self._model_cache[oid])
        self._model_cache[newid] = obj
