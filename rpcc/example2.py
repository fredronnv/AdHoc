#!/usr/bin/env python2.6

from model import Model, Manager, template, update
from exttype import *
from function import Function

import server
import authenticator

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

class PersonFunBase(Function):
    params = [("person", ExtPerson, "A person")]

class FunPersonGetName(PersonFunBase):
    extname = "person_get_name"
    params = []
    returns = (ExtString, "Composite name")

    def do(self):
        raise ValueError()
        return self.person.fname + " " + self.person.lname

class Person(Model):
    name = "person"
    exttype = ExtPerson

    def init(self, myid, fname, lname):
        self.pid = myid
        self.fname = fname
        self.lname = lname
        self.account_name = "acc-" + myid

    @template(ExtPerson)
    def get_person(self):
        return self

    @template(ExtString)
    def get_firstname(self):
        return self.fname

    @template(ExtString)
    def get_lastname(self):
        return self.lname

    @template(ExtAccount, model="account")
    def get_account(self):
        return self.account_manager.get_account(self.account_name)

class PersonManager(Manager):
    name = "person_manager"

    def get_person(self, pid):
        if not pid.startswith("pers-"):
            raise LookupError()
        persid = pid[5:]
        return Person(self, persid, "fn-" + persid, "en-" + persid)

class Account(Model):
    name = "account"
    exttype = ExtAccount

    def init(self, myid, uid):
        self.aid = myid
        self.uid = uid
        self.owner_id = "pers-" + self.aid

    @template(ExtAccount)
    def get_account(self):
        return self

    @template(ExtInteger)
    def get_uid(self):
        return self.uid

    @template(ExtPerson, model="person")
    def get_owner(self):
        return self.person_manager.get_person(self.owner_id)

class AccountManager(Manager):
    name = "account_manager"

    def get_account(self, aid):
        if not aid.startswith("acc-"):
            raise LookupError()
        accid = aid[4:]
        return Account(self, accid, len(accid))

class MyServer(server.Server):
    authenticator = authenticator.NullAuthenticator

srv = MyServer("venus.ita.chalmers.se", 12121)
srv.register_function(FunPersonGetName)
srv.register_manager(AccountManager)
srv.register_manager(PersonManager)
srv.register_model(Account)
srv.register_model(Person)
srv.generate_model_stuff()
srv.serve_forever()
