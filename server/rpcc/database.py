#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

"""
Wrapper around Python DB-API 2.0 databases.

A Database subclass implements all functionality specific to a database
engine.

.get_link() gets a DB link as specified below.

.return_link() returns a DB link. It might be reused if the database engine
    is slow to create new links.

.query() returns a DynamicQuery subclass instance specific to the engine. The
    DynamicQuery objects are used to incrementally build queries.


The DatabaseLink subclass implements actual database interaction.

.get(query, **params)
    The query must be a SELECT. Returns an iterator over sequences
    representing the result in native Python data types (for example
    with BLOB:s/CLOB:s processed for database modules that need this).

.put(query, **params)
    The query must be an INSERT or UPDATE. Returns the number of
    affected rows.

.insert(column, query, **params)
    The query must be an INSERT. Returns the new value of an AUTO_INCREMENT
    column. Only works with a single AUTO_INCREMENT column. The column name
    must be given since Oracle needs that.

"""

import threading
import datetime
import re

import default_tables


import exterror

try:
    import cx_Oracle  # @UnresolvedImport
except:
    pass

try:
    import mysql.connector
    #from mysql.connector.conversion import MySQLConverter
    #from mysql.connector.cursor import MySQLCursor
except:
    pass

try:
    import sqlite3
except:
    pass

from enum import Enum
from interror import IntInvalidUsageError

from database_description import *

class DatabaseError(Exception):

    def __init__(self, msg, inner=None):
        Exception.__init__(self, msg)
        if inner:
            self.inner = inner


class LinkError(DatabaseError):
    """There is an error with the database link (i.e. no error with
    the SQL or the data), for example a database that has stopped
    responding."""


class LinkClosedError(LinkError):
    """ The database link was closed"""


class IntegrityError(DatabaseError):
    """There was an error in the data or the use of it (e.g. referencing
    a foreign key that doesn't exist or trying to create duplicate keys
    in unique columns)."""
    pass


class ProgrammingError(DatabaseError):
    """There was an error in the way the programmer uses the database
    (e.g. an SQL syntax error, or the attempted use of a non-existant
    database or column name."""
    pass


class InvalidIdentifierError(ProgrammingError):

    def __init__(self, idf, **kwargs):
        ProgrammingError.__init__(self, "Invalid identifier: " + idf, **kwargs)
        self.identifier = idf


class InvalidTableError(ProgrammingError):

    def __init__(self, tbl, **kwargs):
        ProgrammingError.__init__(self, "Invalid table name: " + tbl, **kwargs)
        self.table = tbl


class DatabaseIterator(object):
    """A DatabaseIterator supplies on-the-fly translation of database-
    specific column values (such as cx_Oracle's BLOB data types), one
    row at a time. The database cursor is used as sub-iterator so
    that data is only read and converted on actual use.

    Subclasses override the convert() method, which should return a
    sequence where possible database-specific values have been type
    converted.
    """

    def __init__(self, curs):
        self.curs = curs
        self.iter = curs.__iter__()

    def __iter__(self):
        return self

    def convert(self, row):
        return row

    def next(self):
        try:
            return self.convert(self.iter.next())
        except (StopIteration, GeneratorExit):
            self.curs.close()
            raise


