#!/usr/bin/env python2.6

from rpcc.model import *
from rpcc.exttype import *
from rpcc.function import SessionedFunction


class ExtNoSuchBuildingError(ExtLookupError):
    desc = "No such building exists."


class ExtBuildingID(ExtString):
    name = "building-name"
    desc = "ID of a building"
    regexp = "^[-a-zA-Z0-9_]+$"


class ExtBuildingRe(ExtString):
    name = "building-re"
    desc = "Re. A regular expression"
    regexp = "^[-a-z0-9_., ]*$"


class ExtBuilding(ExtBuildingID):
    name = "building"
    desc = "A building instance"

    def lookup(self, fun, cval):
        return fun.building_manager.get_building(cval)

    def output(self, fun, obj):
        return obj.oid
    
    
class BuildingFunBase(SessionedFunction):  
    params = [("id", ExtBuildingID, "Building name to create")]
    
    
class BuildingCreate(BuildingFunBase):
    extname = "building_create"
    params = [("re", ExtBuildingRe, "The regular expression rooms must match for this building"),
              ("info", ExtString, "Building description")]
    desc = "Creates a building"
    returns = (ExtNull)

    def do(self):
        self.building_manager.create_building(self, self.id, self.re, self.info)


class BuildingDestroy(BuildingFunBase):
    extname = "building_destroy"
    desc = "Destroys a building"
    returns = (ExtNull)

    def do(self):
        self.building_manager.destroy_building(self, self.id)


class Building(Model):
    name = "building"
    exttype = ExtBuilding
    id_type = unicode

    def init(self, id, re, info):
        #print "Building.init", id, re, info
        self.oid = id
        self.re = re
        self.info = info

    @template("id", ExtBuilding)
    def get_id(self):
        return self

    @template("re", ExtBuildingRe)
    def get_re(self):
        if self.re == None:
            return ""
        return self.re

    @template("info", ExtString)
    def get_info(self):
        return self.info
    
    @update("id", ExtString)
    def set_id(self, newid):
        nn = str(newid)
        q = "UPDATE buildings SET id=:newid WHERE id=:id LIMIT 1"
        self.db.put(q, id=self.oid, newid=nn)
        self.db.commit()
        print "Building %s changed ID to %s" % (self.oid, nn)
        self.manager.rename_building(self, nn)
        
    @update("info", ExtString)
    def set_info(self, newinfo):
        q = "UPDATE buildings SET info=:info WHERE id=:id"
        self.db.put(q, id=self.oid, info=newinfo)
        self.db.commit()
        
    @update("re", ExtBuildingRe)
    def set_re(self, newre):
        q = "UPDATE buildings SET re=:re WHERE id=:id"
        self.db.put(q, id=self.oid, re=newre)
        self.db.commit()


class BuildingManager(Manager):
    name = "building_manager"
    manages = Building

    model_lookup_error = ExtNoSuchBuildingError

    def init(self):
        self._model_cache = {}

    def base_query(self, dq):
        dq.select("r.id", "r.re", "r.info")
        dq.table("buildings r")
        return dq

    def get_building(self, id):
        return self.model(id)

    def search_select(self, dq):
        dq.table("buildings r")
        dq.select("r.id")
    
    @search("id", StringMatch)
    def s_id(self, dq):
        dq.table("buildings r")
        return "r.id"
    
    def create_building(self, fun, id, re, info):
        q = "INSERT INTO buildings (id, re, info, changed_by) VALUES (:id, :re, :info, :changed_by)"
        self.db.put(q, id=id, re=re, info=info, changed_by=fun.session.authuser)
        print "Building created, id=", id
        self.db.commit()
        
    def destroy_building(self, fun, id):
        q = "DELETE FROM buildings WHERE id=:id LIMIT 1"
        self.db.put(q, id=id)
        print "Building destroyed, id=", id
        self.db.commit()
        
    def rename_building(self, obj, newid):
        oid = obj.oid
        obj.oid = newid
        del(self._model_cache[oid])
        self._model_cache[newid] = obj
