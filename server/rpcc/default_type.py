#!/usr/bin/env python2.6

import exttype
import exterror
import default_error
import re


class ExtFunctionName(exttype.ExtString):
    name = "function-name"
    desc = "A string containing the name of a function this server exposes."

    def lookup(self, fun, cval):
        if fun.api.has_function(cval):
            return cval
        raise default_error.ExtNoSuchFunctionError(value=cval)


class ExtSession(exttype.ExtString):
    name = "session"
    desc = """Execution context. See session_start()."""
    regexp = '[a-zA-Z0-9]{40}'

    def lookup(self, fun, cval):
        try:
            return fun.session_manager.model(cval)
        except:
            raise
            raise default_error.ExtNoSuchSessionError(value=cval)

    def output(self, function, sesn):
        return sesn.oid


class ExtLikePattern(exttype.ExtString):
    name = "like-pattern"
    desc = "A pattern where % is 0, 1 or more characters and _ is exactly one character."


class ExtGlobPattern(exttype.ExtString):
    name = "glob-pattern"
    desc = "A pattern where * is 0, 1 or more characters and ? is exactly one character."


class ExtRegexpMatch(exttype.ExtString):
    name = "regexp-pattern"
    desc = "A regexp."

    def check(self, fun, rawval):
        try:
            re.compile(rawval)
        except:
            raise exterror.ExtValueError("Invalid regexp pattern")


class ExtSessionInfo(exttype.ExtStruct):
    name = 'session-info'

    mandatory = {'session': ExtSession,
                 'authuser': exttype.ExtOrNull(exttype.ExtString),
                 'expires': exttype.ExtDateTime}


class ExtServerVersion(exttype.ExtStruct):
    name = "server-version-type"

    mandatory = {
        'service': exttype.ExtString,
        'major': exttype.ExtString,
        'minor': exttype.ExtString
        }


class ExtAPIVersion(exttype.ExtStruct):
    name = "api-version"
    desc = "A version of the public API"

    mandatory = {
        "major": exttype.ExtInteger,
        "minor": exttype.ExtInteger
        }


class ExtDocTypename(exttype.ExtString):
    name = "doc-typename"
    regexp = "[-a-z0-9_|]+"


class ExtDocParamname(ExtDocTypename):
    name = "doc-parameter-name"
    regexp = r"^[-A-Za-z0-9_|]+$"


class ExtDocBasetype(exttype.ExtEnum):
    name = "doc-basetype"
    values = ("string", "enum", "integer", "null", "boolean", "list",
              "struct", "nullable")


class ExtDocParameter(exttype.ExtStruct):
    name = "doc-parameter"
    desc = "A (name, type, description) tuple, also used for the single (type, description) case of return values."

    mandatory = {
        "type_name": ExtDocTypename
        }

    optional = {
        "name": ExtDocParamname,
        "description": exttype.ExtString
        }


class ExtDocTypedef(exttype.ExtStruct):
    name = "doc-typedef"
    desc = "A type definition, matching a type name to a definition"

    mandatory = {
        "name": ExtDocTypename,
        "base": ExtDocBasetype,
        }

    optional = {
        "regexp": (exttype.ExtString, "For strings: constraining regexp"),
        "maxlen": (exttype.ExtInteger, "For strings: maximum length"),
        "values": (exttype.ExtList(exttype.ExtString), "For enums: valid values"),
        "min": (exttype.ExtInteger, "For integers: minimum value (inclusive)"),
        "max": (exttype.ExtInteger, "For integers: maximum value (inclusive)"),
        "subtype": (ExtDocTypename, "For nullable: type of non-null, for lists: type of elements"),
        "mandatory": (exttype.ExtList(ExtDocParameter), "For structs: list of mandatory members"),
        "optional": (exttype.ExtList(ExtDocParameter), "For structs: list of optional members")
        }


class ExtDocFunction(exttype.ExtStruct):
    name = "doc-function"
    desc = "Top-level struct for documenting a function"

    mandatory = {
        "function": ExtFunctionName,
        "parameters": exttype.ExtList(ExtDocParameter),
        "returns": ExtDocParameter,
        "types": exttype.ExtList(ExtDocTypedef)
        }

    optional = {
        "description": exttype.ExtString,
        }


class ExtMutexName(exttype.ExtString):
    name = "mutex-name"
    desc = "A string valid for use as the name of a mutex"
    regexp = "[-_a-z0-9]{1,64}"


class ExtMutex(ExtMutexName):
    name = "mutex"
    desc = "A mutex, identified by its name"

    def lookup(self, fun, cvar):
        return fun.mutex_manager.model(cvar)

    def output(self, fun, m):
        return m.oid


class ExtMutexState(exttype.ExtEnum):
    name = "mutex-state"
    desc = "State of a mutex"

    values = ["held", "free"]


class ExtMutexInfo(exttype.ExtStruct):
    name = "mutex-info"
    desc = "Information about a mutex"

    mandatory = {
        "mutex": ExtMutex,
        "last_change": exttype.ExtDateTime,
        "state": ExtMutexState,
        "forced": exttype.ExtBoolean
        }

    optional = {
        "holder": exttype.ExtString,
        }


class ExtMutexVarName(exttype.ExtString):
    name = "mutex-var-name"
    desc = "A mutex variable name"
    regexp = "[-_a-z0-9]+"


class ExtMutexStringVar(ExtMutexVarName):
    name = "mutex-string-var"
    desc = "A mutex string variable"

    # This only works if a mutex has already been set for the Function.
    def lookup(self, fun, cvar):
        return fun.mutex.get_string_variable(cvar)

    def output(self, fun, val):
        return val.name


class ExtMutexStringsetVar(ExtMutexVarName):
    name = "mutex-stringset-var"
    desc = "A mutex string-set variable"

    # This only works if a mutex has already been set for the Function.
    def lookup(self, fun, cvar):
        return fun.mutex.get_stringset_variable(cvar)

    def output(self, fun, val):
        return val.name


class ExtWatchdogName(exttype.ExtString):
    name = "watchdog-name"
    desc = "A string valid for use as a name for a watchdog"
    regexp = "[-_a-z0-9]+{1,64}"


class ExtWatchdog(ExtWatchdogName):
    name = "watchdog"
    desc = "The name of a watchdog, belonging to a mutex and only visible to the current holder of that mutex"

    # This only works if a mutex has already been set for the Function.
    def lookup(self, fun, cvar):
        return fun.mutex.get_watchdog(cvar)


class ExtWatchdogState(exttype.ExtString):
    name = "watchdog-state"
    desc = "The state of a watchdog"

    values = ["stopped", "running", "warning", "error"]


class ExtWatchdogInfo(exttype.ExtStruct):
    name = "watchdog-info"
    desc = "Information about a watchdog"

    mandatory = {
        "state": ExtWatchdogState,
        "warning_at": exttype.ExtOrNull(exttype.ExtDateTime),
        "error_at": exttype.ExtOrNull(exttype.ExtDateTime)
        }


class ExtEvent(exttype.ExtInteger):
    pass

#class ExtEventType(exttype.ExtEnum):
#    values = ["create", "update", "destroy", "call", "watchdog", "marker"]