class DynamicQuery(object):
    """DynamicQuery objects that allow incrementally built queries, as well
    as abstracting common database-specific things like limited queries
    and input variables (which the Python DB-API tragically didn't
    specify a standard for).

    Intended use:

    q = DynamicQuery()
    q.select('p.ucid', 'a.ucid')
    q.table('person p')
    q.table('account a')
    q.where('p.ucid = a.ucid_owner')
    q.where('a.ucid =' + self.var(account.ucid))
    q.limit(100)
    q.run() (OR db.get(q) / db.put(q))
    """

    onre = re.compile("[^a-z]*([a-z]+[.][a-z]+)")

    def __init__(self, link, master_query=None):
        self.link = link
        self.master_query = master_query
        if not master_query:
            self.varid = 0

        self.store_prefix = ""
        self.selects = []
        self.aliases = set()
        self.tables = set()
        self.table_aliases = {}  # Collects table aliases
        self.outers = set()
        self.conditions = set()
        self.subqueries = []
        self.groups = []
        self.havings = []
        self.orders = []
        self.values = {}
        self.limit = None
        self.outer_join_leftside = None
        self.outer_join_alias = None

    def subquery(self, onexpr):
        """Return a DynamicQuery which uses the same database values and
        is executed as a subquery (implicit condition: <onexpr> IN (<subq string>))

        Usage:
          dynq.table(...)
          dynq.wher(...)
          subq = dynq.subquery('foo.x')
          subq.table(...)
          subq.where(...)

        """
        subq = self.__class__(self.link, self)
        self.subqueries.append((onexpr, subq))
        return subq

    def _alias(self, tbldef):
        if " " in tbldef:
            return tbldef.split()[1]
        else:
            return tbldef

    def store_result(self, expr):
        self.store_prefix = expr

    def select(self, *sels):
        self.selects += sels

    def get_select_at(self, idx):
        return self.selects[idx]

    def table(self, *tbls):
        for tbl in tbls:
            if tbl not in self.tables:
                if tbl in self.aliases:
                    raise IntInvalidUsageError("Table name '%s' duplicates an already used table alias")
                self.tables.add(tbl)
                alias = self._alias(tbl)
                if alias != tbl and alias in self.tables:
                    raise IntInvalidUsageError("Table alias '%s' duplicates an already defined table name")
                self.aliases.add(self._alias(tbl))
                self.table_aliases[self._alias(tbl)] = tbl

    def outer(self, tblalias, onexpr):
        """Limited OUTER JOIN functionality.

        One defined table alias must be used on the left side of the first
        comparison in the ON statemement. The same alias must be used
        in _all_ OUTER JOIN:s in the same DynamicQuery

        dquery.table('rpcc_event e')
        dquery.outer('rpcc_event_string es1', 'e.id=es1.event')
        # WRONG (e.id needs to be first in the ON statement):
        dquery.outer('rpcc_event_string es2', 'es2.event=e.id')
        # WRONG (e.id has been used for a previous OUTER and all must 
        #        use the same alias):
        dquery.outer('rpcc_event_string es2', 'es1.event=es2.event')

        """
        try:
            _tbl, alias = tblalias.split(" ")
        except:
            raise ValueError("OUTER JOIN table needs to be aliased like 'tblname al', which '%s' is not" % (tblalias,))

        mo = self.onre.match(onexpr)
        if not mo:
            raise ValueError(
                "OUTER JOIN on-expression needs to have a leftside of the a.b format, '%s' does not" % (onexpr,))

        leftside = self.onre.match(onexpr).group(1)

        if self.outer_join_leftside is None:
            self.outer_join_leftside = leftside
            try:
                alias, _col = leftside.split(".")
            except:
                raise ValueError(
                    "OUTER JOIN on-expression's first leftside needs to be an alias.column value, '%s' is not." % (leftside,))
            if alias not in self.aliases:
                raise ValueError(
                    "OUTER JOIN on-expressions's first leftside needs to use an alias that is already defined, '%s' is not." % (alias,))
            self.outer_join_alias = alias
        elif self.outer_join_leftside != leftside:
            raise ValueError(
                "All OUTER JOIN on-expressions need to use the same initial leftside, but '%s' is different from previously used '%s'" % (leftside, self.outer_join_leftside))

        self.outers.add( (tblalias, onexpr) )

    def where(self, cond):
        if cond not in self.conditions:
            self.conditions.add(cond)

    def group(self, *groups):
        self.groups += groups

    def having(self, *havings):
        self.havings += havings

    def order(self, *orders):
        self.orders += orders

    def var(self, value):
        if self.master_query:
            return self.master_query.var(value)
        else:
            varname = "var%d" % (self.varid,)
            self.varid += 1
            self.values[varname] = value
            return self.dbvar(varname)

    def limit(self, count):
        self.limit = count

    def query(self):
        q = self.store_prefix or ""
        q += " SELECT " + ",".join(self.selects)

        tbls, last = [], []
        for t in self.tables:
            if self._alias(t) == self.outer_join_alias:
                last = [t]
            else:
                tbls.append(t)

        q += " FROM " + ",".join(tbls + last)
        for (a, x) in self.outers:
            q += " LEFT OUTER JOIN %s ON (%s)" % (a, x)
        for (onexpr, subq) in self.subqueries:
            self.where(onexpr + " IN (" + subq.query() + ")")
        if self.conditions:
            q += " WHERE " + " AND ".join(list(self.conditions))
        if self.groups:
            q += " GROUP BY " + ", ".join(list(self.groups))
        if self.havings:
            q += " HAVING " + " AND ".join(list(self.havings))
        if self.limit:
            q += " " + self.dblimit(self.limit)
        return q

    def run(self):
        qstr = self.query()
        if qstr[:7].lower() == "insert ":
            return self.link.put(qstr, **self.values)
        else:
            return self.link.get(qstr, **self.values)

    def dbvar(self, name):
        raise NotImplementedError()

    def dblimit(self, limit):
        return ""


