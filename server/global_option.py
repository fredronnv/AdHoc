#!/usr/bin/env python2.6

from rpcc import *
from option_def import ExtNoSuchOptionDefError
from util import *

g_write = AnyGrants(AllowUserWithPriv("write_all_global_options"), AdHocSuperuserGuard)

class ExtNoSuchGlobalOptionError(ExtLookupError):
    desc = "No such global-option exists."
    

class ExtGlobalOptionAlreadyExistsError(ExtLookupError):
    desc = "The global option already exists"

    
class ExtGlobalOptionInUseError(ExtValueError):
    desc = "The global option is referred to by other objects. It cannot be destroyed"    


class ExtGlobalOptionName(ExtString):
    name = "global-option-name"
    desc = "Name of a global-option"
    regexp = "^[-a-zA-Z0-9_]+$"
    
    
class ExtGlobalOptionID(ExtInteger):
    name = "global-option-id"
    desc = "ID of a global-option"


class ExtGlobalOptionValue(ExtString):
    name = "global-option-value"
    desc = "Value. The value of the option"
    regexp = "^.*$"


class ExtGlobalOption(ExtGlobalOptionID):
    name = "global-option"
    desc = "A global-option instance, identified by its ID"

    def lookup(self, fun, cval):
        return fun.global_option_manager.get_global_option(cval)

    def output(self, fun, obj):
        return obj.oid
    
    
class GlobalOptionCreate(SessionedFunction):
    extname = "global_option_create"
    params = [("global_option_name", ExtGlobalOptionName, "Global option name to create"),
              ("value", ExtGlobalOptionValue, "The value of this particular option")]
    desc = "Creates a global option"
    returns = (ExtGlobalOptionID)

    def do(self):
        id = self.global_option_manager.create_global_option(self, self.global_option_name, self.value)
        return id


class GlobalOptionDestroy(SessionedFunction):
    extname = "global_option_destroy"
    params = [("global_option", ExtGlobalOption, "GlobalOption")]
    desc = "Destroys a global option"
    returns = (ExtNull)

    def do(self):
        self.global_option_manager.destroy_global_option(self, self.global_option)


class GlobalOption(Model):
    name = "global_option"
    exttype = ExtGlobalOption
    id_type = int

    def init(self, *args, **kwargs):
        a = list(args)
        #print "GlobalOption.init", a
        self.oid = a.pop(0)
        self.name = a.pop(0)
        self.value = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)

    @template("global_option", ExtGlobalOption)
    def get_global_option(self):
        return self
    
    @template("name", ExtGlobalOptionName)
    def get_name(self):
        return self.name

    @template("value", ExtGlobalOptionValue)
    def get_value(self):
        if self.value == None:
            return ""
        return self.value
    
    @template("mtime", ExtDateTime)
    def get_mtime(self):
        return self.mtime
    
    @template("info", ExtOrNull(ExtString))
    def get_info(self):
        try:
            return self.option_def_manager.get_option_def(self.name).info
        except ExtNoSuchOptionDefError:
            return None
    
    @template("changed_by", ExtString)
    def get_changed_by(self):
        return self.changed_by
    
    @update("name", ExtString)
    @entry(g_write)
    def set_global_option(self, newname):
        nn = str(newname)
        q = "UPDATE global_options SET name=:newname WHERE id=:id LIMIT 1"
        self.db.put(q, id=self.oid, newname=nn)
        self.manager.rename_object(self, nn)
        
        #print "GlobalOption %s changed Name to %s" % (self.oid, nn)
        
    @update("value", ExtGlobalOptionValue)
    @entry(g_write)
    def set_value(self, newvalue):
        q = "UPDATE global_options SET value=:value WHERE id=:id LIMIT 1"
        self.db.put(q, id=self.oid, value=newvalue)
        

class GlobalOptionManager(AdHocManager):
    name = "global_option_manager"
    manages = GlobalOption

    model_lookup_error = ExtNoSuchGlobalOptionError
    
    def init(self):
        self._model_cache = {}
        
    def base_query(self, dq):
        dq.select("r.id", "r.name", "r.value", "r.mtime", "r.changed_by")
        dq.table("global_options r")
        return dq

    def get_global_option(self, name):
        return self.model(name)

    def search_select(self, dq):
        dq.table("global_options r")
        dq.select("r.id")
    
    @search("name", StringMatch)
    def s_name(self, dq):
        dq.table("global_options r")
        return "r.name"
    
    @search("value", StringMatch)
    def s_value(self, dq):
        dq.table("global_options r")
        return "r.value"
    
    @search("id", IntegerMatch)
    def s_id(self, dq):
        dq.table("global_options r")
        return "r.id"
    
    @entry(g_write)
    def create_global_option(self, fun, name, value):
        q = "INSERT INTO global_options (name, value, changed_by) VALUES (:name, :value, :changed_by)"
        try:
            id = self.db.insert("id", q, name=name, value=value, changed_by=fun.session.authuser)
        except IntegrityError:
            raise ExtGlobalOptionAlreadyExistsError()
        return id
        
    @entry(g_write)
    def destroy_global_option(self, fun, global_option):
        q = "DELETE FROM global_options WHERE id=:id LIMIT 1"
        try:
            self.db.put(q, id=global_option.oid)
        except IntegrityError:
            raise ExtGlobalOptionInUseError()
