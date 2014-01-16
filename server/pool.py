#!/usr/bin/env python2.6

from rpcc.model import *
from rpcc.exttype import *
from rpcc.function import SessionedFunction
from optionspace import ExtOptionspace, ExtOrNullOptionspace
from rpcc.database import  IntegrityError
from shared_network import ExtNetwork, ExtNetworkName
from option_def import ExtOptionDef, ExtOptionNotSetError, ExtOptions
from rpcc.access import *


class ExtNoSuchPoolError(ExtLookupError):
    desc = "No such pool exists."


class ExtPoolAlreadyExistsError(ExtLookupError):
    desc = "The pool name is already in use"
    

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


class PoolOptionSet(PoolFunBase):
    extname = "pool_option_set"
    desc = "Set an option value on a pool"
    params = [("option_name", ExtOptionDef, "Option name"),
              ("value", ExtString, "Option value")]
    returns = (ExtNull)
    
    def do(self):
        self.pool_manager.set_option(self, self.pool, self.option_name, self.value)
        
        
class PoolLiteralOptionAdd(PoolFunBase):
    extname = "pool_literal_option_add"


class PoolOptionUnset(PoolFunBase):
    extname = "pool_option_unset"
    desc = "Unset an option value on a pool"
    params = [("option_name", ExtOptionDef, "Option name")]
    returns = (ExtNull)
    
    def do(self):
        self.pool_manager.unset_option(self, self.pool, self.option_name)


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
        self.info = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)

    @template("pool", ExtPool)
    def get_pool(self):
        return self

    @template("network", ExtNetworkName)
    def get_network(self):
        return self.network
    
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
        q = "SELECT name, value FROM pool_options WHERE `for`=:id"
        ret = {}
        res = self.db.get_all(q, id=self.oid)
        for opt in res:
            ret[opt[0]] = opt[1]
        return ret
    
    @update("pool", ExtString)
    @entry(AuthRequiredGuard)
    def set_pool(self, pool_name):
        nn = str(pool_name)
        q = "UPDATE pools SET poolname=:value WHERE poolname=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=nn)
        self.db.commit()
        print "Pool %s changed Name to %s" % (self.oid, nn)
        self.manager.rename_pool(self, nn)
        
    @update("info", ExtString)
    @entry(AuthRequiredGuard)
    def set_info(self, value):
        q = "UPDATE pools SET info=:value WHERE poolname=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=value)
        self.db.commit()
        print "Pool %s changed Info to %s" % (self.oid, value)
    
    @update("network", ExtString)
    @entry(AuthRequiredGuard)
    def set_network(self, value):
        q = "UPDATE pools SET network=:value WHERE poolname=:name"
        self.db.put(q, name=self.oid, value=value)
        self.db.commit()
        
    @update("optionspace", ExtOrNullOptionspace)
    @entry(AuthRequiredGuard)
    def set_optionspace(self, value):
        q = "UPDATE pooles SET optionspace=:value WHERE poolname=:name"
        self.db.put(q, name=self.oid, value=value)
        self.db.commit()


class PoolManager(Manager):
    name = "pool_manager"
    manages = Pool

    model_lookup_error = ExtNoSuchPoolError

    def init(self):
        self._model_cache = {}
        
    def base_query(self, dq):
        dq.select("g.poolname", "g.network", "g.optionspace",
                  "g.info", "g.mtime", "g.changed_by")
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
    
    @entry(AuthRequiredGuard)
    def create_pool(self, fun, pool_name, network, info, options):
        if options == None:
            options = {}
        optionspace = options.get("optionspace", None)
            
        q = """INSERT INTO pools (poolname, network, optionspace, info, changed_by) 
               VALUES (:pool_name, :network, :optionspace, :info, :changed_by)"""
        try:
            self.db.insert("id", q, pool_name=pool_name, network=network.oid, optionspace=optionspace,
                       info=info, changed_by=fun.session.authuser)
            print "Pool created, name=", pool_name
            self.db.commit()
        except IntegrityError, e:
            raise ExtPoolAlreadyExistsError()
    
    @entry(AuthRequiredGuard)
    def destroy_pool(self, fun, pool):
        q = "DELETE FROM pools WHERE poolname=:poolname LIMIT 1"
        self.db.put(q, poolname=pool.oid)
        print "Pool destroyed, name=", pool.oid
        self.db.commit()
        
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