class DatabaseLink(object):
    """A database link, which simplifies database calls by giving the
    .get(), .put() and .insert() methods. Hides the 'cursor' concept
    entirely, which is OK for most usages.

    Subclasses implement .insert() (where some databases have native
    ways of getting the last inserted id), set .iterator_class if needed,
    and override .exception() to convert database-specific errors to
    local errors.

    Subclasses also implement .convert() to convert (if needed) :abcde
    variable references into native format.
    """
    iterator_class = DatabaseIterator
    query_class = DynamicQuery

    def __init__(self, database, raw_link):
        self.database = database
        self.logger = self.database.logger
        self.link = raw_link
        self.intrans = False
        self.open = True

    def dynamic_query(self):
        return self.query_class(self)

    def close(self):
        self.open = False
        self.link.close()

    def exception(self, inner, query, args):
        self.logger.error("Unhandled error: %s" % (inner,))
        raise inner

    def iterator(self, curs):
        return self.iterator_class(curs)

    def convert(self, query, values):
        return query, values

    def execute(self, curs, query, values):
        raise NotImplementedError()

    def get_all(self, query, **kwargs):
        """ Executes the query and returns the result as a list instead of an iterator.

            This is needed when looping over a result and the loop body is doing writes
            to the database.
        """
        return list(self._get(query, **kwargs).fetchall())

    def get(self, query, **kwargs):
        curs = self._get(query, **kwargs)
        return curs.fetchall()

    def get_iterator(self, query, **kwargs):
        curs = self._get(query, **kwargs)
        return self.iterator(curs)

    def _get(self, query, **kwargs):
        """ Beware! This method returns a cursor, not the result"""
        if not self.open:
            raise LinkClosedError()

        if self.database.debug:
            self.logger.debug("%s %s" % (id(self), "QUERY: " + query))
            self.logger.debug("%s %s" % (id(self), "ARGS: %s" % str(kwargs)))

        curs = self.link.cursor()
        try:
            try:
                if isinstance(query, DynamicQuery):
                    q, v = self.convert(query.query(), query.values)
                else:
                    q, v = self.convert(query, kwargs)

                self.execute(curs, q, v)
                return curs
            except Exception as e:
                # print "ERROR", e
                # print "ERROR ARGUMENTS", e.args
                self.exception(e, q, v)
        finally:
            pass
            #curs.close()

    def get_value(self, query, **kwargs):
        ((val,),) = self.get(query, **kwargs)
        return val

    def put(self, query, **kwargs):
        if not self.open:
            raise LinkClosedError()

        if self.database.debug:
            self.logger.debug("%s %s" % (id(self), "QUERY: " + query))
            self.logger.debug("%s %s" % (id(self), "ARGS: %s" % str(kwargs)))

        curs = self.link.cursor()
        try:
            try:
                if isinstance(query, DynamicQuery):
                    v = query.values()
                    q, v = self.convert(query.query(), query.values())
                else:
                    v = kwargs
                    q, v = self.convert(query, kwargs)
                self.execute(curs, q, v)
                if self.database.debug:
                    self.logger.debug("%s -> %s" % (id(self), str(curs.rowcount)))
                return curs.rowcount
            except Exception as e:
                self.exception(e, query, v)
        finally:
            curs.close()

    def insert(self, insert_col, query, **kwargs):
        raise NotImplementedError()

    def begin(self):
        if not self.open:
            raise LinkClosedError()

        if self.database.debug:
            self.logger.debug("%s BEGIN" % id(self))

        self.link.begin()
        self.intrans = True

    def commit(self):
        if not self.open:
            raise LinkClosedError()

        if self.database.debug:
            self.logger.debug("%s COMMIT" % id(self))

        self.link.commit()
        self.intrans = False

    def rollback(self):
        if not self.open:
            raise LinkClosedError()

        if self.database.debug:
            self.logger.debug("%s ROLLBACK" % id(self))

        self.link.rollback()
        self.intrans = False


