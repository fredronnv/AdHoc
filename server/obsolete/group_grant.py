#!/usr/bin/env python2.6

# $Id: group_class.py 683 2015-02-23 10:09:22Z bernerus@CHALMERS.SE $

from rpcc import *
from lib.pool import ExtPool, ExtPoolIsOpenError, ExtPoolName
from lib.group import *


class ExtNoSuchGroupGrantError(ExtLookupError):
    desc = "No such group grant exists."
    
    
class ExtGroupGrantAlreadyExistsError(ExtLookupError):
    desc = "The group grant id already exists"

    
class ExtGroupGrantInUseError(ExtValueError):
    desc = "The group grant is referred to by other objects. It cannot be destroyed"    


class ExtGroupGrantID(ExtInteger):
    name = "group_grant-id"
    desc = "ID of a group grant"


class ExtGroupGrantList(ExtList):
    name = "group_grant-list"
    desc = "List of group grants"
    typ = ExtGroupGrantID


class ExtGroupGrant(ExtGroupGrantID):
    name = "group_grant"
    desc = "A group_grant instance"

    def lookup(self, fun, cval):
        return fun.group_grant_manager.get_group_grant(cval)

    def output(self, fun, obj):
        return obj.oid


class GroupGrantFunBase(SessionedFunction):  
    params = [("grant", ExtGroupGrantID, "Group_grant id")]
    
    
class GroupGrantCreate(SessionedFunction):
    extname = "group_grant_create"
    params = [("pool", ExtPool, "Pool"),
              ("group", ExtGroup, "Group to be granted into the pool")]
    desc = "Creates a group grant"
    returns = (ExtGroupGrantID)

    def do(self):
        if self.pool.open:
            raise ExtPoolIsOpenError()
        self.pool_manager.grant_group(self, self.pool, self.group)


class GroupGrantRevoke(GroupGrantFunBase):
    extname = "group_grant_revoke"
    desc = "Revokes a group grant"
    returns = (ExtNull)

    def do(self):
        self.pool_manager.revoke(self, self.grant.poolname, self.grant.groupname)


class GroupGrant(AdHocModel):
    name = "group_grant"
    exttype = ExtGroupGrant
    id_type = int

    def init(self, *args, **kwargs):
        a = list(args)
        # print "GroupClass.init", a
        self.oid = a.pop(0)
        self.pool_name = a.pop(0)
        self.group_name = a.pop(0)
        self.changed_by = a.pop(0)
        self.mtime = a.pop(0)

    @template("group_grant", ExtGroupGrant)
    def get_group_grant(self):
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
        

class GroupGrantManager(AdHocManager):
    name = "group_grant_manager"
    manages = GroupGrant

    model_lookup_error = ExtNoSuchGroupGrantError

    def init(self):
        self._model_cache = {}
        
    @classmethod
    def base_query(cls, dq):
        dq.select("m.id", "m.poolname", "m.groupname",
                  "m.changed_by", "m.mtime")
        dq.table("pool_group_map m")
        return dq

    def get_group_grant(self, group_grant_id):
        return self.model(group_grant_id)

    def search_select(self, dq):
        dq.table("pool_group_map m")
        dq.select("m.id")
    
    @search("group_name", StringMatch)
    def s_group_name(self, dq):
        dq.table("pool_group_map m")
        return "m.groupname"
    
    @search("pool_name", StringMatch)
    def s_pool_name(self, dq):
        dq.table("pool_group_map m")
        return "m.poolname"
