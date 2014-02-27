#!/usr/bin/env python2.6
from rpcc import *

   
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
    regexp_dns = "(([a-zA-Z]{1})|([a-zA-Z]{1}[a-zA-Z]{1})|([a-zA-Z]{1}[0-9]{1})|([0-9]{1}[a-zA-Z]{1})|([a-zA-Z0-9][a-zA-Z0-9-_]{1,61}[a-zA-Z0-9]))\.([a-zA-Z]{2,6}|[a-zA-Z0-9-]{2,30}\.[a-zA-Z]{2,6})"
    regexp = "^" + regexp_num + "|" + regexp_dns + "$"
    
    def lookup(self, fun, cval):
        
        if re.match("^" + self.regexp_num + "$", cval):
            return cval
        
        try:
            dummy = socket.gethostbyname(cval)
            
        except socket.gaierror:
            raise ExtNoSuchDNSNameError()
        return cval
