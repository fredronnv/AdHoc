#!/usr/bin/env python2.6


# $Id$

from rpcc import *
from util import * 

from privilege import *

g_read = AnyGrants(AllowUserWithPriv("write_all_accounts"), AllowUserWithPriv("read_all_accounts"), AdHocSuperuserGuard)
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
    log_call_event = False

    def do(self):
        self.account_manager.create_account(self, self.account_name, self.fname, self.lname)


class ExtAccountStatus(ExtOrNull):
    name = "account_status"
    desc = "Account status. To be synchronized with PDB"
    typ = ExtString


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
    log_fetch_calls = False
    log_update_calls = False

    def init(self, *args, **kwargs):
        a = list(args)
        self.oid = a.pop(0)
        self.fname = a.pop(0)
        self.lname = a.pop(0)
        self.status = a.pop(0)

    @template("account", ExtAccount, desc="Account id (cid)")
    @entry(g_read)
    def get_account(self):
        return self

    @template("fname", ExtString, desc="First name of the account owner")
    @entry(g_read)
    def get_fname(self):
        return self.fname
    
    @template("lname", ExtString, desc="Last name of the account owner")
    @entry(g_read)
    def get_lname(self):
        return self.lname

    @template("status", ExtAccountStatus, desc="PDB status")
    @entry(g_read)
    def get_status(self):
        return self.status
    
    @template("granted_privileges", ExtPrivilegeList, desc="AdHoc privileges granted for the account")
    @entry(g_read)
    def get_privileges(self):
        q = "SELECT privilege FROM account_privilege_map WHERE account=:account"
        privileges = self.db.get(q, account=self.oid)
        return [x[0] for x in privileges]

    @update("fname", ExtString)
    @entry(g_write)
    def set_fname(self, fname):
        q = "UPDATE accounts SET fname=:fname WHERE account=:id"
        self.db.put(q, id=self.oid, fname=fname)
        
    @update("lname", ExtString)
    @entry(g_write)
    def set_lname(self, lname):
        q = "UPDATE accounts SET lname=:lname WHERE account=:id"
        self.db.put(q, id=self.oid, lname=lname)
        
    @update("status", ExtAccountStatus)
    @entry(g_write)
    def set_status(self, status):
        q = "UPDATE accounts SET status=:status WHERE account=:id"
        self.db.put(q, id=self.oid, status=status)


class AccountManager(AdHocManager):
    name = "account_manager"
    manages = Account
    log_dig_calls = False

    model_lookup_error = ExtNoSuchAccountError
    
    def init(self):
        self._model_cache = {}
        
    @classmethod    
    def base_query(self, dq):
        dq.table("accounts a")
        dq.select("a.account", "a.fname", "a.lname", "a.status")
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
    
    @search("fname", StringMatch)
    @entry(g_read)
    def s_fname(self, dq):
        dq.table("accounts a")
        return "a.fname"
    
    @search("lname", StringMatch)
    @entry(g_read)
    def s_lname(self, dq):
        dq.table("accounts a")
        return "a.lname"
    
    @search("status", NullableStringMatch)
    @entry(g_read)
    def s_status(self, dq):
        dq.table("accounts a")
        return "a.status"
    
    @entry(g_write)
    def create_account(self, fun, account_name, fname, lname):
        
        #self.optionset_manager.create_optionset(fun)
        
        q = """INSERT INTO accounts (account, fname, lname) 
               VALUES (:account, :fname, :lname)"""
        try:
            self.db.put(q, account=account_name, fname=fname, 
                        lname=lname)
        except IntegrityError:
            raise ExtAccountAlreadyExistsError()
        
        # print "Account created, account_name=", account_name
        
    @entry(g_write)
    def destroy_account(self, fun, account):
        
        #account.get_optionset().destroy()
        
        try:
            q = "DELETE FROM accounts WHERE account=:account LIMIT 1"
        except IntegrityError:
            raise ExtAccountInUseError()
        self.db.put(q, account=account.oid)
        
    @entry(AlwaysAllowGuard)
    def get_authuser_account_privileges(self, fun):
        try:
            authacc = self.get_account(fun.session.authuser)
        except ExtNoSuchAccountError:
            return []
        return authacc.get_privileges()
