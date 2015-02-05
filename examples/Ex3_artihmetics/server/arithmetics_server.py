#!/usr/bin/env python2.6

# This server implements four artihmetics functions.
# It also demonstrates returning structured data and
# enables the documentation functionality.
# The last thing makes it possible to use the rpcc_client library.
# Now also point your browser to http://localhost:12121/api/0 to browse the documentation
# of all functione exported by the server.

from rpcc import *


class FnAdd2(SimpleFunction):
    extname = "add2"
    params = [("num1", exttype.ExtInteger, "Number 1"),
              ("num2", exttype.ExtInteger, "Number 2")]

    returns = (exttype.ExtInteger, "Sum of num1 and num2")

    desc = "Sums two integers and returns their sum."

    def do(self):
        return self.num1 + self.num2
    

class FnSub2(SimpleFunction):
    extname = "sub2"
    params = [("num1", exttype.ExtInteger, "Number 1"),
              ("num2", exttype.ExtInteger, "Number 2")]

    returns = (exttype.ExtInteger, "Difference between num1 and num2")

    desc = "Subracts Number 2 from Number 1 and returns the difference"

    def do(self):
        return self.num1 - self.num2
    
    
class FnMul2(SimpleFunction):
    extname = "mul2"
    params = [("num1", exttype.ExtInteger, "Number 1"),
              ("num2", exttype.ExtInteger, "Number 2")]

    returns = (exttype.ExtInteger, "Product of num1 and num2")

    desc = "Multiplies Number 1 with Number 2 and returns their product"

    def do(self):
        return self.num1 * self.num2


# Define a structure to be returned from the div2 function    
class ExtDivisionResult(ExtStruct):
    name = "division-result"
    mandatory = { "quotient": (ExtInteger, "Quotient of division"),
                  "residue": (ExtInteger, "Residue after divsion")}
    
    
class FnDiv2(SimpleFunction):
    extname = "div2"
    params = [("denominator", ExtInteger, "Denominator"),
              ("dividend", exttype.ExtInteger, "Dividend")]

    returns = (ExtDivisionResult, "Quotient and residue when dividing the Denominator with the dividend")

    desc = "Divides two numbers and returns both quotient and residue"

    def do(self):
        d = {"quotient": self.denominator / self.dividend,
             "residue": self.denominator - ((self.denominator / self.dividend) * self.dividend) 
             }
        return d

srv = Server("localhost", 12121)
# Register the functions
srv.register_function(FnAdd2)
srv.register_function(FnSub2)
srv.register_function(FnMul2)
srv.register_function(FnDiv2)

srv.enable_documentation()  # Enable documentation functions
srv.serve_forever()
