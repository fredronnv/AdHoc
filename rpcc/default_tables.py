#!/usr/bin/env python

import database

from database import *
            

def table_exists(db, q_check, tbl, cols, fix, q_create, q_addcol):
    while(True):
        try:
            dummy = list(db.get(q_check))
            return True
        except database.InvalidIdentifierError as e:
            if fix:
                for col in cols:
                    try:
                        # TODO: Column type specification not done
                        db.put(q_addcol, tbl, col)
                    except:
                        print "COLUMN %s MISSING FROM TABLE %s - FIX MANUALLY" % (col, tbl)
                        return False
                continue
            else:
                print "COLUMN %s MISSING FROM TABLE %s - FIX MANUALLY" % (e.identifier, tbl)
                return False
        except database.InvalidTableError as e:
            if fix:
                try:
                    db.put(q_create, tbl)
                except:
                    print "TABLE %s MISSING FROM DATABASE - FIX MANUALLY" % (tbl,)
                    return False
                continue
            else:
                print "TABLE %s MISSING FROM DATABASE - FIX MANUALLY" % (tbl,)
                return False
        except Exception as e:
            raise

def oracle_exists(db, tbl, tblspec, fix=False):
    q_check = "SELECT " + ", ".join(tblspec.keys()) + " FROM " + tbl + " WHERE ROWNUM < 2"
    q_create = "CREATE TABLE :t"
    q_addcol = "ALTER TABLE :t ADD COLUMN :c TYPE X"
    
    return table_exists(db, q_check, tbl, tblspec, fix, q_create, q_addcol);
   
#TODO: Add column type specification

_spec = [ 
          DBTable("rpcc_result", "Dig results help table", 
                  engine=EngineType.memory,
                  columns=
                  [
                   DBColumn("resid", VType.integer, 16, primary=True, autoincrement=True),
                   DBColumn("manager", VType.string, 32, index=True),
                   DBColumn("expires", VType.datetime),
                   ]),
          DBTable("rpcc_result_string", "Dig string results help table",
                  engine=EngineType.memory,
                  columns = 
                  [
                   DBColumn("resid", VType.integer, 16),
                   DBColumn("value", VType.string, 64, index=True),
                  ]),
          DBTable("rpcc_result_int", "Dig integer results help table",
                  engine=EngineType.memory,
                  columns = 
                  [
                   DBColumn("resid", VType.integer, 16),
                   DBColumn("value", VType.integer, 16, index=True),
                  ]),
          DBTable("rpcc_session",
                  engine=EngineType.transactional,
                  columns =
                  [
                   DBColumn("id", VType.string, 64, primary=True),
                   DBColumn("expires", VType.datetime),
                   ]),
          DBTable("rpcc_session_string", 
                  engine=EngineType.transactional,
                  columns = 
                  [
                   DBColumn("session_id", VType.string, 64, primary=True),
                   DBColumn("name", VType.string, 32),
                   DBColumn("value",VType.string, 64, index=True),
                   ]),
          ]
           
_ospec = [
       ("rpcc_session",("id", "expires")),
       ("rpcc_session_string", ("session_id", "name", "value")),
       ("rpcc_result", ("resid", "manager", "expires")),
       ("rpcc_result_string", ("resid", "value")),
       ("rpcc_result_int", ("resid", "value"))]


def check_default_oracle_tables(db, fix=False, spec=_spec):
    ok = True
    for (tbl, tblspec) in spec.iteritems():
        if not oracle_exists(db, tbl, tblspec, fix):
            ok = False
   
    if not ok:
        raise ValueError("Not all RPCC default tables are correct")

def mysql_exists(db, tbl, tblspec, fix=False):
    q_check = "SELECT " + ", ".join(tblspec.keys()) + " FROM " + tbl + " LIMIT 1"
    q_create = "CREATE TABLE :t";
    q_addcol = "ALTER TABLE :t ADD COLUMN :c TYPE X"
    return table_exists(db, q_check, tbl, tblspec, fix, q_create, q_addcol);


def check_default_mysql_tables(db, fix=False, spec=_spec):
    ok = True
    for (tbl, tblspec) in spec.iteritems():
        if not mysql_exists(db, tbl, tblspec, fix):
            ok = False

    if not ok:
        raise ValueError("Not all RPCC default tables are correct")
    
def sqlite_exists(db, tbl, tblspec, fix=False):

    q_check = "SELECT " + ", ".join(tblspec.keys()) + " FROM " + tbl + " LIMIT 1"
    q_addcol = "ALTER TABLE :t ADD COLUMN :c TYPE X"

    q_create = "CREATE TABLE :t(";
    colspec = []
    for colname, typespec in tblspec.iteritems():
        colspec.append( colname + " " + sqlite_coltype(typespec))
        q_create += ",".join(colspec)
    return table_exists(db, q_check, tbl, tblspec, fix, q_create, q_addcol);

def sqlite_coltype(typespec):
    pass

def check_default_sqlite_tables(db, fix=False, spec=_spec):
    ok = True
    for (tbl, tblspec) in spec.iteritems():
        if not sqlite_exists(db, tbl, tblspec, fix):
            ok = False

    if not ok:
        raise ValueError("Not all RPCC default tables are correct")
