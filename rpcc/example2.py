#!/usr/bin/env python2.6

from model import *
from exttype import *
from function import Function

import server
import access
import authenticator
import database
import session

class AllowCertainUser(access.Guard):
    def __init__(self, uname):
        self.uname = uname

    def check(self, obj, fun):
        if fun.session.authuser == self.uname:
            return access.AccessGranted(access.CacheInFunction)
        else:
            return access.AccessDenied(access.CacheInFunction)

class AllowOwner(access.Guard):
    def check(self, obj, fun):
        if isinstance(obj, Account):
            if fun.session.authuser == obj.oid:
                return access.AccessGranted(access.CacheInFunction)
            else:
                return access.AccessDenied(access.CacheInFunction)
        elif isinstance(obj, Person):
            if fun.session.authuser == obj.account_name:
                return access.AccessGranted(access.CacheInFunction)
            else:
                return access.AccessDenied(access.CacheInFunction)
        else:
            return access.AccessReferred(access.CacheInFunction)

class AllowBeforeLunch(access.Guard):
    def check(self, obj, fun):
        if fun.started_at().hour < 12:
            return access.AccessGranted(access.CacheInFunction)
        else:
            return access.AccessDenied(access.CacheInFunction)

class AllowAfterLunch(access.Guard):
    def check(self, obj, fun):
        if fun.started_at().hour >= 12:
            return access.AccessGranted(access.CacheInFunction)
        else:
            return access.AccessDenied(access.CacheInFunction)


class ExtPerson(ExtString):
    name = "person"
    desc = "ID of a person in the system"

    def lookup(self, fun, cval):
        return fun.person_manager.get_person(cval)

    def output(self, fun, obj):
        return obj.oid

class ExtAccount(ExtString):
    name = "account"
    desc = "ID of an account in the system"

    def lookup(self, fun, cval):
        return fun.account_manager.get_account(cval)

    def output(self, fun, obj):
        return obj.oid

class ExtNoSuchPersonError(ExtLookupError):
    desc = "No such person exists."

class ExtNoSuchAccountError(ExtLookupError):
    desc = "No such account exists."

class PersonFunBase(Function):
    params = [("person", ExtPerson, "A person")]

class FunPersonGetName(PersonFunBase):
    extname = "person_get_name"
    returns = (ExtString, "Composite name")

    def do(self):
        return self.person.fname + " " + self.person.lname

class Person(Model):
    name = "person"
    exttype = ExtPerson
    id_type = str

    def init(self, persid, fname, lname, pnr, acc):
        self.oid = persid
        self.fname = fname.decode("iso-8859-1")
        self.lname = lname.decode("iso-8859-1")
        self.pnr = pnr
        self.account_name = acc

    g_before_lunch = AllowBeforeLunch()
    g_after_lunch = AllowAfterLunch()
    g_owner = AllowOwner()
    g_viktor = AllowCertainUser("viktor")

    @template("person", ExtPerson)
    def get_person(self):
        return self

    @template("firstname", ExtString)
    def get_firstname(self):
        return self.fname

    @update("firstname", ExtString)
    @access.entry(g_before_lunch)
    def set_firstname(self, newname):
        print "set_firstname"
        q = "UPDATE person SET fname=:name WHERE ucid=:pid"
        self.db.put(q, pid=self.pid, name=newname.encode("iso-8859-1"))
        self.db.commit()

    @template("lastname", ExtString)
    def get_lastname(self):
        return self.lname

    @access.entry(g_before_lunch)
    @update("noop1", ExtBoolean)
    def set_noop1(self, newvalue):
        pass

    @update("noop2", ExtBoolean)
    @access.entry(g_before_lunch)
    def set_noop2(self, newvalue):
        pass

    @access.entry(g_after_lunch)
    @update("noop3", ExtBoolean)
    def set_noop3(self, newvalue):
        pass

    @update("noop4", ExtBoolean)
    @access.entry(g_after_lunch)
    def set_noop4(self, newvalue):
        pass

    @update("lastname", ExtString)
    def set_lastname(self, newname):
        q = "UPDATE person SET lname=:name WHERE ucid=:pid"
        self.db.put(q, pid=self.pid, name=newname.encode("iso-8859-1"))
        self.db.commit()

    @template("personnummer", ExtString)
    @access.entry(access.AnyGrants(g_owner, g_viktor))
    def get_personnummer(self):
        return self.pnr

    @template("account", ExtList(ExtAccount), model="account")
    def get_accounts(self):
        q = "SELECT ucid FROM account WHERE ucid_owner=:pid"
        amgr = self.account_manager
        return [amgr.model(a) for (a,) in self.db.get(q, pid=self.oid)]

