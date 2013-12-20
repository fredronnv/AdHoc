#!/usr/bin/env python2.6

from rpcc.model import *
from rpcc.exttype import *
from rpcc.function import SessionedFunction
from optionspace import ExtOptionspace, ExtOrNullOptionspace
from rpcc.database import  IntegrityError


class ExtNoSuchHostClassError(ExtLookupError):
    desc = "No such host_class exists."


class ExtHostClassError(ExtValueError):
    desc = "The host_class name is invalid or in use"


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
    
    @update("host_class", ExtString)
    def set_host_class(self, host_class_name):
        nn = str(host_class_name)
        q = "UPDATE classes SET classname=:value WHERE classname=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=nn)
        self.db.commit()
        print "HostClass %s changed Name to %s" % (self.oid, nn)
        self.manager.rename_host_class(self, nn)
        
    @update("info", ExtString)
    def set_info(self, value):
        q = "UPDATE classes SET info=:value WHERE classname=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=value)
        self.db.commit()
        print "HostClass %s changed Info to %s" % (self.oid, value)
    
    @update("vendor_class_id", ExtString)
    def set_vendor_class_id(self, value):
        q = "UPDATE classes SET vendor_class_id=:value WHERE classname=:name"
        self.db.put(q, name=self.oid, value=value)
        self.db.commit()
        
    @update("optionspace", ExtOrNullOptionspace)
    def set_optionspace(self, value):
        q = "UPDATE host_classes SET optionspace=:value WHERE classname=:name"
        self.db.put(q, name=self.oid, value=value)
        self.db.commit()


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
            self.db.commit()
        except IntegrityError, e:
            print "SKAPELSEFEL A:",e
            raise ExtHostClassError("The host_class name is already in use")
        except Exception, e:
            print "SKAPELSEFEL:",e
            raise
        
    def destroy_host_class(self, fun, host_class):
        q = "DELETE FROM classes WHERE classname=:classname LIMIT 1"
        self.db.put(q, classname=host_class.oid)
        print "HostClass destroyed, name=", host_class.oid
        self.db.commit()
        
    def rename_host_class(self, obj, newname):
        oid = obj.oid
        obj.oid = newname
        del(self._model_cache[oid])
        self._model_cache[newname] = obj
