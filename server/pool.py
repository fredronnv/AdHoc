#!/usr/bin/env python2.6

from rpcc import *
from shared_network import ExtNetwork, ExtNetworkName
from optionset import *
from option_def import *
from host import ExtHostList, ExtHost
from group import ExtGroupList, ExtGroup
from host_class import ExtHostClassList, ExtHostClass


g_write = AnyGrants(AllowUserWithPriv("write_all_pools"), AdHocSuperuserGuard)
g_admin = AnyGrants(g_write, AllowUserWithPriv("admin_all_pools"), AdHocSuperuserGuard)

class ExtNoSuchPoolError(ExtLookupError):
    desc = "No such pool exists."


class ExtPoolAlreadyExistsError(ExtLookupError):
    desc = "The pool name is already in use"
    
    
class ExtPoolInUseError(ExtValueError):
    desc = "The pool is referred to by other objects. It cannot be destroyed"    


class ExtHostAlreadyAllowedError(ExtValueError):
    desc = "The host is already allowed into the pool"


class ExtGroupAlreadyAllowedError(ExtValueError):
    desc = "The group is already allowed into the pool"


class ExtHostClassAlreadyAllowedError(ExtValueError):
    desc = "The host class is already allowed into the pool"
    
    
class ExtHostNotAllowedInPoolError(ExtValueError):
    desc = "The host is not currently allowed into the pool"
    
    
class ExtGroupNotAllowedInPoolError(ExtValueError):
    desc = "The group is not currently allowed into the pool"
    
    
class ExtHostClassNotAllowedInPoolError(ExtValueError):
    desc = "The host class is not currently allowed into the pool"


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
    desc = "Add a literal option to a pool"
    returns =(ExtInteger, "ID of added literal option")
    params = [("option_text", ExtString, "Text of literal option")]
    
    def do(self):
        return self.pool_manager.add_literal_option(self, self.pool, self.option_text)
    
    
class PoolLiteralOptionDestroy(PoolFunBase):
    extname = "pool_literal_option_destroy"
    desc = "Destroy a literal option from a pool"
    returns =(ExtNull)
    params = [("option_id", ExtInteger, "ID of literal option to destroy")]
    
    def do(self):
        return self.pool_manager.destroy_literal_option(self, self.pool, self.option_id)
        
    
class PoolAllowHost(PoolFunBase):
    extname = "pool_allow_host"
    desc = "Allows a host to use a pool"
    params = [("host", ExtHost, "Host to be allowed into the pool")]
    returns = (ExtNull)
    
    def do(self):
        self.pool_manager.allow_host(self, self.pool, self.host)
        
        
class PoolAllowGroup(PoolFunBase):
    extname = "pool_allow_group"
    desc = "Allows a group of hosts to use a pool"
    params = [("group", ExtGroup, "Group to be allowed into the pool")]
    returns = (ExtNull)
    
    def do(self):
        self.pool_manager.allow_group(self, self.pool, self.group)


class PoolAllowHostClass(PoolFunBase):
    extname = "pool_allow_host_class"
    desc = "Allows a host class to use a pool"
    params = [("host_class", ExtHostClass, "Host class to be allowed into the pool")]
    returns = (ExtNull)
    
    def do(self):
        self.pool_manager.allow_host_class(self, self.pool, self.host_class)
        
        
class PoolDisallowHost(PoolFunBase):
    extname = "pool_disallow_host"
    desc = "Disallows a host to use a pool"
    params = [("host", ExtHost, "Host to be disallowed from the pool")]
    returns = (ExtNull)
    
    def do(self):
        self.pool_manager.disallow_host(self.pool, self.host)

        
class PoolDisallowGroup(PoolFunBase):
    extname = "pool_disallow_group"
    desc = "Disallows a group of hosts from using a pool"
    params = [("group", ExtGroup, "Group to be disallowed from the pool")]
    returns = (ExtNull)
    
    def do(self):
        self.pool_manager.disallow_group(self.pool, self.group)


class PoolDisallowHostClass(PoolFunBase):
    extname = "pool_disallow_host_class"
    desc = "Disallows a host class to use a pool"
    params = [("host_class", ExtHostClass, "Host class to be disallowed from the pool")]
    returns = (ExtNull)
    
    def do(self):
        self.pool_manager.disallow_host_class(self.pool, self.host_class)


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
        self.pool_manager.update_options(self, self.pool, self.updates)


