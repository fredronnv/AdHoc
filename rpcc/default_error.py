#!/usr/bin/env python

from exterror import *  # @UnusedWildImport


class ExtNoSuchSessionError(ExtLookupError):
    desc = 'No session by that id exists.'


class ExtNoSuchFunctionError(ExtLookupError):
    desc = 'No function by that name is callable on the server in the api version you selected'


class ExtNoSuchAPIVersionError(ExtLookupError):
    desc = 'No such API version exists.'


class ExtNoSuchMutexError(ExtLookupError):
    desc = "No such mutex exists."


class ExtMutexNotHeldError(ExtRuntimeError):
    desc = "You tried to release a mutex that you do not hold, and did not specify the force flag."


class ExtMutexHeldError(ExtRuntimeError):
    desc = "You tried to acquire a mutex that another session already holds, and did not specify the force flag"
