#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime

import model
import access
import database
import default_type
import default_error

class MutexVariable(object):
    type_field = None

    def __init__(self, mutex, name, varid, typ):
        self.function = mutex.function
        self.mutex = mutex
        self.db = mutex.db
        self.name = name
        self.varid = varid
        self.typ = typ
        if typ != self.type_field:
            raise TypeError()

    def clear(self):
        q = "DELETE FROM rpcc_mutex_var_val "
        q += "WHERE var=:var "
        self.db.put(q, var=self.varid)


class MutexString(MutexVariable):
    type_field = "S"

    def set_value(self, newval):
        q = "UPDATE rpcc_mutex_var_val "
        q += "  SET value=:val "
        q += "WHERE var=:var "
        affected = self.db.put(q, var=self.varid, val=newval)
        
        if affected == 0:
            q = "INSERT INTO rpcc_mutex_var_val (var, value) "
            q += " VALUES (:var, :val) "
            self.db.put(q, var=self.varid, val=newval)

    def unset_value(self):
        q = "DELETE FROM rpcc_mutex_var_val "
        q += " WHERE var=:var "
        self.db.put(q, var=self.varid)

    def get_value(self):
        q = "SELECT value FROM rpcc_mutex_var_val WHERE var=:var "
        try:
            ((val,),) = self.db.get(q, var=self.varid)
            return val
        except ValueError:
            return None


class MutexStringSet(MutexVariable):
    type_field = "C"

    def add(self, newval):
        q = "SELECT 1 "
        q += " FROM rpcc_mutex_var_val "
        q += "WHERE var=:var "
        q += "  AND value=:val "
        ret = list(self.db.get(q, var=self.varid, val=newval))
        if ret:
            return

        q = "INSERT INTO rpcc_mutex_var_val (var, value) VALUES (:var, :val) "
        self.db.put(q, var=self.varid, val=newval)

    def remove(self, oldval):
        q = "DELETE FROM rpcc_mutex_var_val "
        q += "WHERE var=:var "
        q += "  AND value=:val "
        affected = self.db.put(q, var=self.varid, val=oldval)

        if affected == 0:
            raise default_error.ExtNoSuchMutexVariableValueError()

    def get_values(self):
        q = "SELECT value FROM rpcc_mutex_var_val WHERE var=:var "
        return [row[0] for row in self.db.get(q, var=self.varid)]


class Watchdog(object):
    def __init__(self, mutex, name, readonly):
        self.name = name
        self.mutex = mutex
        self.function = mutex.function
        self.db = mutex.db
        self.readonly = readonly

        q = "SELECT warning_at, error_at "
        q += " FROM rpcc_watchdog "
        q += "WHERE mutex=:mtx "
        q += "  AND name=:name "
        ((warn, err),) = self.db.get(q, mtx=self.mutex.oid, name=self.name)

        self.warning_at = warn
        self.error_at = err

    def set(self, warn_at, err_at):
        if self.readonly:
            raise ValueError("This Watchdog instance is read-only.")

        q = "UPDATE rpcc_watchdog "
        q += "  SET warning_at=:warn, error_at=:err "
        q += "WHERE mutex=:mtx "
        q += "AND name=:name "
        self.db.put(q, mtx=self.mutex.oid, name=self.name, err=err_at,
                    warn=warn_at)

    def start(self, warning_at, error_at):
        if warning_at is None or error_at is None:
            raise ValueError("Both warning and error times must be set. Or perhaps you meant .stop()?")
        self.set(warning_at, error_at)

    def stop(self):
        self.set(None, None)

    def get_state(self):
        now = self.function.started_at()
        if self.error_at is None:
            return "stopped"
        elif now > self.error_at:
            return "error"
        elif now > self.warning_at:
            return "warning"
        else:
            return "running"


