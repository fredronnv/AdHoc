#!/usr/bin/env python2.6
from rpcc.exttype import *


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