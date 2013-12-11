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
    needs_database = False  # Not needed

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
    needs_database = False  # Not needed

    def do(self):
        import socket
        return socket.gethostname()


class Fn_Ping(Function):
    extname = 'server_ping'
    params = []
    rettype = ExtNull
    needs_database = False  # I'll do it myself

    desc = """Checks that the server is alive.

    This includes for example contacting the database to check that the
    connection is working."""

    def do(self):
        db = None
        try:
            db = self.server.database.get_link()
            db.get('SELECT 1')
            #self.server.db_handler.restart_passive_links()
        except:
            raise ExtRuntimeError("Database link not working")
        
        finally:
            if db:
                self.server.database.return_link(db)
