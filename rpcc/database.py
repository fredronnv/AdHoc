#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

"""
Wrapper around Python DB-API 2.0 databases.

A Database subclass implements all functionality specific to a database
engine.

.get_link() gets a DB link as specified below.

.return_link() returns a DB link. It might be reused if the database engine
    is slow to create new links.

.query() returns a Query subclass instance specific to the engine. The
    Query objects are used to incrementally build queries.


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

import os
import sys
import threading
import datetime
import re

try:
    import cx_Oracle
except:
    pass

try:
    import MySQLdb
except:
    pass


class DatabaseError(Exception):
    pass


class LinkClosedError(DatabaseError):
    pass


class IntegrityError(DatabaseError):
    pass


class ProgrammingError(DatabaseError):
    pass


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
        except StopIteration, GeneratorExit:
            self.curs.close()
            raise


class Query(object):
    """Query objects that allow incrementally built queries, as well
    as abstracting common database-specific things like limited queries
    and input variables (which the Python DB-API tragically didn't
    specify a standard for).

    Intended use:

    q = Query()
    q.select('p.ucid', 'a.ucid')
    q.table('person p')
    q.table('account a')
    q.where('p.ucid = a.ucid_owner')
    q.where('a.ucid =' + self.var(account.ucid))
    q.limit(100)
    """

    def __init__(self, *selects):
        self.selects = selects or []
        self.tables = []
        self.conditions = []
        self.groups = []
        self.havings = []
        self.orders = []
        self.values = {}
        self.limit = None
        self.varid = 0

    def select(self, sel):
        self.selects.append(sel)

    def table(self, *tbls):
        self.tables += tbls

    def where(self, *conds):
        self.conditions += conds

    def group(self, *groups):
        self.groups += groups

    def having(self, *havings):
        self.havings += havings

    def order(self, *orders):
        self.orders += orders

    def var(self, value):
        varname = "var%d" % (self.varid,)
        self.varid += 1
        self.values[varname] = value
        return dbvar(varname)

    def limit(self, count):
        self.limit = count

    def query(self, curs):
        q = "SELECT " + self.select
        q += " FROM " + ",".join(self.tables)
        if self.conditions:
            q += "WHERE " + "AND ".join(self.conditions)
        if self.groups:
            q += "GROUP BY " + ", ".join(self.groups)
        if self.havings:
            q += "HAVING " + "AND ".join(self.havings)
        if self.limit:
            q += self.dblimit(self.limit)
        return q

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
    query_class = Query

    def __init__(self, database, raw_link):
        self.database = database
        self.link = raw_link
        self.intrans = False
        self.open = True

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

    def get(self, query, **kwargs):
        if not self.open:
            raise LinkClosedError()

        curs = self.link.cursor()
        try:
            try:
                if isinstance(query, Query):
                    curs.execute(query.query(), **query.values)
                else:
                    curs.execute(self.convert(query), **kwargs)
                return self.iterator(curs)
            except Exception as e:
                print "ERROR IN QUERY:", self.convert(query)
                print "WITH ARGUMENTS:", kwargs
                self.exception(e)
        finally:
            pass
            #curs.close()

    def put(self, query, **kwargs):
        if not self.open:
            raise LinkClosedError()

        curs = self.link.cursor()
        try:
            try:
                if isinstance(query, Query):
                    curs.execute(query.query(), **query.values)
                else:
                    curs.execute(self.convert(query), **kwargs)
                return curs.rowcount
            except Exception as e:
                print "ERROR IN QUERY:", self.convert(query)
                print "WITH ARGUMENTS:", kwargs
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
class OracleQuery(Query):
    def dbvar(self, name):
        return ":" + name

    def limit(self, limit):
        self.where("ROWNUM < " + self.var(limit))
        Query.limit(self, limit)


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
    query_class = OracleQuery

    def insert(self, insert_col, query, **kwargs):
        if not self.open:
            raise LinkClosedError()

        curs = self.link.cursor()
        try:
            try:
                if isinstance(query, Query):
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
class MySQLQuery(Query):
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

    def insert(self, dummy, query, **kwargs):
        if not self.open:
            raise LinkClosedError()

        curs = self.link.cursor()
        try:
            try:
                if isinstance(query, Query):
                    curs.execute(query.query(), **query.values)
                else:
                    curs.execute(self.convert(query), **kwargs)
                return curs.lastrowid
            except Exception as e:
                self.exception(e)
        finally:
            curs.close()


class MySQLDatabase(Database):
    query_class = MySQLQuery
    link_class = MySQLLink

    def init(self, user=None, password=None, database=None, host=None, port=None, socket=None):
        user = user or self.server.config("DB_USER")
        password = password or self.server.config("DB_PASSWORD")
        database = database or self.server.config("DB_DATABASE")
        host = host or self.server.config("DB_HOST", None)
        port = port or self.server.config("DB_PORT", None)
        socket = port or self.server.config("DB_SOCKET", None)

        self.connect_args = {"user": user, "passwd": password, "db": database}
        if host:
            self.connect_args["host"] = host
            if port:
                self.connect_args["port"] = int(port)
        elif socket:
            self.connect_args["unix_socket"] = socket
        else:
            raise ValueError()

    def get_link(self):
        raw_link = MySQLdb.connect(**self.connect_args)
        return self.link_class(self, raw_link)

    def return_link(self, link):
        if link.intrans:
            link.rollback()
        link.close()


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

