#!/usr/bin/env python2.6

from exttype import *

class ExtFunctionName(ExtString):
    name = "function-name"
    desc = "A string containing the name of a function this server exposes."

    def lookup(self, server, function, val):
        if function.api.has_function(val):
            return val
        raise ExtValueError("Unknown function", value=val)


class ExtSession(ExtString):
    name = "session"
    desc = """Execution context. See session_start()."""
    regexp = '(singlecall)|([a-zA-Z0-9]+)'

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




