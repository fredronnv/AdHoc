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
sys.path.append(os.path.join(adhoc_home, 'lib'))
sys.path.append(os.path.join(adhoc_home, 'lib','python2.6'))

from rpcc import *
from util import *


class AdHocServer(Server):
    envvar_prefix = env_prefix
    service_name = "AdHoc"
    major_version = 0
    minor_version = 1
    
    superuser_guard = AdHocSuperuserGuard
    
    
    
class StartMe(object):
    def __init__(self, host, port, generic_password=None, enable_ssl=False):

	ssl_config = None
        if enable_ssl:
            print "Enabling SSL"
            keyfile = os.environ.get('RPCC_SERVER_SSL_KEYFILE', 'etc/xmlrpc_server.key')
            certfile = os.environ.get('RPCC_SERVER_SSL_CERTFILE', 'etc/xmlrpc_server.cert')
            chainfile = os.environ.get('RPCC_SERVER_SSL_CHAINFILE', None)

	    ssl_config = SSLConfig(keyfile, cerftfine, chainfile)

        srv = AdHocServer(host, port, ssl_config)

        srv.enable_database(MySQLDatabase)
        srv.database.check_rpcc_tables()

        scriptdir = os.path.dirname(os.path.realpath(__file__))
        (scriptparent, tail) = os.path.split(scriptdir)
        serverdir = os.path.join(scriptparent, "server")

        srv.register_manager(session.DatabaseBackedSessionManager)
        
        srv.register_manager(event.EventManager)
        srv.generic_password=generic_password
        
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
        


if __name__ == "__main__":
    import sys, os
    
    if len(sys.argv) > 1:
        if ':' in sys.argv[1]:
	    print  sys.argv[1]
            host, port = sys.argv[1].split(':')
            port = int(port)
        else:
            host = 'localhost'
            port = int(sys.argv[1])
    else:
        host, port = 'localhost', 4433

    generic_password = os.environ.get("ADHOC_GENERIC_PASSWORD", None)

    enable_ssl = os.environ.get("ADHOC_SSL_ENABLE", False)
    
    if enable_ssl:
        print "Serving HTTPS on '%s' port %d." % (host, port)
    else:
        print "Serving HTTP on '%s' port %d." % (host, port)
        
    starter = StartMe(host, port, generic_password=generic_password, enable_ssl=enable_ssl)
    starter.serve_forever()
    
