#!/usr/bin/env python

import database

class VType:
    class Integer: pass
    class String: pass
    class Datetime: pass
    class Blob: pass


class DBColumn(object):
    def __init__(self, name, value_type, size=None, autoincrement=None, index=None, primary=False):
        self.name = name
        
        if type(value_type) is not VType:
            raise TypeError("Bad type for database table column")
        self.value_type = value_type
        self.size = size
        if value_type is not VType.Integer:
            raise TypeError("Autoincrement is only for integer type columns")
        self.autoincrement = autoincrement

class DBTable(object):
    
    def __init__(self, name, desc=None, engine=None, collation=None):
        self.name = name
        self.desc = desc
        self.engine = engine
        self.collation = collation
        self.columns = []
        
    def add_column(self, column):
        if type(column) is DBColumn:
            
            self.columns.append(column)
        else:
            raise TypeError("Database column is not of type DBColumn")
    

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
            {"rpcc_result":
                {
                    "columns":
                     {
                        "resid":{"type":"integer", "precision": 16, "primary_key":True, "autoincrement":True},
                        "manager":{"type":"varchar", "precision": 32, "index":True},
                        "expires":{"type":"datetime"}
                     },
                     "engine":"memory"
                }
            },
            
            {"rpcc_result_string": 
                {
                    "columns":
                    {
                        "resid":{"type":"integer", "precision": 16},
                        "value":{"type":"varchar", "precision": 64, "index":True}
                    },
                    "engine": "memory"
                }
            },
            
            {"rpcc_result_int": 
                {
                    "columns":
                    {
                        "resid":{"type":"integer", "precision": 16},
                        "value":{"type":"integer", "precision": 16, "index":True}
                    },
                    "engine": "memory"
                }
            },
            {"rpcc_session":
                {
                    "columns":
                    {
                        "id": {"type":"varchar", "precision": 64, "primary_key":True}, 
                        "expires":{"type":"datetime"}
                    }
                 },
                 "engine":"innodb",
            },
              
            {"rpcc_session_string":
                {
                    "columns":
                    {
                         "session_id": {"type":"varchar", "precision": 64, "primary_key":True},
                         "name":{"type":"varchar", "precision": 32},
                         "value":{"type":"varchar", "precision": 64, "index":True}
                    }
                 },
                 "engine":"innodb",
            }
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
    q_create = "CREATE TABLE :t()";
    q_addcol = "ALTER TABLE :t ADD COLUMN :c TYPE X"

    q_create = "CREATE TABLE :t(";
    colspec = []
    for colname, typespec in tblspec.iteritems():
        colspec.append( colname + " " + sqlite_coltype(typespec))
    q.create += ",".join(colspec)
    return table_exists(db, q_check, tbl, tblspec, fix, q_create, q_addcol);

def sqlite_coltype(typespec):
    

def check_default_sqlite_tables(db, fix=False, spec=_spec):
    ok = True
    for (tbl, tblspec) in spec.iteritems():
        if not sqlite_exists(db, tbl, tblspec, fix):
            ok = False

    if not ok:
        raise ValueError("Not all RPCC default tables are correct")
