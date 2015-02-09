#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

from rpcc import *
from user import *

class UserServer(Server):
    envvar_prefix = "USERSERVER_"

if __name__ == "__main__":    
    srv = UserServer("localhost", 12121) # Create a server instance
    
    srv.enable_documentation()  # Enable documentation functions
    
    srv.enable_database(SQLiteDatabase)
    srv.register_manager(DatabaseBackedSessionManager)
    srv.register_manager(UserAuthenticationManager)
    
    srv.register_manager(UserManager)
    srv.register_model(User)
    srv.register_function(UserCreate)
    srv.register_function(UserRemove)
    
    srv.enable_digs_and_updates()
    
    srv.check_tables(tables_spec=None, dynamic=True, fix=True)
    
    srv.enable_static_documents('docroot')
    
    srv.serve_forever() # Start serving. 
    # Now point your browser to http://localhost:12121/api/0
    # Also run sqlite3 on the database rpcc_scratch_database
