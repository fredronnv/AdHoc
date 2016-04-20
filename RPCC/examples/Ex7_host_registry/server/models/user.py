#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

from rpcc import *
from __builtin__ import classmethod
from email.utils import parseaddr
from userauthentication import UserAuthenticationManager


# Model description of a user record containing first and last names and an email
#
# Possible errors 
class ExtNoSuchUserError(ExtLookupError):
    desc = "No such user is known."
    

class ExtUserAlreadyExistsError(ExtLookupError):
    desc = "The user id already exists"


class ExtInvalidEmailAddress(ExtLookupError):
    desc = "The email address is invalid"
    

class ExtBadPassword(ExtLookupError):
    desc = "The password given dows not follow the requirements"
  
    
# Desription of how we identify the user    
class ExtUserId(ExtString):
    name = "user-id"
    desc = "ID of a user"
    regexp = "^[a-z]{1,8}$"
  
    
class ExtEmailAddress(ExtString):
    name = "email-address"
    desc = "An email address"
    
    def lookup(self, _fun, cval):
        _comment, email = parseaddr(cval)
        if len(email) == 0:
            raise ExtInvalidEmailAddress()
        return email
    
    
class ExtPassword(ExtString):
    name = "password"
    desc = "A password in cleartext"
    
    def lookup(self, _fun, cval):
        hardCodedSetOfAllowedCharacters = '0123456789abcdefghijklmnopqrstuvwxyzzABCDEFGHIJKLMNOPQRSTUVWXYZ~!@#$%^&*()_+'
        if (len(cval) < 8):
            raise ExtBadPassword("password is too short", cval)
        if any(passChar not in hardCodedSetOfAllowedCharacters for passChar in cval):
            raise ExtBadPassword("password contains illegal characters", cval)
        return cval
    
    
# The user record itself
class ExtUser(ExtUserId):
    name = "user"
    desc = "A User record, identified by its ID"

    # Defines how we look up the user. This method is called in the context
    # of an RPCC function
    # Parameters are;
    #     fun: RPCC function context
    #    cval: The value of the user identifier sent to the function
    def lookup(self, fun, cval):
        # Hand over the lookup to the peron_manager
        return fun.user_manager.get_user(cval)
    
    #
    # The output function is the opposite of a lookup. It takes a user record
    # and returns its identifier
    def output(self, _fun, obj):
        # print "User output", obj, obj.__dict__
        return obj.oid

    
# Function to create a user record.
class UserCreate(SessionedFunction):
    extname = "user_create"
    params = [("id", ExtUserId, "User identifier"),
              ("firstname", ExtString, "First name"),
              ("lastname", ExtString, "Last name"),
              ("email", ExtEmailAddress, "Email address"),
              ("password", ExtPassword, "Password")]
    desc = "Creates a user record"
    returns = (ExtNull)

    def do(self):
        self.user_manager.create_user(self.id, self.firstname, self.lastname, self.email, self.password)
        
        
# Function to remove a user record
class UserRemove(SessionedFunction):
    extname = "user_remove"
    params = [("user", ExtUser, "User to remove")] 
    desc = "Removes a user from the database"
    
    returns = (ExtNull)
    
    def do(self):
        self.user_manager.remove_user(self.user)  


class User(Model):
    name = "user"  
    exttype = ExtUser  
    id_type = unicode  

    def init(self, *args, **_kwargs):  
        a = list(args)
        self.oid = a.pop(0) 
        self.firstname = a.pop(0)
        self.lastname = a.pop(0)
        self.email = a.pop(0)
        self.password = a.pop(0)

    # Access functions
    @template("user", ExtUser)
    def get_user(self):
        return self

    @template("firstname", ExtString)
    def get_firstname(self):
        return self.firstname
    
    @template("lastname", ExtString)
    def get_lastname(self):
        return self.lastname
    
    @template("email", ExtEmailAddress)
    def get_email(self):
        return self.email
    
    @template("password", ExtPassword)
    def get_password(self):
        return "*****"
    
    # Uopdate functions
    @update("email", ExtEmailAddress)
    def set_email(self, new_email):
        q = "UPDATE users SET email=:email WHERE id=:id"
        self.db.put(q, id=self.oid, email=new_email)
        
    @update("firstname", ExtString)
    def set_firstname(self, firstname):
        q = "UPDATE users SET firstname=:firstname WHERE id=:id"
        self.db.put(q, id=self.oid, firstname=firstname)
        
    @update("lastname", ExtString)
    def set_lastname(self, lastname):
        q = "UPDATE users SET lastname=:lastname WHERE id=:id"
        self.db.put(q, id=self.oid, lastname=lastname)
        
    @update("password", ExtPassword)
    def set_password(self, password):
        q = "UPDATE users SET password=:password WHERE id=:id"
        self.db.put(q, id=self.oid, password=self.user_manager.pwhash(password))
            
            
class UserManager(AuthenticationManager):
    name = "user_manager"
    manages = User

    model_lookup_error = ExtNoSuchUserError
    
    def init(self, *args, **kwargs):
        self._model_cache = {}
        return AuthenticationManager.init(self, *args, **kwargs)
    
    def model(self, oid):
        return Manager.model(self, oid)  # Bypass the model method in AuthenticationManager
    
    @classmethod
    def base_query(cls, dq):
        dq.select("ds.id", "ds.firstname", "ds.lastname", "ds.email", "ds.password")
        dq.table("users ds")
        return dq

    def get_user(self, user_id):
        return self.model(user_id)

    def search_select(self, dq):
        dq.table("users ds")
        dq.select("ds.id")

    @search("user", StringMatch)
    def s_user(self, dq):
        dq.table("users ds")
        return "ds.id"
    
    @search("firstname", StringMatch)
    def s_firstname(self, dq):
        dq.table("users ds")
        return "ds.firstname"
        
    @search("lastname", StringMatch)
    def s_lastname(self, dq):
        dq.table("users ds")
        return "ds.lastname"
        
    @search("email", StringMatch)
    def s_email(self, dq):
        dq.table("users ds")
        return "ds.email"
    
    def create_user(self, user_id, firstname, lastname, email, password):  
        q = """INSERT INTO users (id, firstname, lastname, email, password) 
               VALUES (:user_id, :firstname, :lastname, :email, :pwhash)"""
        try:
            pwhash = UserAuthenticationManager.pwhash(password)
            self.db.put(q, user_id=user_id, firstname=firstname, lastname=lastname, email=email, pwhash=pwhash)
            
        except IntegrityError, e:
            print e
            raise ExtUserAlreadyExistsError()
        
    def remove_user(self, user):
        
        q = """DELETE FROM users WHERE id=:id"""
        self.db.put(q, id=user.oid)