class Pool(AdHocModel):
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
    
    @template("options", ExtOptionKeyList, desc="List of options defined for this pool")
    def list_options(self):
        return self.get_optionset().list_options()
    
    @template("optionset", ExtOptionset, model=Optionset)
    def get_optionset(self):
        return self.optionset_manager.get_optionset(self.optionset)
    
    @template("literal_options", ExtLiteralOptionList, desc="List of literal options defined for this pool")
    def get_literal_options(self):
        q = "SELECT value, changed_by, id FROM pool_literal_options WHERE `for`= :pool"
        ret = []
        for (value, changed_by, id) in self.db.get(q, pool=self.oid):
            d = {"value":value,
                 "changed_by":changed_by,
                 "id": id}
            ret.append(d)
        return ret
        
    @template("allowed_hosts", ExtHostList)
    def get_allowed_hosts(self):
        q = "SELECT hostname FROM pool_host_map WHERE poolname=:pool"
        hosts = self.db.get(q, pool=self.oid)
        return [x[0] for x in hosts]
    
    @template("allowed_groups", ExtGroupList)
    def get_allowed_groups(self):
        q = "SELECT groupname FROM pool_group_map WHERE poolname=:pool"
        groups = self.db.get(q, pool=self.oid)
        return [x[0] for x in groups]
    
    @template("allowed_host_classes", ExtHostClassList)
    def get_allowed_host_classes(self):
        q = "SELECT classname FROM pool_class_map WHERE poolname=:pool"
        classes = self.db.get(q, pool=self.oid)
        return [x[0] for x in classes]
    
    @update("pool", ExtString)
    @entry(g_rename)  
    def set_pool(self, pool_name):
        nn = str(pool_name)
        q = "UPDATE pools SET poolname=:value WHERE poolname=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=nn)
        
        #print "Pool %s changed Name to %s" % (self.oid, nn)
        self.manager.rename_object(self, nn)
        self.event_manager.add("rename",  pool=self.oid, newstr=nn, authuser=self.function.session.authuser)
   
    @update("info", ExtString)
    @entry(g_write)     
    def set_info(self, value):
        q = "UPDATE pools SET info=:value WHERE poolname=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update",  pool=self.oid, info=value, authuser=self.function.session.authuser)
        
        #print "Pool %s changed Info to %s" % (self.oid, value)
  
    @update("network", ExtString)
    @entry(g_write)  
    def set_network(self, value):
        q = "UPDATE pools SET network=:value WHERE poolname=:name"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update",  pool=self.oid, network=value, authuser=self.function.session.authuser)
 
    @update("optionspace", ExtOrNullOptionspace)
    @entry(g_write)       
    def set_optionspace(self, value):
        q = "UPDATE pools SET optionspace=:value WHERE poolname=:name"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update",  pool=self.oid, optionspace=value, authuser=self.function.session.authuser)
 
    @update("max_lease_time", ExtInteger)
    @entry(g_write)       
    def set_max_lease_time(self, value):
        q = "UPDATE pools SET max_lease_time=:value WHERE poolname=:name"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("rename",  pool=self.oid, max_lease_time=value, authuser=self.function.session.authuser)
        

