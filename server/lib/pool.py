#!/usr/bin/env python2.6

# $Id$

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


class ExtHostAlreadyGrantedError(ExtValueError):
    desc = "The host is already granted into the pool"


class ExtGroupAlreadyGrantedError(ExtValueError):
    desc = "The group is already granted into the pool"


class ExtHostClassAlreadyGrantedError(ExtValueError):
    desc = "The host class is already granted into the pool"
    
    
class ExtHostNotGrantedInPoolError(ExtValueError):
    desc = "The host is not currently granted into the pool"
    
    
class ExtGroupNotGrantedInPoolError(ExtValueError):
    desc = "The group is not currently granted into the pool"
    
    
class ExtHostClassNotGrantedInPoolError(ExtValueError):
    desc = "The host class is not currently granted into the pool"


class ExtPoolIsOpenError(ExtValueError):
    desc = "The pool is open to all hosts. Grants do not apply"
    
    
class ExtPoolHasGrants(ExtValueError):
    desc = "The pool has grants. It may not be opened implicitly"


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
    
    optional = {"optionspace": (ExtOptionspace, "Whether the pool should declare an option space"),
                "max_lease_time": (ExtInteger, "Maximum lease time for the pool. Default 600 seconds"),
                "allow_all_hosts": (ExtBoolean, "Create an open pool, all hosts are allowed to join")
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
    returns = (ExtInteger, "ID of added literal option")
    params = [("option_text", ExtString, "Text of literal option")]
    
    def do(self):
        return self.pool_manager.add_literal_option(self, self.pool, self.option_text)
    
    
class PoolLiteralOptionDestroy(PoolFunBase):
    extname = "pool_literal_option_destroy"
    desc = "Destroy a literal option from a pool"
    returns = (ExtNull)
    params = [("option_id", ExtInteger, "ID of literal option to destroy")]
    
    def do(self):
        return self.pool_manager.destroy_literal_option(self, self.pool, self.option_id)
        
    
class PoolGrantHost(PoolFunBase):
    extname = "pool_grant_host"
    desc = "Grants a host to use a pool"
    params = [("host", ExtHost, "Host to be granted into the pool")]
    returns = (ExtNull)
    
    def do(self):
        self.pool_manager.grant_host(self, self.pool, self.host)
        
        
class PoolGrantGroup(PoolFunBase):
    extname = "pool_grant_group"
    desc = "Grants a group of hosts to use a pool"
    params = [("group", ExtGroup, "Group to be granted into the pool")]
    returns = (ExtNull)
    
    def do(self):
        if self.pool.open:
            raise ExtPoolIsOpenError()
        self.pool_manager.grant_group(self, self.pool, self.group)


class PoolGrantHostClass(PoolFunBase):
    extname = "pool_grant_host_class"
    desc = "Grants a host class to use a pool"
    params = [("host_class", ExtHostClass, "Host class to be granted into the pool")]
    returns = (ExtNull)
    
    def do(self):
        if self.pool.open:
            raise ExtPoolIsOpenError()
        self.pool_manager.grant_host_class(self, self.pool, self.host_class)
        
        
class PoolRevokeHost(PoolFunBase):
    extname = "pool_revoke_host"
    desc = "Revokes access for a host to use a pool"
    params = [("host", ExtHost, "Host to be revoked from the pool")]
    returns = (ExtNull)
    
    def do(self):
        if self.pool.open:
            raise ExtPoolIsOpenError()
        self.pool_manager.revoke_host(self, self.pool, self.host)

        
class PoolRevokeGroup(PoolFunBase):
    extname = "pool_revoke_group"
    desc = "Revokes access for a group of hosts from using a pool"
    params = [("group", ExtGroup, "Group to be revoked from the pool")]
    returns = (ExtNull)
    
    def do(self):
        if self.pool.open:
            raise ExtPoolIsOpenError()
        self.pool_manager.revoke_group(self, self.pool, self.group)


class PoolRevokeHostClass(PoolFunBase):
    extname = "pool_revoke_host_class"
    desc = "Revokes a host class from using a pool"
    params = [("host_class", ExtHostClass, "Host class to be revoked from the pool")]
    returns = (ExtNull)
    
    def do(self):
        if self.pool.open:
            raise ExtPoolIsOpenError()
        self.pool_manager.revoke_host_class(self, self.pool, self.host_class)


class PoolOptionsUpdate(PoolFunBase):
    extname = "pool_option_update"
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
        # print "Pool.init", a
        self.oid = a.pop(0)
        self.network = a.pop(0)
        self.optionspace = a.pop(0)
        self.max_lease_time = a.pop(0)
        self.info = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)
        self.optionset = a.pop(0)
        self.open = a.pop(0)

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
            d = {"value": value,
                 "changed_by": changed_by,
                 "id": id}
            ret.append(d)
        return ret
        
    @template("granted_hosts", ExtHostList)
    def get_granted_hosts(self):
        q = "SELECT hostname FROM pool_host_map WHERE poolname=:pool"
        hosts = self.db.get(q, pool=self.oid)
        return [x[0] for x in hosts]
    
    @template("granted_groups", ExtGroupList)
    def get_granted_groups(self):
        q = "SELECT groupname FROM pool_group_map WHERE poolname=:pool"
        groups = self.db.get(q, pool=self.oid)
        return [x[0] for x in groups]
    
    @template("granted_host_classes", ExtHostClassList)
    def get_granted_host_classes(self):
        q = "SELECT classname FROM pool_class_map WHERE poolname=:pool"
        classes = self.db.get(q, pool=self.oid)
        return [x[0] for x in classes]
    
    @template("open", ExtBoolean)
    def get_open(self):
        return self.open
    
    @update("pool", ExtString)
    @entry(g_rename)  
    def set_pool(self, pool_name):
        nn = str(pool_name)
        q = "UPDATE pools SET poolname=:value WHERE poolname=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=nn)
        
        # print "Pool %s changed Name to %s" % (self.oid, nn)
        self.manager.rename_object(self, nn)
        self.event_manager.add("rename", pool=self.oid, newstr=nn, authuser=self.function.session.authuser)
   
    @update("info", ExtString)
    @entry(g_write)     
    def set_info(self, value):
        q = "UPDATE pools SET info=:value WHERE poolname=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update", pool=self.oid, info=value, authuser=self.function.session.authuser)
        
        # print "Pool %s changed Info to %s" % (self.oid, value)
  
    @update("network", ExtString)
    @entry(g_write)  
    def set_network(self, value):
        q = "UPDATE pools SET network=:value WHERE poolname=:name"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update", pool=self.oid, network=value, authuser=self.function.session.authuser)
 
    @update("optionspace", ExtOrNullOptionspace)
    @entry(g_write)       
    def set_optionspace(self, value):
        q = "UPDATE pools SET optionspace=:value WHERE poolname=:name"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update", pool=self.oid, optionspace=value, authuser=self.function.session.authuser)
 
    @update("max_lease_time", ExtInteger)
    @entry(g_write)       
    def set_max_lease_time(self, value):
        q = "UPDATE pools SET max_lease_time=:value WHERE poolname=:name"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("rename", pool=self.oid, max_lease_time=value, authuser=self.function.session.authuser)
        
    @update("open", ExtBoolean)
    @entry(g_write)       
    def set_open(self, value):
        if self.open == value:
            return  # No change
        if not self.open and self.get_granted_hosts() or self.get_granted_groups() or self.get_granted_host_classes():
                raise ExtPoolHasGrants()
        q = "UPDATE pools SET open=:value WHERE poolname=:name"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update", pool=self.oid, max_lease_time=value, authuser=self.function.session.authuser)
                
                
