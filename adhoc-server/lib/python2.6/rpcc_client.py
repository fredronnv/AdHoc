#!/home/viktor/python2.6/bin/python2.6
# -*- coding: utf-8 -*-
"""
Client for RPCC servers.

To create a client proxy, instantiate the RPCCProxy class.

  rpcc = RPCCProxy("https://some.where/", api=1, attrdicts=True)

Functions on the server appear as methods on the proxy object. 

  print rpcc.server_list_functions()

Documentation is printed by calling a doc method on the function 
attribute:

  rpcc.server_list_functions.doc()

A list of functions is printed by calling that method on the proxy 
object:

  rpcc.doc()

The proxy object handles sessions automagically. When a function is called
that expects a session argument, and where no such argument is given,
proxy.session_start() is called, and the result kept.

A convenience method rpcc.login([<username>[, <password>]]) calls
session_start() and then session_auth_login(). Username and password are
filled in using getpass.

The proxy uses JSON when communicating with the server.

"""

import getpass
import json
import re
import time
import urllib2


class AttrDict(dict):
    """A dictionary where keys can also be accessed as attributes."""
    def __init__(self, rawdict=None):
        if not rawdict:
            return

        for (key, value) in rawdict.items():
            self[key] = value

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        raise ValueError("Cannot set attributes on AttrDict:s")


class RPCCError(Exception):
    def __init__(self, err):
        Exception.__init__(self, err)
        self.name = err["name"]
        self.namelist = err["namelist"]

    def is_base(self, errname):
        return (self.namelist[0] == errname)

    def is_error(self, errname):
        return (self.namelist[-1] == errname)


