#!/usr/bin/env python2.6

from model import *
from exttype import *
from function import Function

import server
import authenticator
import database
import session

class ExtPerson(ExtString):
    def lookup(self, fun, cval):
        return fun.person_manager.get_person(cval)

    def output(self, fun, obj):
        return obj.pid

class ExtAccount(ExtString):
    def lookup(self, fun, cval):
        return fun.account_manager.get_account(cval)

    def output(self, fun, obj):
        return obj.aid

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

    def init(self, myid, fname, lname, acc):
        print "Person.init", myid
        self.pid = myid
        self.fname = fname.decode("iso-8859-1")
        self.lname = lname.decode("iso-8859-1")
        self.account_name = acc

    @template("person", ExtPerson)
    def get_person(self):
        return self

    @template("firstname", ExtString)
    def get_firstname(self):
        return self.fname

    @update("firstname", ExtString)
    def set_firstname(self, newname):
        print "set_firstname"
        q = "UPDATE person SET fname=:name WHERE ucid=:pid"
        self.db.put(q, pid=self.pid, name=newname.encode("iso-8859-1"))
        self.db.commit()

    @template("lastname", ExtString)
    def get_lastname(self):
        return self.lname

    @update("lastname", ExtString)
    def set_lastname(self, newname):
        print "set_lastname"
        q = "UPDATE person SET lname=:name WHERE ucid=:pid"
        self.db.put(q, pid=self.pid, name=newname.encode("iso-8859-1"))
        self.db.commit()

    @template("account", ExtAccount, model="account")
    def get_account(self):
        return self.account_manager.get_account(self.account_name)

class PersonManager(Manager):
    name = "person_manager"
    manages = Person

    result_table = "rpcc_result_string"
    model_lookup_error = ExtNoSuchPersonError

    def init(self):
        self._model_cache = {}

    def base_query(self, dq):
        dq.select("p.ucid", "p.fname", "p.lname", "a.ucid")
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

    def init(self, myid, uid, owner_id):
        print "Account.init", myid
        self.aid = myid
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


class MyServer(server.Server):
    authenticator_class = authenticator.NullAuthenticator
    database_class = database.OracleDatabase
    session_store_class = session.DatabaseSessionStore
    envvar_prefix = "XMPL_"

srv = MyServer("venus.ita.chalmers.se", 12121)
srv.register_function(FunPersonGetName)
srv.register_manager(AccountManager)
srv.register_manager(PersonManager)
#srv.register_model(Account)
#srv.register_model(Person)
srv.generate_model_stuff()
srv.serve_forever()
