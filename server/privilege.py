#!/usr/bin/env python2.6

from rpcc import *
from util import *


g_read = AnyGrants(AllowUserWithPriv("read_all_privileges"), AdHocSuperuserGuard)
g_write = AnyGrants(AdHocSuperuserGuard)
g_grant = AnyGrants(AllowUserWithPriv("grant_all_privileges"), AdHocSuperuserGuard)

class ExtNoSuchPrivilegeError(ExtLookupError):
    desc = "No such privilege exists."
    
    
class ExtPrivilegeAlreadyExistsError(ExtLookupError):
    desc = "The privilege already exists"
    
    
class ExtPrivilegeNotGrantedError(ExtLookupError):
    desc = "No such privilege is granted"
    
    
class ExtPrivilegeAlreadyGrantedError(ExtValueError):
    desc = "That privilege has already been granted"

    
class ExtPrivilegeInUseError(ExtValueError):
    desc = "The privilege is referred to by other objects. It must not destroyed"    


class ExtPrivilegeName(ExtString):
    name = "privilege-name"
    desc = "Name of a privilege"
    regexp = "^[a-z][-a-z0-9_]{0,31}$"


class ExtPrivilege(ExtPrivilegeName):
    name = "privilege"
    desc = "A privilege"

    def lookup(self, fun, cval):
        return fun.privilege_manager.get_privilege(str(cval))

    def output(self, fun, obj):
        return obj.oid
    
class ExtPrivilegeList(ExtList):
    name = "privilege-list"
    desc = "List of privileges"
    typ = ExtPrivilegeName
    
    

    
        
class PrivilegeFunBase(SessionedFunction):  
    params = [("privilege", ExtPrivilege, "A registered privilege")]
   

class PrivilegeCreate(SessionedFunction):
    extname = "privilege_create"
    params = [("privilege_name", ExtPrivilegeName, "Privilege to create"),
              ("info", ExtString, "Privilege description"),]
    desc = "Registers a privilege"
    returns = (ExtNull)

    def do(self):
        self.privilege_manager.create_privilege(self, self.privilege_name, self.info)
        

class PrivilegeDestroy(PrivilegeFunBase):
    extname = "privilege_destroy"
    desc = "Unregisters a privilege"
    returns = (ExtNull)

    def do(self):
        self.privilege_manager.destroy_privilege(self, self.privilege)
        
        
        
class PrivilegeGrant(PrivilegeFunBase):
    extname = "privilege_grant"
    desc = "Grants a privilege to an account"
    params = [("account", ExtAccount, "Account to be granted the privilege")]
    returns = (ExtNull)
    
    def do(self):
        self.privilege_manager.grant_privilege(self, self.privilege, self.account)
        
        
class PrivilegeRevoke(PrivilegeFunBase):
    extname = "privilege_revoke"
    desc = "Revokes a privilege givento an account"
    params = [("account", ExtAccount, "Account whose privolege is to be revoked")]
    returns = (ExtNull)
    
    def do(self):
        self.privilege_manager.revoke_privilege(self.privilege, self.account)



class Privilege(Model):
    name = "privilege"
    exttype = ExtPrivilege
    id_type = str

    def init(self, *args, **kwargs):
        a = list(args)
        self.oid = a.pop(0)
        self.info = a.pop(0)

    @template("privilege", ExtPrivilege)
    @entry(g_read)
    def get_privilege(self):
        return self

    @template("info", ExtString)
    @entry(g_read)
    def get_info(self):
        return self.info
    
    @template("accounts_granted", ExtAccountList)
    @entry(g_read)
    def get_grants(self):
        q = "SELECT account FROM account_privilege_map WHERE privilege=:privilege"
        accounts = self.db.get(q, privilege=self.oid)
        return [x[0] for x in accounts]

    @update("info", ExtString)
    @entry(g_write)
    def set_info(self, fname):
        q = "UPDATE privileges SET info=:info WHERE id=:id"
        self.db.put(q, id=self.oid, info=info)
        

class PrivilegeManager(Manager):
    name = "privilege_manager"
    manages = Privilege

    model_lookup_error = ExtNoSuchPrivilegeError
    
    def init(self):
        self._model_cache = {}
        
    def base_query(self, dq):
        dq.table("privileges p")
        dq.select("p.privilege", "p.info")
        return dq

    def get_privilege(self, privilege_name):
        return self.model(privilege_name)

    def search_select(self, dq):
        dq.table("privileges p")
        dq.select("p.privilege")

    @search("privilege", StringMatch)
    @entry(g_read)
    def s_privilege(self, dq):
        dq.table("privileges p")
        return "p.privilege"
    
    @entry(g_write)
    def create_privilege(self, fun, privilege_name, info):
        
        optionset = self.optionset_manager.create_optionset()
        
        q = """INSERT INTO privileges (privilege, info) 
               VALUES (:privilege, :info)"""
        try:
            self.db.put(q, privilege=privilege_name, info=info,)
        except IntegrityError:
            raise ExtPrivilegeAlreadyExistsError()
        
        #print "Privilege created, privilege_name=", privilege_name
        
    @entry(g_write)
    def destroy_privilege(self, fun, privilege):
        
        privilege.get_optionset().destroy()
        
        try:
            q = "DELETE FROM privileges WHERE privilege=:privilege LIMIT 1"
        except IntegrityError:
            raise ExtPrivilegeInUseError()
        self.db.put(q, privilege=privilege.oid)
        
    @entry(g_grant)
    def grant_privilege(self, fun, privilege, account):
        q = """INSERT INTO account_privilege_map (account, privilege, changed_by) 
            VALUES (:account, :privilege, :changed_by)"""
        try:
            self.db.put(q, privilege=privilege.oid, account=account.oid, changed_by=fun.session.authuser)
        except IntegrityError:
            raise ExtPrivilegeAlreadyGrantedError()
    
    @entry(g_grant)
    def revoke_privilege(self, privilege, account):
        q0 = "SELECT privilege FROM account_privilege_map WHERE privilege=:privilege AND account=:account"
        pools = self.db.get(q0, privilege=privilege.oid, account=account.oid)
        if len(pools) == 0:
            raise ExtPrivilegeNotGrantedError()
        q = """DELETE FROM account_privilege_map WHERE privilege=:privilege AND account=:account""" 
        self.db.put(q, privilege=privilege.oid, account=account.oid)