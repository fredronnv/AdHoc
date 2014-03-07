#!/usr/bin/env python2.6
import inspect
import os
import sys

env_prefix = "ADHOC_"

# Automagic way to find out the home of adhoc.
adhoc_home = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) + "/.."
#print "ADHOC_HOME=", adhoc_home
os.environ[env_prefix + "RUNTIME_HOME"] = adhoc_home  # Export as env variable ADHOC_RUNTIME_HOME if needed outside server

sys.path.append(adhoc_home)
sys.path.append(os.path.join(adhoc_home, 'server'))

from rpcc import *
from util import *


class AdHocServer(Server):
    envvar_prefix = env_prefix
    service_name = "AdHoc"
    major_version = 0
    minor_version = 1
    
    superuser_guard = AdHocSuperuserGuard
    
       
srv = AdHocServer("localhost", 12121)

srv.enable_database(MySQLDatabase)
srv.database.check_rpcc_tables()

scriptdir = os.path.dirname(os.path.realpath(__file__))
(scriptparent, tail) = os.path.split(scriptdir)
serverdir = os.path.join(scriptparent, "server")

srv.register_manager(session.DatabaseBackedSessionManager)

srv.register_manager(event.EventManager)

# Find the server directory and register all managers and functions in the modules found.
seen_managers = []  # Avoid duplicating registrations. This can happen if managers are imported from other objects.

for file in os.listdir(serverdir):
    mo = re.match(r"^([a-z_]+).py$", file)
    if not mo:
        continue
    module = __import__(mo.group(1))
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj):
            if issubclass(obj, model.Manager):
                if hasattr(obj, "name") and obj.name and obj.name not in seen_managers:
                    try:
                        srv.register_manager(obj)
                        seen_managers.append(obj.name)
                    except:
                        print "Failed to register manager ", obj, " in module", mo.group(1)
                        raise
    srv.register_functions_from_module(module)
             

srv.register_manager(authentication.NullAuthenticationManager)
srv.enable_global_functions()
srv.enable_documentation()
srv.enable_static_documents(os.path.join(adhoc_home, 'docroot'))
srv.enable_digs_and_updates()
srv.serve_forever()
