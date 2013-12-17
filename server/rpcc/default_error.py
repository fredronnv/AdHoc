#!/usr/bin/env python

# Naming standard:
#
# ExtNoSuchFooError() - error when getting a non-existant Foo
# ExtFooAlreadyExists() - error when creating a Foo that already exists


from exterror import *


class ExtNoSuchSessionError(ExtLookupError):
    desc = 'No session by that id exists.'


class ExtNoSuchFunctionError(ExtLookupError):
    desc = 'No function by that name is callable on the server in the api version you selected'


class ExtNoSuchAPIVersionError(ExtLookupError):
    desc = 'No such API version exists.'


class ExtNoSuchMutexError(ExtLookupError):
    desc = "No such mutex exists."


class ExtMutexAlreadyExistsError(ExtValueError):
    desc = "A mutex by that name already exists"


class ExtMutexNotHeldError(ExtRuntimeError):
    desc = "You tried to release a mutex that you do not hold, and did not specify the force flag."


class ExtMutexHeldError(ExtRuntimeError):
    desc = "You tried to acquire a mutex that another session already holds, and did not specify the force flag"


class ExtNoSuchMutexVariableError(ExtLookupError):
    desc = "No such mutex variable exists"


class ExtMutexVariableAlreadyExistsError(ExtValueError):
    desc = "A mutex variable by that name already exists"


class ExtMutexVariableIsWrongTypeError(ExtValueError):
    desc = "The mutex variable you tried to operate on is of the wrong type for the operation you tried to perform"


class ExtNoSuchMutexVariableValueError(ExtLookupError):
    desc = "You tried to remove a value which wasn't present"


class ExtNoSuchWatchdogError(ExtLookupError):
    desc = "No such watchdog exists"


class ExtWatchdogAlreadyExistsError(ExtValueError):
    desc = "A watchdog by that name already exists for that mutex"

