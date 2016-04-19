#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

from rpcc import *
from __builtin__ import classmethod


# Model description of a host record containing first and last names and an email
#
# Possible errors 
class ExtNoSuchHostError(ExtLookupError):
    desc = "No such host is known."
    

class ExtHostAlreadyExistsError(ExtLookupError):
    desc = "The host id already exists"


class ExtInvalidEmailAddress(ExtLookupError):
    desc = "The email address is invalid"
    

class ExtBadPassword(ExtLookupError):
    desc = "The password given dows not follow the requirements"
  
    
# Desription of how we identify the host    
class ExtHostId(ExtString):
    name = "host-id"
    desc = "ID of a host"
    regexp = "^[a-z]{1,8}$"
  

# The host record itself
class ExtHost(ExtHostId):
    name = "host"
    desc = "A Host record, identified by its ID"

    # Defines how we look up the host. This method is called in the context
    # of an RPCC function
    # Parameters are;
    #     fun: RPCC function context
    #    cval: The value of the host identifier sent to the function
    def lookup(self, fun, cval):
        # Hand over the lookup to the peron_manager
        return fun.host_manager.get_host(cval)
    
    #
    # The output function is the opposite of a lookup. It takes a host record
    # and returns its identifier
    def output(self, _fun, obj):
        # print "Host output", obj, obj.__dict__
        return obj.oid

    
# Function to create a host record.
class HostCreate(SessionedFunction):
    extname = "host_create"
    params = [("id", ExtHostId, "Host identifier"),
              ]
    desc = "Creates a host record"
    returns = (ExtNull)

    def do(self):
        self.host_manager.create_host(self.id, self.firstname, self.lastname, self.email, self.password)
        
        
# Function to remove a host record
class HostRemove(SessionedFunction):
    extname = "host_remove"
    params = [("host", ExtHost, "Host to remove")] 
    desc = "Removes a host from the database"
    
    returns = (ExtNull)
    
    def do(self):
        self.host_manager.remove_host(self.host)  


class Host(Model):
    name = "host"  
    exttype = ExtHost  
    id_type = unicode  

    def init(self, *args, **_kwargs):  
        a = list(args)
        self.oid = a.pop(0) 
        self.firstname = a.pop(0)
        self.lastname = a.pop(0)
        self.email = a.pop(0)
        self.password = a.pop(0)

    # Access functions
    @template("host", ExtHost)
    def get_host(self):
        return self

    @template("firstname", ExtString)
    def get_firstname(self):
        return self.firstname
    
    @template("lastname", ExtString)
    def get_lastname(self):
        return self.lastname
    
    @update("firstname", ExtString)
    def set_firstname(self, firstname):
        q = "UPDATE hosts SET firstname=:firstname WHERE id=:id"
        self.db.put(q, id=self.oid, firstname=firstname)
        
    @update("lastname", ExtString)
    def set_lastname(self, lastname):
        q = "UPDATE hosts SET lastname=:lastname WHERE id=:id"
        self.db.put(q, id=self.oid, lastname=lastname)

               
class HostManager(AuthenticationManager):
    name = "host_manager"
    manages = Host

    model_lookup_error = ExtNoSuchHostError
    
    def init(self, *args, **kwargs):
        self._model_cache = {}
        return AuthenticationManager.init(self, *args, **kwargs)
    
    def model(self, oid):
        return Manager.model(self, oid)  # Bypass the model method in AuthenticationManager
    
    @classmethod
    def base_query(cls, dq):
        dq.select("h.id", "h.colorcode", "h.ip", "h.dns", "h.placement", "h.os", "h.model", "h.serial", "h.roles", "h.mac", "h.tty", "h.services", ".function", "h.connections", 
                  "h.status", "h.inventory", "h.techresp", "h.admresp", "h.billing", "h.backup", "h.comment", "h.system" )
        dq.table("hosts h")
        return dq

    def get_host(self, host_id):
        return self.model(host_id)

    def search_select(self, dq):
        dq.table("hosts h")
        dq.select("h.id")

    @search("host", StringMatch)
    def s_host(self, dq):
        dq.table("hosts h")
        return "h.id"
    
    @search("placement", StringMatch)
    def s_placement(self, dq):
        dq.table("hosts h")
        return "h.placement"
    
    @search("model", StringMatch)
    def s_model(self, dq):
        dq.table("hosts h")
        return "h.model"
    
    @search("serial", StringMatch)
    def s_serial(self, dq):
        dq.table("hosts h")
        return "h.serial"
    
    @search("roles", StringMatch)
    def s_roles(self, dq):
        dq.table("roles r")
  
    def create_host(self, host_id, firstname, lastname, email, password):  
        q = """INSERT INTO hosts (id, firstname, lastname) 
               VALUES (:host_id, :firstname, :lastname)"""
        try:
            self.db.put(q, host_id=host_id, firstname=firstname, lastname=lastname)
            
        except IntegrityError, e:
            print e
            raise ExtHostAlreadyExistsError()
        
    def remove_host(self, host):
        q = """DELETE FROM hosts WHERE id=:id"""
        self.db.put(q, id=host.oid)
