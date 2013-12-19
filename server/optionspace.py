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
    
    
class OptionspaceFunBase(SessionedFunction):  
    params = [("name", ExtOptionspaceName, "Optionspace name to create")]
    
    
class OptionspaceCreate(OptionspaceFunBase):
    extname = "optionspace_create"
    params = [("type", ExtOptionspaceType, "The type of the optionspace"),
              ("info", ExtString, "Optionspace description")]
    desc = "Creates an optionspace"
    returns = (ExtNull)

    def do(self):
        self.optionspace_manager.create_optionspace(self, self.name, self.type, self.info)


class OptionspaceDestroy(OptionspaceFunBase):
    extname = "optionspace_destroy"
    desc = "Destroys an optionspace"
    returns = (ExtNull)

    def do(self):
        self.optionspace_manager.destroy_optionspace(self, self.name)


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
        
    @template("name", ExtOptionspace)
    def get_name(self):
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
    
    @update("name", ExtString)
    def set_name(self, newname):
        nn = str(newname)
        q = "UPDATE optionspaces SET value=:newname WHERE value=:name LIMIT 1"
        self.db.put(q, name=self.oid, newname=nn)
        self.db.commit()
        print "Optionspace %s changed name to %s" % (self.oid, nn)
        self.manager.rename_optionspace(self, nn)
        
    @update("info", ExtString)
    def set_info(self, newinfo):
        q = "UPDATE optionspaces SET info=:info WHERE value=:name"
        self.db.put(q, name=self.oid, info=newinfo)
        self.db.commit()
        
    @update("type", ExtOptionspaceType)
    def set_type(self, newtype):
        q = "UPDATE optionspaces SET type=:type WHERE value=:name"
        self.db.put(q, name=self.oid, type=newtype)
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

    def get_optionspace(self, name):
        return self.model(name)

    def search_select(self, dq):
        dq.table("optionspaces ds")
        dq.select("ds.value")

    @search("optionspace", StringMatch)
    def s_name(self, dq):
        dq.table("optionspaces ds")
        return "ds.value"
    
    def create_optionspace(self, fun, name, optionspace_type, info):
        q = "INSERT INTO optionspaces (value, type, info, changed_by) VALUES (:name, :type, :info, :changed_by)"
        self.db.put(q, name=name, type=optionspace_type, info=info, changed_by=fun.session.authuser)
        print "Optionspace created, name=", name
        self.db.commit()
        
    def destroy_optionspace(self, fun, name):
        q = "DELETE FROM optionspaces WHERE value=:name LIMIT 1"
        self.db.put(q, name=name)
        print "Optionspace destroyed, name=", name
        self.db.commit()
        
    def rename_optionspace(self, obj, newname):
        oname = obj.oid
        obj.oid = newname
        del(self._model_cache[oname])
        self._model_cache[newname] = obj
        
        