class Mutex(model.Model):
    name = "mutex"
    exttype = default_type.ExtMutex
    id_type = basestring

    def init(self, name, mutex_id, holder, holder_public, last_change, forced):
        self.oid = name
        self.mutex_id = mutex_id
        self.holder = holder
        self.holder_public = holder_public
        self.last_change = last_change
        self.forced = (forced == 'Y')

    def acquire(self, holder_pub, force=False, session=None):
        # Acquiring the mutex is a single operation on the rpcc_mutex
        # table, where we (ab)use the row lock to make sure that
        # exactly one session can acquire the mutex at any one time
        # (even in the face of multiple simultaneous attempts in
        # parallell transactions).

        if session is None:
            session = self.function.session.oid

        q = "UPDATE rpcc_mutex "
        q += "  SET holder_session=:sesn, "
        q += "      holder_public=:pub, "
        q += "      forced='N' "
        q += "WHERE id=:mutex "
        q += "  AND holder_session IS NULL "
        affected = self.db.put(q, sesn=session, pub=holder_pub,
                               mutex=self.mutex_id)

        if affected == 1:
            self.reload()
            return True

        if force:
            q = "UPDATE rpcc_mutex "
            q += "  SET holder_session=:sesn, "
            q += "      holder_public=:pub, "
            q += "      forced='Y' "
            q += "WHERE id=:mutex "
            affected = self.db.put(q, sesn=session, pub=holder_pub,
                                   mutex=self.mutex_id)
            self.reload()
            return True
        else:
            return False

    def release(self, force=False, session=None):
        if session is None:
            session = self.function.session.oid

        q = "UPDATE rpcc_mutex "
        q += "  SET holder_session=NULL, "
        q += "      holder_public=NULL, "
        q += "      forced='N' "
        q += "WHERE id=:mutex "
        q += "  AND holder_session=:sesn "

        affected = self.db.put(q, mutex=self.mutex_id, sesn=session)
        if affected == 1:
            self.reload()
            return True

        if force:
            q = "UPDATE rpcc_mutex "
            q += "  SET holder_session=NULL, "
            q += "      holder_public=NULL, "
            q += "      forced='Y' "
            q += "WHERE id=:mutex "
            self.db.put(q, mutex=self.mutex_id)
            self.reload()
            return True

        return False

    def _check_current_holder(self, session_id=None):
        if not session_id:
            session_id = self.function.session.oid

        q = "SELECT 1 "
        q += " FROM rpcc_mutex "
        q += "WHERE id=:mutex "
        q += "  AND holder_session=:sesn "
        ret = list(self.db.get(q, mutex=self.mutex_id, sesn=session_id))

        if len(ret) == 0:
            raise default_error.ExtMutexNotHeldError()

    #               ###
    # Mutex variables #
    #               ###

    def get_variable(self, varname, other_session=None):
        self._check_current_holder(other_session)

        q = "SELECT v.id, v.typ "
        q += " FROM rpcc_mutex_var v "
        q += "WHERE v.mutex_id = :mutex "
        q += "  AND v.name = :name "
        ret = list(self.db.get(q, mutex=self.mutex_id, name=varname))
        if not ret:
            raise default_error.ExtNoSuchMutexVariableError()

        ((varid, typ),) = ret

        if typ == 'S':
            return MutexString(self, varname, varid, typ)
        elif typ == 'C':
            return MutexStringSet(self, varname, varid, typ)
        else:
            raise ValueError("Undefined type %s for mutex variable %s on mutex %s" % (typ, varname, self.oid))

    def get_string_variable(self, varname, session=None):
        var = self.get_variable(varname, session)
        if not isinstance(var, MutexString):
            raise default_error.ExtMutexVariableIsWrongTypeError()
        return var

    def get_stringset_variable(self, varname, session=None):
        var = self.get_variable(varname, session)
        if not isinstance(var, MutexStringSet):
            raise default_error.ExtMutexVariableIsWrongTypeError()
        return var

    def get_variable_names(self, typ, session=None):
        # Mutex hold check is implicit in query
        if not session:
            session = self.function.session.oid

        q = "SELECT m.id, v.name "
        q += " FROM rpcc_mutex m LEFT OUTER JOIN rpcc_mutex_var v "
        q += "      ON (m.id=v.mutex_id "
        q += "          AND m.holder_session=:sesn "
        q += "          AND v.typ=:typ) "

        ret = list(self.db.get(q, sesn=session, typ=typ))

        # No rows returned -> mutex not held
        if len(ret) == 0:
            raise default_error.ExtMutexNotHeldError()
    
        # One or more rows -> non-null values are variable names of the
        # specified type.
        return [var for (_, var) in ret if var is not None]

    def get_string_variable_names(self, session):
        return self.get_variable_names('S', session)

    def get_stringset_variable_names(self, session):
        return self.get_variable_names('C', session)

    def create_variable(self, name, typ, session=None):
        self._check_current_holder(session)

        q = "INSERT INTO rpcc_mutex_var (mutex_id, name, typ) "
        q += " VALUES (:mtx, :name, :typ) "

        try:
            affected = self.db.put(q, mtx=self.mutex_id, name=name, typ=typ)
        except database.IntegrityError as _e:
            raise default_error.ExtMutexVariableAlreadyExistsError()

        if affected == 0:
            raise default_error.ExtMutexNotHeldError()

    def create_string_variable(self, name, session=None):
        return self.create_variable(name, 'S', session)

    def create_stringset_variable(self, name, session=None):
        return self.create_variable(name, 'C', session)

    def destroy_variable(self, varname, typ, session=None):
        if session is None:
            session = self.function.session.oid

        muvar = self.get_variable(varname, session)
        if muvar.typ != typ:
            raise default_error.ExtMutexVariableIsWrongTypeError()

        # Mutex hold check was performed by .get_variable(), no need
        # to do it again.
        
        muvar.clear()

        q = "DELETE FROM rpcc_mutex_var WHERE id=:var "
        self.db.put(q, var=muvar.varid)

    def destroy_string_variable(self, name, session=None):
        return self.destroy_variable(name, 'S', session)

    def destroy_stringset_variable(self, name, session=None):
        return self.destroy_variable(name, 'C', session)

    #         ###
    # Watchdogs #
    #         ###

    def get_watchdog(self, wdname, session=None, override=False):
        # If override is True, this is a call from the
        # WatchdogProtocol, and a readonly instance should be returned.

        if override:
            readonly = True
        else:
            if session is None:
                session = self.function.session.oid
            self._check_current_holder(session)
            readonly = False

        return Watchdog(self, wdname, not readonly)

    def get_all_watchdogs(self, session=None):
        self._check_current_holder(session)

        q = "SELECT name FROM rpcc_watchdog WHERE mutex_id = :mtx"
        return [self.get_watchdog(row[0]) for row in self.db.get(q, mtx=self.oid)]

    def create_watchdog(self, wdname, session=None):
        self._check_current_holder(session)

        q = "INSERT INTO watchdog (mutex_id, name) VALUES (:mtx, :name)"
        try:
            self.db.put(q, mtx=self.oid, name=wdname)
        except:
            raise default_error.ExtWatchdogAlreadyExistsError()

    def destroy_watchdog(self, wdname, session=None):
        self._check_current_holder(session)

        q = "DELETE FROM rpcc_watchdog "
        q += "WHERE mutex_id = :mtx "
        q += "  AND name = :name "
        affected = self.db.put(q, mtx=self.oid, name=wdname)

        if affected == 0:
            raise default_error.ExtNoSuchWatchdogError()