class RPCC(object):
    """RPCC client proxy."""

    class FunctionProxy(object):
        def __init__(self, proxy, funname):
            self.proxy = proxy
            self.funname = funname
            
        def doc(self):
            print self.proxy.server_documentation(self.rpcname)
            
        def __call__(self, *args):
            return self.proxy._call(self.funname, *args)

    def __init__(self, url, api_version=0, attrdicts=True, pyexceptions=True):
        self._attrdicts = attrdicts
        self._pyexceptions = pyexceptions

        self._fundefs = {}
        if url[-1] != '/':
            url += "/"
        self._url = url + "json?v%d" % (api_version,)
        self._purl = url.replace("http://", "").replace("https://", "") + "#%d" % (api_version,)
        self._api = api_version
        self._auth = None
        self.reset()

    def __getattr__(self, name):
        if name[0] != '_':
            return self.FunctionProxy(self, name)

    def _rawcall(self, fun, *args):
        #print "RAWCALL", fun, args
        call = json.dumps({"function": fun, "params": args})
        retstr = urllib2.urlopen(self._url, call.encode("utf-8")).read()
        return json.loads(retstr.decode("utf-8"))

    def _fundef(self, fun):
        try:
            if fun not in self._fundefs:
                self._fundefs[fun] = self._rawcall("server_function_definition", fun)["result"]
            return self._fundefs[fun]
        except KeyError:
            raise ValueError("No function %s is defined on the server" % (fun,))

    def _function_is_sessioned(self, fun):
        fundef = self._fundef(fun)
        if len(fundef["parameters"]) == 0:
            return False
        first = fundef["parameters"][0]
        if first["type_name"] == 'session' and first["name"] == 'session':
            return True
        return False

    def _argcount(self, fun):
        return len(self._fundef(fun)["parameters"])
    
    def _get_session(self):
        if self._session_id is None:
            self._session_id = self._rawcall("session_start")["result"]
        return self._session_id

    def stop(self):
        if self._session_id is not None:
            self._rawcall("session_stop", self._session_id)

    def _call(self, fun, *args):
        if self._function_is_sessioned(fun):
            args = [self._get_session()] + list(args)

        if fun.endswith("_dig") and self._argcount(fun) == 3:
            if isinstance(args[1], str) or isinstance(args[1], unicode):
                args[1] = self._parse_digstr(args[1])

            if len(args) == 2:
                args.append({'_': True})
            elif isinstance(args[2], str) or isinstance(args[2], unicode):
                args[2] = self._parse_digstr(args[2])

        # Perform call, measuring passed time.
        start_time = time.time()
        rawret = self._rawcall(fun, *args)
        self._time = time.time() - start_time

        if "result" in rawret:
            # Call succeeded.
            ret = rawret["result"]

            # Save auth and session data from known calls.
            if fun == 'session_auth_login':
                self._auth = args[1]
            elif fun == 'session_deauth':
                self._auth = None
            elif fun.startswith('session_start'):
                self._session_id = ret

            if self._attrdicts:
                ret = self._convert_to_attrdicts(ret)

            return ret
        else:
            # Call returned an error

            err = rawret['error']
            if self._attrdicts:
                err = self._convert_to_attrdicts(err)

            errname = err['name']
            if self._pyexceptions and errname.startswith('ValueError'):
                raise ValueError(err)
            elif self._pyexceptions and errname.startswith('LookupError'):
                raise LookupError(err)
            elif self._pyexceptions and errname.startswith('RuntimeError'):
                raise RuntimeError(err)
            elif self._pyexceptions and errname.startswith('TypeError'):
                raise TypeError(err)
            else:
                raise RPCCError(err)

    def _convert_to_attrdicts(self, val):
        if isinstance(val, dict):
            newdict = AttrDict()
            for (key, subval) in val.items():
                newdict[key] = self._convert_to_attrdicts(subval)
            return newdict
        elif isinstance(val, list):
            return [self._convert_to_attrdicts(elem) for elem in val]
        else:
            return val

    def _parse_digstr(self, digstr):
        """Simple syntax to ease manual _dig():ing.

        When the proxy is instantiated with convert_digs=True:
        * _dig() calls can omit the last parameter, which will be
          filled in as {'_': True}

        * any of the two _dig() parameters can be a string instead
          of a dict. The string will be parsed into a dict using
          the below syntax, and the dict passed in the RPC call.

          The string is a list of tokens separated by ','.

          A token that is just a name [a-z-_] is converted to {token: 
          True}. Otherwise it must be a name:value pair.

          Values #False, #True, #None are converted to False, True, None.

          Values #[0-9]+ are converted to ints.

          Values beginning with { start a sub-dict until the matching }.

          All other values are converted to strings as-is.

          'empty,false:#False,true:#True,none:#None,sub:{int:#1,str:apa}'

          results in a dict

          {'empty': True, 'false': False, 'true': True, 'none': None,
           'sub': {'int': 1, 'str': 'apa'}}
        """

        tokens = re.split("([,:{}])", digstr)
        tokens = [t for t in tokens if t != ""]

        (left, res) = self._parse_dig_tokens(tokens)
        if left:
            raise ValueError()
        return res

    def _parse_dig_tokens(self, tokens):
        out = {}

        while tokens:
            key = tokens.pop(0)
            if key == '}':
                break

            if not tokens:
                out[key] = True
                break

            if tokens[0] == '}':
                tokens.pop(0)
                out[key] = True
                break

            if tokens[0] == ':':
                # Value for the key
                if len(tokens) > 1 and tokens[1] == '{':
                    (tokens, subval) = self.parse_dig_tokens(tokens[2:])
                elif len(tokens) > 0:
                    subval = tokens[1]
                    tokens = tokens[2:]
                else:
                    subval = True
                    
                if isinstance(subval, str) and subval and subval[0] == '#':
                    if subval == '#None':
                        subval = None
                    elif subval == '#False':
                        subval = False
                    elif subval == '#True':
                        subval = True
                    else:
                        subval = int(subval[1:])

                out[key] = subval
            else:
                out[key] = True

            # Value read. If there is a next token, it must be
            # "," meaning "read another key" or "}" meaning
            # return to caller.

            if tokens and tokens[0] == ",":
                tokens.pop(0)

        return (tokens, out)

    def reset(self, password=None):
        """Create a new session with the server. If a previous session
        was authenticated, give the user a password prompt for the
        same username as was previously authenticated. This allows
        to 'restart' a proxy object when the server has been restarted
        or a session has timed out.
        """

        oldauth = self._auth

        self._auth = None
        self._time = None
        self._session_id = None
        self._fundefs = {}

        if not oldauth:
            return "Reconnected to %s" % (self._purl,)
        
        if password is not None:
            if self.session_auth_login(oldauth, password):
                return "Reconnected to %s as %s" % (self._purl, self._auth)
            else:
                return "Restarted with new session to %s, but login for %s failed" % (self._purl, self._auth)
            
        for dummy in range(3):
            try:
                self.session_auth_login(oldauth, getpass.getpass("Reconnect %s@%s, password: " % (oldauth, self._purl)))
                return "Reconnected to %s as %s" % (self._purl, self._auth)
            except RuntimeError as e:
                if len(e.args) == 0:
                    raise
                if "name" not in e.args[0]:
                    raise
                if not e.args[0]['name'].startswith("RuntimeError::AuthenticationFailed"):
                    raise
                pass
            except RPCCError as e:
                if e.is_error("AuthenticationFailed"):
                    pass
                raise

        return "Restarted with new session to %s, but login for %s failed" % (self._purl, oldauth)
                                    
    def doc(self, substr=None):
        funcs = self.server_list_functions()
        if substr:
            funcs = [f for f in funcs if substr in f]
        print "\n".join(funcs)

    def login(self, user=None, password=None):
        if user is None:
            user = getpass.getuser()
        if password is None:
            password = getpass.getpass("Password for %s@%s: " % (user, self._url))
        return self.session_auth_login(user, password)


class XXXRPCC_Krb5(RPCC):
    def reset(self):
        # xmlrpclib.Server cannot pass arbitrary headers with the calls,
        # so run an explicit session_start() to fetch a session id and
        # associate it with a principal.
        
        start_call = xmlrpclib.dumps(tuple(), "session_start", False, "UTF-8")
        req = urllib2.Request(self._url, start_call)
        (scheme, host, path, params, query, fragment) = urlparse.urlparse(self._url)
        if ':' in host:
            host = host.split(':', 1)[0]

        (res, ctx) = kerberos.authGSSClientInit("HTTP@" + host)
        kerberos.authGSSClientStep(ctx, "")
        token = kerberos.authGSSClientResponse(ctx)

        req.add_header('Authorization', "Negotiate " + token)
        result = urllib2.urlopen(req)

        start_response = result.read()
        res = xmlrpclib.loads(start_response)
        self._sid = res[0][0]['result']
        
        self._server = xmlrpclib.Server(self._url, encoding='UTF-8', allow_none=1)
        
    
def pp(d, ind=0):
    for (k, v) in d.iteritems():
        print ' ' * ind + k + ':',
        if type(v) == type({}):
            print '{'
            pp(v, ind + 4)
            print ' ' * ind + '}'
        elif type(v) == type([]):
            print '['
            for sv in v:
                pp(sv, ind + 4)
                print ' ' * ind + ','
            print ' ' * ind + ']'
        else:
            print v