class PoolManager(AdHocManager):
    name = "pool_manager"
    manages = Pool

    model_lookup_error = ExtNoSuchPoolError

    def init(self):
        self._model_cache = {}
        
    @classmethod
    def base_query(cls, dq):
        dq.select("g.poolname", "g.network", "g.optionspace", "g.max_lease_time",
                  "g.info", "g.mtime", "g.changed_by", "g.optionset", "g.open")
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
        if options is None:
            options = {}
            
        optionspace = options.get("optionspace", None)
        if optionspace:
            optionspace = optionspace.oid
        max_lease_time = options.get("max_lease_time", 600)
        
        open = options.get("allow_all_hosts", False)
        
        optionset = self.optionset_manager.create_optionset()
        
        q = """INSERT INTO pools (poolname, network, optionspace, max_lease_time, info, changed_by, optionset, open) 
               VALUES (:pool_name, :network, :optionspace, :max_lease_time, :info, :changed_by, :optionset. :open)"""
        try:
            self.db.insert("id", q, pool_name=pool_name, network=network.oid, 
                           optionspace=optionspace, max_lease_time=max_lease_time,
                           info=info, changed_by=fun.session.authuser, optionset=optionset,
                           open=open)
            # print "Pool created, name=", pool_name
            self.event_manager.add("create", pool=pool_name, parent_object=network.oid, 
                                   optionspace=optionspace, max_lease_time=max_lease_time,
                                   info=info, authuser=fun.session.authuser, optionset=optionset, open=int(open))
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
        
        self.db.put("DELETE FROM pool_literal_options WHERE `for`=:poolname", poolname=pool.oid)
        self.db.put("DELETE FROM pool_host_map WHERE poolname=:poolname", poolname=pool.oid)
        self.db.put("DELETE FROM pool_group_map WHERE poolname=:poolname", poolname=pool.oid)
        self.db.put("DELETE FROM pool_class_map WHERE poolname=:poolname", poolname=pool.oid)
        self.db.put("DELETE FROM pool_ranges WHERE pool=:poolname", poolname=pool.oid)
        
        self.event_manager.add("destroy", pool=pool.oid)
        # print "Pool destroyed, name=", pool.oid
    
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
    def grant_host(self, fun, pool, host):
        q = """INSERT INTO pool_host_map (poolname, hostname, changed_by) 
            VALUES (:poolname, :hostname, :changed_by)"""
        try:
            self.db.put(q, poolname=pool.oid, hostname=host.oid, changed_by=fun.session.authuser)
        except IntegrityError:
            raise ExtHostAlreadyGrantedError()
        self.event_manager.add("grant_access", pool=pool.oid, host=host.oid, authuser=fun.session.authuser)
    
    @entry(g_admin)
    def grant_group(self, fun, pool, group):
        q = """INSERT INTO pool_group_map (poolname, groupname, changed_by) 
            VALUES (:poolname, :groupname, :changed_by)"""
        try:
            self.db.put(q, poolname=pool.oid, groupname=group.oid, changed_by=fun.session.authuser)
        except IntegrityError:
            raise ExtGroupAlreadyGrantedError()
        self.event_manager.add("grant_access", pool=pool.oid, group=group.oid, authuser=fun.session.authuser)
        
    @entry(g_admin)
    def grant_host_class(self, fun, pool, host_class):
        q = """INSERT INTO pool_class_map (poolname, classname, changed_by) 
            VALUES (:poolname, :classname, :changed_by)"""
        try:
            self.db.put(q, poolname=pool.oid, classname=host_class.oid, changed_by=fun.session.authuser)
        except IntegrityError:
            raise ExtHostClassAlreadyGrantedError()
        self.event_manager.add("grant_access", pool=pool.oid, host_class=host_class.oid, authuser=fun.session.authuser)
        
    @entry(g_admin)
    def revoke_host(self, fun, pool, host):
        q0 = "SELECT poolname FROM pool_host_map WHERE poolname=:poolname AND hostname=:hostname"
        pools = self.db.get(q0, poolname=pool.oid, hostname=host.oid)
        if len(pools) == 0:
            raise ExtHostNotGrantedInPoolError()
        q = """DELETE FROM pool_host_map WHERE poolname=:poolname AND hostname=:hostname""" 
        self.db.put(q, poolname=pool.oid, hostname=host.oid)
        self.event_manager.add("revoke_access", pool=pool.oid, host=host.oid, authuser=fun.session.authuser)
        
    @entry(g_admin)
    def revoke_group(self, fun, pool, group):
        q0 = "SELECT poolname FROM pool_group_map WHERE poolname=:poolname AND groupname=:groupname"
        pools = self.db.get(q0, poolname=pool.oid, groupname=group.oid)
        if len(pools) == 0:
            raise ExtGroupNotGrantedInPoolError()
        q = """DELETE FROM pool_group_map WHERE poolname=:poolname AND groupname=:groupname""" 
        self.db.put(q, poolname=pool.oid, groupname=group.oid)
        self.event_manager.add("revoke_access", pool=pool.oid, group=group.oid, authuser=fun.session.authuser)
        
    @entry(g_admin)
    def revoke_host_class(self, fun, pool, host_class):
        q0 = "SELECT poolname FROM pool_class_map WHERE poolname=:poolname AND classname=:classname"
        pools = self.db.get(q0, poolname=pool.oid, classname=host_class.oid)
        if len(pools) == 0:
            raise ExtHostClassNotGrantedInPoolError()
        q = """DELETE FROM pool_class_map WHERE poolname=:poolname AND classname=:classname""" 
        self.db.put(q, poolname=pool.oid, classname=host_class.oid)
        self.event_manager.add("revoke_access", pool=pool.oid, host_class=host_class.oid, authuser=fun.session.authuser)
    
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
            self.event_manager.add("update", pool=pool.oid, option=key, option_value=unicode(value), authuser=self.function.session.authuser)
