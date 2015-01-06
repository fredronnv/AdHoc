#!/usr/bin/env python2.6

from rpcc import SimpleFunction, ExtString, exttype, Server 


class FnHello(SimpleFunction):
    extname = "hello"
    returns = (exttype.ExtString, "A friendly greeting")
    desc = "Returns a friendly greeting"

    def do(self):
        return "Hello my friend"

class FnHelloTo(SimpleFunction):
    extname = "hello_to"
    params = [("me", ExtString, "Name of someone to say hello to")]

    returns = (exttype.ExtString, "A friendly personal greeting")

    def do(self):
        return "Hello %s my friend, how are you today?" % self.me

srv = Server("localhost", 12121)
srv.register_function(FnHello)
srv.register_function(FnHelloTo)
srv.serve_forever()
