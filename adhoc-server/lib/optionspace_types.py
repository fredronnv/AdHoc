'''
Created on 24 maj 2017

@author: bernerus
'''

from rpcc import ExtString, ExtEnum, ExtOrNull


class ExtOptionspaceName(ExtString):
    name = "optionspace-name"
    desc = "Name of an optionspace"
    regexp = "^[-a-zA-Z0-9_]+$"


class ExtOptionspaceType(ExtEnum):
    name = "optionspace-type"
    desc = "Type of an optionspace"
    values = ['vendor', 'site']
    
  
class ExtOrNullOptionspace(ExtOrNull):
    name = "group_option_space"
    desc = "An option space, or null"
    typ = ExtOptionspaceName
    

class ExtOptionspace(ExtOptionspaceName):
    name = "optionspace"
    desc = "An optionspace instance"

    def lookup(self, fun, cval):
        return fun.optionspace_manager.get_optionspace(str(cval))

    def output(self, fun, obj):
        return obj.oid
