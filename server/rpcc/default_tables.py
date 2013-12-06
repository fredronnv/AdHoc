#!/usr/bin/env python

import database


def oracle_exists(db, tbl, cols):
    try:
        q = "SELECT " + ", ".join(cols) + " FROM " + tbl + " WHERE ROWNUM < 2"
        dummy = list(db.get(q))
        return True
    except database.InvalidIdentifierError as e:
        print "COLUMN %s MISSING FROM TABLE %s - FIX MANUALLY" % (e.identifier, tbl)
        return False
    except database.InvalidTableError as e:
        print "TABLE %s MISSING FROM DATABASE - FIX MANUALLY" % (tbl,)
        return False
    except Exception as e:
        raise

_spec = [("rpcc_session", ("id", "expires")),
       ("rpcc_session_string", ("session_id", "name", "value")),
       ("rpcc_result", ("resid", "manager", "expires")),
       ("rpcc_result_string", ("resid", "value")),
       ("rpcc_result_int", ("resid", "value"))]


def check_default_oracle_tables(db):
    ok = True
    for (tbl, cols) in _spec:
        if not oracle_exists(db, tbl, cols):
            ok = False

    if not ok:
        raise ValueError("Not all RPCC default tables are correct")


def mysql_exists(db, tbl, cols):
    try:
        q = "SELECT " + ", ".join(cols) + " FROM " + tbl + " LIMIT 1"
        dummy = list(db.get(q))
        return True
    except database.InvalidIdentifierError as e:
        print "COLUMN %s MISSING FROM TABLE %s - FIX MANUALLY" % (e.identifier, tbl)
        return False
    except database.InvalidTableError as e:
        print "TABLE %s MISSING FROM DATABASE - FIX MANUALLY" % (tbl,)
        return False
    except Exception as e:
        raise


def check_default_mysql_tables(db):
    ok = True
    for (tbl, cols) in _spec:
        if not mysql_exists(db, tbl, cols):
            ok = False

    if not ok:
        raise ValueError("Not all RPCC default tables are correct")