class Database(object):
    """Represents a database - with methods to handle DatabaseLink.

    Subclasses implement .init() (with database-specific keyword
    initialization options), .get_link() and .return_link() (which
    may be a null operation if the database is quick to create links).
    """
    link_class = DatabaseLink

    def __init__(self, server, **args):
        self.server = server
        self.logger = server.logger
        self.lock = threading.Lock()
        self.init(**args)
        self.debug = server.config("DEBUG_SQL", default=False)
        self.dynamic_table_specs = {}  # Dict keyed by manager type containng table specs for that manager

    def specify_tables(self, cls, tables):
        """ Specify a list of table specifications for a manager"""
        self.dynamic_table_specs[cls] = tables

    def get_tables_spec(self, cls):
        """ Return a list of table specifications for a manager, if present"""
        if cls in self.dynamic_table_specs:
            return self.dynamic_table_specs[cls]
        return None

    def get_link(self):
        raise NotImplementedError()

    def return_link(self, link):
        raise NotImplementedError()

    def query(self):
        return self.query_class()

    def table_exists(self, table_spec):
        raise NotImplementedError()

    def add_tables_from_dynamic_query(self, dq, cls):
        if not isinstance(dq, DynamicQuery):
            raise ValueError("dq argument is not a DynamicQuery")
        if cls in self.dynamic_table_specs:
            return
        table_list = []
        for t in dq.tables:
            if " " in t:
                t, _alias = t.split()
            dt = DBTable(t, desc="Dynamically created table")
            for sel in dq.selects:
                if "." in sel:
                    tbl, col = sel.split(".")
                else:
                    if len(dq.tables) < 1:
                        raise ProgrammingError("No tables defined in base query for selects in %s" % dq)
                    if len(dq.tables) > 1:
                        raise ProgrammingError("Selects specified ambigously in base query of %s" % dq)
                    tbl = list(dq.tables)[0]
                    col = sel
                if tbl in dq.table_aliases:
                    tbl = dq.table_aliases[tbl]
                if " " in tbl:
                    tbl, _alias = tbl.split()
                if tbl == t:
                    dcol = DBColumn(col)
                    dt.add_column(dcol)
            table_list.append(dt)
        self.specify_tables(cls, table_list)

###
# Oracle specifics
###


class OracleDynamicQuery(DynamicQuery):

    def dbvar(self, name):
        return ":" + name

    def limit(self, limit):
        self.where("ROWNUM < " + self.var(limit))
        DynamicQuery.limit(self, limit)


class OracleIterator(DatabaseIterator):

    def convert(self, row):
        ret = None
        for idx in range(len(row)):
            c = row[idx]
            if isinstance(c, cx_Oracle.BLOB) or isinstance(c, cx_Oracle.CLOB) or isinstance(c, cx_Oracle.NCLOB) or isinstance(c, cx_Oracle.LOB):  # @UndefinedVariable
                if not ret:
                    ret = list(row)
                ret[idx] = c.read()

        return ret or row


