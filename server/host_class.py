#!/usr/bin/env python2.6

from rpcc.model import *
from rpcc.exttype import *
from rpcc.function import SessionedFunction
from optionspace import ExtOptionspace, ExtOrNullOptionspace
from rpcc.database import  IntegrityError
from option_def import ExtOptionDef, ExtOptionNotSetError, ExtOptions
from rpcc.access import *


class ExtNoSuchHostClassError(ExtLookupError):
    desc = "No such host_class exists."
    
    
class ExtHostClassAlreadyExistsError(ExtLookupError):
    desc = "The host class name already exists"

    
class ExtHostClassInUseError(ExtValueError):
    desc = "The host class is referred to by other objects. It cannot be destroyed"    


class ExtHostClassName(ExtString):
    name = "host_class-name"
    desc = "Name of a host_class"
    regexp = "^[-a-zA-Z0-9_]+$"
    maxlen = 64


class ExtHostClass(ExtHostClassName):
    name = "host_class"
    desc = "A host_class instance"

    def lookup(self, fun, cval):
        return fun.host_class_manager.get_host_class(cval)

    def output(self, fun, obj):
        return obj.oid
    
    
class ExtHostClassCreateOptions(ExtStruct):
    name = "host_class_create_options"
    desc = "Optional parameters when creating a host_class"
    
    optional = {
                "optionspace": (ExtOptionspace, "Whether the host_class should declare an option space"),
                }
    
    
class ExtHostClassVendorClassID(ExtOrNull):
    name = "host_class_vendor_class_id"
    desc = "An option record, or null"
    typ = ExtString


class HostClassFunBase(SessionedFunction):  
    params = [("host_class", ExtHostClass, "HostClass name")]
    
    
class HostClassCreate(SessionedFunction):
    extname = "host_class_create"
    params = [("host_class_name", ExtHostClassName, "Name of DHCP host_class to create"),
              ("vendor_class_id", ExtHostClassVendorClassID, "Vendor class ID"),
              ("info", ExtString, "HostClass description"),
              ("options", ExtHostClassCreateOptions, "Create options")]
    desc = "Creates a host_class"
    returns = (ExtNull)

    def do(self):
        self.host_class_manager.create_host_class(self, self.host_class_name, self.vendor_class_id, self.info, self.options)


class HostClassDestroy(SessionedFunction):
    extname = "host_class_destroy"
    params = [("host_class", ExtHostClass, "HostClass to destroy")]
    desc = "Destroys a DHCP host_class"
    returns = (ExtNull)

    def do(self):
        self.host_class_manager.destroy_host_class(self, self.host_class)


class HostClassOptionSet(HostClassFunBase):
    extname = "host_class_option_set"
    desc = "Set an option value on a host_class"
    params = [("option_name", ExtOptionDef, "Option name"),
              ("value", ExtString, "Option value")]
    returns = (ExtNull)
    
    def do(self):
        self.host_class_manager.set_option(self, self.host_class, self.option_name, self.value)


class HostClassOptionUnset(HostClassFunBase):
    extname = "host_class_option_unset"
    desc = "Unset an option value on a host_class"
    params = [("option_name", ExtOptionDef, "Option name")]
    returns = (ExtNull)
    
    def do(self):
        self.host_class_manager.unset_option(self, self.host_class, self.option_name)


