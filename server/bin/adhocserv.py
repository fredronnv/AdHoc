#!/usr/bin/env python2.6
import inspect
import os
import sys

env_prefix = "ADHOC_"

# Automagic way to find out the home of adhoc.
adhoc_home = os.path.join(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))), "..", "..")

os.environ[env_prefix + "RUNTIME_HOME"] = adhoc_home  # Export as env variable ADHOC_RUNTIME_HOME if needed outside server

sys.path.append(adhoc_home)
sys.path.append(os.path.join(adhoc_home, 'server'))
sys.path.append(os.path.join(adhoc_home, 'server', 'lib'))
sys.path.append(os.path.join(adhoc_home, 'lib'))


from rpcc import *
from protocol import *
from util import AdHocSuperuserGuard


class AdHocServer(Server):
    envvar_prefix = env_prefix
    service_name = "AdHoc"
    major_version = 0
    minor_version = 1
    
    from util import AdHocSuperuserGuard
    superuser_guard = AdHocSuperuserGuard
    
    
class StartMe(object):
    def __init__(self, host, port, enable_ssl=False):

        ssl_config = None
        if enable_ssl:
            print "Enabling SSL"
            keyfile = os.environ.get('RPCC_SERVER_SSL_KEYFILE', 'etc/rpcc_server.key')
            certfile = os.environ.get('RPCC_SERVER_SSL_CERTFILE', 'etc/rpcc_server.cert')

            ssl_config = SSLConfig(keyfile, certfile)

        srv = AdHocServer(host, port, ssl_config)

        srv.enable_database(MySQLDatabase)

        scriptdir = os.path.dirname(os.path.realpath(__file__))
        (scriptparent, _tail) = os.path.split(scriptdir)
        serverdir = os.path.join(scriptparent, "lib")

        srv.register_manager(session.DatabaseBackedSessionManager)
        
        srv.register_manager(event.EventManager)
        event.EventManager.clean_all_markers(srv)
        
        srv.register_from_directory(serverdir)
        srv.register_manager(authentication.KerberosAuthenticationManager)
        srv.enable_global_functions()
        srv.enable_documentation()
        srv.enable_static_documents(os.path.join(adhoc_home, 'docroot'))
        srv.enable_digs_and_updates()
        
        srv.check_tables(tables_spec=None, dynamic=False, fix=False)
        
        srv.add_protocol_handler("dhcpd", DhcpdConfProtocol)
        
        self.srv = srv
        
if __name__ == "__main__":
    
    if len(sys.argv) > 1:
        if ':' in sys.argv[1]:
            host, port = sys.argv[1].split(':')
            if port:
                try:
                    port = int(port)
                except:
                    print "Invalid port number:", port
                    raise
            else:
                port = 4433
        else:
            host = 'localhost'
            port = int(sys.argv[1])
    else:
        host, port = 'localhost', 4433

    enable_ssl = os.environ.get("ADHOC_SSL_ENABLE", "0") != "0"

    if enable_ssl:
        print "Serving HTTPS on '%s' port %d." % (host, port)
    else:
        print "Serving HTTP on '%s' port %d." % (host, port)
        
    starter = StartMe(host, port, enable_ssl=enable_ssl)
    
    if starter.srv.config("SKIP_DHCPD_CHECKS", default=None):
        print "WARNING: DHCPD Checks disabled. Remove ADHOC_SKIP_DHCPD_CHECKS from the environment and define ADHOC_DHCPD_PATH"
        
    starter.srv.serve_forever()
