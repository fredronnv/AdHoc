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

class ExtUnknownPersonError(ExtLookupError):
    desc = "No such person exists."

class ExtUnknownAccountError(ExtLookupError):
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
        self.pid = myid
        self.fname = fname
        self.lname = lname
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

    def get_person(self, pid):
        q = "SELECT p.ucid, p.fname, p.lname, a.ucid "
        q += " FROM person p, account a "
        q += "WHERE p.ucid=a.ucid_owner "
        q += "  AND a.primary=1 "
        q += "  AND p.ucid=:pid "
        try:
            ((persid, fname, lname, acc),) = self.db.get(q, pid=pid)
        except:
            raise ExtUnknownPersonError()
        return Person(self, persid, fname.decode("iso-8859-1"), lname.decode("iso-8859-1"), acc)

    @search("firstname", StringMatch)
    def s_firstname(self, q):
        q.table("person p")
        return "p.firstname"

    @search("lastname", StringMatch)
    def s_lastname(self, q):
        q.table("person p")
        return "p.lastname"

    @search("account", StringMatch, manager="account_manager")
    def s_account(self, q):
        q.table("person a")
        q.where("a.ucid_owner = p.ucid")
        return "a.ucid"

class Account(Model):
    name = "account"
    exttype = ExtAccount

    def init(self, myid, uid, owner_id):
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

    def get_account(self, aid):
        q = "SELECT ucid, unix_uid, ucid_owner "
        q += " FROM account "
        q += "WHERE ucid=:aid "
        try:
            ((accid, uid, owner_id),) = self.db.get(q, aid=aid)
        except:
            raise ExtUnknownAccountError()
        return Account(self, accid, uid, owner_id)

class MyServer(server.Server):
    authenticator_class = authenticator.NullAuthenticator
    database_class = database.OracleDatabase
    session_store_class = session.DatabaseSessionStore
    envvar_prefix = "XMPL_"

srv = MyServer("venus.ita.chalmers.se", 12121)
srv.register_function(FunPersonGetName)
srv.register_manager(AccountManager)
srv.register_manager(PersonManager)
srv.register_model(Account)
srv.register_model(Person)
srv.generate_model_stuff()
srv.serve_forever()
