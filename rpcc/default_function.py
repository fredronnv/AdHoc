
import datetime

from exttype import *
from default_type import *
from function import Function, SessionedFunction

class ExtFunctionName(ExtString):
    name = "function-name"
    desc = "A string containing the name of a function this server exposes."

    def lookup(self, server, function, val):
        if function.api.has_function(val):
            return val
        raise ExtValueError("Unknown function", value=val)


class ExtSessionID(ExtString):
    name = "session-id"
    desc = """Execution context. See session_start()."""
    regexp = '(singlecall)|([a-zA-Z0-9]+)'

    def lookup(self, server, function, val):
        try:
            session = server.get_session(val, function.handler.client_address[0])
            session.extend_expiry_time()
            return session
        except:
            raise RPCInvalidSessionIDError(value=val)
            

class ExtDateTime(ExtString):
    name = 'datetime'
    regexp = '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}$'
    desc = 'A date and time in YYYY-MM-DDTHH:MM:SS format, e.g. 2007-04-14T13:54:22'
    
    def lookup(self, server, function, val):
        import datetime
        
        try:
            date, tm = val.split('T')
            y, mo, d = [int(i) for i in date.split('-')]
            h, mi, s = [int(i) for i in tm.split(':')]
            return datetime.datetime(y, mo, d, h, mi, s)
        except:
            raise ExtValueError("Not a valid datetime")

