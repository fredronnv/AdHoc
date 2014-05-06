#!/usr/bin/env python2.6

# $Id$

from rpcc import *
from util import *


g_read = AnyGrants(AllowUserWithPriv("read_all_buildings"), AdHocSuperuserGuard)
g_write = AnyGrants(AllowUserWithPriv("write_all_buildings"), AdHocSuperuserGuard)

class ExtNoSuchBuildingError(ExtLookupError):
    desc = "No such building exists."


class ExtBuildingAlreadyExistsError(ExtLookupError):
    desc = "The building name is already in use"

    
class ExtBuildingInUseError(ExtValueError):
    desc = "The building is referred to by other objects. It cannot be destroyed"    


class ExtBuildingName(ExtString):
    name = "building-name"
    desc = "ID of a building"
    regexp = "^[-a-zA-Z0-9_]+$"


class ExtBuildingRe(ExtString):
    name = "building-re"
    desc = "Re. A regular expression"
    regexp = "^.*$"


class ExtBuilding(ExtBuildingName):
    name = "building"
    desc = "A building instance"

    def lookup(self, fun, cval):
        return fun.building_manager.get_building(cval)

    def output(self, fun, obj):
        return obj.oid
   
    
class BuildingCreate(SessionedFunction):
    extname = "building_create"
    params = [("id", ExtBuildingName, "Building name to create"),
              ("re", ExtBuildingRe, "The regular expression rooms must match for this building"),
              ("info", ExtString, "Building description")]
    desc = "Creates a building"
    creates_event = True
    returns = (ExtNull)

    def do(self):
        self.building_manager.create_building(self, self.id, self.re, self.info)


class BuildingDestroy(SessionedFunction):
    extname = "building_destroy"
    params = [("building", ExtBuilding, "Building to destroy")]
    desc = "Destroys a building"
    creates_event = True
    returns = (ExtNull)

    def do(self):
        self.building_manager.destroy_building(self, self.building)


class Building(AdHocModel):
    name = "building"
    exttype = ExtBuilding
    id_type = unicode

    def init(self, *args, **kwargs):
        a = list(args)
        #print "Building.init", a
        self.oid = a.pop(0)
        self.re = a.pop(0)
        self.info = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)

    @template("building", ExtBuilding)
    def get_building(self):
        return self

    @template("re", ExtBuildingRe)
    def get_re(self):
        if self.re == None:
            return ""
        return self.re

    @template("info", ExtString)
    def get_info(self):
        return self.info
    
    @template("mtime", ExtDateTime)
    def get_mtime(self):
        return self.mtime
    
    @template("changed_by", ExtString)
    def get_changed_by(self):
        return self.changed_by
    
    @update("building", ExtString)
    @entry(g_write)
    def set_building(self, value):
        nn = str(value)
        q = "UPDATE buildings SET id=:value WHERE id=:id LIMIT 1"
        self.db.put(q, id=self.oid, value=str(value))
        
        #print "Building %s changed ID to %s" % (self.oid, nn)
        self.manager.rename_object(self, str(value))
        self.event_manager.add("rename", building=self.oid, newstr=str(value), authuser=self.function.session.authuser)
        
    @update("info", ExtString)
    @entry(g_write)
    def set_info(self, newinfo):
        q = "UPDATE buildings SET info=:info WHERE id=:id"
        self.db.put(q, id=self.oid, info=newinfo)
        self.event_manager.add("update",  building=self.oid, info=newinfo, authuser=self.function.session.authuser)
        
    @update("re", ExtBuildingRe)
    @entry(g_write)
    def set_re(self, newre):
        q = "UPDATE buildings SET re=:re WHERE id=:id"
        self.db.put(q, id=self.oid, re=newre)
        self.event_manager.add("update",  building=self.oid, re=newre, authuser=self.function.session.authuser)
        

class BuildingManager(AdHocManager):
    name = "building_manager"
    manages = Building

    model_lookup_error = ExtNoSuchBuildingError

    def init(self):
        self._model_cache = {}
        
    def base_query(self, dq):
        dq.select("r.id", "r.re", "r.info", "r.mtime", "r.changed_by")
        dq.table("buildings r")
        return dq

    def get_building(self, building_name):
        return self.model(building_name)

    def search_select(self, dq):
        dq.table("buildings r")
        dq.select("r.id")
    
    @search("building", StringMatch)
    def s_building(self, dq):
        dq.table("buildings r")
        return "r.id"
    
    @entry(g_write)
    def create_building(self, fun, building_name, re, info):
        q = "INSERT INTO buildings (id, re, info, changed_by) VALUES (:id, :re, :info, :changed_by)"
        try:
            self.db.put(q, id=building_name, re=re, info=info, changed_by=fun.session.authuser)
        except IntegrityError:
            raise ExtBuildingAlreadyExistsError()
        self.event_manager.add("create", building=building_name, re=re, info=info)
               
    @entry(g_write)
    def destroy_building(self, fun, building):
        q = "DELETE FROM buildings WHERE id=:id LIMIT 1"
        try:
            self.db.put(q, id=building.oid)
        except IntegrityError:
            raise ExtBuildingInUseError()
        
        self.event_manager.add("destroy", building=building.oid)
        #print "Building destroyed, id=", building.oid
        
