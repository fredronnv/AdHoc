#!/usr/bin/env python2.6

from rpcc.model import *
from rpcc.exttype import *
from rpcc.function import SessionedFunction
from optionspace import ExtOptionspace, ExtOrNullOptionspace
from rpcc.database import  IntegrityError
from shared_network import ExtNetwork, ExtNetworkName
from option_def import ExtOptionDef, ExtOptionNotSetError, ExtOptions
from rpcc.access import *
from optionset import *
from option_def import *


class ExtNoSuchPoolError(ExtLookupError):
    desc = "No such pool exists."


class ExtPoolAlreadyExistsError(ExtLookupError):
    desc = "The pool name is already in use"
    
    
class ExtPoolInUseError(ExtValueError):
    desc = "The pool is referred to by other objects. It cannot be destroyed"    


class ExtPoolName(ExtString):
    name = "pool-name"
    desc = "Name of a pool"
    regexp = "^[-a-zA-Z0-9_]+$"
    maxlen = 64


class ExtPool(ExtPoolName):
    name = "pool"
    desc = "A pool instance"

    def lookup(self, fun, cval):
        return fun.pool_manager.get_pool(cval)

    def output(self, fun, obj):
        return obj.oid
    
    
class ExtPoolCreateOptions(ExtStruct):
    name = "pool_create_options"
    desc = "Optional parameters when creating a pool"
    
    optional = {
                "optionspace": (ExtOptionspace, "Whether the pool should declare an option space"),
                "max_lease_time": (ExtInteger, "Maximum lease time for the pool. Default 600 seconds")
                }
    
    
class PoolFunBase(SessionedFunction):  
    params = [("pool", ExtPool, "Pool")]
    
    
class PoolCreate(SessionedFunction):
    extname = "pool_create"
    params = [("pool_name", ExtPoolName, "Name of DHCP pool to create"),
              ("network", ExtNetwork, "Shared network in which the pool lives"),
              ("info", ExtString, "Pool description"),
              ("options", ExtPoolCreateOptions, "Create options")]
    desc = "Creates a pool"
    returns = (ExtNull)

    def do(self):
        self.pool_manager.create_pool(self, self.pool_name, self.network, self.info, self.options)


class PoolDestroy(PoolFunBase):
    extname = "pool_destroy"
    desc = "Destroys a DHCP pool"
    returns = (ExtNull)

    def do(self):
        self.pool_manager.destroy_pool(self, self.pool)
        
        
class PoolLiteralOptionAdd(PoolFunBase):
    extname = "pool_literal_option_add"


class PoolOptionsUpdate(PoolFunBase):
    extname = "pool_options_update"
    desc = "Update option value(s) on a pool"
    returns = (ExtNull)
    
    @classmethod
    def get_parameters(cls):
        pars = super(PoolOptionsUpdate, cls).get_parameters()
        ptype = Optionset._update_type(0)
        ptype.name = "pool-" + ptype.name
        pars.append(("updates", ptype, "Fields and updates"))
        return pars
    
    def do(self):
        omgr = self.optionset_manager
        optionset = omgr.get_optionset(self.pool.optionset)
        for (key, value) in self.updates.iteritems():
            optionset.set_option_by_name(key, value)


class Pool(Model):
    name = "pool"
    exttype = ExtPool
    id_type = unicode

    def init(self, *args, **kwargs):
        a = list(args)
        #print "Pool.init", a
        self.oid = a.pop(0)
        self.network = a.pop(0)
        self.optionspace = a.pop(0)
        self.max_lease_time = a.pop(0)
        self.info = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)
        self.optionset = a.pop(0)

    @template("pool", ExtPool)
    def get_pool(self):
        return self

    @template("network", ExtNetworkName)
    def get_network(self):
        return self.network
    
    @template("optionspace", ExtOrNullOptionspace)
    def get_optionspace(self):
        return self.optionspace
    
    @template("max_lease_time", ExtInteger)
    def get_max_lease_time(self):
        return self.max_lease_time

    @template("info", ExtString)
    def get_info(self):
        return self.info
    
    @template("mtime", ExtDateTime)
    def get_mtime(self):
        return self.mtime
    
    @template("changed_by", ExtString)
    def get_changed_by(self):
        return self.changed_by
    
    @template("options", ExtOptionKeyList, desc="List of options defined for this host")
    def list_options(self):
        return self.get_optionset().list_options()
    
    @template("optionset", ExtOptionset, model=Optionset)
    def get_optionset(self):
        return self.optionset_manager.get_optionset(self.optionset)
    
    @update("pool", ExtString)
    @entry(AuthRequiredGuard)  
    def set_pool(self, pool_name):
        nn = str(pool_name)
        q = "UPDATE pools SET poolname=:value WHERE poolname=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=nn)
        
        #print "Pool %s changed Name to %s" % (self.oid, nn)
        self.manager.rename_pool(self, nn)
   
    @update("info", ExtString)
    @entry(AuthRequiredGuard)     
    def set_info(self, value):
        q = "UPDATE pools SET info=:value WHERE poolname=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=value)
        
        #print "Pool %s changed Info to %s" % (self.oid, value)
  
    @update("network", ExtString)
    @entry(AuthRequiredGuard)  
    def set_network(self, value):
        q = "UPDATE pools SET network=:value WHERE poolname=:name"
        self.db.put(q, name=self.oid, value=value)
 
    @update("optionspace", ExtOrNullOptionspace)
    @entry(AuthRequiredGuard)       
    def set_optionspace(self, value):
        q = "UPDATE pools SET optionspace=:value WHERE poolname=:name"
        self.db.put(q, name=self.oid, value=value)
 
    @update("max_lease_time", ExtInteger)
    @entry(AuthRequiredGuard)       
    def set_max_lease_time(self, value):
        q = "UPDATE pools SET max_lease_time=:value WHERE poolname=:name"
        self.db.put(q, name=self.oid, value=value)
        

