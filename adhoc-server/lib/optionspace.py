#!/usr/bin/env python2.6

# $Id$

from rpcc import *
from util import *

g_write = AnyGrants(AllowUserWithPriv("write_all_optionspaces"), AdHocSuperuserGuard)
g_read = AnyGrants(g_write, AllowUserWithPriv("read_all_optionspaces"))


class ExtNoSuchOptionspaceError(ExtLookupError):
    desc = "No such optionspace exists."


class ExtOptionspaceAlreadyExistsError(ExtLookupError):
    desc = "The optionspace already exists"

    
class ExtOptionspaceInUseError(ExtValueError):
    desc = "The optionspace is referred to by other objects. It cannot be destroyed"    


class ExtOptionspaceName(ExtString):
    name = "optionspace-name"
    desc = "Name of an optionspace"
    regexp = "^[-a-zA-Z0-9_]+$"


class ExtOptionspaceType(ExtEnum):
    name = "optionspace-type"
    desc = "Type of an optionspace"
    values = ['vendor', 'site']
    
  
class ExtOrNullOptionspace(ExtOrNull):
    name = "group_option_space"
    desc = "An option space, or null"
    typ = ExtOptionspaceName
    

class ExtOptionspace(ExtOptionspaceName):
    name = "optionspace"
    desc = "An optionspace instance"

    def lookup(self, fun, cval):
        return fun.optionspace_manager.get_optionspace(str(cval))

    def output(self, fun, obj):
        return obj.oid
 
    
class OptionspaceCreate(SessionedFunction):
    extname = "optionspace_create"
    params = [("optionspace_name", ExtOptionspaceName, "Optionspace to create"),
              ("type", ExtOptionspaceType, "The type of the optionspace"),
              ("info", ExtString, "Optionspace description")]
    desc = "Creates an optionspace"
    returns = (ExtNull)

    def do(self):
        self.optionspace_manager.create_optionspace(self, self.optionspace_name, self.type, self.info)


class OptionspaceDestroy(SessionedFunction):
    extname = "optionspace_destroy"
    params = [("optionspace", ExtOptionspace, "Optionspace to destroy")]
    desc = "Destroys an optionspace"
    returns = (ExtNull)

    def do(self):
        self.optionspace_manager.destroy_optionspace(self, self.optionspace)


class Optionspace(AdHocModel):
    name = "optionspace"
    exttype = ExtOptionspace
    id_type = str

    def init(self, *args, **kwargs):
        a = list(args)
        # print "Optionspace.init", a
        self.oid = a.pop(0)
        self.type = a.pop(0)
        self.info = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)
        
    @template("optionspace", ExtOptionspace)
    @entry(g_read)
    def get_optionspace(self):
        return self

    @template("type", ExtOptionspaceType)
    @entry(g_read)
    def get_type(self):
        return self.type

    @template("info", ExtString)
    @entry(g_read)
    def get_info(self):
        return self.info
    
    @template("mtime", ExtDateTime)
    @entry(g_read)
    def get_mtime(self):
        return self.mtime
    
    @template("changed_by", ExtString)
    @entry(g_read)
    def get_changed_by(self):
        return self.changed_by
    
    @update("optionspace", ExtString)
    @entry(g_write)
    def set_optionspace(self, optionspace_name):
        nn = str(optionspace_name)
        q = "UPDATE optionspaces SET value=:value WHERE value=:oid LIMIT 1"
        self.db.put(q, oid=self.oid, value=nn)
        
        # print "Optionspace %s changed name to %s" % (self.oid, nn)
        self.manager.rename_object(self, nn)
        self.event_manager.add("rename", optionspace=self.oid, newstr=nn, authuser=self.function.session.authuser)
        
    @update("info", ExtString)
    @entry(g_write)
    def set_info(self, value):
        q = "UPDATE optionspaces SET info=:info WHERE value=:optionspace"
        self.db.put(q, optionspace=self.oid, info=value)
        self.event_manager.add("update", optionspace=self.oid, info=value, authuser=self.function.session.authuser)
              
    @update("type", ExtOptionspaceType)
    @entry(g_write)
    def set_type(self, value):
        q = "UPDATE optionspaces SET type=:type WHERE value=:optionspace"
        self.db.put(q, optionspace=self.oid, type=value)
        self.event_manager.add("update", optionspace=self.oid, type=value, authuser=self.function.session.authuser)
        

class OptionspaceManager(AdHocManager):
    name = "optionspace_manager"
    manages = Optionspace

    model_lookup_error = ExtNoSuchOptionspaceError
    
    def init(self):
        self._model_cache = {}
        
    @classmethod
    def base_query(cls, dq):
        dq.select("ds.value", "ds.type", "ds.info", "ds.mtime", "ds.changed_by")
        dq.table("optionspaces ds")
        return dq

    def get_optionspace(self, optionspace_name):
        return self.model(optionspace_name)

    def search_select(self, dq):
        dq.table("optionspaces ds")
        dq.select("ds.value")

    @search("optionspace", StringMatch)
    def s_optionspace(self, dq):
        dq.table("optionspaces ds")
        return "ds.value"
    
    @search("type", StringMatch)
    def s_type(self, dq):
        dq.table("optionspaces ds")
        return "ds.type"
    
    @search("info", NullableStringMatch)
    def s_info(self, dq):
        dq.table("optionspaces ds")
        return "ds.info"
    
    @entry(g_write)
    def create_optionspace(self, fun, optionspace_name, optionspace_type, info):
        q = "INSERT INTO optionspaces (value, type, info, changed_by) VALUES (:value, :type, :info, :changed_by)"
        try:
            self.db.put(q, value=optionspace_name, type=optionspace_type, info=info, changed_by=fun.session.authuser)
        except IntegrityError:
            raise ExtOptionspaceAlreadyExistsError()
        self.event_manager.add("create", optionspace=optionspace_name, type=optionspace_type,
                               info=info, authuser=fun.session.authuser)
        
    @entry(g_write)
    def destroy_optionspace(self, fun, optionspace):
        
        try:
            q = "DELETE FROM optionspaces WHERE value=:value LIMIT 1"
            self.db.put(q, value=optionspace.oid)
        except IntegrityError:
            raise ExtOptionspaceInUseError()
        self.event_manager.add("destroy", optionspace=optionspace.oid, authuser=fun.session.authuser)
