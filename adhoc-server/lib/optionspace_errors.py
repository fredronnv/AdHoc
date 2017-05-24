'''
Created on 24 maj 2017

@author: bernerus
'''


from rpcc import ExtLookupError, ExtValueError


class ExtNoSuchOptionspaceError(ExtLookupError):
    desc = "No such optionspace exists."


class ExtOptionspaceAlreadyExistsError(ExtLookupError):
    desc = "The optionspace already exists"

    
class ExtOptionspaceInUseError(ExtValueError):
    desc = "The optionspace is referred to by other objects. It cannot be destroyed"    
