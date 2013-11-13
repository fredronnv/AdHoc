
import re
import datetime

from exttype import *
import default_type
from session import Session
from xmlnode import XMLNode

import exterror

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
        marker_id = None
        try:
            if self.creates_event:
                marker_id = self.server.create_marker_event()
                
            self.parse_args(args)
            self.check_access()
            ret = self.do()

            #return ret
            return ExtType.instance(self.returns).output(self, ret)
        finally:
            if marker_id:
                self.server.destroy_marker_event(marker_id)

    def do(self):
        """Implement in subclasses for actual functionality."""
        raise NotImplementedError


class SessionedFunction(Function):
    params = [("session", default_type.ExtSession, "Execution context")]


# This class is _dynamically_ (i.e. automatically) subclassed by
# api.create_fetch_functions() to create the actual update functions.
class FetchFunction(Function):
    def do(self):
        # Find the object and template.
        params = self.get_parameters()
        obj = getattr(self, params[-2][0])
        tmpl = getattr(self, params[-1][0])
        return obj.apply_template(self.api.version, tmpl)

# This class is _dynamically_ (i.e. automatically) subclassed by
# api.create_update_functions() to create the actual update functions.
class UpdateFunction(Function):
    def do(self):
        params = self.get_parameters()
        obj = getattr(self, params[-2][0])
        upd = getattr(self, params[-1][0])
        obj.apply_update(self.api.version, upd)

# This class is _dynamically_ (i.e. automatically) subclassed by
# api.create_update_functions() to create the actual update functions.
class DigFunction(Function):
    def do(self):
        pass
        #params = self.get_parameters()
        #obj = getattr(self, params[-2][0])
        #upd = getattr(self, params[-1][0])
        #obj.apply_update(self.api.version, upd)