class HostClass(Model):
    name = "host_class"
    exttype = ExtHostClass
    id_type = unicode

    def init(self, *args, **kwargs):
        a = list(args)
        #print "HostClass.init", a
        self.oid = a.pop(0)
        self.vendor_class_id = a.pop(0)
        self.optionspace = a.pop(0)
        self.info = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)

    @template("host_class", ExtHostClass)
    def get_host_class(self):
        return self

    @template("vendor_class_id", ExtHostClassVendorClassID)
    def get_vendor_class_id(self):
        return self.vendor_class_id
    
    @template("optionspace", ExtOrNullOptionspace)
    def get_optionspace(self):
        return self.optionspace

    @template("info", ExtString)
    def get_info(self):
        return self.info
    
    @template("mtime", ExtDateTime)
    def get_mtime(self):
        return self.mtime
    
    @template("changed_by", ExtString)
    def get_changed_by(self):
        return self.changed_by
    
    @template("options", ExtOptions)
    def get_options(self):
        q = "SELECT name, value FROM class_options WHERE `for`=:id"
        ret = {}
        res = self.db.get_all(q, id=self.oid)
        for opt in res:
            ret[opt[0]] = opt[1]
        return ret
    
    @update("host_class", ExtString)
    @entry(AuthRequiredGuard)
    def set_host_class(self, host_class_name):
        nn = str(host_class_name)
        q = "UPDATE classes SET classname=:value WHERE classname=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=nn)
        
        print "HostClass %s changed Name to %s" % (self.oid, nn)
        self.manager.rename_host_class(self, nn)
        
    @update("info", ExtString)
    @entry(AuthRequiredGuard)
    def set_info(self, value):
        q = "UPDATE classes SET info=:value WHERE classname=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=value)
        
        print "HostClass %s changed Info to %s" % (self.oid, value)
    
    @update("vendor_class_id", ExtString)
    @entry(AuthRequiredGuard)
    def set_vendor_class_id(self, value):
        q = "UPDATE classes SET vendor_class_id=:value WHERE classname=:name"
        self.db.put(q, name=self.oid, value=value)
        
        
    @update("optionspace", ExtOrNullOptionspace)
    @entry(AuthRequiredGuard)
    def set_optionspace(self, value):
        q = "UPDATE host_classes SET optionspace=:value WHERE classname=:name"
        self.db.put(q, name=self.oid, value=value)
        


class HostClassManager(Manager):
    name = "host_class_manager"
    manages = HostClass

    model_lookup_error = ExtNoSuchHostClassError

    def init(self):
        self._model_cache = {}
        
    def base_query(self, dq):
        dq.select("g.classname", "g.vendor_class_id", "g.optionspace",
                  "g.info", "g.mtime", "g.changed_by")
        dq.table("classes g")
        return dq

    def get_host_class(self, host_class_name):
        return self.model(host_class_name)

    def search_select(self, dq):
        dq.table("classes g")
        dq.select("g.classname")
    
    @search("host_class", StringMatch)
    def s_host_class(self, dq):
        dq.table("classes g")
        return "g.classname"
    
    @search("vendor_class_id", StringMatch)
    def s_vendor_class_id(self, dq):
        dq.table("classes g")
        return "g.vendor_class_id"
    
    @entry(AuthRequiredGuard)
    def create_host_class(self, fun, host_class_name, vendor_class_id, info, options):
        if options == None:
            options = {}
        optionspace = options.get("optionspace", None)
            
        q = """INSERT INTO classes (classname, vendor_class_id, optionspace, info, changed_by) 
               VALUES (:host_class_name, :vendor_class_id, :optionspace, :info, :changed_by)"""
        try:
            self.db.insert("id", q, host_class_name=host_class_name, vendor_class_id=vendor_class_id, optionspace=optionspace,
                       info=info, changed_by=fun.session.authuser)
            print "HostClass created, name=", host_class_name
            
        except IntegrityError, e:
            raise ExtHostClassAlreadyExistsError()
        
    @entry(AuthRequiredGuard)
    def destroy_host_class(self, fun, host_class):
        q = "DELETE FROM classes WHERE classname=:classname LIMIT 1"
        try:
            self.db.put(q, classname=host_class.oid)
        except IntegrityError:
            raise ExtHostClassInUseError()
        print "HostClass destroyed, name=", host_class.oid
        
        
    def rename_host_class(self, obj, newname):
        oid = obj.oid
        obj.oid = newname
        del(self._model_cache[oid])
        self._model_cache[newname] = obj
            
    @entry(AuthRequiredGuard)
    def set_option(self, fun, host_class, option, value):
        q = """INSERT INTO class_options (`for`, name, value, changed_by) VALUES (:id, :name, :value, :changed_by)
               ON DUPLICATE KEY UPDATE value=:value"""
        self.db.put(q, id=host_class.oid, name=option.oid, value=value, changed_by=fun.session.authuser)
        
    @entry(AuthRequiredGuard)
    def unset_option(self, fun, host_class, option):
        q = """DELETE FROM class_options WHERE `for`=:id AND name=:name"""
        if not self.db.put(q, id=host_class.oid, name=option.oid):
            raise ExtOptionNotSetError()
