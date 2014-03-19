#!/usr/bin/env python2.6

from rpcc import *
from util import *
from privilege import *

g_read = AnyGrants(AllowUserWithPriv("read_all_accounts"), AdHocSuperuserGuard)
g_write = AnyGrants(AllowUserWithPriv("write_all_accounts"), AdHocSuperuserGuard)


class SessionGetPrivileges(SessionedFunction):
    extname = "session_get_privileges"
    returns = ExtPrivilegeList

    desc = """Returns a list of all privileges for the currently authenticated user."""

    def do(self):
        return self.account_manager.get_authuser_account_privileges(self)


class AccountFunBase(SessionedFunction):  
    params = [("account", ExtAccount, "A registered account")]
   

class AccountCreate(SessionedFunction):
    extname = "account_create"
    params = [("account_name", ExtAccountName, "Account to create"),
              ("fname", ExtString, "First name of account owner"),
              ("lname", ExtString, "Last name of account owner")]
    desc = "Registers an account"
    returns = (ExtNull)

    def do(self):
        self.account_manager.create_account(self, self.account_name, self.fname, self.lname)
        

class AccountDestroy(AccountFunBase):
    extname = "account_destroy"
    desc = "Unregisters an account"
    returns = (ExtNull)

    def do(self):
        self.account_manager.destroy_account(self, self.account)

class Account(AdHocModel):
    name = "account"
    exttype = ExtAccount
    id_type = str

    def init(self, *args, **kwargs):
        a = list(args)
        self.oid = a.pop(0)
        self.fname = a.pop(0)
        self.lname = a.pop(0)

    @template("account", ExtAccount)
    @entry(g_read)
    def get_account(self):
        return self

    @template("fname", ExtString)
    @entry(g_read)
    def get_fname(self):
        return self.fname
    
    @template("lname", ExtDateTime)
    @entry(g_read)
    def get_lname(self):
        return self.lname
    
    @template("granted_privileges", ExtPrivilegeList)
    @entry(g_read)
    def get_privileges(self):
        q = "SELECT privilege FROM account_privilege_map WHERE account=:account"
        privileges= self.db.get(q, account=self.oid)
        return [x[0] for x in privileges]

    @update("fname", ExtString)
    @entry(g_write)
    def set_authoritative(self, fname):
        q = "UPDATE accounts SET fname=:fname WHERE id=:id"
        self.db.put(q, id=self.oid, fname=fname)
        
    @update("lname", ExtString)
    @entry(g_write)
    def set_authoritative(self, lname):
        q = "UPDATE accounts SET lname=:lname WHERE id=:id"
        self.db.put(q, id=self.oid, lname=lname)
        
        

class AccountManager(AdHocManager):
    name = "account_manager"
    manages = Account

    model_lookup_error = ExtNoSuchAccountError
    
    def init(self):
        self._model_cache = {}
        
    def base_query(self, dq):
        dq.table("accounts a")
        dq.select("a.account", "a.fname", "a.lname")
        return dq

    def get_account(self, account_name):
        return self.model(account_name)

    def search_select(self, dq):
        dq.table("accounts a")
        dq.select("a.account")

    @search("account", StringMatch)
    @entry(g_read)
    def s_account(self, dq):
        dq.table("accounts a")
        return "a.account"
    
    @entry(g_write)
    def create_account(self, fun, account_name, fname, lname):
        
        optionset = self.optionset_manager.create_optionset()
        
        q = """INSERT INTO accounts (account, fname, lname) 
               VALUES (:account, :fname, :lname)"""
        try:
            self.db.put(q, account=account_name, fname=fname, 
                        lname=lname)
        except IntegrityError:
            raise ExtAccountAlreadyExistsError()
        
        #print "Account created, account_name=", account_name
        
    @entry(g_write)
    def destroy_account(self, fun, account):
        
        account.get_optionset().destroy()
        
        try:
            q = "DELETE FROM accounts WHERE account=:account LIMIT 1"
        except IntegrityError:
            raise ExtAccountInUseError()
        self.db.put(q, account=account.oid)
        
    @entry(AlwaysAllowGuard)
    def get_authuser_account_privileges(self, fun):
        try:
            authacc =  self.get_account(fun.session.authuser)
        except ExtNoSuchAccountError:
            return []
        return authacc.get_privileges()
    
        

