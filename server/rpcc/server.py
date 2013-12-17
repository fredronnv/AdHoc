
import os
import sys
import time
import socket
import traceback
import threading
import SocketServer
import BaseHTTPServer

import mutex
import event
import access
import exttype
import session
import exterror
import function
import protocol
import response
import api_handler
import documentation
import authentication
import request_handler
import default_function
from exterror import ExtInternalError

from function import Function

try:
    import ssl
except:
    pass

class SSLConfig(object):
    keyfile = None
    certfile = None
    chainfile = None

    def __init__(self, keyfile=None, certfile=None, chainfile=None):
        if keyfile:
            self.keyfile = keyfile
        if certfile:
            self.certfile = certfile
        if chainfile:
            self.chainfile = chainfile

        self.ctx = SSL.Context(SSL.SSLv23_METHOD)
        self.ctx.use_privatekey_file(keyfile)
        self.ctx.use_certificate_file(certfile)
        if chainfile:
            self.ctx.load_verify_locations(chainfile)

    def wrap_socket(self, server, raw_socket):
        return SSL.Connection(self.ctx, raw_socket)


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

    # If docroot is set, a default "GET" HTTP-method handler will be
    # enabled, and serve documents from docroot.

    docroot = None

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
        #('__POST__', protocol.XMLRPCProtocol),
        ('/apache-xmlrpc', protocol.ApacheXMLRPCProtocol),
        ('/json', protocol.JSONProtocol),
        ('/WSDL', protocol.WSDLProtocol),
        ('/SOAP', protocol.SOAPProtocol),
        ('/api', protocol.FunctionDefinitionProtocol),

        #('/spnego+xmlrpc', RPCKRB5XMLRPCProtocolHandler),
        #('/spnego+apache-xmlrpc', RPCKRB5ApacheXMLRPCProtocolHandler),
        #('/spnego+SOAP', RPCKRB5SOAPProtocolHandler),

        # Default GET handler added only if self.docroot is set
        # ('__GET__', RPCStaticDocumentHandler),
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

    def __init__(self, address, port, ssl_config=None, handler_class=None):
        self.database = None
        self.digs_n_updates = False
        self.mutexes_enabled = False
        self.events_enabled = False

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
        print "SUCCESS (%.2fs) %s%s => %s" % (call_time, function_name, params, result)

    def log_error(self, handler, function_name, function_object, params, result, exc, call_time):
        """Log exceptions. Called id the Function subclass
        instance's .do()-method raised an exception.
        """
        print "ERROR (%.2fs) %s%s => %s" % (call_time, function_name, params, result)

    def get_running_functions(self):
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
        with self.thread_lock:
            self.running_functions[funobj] = (args, starttime, api_version)

    def function_stop(self, funobj):
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
            self.function_start(funobj, params, start_time, api_version)
            result = funobj.call(params)
            ret = {'result': result}
            if db:
                db.commit()
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

        for (key, value) in mod.__dict__.items():
            if type(value) != types.TypeType:
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

        return "http://%s:%d/" % (self.instance_address, self.instance_port)

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
            start = time.time()
            ret = prothandler.request(httphandler, rest, data)
            if type(ret) == type(""):
                resstr = ret
                isstr = "Response was string"
            else:
                resstr = ret.data
                isstr = ""

            #print "\nDISPATCH", "%lx" % (id(prothandler),), time.ctime(), "path:", path, "response length:", len(resstr), "elapsed:", "%.1f" % (time.time()-start,), isstr
            return ret

        method = httphandler.command
        if method:
            defkey = '__' + method.upper() + '__'
            try:
                prothandler = self.protocol_handlers[defkey]
            except LookupError:
                return response.HTTP404()
            start = time.time()
            ret = prothandler.request(httphandler, path, data)
            return ret

        raise LookupError("No protocol handler found for request path " + path)

    ###
    # Optional subsystems.
    ###
    def enable_static_documents(self, docroot):
        self.add_protocol_handler('__GET__', protocol.StaticDocumentProtocol(docroot))

    def enable_mutexes(self, mutex_manager_class=mutex.MutexManager):
        self.mutexes_enabled = True
        self.register_manager(mutex_manager_class)
        self.register_function(default_function.FunMutexAcquire)
        self.register_function(default_function.FunMutexRelease)
        self.register_function(default_function.FunMutexInfo)
        self.register_function(default_function.FunMutexCreate)
        self.register_function(default_function.FunMutexDestroy)
        self.register_function(default_function.FunServerListMutexes)
        self.register_function(default_function.FunMutexListStrings)
        self.register_function(default_function.FunMutexCreateString)
        self.register_function(default_function.FunMutexStringGet)
        self.register_function(default_function.FunMutexStringSet)
        self.register_function(default_function.FunMutexStringUnset)
        self.register_function(default_function.FunMutexStringDestroy)
        self.register_function(default_function.FunMutexListStringsets)
        self.register_function(default_function.FunMutexCreateStringset)
        self.register_function(default_function.FunMutexStringsetGet)
        self.register_function(default_function.FunMutexStringsetAdd)
        self.register_function(default_function.FunMutexStringsetRemove)
        self.register_function(default_function.FunMutexStringsetDestroy)
        self.register_function(default_function.FunMutexListWatchdogs)
        self.register_function(default_function.FunMutexCreateWatchdog)
        self.register_function(default_function.FunMutexWatchdogState)
        self.register_function(default_function.FunMutexWatchdogInfo)
        self.register_function(default_function.FunMutexWatchdogStart)
        self.register_function(default_function.FunMutexWatchdogStop)
        self.register_function(default_function.FunMutexWatchdogDestroy)

    def enable_database(self, database_class):
        self.database = database_class(self)

    def enable_documentation(self):
        self.register_function(default_function.FunServerListFunctions)
        self.register_function(default_function.FunServerDocumentation)
        self.register_function(default_function.FunServerFunctionDefinition)

    def enable_digs_and_updates(self):
        self.api_handler.generate_model_stuff()
        self.digs_n_updates = True

    ###
    # model.Manager subclasses this server handles. Registered under a
    #    name, which the magic get method in Function uses to create
    #    singletons.
    ###
    def register_manager(self, manager_class):
        if self.digs_n_updates:
            raise ValueError("You must register all models and managers after digs and updates.")
        self.manager_by_name[manager_class._name()] = manager_class

        modelcls = manager_class.manages
        if modelcls is not None:
            self.model_by_name[modelcls._name()] = modelcls

        if self.database:
            db = self.database.get_link()
        else:
            db = None

        try:
            manager_class.on_register(self, db)
        finally:
            if db:
                self.database.return_link(db)

        if issubclass(manager_class, session.SessionManager):
            self.register_function(default_function.FunSessionStart)
            self.register_function(default_function.FunSessionStop)
            self.register_function(default_function.FunSessionInfo)

        elif issubclass(manager_class, authentication.AuthenticationManager):
            self.register_function(default_function.FunSessionAuthLogin)
            self.register_function(default_function.FunSessionDeauth)

        elif issubclass(manager_class, event.EventManager):
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
        self.model_by_name[model_class._name()] = model_class

    def get_all_models(self):
        return self.model_by_name.values()

    def is_superuser(self, obj, fun):
        return self.superuser_guard.check(obj, fun)