class OracleLink(DatabaseLink):
    iterator_class = OracleIterator
    query_class = OracleDynamicQuery

    def exception(self, inner, query, args):
        if self.database.server.config("DEBUG_SQL", default=False):
            self.logger.debug("ERROR IN QUERY: " + query)
            self.logger.debug("WITH ARGUMENTS: " + args)

        if isinstance(inner, cx_Oracle.DatabaseError):  # @UndefinedVariable
            err = inner.args[0]
            if isinstance(err, str):
                raise

            if err.code == 904:
                idf = err.message.split('"')[1]
                raise InvalidIdentifierError(idf, inner=inner)
            if err.code == 942:
                raise InvalidTableError("?", inner=inner)
            if err.code == 1:
                const = err.message.split("(")[1].split(")")[0]
                raise IntegrityError(const, inner=inner)
            self.logger.debug("CODE:" + err.code)
            self.logger.debug("CONTEXT:" + err.context)
            self.logger.debug("MESSAGE:" + err.message.strip())
            self.logger.debug("OFFSET:" + err.offset)
        raise

    def execute(self, curs, query, values):
        curs.execute(query, **values)

    def insert(self, insert_col, query, **kwargs):
        if not self.open:
            raise LinkClosedError()

        if self.database.debug:
            self.logger.debug("%s QUERY: %s" % (id(self), query))
            self.logger.debug("%s ARGS: %s" % (id(self), kwargs))

        curs = self.link.cursor()
        try:
            try:
                if isinstance(query, DynamicQuery):
                    q, kw = self.convert(query.query(), query.values())
                else:
                    q, kw = self.convert(query, kwargs)

                var = curs.var(cx_Oracle.NUMBER)  # @UndefinedVariable
                kw["last_insert_id"] = var
                q += " RETURNING %s INTO :last_insert_id" % (insert_col,)
                curs.execute(q, **kw)
                return var.getvalue()
            except Exception as e:
                self.exception(e, q, kw)
        finally:
            curs.close()


class OracleDatabase(Database):
    link_class = OracleLink

    def init(self, user=None, password=None, database=None):
        self.user = user or self.server.config("DB_USER")
        self.password = password or self.server.config("DB_PASSWORD")
        self.database = database or self.server.config("DB_DATABASE")
        self.pool = []

    def check_rpcc_tables(self):
        lnk = self.get_link()
        default_tables.check_default_oracle_tables(lnk)
        self.return_link(lnk)

    def get_link(self):
        with self.lock:
            while self.pool:
                link = self.pool.pop(0)
                try:
                    dummy = link.get("SELECT 1 FROM DUAL")
                    return link
                except:
                    pass

            try:
                raw_link = cx_Oracle.connect(self.user, self.password, self.database, threaded=True)  # @UndefinedVariable

                # Disable the buggy "cardinality feedback" misfeature.
                raw_link.cursor().execute('alter session set "_optimizer_use_feedback" = false')

                return self.link_class(self, raw_link)
            except:
                raise exterror.ExtRuntimeError("Database has gone away")

    def return_link(self, link):
        with self.lock:
            if link.intrans:
                link.rollback()
            self.pool.append(link)


###
# MySQL specifics.
###
class MySQLDynamicQuery(DynamicQuery):

    def dbvar(self, name):
        #return "%(" + name + ")s"
        return ":" + name

    def dblimit(self, limit):
        return "LIMIT %d" % (limit,)


class MySQLIterator(DatabaseIterator):

    def convert(self, row):
        # TODO: Check if any data types need special treatment like in OracleIterator
        return row


class MySQLLink(DatabaseLink):

    iterator_class = MySQLIterator
    query_class = MySQLDynamicQuery

    def __init__(self, *args, **kwargs):
        DatabaseLink.__init__(self, *args, **kwargs)
        self.re = re.compile(":([a-z0-9_]+)")

    def convert(self, query, values):
        return self.re.sub("%(\\1)s", query), values

    def execute(self, curs, query, values):
        try:
            curs.execute(query, values)
        except Exception as e:
            self.logger.error("DBEXCEPTION: %s %s" % (str(e), str(type(e))))
            self.logger.error("QUERY= " + query)
            raise

    def insert(self, dummy, query, **kwargs):
        if not self.open:
            raise LinkClosedError()

        if self.database.debug:
            self.logger.debug("%s QUERY: %s" % (id(self), query))
            self.logger.debug("%s ARGS: %s" % (id(self), kwargs))

        curs = self.link.cursor()
        try:
            try:
                if isinstance(query, DynamicQuery):
                    q, v = self.convert(query.query(), query.values())
                else:
                    q, v = self.convert(query, kwargs)
                curs.execute(q, v)
                return curs.lastrowid
            except Exception as e:
                self.logger.error("DBEXCEPTION: %s %s" % (str(e), str(type(e))))
                self.exception(e, q, v)
        finally:
            curs.close()

    def exception(self, inner, query, args):
        if self.database.server.config("DEBUG_SQL", default=False):
            self.logger.error("ERROR IN QUERY: " + query)
            self.logger.error("WITH ARGUMENTS: " + str(args))
            self.logger.error("INNER ERROR: " + str(inner))
        if isinstance(inner, mysql.connector.errors.IntegrityError):
            errno = inner.errno
            message = inner.msg
            if errno == 1452:
                message = "Cannot add or update a child row: a foreign key constraint fails"
            raise IntegrityError(message, inner=inner)

