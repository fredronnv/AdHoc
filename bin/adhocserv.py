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


import server
import session
import database
import authentication

from model import *
from exttype import *
from dhcp_manager import DHCPManager, DhcpdConf, DhcpXfer


class AdHocServer(server.Server):
    envvar_prefix = env_prefix
    service_name = "AdHoc"
    major_version = 0
    minor_version = 1

srv = AdHocServer("nile.medic.chalmers.se", 12121)

srv.enable_database(database.MySQLDatabase)
srv.database.check_rpcc_tables()
srv.register_manager(session.DatabaseBackedSessionManager)
srv.register_manager(authentication.NullAuthenticationManager)
srv.register_manager(DHCPManager)
srv.register_function(DhcpdConf)
srv.register_function(DhcpXfer)
srv.enable_documentation()
srv.enable_static_documents(os.path.join(adhoc_home, 'docroot'))
srv.enable_digs_and_updates()
srv.serve_forever()
