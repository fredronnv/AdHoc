#!/usr/bin/env python2.6
from rpcc.exttype import *
from rpcc.function import Function


class ExtVersion(ExtStruct):
    name = "server-version-type"
    desc = "Struct describing the server service and version"
    
    mandatory = {
        'service': ExtString,
        'major': ExtString,
        'minor': ExtString
        }


class Fn_ServerVersion(Function):
    extname = 'server_version'
    desc = "Returns a struct indicating the version of this server."
    params = []
    returns = (ExtVersion, "The service and version information")

    def do(self):
        return {'service': self.server.service_name,
                'major': str(self.server.major_version),
                'minor': str(self.server.minor_version)
                }
      

class Fn_ServerNodeName(Function):
    extname = "server_node_name"
    params = []
    returns = ExtString
    desc = "Returns the host name of the currently connected server."

    def do(self):
        import socket
        return socket.gethostname()