class PersonManager(Manager):
    name = "person_manager"
    manages = Person

    result_table = "rpcc_result_string"
    model_lookup_error = ExtNoSuchPersonError

    def init(self):
        self._model_cache = {}

    def base_query(self, dq):
        dq.select("p.ucid", "p.fname", "p.lname", "p.pnr", "a.ucid")
        dq.table("person p", "account a")
        dq.where("p.ucid=a.ucid_owner")
        dq.where("a.primary=1")

    def get_person(self, pid):
        return self.model(pid)

    def search_select(self, q):
        q.table("person p")
        q.select("p.ucid")

    @search("firstname", StringMatch)
    def s_firstname(self, q):
        q.table("person p")
        return "p.fname"

    @search("lastname", StringMatch)
    def s_lastname(self, q):
        q.table("person p")
        return "p.lname"

    @search("account", StringMatch, manager="account_manager")
    def s_account(self, q):
        q.table("account a")
        q.where("a.ucid_owner = p.ucid")
        return "a.ucid"

class Account(Model):
    name = "account"
    exttype = ExtAccount
    id_type = str

    def init(self, accid, uid, owner_id):
        print "Account.init", accid
        self.oid = accid
        self.uid = uid
        self.owner_id = owner_id

    @template("account", ExtAccount)
    def get_account(self):
        return self

    @template("uid", ExtInteger)
    def get_uid(self):
        return self.uid

    @template("owner", ExtPerson, model="person")
    def get_owner(self):
        return self.person_manager.get_person(self.owner_id)

class AccountManager(Manager):
    name = "account_manager"
    manages = Account

    result_table = "rpcc_result_string"
    model_lookup_error = ExtNoSuchAccountError

    def init(self):
        self._model_cache = {}

    def base_query(self, dq):
        dq.select("a.ucid", "a.unix_uid", "a.ucid_owner")
        dq.table("account a")
        return dq

    def get_account(self, aid):
        return self.model(aid)

    def search_select(self, dq):
        dq.table("account a")
        dq.select("a.ucid")

    @search("uid", IntegerMatch)
    def s_uid(self, dq):
        dq.table("account a")
        return "a.unix_uid"

    @search("account", StringMatch)
    def s_acc(self, dq):
        dq.table("account a")
        return "a.ucid"

    @search("owner", StringMatch, manager="person_manager")
    def s_own(self, q):
        q.table("account a")
        return "a.ucid_owner"


###
# Complex types and functions that only serve to test documentation code.
###
class ExtStringSample(ExtString):
    name = "string-sample"
    desc = "A sample of a string"
    regexp = "[sample]+"
    maxlen = 33

class ExtIntegerSample(ExtInteger):
    name = "integer-sample"
    desc = "An integer sample"
    range = (1, 11)

class ExtEnumSample(ExtEnum):
    name = "enum-sample"
    desc = "A sample of an enum"
    values = ["value1", "value2", "value3", "value4"]

class ExtStructSample(ExtStruct):
    name = "struct-sample"
    desc = "A sample of a struct"
    mandatory = {
        "string": (ExtStringSample, "Mandatory string"),
        "integer": (ExtIntegerSample, "Mandatory integer"),
        "bool": ExtBoolean,
        "or_null": ((ExtOrNull(ExtEnumSample), "Mandatory or-null enum")),
        }

    optional = {
        "null": (ExtNull, "Optional null"),
        }

ExtStructSample.optional["self"] = (ExtStructSample, "A value of its own type")

class FunDoctest(Function):
    extname = "doctest"
    params = [("first_string", ExtStringSample),
              ("second_string", ExtString, "A second string of the generic type"),
              ]
    returns = (ExtList(ExtStructSample), "A sample struct returned")

    def do(self):
        pass


class MyServer(server.Server):
    envvar_prefix = "XMPL_"

srv = MyServer("venus.ita.chalmers.se", 12121)
srv.register_function(FunPersonGetName)
srv.register_function(FunDoctest)
srv.register_manager(AccountManager)
srv.register_manager(PersonManager)
srv.enable_database(database.OracleDatabase)
srv.enable_sessions(session.DatabaseSessionStore)
srv.enable_authentication(authenticator.NullAuthenticator)
srv.enable_documentation()
srv.enable_mutexes()
srv.enable_digs_and_updates()
srv.serve_forever()