class PoolManager(Manager):
    name = "pool_manager"
    manages = Pool

    model_lookup_error = ExtNoSuchPoolError

    def init(self):
        self._model_cache = {}
        
    def base_query(self, dq):
        dq.select("g.poolname", "g.network", "g.optionspace", "g.max_lease_time",
                  "g.info", "g.mtime", "g.changed_by", "g.optionset")
        dq.table("pools g")
        return dq

    def get_pool(self, pool_name):
        return self.model(pool_name)

    def search_select(self, dq):
        dq.table("pools g")
        dq.select("g.poolname")
    
    @search("pool", StringMatch)
    def s_pool(self, dq):
        dq.table("pools g")
        return "g.poolname"
    
    @search("network", StringMatch)
    def s_network(self, dq):
        dq.table("pools g")
        return "g.network"
    
    @search("info", StringMatch)
    def s_info(self, dq):
        dq.table("pools g")
        return "g.info"
    
    @search("max_lease_time", IntegerMatch)
    def s_max_lease_time(self, dq):
        dq.table("pools g")
        return "g.max_lease_time"
    
    @entry(AuthRequiredGuard)
    def create_pool(self, fun, pool_name, network, info, options):
        if options == None:
            options = {}
        optionspace = options.get("optionspace", None)
        if optionspace:
            optionspace = optionspace.oid
        max_lease_time = options.get("max_lease_time", 600)
        
        optionset = self.optionset_manager.create_optionset()
        
        q = """INSERT INTO pools (poolname, network, optionspace, max_lease_time, info, changed_by, optionset) 
               VALUES (:pool_name, :network, :optionspace, :max_lease_time, :info, :changed_by, :optionset)"""
        try:
            self.db.insert("id", q, pool_name=pool_name, network=network.oid, 
                           optionspace=optionspace, max_lease_time=max_lease_time,
                           info=info, changed_by=fun.session.authuser, optionset=optionset)
            #print "Pool created, name=", pool_name
            
        except IntegrityError, e:
            raise ExtPoolAlreadyExistsError()
    
    @entry(AuthRequiredGuard)
    def destroy_pool(self, fun, pool):
        
        pool.get_optionset().destroy()
        
        try:
            q = "DELETE FROM pools WHERE poolname=:poolname LIMIT 1"
        except IntegrityError:
            raise ExtPoolInUseError()
        self.db.put(q, poolname=pool.oid)
        #print "Pool destroyed, name=", pool.oid
        
    def rename_pool(self, obj, newname):
        oid = obj.oid
        obj.oid = newname
        del(self._model_cache[oid])
        self._model_cache[newname] = obj
    
    @entry(AuthRequiredGuard)   
    def set_option(self, fun, pool, option, value):
        q = """INSERT INTO pool_options (`for`, name, value, changed_by) VALUES (:id, :name, :value, :changed_by)
               ON DUPLICATE KEY UPDATE value=:value"""
        self.db.put(q, id=pool.oid, name=option.oid, value=value, changed_by=fun.session.authuser)
    
    @entry(AuthRequiredGuard)    
    def unset_option(self, fun, pool, option):
        q = """DELETE FROM pool_options WHERE `for`=:id AND name=:name"""
        if not self.db.put(q, id=pool.oid, name=option.oid):
            raise ExtOptionNotSetError()
