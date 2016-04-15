#!/usr/bin/env python2.6

# $Id$

from rpcc import *
from optionset import *
from option_def import *
#from util import ExtLiteralOptionString

g_write = AnyGrants(AllowUserWithPriv("write_all_host_classes"), AdHocSuperuserGuard)


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


class ExtHostClassList(ExtList):
    name = "host_class-list"
    desc = "List of classes"
    typ = ExtHostClassName


class ExtHostClass(ExtHostClassName):
    name = "host_class"
    desc = "A host_class instance"

    def lookup(self, fun, cval):
        return fun.host_class_manager.get_host_class(cval)

    def output(self, fun, obj):
        return obj.oid
    
   
class ExtHostClassCreateOptions(ExtStruct):
    name = "host_class-create-options"
    desc = "Optional parameters when creating a host_class"
    
    optional = {"optionspace": (ExtOptionspace, "Whether the host_class should declare an option space")}
    
    
class ExtHostClassVendorClassID(ExtOrNull):
    name = "host_class-vendor-class-id"
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


class HostClassLiteralOptionAdd(HostClassFunBase):
    extname = "host_class_literal_option_add"
    desc = "Add a literal option to a host_class"
    returns = (ExtInteger, "ID of added literal option")
    params = [("option_text", ExtLiteralOptionString, "Text of literal option")]
    
    def do(self):
        return self.host_class_manager.add_literal_option(self, self.host_class, self.option_text)
     

class HostClassLiteralOptionDestroy(HostClassFunBase):
    extname = "host_class_literal_option_destroy"
    desc = "Destroy a literal option from a host_class"
    returns = (ExtNull)
    params = [("option_id", ExtInteger, "ID of literal option to destroy")]
    
    def do(self):
        return self.host_class_manager.destroy_literal_option(self, self.host_class, self.option_id)     
    

class HostClassOptionsUpdate(HostClassFunBase):
    extname = "host_class_option_update"
    desc = "Update option value(s) on a host_class"
    returns = (ExtNull)
    
    @classmethod
    def get_parameters(cls):
        pars = super(HostClassOptionsUpdate, cls).get_parameters()
        ptype = Optionset._update_type(0)
        ptype.name = "host_class-" + ptype.name
        pars.append(("updates", ptype, "Fields and updates"))
        return pars
    
    def do(self):
        self.host_class_manager.update_options(self, self.host_class, self.updates)


class HostClass(AdHocModel):
    name = "host_class"
    exttype = ExtHostClass
    id_type = unicode

    def init(self, *args, **kwargs):
        a = list(args)
        # print "HostClass.init", a
        self.oid = a.pop(0)
        self.vendor_class_id = a.pop(0)
        self.optionspace = a.pop(0)
        self.info = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)
        self.optionset = a.pop(0)

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
    
    @template("options", ExtOptionKeyList, desc="List of options defined for this class")
    def list_options(self):
        return self.get_optionset().list_options()
    
    @template("optionset", ExtOptionset, model=Optionset)
    def get_optionset(self):
        return self.optionset_manager.get_optionset(self.optionset)
    
    @template("literal_options", ExtLiteralOptionList, desc="List of literal options defined for this class")
    def get_literal_options(self):
        q = "SELECT value, changed_by, id FROM class_literal_options WHERE `for`= :host_class"
        ret = []
        for (value, changed_by, id) in self.db.get(q, host_class=self.oid):
            d = {"value": value,
                 "changed_by": changed_by,
                 "id": id}
            ret.append(d)
        return ret
    
    @update("host_class", ExtString)
    @entry(g_write)
    def set_host_class(self, host_class_name):
        nn = str(host_class_name)
        q = "UPDATE classes SET classname=:value WHERE classname=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=nn)
        
        # print "HostClass %s changed Name to %s" % (self.oid, nn)
        self.manager.rename_object(self, nn)
        self.event_manager.add("rename", host_class=self.oid, newstr=nn, authuser=self.function.session.authuser)
        
    @update("info", ExtString)
    @entry(g_write)
    def set_info(self, value):
        q = "UPDATE classes SET info=:value WHERE classname=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update", host_class=self.oid, info=value, authuser=self.function.session.authuser)
        
        # print "HostClass %s changed Info to %s" % (self.oid, value)
    
    @update("vendor_class_id", ExtString)
    @entry(g_write)
    def set_vendor_class_id(self, value):
        q = "UPDATE classes SET vendor_class_id=:value WHERE classname=:name"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update", host_class=self.oid, vendor_class_id=value, authuser=self.function.session.authuser)
             
    @update("optionspace", ExtOrNullOptionspace)
    @entry(g_write)
    def set_optionspace(self, value):
        q = "UPDATE host_classes SET optionspace=:value WHERE classname=:name"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update", host_class=self.oid, optionspace=value, authuser=self.function.session.authuser)
        

