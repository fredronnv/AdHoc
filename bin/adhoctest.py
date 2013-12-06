#!/usr/bin/env python2.6
import inspect
import os
import sys

env_prefix = "ADHOC_"

# Automagic way to find out the home of adhoc.
adhoc_home = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
os.environ[env_prefix + "RUNTIME_HOME"] = adhoc_home  # Export as env variable ADHOC_RUNTIME_HOME if needed outside server

sys.path.append(adhoc_home)
sys.path.append(os.path.join(adhoc_home, 'rpcc'))


from function import Function

import server
import access
import session
import database
import authentication

from model import *
from exttype import *
from dhcp_manager import DHCPManager, DhcpdConf, DhcpXfer


class ExtNoSuchNetworkError(ExtLookupError):
    desc = "No such network exists."


class ExtNetwork(ExtString):
    name = "network"
    desc = "ID of a DHCP network"

    def lookup(self, fun, cval):
        return fun.network_manager.get_network(cval)

    def output(self, fun, obj):
        return obj.oid


class Network(Model):
    name = "network"
    exttype = ExtNetwork
    id_type = str

    def init(self, netid):
        print "Network.init", netid
        self.oid = netid
        self.authoritative = True
        self.info = None

    @template("network", ExtNetwork)
    def get_account(self):
        return self

    @template("authoritative", ExtBoolean)
    def get_authoritative(self):
        return self.authoritative

    @template("info", ExtString)
    def get_owner(self):
        return self.info


class NetworkManager(Manager):
    name = "network_manager"
    manages = Network

    result_table = "rpcc_result_string"
    model_lookup_error = ExtNoSuchNetworkError

    def init(self):
        self._model_cache = {}

    def base_query(self, dq):
        dq.select("nw.id", "nw.authoritative", "nw.info")
        dq.table("networks nw")
        return dq

    def get_network(self, netid):
        return self.model(netid)

    def search_select(self, dq):
        dq.table("networks nw")
        dq.select("nw.id")

    @search("network", StringMatch)
    def s_net(self, dq):
        dq.table("networks nw")
        return "nw.id"
    
    
class Fn_Ping(Function):
    extname = 'server_ping'
    params = []
    returns = ExtNull

    desc = """Checks that the server is alive.

    This includes for example contacting the database to check that the
    connection is working."""

    def do(self):
        dummy = self.db.get("SELECT 1")
        
        
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
    

class AdHocServer(server.Server):
    envvar_prefix = env_prefix
    service_name = "AdHoc"
    major_version = 0
    minor_version = 1

srv = AdHocServer("nile.medic.chalmers.se", 12121)

srv.enable_database(database.MySQLDatabase)
srv.database.check_rpcc_tables()
srv.register_manager(NetworkManager)
srv.register_manager(session.DatabaseBackedSessionManager)
srv.register_manager(authentication.NullAuthenticationManager)
srv.register_manager(DHCPManager)
srv.register_function(DhcpdConf)
srv.register_function(DhcpXfer)
srv.register_function(Fn_Ping)
srv.register_function(Fn_ServerVersion)
srv.register_function(Fn_ServerNodeName)
srv.enable_documentation()
srv.enable_static_documents(os.path.join(adhoc_home, 'docroot'))
srv.enable_digs_and_updates()
srv.serve_forever()