#         if isinstance(inner, cx_Oracle.DatabaseError):
#             err = inner.args[0]
#             if isinstance(err, str):
#                 raise
#
#             if err.code == 904:
#                 idf = err.message.split('"')[1]
#                 raise InvalidIdentifierError(idf, inner=inner)
#             if err.code == 942:
#                 raise InvalidTableError("?", inner=inner)
#             if err.code == 1:
#                 const = err.message.split("(")[1].split(")")[0]
#                 raise IntegrityError(const, inner=inner)
#             print "CODE:", err.code
#             print "CONTEXT:", err.context
#             print "MESSAGE:", err.message.strip()
#             print "OFFSET:", err.offset
        raise


class MySQLDatabase(Database):
    query_class = MySQLDynamicQuery
    link_class = MySQLLink

    def init(self, user=None, password=None, database=None, host=None, port=None, socket=None):
        user = user or self.server.config("DB_USER")
        password = password or self.server.config("DB_PASSWORD")
        database = database or self.server.config("DB_DATABASE")
        host = host or self.server.config("DB_HOST")
        port = port or self.server.config("DB_PORT")
        socket = port or self.server.config("DB_SOCKET")

        if mysql.connector.__version_info__[0] > 1:
            raise exterror.ExtRuntimeError("The server is not supporting the use of MySQL connector version 2 and above")

        self.connect_args = {"user": user, "password": password, "db": database}
        if host:
            self.connect_args["host"] = host
            if port:
                self.connect_args["port"] = int(port)
        elif socket:
            self.connect_args["unix_socket"] = socket
        else:
            raise ValueError()

    def get_link(self):
        try:
            raw_link = mysql.connector.connect(**self.connect_args)
            return self.link_class(self, raw_link)
        except:
            raise
            raise exterror.ExtRuntimeError("Database has gone away")

    def return_link(self, link):
        if link.intrans:
            link.rollback()
        link.close()

    def check_rpcc_tables_old(self):
        lnk = self.get_link()
        default_tables.check_default_mysql_tables(lnk)
        self.return_link(lnk)

    def check_rpcc_tables(self, tables_spec=default_tables._dig_tables, fix=False):
        lnk = self.get_link()
        for table_spec in tables_spec:
            if not self.table_check(table_spec, lnk, fix=fix):
                raise ValueError("Database Tables validation failed")
        self.return_link(lnk)

    def col_sql_type(self, col):
        if col.value_type == VType.integer:
            return "INT(11) "
        if col.value_type == VType.string:
            return "VARCHAR(256) "
        if col.value_type == VType.datetime:
            return "DATETIME "
        if col.value_type == VType.float:
            return "DOUBLE "
        if col.value_type == VType.blob:
            return "BLOB "
        if not col.value_type:
            raise ValueError("MySQL database column has no type")

    def table_check(self, table_spec, link, fix=False):
        q_check = "SELECT " + \
                  ", ".join(table_spec.column_names()) + \
                  " FROM " + table_spec.name + " LIMIT 1"

        while(True):
            try:
                dummy = list(link.get(q_check))
                return True
            except InvalidIdentifierError as e:
                if fix:
                    for col in table_spec.columns:
                        try:
                            q_addcol = "ALTER TABLE %s ADD COLUMN %s TYPE " % (table_spec.name, col.name)
                            q_addcol += self.col_sql_type(col)

                            # TODO: Column type specification not done
                            link.put(q_addcol)
                        except:
                            self.logger.critical("COLUMN %s MISSING FROM TABLE %s - FIX MANUALLY" %
                                                 (col, table_spec.name))
                            return False
                    continue
                else:
                    self.logger.critical("COLUMN %s MISSING FROM TABLE %s - FIX MANUALLY" % (e.identifier, table_spec.name))
                    return False

            except InvalidTableError as e:
                if fix:
                    try:
                        q_create = "CREATE TABLE %s( " % (table_spec.name)
                        colsqls = []
                        for col in table_spec.columns:
                            colsql = col.name + " "
                            colsql += self.col_sql_type(col) + " "
                            if col.primary:
                                colsql += "PRIMARY KEY NOT NULL"
                            else:
                                if col.unique:
                                    colsql += "UNIQUE "
                                if col.not_null:
                                    colsql += "NOT NULL "
                            colsqls.append(colsql)
                        q_create += ", ".join(colsqls) + ")"

                        link.put(q_create)

                    except:
                        self.logger.critical("TABLE %s MISSING FROM DATABASE - FIX MANUALLY" % (table_spec.name,))
                        return False
                    continue
                else:
                    self.logger.critical("TABLE %s MISSING FROM DATABASE - FIX MANUALLY" % (table_spec.name,))
                    return False
            except Exception as e:
                raise


