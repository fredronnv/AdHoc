#!/usr/bin/env python2.6

from exttype import *

class ExtFunctionName(ExtString):
    name = "function-name"
    desc = "A string containing the name of a function this server exposes."

    def lookup(self, fun, cval):
        if fun.api.has_function(cval):
            return cval
        raise ExtValueError("Unknown function", value=cval)

class ExtSession(ExtString):
    name = "session"
    desc = """Execution context. See session_start()."""
    regexp = '[a-zA-Z0-9]{40}'

    def lookup(self, fun, cval):
        try:
            return fun.server.session_store.get_session(fun, cval)
        except:
            raise ExtInvalidSessionIDError(value=val)

    def output(self, function, sesn):
        return sesn.id

class ExtDateTime(ExtString):
    name = 'datetime'
    regexp = '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}$'
    desc = 'A date and time in YYYY-MM-DDTHH:MM:SS format, e.g. 2007-04-14T13:54:22'
    
    def convert(self, function, rawval):
        import datetime
        
        try:
            date, tm = val.split('T')
            y, mo, d = [int(i) for i in date.split('-')]
            h, mi, s = [int(i) for i in tm.split(':')]
            return datetime.datetime(y, mo, d, h, mi, s)
        except:
            raise ExtValueError("Not a valid datetime")

    def output(self, fun, value):
        return value.isoformat()[:19]

class ExtLikePattern(ExtString):
    name = "like-pattern"
    desc = "A pattern where % is 0, 1 or more characters and _ is exactly one character."

class ExtGlobPattern(ExtString):
    name = "glob-pattern"
    desc = "A pattern where * is 0, 1 or more characters and ? is exactly one character."

class ExtRegexpMatch(ExtString):
    name = "regexp-pattern"
    desc = "A regexp."

    def check(self, fun, rawval):
        try:
            re.compile(rawval)
        except:
            raise ExtValueError("Invalid regexp pattern")

class ExtSessionInfo(ExtStruct):
    name = 'session-info'

    mandatory = {'session': ExtSession,
                 'authuser': ExtOrNull(ExtString),
                 'expires': ExtDateTime}

class ExtServerVersion(ExtStruct):
    name = "server-version-type"
    
    mandatory = {
        'service': ExtString,
        'major': ExtString,
        'minor': ExtString
        }

class ExtAPIVersion(ExtStruct):
    name = "api-version"
    desc = "A version of the public API"

    mandatory = {
        "major": ExtInteger,
        "minor": ExtInteger
        }

class ExtDocTypename(ExtString):
    name = "doc-typename"
    regexp = "[-a-z_]+"

class ExtDocParamname(ExtDocTypename):
    name = "doc-parameter-name"

class ExtDocBasetype(ExtEnum):
    name = "doc-basetype"
    values = ("string", "enum", "integer", "null", "boolean", "list", 
              "struct", "nullable")

class ExtDocParameter(ExtStruct):
    name = "doc-parameter"
    desc = "A (name, type, description) tuple, also used for the single (type, description) case of return values."
    
    mandatory = {
        "type_name": ExtDocTypename
        }

    optional = {
        "name": ExtDocParamname,
        "description": ExtString
        }

class ExtDocTypedef(ExtStruct):
    name = "doc-typedef"
    desc = "A type definition, matching a type name to a definition"

    mandatory = {
        "name": ExtDocTypename,
        "base": ExtDocBasetype,
        }

    optional = {
        "regexp": (ExtString, "For strings: constraining regexp"),
        "maxlen": (ExtInteger, "For strings: maximum length"),
        "values": (ExtList(ExtString), "For enums: valid values"),
        "min": (ExtInteger, "For integers: minimum value (inclusive)"),
        "max": (ExtInteger, "For integers: maximum value (inclusive)"),
        "subtype": (ExtDocTypename, "For nullable: type of non-null, for lists: type of elements"),
        "mandatory": (ExtList(ExtDocParameter), "For structs: list of mandatory members"),
        "optional": (ExtList(ExtDocParameter), "For structs: list of optional members")
        }

class ExtDocFunction(ExtStruct):
    name = "doc-function"
    desc = "Top-level struct for documenting a function"

    mandatory = {
        "function": ExtFunctionName,
        "parameters": ExtList(ExtDocParameter),
        "returns": ExtDocParameter,
        "types": ExtList(ExtDocTypedef)
        }

    optional = {
        "description": ExtString,
        }

class ExtMutex(ExtString):
    name = "mutex"
    desc = "A mutex, identified by its name"

    
