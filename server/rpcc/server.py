
import os
import time
import socket
import traceback
import threading
import SocketServer
import BaseHTTPServer
import logging

import event
import access
import session
import exterror
import protocol
import response
import api_handler
import documentation
import authentication
import request_handler
import default_function
import exttype
from exterror import ExtInternalError

from function import Function
from database_description import VType
from mutex import MutexManager

try:
    import ssl
except:
    pass


class SSLConfig(object):
    keyfile = None
    certfile = None

    def __init__(self, keyfile=None, certfile=None):
        if keyfile:
            self.keyfile = keyfile
        if certfile:
            self.certfile = certfile

    def wrap_socket(self, raw_socket):
        return ssl.wrap_socket(raw_socket, 
                               keyfile=self.keyfile, 
                               certfile=self.certfile, 
                               server_side=True,
                               ssl_version=ssl.PROTOCOL_TLSv1)


class Server(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    """An RPCC server class with session handling and thread-locks.

    The server listens on a host/port and handles HTTP/HTTPS
    connections coming in on that port. For each connection, a new
    thread is created, and a handler is created depending on the
    request URL.

    There are a few default handlers installed - see code comments
    for a list and an explanation.

    The important class attributes are:

    handler_class
        Default RPCRequestHandler (sub)class to use for decoding/encoding
        requests. Can be overriden when instantiating the RPCServer.
    """

    # A RequestHandler starts up in a separate thread for each
    # incoming connection, and then calls back to the Server instance
    # for actual processing (it's only used because that's how
    # BaseHTTPServer from Python's standard library works). You'll
    # seldom want to override this.

    handler_class = request_handler.RawRequestHandler

    manager_classes = []
    model_classes = []

    api_version_comments = {}

    # Service name, visible in the WSDL portType and in server_get_version().
    service_name = 'unknown'

    # Base for schema namespace. If set, the WSDL:s targetNamespace
    # and SOAP-response namespace will be soap_schema_ns_base + version,
    # else the server URL will be used as base.
    soap_schema_ns_base = None

    # Default protocol handlers, added on startup by automatic calls to
    # .add_protocol_handler(). You can add your own by calling that
    # method yourself.

    default_protocol_handlers = [
        ('/RPC2', protocol.XMLRPCProtocol),
        ('/xmlrpc', protocol.XMLRPCProtocol),
        # ('__POST__', protocol.XMLRPCProtocol),
        ('/apache-xmlrpc', protocol.ApacheXMLRPCProtocol),
        ('/json', protocol.JSONProtocol),
        ('/WSDL', protocol.WSDLProtocol),
        ('/SOAP', protocol.SOAPProtocol),
        ('/api', protocol.FunctionDefinitionProtocol),

        # ('/spnego+xmlrpc', RPCKRB5XMLRPCProtocolHandler),
        # ('/spnego+apache-xmlrpc', RPCKRB5ApacheXMLRPCProtocolHandler),
        # ('/spnego+SOAP', RPCKRB5SOAPProtocolHandler),
    ]

    # Environment variable prefix. All configuration for this server is
    # prefixed by this string. Default is "RPCC_", so
    # the default Databases have config in RPCC_DB_USER and so on.
    envvar_prefix = "RPCC_"

    # Sensitive information such as session id:s are protected by this
    # guard. Set a guard specific for your application's authorization
    # model (use access.DefaultSuperuserGuard and
    # authentication.DefaultSuperuserOnlyAuthenticator) if you want to
    # be able to read this information but don't have an authorization
    # model of your own.
    
    superuser_guard = access.NeverAllowGuard()

    def __init__(self, address, port, ssl_config=None, handler_class=None, generic_password=None, logger=None):
        self.database = None
        self.digs_n_updates = False
        self.sessions_enabled = False
        self.mutexes_enabled = False
        self.events_enabled = False
        self.tables_checked = False

        self.logger = logger if logger else logging.getLogger(__name__)

        self.manager_by_name = {}
        for cls in self.manager_classes:
            self.manager_by_name[cls._name()] = cls

        self.model_by_name = {}
        for cls in self.model_classes:
            self.model_by_name[cls._name()] = cls

        self.protocol_handlers = {}
        self.running_functions = {}

        if handler_class:
            self.handler_class = handler_class

        SocketServer.BaseServer.__init__(self, (address, port),
                                         self.handler_class)

        self.instance_hostname = socket.gethostname()
        self.instance_address = address
        self.instance_port = port

        self.server_id = "%s:%s:%d" % (self.instance_hostname,
                                       self.instance_address,
                                       self.instance_port)

        rawsocket = socket.socket(self.address_family, self.socket_type)

        if ssl_config:
            self.ssl_enabled = True
            self.ssl_config = ssl_config
            self.socket = self.ssl_config.wrap_socket(rawsocket)
        else:
            self.ssl_enabled = False
            self.socket = rawsocket

        self.server_bind()
        self.server_activate()

        self.thread_lock = threading.RLock()
        self.api_handler = api_handler.APIHandler(self)

        self.add_default_protocol_handlers()
        self.documentation = documentation.Documentation(self)
        self.generic_password = generic_password

    def config(self, varname, **kwargs):
        envvar = (self.envvar_prefix + varname).upper()
        if "default" in kwargs:
            return os.environ.get(envvar, kwargs["default"])
        else:
            return os.environ[envvar]

    ##
    # Function handling.
    ##
    def log_success(self, handler, function_name, function_object, params, result, call_time):
        """Log succesful calls. Called if the Function subclass
        instance's .do() did not raise an exception.
        """
        self.logger.debug("SUCCESS (%.2fs) %s%s => %s" % (call_time, function_name, params, result))

    def log_error(self, handler, function_name, function_object, params, result, exc, call_time):
        """Log exceptions. Called id the Function subclass
        instance's .do()-method raised an exception.
        """
        self.logger.error("ERROR (%.2fs) %s%s => %s" % (call_time, function_name, params, result))

    def get_running_functions(self):
        # print "THREAD_LOCK A:", self.thread_lock, hex(id(self.thread_lock))
        with self.thread_lock:
            res = []
            now = time.time()
            for (fun, (args, starttime, apiversion)) in self.running_functions.items():
                if hasattr(fun, "session"):
                    sid = fun.session.id[:8]
                else:
                    sid = '????????'

                res.append({'function': fun.rpcname, 'args': fun.log_arguments(args), 'runtime': now - starttime, 'api_version': apiversion, 'masked_session': sid})

            return res

    def function_start(self, funobj, args, starttime, api_version):
        # print "Function_start", funobj.__dict__, args, api_version
        # print "THREAD_LOCK B:", self.thread_lock, hex(id(self.thread_lock))
        with self.thread_lock:
            self.running_functions[funobj] = (args, starttime, api_version)

    def function_stop(self, funobj):
        # print "Function_stop", funobj.__dict__
        # print "THREAD_LOCK C:", self.thread_lock, hex(id(self.thread_lock))
        with self.thread_lock:
            try:
                del self.running_functions[funobj]
            except KeyError:
                pass

    def call_rpc(self, httphandler, function, params, api_version):
        """Method used to perform actual calls.

        Since each HTTPRequestHandler-object runs in a separate therad,
        this method can be entered simultaneously from different threads.

        The input to this method is:

        handler
            The HTTPRequestHandler compatible object that this call
            originated in. It is intended to get at the client address.

            The Protocol object is intentionally _not_ avaialble to the
            Function, which has a Protcol-agnostic interface to the
            rest of the system.

        function
            The function to call, identified by its name and api_version.

        params
            The call parameters, as a list of native Python data types.

        The return value is a Python dictionary with either the key
        'result' with the value of the function call (as internal
        Python objects), or the key 'error' with the value an error
        dictionary.

        """

        start_time = time.time()
        funobj = None
        db = None

        try:
            api = self.api_handler.get_api(api_version)
            funobj = api.get_function_object(function, httphandler)
            if funobj.needs_database():
                if not self.database:
                    raise ExtInternalError("Function %s uses database, but no database is defined" % (funobj,))

                db = self.database.get_link()
                funobj.set_db_link(db)
            else:
                db = None
            # print
            # print "RPC: ", function
            self.function_start(funobj, params, start_time, api_version)
            result = funobj.call(params)
            ret = {'result': result}
            if db:
                db.commit()
                
        except exterror.ExtInternalError as e:
            self.logger.error((e.intdesc))
            traceback.print_exc()
            s = e.struct()
            ret = {'error': s}
            if db:
                db.rollback()
                
        except exterror.ExtError as e:
            s = e.struct()
            ret = {'error': s}
            if db:
                db.rollback()
                
        except Exception as e:
            # funobj.call() may only return a result or raise an
            # ExtError instance, but in very rare circumstances other
            # errors may bubble up.
            traceback.print_exc()
            e = exterror.ExtInternalError()
            s = e.struct()
            ret = {'error': s}
            if db:
                db.rollback()
        
        if funobj:
            self.function_stop(funobj)
        # print "RPC END:", function
        # print
        
        if db:
            self.database.return_link(db)

        ret['api_version'] = api_version
        return ret

    def register_function(self, cls):
        """Registers a Function subclass.

        The class will be callable from the outside, using the name in
        the class' .rpcname attribute, if the client has selected an
        API version between the class' .from_version and .to_version
        attributes values inclusive.

        It is an error to register two classes that have the same
        externally visible name and overlapping API versions.
        """

        if not issubclass(cls, Function):
            raise ValueError("Can only register subclasses of Function, %s is not" % (cls,))
        self.api_handler.add_function(cls)

    def register_category(self, cls):
        self.api_handler.add_category(cls)

    def register_functions_from_module(self, mod):
        """Scans an entire module, registering all Function subclasses in
        the module using self.register_function().

        If the class has an .rpcdisabled attribute set to a true value, it
        will not be added. If it lacks such an attribute, or it has a false
        value, it will be added. (This backwardsness is to minimize coding
        for the normal case, which is that all functions are enabled).
        """

        import types

        for (_key, value) in mod.__dict__.items():
            if not isinstance(value, types.TypeType):
                continue
            if not issubclass(value, Function):
                continue
            if value == Function:
                continue
            if not getattr(value, 'extname', None):
                continue
            if getattr(value, 'extdisabled', False):
                continue
           
            self.register_function(value)

    def register_categories_from_module(self, mod):
        self.api_handler.add_categories_from_module(mod)
        
    def register_from_directory(self, dirname):
        """ Register functions and managers found in python files within a directory"""
        import re
        import inspect
        import model
        seen_managers = []  # Avoid duplicating registrations. This can happen if managers are imported from other objects.
        
        for filename in os.listdir(dirname):
            mo = re.match(r"^([a-z0-9_]+).py$", filename)
            if not mo:
                continue
            if mo.group(1) == "__init__":
                continue
            self.logger.debug("Looking for managers in %s" % filename)
            module = __import__(mo.group(1))
            for _name, obj in inspect.getmembers(module):
                if inspect.isclass(obj):
                    if issubclass(obj, model.Manager):
                        if hasattr(obj, "name") and obj.name and obj.name not in seen_managers:
                            try:
                                self.register_manager(obj)
                                self.logger.debug("Registered manager %s" % str(obj))
                                seen_managers.append(obj.name)
                            except:
                                self.logger.error("Failed to register manager ", obj, " in module", mo.group(1))
                                raise
            self.register_functions_from_module(module)

    def get_server_id(self):
        """Returns a string that is unique to this server instance,
        and which can be used to identify it in logs and events.

        Contains the pattern hostname:listen_address:listen_port.
        """

        return self.server_id

    def get_server_url(self):
        """Returns the URL where this server is accessible.

        Either calculates a value automatically, or uses an explicit
        value to accomodate the server being used behind a load-balancer,
        ssl-tunnel or similar.

        If the environment variable SERVER_PUBLIC_URL is set to a non-empty
        value, that is returned.

        Otherwise, if the .server_public_url class attribute is set to
        a non-empty value, that is returned.

        Otherwise, the address and port used when insantiating the
        server object is used to form a URL.
        """

        url = os.environ.get("SERVER_PUBLIC_URL", "")
        if url:
            return url

        if hasattr(self, "server_public_url") and self.server_public_url:
            return self.server_public_url
        prot = "http"
        if self.ssl_enabled:
            prot = "https"
        return "%s://%s:%d/" % (prot, self.instance_address, self.instance_port)

    ###
    # Request dispatch
    ###
    def add_protocol_handler(self, prefix, handler):
        """A prefix to dispatch on. The prefix is what looks like a
        top-level directory in the URL.

        If the prefix for a FooHandler instance is "foo", requests to
        e.g. "/foo", "/foo/" and "/foo/bar/baz" are sent to
        FooHandler. It's .request() method will receive a subpath set
        to (respectively) "", "" and "bar/baz".

        If the prefix is None, then all requests not matched by
        another prefix will be sent to that handler.
        """

        try:
            if issubclass(handler, protocol.Protocol):
                handler = handler()
        except TypeError:
            pass

        if prefix[0] == '/':
            prefix = prefix[1:]

        handler.set_server(self)
        self.protocol_handlers[prefix] = handler

    def add_default_protocol_handlers(self):
        """Add the default protocol handlers, fetched
        from self.default_protocol_handlers.
        """

        for (prefix, handler) in self.default_protocol_handlers:
            self.add_protocol_handler(prefix, handler)

    def dispatch(self, httphandler, path, data):
        """Dispatch an incoming request, based on method and path."""

        if '__' in path:
            raise ValueError("__ is not allowed in request paths")

        if '/' in path:
            prefix, rest = path.split('/', 1)
        else:
            prefix, rest = path, ""

        if "?" in prefix:
            prefix, qs = prefix.split('?', 1)
            rest += '?' + qs

        if prefix in self.protocol_handlers:
            prothandler = self.protocol_handlers[prefix]
#             start = time.time()
            ret = prothandler.request(httphandler, rest, data)
#             if isinstance(ret, str):
#                 resstr = ret
#                 isstr = "Response was string"
#             else:
#                 resstr = ret.data
#                 isstr = ""

#             print "\nDISPATCH", "%lx" % (id(prothandler),), time.ctime(), "path:", path, "response length:", len(resstr), "elapsed:", "%.1f" % (time.time()-start,), isstr
            return ret

        method = httphandler.command
        if method:
            defkey = '__' + method.upper() + '__'
            try:
                prothandler = self.protocol_handlers[defkey]
            except LookupError:
                return response.HTTP404()
#           start = time.time()
            ret = prothandler.request(httphandler, path, data)
            return ret

        raise LookupError("No protocol handler found for request path " + path)

    ###
    # Optional subsystems.
    ###
    def enable_global_functions(self):
        self.register_function(default_function.FunPing)
        self.register_function(default_function.FunServerURLAPI)
        self.register_function(default_function.FunServerNodeName)
        
    def enable_static_documents(self, docroot):
        self.add_protocol_handler('__GET__', protocol.StaticDocumentProtocol(docroot))

    def enable_mutexes(self, mutex_manager_class=MutexManager):
        self.mutexes_enabled = True
        self.register_manager(mutex_manager_class)
        self.register_function(default_function.FunMutexAcquire)
        self.register_function(default_function.FunMutexRelease)
        self.register_function(default_function.FunMutexInfo)
        self.register_function(default_function.FunMutexCreate)
        self.register_function(default_function.FunMutexDestroy)
        self.register_function(default_function.FunMutexList)
        self.register_function(default_function.FunMutexStringList)
        self.register_function(default_function.FunMutexStringCreate)
        self.register_function(default_function.FunMutexStringGet)
        self.register_function(default_function.FunMutexStringSet)
        self.register_function(default_function.FunMutexStringUnset)
        self.register_function(default_function.FunMutexStringDestroy)
        self.register_function(default_function.FunMutexStringsetList)
        self.register_function(default_function.FunMutexStringsetCreate)
        self.register_function(default_function.FunMutexStringsetGet)
        self.register_function(default_function.FunMutexStringsetAdd)
        self.register_function(default_function.FunMutexStringsetRemove)
        self.register_function(default_function.FunMutexStringsetRemoveAll)
        self.register_function(default_function.FunMutexStringsetDestroy)
        self.register_function(default_function.FunMutexWatchdogList)
        self.register_function(default_function.FunMutexWatchdogCreate)
        self.register_function(default_function.FunMutexWatchdogState)
        self.register_function(default_function.FunMutexWatchdogInfo)
        self.register_function(default_function.FunMutexWatchdogStart)
        self.register_function(default_function.FunMutexWatchdogStop)
        self.register_function(default_function.FunMutexWatchdogDestroy)

    def enable_database(self, database_class, **kwargs):
        self.database = database_class(self, **kwargs)

    def enable_documentation(self):
        self.register_function(default_function.FunServerListFunctions)
        self.register_function(default_function.FunServerDocumentation)
        self.register_function(default_function.FunServerFunctionDefinition)

    def enable_digs_and_updates(self):
        self.api_handler.generate_model_stuff()
        self.digs_n_updates = True
        
    def check_tables(self, tables_spec=None, dynamic=False, fix=False):
        """ Checks and possibly fixes the needed database tables.
            If fix is set to True, any missing tables or columns in the tables will be created.
            If dynamic is set to True, the automatic tables specification, built while enabling digs
            is also checked and possibly fixed.
            If tables_spec is given, that specification is checked, but never fixed"""
            
        if not self.database:
            raise ExtInternalError("Server function %s uses database, but no database is defined" % "check_rpcc_tables")
        if not self.digs_n_updates:
            raise ValueError("You must enable digs and updates before checking the tables.")
        
        self.database.check_rpcc_tables(fix=fix)
        
        if dynamic:
            if not self.digs_n_updates:
                raise ValueError("Dynamic tables cannot be checked or fixed before digs and updates are enabled")
            
            for mgr in self.get_all_managers():
                
                dtspec = self.database.get_tables_spec(mgr)
                # TODO: Introspect models and managers and build a tables specification
                if dtspec:
                    self.generate_column_types(mgr, dtspec)
                    self.database.check_rpcc_tables(tables_spec=dtspec, fix=fix)
            
        if tables_spec:
            self.database.check_rpcc_tables(tables_spec=tables_spec, fix=False)
        
        self.tables_checked = True
        
    def generate_column_types(self, mgr, dtspec):
        for api in self.api_handler.apis:
            types = api.types
            my_type = types[mgr.manages.name + "-templated-data"]
            model_name = mgr.manages.name
            if model_name not in my_type.optional:
                self.logger.warning(
                    "Warning: model name %s of manager %s not found among its templated data" % (model_name, mgr))
                continue
            my_id_type_tuple = my_type.optional[model_name]
            my_id_type = my_id_type_tuple[0]
            if issubclass(my_id_type, exttype.ExtString):
                vtype = VType.string
            if issubclass(my_id_type, exttype.ExtInteger):
                vtype = VType.integer
            
            table = dtspec[0]
            col = table.columns[0]  # Id must be in the first column
            col.set_value_type(vtype)
            col.primary = True
            
            for i in range(0, len(dtspec)):
                table = dtspec[i]
                for j in range(0, len(table.columns)):
                    if j == 0:
                        continue
                    col = table.columns[j]
                    my_col_type_tuple = my_type.optional[col.name]
                    my_col_type = my_col_type_tuple[0]
                    vtype = None
                    if issubclass(my_col_type, exttype.ExtString):
                        vtype = VType.string
                    if issubclass(my_col_type, exttype.ExtInteger):
                        vtype = VType.integer
                    col.set_value_type(vtype)
   
    ###
    # model.Manager subclasses this server handles. Registered under a
    #    name, which the magic get method in Function uses to create
    #    singletons.
    ###
    def register_manager(self, manager_class):
        if self.digs_n_updates:
            raise ValueError("You must register all models and managers before enabling digs and updates.")
        if self.tables_checked:
            raise ValueError("You must register all models and managers before checking tables")
        
        self.manager_by_name[manager_class._name()] = manager_class

        modelcls = manager_class.manages
        if modelcls is not None:
            self.model_by_name[modelcls._name()] = modelcls

        if self.database:
            db = self.database.get_link()
        else:
            db = None

        try:
            manager_class.do_register(self, db)
        finally:
            if db:
                self.database.return_link(db)

        if issubclass(manager_class, session.SessionManager):
            self.register_function(default_function.FunSessionStart)
            self.register_function(default_function.FunSessionStop)
            self.register_function(default_function.FunSessionInfo)
            self.sessions_enabled = True

        elif issubclass(manager_class, authentication.AuthenticationManager):
            self.register_function(default_function.FunSessionAuthLogin)
            self.register_function(default_function.FunSessionDeauth)

        elif issubclass(manager_class, event.EventManager):
            self.register_function(event.EventGetMaxId)
            self.register_function(event.EventGetMaxAppId)
            self.events_enabled = True
        
    def create_manager(self, mgrname, function):
        if mgrname in self.manager_by_name:
            return self.manager_by_name[mgrname](function)
        if hasattr(self, "create_" + mgrname):
            return getattr(self, "create_" + mgrname)(function)
        return None

    def get_all_managers(self):
        return self.manager_by_name.values()

    def register_model(self, model_class):
        if self.digs_n_updates:
            raise ValueError("You must register all models and managers before enabling digs and updates.")
        if self.tables_checked:
            raise ValueError("You must register all models and managers before checking tables")
        self.model_by_name[model_class._name()] = model_class

    def get_all_models(self):
        return self.model_by_name.values()

    def is_superuser(self, obj, fun):
        return self.superuser_guard.check(obj, fun)