class PoolManager(AdHocManager):
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
    
    @entry(g_write)
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
            self.event_manager.add("create",pool=pool_name, parent_object=network.oid, 
                           optionspace=optionspace, max_lease_time=max_lease_time,
                           info=info, authuser=fun.session.authuser, optionset=optionset)
        except IntegrityError, e:
            raise ExtPoolAlreadyExistsError()
    
    @entry(g_write)
    def destroy_pool(self, fun, pool):
        
        pool.get_optionset().destroy()
        
        try:
            q = "DELETE FROM pools WHERE poolname=:poolname LIMIT 1"
            self.db.put(q, poolname=pool.oid)
        except IntegrityError:
            raise ExtPoolInUseError()
        
        self.event_manager.add("destroy", pool=pool.oid)
        #print "Pool destroyed, name=", pool.oid
    
    @entry(g_write)   
    def set_option(self, fun, pool, option, value):
        q = """INSERT INTO pool_options (`for`, name, value, changed_by) VALUES (:id, :name, :value, :changed_by)
               ON DUPLICATE KEY UPDATE value=:value"""
        self.db.put(q, id=pool.oid, name=option.oid, value=value, changed_by=fun.session.authuser)
    
    @entry(g_write)    
    def unset_option(self, fun, pool, option):
        q = """DELETE FROM pool_options WHERE `for`=:id AND name=:name"""
        if not self.db.put(q, id=pool.oid, name=option.oid):
            raise ExtOptionNotSetError()
        
    @entry(g_admin)
    def allow_host(self, fun, pool, host):
        q = """INSERT INTO pool_host_map (poolname, hostname, changed_by) 
            VALUES (:poolname, :hostname, :changed_by)"""
        try:
            self.db.put(q, poolname=pool.oid, hostname=host.oid, changed_by=fun.session.authuser)
        except IntegrityError:
            raise ExtHostAlreadyAllowedError()
    
    @entry(g_admin)
    def allow_group(self, fun, pool, group):
        q = """INSERT INTO pool_group_map (poolname, groupname, changed_by) 
            VALUES (:poolname, :groupname, :changed_by)"""
        try:
            self.db.put(q, poolname=pool.oid, groupname=group.oid, changed_by=fun.session.authuser)
        except IntegrityError:
            raise ExtGroupAlreadyAllowedError()
        
    @entry(g_admin)
    def allow_host_class(self, fun, pool, host_class):
        q = """INSERT INTO pool_class_map (poolname, classname, changed_by) 
            VALUES (:poolname, :classname, :changed_by)"""
        try:
            self.db.put(q, poolname=pool.oid, classname=host_class.oid, changed_by=fun.session.authuser)
        except IntegrityError:
            raise ExtHostClassAlreadyAllowedError()
        
    @entry(g_admin)
    def disallow_host(self, pool, host):
        q0 = "SELECT poolname FROM pool_host_map WHERE poolname=:poolname AND hostname=:hostname"
        pools = self.db.get(q0, poolname=pool.oid, hostname=host.oid)
        if len(pools) == 0:
            raise ExtHostNotAllowedInPoolError()
        q = """DELETE FROM pool_host_map WHERE poolname=:poolname AND hostname=:hostname""" 
        self.db.put(q, poolname=pool.oid, hostname=host.oid)
        
    @entry(g_admin)
    def disallow_group(self, pool, group):
        q0 = "SELECT poolname FROM pool_group_map WHERE poolname=:poolname AND groupname=:groupname"
        pools = self.db.get(q0, poolname=pool.oid, groupname=group.oid)
        if len(pools) == 0:
            raise ExtGroupNotAllowedInPoolError()
        q = """DELETE FROM pool_group_map WHERE poolname=:poolname AND groupname=:groupname""" 
        self.db.put(q, poolname=pool.oid, groupname=group.oid)
        
    @entry(g_admin)
    def disallow_host_class(self, pool, host_class):
        q0 = "SELECT poolname FROM pool_class_map WHERE poolname=:poolname AND classname=:classname"
        pools = self.db.get(q0, poolname=pool.oid, classname=host_class.oid)
        if len(pools) == 0:
            raise ExtHostClassNotAllowedInPoolError()
        q = """DELETE FROM pool_class_map WHERE poolname=:poolname AND classname=:classname""" 
        self.db.put(q, poolname=pool.oid, classname=host_class.oid)
    
    @entry(g_write_literal_option)
    def add_literal_option(self, fun, pool, option_text):
        q = "INSERT INTO pool_literal_options (`for`, value, changed_by) VALUES (:poolname, :value, :changed_by)"
        id = self.db.insert("id", q, poolname=pool.oid, value=option_text, changed_by=fun.session.authuser)
        return id
    
    @entry(AdHocSuperuserGuard)
    def destroy_literal_option(self, fun, pool, id):
        q = "DELETE FROM pool_literal_options WHERE `for`=:poolname AND id=:id LIMIT 1"
        self.db.put(q, poolname=pool.oid, id=id)

    @entry(g_write)
    def update_options(self, fun, pool, updates):
        omgr = fun.optionset_manager
        optionset = omgr.get_optionset(pool.optionset)
        for (key, value) in updates.iteritems():
            optionset.set_option_by_name(key, value)