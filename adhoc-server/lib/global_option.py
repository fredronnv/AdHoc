#!/usr/bin/env python2.6

# $Id$

from option_def import ExtNoSuchOptionDefError
from rpcc import *
from util import *

g_write = AnyGrants(AllowUserWithPriv("write_all_global_options"), AdHocSuperuserGuard)
g_read = AnyGrants(g_write, AllowUserWithPriv("read_all_global_options"))


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
              ("value", ExtGlobalOptionValue, "The value of this particular option"),
              ("basic_command", ExtBoolean, "The option is a basic command rather than an option")]
    desc = "Creates a global option"
    returns = (ExtGlobalOptionID)

    def do(self):
        id = self.global_option_manager.create_global_option(self, self.global_option_name, self.value, self.basic_command)
        return id


class GlobalOptionDestroy(SessionedFunction):
    extname = "global_option_destroy"
    params = [("global_option", ExtGlobalOption, "GlobalOption")]
    desc = "Destroys a global option"
    returns = (ExtNull)

    def do(self):
        self.global_option_manager.destroy_global_option(self, self.global_option)


class GlobalOption(AdHocModel):
    name = "global_option"
    exttype = ExtGlobalOption
    id_type = int

    def init(self, *args, **kwargs):
        a = list(args)
        # print "GlobalOption.init", a
        self.oid = a.pop(0)
        self.name = a.pop(0)
        self.value = a.pop(0)
        self.basic = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)

    @template("global_option", ExtGlobalOption)
    @entry(g_read)
    def get_global_option(self):
        return self
    
    @template("name", ExtGlobalOptionName)
    @entry(g_read)
    def get_name(self):
        return self.name

    @template("value", ExtGlobalOptionValue)
    @entry(g_read)
    def get_value(self):
        if self.value is None:
            return ""
        return self.value
    
    @template("mtime", ExtDateTime)
    @entry(g_read)
    def get_mtime(self):
        return self.mtime
    
    @template("basic", ExtBoolean)
    @entry(g_read)
    def get_basic_command(self):
        return self.basic
    
    @template("info", ExtOrNull(ExtString))
    @entry(g_read)
    def get_info(self):
        try:
            return self.option_def_manager.get_option_def(self.name).info
        except ExtNoSuchOptionDefError:
            return None
    
    @template("changed_by", ExtString)
    @entry(g_read)
    def get_changed_by(self):
        return self.changed_by
    
    @update("name", ExtString)
    @entry(g_write)
    def set_global_option(self, newname):
        nn = str(newname)
        q = "UPDATE global_options SET name=:newname WHERE id=:id LIMIT 1"
        self.db.put(q, id=self.oid, newname=nn)
        self.manager.approve_config = True
        self.event_manager.add("rename", global_option=self.oid, newstr=newname, authuser=self.function.session.authuser)
        # Do not call self.manager.rename_object(self, nn) here. Global options are identified with a separate ID
        # which is not touched by the setting of a new name.
        
        # print "GlobalOption %s changed Name to %s" % (self.oid, nn)
        
    @update("value", ExtGlobalOptionValue)
    @entry(g_write)
    def set_value(self, newvalue):
        q = "UPDATE global_options SET value=:value WHERE id=:id LIMIT 1"
        self.db.put(q, id=self.oid, value=newvalue)
        self.manager.approve_config = True
        if type(newvalue) is int:
            self.event_manager.add("update", global_option=self.oid, newint=newvalue, authuser=self.function.session.authuser)
        else:
            self.event_manager.add("update", global_option=self.oid, newstr=newvalue, authuser=self.function.session.authuser)


class GlobalOptionManager(AdHocManager):
    name = "global_option_manager"
    manages = GlobalOption

    model_lookup_error = ExtNoSuchGlobalOptionError
    
    def init(self):
        self._model_cache = {}
        
    @classmethod
    def base_query(cls, dq):
        dq.select("r.id", "r.name", "r.value", "r.basic", "r.mtime", "r.changed_by")
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
    
    @search("basic", BooleanMatch, desc="If option is a basic command or not")
    def s_basic(self, dq):
        dq.table("global_options r")
        return "r.basic"
    
    @entry(g_write)
    def create_global_option(self, fun, name, value, basic):
        q = "INSERT INTO global_options (name, value, basic, changed_by) VALUES (:name, :value, :basic, :changed_by)"
        try:
            id = self.db.insert("id", q, name=name, value=value, basic=1 if basic else 0, changed_by=fun.session.authuser)
        except IntegrityError:
            raise ExtGlobalOptionAlreadyExistsError()
        
        self.event_manager.add("create", global_option=name, id=id, authuser=fun.session.authuser)
        self.approve_config = True
        self.approve()
        return id
        
    @entry(g_write)
    def destroy_global_option(self, fun, global_option):
        
        try:
            q = "DELETE FROM global_options WHERE id=:id LIMIT 1"
            self.db.put(q, id=global_option.oid)
        except IntegrityError:
            raise ExtGlobalOptionInUseError()
        self.event_manager.add("destroy", global_option=global_option.name, id=global_option.oid, authuser=fun.session.authuser)
        self.approve_config = True
        self.approve()
