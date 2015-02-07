#!/usr/bin/env python2.6

from rpcc import *
from unsessioned_person import *

srv = Server("localhost", 12121) # Create a server instance

srv.enable_documentation()  # Enable documentation functions

srv.enable_database(SQLiteDatabase, database="unsessioned_database")
srv.register_manager(PersonManager)
srv.register_model(Person)
srv.register_function(PersonCreate)
srv.register_function(PersonRemove)

srv.enable_digs_and_updates()

srv.check_tables(tables_spec=None, dynamic=True, fix=True)

srv.serve_forever() # Start serving. 
# Now point your browser to http://localhost:12121/api/0
# Also run sqlite3 on the database rpcc_scratch_database
