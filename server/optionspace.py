#!/usr/bin/env python2.6

from rpcc.model import *
from rpcc.exttype import *
from rpcc.function import SessionedFunction


class ExtNoSuchOptionspaceError(ExtLookupError):
    desc = "No such optionspace exists."


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


class Optionspace(Model):
    name = "optionspace"
    exttype = ExtOptionspace
    id_type = str

    def init(self, *args, **kwargs):
        a = list(args)
        #print "Optionspace.init", a
        self.oid = a.pop(0)
        self.type = a.pop(0)
        self.info = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)
        
    @template("optionspace", ExtOptionspace)
    def get_optionspace(self):
        return self

    @template("type", ExtOptionspaceType)
    def get_type(self):
        return self.type

    @template("info", ExtString)
    def get_info(self):
        return self.info
    
    @template("mtime", ExtDateTime)
    def get_mtime(self):
        return self.mtime
    
    @template("changed_by", ExtString)
    def get_changed_by(self):
        return self.changed_by
    
    @update("optionspace", ExtString)
    def set_optionspace(self, optionspace_name):
        nn = str(optionspace_name)
        q = "UPDATE optionspaces SET value=:value WHERE value=:oid LIMIT 1"
        self.db.put(q, oid=self.oid, value=nn)
        self.db.commit()
        print "Optionspace %s changed name to %s" % (self.oid, nn)
        self.manager.rename_optionspace(self, nn)
        
    @update("info", ExtString)
    def set_info(self, info):
        q = "UPDATE optionspaces SET info=:info WHERE value=:value"
        self.db.put(q, value=self.oid, info=info)
        self.db.commit()
        
    @update("type", ExtOptionspaceType)
    def set_type(self, newtype):
        q = "UPDATE optionspaces SET type=:type WHERE value=:value"
        self.db.put(q, value=self.oid, type=newtype)
        self.db.commit()


class OptionspaceManager(Manager):
    name = "optionspace_manager"
    manages = Optionspace

    model_lookup_error = ExtNoSuchOptionspaceError
    
    def init(self):
        self._model_cache = {}
        
    def base_query(self, dq):
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
    
    def create_optionspace(self, fun, optionspace_name, optionspace_type, info):
        q = "INSERT INTO optionspaces (value, type, info, changed_by) VALUES (:value, :type, :info, :changed_by)"
        self.db.put(q, value=optionspace_name, type=optionspace_type, info=info, changed_by=fun.session.authuser)
        print "Optionspace created, name=", optionspace_name
        self.db.commit()
        
    def destroy_optionspace(self, fun, optionspace):
        q = "DELETE FROM optionspaces WHERE value=:value LIMIT 1"
        self.db.put(q, value=optionspace.oid)
        print "Optionspace destroyed, name=", optionspace.oid
        self.db.commit()
        
    def rename_optionspace(self, obj, optionspace_name):
        oname = obj.oid
        obj.oid = optionspace_name
        del(self._model_cache[oname])
        self._model_cache[optionspace_name] = obj
