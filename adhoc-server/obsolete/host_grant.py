#!/usr/bin/env python2.6

# $Id: host_class.py 683 2015-02-23 10:09:22Z bernerus@CHALMERS.SE $

from lib.host import *
from lib.pool import *
from rpcc import *


class ExtNoSuchHostGrantError(ExtLookupError):
    desc = "No such host grant exists."
    
    
class ExtHostGrantAlreadyExistsError(ExtLookupError):
    desc = "The host grant id already exists"

    
class ExtHostGrantInUseError(ExtValueError):
    desc = "The host grant is referred to by other objects. It cannot be destroyed"    


class ExtHostGrantID(ExtInteger):
    name = "host_grant-id"
    desc = "ID of a host grant"


class ExtHostGrantList(ExtList):
    name = "host_grant-list"
    desc = "List of host grants"
    typ = ExtHostGrantID


class ExtHostGrant(ExtHostGrantID):
    name = "host_grant"
    desc = "A host_grant instance"

    def lookup(self, fun, cval):
        return fun.host_class_manager.get_host_grant(cval)

    def output(self, fun, obj):
        return obj.oid


class HostGrantFunBase(SessionedFunction):  
    params = [("grant", ExtHostGrantID, "Host_grant id")]
    
    
class HostGrantCreate(SessionedFunction):
    extname = "host_grant_create"
    params = [("pool", ExtPool, "Pool"),
              ("host", ExtHost, "Host to be granted into the pool")]
    desc = "Creates a host grant"
    returns = (ExtHostGrantID)

    def do(self):
        if self.pool.open:
            raise ExtPoolIsOpenError()
        id = self.pool_manager.grant_host(self, self.pool, self.host)
        return id


class HostGrantRevoke(HostGrantFunBase):
    extname = "host_grant_revoke"
    desc = "Revokes a host grant"
    returns = (ExtNull)

    def do(self):
        self.pool_manager.revoke(self, self.grant.poolname, self.grant.hostname)


class HostGrant(AdHocModel):
    name = "host_grant"
    exttype = ExtHostGrant
    id_type = int

    def init(self, *args, **kwargs):
        a = list(args)
        # print "HostClass.init", a
        self.oid = a.pop(0)
        self.pool_name = a.pop(0)
        self.host_name = a.pop(0)
        self.changed_by = a.pop(0)
        self.mtime = a.pop(0)

    @template("host_grant", ExtHostGrant)
    def get_host_grant(self):
        return self

    @template("pool_name", ExtPoolName)
    def get_pool_name(self):
        return self.pool_name
    
    @template("mtime", ExtDateTime)
    def get_mtime(self):
        return self.mtime
    
    @template("changed_by", ExtString)
    def get_changed_by(self):
        return self.changed_by
        

class HostGrantManager(AdHocManager):
    name = "host_grant_manager"
    manages = HostGrant

    model_lookup_error = ExtNoSuchHostGrantError

    def init(self):
        self._model_cache = {}
        
    @classmethod
    def base_query(cls, dq):
        dq.select("m.id", "m.poolname", "m.hostname",
                  "m.changed_by", "m.mtime")
        dq.table("pool_host_map m")
        return dq

    def get_host_grant(self, host_grant_id):
        return self.model(host_grant_id)

    def search_select(self, dq):
        dq.table("pool_host_map m")
        dq.select("m.id")
    
    @search("host_name", StringMatch)
    def s_host_name(self, dq):
        dq.table("pool_host_map m")
        return "m.hostname"
    
    @search("pool_name", StringMatch)
    def s_pool_name(self, dq):
        dq.table("pool_host_map m")
        return "m.poolname"
