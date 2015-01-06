
class IntAPIValidationError(Exception):
    pass

class IntAttributeDefitionsOverlapError(IntAPIValidationError):
    pass

class IntInvalidUsageError(Exception):
    pass
