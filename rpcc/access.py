
from error import AccessError

class Access(object):
    """Class representing one particular access control for a Function.

    The Access class implements Function-level access. Subclasses have
    their .check() methods called to grant or deny access to an entire
    Function.

    It is strongly recommended that this only be used for very broad 
    checks such as 'user is logged in' or 'call comes from the company
    network'. The real meat of access control is recommended to be
    performed in the model using guards.
    """

    # The name and description visible in external documentation.
    name = ''
    desc = ''

    def __init__(self, server, function):
        self.server = server
        self.function = function

    def delegate(self, cls):
        """Delegate decision to another Access class."""
        cls(self.server, self.function).check()

    def check(self):
        raise AccessError("Access denied")

