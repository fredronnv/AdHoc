#!/usr/bin/env python
"""HTTPS XMLRPC Server.

(c)2007 Viktor Fougstedt <viktor@chalmers.se>.

Released under BSD License. You may do what you want with the code,
even commercially, but must give credit when doing so.

SSL server code based on
http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/496786 by Laszlo Nagy.

To implement RPC:s, subclass RPCFunction:

  class Fun_Add(RPCFunction):
      rpcname = 'add'

      def do(self, i1, i2):
          return i1 + i2

To use, instantiate RPCServer, passing the local ip address, port number,
and paths to key/cert files for HTTPS. Optionally include an RPCSession
subclass to use for sessions (which, if given, overrides the class
attribute for selecting such a class).                             

  srv = RPCServer('127.0.0.1', 443, '/some/key.file', '/some/cert.file')
or
  srv = RPCServer('127.0.0.1', 443, '/some/key.file', '/some/cert.file',
                  session_class=MyRPCSessionSubclass)

Then register your RPCFunction subclasses:

  srv.register_class(Fun_Add)

or, if you have an entire module of such subclasses:

  import my_rpc_module
  srv.register_classes_from_module(my_rpc_module)

Then start serving:
  srv.serve_forever()

Sessions are persistent during a server's uptime (only stored in
memory), and can hold arbitrary attributes for future reference.

The included TypedRPCFunction base class includes functionality for
automatically creating documentation. Use the attributes .params and
.doc to enable this functionality.

The .params attribute of your subclass should be a sequence of
tuples. Each such tuple describes one parameter of your function. The
members of the tuple are a parameter name, which is both externally
and internally visible, a parameter type, and a description of the
parameters role in the call.

When the function is called, the parameters are parsed using the
supplied RPCType subclasses, and attributes of the TypedRPCFunction
instance named equally to the parameters name are set to the results.

An RPCTypedFunction also has a .signature() method which returns a
succint signature and a .documentation() method which returns ASCII
text describing the function, its parameters and their types.

class Func_SetAccountOwner(RPCTypedFunction):
    rpcname = 'set_account_owner'

    params = ( ('session', SessionIdType, 'Session identifier of context'),
                ('account', UserNameType, 'The account to set owner for'),
                ('owner', UserNameType, 'The account to set as owner') )

    doc = 'Updates an account, setting another account as it's owner.'

    def call():
        target = self.account
        target.require_priv('update', self.session.authuser)
        target.set_owner(self.owner)
"""

DEBUG = True

from access import *
from api import *
from api_handler import *
from authentication import *
from category import *
from database import *
from default_function import *
from error import *
from exttype import *
from function import *
from model import *
from request_handler import *
from response import *
from protocol import *
from server import *
from session import *
