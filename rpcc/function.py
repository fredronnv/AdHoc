
from exttype import *
import default_type

import exterror
import sys

class Function(object):
    """Base class for functions exposed via the RPC server.

    Each RPC function is implemented as its own subclass of this class.
    All such classes are registered with a Server instance.
    
    All calls coming in to the Server work through a Function instance. 
    In a database-backed server each Function has it's own transaction(s).

    When an RPC request is received, the server uses the API version 
    requested and the public RPC function name to find the Function
    subclass that represents the function in the request, and instantiates
    it with the server instance and handler instance as parameters. Each
    invocation of each RPC is therefore its own object.

    The Function object's .call() method is called, and passed all
    the parameters in the RPC request. It should return an RPC response
    struct.

    It checks types etcetera, and then calls the .do() method.

    If attributes .from_version and possibly .to_version are set, the
    RPCFunction is only visible if the client has selected to use an
    API version above/including .from_version (and below/including 
    .to_version if set).

    Access to non-existant attributes ending with '_manager' will
    trigger logic. If a non-existant attribute '.foo_manager' is
    accessed:
      1. If one of the classes in self.managers has a .name attribute 
         which is 'foo', that class will be instantiated with one
         argument - the Function instance.

      2. Otherwise, if the Function instance has a method
         create_foo_manager, it will be called. Then self.foo_manager
         will be returned.

      3. Otherwise an attribute error is raised.
    """

    # External name. In all API versions from .from_version to 
    # .to_version, this is the external name bound to this Function
    # class.
    extname = None

    # Boolean whether this function should be included in
    # server_list_functions() responses.
    extvisible = True

    # First API version where this function is valid
    from_version = 0

    # Last API version where this function is valid
    to_version = 10000

    # If params is set to a [(name, type, description), ...] tuple
    # list, incoming parameters will be passed through the types
    # to be parsed. NOTE: Classes will prepend their parent's .params 
    # to their own.
    params = None
    returns = ExtNull
    desc = ""
    border_checks = []

    # List of FunctionCategory subclasses that this function considers
    # itself to belong to. The Categories can also specify which
    # functions they consider belong to them.
    #categories = []

    # If True, the Function will likely create at least one Event, and a
    # marker event should be created/destroyed.
    creates_event = False

    @classmethod
    def _name(cls):
        return cls.extname or ""

    @classmethod
    def _returns(cls):
        if isinstance(cls.returns, tuple):
            return cls.returns
        return (cls.returns, None)

    @classmethod
    def get_parameters(cls):
        # In order to inherit parameters through subclasses, which
        # goes against Python's normal inheritance, we start by
        # fetching the parameters (if any) of a baseclass which is
        # also a Function or Function subclass. We then append the
        # parameters defined locally in this class.

        funbases = [b for b in cls.__bases__ if issubclass(b, Function)]
        if not funbases:
            return []

        if len(funbases) > 1:
            raise ValueError("Function may only be inherited once - %s inherits %s" % (cls, funbases))

        pars = funbases[0].get_parameters()
        for par in cls.__dict__.get("params", []):
            if len(par) == 2:
                pars.append( (par[0], par[1], None) )
            else:
                pars.append(par)

        return pars

    @classmethod
    def _subtypes_flat(cls):
        """Returns a dict-by-name of all types referenced directly or 
        indirectly in the function's parameters or return type, in 
        depth-first order."""

        types = {}
        
        def add_type(typedict, t):
            t = ExtType.instance(t)
            n = t._name()
            if n in typedict:
                return
            typedict[n] = t
            for (name, subt) in t._subtypes():
                add_type(typedict, subt)

        for (p, t, _d) in cls.get_parameters():
            add_type(types, t)

        add_type(types, cls._returns()[0])
        return types

    @classmethod
    def soap_name(cls):
        return ExtType.capsify(cls._name())

    @classmethod
    def request_element_name(cls):
        return cls.soap_name()

    @classmethod
    def response_element_name(cls):
        return cls.soap_name() + "Response"

    @classmethod
    def input_message_name(cls):
        return cls.soap_name() + "InputMessage"

    @classmethod
    def output_message_name(cls):
        return cls.soap_name() + "OutputMessage"

    @classmethod
    def xsd_request(cls, mscompat):
        node = XMLNode("element", name=cls.request_element_name())
        params = node.new("complexType").new("sequence")
        for (name, typ, desc) in cls.get_parameters():
            elemname = ExtType.capsify(name)
            if mscompat:
                elemname += "In"
            typ = ExtType.instance(typ)
            typename = "myxsd:" + typ.xsd_name()
            el = params.new("element", name=elemname, type=typename)
            if desc:
                el.new("annotation").new("documentation").cdata(XMLNode.escape(desc))
        return node

    @classmethod
    def xsd_response(cls):
        typ, desc = cls._returns()

        node = XMLNode("element", 
                       name=cls.response_element_name(),
                       type=ExtType.instance(typ).xsd_name())
        if desc:
            node.new("annotation").new("documentation").cdata(XMLNode.escape(desc))

        return node        

    @classmethod
    def from_xml(cls, elem):
        children = ExtType.child_elements(elem)
        params = []
        for (name, typ, desc) in cls.get_parameters():
            elemname = ExtType.capsify(name)

            if len(children) == 0:
                raise ExtSOAPMissingElementError(elem, "Parameter element %s or %s_in missing" % (elemname, elemname))

            child = children.pop(0)
            child_tag = child.tagName.split(":")[-1]
            if child_tag != elemname and child_tag != elemname + "_in":
                raise ExtSOAPMissingElementError(elem, "Parameter element %s or %s_in missing" % (elemname, elemname))

            typ = ExtType.instance(typ)
            params.append(typ.from_xml(child))
        return tuple(params)

    @classmethod
    def to_xml_node(cls, value):
        typ = ExtType.instance(cls.returns)
        elem = XMLNode(cls.response_element_name())
        typ.to_xml(elem, value)
        return elem

    def __init__(self, server, http_handler, api, db=None):
        self.server = server
        self.db = db
        # HTTPRequestHandler that handles this request. Interesting
        # for the .headers and .client attributes.
        self.http_handler = http_handler
        self.api = api

        # Dict of Function-stable _Decision:s, indexed by Guard
        # instance.
        self._decision_cache = {}

        # Flag indicating that the Function is currently in "granted"
        # state (set/cleared in a try/finally in the @entry decorator
        # where a Guard has returned AccessGranted).
        self._entry_granted = False

    def __getattr__(self, attr):
        if attr.endswith("_manager"):
            mgr = self.server.create_manager(attr, self)
            if mgr:
                setattr(self, attr, mgr)
                return getattr(self, attr)
        raise AttributeError(attr)

    def log_arguments(self, args):
        """When logging the parameters, this method is used to filter
        out potentially sensitive data (for example passwords).

        It gets a list of the parameters as sent to the .do() method,
        and must return a list to include in the log."""

        return args

    def parse_args(self, args):
        params = self.get_parameters()

        if len(params) != len(args):
            raise exterror.ExtArgumentCountError(len(params), len(args))

        argidx = 0
        for (param, arg) in zip(params, args):
            try:
                (attr, typ, desc) = param
            except:
                raise exterror.ExtInternalError("Wrong tuple member count in params of %s" % (self.__class__.__name__))

            setattr(self, "_raw_" + attr, arg)

            try:
                typ = ExtType.instance(typ)
                value = typ.parse(self, arg)
            except exterror.ExtError as e:
                # Other errors are converted to ExtInternalError by the Server.
                e.argno = argidx
                e.add_traceback(argidx)
                raise

            setattr(self, attr, value)
            argidx += 1

    def check_access(self):
        # If one says yes, we're ok. It's only a border check.

        if not self.border_checks:
            return

        denied_by = None
        for axscls in self.border_checks:
            ao = axscls(self)
            try:
                ao.check()
                break
            except exterror.ExtAccessDeniedError as e:
                if denied_by is None and e.__class__ != errors.AccessError:
                    denied_by = ao
        else:
            if denied_by:
                # By checking again with the first class that said no,
                # it will raise it's specific error again.
                denied_by.check()
            else:
                raise exterror.ExtAccessDeniedError("Function access denied.")

    def started_at(self):
        return self.call_time

    def started_iso(self):
        return self.call_time.isoformat()[:19]

    def call(self, args):
        """Called by the rpc server for call handling."""

        self.call_time = datetime.datetime.now()
        call_success = False
        evattrs = {}

        try:
            funname = "%s#%d" % (self._name(), self.api.version)
            if self.server.events_enabled:
                self.event_manager.start("call", function=funname,
                                         params=str(self.log_arguments(args)))

                if self.creates_event:
                    self.event_manager.create_marker()
                    self.db.commit()

            self.parse_args(args)
            self.check_access()
            ret = self.do()
            response = ExtType.instance(self.returns).output(self, ret)
            call_success = True
            return response
        except Exception as e:
            if isinstance(e, exterror.ExtOutputError):
                print "ExtOutputError"
                e.print_trace()
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exc()
            tb = traceback.extract_tb(exc_traceback)
            evattrs["error"] = exc_type.__name__
            evattrs["errline"] = "%s:%d" % (tb[-1][0], tb[-1][1])
            evattrs["errval"] = str(exc_value)
            if not isinstance(e, ExtError):
                e = exterror.ExtInternalError()
            evattrs["errid"] = e.id
            if isinstance(e, ExtInternalError):
                evattrs["stack"] = traceback.format_exc()
            raise e
        finally:
            if self.server.events_enabled:
                elapsed = datetime.datetime.now() - self.call_time
                evattrs["elapsed"] = int(1000 * elapsed.seconds)
                self.event_manager.stop(call_success, **evattrs)
                self.db.commit()

    def do(self):
        """Implement in subclasses for actual functionality."""
        raise NotImplementedError


class SessionedFunction(Function):
    params = [("session", default_type.ExtSession, "Execution context")]


# This class is _dynamically_ (i.e. automatically) subclassed by
# api.create_fetch_functions() to create the actual update functions.
class FetchFunction(SessionedFunction):
    def do(self):
        # Find the object and template.
        params = self.get_parameters()
        obj = getattr(self, params[-2][0])
        tmpl = getattr(self, params[-1][0])
        return obj.apply_template(self.api.version, tmpl)


# This class is _dynamically_ (i.e. automatically) subclassed by
# api.create_update_functions() to create the actual update functions.
class UpdateFunction(SessionedFunction):
    def do(self):
        params = self.get_parameters()
        obj = getattr(self, params[-2][0])
        upd = getattr(self, params[-1][0])
        obj.apply_update(self.api.version, upd)


# This class is _dynamically_ (i.e. automatically) subclassed by
# api.create_update_functions() to create the actual update functions.
class DigFunction(SessionedFunction):
    def do(self):
        mgr = getattr(self, self.dig_manager)
        resid = mgr.perform_search(self.search)
        objs = mgr.models_by_result_id(resid)
        return [o.apply_template(self.api.version, self.template) for o in objs]