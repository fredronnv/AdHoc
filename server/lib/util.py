#!/usr/bin/env python2.6

# $Id$

from rpcc import ExtString, ExtList, ExtStruct, ExtType, ExtInteger, \
                 Manager, Model, Guard, AccessGranted, CacheInFunction, DecisionReferred, AnyGrants, \
                 ExtError, ExtLookupError, ExtExpectedStructError, ExtOutputError, ExtValueError
import re
import socket


class ExtHostName(ExtString):
    name = "host-name"
    desc = "Name of a host"
    regexp = r"^[-a-zA-Z0-9_]+$"
    regexp = r"^[012][0-9]{3}(0[1-9]|1[012])(0[1-9]|[12][0-9]|3[01])-[0-9]{3}[A-Z]{1,2}$"
    maxlen = 14
    minlen = 12
  
    
class ExtHostList(ExtList):
    name = "host-list"
    desc = "List of host names"
    typ = ExtHostName
    

class AdHocManager(Manager):
    """ Intermediate class to harbour methods common to all AdHoc Managers """
    approve_config = False
    
    def rename_object(self, obj, new_name):
        oid = obj.oid
        obj.oid = new_name
        del(self._model_cache[oid])
        self._model_cache[new_name] = obj
        
    def approve(self, approve_config=None):
        if self.approve_config or approve_config:
            self.logger.debug("CONFIG APPROVAL CHECK:")
            self.dhcp_manager.check_config()
        pass
    
    
class AdHocModel(Model):
    """ Intermediate class to harbour methods common to all AdHoc Models """
    
    def check_model(self):
        self.manager.approve()
        pass


class AdHocSuperuserGuard(Guard):
    """This guard says yes if session.authuser is someone in the given list"""
    
    superusers = ["viktor", "bernerus"]

    def check(self, obj, function):
        if function.session.authuser in self.superusers:
            return AccessGranted(CacheInFunction)
        function.privs_checked.add("superuser")
        return DecisionReferred(CacheInFunction)
    

class AllowUserWithPriv(Guard):
    def __init__(self, priv):
        self.priv = priv
        
    def check(self, obj, function):
        privs = function.db.get("SELECT privilege from account_privilege_map WHERE account=:account AND privilege=:privilege",
                                account=function.session.authuser, privilege=self.priv)
        if len(privs):
            return AccessGranted(CacheInFunction)
        else:
            function.privs_checked.add(self.priv)
            return DecisionReferred(CacheInFunction)

g_write_literal_option = AnyGrants(AllowUserWithPriv("write_literal_options"), 
                                   AdHocSuperuserGuard)
g_rename = AnyGrants(AllowUserWithPriv("rename_all_objects"), 
                     AdHocSuperuserGuard)


class ExtNoSuchDNSNameError(ExtLookupError):
    desc = "The DNS name is not defined"


class ExtDict(ExtStruct):
    typ = None

    def __init__(self, typ=None):            
        if typ is not None:
            if self.typ is not None:
                raise TypeError("When an ExtDict subclass has its .typ set, you cannot override it on instantiation. You use an ExtDict subclass just like an ExtString or ExtInteger subclass.")            
            self.typ = typ

        if self.typ is not None:
            self.name = self.typ.name + '-dict'
        else:
            self.name = None
    
    def check(self, function, rawval):
        if not isinstance(rawval, dict):
            raise ExtExpectedStructError(value=rawval)

        for (key, val) in rawval.items():
            try:
                ExtType.instance(self.typ).check(function, val)
            except ExtError as e:
                e.add_traceback(key)
                raise
            
    def output(self, function, value):
        converted = {}
        inval = value.copy()

        for (key, subval) in inval.items():
           
            typ = ExtType.instance(self.typ)
            try:
                converted[key] = typ.output(function, subval)
            except ExtOutputError as e:
                e.add_trace(self, "While converting key '%s'" % (key,))
                raise

        return converted
    
    
class ExtIpV4Address(ExtString):
    name = "ipv4-address"
    desc = "An IPv4 address using dotted decimal representation"
    regexp = "^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"




class ExtIPAddress(ExtString):
    name = "ip-address"
    desc = "An IP address specified either as a numeric IP Address or a DNS name"
    regexp_num = "(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
    regexp_dns = "(?=^.{1,254}$)(^(?:(?!\d+\.)[a-zA-Z0-9_\-]{1,63}\.?)+(?:[a-zA-Z]{2,})$)"
    regexp = "^" + regexp_num + "|" + regexp_dns + "$"
    
    def lookup(self, fun, cval):
        
        if re.match("^" + self.regexp_num + "$", cval):
            return cval
        
        try:
            dummy = socket.gethostbyname(cval)
            
        except socket.gaierror:
            raise ExtNoSuchDNSNameError()
        return cval

    
class ExtIPAddressList(ExtList):
    name = "ip-address-array"
    desc = "List of IP addresses"
    typ = ExtIPAddress
    
    
class ExtIntegerList(ExtList):
    name = "integer-array"
    desc = "List of integers"
    typ = ExtInteger

    
class ExtLiteralOption(ExtStruct):
    name = "literal-option-data"
    desc = "Data for a literal option"
    
    mandatory = {'value': (ExtString, "Literal text of the option"),
                 'changed_by': (ExtString, "CID of creator"),
                 'id': (ExtInteger)
                 }


class ExtLiteralOptionList(ExtList):
    name = "literal-option-list"
    desc = "List of literal options"
    typ = ExtLiteralOption
    

class ExtOptionList(ExtList):
    typ = ExtString
    name = "option-list"
    desc = "A list of option names"

    def __init__(self, typ=None, **kwargs):            
        if typ is not None:
            if self.typ is not None:
                raise TypeError("When an ExtList subclass has its .typ set, you cannot override it on instantiation. You use an ExtList subclass just like an ExtString or ExtInteger subclass.")            
            self.typ = typ

        if "typ" in kwargs:
            self.typ = kwargs.pop("typ")

        if self.typ is not None:
            self.name = "option" + '-list'
 
            
class ExtNoSuchAccountError(ExtLookupError):
    desc = "No such account exists."
    
    
class ExtAccountAlreadyExistsError(ExtLookupError):
    desc = "The account is already registered"
    
    
class ExtAccountInUseError(ExtValueError):
    desc = "The account is referred to by other objects. It must not destroyed"    
   
            
class ExtAccountName(ExtString):
    name = "account-name"
    desc = "Name of an account"
    regexp = "^[a-z][-a-z0-9_]{0,8}$"


class ExtAccount(ExtAccountName):
    name = "account"
    desc = "An account"

    def lookup(self, fun, cval):
        return fun.account_manager.get_account(str(cval))

    def output(self, fun, obj):
        return obj.oid


class ExtAccountList(ExtList):
    name = "account-list"
    desc = "List of account names"
    typ = ExtAccountName