class SQLiteIterator(DatabaseIterator):

    def convert(self, row):
        # TODO: Check if any data types need special treatment like in OracleIterator
        return row


class SQLiteDynamicQuery(DynamicQuery):

    def dbvar(self, name):
        return ":" + name

    def dblimit(self, limit):
        return "LIMIT %d" % (limit,)


class SQLiteLink(DatabaseLink):

    query_class = SQLiteDynamicQuery

    def __init__(self, *args, **kwargs):
        DatabaseLink.__init__(self, *args, **kwargs)
        self.re = re.compile(":([a-z0-9_]+)")

    def iterator(self, curs):
        return curs

    def convert(self, query, values):
        values_usage = {}
        value_list = []
        try:
            for m in self.re.finditer(query):
                key = m.group(0)[1:]
                value_list.append(values[key])
                values_usage[key] = True
        except KeyError:
            raise ProgrammingError("No value for query parameter %s" % key)
        if len(values_usage) != len(values):
            raise ProgrammingError("One or more values unused in query")
        return self.re.sub("?", query), value_list

    def execute(self, curs, query, values):
        curs.execute(query, values)

    def insert(self, dummy, query, **kwargs):
        if not self.open:
            raise LinkClosedError()

        if self.database.debug:
            self.logger.debug("%s QUERY: %s" % (id(self), query))
            self.logger.debug("%s ARGS: %s" % (id(self), kwargs))

        curs = self.link.cursor()
        try:
            try:
                if isinstance(query, DynamicQuery):
                    raw_values = query.values
                    q, v = self.convert(query.query(), query.values)
                else:
                    raw_values = kwargs
                    q, v = self.convert(query, kwargs)
                curs.execute(q, v)
                return curs.lastrowid
            except Exception as e:
                self.logger.error("DBEXCEPTION: %s %s" % (str(e), str(type(e))))
                self.exception(e, q, raw_values)
        finally:
            curs.close()

    def exception(self, inner, query, args):
        if self.database.server.config("DEBUG_SQL", default=False):
            self.logger.debug("ERROR IN QUERY: " + query)
            self.logger.debug("WITH ARGUMENTS: " + str(args))
            self.logger.debug("INNER ERROR: " + str(inner))
        if isinstance(inner, sqlite3.OperationalError):
            message = inner.message
            if ":" in message:
                (msg, param) = message.split(":")
            else:
                msg = message
            if msg == "no such table":
                raise InvalidTableError(param, inner=inner)
            raise IntegrityError(message, inner=inner)
        if isinstance(inner, sqlite3.IntegrityError):
            message = inner.message
            raise IntegrityError(message, inner=inner)
        raise


