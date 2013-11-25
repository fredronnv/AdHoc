#!/usr/bin/env python2.6
import inspect
import os


import sys

env_prefix = "ADHOC_"

adhoc_home = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
os.environ[env_prefix + "RUNTIME_HOME"] = adhoc_home

sys.path.append(env_prefix + "RUNTIME_HOME")
sys.path.append(os.path.join(os.environ[env_prefix + "RUNTIME_HOME"], 'rpcc'))
print adhoc_home
print sys.path

import server
import authenticator
import database
import session


class MyServer(server.Server):
    envvar_prefix = env_prefix

srv = MyServer("nile.medic.chalmers.se", 12121)

srv.enable_database(database.MySQLDatabase)
srv.database.check_rpcc_tables()
srv.enable_sessions(session.DatabaseSessionStore)
srv.enable_authentication(authenticator.NullAuthenticator)
srv.enable_documentation()
srv.enable_static_documents(adhoc_home + '/docroot')
srv.enable_digs_and_updates()
srv.serve_forever()