class ExtSessionInfo(ExtStruct):
    name = 'session-info'
    mandatory = {'authuser': ExtOrNull(ExtString),
                 'startup': ExtDateTime,
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

dummy = """
class ExtStructItemDocdictType(ExtStruct):
    name = "struct-item-definition"

    mandatory = {
        "name": (RPCStringType, "Item key/attribute name"),
        "type": None, # Filled in below due to mutual recursion
        "description": (RPCStringType, "Item description"),
        "optional": (RPCBooleanType, "Whether this is an optional type or not")
        }

class Sys_TypeDocdictType(RPCStructType):
    name = "type-definition"

    mandatory = {
        "dict_type": (RPCStringType, "Base type of this type definition"),
        }

    optional = {
        "name": (RPCStringType, "Type name"),
        "description": (RPCStringType, "Type description"),
        "min_value": (RPCIntegerType, "Minimum value (only integer-type)"),
        "max_value": (RPCIntegerType, "Maximum value (only integer-type)"),
        "maxlen": (RPCIntegerType, "Maximum length (only string-type)"),
        "regexp": (RPCStringType, "String regexp pattern (only string-type)"),
        "values": (RPCListType(RPCStringType), "Permissible values (only enum-type)"),
        # Filled below due to self-recursion.
        #"value_type": (Sys_TypeDocdictType, "Element type (only list-type)"),
        #"otherwise": (Sys_TypeDocdictType, "Value if not null (only ornull-type)"),
        "mandatory": (RPCListType(Sys_StructItemDocdictType), "List of mandatory items (only struct-type)"),
        "optional": (RPCListType(Sys_StructItemDocdictType), "List of optional items (only struct-type)"),
        }

Sys_TypeDocdictType.optional["value_type"] = (Sys_TypeDocdictType, "Element type (only list-type)")
Sys_TypeDocdictType.optional["otherwise"] = (Sys_TypeDocdictType, "Value if not null (only ornull-type)")
Sys_StructItemDocdictType.mandatory["type"] = (Sys_TypeDocdictType, "Item type definition")


class Sys_ParameterDocdictType(RPCStructType):
    name = "parameter-definition"

    mandatory = {
        "name": (RPCStringType, "The parameter name (not used in XMLRPC)"),
        "desc": (RPCStringType, "Parameter description"),
        "type": (Sys_TypeDocdictType, "Parameter value definition"),
        }

class Sys_FunctionDocdictType(RPCStructType):
    name = "function-definition"

    mandatory = {
        "name": (RPCStringType, "Public function name"),
        "description": (RPCStringType, "Function documentation"),
        "min_api_version": (Sys_APIVersionType, "Minimum API version where this function is available"),
        "return_type": (Sys_TypeDocdictType, "Return type definition"),
        "parameters": (RPCListType(Sys_ParameterDocdictType), "Definition of function parameters")
        }

    optional = {
        "max_api_version": (Sys_APIVersionType, "Maximum API version where this function is available"),
        }

"""

class FunServerURLAPI(Function):
    extname = 'server_url_api'

    desc = "Returns a struct indicating the protocol version of this URL. The version number is increased whenever changes programmatically visible to clients are made."
    params = []
    returns = (ExtServerVersion, "API version for current URL")

    grants = None

    def do(self):
        return {'service': self.server.service_name,
                'major': self.server.major_version,
                'minor': self.server.minor_version}

dummy = """
class Sys_Documentation(RPCTypedFunction):
    rpcname = 'server_documentation'
    desc = "Returns a string containing the documentation of the given function."
    params = [("function", FunctionNameType, "Function to return documentation for")]
    rettype = RPCStringType
    retdesc = "Function documentation as text"
    grants = None
    #retdesc = "Documentation of named function as text"

    def typed_do(self):
        fun = self.api.get_function_object(self.function, self.handler)
        return fun.documentation()
    

class Sys_DocumentationStruct(RPCTypedFunction):
    rpcname = 'server_documentation_struct'
    desc = "Returns a string containing the documentation of the given function."
    params = [("function", FunctionNameType, "Function to return documentation for")]
    rettype = Sys_FunctionDocdictType
    retdesc = "Function documentation as a structure"
    grants = None

    def typed_do(self):
        fun = self.api.get_function_object(self.function, self.handler)
        return fun.documentation_dict()
        

class Sys_XmlDocumentation(RPCTypedFunction):
    rpcname = 'server_xml_documentation'
    desc = "Returns a XML document containing the documentation of the given function."
    params = [("function", FunctionNameType, "Function to return documentation for")]
    rettype = RPCStringType
    retdesc = "Function documentation as XML"
    grants = None
    #retdesc = "Documentation of named function as text"

    def typed_do(self):
        generator = documentation.DocumentationGenerator()
        generator.document_function(self.server.functions[self.function])
        generator.close()
        return str(generator)


class Sys_XmlDocumentationAll(RPCTypedFunction):
    rpcname = 'server_xml_documentation_all'
    desc = "Returns a XML document containing the documentation for all functions."
    params = []
    rettype = RPCStringType
    retdesc = "Function documentation as XML"
    grants = None
    #retdesc = "Documentation of named function as text"

    def typed_do(self):
        generator = documentation.DocumentationGenerator()
        generator.document_functions(self.server.functions)
        generator.close()
        return str(generator)
"""

class FunSessionInfo(SessionedFunction):
    extname = 'session_info'
    params = [('session', ExtSessionID, "Execution context.")]
    desc = "Returns information about the session (execution context)."
    returns = (ExtSessionInfo, "Information about the supplied session")
    
    def typed_do(self):
        return {'authuser': self.session.authuser,
                'startup': self.session.get_create_time(),
                'expires': self.session.get_expiry_time(),
                'temporary': self.session.temporary,
                'id': self.session.get_id()}

class FunSessionStart(Function):
    """Default function to create a new session."""
    
    extname = 'session_start'
    params = []
    desc = "Creates a new session (execution context) for further calling. Returns an ID valid for a limited time for the current client address only."
    returns = (ExtSessionID, "A string that must be the first argument of any furter calls to perform in the context of this session.")
    
    def do(self):
        remote_ip = self.handler.client_address[0]
        sesn = self.server.create_session(remote_ip, function=self, temporary=False)
        # Below makes the session id be logged together with the
        # session_start() call in the call log.
        self.session = sesn
        return sesn.get_id()
    

class FunSessionStop(SessionedFunction):
    """Default function to destroy a session."""
    
    rpcname = 'session_stop'
    params = []
    desc = "Invalidates a session (execution context), making it unavailable for any furhter calls."
    rettype = ExtNull
    
    def typed_do(self):
        self.server.kill_session(self.session)
        

class FunSessionAuthLogin(SessionedFunction):
    extname = 'session_auth_login'
    params = [('username', ExtString, 'Username to authenticate as'),
              ('password', ExtString, 'Password to authenticate with')]

    desc = "Authenticates a session (execution context). If successful, further calls done in that context count as being made by the user whose username was given as argument to this call."
    returns = (ExtBoolean, "Will always be True - a failed login is returned as an error")

    def log_arguments(self, args):
        return ('*', args[1], '****')
    
    def do(self):
        return self.server.auth.login(self.session, self.username, self.password)


class FunSessionStartWithLogin(Function):
    extname = 'session_start_with_login'
    params = [('username', ExtString, 'Username to authenticate as'),
              ('password', ExtString, 'Password to authenticate with')]

    desc = "Create a session and attempt to authenticate it returning the session if authentication succeeded."
    rettype = (ExtSessionID, "Authenticated call context")

    def log_arguments(self, args):
        return (args[0], '****')

    def do(self):
        remote_ip = self.handler.client_address[0]
        sesn = self.server.create_session(remote_ip, function=self, temporary=False)
        # Below makes the session id be logged together with the
        # session_start() call in the call log.
        self.session = sesn

        try:
            self.server.auth.login(self.session, self.username, self.password)
            return self.session.get_id()
        except:
            self.server.kill_session(self.session)
            raise
        

class FunSessionDeauth(SessionedFunction):
    rpcname = 'session_deauth'
    params = []

    desc = "De-authenticate, leavning the session unauthenticated."
    returns = ExtNull
    
    def do(self):
        self.server.auth.logout(self.session)


class FunServerListFunctions(Function):
    rpcname = 'server_list_functions'
    params = []
    returns = ExtList(ExtString)
    desc = 'Return a list of function names available on this server.'
    grants = None
    
    def do(self):
        return self.api.get_all_function_names()