class HostClassManager(AdHocManager):
    name = "host_class_manager"
    manages = HostClass

    model_lookup_error = ExtNoSuchHostClassError

    def init(self):
        self._model_cache = {}
        
    @classmethod
    def base_query(cls, dq):
        dq.select("g.classname", "g.vendor_class_id", "g.optionspace",
                  "g.info", "g.mtime", "g.changed_by", "g.optionset")
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
    
    @search("vendor_class_id", NullableStringMatch)
    def s_vendor_class_id(self, dq):
        dq.table("classes g")
        return "g.vendor_class_id"
    
    @search("info", NullableStringMatch)
    def s_info(self, dq):
        dq.table("classes g")
        return "g.info"
    
    @search("optionset", IntegerMatch, desc="Server internal option set number")
    def s_optionset(self, dq):
        dq.table("classes g")
        return "g.optionset"
    
    # Note: This seems to do the trick I want, but I don't understand why...
    @search("granted_for", StringMatch)
    def s_granted_for(self, q):
        q.table("pool_class_map pcm")
        q.where("g.classname = pcm.classname")
        return "pcm.poolname"
    
    @entry(g_write)
    def create_host_class(self, fun, host_class_name, vendor_class_id, info, options):
        if options is None:
            options = {}
        optionspace = options.get("optionspace", None)
        
        optionset = self.optionset_manager.create_optionset(fun)
        
        q = """INSERT INTO classes (classname, vendor_class_id, optionspace, info, changed_by, optionset) 
               VALUES (:host_class_name, :vendor_class_id, :optionspace, :info, :changed_by, :optionset)"""
        try:
            self.db.insert("id", q, host_class_name=host_class_name, vendor_class_id=vendor_class_id, optionspace=optionspace,
                           info=info, changed_by=fun.session.authuser, optionset=optionset)
            # print "HostClass created, name=", host_class_name
            
        except IntegrityError, e:
            raise ExtHostClassAlreadyExistsError()
        self.event_manager.add("create", host_class=host_class_name, 
                               vendor_class_id=vendor_class_id, 
                               optionspace=optionspace,
                               authuser=fun.session.authuser,
                               optionset=optionset,
                               info=info)
        
    @entry(g_write)
    def destroy_host_class(self, fun, host_class):
        
        host_class.get_optionset().destroy()
        
        try:
            q = "DELETE FROM classes WHERE classname=:classname LIMIT 1"
            self.db.put(q, classname=host_class.oid)
        except IntegrityError:
            raise ExtHostClassInUseError()
        
        q = "DELETE FROM class_literal_options WHERE `for`=:host_classname"
        self.db.put(q, host_classname=host_class.oid)
        
        self.event_manager.add("destroy", host_class=host_class.oid, authuser=fun.session.authuser)
        # print "HostClass destroyed, name=", host_class.oid
            
    @entry(g_write)
    def set_option(self, fun, host_class, option, value):
        q = """INSERT INTO class_options (`for`, name, value, changed_by) VALUES (:id, :name, :value, :changed_by)
               ON DUPLICATE KEY UPDATE value=:value"""
        self.db.put(q, id=host_class.oid, name=option.oid, value=value, changed_by=fun.session.authuser)
        
    @entry(g_write)
    def unset_option(self, fun, host_class, option):
        q = """DELETE FROM class_options WHERE `for`=:id AND name=:name"""
        if not self.db.put(q, id=host_class.oid, name=option.oid):
            raise ExtOptionNotSetError()
   
    @entry(g_write_literal_option)
    def add_literal_option(self, fun, host_class, option_text):
        q = "INSERT INTO class_literal_options (`for`, value, changed_by) VALUES (:host_classname, :value, :changed_by)"
        id = self.db.insert("id", q, host_classname=host_class.oid, value=option_text, changed_by=fun.session.authuser)
        self.approve_config = True
        self.approve()
        self.event_manager.add("create", host_class=host_class.oid, literal_option_id=id, literal_option_value=unicode(option_text), authuser=fun.session.authuser)
        return id
    
    @entry(g_write_literal_option)
    def destroy_literal_option(self, fun, host_class, id):
        q = "DELETE FROM class_literal_options WHERE `for`=:host_classname AND id=:id LIMIT 1"
        self.db.put(q, host_classname=host_class.oid, id=id)
        self.event_manager.add("destroy", host_class=host_class.oid, literal_option_id=id, authuser=fun.session.authuser)
        
    @entry(g_write)
    def update_options(self, fun, host_class, updates):
        omgr = fun.optionset_manager
        optionset = omgr.get_optionset(host_class.optionset)
        for (key, value) in updates.iteritems():
            optionset.set_option_by_name(key, value)
            self.event_manager.add("update", host_class=host_class.oid, option=key, option_value=unicode(value), authuser=fun.session.authuser)
