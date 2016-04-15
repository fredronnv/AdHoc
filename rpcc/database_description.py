#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-


# Classes for describing databases in a way independent of database engines
from enum import Enum


class VType(Enum):
    """ Enumeration of column types """
    integer = 1
    string = 2
    datetime = 3
    float = 4
    blob = 5
    timestamp = 6


class Action(Enum):
    """ Enumeration of action types for foreign keys"""
    cascade = 1
    set_null = 2
    no_action = 3
    restrict = 4


class KeyType(Enum):
    """ Key types"""
    primary = 1
    unique = 2
    index = 3
    fulltext = 4
    candidate = 5
    alternate = 6
    foreign = 7


class DBFKey(object):

    def __init__(self, target, on_delete=None, on_update=None):
        self.target = target
        self.on_delete = on_delete
        self.on_update = on_update


class DBKey(object):

    def __init__(self, name, key_type, columns, target=None):
        if not name:
            raise ValueError("Name for DBKey must be specified")

        if type(name) is not str:
            raise TypeError("DBKey name must be a string")

        if key_type and key_type is not KeyType.foreign and target:
            raise TypeError("Key targets can only be specified for foreign keys, key named %s" % name)

        if type(key_type) is not KeyType:
            raise TypeError("Key types must be specified using a KeyType enum")

        if type(columns) is not list:
            columns = [columns]

        if len(columns) < 1:
            raise ValueError("Too few columns specified for key named %s" % name)

        self.name = name
        self.key_type = key_type
        self.columns = columns
        self.target = target


class EngineType(Enum):
    """ Enumeration of database table engine types"""
    temporary = 1
    memory = 2
    transactional = 3
    big = 4


class DBColumn(object):
    """ Column description class"""

    def __init__(self, name, value_type=None, size=None, autoincrement=None, index=None, primary=False, unique=False, not_null=False, autoupdate=None, fkey=None, default=None):
        if not name:
            raise ValueError("Name for columns must be specified")

        if type(name) is not str:
            raise TypeError("Column  name must be a string")

        self.name = name

        if value_type and type(value_type) is not VType:
            raise TypeError("Bad type for database table column")
        self.value_type = value_type
        self.size = size

        if value_type and value_type is not VType.integer and autoincrement:
            raise TypeError("Autoincrement is only for integer type columns")
        self.autoincrement = autoincrement

        if value_type and value_type is not VType.timestamp and autoupdate:
            raise TypeError("Autoupdate is only for timestamp type columns")
        self.autoupdate = autoupdate

        self.not_null = not_null

        if default:
            self.default = default
        else:
            if not self.not_null:
                self.default = "NULL"
            else:
                self.default = None

        self.index = index
        self.primary = primary
        self.unique = unique
        self.owning_table = None
        self.fkey = fkey

    def set_value_type(self, value_type):
        if type(value_type) is not VType:
            raise TypeError("Bad type for database table column")
        if value_type is not VType.integer and self.autoincrement:
            raise TypeError("Cannot set table value_type to anything but integer because autioncrement is already set")
        self.value_type = value_type

    def set_primary(self):
        self.primary = True

    def unset_primary(self):
        self.primary = False

    def __repr__(self):
        s = "\nDBColumn: "
        s += "\n name=" + str(self.name)
        s += "\n owning_table=" + str(self.owning_table)
        s += "\n value_type=" + str(self.value_type)
        s += "\n size=" + str(self.size)
        s += "\n autoincrement=" + str(self.autoincrement)
        s += "\n index=" + str(self.index)
        s += "\n primary=" + str(self.primary)
        s += "\n unique=" + str(self.unique)
        s += "\n not_null=" + str(self.not_null)
        return s


class DBTable(object):
    """Table description class"""

    def __init__(self, name, desc=None, engine=None, collation=None, columns=None, keys=None, oids=None):
        self.name = name
        self.desc = desc
        self.engine = engine
        self.collation = collation
        self.primary_col = None
        self.columns = []
        if columns:
            for c in columns:
                self.add_column(c)
        self.keys = []
        if keys:
            self.keys = keys
        self.oids = oids

    def add_column(self, column):
        if type(column) is DBColumn:
            if self.primary_col and column.primary:
                raise ValueError("Data table already has a column specified as primary")
            if column.primary:
                self.primary_col = column
            self.columns.append(column)
            column.owning_table = self
        else:
            raise TypeError("Database column is not of type DBColumn")

    def column_names(self):
        return [x.name for x in self.columns]

    def __str__(self):
        s = "\nDBTable: "
        s += "\n name=" + str(self.name)
        s += "\n description=" + str(self.desc)
        s += "\n engine=" + str(self.engine)
        s += "\n collation=" + str(self.collation)
        s += "\n primary_col=" + str(self.primary_col)
        s += "\n columns=" + str(self.columns)
        return s


class DatabaseError(Exception):

    def __init__(self, msg, inner=None):
        Exception.__init__(self, msg)
        if inner:
            self.inner = inner


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
