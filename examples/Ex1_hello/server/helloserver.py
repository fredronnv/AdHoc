#!/usr/bin/env python2.6

import rpcc

# A super simple RPC server with a single parameterless function.

class FnHello(rpcc.SimpleFunction): # Every RPC function is defined as a subclass of rpcc.Function or a subclass thereof
    extname = "hello" # Every function must have a name.
    returns = (rpcc.exttype.ExtString, "A friendly greeting") # and a definition of what is returned
    desc = "Returns a friendly greeting" # A desrcitipon of the function is also desirable

    def do(self): # The do() method is the actoal implementation of the RPC function
        return "Hello my friend"

srv = rpcc.Server("localhost", 12121) # Create a server instance
srv.register_function(FnHello) # The RPC functions must be registered with the server
srv.serve_forever() # Start serving