class MutexManager(model.Manager):
    name = "mutex_manager"
    manages = Mutex
    model_lookup_error = default_error.ExtNoSuchMutexError

    @classmethod
    def base_query(cls, dq):
        dq.select("name", "id", "holder_session", "holder_public")
        dq.select("last_change", "forced")
        dq.table("rpcc_mutex")

    @access.entry(access.SuperuserGuardProxy)
    def create_mutex(self, name):
        q = "INSERT INTO rpcc_mutex (id, name, holder_session, holder_public, last_change, forced) "
        q += "VALUES (NULL, :name, NULL, NULL, SYSDATE, 'N') "
        try:
            self.db.put(q, name=name)
        except:
            raise default_error.ExtMutexAlreadyExistsError()

    @access.entry(access.SuperuserGuardProxy)
    def destroy_mutex(self, name):
        q = "SELECT id FROM rpcc_mutex WHERE name=:name"
        try:
            ((mutexid,),) = self.db.get(q, name=name)
        except:
            raise default_error.ExtNoSuchMutexError()

        q = "DELETE FROM rpcc_mutex_var_val "
        q += "WHERE var IN (SELECT id "
        q += "                FROM rpcc_mutex_var "
        q += "               WHERE mutex_id = :mtx) "
        self.db.put(q, mtx=mutexid)

        q = "DELETE FROM rpcc_mutex_var "
        q += "WHERE mutex_id = :mtx"
        self.db.put(q, mtx=mutexid)

        q = "DELETE FROM rpcc_mutex "
        q += "WHERE mutex_is = :mtx "
        self.db.put(q, mtx=mutexid)

    @access.entry(access.SuperuserGuardProxy)
    def list_mutex_names(self):
        q = "SELECT name FROM rpcc_mutex"
        return [row[0] for row in self.db.get(q)]
