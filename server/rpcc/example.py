#!/usr/bin/env python2.6

from server import Server
from function import Function
import exttype
import authentication



class FnAdd(Function):
    extname = "add"
    to_version = 0
    params = [("num1", exttype.ExtInteger, "Number 1"),
              ("num2", exttype.ExtInteger, "Number 2")]

    returns = (exttype.ExtInteger, "Sum of num1 and num2")

    desc = "Sums two integers and returns their sum."

    def do(self):
        return self.num1 + self.num2


class FnAdd2(Function):
    from_version = 1
    extname = "add"

    params = [("num1", exttype.ExtInteger, "Number 1"),
              ("num2", exttype.ExtInteger, "Number 2"),
              ("num3", exttype.ExtInteger, "Number 3")]

    returns = (exttype.ExtInteger, "Sum of num1, num2 and num3")

    desc = "Sums three integers and returns their sum."

    def do(self):
        return self.num1 + self.num2 + self.num3


class MyServer(Server):
    authenticator = authentication.NullAuthenticationManager

srv = Server("venus.ita.chalmers.se", 12121)
srv.register_function(FnAdd)
srv.register_function(FnAdd2)
srv.serve_forever()
