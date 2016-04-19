#!/usr/bin/env python2.6
import inspect
import os
import sys

from protocol import *
from rpcc import *


env_prefix = "ADHOC_"

# Automagic way to find out the home of adhoc.
adhoc_home = os.path.join(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))), "..", "..")

os.environ[env_prefix + "RUNTIME_HOME"] = adhoc_home  # Export as env variable ADHOC_RUNTIME_HOME if needed outside server

sys.path.append(adhoc_home)
sys.path.append(os.path.join(adhoc_home, 'adhoc-server'))
sys.path.append(os.path.join(adhoc_home, 'adhoc-server', 'lib'))
sys.path.append(os.path.join(adhoc_home, 'lib'))

for path in sys.path: print path



class AdHocServer(Server):
    envvar_prefix = env_prefix
    service_name = "AdHoc"
    major_version = 0
    minor_version = 1
    
    from util import AdHocSuperuserGuard
    
    superuser_guard = AdHocSuperuserGuard
    
    
class StartMe(object):

    def __init__(self, host, port, enable_ssl=False, generic_password=None, logger=None):
        
        self.logger = logger if logger else logging.getLogger(__name__)

        ssl_config = None
        if enable_ssl:
            self.logger.info("Enabling SSL")
            keyfile = os.environ.get('RPCC_SERVER_SSL_KEYFILE', 'etc/rpcc_server.key')
            certfile = os.environ.get('RPCC_SERVER_SSL_CERTFILE', 'etc/rpcc_server.cert')

            ssl_config = SSLConfig(keyfile, certfile)

        srv = AdHocServer(host, port, ssl_config, logger=logger, generic_password=generic_password)

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
        srv.enable_static_documents(os.path.join(adhoc_home, "adhoc-server", 'docroot'))
        srv.enable_digs_and_updates()
        
        srv.check_tables(tables_spec=None, dynamic=False, fix=False)
        
        srv.add_protocol_handler("dhcpd", DhcpdConfProtocol)
        
        self.srv = srv
        
    def serve_forever(self):
        self.srv.serve_forever()
        
if __name__ == "__main__":
    
    import argparse  # @UnresolvedImport

    argv = []
    argv.append(sys.argv[0])

    parser = argparse.ArgumentParser(description='Run the AdHoc server')
    parser.add_argument('--host', metavar='host', type=str, help="Host name to react on", default="localhost")
    parser.add_argument('--port', metavar='port', type=int, help="Port number to serve", default=4433)
    parser.add_argument('--ssl', action='store_true', help="Use SSL/TLS and serve https instead of http")
    parser.add_argument('--debug', action='store_true', help="Print debugging info on stdout")

    opts = parser.parse_args()

    logger = logging.getLogger(__name__)
    lvl = logging.DEBUG if opts.debug else logging.INFO
    logger.setLevel(lvl)

    sh = logging.StreamHandler()
    sh.setLevel(lvl)

    formatter = logging.Formatter('%(asctime)s %(levelname)8s %(filename)20s:%(lineno)-5s %(message)s')
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    generic_password = os.environ.get("ADHOC_GENERIC_PASSWORD", None)

    os.environ['PDB4_GENERIC_PASSWORD'] = 'xxxxxxxxxxxxxxx'  # Possibly zap the password
        
    protocol = "HTTPS" if opts.ssl else "HTTP"
    
    starter = StartMe(opts.host, opts.port, generic_password=generic_password, enable_ssl=opts.ssl, logger=logger)
    
    if starter.srv.config("SKIP_DHCPD_CHECKS", default=None):
        logger.warning("WARNING: DHCPD Checks disabled. Remove ADHOC_SKIP_DHCPD_CHECKS from the environment and define ADHOC_DHCPD_PATH")
        
    logger.info("Serving %s on '%s' port %d." % (protocol, opts.host, opts.port))
    starter.serve_forever()