class XXXTypedFunction(Function):
    """Subclass to Function that adds automatic documentation and typing.
    
    The .params attribute is exposed by the Server as the
    function's signature, and used for generating online
    documentation. It must be set to a sequence of three-tuples:
      (paramname, paramtype, paramdescription)

    .desc is a string with the function documentation.

    .rettype is a Type subclass representing the return type.

    .access is a single Access subclass, or list of such
    subclasses, that will be instantiated and called to perform access
    control checks before entering into actual code (where additional
    checks may be performed).

    The .do()-method implemented by TypedFunction will read the incoming
    call values, and match them to .params() tuples. For each parameter,
    the tuple's Type subclass is instantiated and its .parse()-method
    called with the incoming value as input. The return value from
    .parse() is stored in the attribute on self called "paramname".

    It will then instantiate and call each Access subclass in the 
    .access attribute. If any of them raise an exception, that will finish
    processing of the incoming call.

    No set semantics are in place for what Access objects may
    check. They are passed the Server and Function objects, and may call 
    any methods in them. From experience, it is however recommended not to 
    do too deep inspection, since that leads to a proliferation of
    a gazillion Access classes. It is often better to let Access subclasses
    perform simple checks ("is authenticated", "from internal network",
    "in the superusers group"), and let the data model do the intricate
    checks ("operates on a person belonging to a group for which the
    caller has a temporary access token").

    When generating documentation, the paramdescription will be used
    to describe the role in the function call of the parameter (which
    is not the same as the parameter's type).

    After performing the parsing, attribute setting and access
    control, .typed_do() will be called. Implement it in your subclass
    to do the actual dirty stuff.
    """


    def __init__(self, *args, **kwdict):
        RPCFunction.__init__(self, *args, **kwdict)
        self._html_seen_types = []
        self._temp_session = None

    @classmethod
    def get_parameters(cls):
        return [(p[0], p[1]) for p in cls.params]

    def do(self, *args):
        if len(self.params) != len(args):
            raise RPCTypeError("%d arguments expected, got %d" % (len(self.params), len(args)))

        try:
            for argno in range(len(self.params)):
                param = self.params[argno]
                arg = args[argno]
                try:
                    paramname, paramtype, paramdesc = param
                    typeobj = RPCType()._typeobj(paramtype)
                    val = typeobj.parse(self.server, self, arg)
                    self.__setattr__(paramname, val)
                    self.__setattr__('_raw_' + paramname, arg)
                    if isinstance(val, RPCSession) and val.temporary:
                        self._temp_session = val
                except RPCError, e:
                    e.argno = argno
                    e.add_traceback(argno)
                    raise
            self.access()
            return self.typed_do()
        finally:
            if self._temp_session:
                self.server.kill_session(self._temp_session)

    def typed_do(self):
        raise NotImplementedError

    def access(self):
        if not self.grants:
            return

        if isinstance(self.grants, list) or isinstance(self.grants, tuple):
            grants = self.grants
        else:
            grants = [self.grants]
            
        specific_denier = None
        for axsclass in self.grants:
            ao = axsclass(self.server, self)
            try:
                ao.check()
                break
            except RPCAccessError as e:
                # If there are several access classes, it is enough that
                # one of them says yes. Continue checking.
                if specific_denier is None and e.__class__ != RPCAccessError:
                    specific_denier = ao
        else:
            if specific_denier:
                # By checking again with the first class that said no,
                # it will raise it's specific error again.
                specific_denier.check()
            else:
                raise RPCAccessError("Function access denied.")

        return

    def XXXdocumentation_dict(self):
        """Generate the documentation dictionary for this function."""

        r = self.rettype
        if not isinstance(self.rettype, RPCType):
            try:
                if issubclass(self.rettype, RPCType):
                    r = r()
                else:
                    raise TypeError
            except TypeError:
                raise TypeError("Rettype %s is not RPCType subclass in %s definition" % (self.rettype, self))

        d = {'dict_type': 'function',
             'name': self.rpcname,
             'description': self.desc,
             'return_type': r._docdict(),
             'parameters': [],
             'from_api_version': self.from_version,
            }

        if self.to_version < 10000:
            d['to_api_version'] = self.to_version

        for par in self.params:
            if len(par) == 3:
                name, typ, desc = par
            else:
                name, typ = par
                desc = name
                
            if not isinstance(typ, RPCType):
                typ = typ()
            d['parameters'].append( {'dict_type': 'parameter',
                                     'name': name,
                                     'desc': desc,
                                     'type': typ._docdict()} )

        return d

    def documentation(self):
        """Generates and returns the documentation for this function."""

        sigl_short = []
        sigl_exp = []
        paraml = []
        types = []

        if self.rettype:
            p = [(None, self.rettype, self.retdesc)] + self.params
        else:
            p = [(None, RPCNullType, "Unspecified")] + self.params

        for (paramname, paramtype, paramdesc) in p:
            to = RPCType()._typeobj(paramtype)
            sigl_short.append(paramname)
            sigl_exp.append(to._typedef_inline())
            (inline, extras) = to._typedef()
            paraml.append( (paramname, inline, paramdesc) )
            types += extras

        s = "Function definition (API version"
        if self.to_version > self.from_version:
            s += "s %d--" % (self.api.version,)
            if self.to_version == 10000:
                s += "oo):\n"
            else:
                s += "%d):\n" % (self.to_version,)
        else:
            s += " %d):" % (self.api.version,)

        s += "\n\n  %s(%s) " % (self.rpcname, ", ".join(sigl_short[1:]))

        s += "\n\nReturns:\n  %s" % (paraml[0][1],)
        if paraml[0][2]:
            s += ": %s" % (paraml[0][2],)
        s += "\n"

        if len(paraml) > 1:
            s += "\nParameters:\n"
            w1 = max([len(a[0]) for a in paraml[1:]])
            w2 = max([len(a[1]) for a in paraml[1:]])
            for (name, inline, desc) in paraml[1:]:
                s += "  %-*s  %-*s  %s\n" % (w1, name, w2, inline, desc)

        if types:
            s += "\nTypes:\n"
            maxlen = max([len(a[0]) for a in types])
            seen, outl = {}, []
            types.reverse()
            for (left, right) in types:
                if seen.has_key(left):
                    continue
                seen[left] = True
                outl.append("  %-*s ::= %s\n" % (maxlen, left, right))
            outl.reverse()
            s += "\n".join(outl) + "\n"
            
        s += "\nFunction signature:\n"
        s += "  %s %s(%s)\n" % (sigl_exp[0], self.rpcname, ", ".join(sigl_exp[1:]))

        if self.grants:
            if isinstance(self.grants, list) or isinstance(self.grants, tuple):
                grantlist = self.grants
            else:
                grantlist = [self.grants]

            if len(grantlist) > 1:
                s += "\nAccess allowed for any of:\n"
            else:
                s += "\nAccess allowed for:\n"
                
            for a in grantlist:
                ao = a(self.server, self)
                s += '  ' + ao.desc + "\n"

        s += "\nDescription:\n"
        lines = [" "]
        for tok in self.desc.split():
            t = tok.strip()
            if not t:
                continue
            if len(lines[-1]) + len(t) > 75:
                lines.append("  " + t)
            else:
                lines[-1] = lines[-1] + " " + t
        s += "\n".join(lines)

        return s

    def html_type_name(self, typ):
        def addtype(t):
            # Simple RPC types do not need to be specified further
            if t in [RPCIntegerType, RPCStringType, RPCBooleanType,
                     RPCNullType]:
                return
            if t not in self._html_seen_types:
                self._html_seen_types.append(t)
                
        if isinstance(typ, RPCListType):
            addtype(typ.typ)
            return "List of %s" % (self.html_type_name(typ.typ),)
        if typ == RPCEnumType:
	    return "One of the strings"
        if typ == RPCListType:
            return "List of anonymous types"
        if isinstance(typ, RPCOrNullType):
            addtype(typ.typ)
            return "(%s or Null)" % (self.html_type_name(typ.typ),)

        addtype(typ)
        return '<span class="typename">&lt;<a href="#typedef-%s">%s</a>&gt;</span>' % (typ.name, typ.name)

    def html_add_links(self, s):
        l = re.split('RPC:([a-z0-9_]+)\(\)', s)
        o = ''
        while l:
            if len(l) == 1:
                o += l[0]
                break
            (raw, capt) = l[:2]
            l = l[2:]
            o += raw
            if self.api.has_function(capt):
                o += '<a href="/functions/v3.%d/%s" class="funlink">%s()</a>' % (self.api.version, capt, capt)
            else:
                o += 'RPC:' + capt + '()'
        return o
    
    def html_documentation(self):
        def qs(s):
            return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        s = ""

        s += '<div class="function"><div class="head">'
        s += '<span class="api_version">API v3.%d:</span><br>' % (self.api.version,)
        s += '<span class="fundef">%s()' % (self.rpcname,)
        s += '</span></div><table class="function">'

        s += '<tr><td class="attribute" valign="top">Description:</td>'
        s += '<td class="definition">' + qs(self.desc).replace('\n\n', '<br><br>')
        s += '</td></tr>'

        s += '<tr><td class="attribute">Function&nbsp;definition:</td>'
        s += '<td class="definition">'
        p = ['<span class="paramname">%s</span>' % (p[0],) for p in self.params]
        s += '<span class="fundef">' + self.rpcname
        s += '(' + ', '.join(p) + ')</span></td></tr>'

        s += '<tr><td class="attribute" valign="top">Parameters:</td>'
        s += '<td class="definition">'
        if self.params:
            s += '<table class="parameters">'

            for (name, typ, desc) in self.params:
                s += '<tr><td class="name"><span class="paramname">%s</span></td>' % (name,)
                s += '<td class="type">%s</td>' % (self.html_type_name(typ),)
                s += '<td class="description">%s</td></tr>' % (self.html_add_links(qs(desc)),)
            s += '</table>'
        else:
            s += 'None.'
        s += '</td></tr>'

        s += '<tr><td class="attribute">Return&nbsp;type:</td>'
        s += '<td class="definition">%s' % (self.html_type_name(self.rettype),)
        s += '</td></tr>'

        s += '<tr><td class="attribute">Access:</td>'
        s += '<td class="definition">'
        if isinstance(self.grants, list) or isinstance(self.grants, tuple):
            grantlist = self.grants
        else:
            grantlist = [self.grants]

        for a in grantlist:
            if a:
                ao = a(self.server, self)
                s += ao.desc + "<br>"

        s += '</td></tr>'

        s += '<tr><td class="attribute" valign="top">API validity:</td>'
        s += '<td class="definition">'
        s += "This definition of %s is " % (self.rpcname,)
        if self.from_version == self.to_version:
            s += "only valid for version 3.%d of the API" % (self.from_version,)
        else:
            s += "valid in API versions 3.%d " % (self.from_version,)
            if self.to_version == 10000:
                s += "and up."
            else:
                s += "through 3.%d." % (self.to_version,)
        s += '</td></tr>'
        
        s += '<tr><td class="attribute" valign="top">Used&nbsp;types:</td>'
        s += '<td class="definition">'

        s += '<table class="typedef">'
        idx = 0
        while idx < len(self._html_seen_types):
            typ = self._html_seen_types[idx]
            idx += 1
            s += '<tr class="head"><td colspan="4">'
            s += '<a name="typedef-%s"/>' % (typ.name,)
            s += '<span class="typename">&lt;%s&gt;</span></td></tr>' % (typ.name,)
            s += '<tr><td class="attribute">Description:</td>'
            if typ.desc:
                s += '<td class="definition" colspan="3">%s</td></tr>' % (self.html_add_links(typ.desc),)
            else:
                s += '<td class="definition" colspan="3">&nbsp;</td></tr>'

            s += '<tr><td class="attribute">XMLRPC&nbsp;type:</td>'
            s += '<td class="definition" colspan="3">'

            if issubclass(typ, RPCIntegerType):
                s += 'integer</td></tr>'
                if typ.range:
                    s += '<tr><td class="attribute">Type&nbsp;constraint:</td>'
                    s += '<td class="definition" colspan="3">Value&nbsp;between'
                    s += '<span class="int">%d</span> and ' % (typ.range[0],)
                    s += '<span class="int">%d</span></td></tr>' % (typ.range[1],)                    
            elif issubclass(typ, RPCEnumType):
                s += 'string</td></tr>'
                s += '<tr><td class="attribute">Type&nbsp;constraint:</td>'
                s += '<td class="definition" colspan="3">Value one of '
                v = ['<span class="value">%s</span>' % (v,) for v in typ.values]
                s += ', '.join(v) + '</td></tr>'
            elif issubclass(typ, RPCStringType):
                s += 'string</td></tr>'
                if typ.regexp:
                    r = typ.regexp
                    if r[0] != '^':
                        r = '^' + r
                    if r[-1] != '$':
                        r = r + '$'
                    s += '<tr><td class="attribute">Type&nbsp;constraint:</td>'
                    s += '<td class="definition" colspan="3">Regexp '
                    s += '<span class="regexp">%s</span></td></tr>' % (r,)
            elif issubclass(typ, RPCBooleanType):
                s += 'boolean</td></tr>'
            elif issubclass(typ, RPCNullType):
                s += 'null</td></tr>'
            elif issubclass(typ, RPCOrNullType):
                s += 'or_null</td></tr>'
            elif issubclass(typ, RPCListType):
                s += 'list</td></tr>'
                s += '<tr><td class="attribute">Element&nbsp;type:</td>'
                s += '<td class="definition" colspan="3">'
                s += '%s</td></tr>'  % (self.html_type_name(typ.typ),)
            elif issubclass(typ, RPCStructType):
                def type_table(typedict):
                    t = '<th class="keyname">Name</th><th class="keytype">Type</th><th class="keydesc">Description</th></tr>'
                    keys = typedict.keys()
                    keys.sort()
                    for k in keys:
                        v = typedict[k]
                        if type(v) == type(()):
                            subtyp, desc = v
                        else:
                            subtyp, desc = v, ""
                        t += '<tr><td class="keyname">%s</td>' % (k,)
                        t += '<td class="keytype">%s</td>' % (self.html_type_name(subtyp),)
                        t += '<td class="keydesc">%s</td></tr>' % (desc,)

                    return t
                    
                s += 'struct</td></tr>'
                numrows = len(typ.mandatory) + 1
                s += '<tr><td class="attribute" valign="top" rowspan=%d>' % (numrows,)
                s += 'Mandatory&nbsp;keys:</td>'
                if typ.mandatory:
                    s += type_table(typ.mandatory)
                else:
                    s += '<td class="definition" colspan="3">None.</td></tr>'

                numrows = len(typ.optional) + 1
                s += '<tr><td class="attribute" valign="top" rowspan=%d>' % (numrows,)
                s += 'Optional&nbsp;keys:</td>'
                if typ.optional:
                    s += type_table(typ.optional)
                else:
                    s += '<td class="definition" colspan="3">None.</td></tr>'
            s += '<tr><td colspan="3">&nbsp;</td></tr>'
            
        s += '</table>'
        s += '</td></tr>'

        categories = self.api.categories_for_function(self)
        if categories:
            s += '<tr><td class="attribute">See&nbsp;also:</td>'
            s += '<td class="definition">'

            for cat in categories:
                s += cat.desc + ':'
                s += '<div class="catlist" style="padding-left: 40px;">'
                for fun in self.api.functions_in_category(cat):
                    name = fun.rpcname
                    s += '<a href="/functions/%s" class="funlink">%s()</a> &nbsp; ' % (name, name)
                s += '</div>'
        s += '</td></tr>'
        s += '</table></div>'
        return s



