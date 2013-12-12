#!/usr/bin/env python2.6
import inspect
import os
import sys

env_prefix = "ADHOC_"

# Automagic way to find out the home of adhoc.
adhoc_home = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))+"/.."
#print "ADHOC_HOME=", adhoc_home
os.environ[env_prefix + "RUNTIME_HOME"] = adhoc_home  # Export as env variable ADHOC_RUNTIME_HOME if needed outside server

sys.path.append(adhoc_home)
sys.path.append(os.path.join(adhoc_home, 'server'))

#for p in sys.path:
    #print p
#import rpcc.server
#import rpcc.session
#import rpcc.database
#import rpcc.authentication

#from model import *
#from exttype import *
#from dhcp_manager import DHCPManager, DhcpdConf, DhcpXfer


from rpcc.server import Server
from rpcc.database import MySQLDatabase
import dhcp 
import util
import shared_network
import dhcp_server

import rpcc


class AdHocServer(Server):
    envvar_prefix = env_prefix
    service_name = "AdHoc"
    major_version = 0
    minor_version = 1
srv = AdHocServer("nile.medic.chalmers.se", 12121)

srv.enable_database(MySQLDatabase)
srv.database.check_rpcc_tables()
srv.register_manager(rpcc.session.DatabaseBackedSessionManager)
srv.register_manager(rpcc.authentication.NullAuthenticationManager)
srv.register_manager(dhcp.DHCPManager)
srv.register_manager(shared_network.NetworkManager)
srv.register_manager(dhcp_server.DHCPServerManager)
srv.register_functions_from_module(dhcp)
srv.register_functions_from_module(util)
srv.register_functions_from_module(shared_network)
srv.register_functions_from_module(dhcp_server)

srv.enable_documentation()
srv.enable_static_documents(os.path.join(adhoc_home, 'docroot'))
srv.enable_digs_and_updates()
srv.serve_forever()
