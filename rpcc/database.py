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

try:
    import cx_Oracle
except:
    pass

try:
    import mysql.connector
    #from mysql.connector.conversion import MySQLConverter
    #from mysql.connector.cursor import MySQLCursor
except:
    pass


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

    def __init__(self, link, master_query=None):
        self.link = link
        self.master_query = master_query
        if not master_query:
            self.varid = 0

        self.store_prefix = ""
        self.selects = []
        self.tables = set()
        self.conditions = set()
        self.subqueries = []
        self.groups = []
        self.havings = []
        self.orders = []
        self.values = {}
        self.limit = None

    def subquery(self, onexpr):
        """Return a DynamicQuery which uses the same database values and
        is executed as a subquery (implicit condition: <onexpr> IN (<subq string>))
        """
        subq = self.__class__(self.link, self)
        self.subqueries.append((onexpr, subq))
        return subq

    def store_result(self, expr):
        self.store_prefix = expr

    def select(self, *sels):
        self.selects += sels

    def get_select_at(self, idx):
        return self.selects[idx]

    def table(self, *tbls):
        for tbl in tbls:
            if tbl not in self.tables:
                self.tables.add(tbl)

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
        q += " FROM " + ",".join(self.tables)
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
        self.link = raw_link
        self.intrans = False
        self.open = True

    def dynamic_query(self):
        return self.query_class(self)

    def close(self):
        self.open = False
        self.link.close()

    def exception(self, inner):
        print "Unhandled error: %s" % (inner,)
        raise inner

    def iterator(self, curs):
        return self.iterator_class(curs)

    def convert(self, query):
        return query

    def execute(self, curs, query, values):
        raise NotImplementedError()

    def get(self, query, **kwargs):
        if not self.open:
            raise LinkClosedError()

        curs = self.link.cursor()
        try:
            try:
                if isinstance(query, DynamicQuery):
                    q = query.query()
                    v = query.values
                else:
                    q = self.convert(query)
                    v = kwargs

                self.execute(curs, q, v)
                return self.iterator(curs)
            except Exception as e:
                print "ERROR", e
                print "ERROR ARGUMENTS", e.args
                print "IN QUERY:", q
                print "WITH ARGUMENTS:", v
                self.exception(e)
        finally:
            pass
            #curs.close()

    def get_value(self, query, **kwargs):
        ((val,),) = self.get(query, **kwargs)
        return val

    def put(self, query, **kwargs):
        if not self.open:
            raise LinkClosedError()

        curs = self.link.cursor()
        try:
            try:
                if isinstance(query, DynamicQuery):
                    q = query.query()
                    v = query.values
                else:
                    q = self.convert(query)
                    v = kwargs
                self.execute(curs, q, v)
                return curs.rowcount
            except Exception as e:
                print "ERROR IN QUERY:", q
                print "WITH ARGUMENTS:", v
                self.exception(e)
        finally:
            curs.close()

    def insert(self, insert_col, query, **kwargs):
        raise NotImplementedError()

    def begin(self):
        if not self.open:
            raise LinkClosedError()

        self.link.begin()
        self.intrans = True

    def commit(self):
        if not self.open:
            raise LinkClosedError()

        self.link.commit()
        self.intrans = False

    def rollback(self):
        if not self.open:
            raise LinkClosedError()

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
        self.lock = threading.Lock()
        self.init(**args)

    def get_link(self):
        raise NotImplementedError()

    def return_link(self, link):
        raise NotImplementedError()

    def query(self):
        return self.query_class()


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
            if isinstance(c, cx_Oracle.BLOB) or \
                    isinstance(c, cx_Oracle.CLOB) or \
                    isinstance(c, cx_Oracle.NCLOB) or \
                    isinstance(c, cx_Oracle.LOB):
                if not ret:
                    ret = list(row)
                ret[idx] = c.read()

        return ret or row


class OracleLink(DatabaseLink):
    iterator_class = OracleIterator
    query_class = OracleDynamicQuery

    def exception(self, inner):
        if isinstance(inner, cx_Oracle.DatabaseError):
            err = inner.args[0]
            if err.code == 904:
                idf = err.message.split('"')[1]
                raise InvalidIdentifierError(idf, inner=inner)
            if err.code == 942:
                raise InvalidTableError("?", inner=inner)
            print "CODE:", err.code
            print "CONTEXT:", err.context
            print "MESSAGE:", err.message
            print "OFFSET:", err.offset
        raise

    def execute(self, curs, query, values):
        curs.execute(query, **values)

    def insert(self, insert_col, query, **kwargs):
        if not self.open:
            raise LinkClosedError()

        curs = self.link.cursor()
        try:
            try:
                if isinstance(query, DynamicQuery):
                    q = query.query()
                    kw = query.values
                else:
                    q = self.convert(query)
                    kw = kwargs

                var = curs.var(cx_Oracle.NUMBER)
                kw["last_insert_id"] = var
                q += " RETURNING %s INTO :last_insert_id" % (insert_col,)
                curs.execute(q, **kw)
                return var.getvalue()
            except Exception as e:
                self.exception(e)
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

            raw_link = cx_Oracle.connect(self.user, self.password, self.database, threaded=True)

            # Disable the buggy "cardinality feedback" misfeature.
            raw_link.cursor().execute('alter session set "_optimizer_use_feedback" = false')

            return self.link_class(self, raw_link)

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
        return "%(" + name + ")"

    def dblimit(self, limit):
        return "LIMIT %d" % (limit,)


class MySQLLink(DatabaseLink):
    def __init__(self, *args, **kwargs):
        DatabaseLink.__init__(self, *args, **kwargs)
        self.re = re.compile(":([a-z])")

    def convert(self, query):
        return self.re.sub("\\1", query)

    def execute(self, curs, query, values):
        curs.execute(query, values)

    def insert(self, dummy, query, **kwargs):
        if not self.open:
            raise LinkClosedError()

        curs = self.link.cursor()
        try:
            try:
                if isinstance(query, DynamicQuery):
                    curs.execute(query.query(), query.values)
                else:
                    curs.execute(self.convert(query), kwargs)
                return curs.lastrowid
            except Exception as e:
                self.exception(e)
        finally:
            curs.close()


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
        raw_link = mysql.connector.connect(**self.connect_args)
        return self.link_class(self, raw_link)

    def return_link(self, link):
        if link.intrans:
            link.rollback()
        link.close()

    def check_rpcc_tables(self):
        lnk = self.get_link()
        default_tables.check_default_mysql_tables(lnk)
        self.return_link(lnk)


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
