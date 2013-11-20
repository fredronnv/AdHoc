
import datetime

from exttype import *
from default_type import *
from function import Function, SessionedFunction

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

class FunSessionStart(Function):
    """Default function to create a new session."""
    
    extname = 'session_start'
    params = []
    desc = "Creates a new session (execution context) for further calling. Returns an ID valid for a limited time for the current client address only."
    returns = (ExtSession, "A string that must be the first argument of any furter calls to perform in the context of this session.")
    
    def do(self):
        remote_ip = self.http_handler.client_address[0]
        sesnid = self.server.session_store.create_session(self, remote_ip)
        # Below makes the session id be logged together with the
        # session_start() call in the call log.
        self.session = self.server.session_store.get_session(self, sesnid)
        return self.session
    
class FunSessionStop(SessionedFunction):
    extname = 'session_stop'
    params = []
    desc = "Invalidates a session (execution context), making it unavailable for any furhter calls."
    returns = ExtNull
    
    def typed_do(self):
        self.server.kill_session(self.session)
        
class FunSessionInfo(SessionedFunction):
    extname = 'session_info'
    returns = (ExtSessionInfo, "Information about the supplied session")
    
    desc = "Returns information about the session (execution context)."

    def do(self):
        return {'session': self.session,
                'expires': self.session.expires,
                'authuser': self.session.authuser}

class FunSessionAuthLogin(SessionedFunction):
    extname = 'session_auth_login'
    params = [('username', ExtString, 'Username to authenticate as'),
              ('password', ExtString, 'Password to authenticate with')]

    returns = (ExtBoolean, "Will always be True - a failed login is returned as an error")

    desc = "Authenticates a session (execution context). If successful, further calls done in that context count as being made by the user whose username was given as argument to this call."

    def log_arguments(self, args):
        return ('*', args[1], '****')
    
    def do(self):
        ath = self.server.authenticator
        ath.login(self, self.session.id, self.username, self.password)
        return True

class FunSessionStartWithLogin(Function):
    extname = 'session_start_with_login'
    params = [('username', ExtString, 'Username to authenticate as'),
              ('password', ExtString, 'Password to authenticate with')]
    returns = (ExtSession, "Authenticated call context")

    desc = "Create a session and attempt to authenticate it returning the session if authentication succeeded."

    def log_arguments(self, args):
        return (args[0], '****')

    def do(self):
        remote_ip = self.handler.client_address[0]
        sesnid = self.server.session_store.create_session(self, remote_ip)
        # Below makes the session id be logged together with the
        # session_start() call in the call log.
        self.session = self.server.session_store.get_session(self, sesnid)

        try:
            ath = self.server.authenticator
            ath.login(self, self.session.id, self.username, self.password)
            return self.session
        except:
            self.server.authenticator.delete_session(self, self.session.id)
            raise
        
class FunSessionDeauth(SessionedFunction):
    extname = 'session_deauth'
    params = []
    returns = ExtNull

    desc = "De-authenticate, leavning the session unauthenticated."
    
    def do(self):
        self.server.authenticator.logout(self, self.session.id)


class FunServerListFunctions(Function):
    extname = 'server_list_functions'
    params = []
    returns = ExtList(ExtString)
    desc = 'Return a list of function names available on this server.'
    grants = None
    
    def do(self):
        return self.api.get_all_function_names()

class FunServerDocumentation(Function):
    extname = "server_documentation"
    params = [("function", ExtFunctionName, "Name of function to document")]
    returns = ExtString
    desc = "Returns a text-version of the documentation for a function."
    
    def do(self):
        return self.server.documentation.function_as_text(self.api.version, self.function)

class FunServerFunctionDefinition(Function):
    extname = "server_function_definition"
    params = [("function", ExtFunctionName, "Name of function to document")]
    returns = ExtDocFunction
    desc = "Returns a structured definition of the named function"
    
    def do(self):
        t = self.server.documentation.function_as_struct(self.api.version, self.function)
        print t
        return t

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