class SQLiteDatabase(Database):
    query_class = SQLiteDynamicQuery
    link_class = SQLiteLink

    def init(self, database=None):
        if not database:
            database = "rpcc_scratch_database"
        self.connect_args = {"database": database}

    def check_rpcc_tables_old(self):
        lnk = self.get_link()
        default_tables.check_default_mysql_tables(lnk)
        self.return_link(lnk)

    def get_link(self):
        try:
            raw_link = sqlite3.connect(**self.connect_args)
            return self.link_class(self, raw_link)
        except:
            raise
            raise exterror.ExtRuntimeError("Database has gone away")

    def return_link(self, link):
        if link.intrans:
            link.rollback()
        link.close()

    def check_rpcc_tables(self, tables_spec=default_tables._dig_tables, fix=False):
        lnk = self.get_link()
        for table_spec in tables_spec:
            if not self.table_check(table_spec, lnk, fix=fix):
                raise ValueError("Database Tables validation failed")
        self.return_link(lnk)

    def col_sql_type(self, col):
        if col.value_type == VType.integer:
            return "INTEGER "
        if col.value_type == VType.string:
            return "TEXT "
        if col.value_type == VType.datetime:
            return "NUMERIC "
        if col.value_type == VType.float:
            return "REAL "
        if col.value_type == VType.blob:
            return "NONE "
        if not col.value_type:
            return "NONE "

    def table_check(self, table_spec, link, fix=False):
        q_check = "SELECT " + \
                  ", ".join(table_spec.column_names()) + \
                  " FROM " + table_spec.name + " LIMIT 1"

        while(True):
            try:
                dummy = list(link.get(q_check))
                return True
            except InvalidIdentifierError as e:
                if fix:
                    for col in table_spec.columns:
                        try:
                            q_addcol = "ALTER TABLE %s ADD COLUMN %s TYPE " % (table_spec.name, col.name)
                            q_addcol += self.col_sql_type(col)

                            # TODO: Column type specification not done
                            link.put(q_addcol)
                        except:
                            self.logger.critical("COLUMN %s MISSING FROM TABLE %s - FIX MANUALLY" %
                                                 (col, table_spec.name))
                            return False
                    continue
                else:
                    self.logger.critical("COLUMN %s MISSING FROM TABLE %s - FIX MANUALLY" %
                                         (e.identifier, table_spec.name))
                    return False

            except InvalidTableError as e:
                if fix:
                    try:
                        q_create = "CREATE TABLE %s( " % (table_spec.name)
                        colsqls = []
                        for col in table_spec.columns:
                            colsql = col.name + " "
                            colsql += self.col_sql_type(col) + " "
                            if col.primary:
                                colsql += "PRIMARY KEY NOT NULL"
                            else:
                                if col.unique:
                                    colsql += "UNIQUE "
                                if col.not_null:
                                    colsql += "NOT NULL "
                            colsqls.append(colsql)
                        q_create += ", ".join(colsqls) + ")"

                        link.put(q_create)

                    except:
                        self.logger.critical("TABLE %s MISSING FROM DATABASE - FIX MANUALLY" % (table_spec.name,))
                        return False
                    continue
                else:
                    self.logger.critical("TABLE %s MISSING FROM DATABASE - FIX MANUALLY" % (table_spec.name,))
                    return False
            except Exception as e:
                raise


if __name__ == '__main__':
    if False:
        db = OracleDatabase()

        lnk1 = db.get_link()
        lnk2 = db.get_link()
        assert lnk1 is not lnk2

        # Check conversions
        for vfrom, vto in lnk1.get("SELECT valid_from, valid_to FROM group_members WHERE valid_to < '2100-01-01' AND ROWNUM < 3"):
            assert isinstance(vfrom, datetime.datetime)
            assert isinstance(vto, datetime.datetime)

        for length, text in lnk2.get("SELECT LENGTH(text_sv), text_sv FROM agreement"):
            assert isinstance(text, str) or isinstance(text, unicode)
            assert len(text) == length

        # If we return a link and fetch a new one, we should get the same
        # link.
        db.return_link(lnk1)
        lnk3 = db.get_link()
        assert lnk1 is lnk3

        # If we return a link and then mess it up so that it won't work,
        # the code to fetch a link should detect this and give us a
        # fresh link instead.

        db.return_link(lnk3)
        lnk3.link = None
        lnk4 = db.get_link()
        assert lnk4 is not lnk3

    if True:
        db = MySQLDatabase()

        # We should get different links.
        lnk1 = db.get_link()
        lnk2 = db.get_link()
        assert lnk1 is not lnk2

        # In fact, we should ALWAYS get different links.
        db.return_link(lnk1)
        lnk3 = db.get_link()
        assert lnk1 is not lnk3

        checked = False
        for length, text in lnk3.get("SELECT length(fullproposition), fullproposition FROM lopp WHERE fullproposition IS NOT NULL LIMIT 10"):
            assert len(text) == length
            assert isinstance(text, str) or isinstance(text, unicode)
            checked = True

        if not checked:
            raise ValueError("Test failed to return any rows")
