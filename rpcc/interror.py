#!/usr/bin/env python2.6
"""
Internal errors - these errors should never be shown externally. Since 
they are not ExtError subclasses, they will be converted to 
ExtInternalError should they bubble up in a function call (which they
shouldn't normally do).

"""


class IntAPINotFoundError(ValueError):
    pass


class IntAPIValidationError(ValueError):
    pass


class IntInvalidUsageError(TypeError):
    pass
