#!/usr/bin/env python

import model
import default_type
import default_error
import datetime

class Mutex(model.Model):
    name = "mutex"
    exttype = default_type.ExtMutex
    id_type = str

    def init(self, name, mutex_id, holder, holder_public, last_change, forced):
        self.oid = name
        self.mutex_id = mutex_id
        self.holder = holder
        self.holder_public = holder_public
        self.last_change = last_change
        self.forced = (forced == 'Y')

    def XXXis_held(self, by_session=None):
        if by_session:
            return (self.holder == by_session)
        else:
            return (self.holder is not None)

    def acquire(self, session_id, holder_pub, force=False):
        q = "UPDATE rpcc_mutex "
        q += "  SET holder_session=:sesn, "
        q += "      holder_public=:pub, "
        q += "      forced='N' "
        q += "WHERE id=:mutex "
        q += "  AND holder_session IS NULL "
        affected = self.db.put(q, sesn=session_id, pub=holder_pub,
                               mutex=self.mutex_id)

        if affected == 1:
            self.db.commit()
            self.reload()
            return True

        if force:
            q = "UPDATE rpcc_mutex "
            q += "  SET holder_session=:sesn, "
            q += "      holder_public=:pub, "
            q += "      forced='Y' "
            q += "WHERE id=:mutex "
            affected = self.db.put(q, sesn=session_id, pub=holder_pub,
                                   mutex=self.mutex_id)
            self.db.commit()
            self.reload()
            return True
        else:
            return False

    def release(self, session_id, force=False):
        q = "UPDATE rpcc_mutex "
        q += "  SET holder_session=NULL, "
        q += "      holder_public=NULL, "
        q += "      forced='N' "
        q += "WHERE id=:mutex "
        q += "  AND holder_session=:sesn "

        affected = self.db.put(q, mutex=self.mutex_id, sesn=session_id)
        if affected == 1:
            self.db.commit()
            self.reload()
            return True

        if force:
            q = "UPDATE rpcc_mutex "
            q += "  SET holder_session=NULL, "
            q += "      holder_public=NULL, "
            q += "      forced='Y' "
            q += "WHERE id=:mutex "
            self.db.put(q, mutex=self.mutex_id)
            self.db.commit()
            self.reload()
            return True

        return False

    def has_variable(self, name, is_set=False):
        q = "SELECT 1 "
        q += " FROM variable "
        q += "WHERE pdb_mutex=:mutex "
        q += "  AND name=:name "
        if is_set:
            q += "  AND collection = 1 "
        else:
            q += "  AND collection = 0 "

        return bool(self.db.get(q, mutex=self.mutex_id, name=name))

    def has_collection(self, name):
        return self.has_variable(name, is_set=True)

    def list_variables(self, session_id):
        q = "SELECT m.id, v.name"
        q += " FROM pdb_mutex m LEFT OUTER JOIN variable v "
        q += "          ON (m.id=v.pdb_mutex AND m.holder_session=:sesn AND v.collection=0) "

        ret = self.db.get(q, sesn=session_id)

        if not ret:
            raise PDBMutexNotHeldError()

        return [var for (dummy, var) in ret if var is not None]

    def list_collections(self, session_id):
        q = "SELECT m.id, v.name"
        q += " FROM pdb_mutex m LEFT OUTER JOIN variable v "
        q += "          ON (m.id=v.pdb_mutex AND m.holder_session=:sesn AND v.collection=1) "

        ret = self.db.get(q, sesn=session_id)

        if not ret:
            raise PDBMutexNotHeldError()

        return [var for (dummy, var) in ret if var is not None]

    def create_variable(self, session_id, name, collection=False):
        q = "INSERT INTO variable (pdb_mutex, name, value, collection) "
        q += " SELECT id, :name, NULL, :collection "
        q += "   FROM pdb_mutex "
        q += "  WHERE id=:mutex "
        q += "    AND holder_session=:sesn "

        if collection:
            collection = 1
        else:
            collection = 0

        try:
            affected = self.db.put(q, mutex=self.my_id, sesn=session_id,
                                     name=name, collection=collection)
        except DBUniqueConstraintViolatedError:
            if collection:
                if self.has_collection(name):
                    raise PDBMutexCollectionAlreadyExistsError()
                else:
                    raise PDBMutexCollectionIsAVariableError()
            else:
                if self.has_variable(name):
                    raise PDBMutexVariableAlreadyExistsError()
                else:
                    raise PDBMutexVariableIsACollectionError()

        if affected == 0:
            raise PDBMutexNotHeldError()

    def get_variable(self, session_id, name):
        q = "SELECT value, "
        q += "      CASE WHEN m.holder_session=:sesn THEN 1 ELSE 0 END, "
        q += "      collection "
        q += " FROM variable v, pdb_mutex m "
        q += "WHERE v.pdb_mutex=:mutex "
        q += "  AND v.name=:name "
        q += "  AND v.pdb_mutex = m.id "

        res = self.db.get(q, sesn=session_id, mutex=self.my_id, name=name)
        
        if not res:
            raise PDBNoSuchMutexVariableError()

        (value, held, collection) = res[0]

        if collection:
            raise PDBVariableIsACollectionError()
        elif not held:
            raise PDBMutexNotHeldError()

        return value

    def get_collection(self, session_id, setvar):
        # Possible outcomes:
        # (a) Mutex not held
        # (b) Mutex held, but variable does not exist
        # (c) Mutex held, but variable is not a list
        # (d) Mutex held, variable has no value
        # (e) Mutex held, variable has one or more values
        
        q = "SELECT v.id, sv.value "
        q += " FROM pdb_mutex m, variable v LEFT OUTER JOIN collection_value sv ON v.id=sv.variable "
        q += "WHERE v.pdb_mutex=:mutex "
        q += "  AND v.name=:name "
        q += "  AND v.pdb_mutex = m.id "
        q += "  AND v.collection = 1 "
        q += "  AND m.holder_session = :sesn "

        res = self.db.get(q, sesn=session_id, mutex=self.my_id, name=setvar)

        if res:
            # (d) and (e)
            return [v[1] for v in res if v[1] is not None]

        if self.has_collection(setvar):
            raise PDBMutexNotHeldError()
        elif self.has_variable(setvar):
            raise PDBVariableIsNotACollectionError()
        else:
            raise PDBNoSuchMutexCollectionError()

    def set_variable(self, session_id, name, value):
        # Possible outcomes:
        # (a) Mutex not held
        # (b) Mutex held, variable does not exist
        # (c) Mutex held, variable is a set
        # (d) Mutex held, variable was updated

        q = "UPDATE variable "
        q += "  SET value=:val "
        q += "WHERE (pdb_mutex, name)"
        q += "   IN (SELECT v.pdb_mutex, v.name "
        q += "         FROM variable v, pdb_mutex m "
        q += "        WHERE v.pdb_mutex = m.id "
        q += "          AND m.holder_session = :sesn "
        q += "          AND v.name = :name "
        q += "          AND v.pdb_mutex = :mutex "
        q += "          AND v.collection = 0 "
        q += "      )"

        affected = self.db.put(q, mutex=self.my_id, sesn=session_id, 
                                 name=name, val=value)

        if affected == 1:
            self.db.commit()
            return

        if self.has_variable(name):
            raise PDBMutexNotHeldError()
        elif self.has_collection(name):
            raise PDBMutexVariableIsACollectionError()
        else:
            raise PDBNoSuchMutexVariableError()
        
    def add_collection_value(self, session_id, name, value):
        # Possible outcomes:
        # (a) Mutex not held
        # (b) Mutex held, variable does not exist
        # (c) Mutex held, variable is not a set
        # (d) Mutex held, value already in set
        # (e) Mutex held, value was added to set

        q = "INSERT INTO collection_value (variable, value) "
        q += "  SELECT v.id, :val "
        q += "    FROM pdb_mutex m, variable v "
        q += "   WHERE m.holder_session = :sesn "
        q += "     AND m.id = v.pdb_mutex "
        q += "     AND v.pdb_mutex = :mutex "
        q += "     AND v.name = :name "
        q += "     AND v.collection = 1 "
        
        try:
            affected = self.db.put(q, mutex=self.my_id, sesn=session_id,
                                     name=name, val=value)
        except DBUniqueConstraintViolatedError:
            # It is explicitly allowed to add the same value more than
            # once.
            return

        if affected == 1:
            self.db.commit()
            return

        if self.has_collection(name):
            raise PDBMutexNotHeldError()
        elif self.has_variable(name):
            raise PDBMutexCollectionIsAVariableError()
        else:
            raise PDBNoSuchMutexCollectionError()

    def remove_collection_value(self, session_id, setvar, value):
        # Possible outcomes:
        # (a) Mutex not held
        # (b) Mutex held, variable does not exist
        # (c) Mutex held, variable is not a set
        # (d) Mutex held, variable does not contain the value
        # (e) Mutex held, value was removed

        q = "DELETE FROM collection_value "
        q += " WHERE value=:val "
        q += "   AND variable = ( "
        q += "        SELECT v.id "
        q += "          FROM pdb_mutex m, variable v "
        q += "         WHERE m.holder_session = :sesn "
        q += "           AND m.id = v.pdb_mutex "
        q += "           AND v.pdb_mutex = :mutex "
        q += "           AND v.name = :name "
        q += "           AND v.collection = 1 "
        q += "       )"

        affected = self.db.put(q, mutex=self.my_id, sesn=session_id,
                                 name=setvar, val=value)

        if affected == 1:
            self.db.commit()
            return

        if self.has_collection(setvar):
            if self.is_held(session_id):
                raise PDBMutexValueNotInCollectionError()
            else:
                raise PDBMutexNotHeldError()
        elif self.has_variable(setvar):
            raise PDBMutexCollectionIsAVariableError()
        else:
            raise PDBNoSuchMutexCollectionError()

    def destroy_collection(self, session_id, name):
        self.destroy_variable(session_id, name, collection=True)

    def destroy_variable(self, session_id, name, collection=False):
        # Possible outcomes:
        # (a) Mutex not held
        # (b) Mutex held, variable does not exist
        # (c) Mutex held, variable removed

        if collection:
            q = "DELETE FROM collection_value "
            q += " WHERE variable = ( "
            q += "         SELECT v.id "
            q += "           FROM variable v, pdb_mutex m "
            q += "          WHERE m.id=:mutex "
            q += "            AND m.id=v.pdb_mutex "
            q += "            AND m.holder_session=:sesn "
            q += "            AND v.name=:name "
            q += "       )"

            affected = self.db.put(q, mutex=self.my_id, sesn=session_id,
                                     name=name)

        q = "DELETE FROM variable "
        q += " WHERE id = ( "
        q += "         SELECT v.id "
        q += "           FROM variable v, pdb_mutex m "
        q += "          WHERE m.id=:mutex "
        q += "            AND m.id=v.pdb_mutex "
        q += "            AND m.holder_session=:sesn "
        q += "            AND v.name=:name "
        q += "            AND v.collection = :collection "
        q += "       )"

        if collection:
            collection = 1
        else:
            collection = 0

        affected = self.db.put(q, mutex=self.my_id, sesn=session_id,
                                 name=name, collection=collection)

        print affected
        if affected == 1:
            self.db.commit()
            return

        if collection:
            if self.has_variable(name):
                raise PDBMutexCollectionIsAVariableError()
            elif self.has_collection(name):
                raise PDBMutexNotHeldError()
            else:
                raise PDBNoSuchMutexCollectionError()
        else:
            if self.has_collection(name):
                raise PDBMutexVariableIsACollectionError()
            elif self.has_variable(name):
                raise PDBMutexNotHeldError()
            else:
                raise PDBNoSuchMutexVariableError()

    def create_watchdog(self, session_id, name):
        q = "INSERT INTO mutex_watchdog (pdb_mutex, name) "
        q += " SELECT id, :name "
        q += "   FROM pdb_mutex "
        q += "  WHERE id = :mutex "
        q += "    AND holder_session = :sesn "

        try:
            affected = self.db.put(q, mutex=self.my_id, sesn=session_id,
                                     name=name)
        except DBUniqueConstraintViolatedError:
            raise PDBMutexWatchdogAlreadyExistsError()

        if affected == 0:
            raise PDBMutexNotHeldError()

    def set_watchdog(self, session_id, name, warn_minutes, err_minutes):
        # Possible outcomes:
        # (a) Mutex not held
        # (b) Mutex held, variable does not exist
        # (c) Mutex held, variable was updated


        if warn_minutes and err_minutes:
            if warn_minutes > err_minutes:
                raise PDBMutexWatchdogTimeError()
            warn_time = self.now + datetime.timedelta(minutes=warn_minutes)
            err_time = self.now + datetime.timedelta(minutes=err_minutes)
        elif warn_minutes or err_minutes:
            raise ValueError()
        else:
            warn_time = None
            err_time = None

        q = "UPDATE mutex_watchdog "
        q += "  SET warning_at = :warn, "
        q += "      error_at = :err "
        q += "WHERE (pdb_mutex, name)"
        q += "   IN (SELECT w.pdb_mutex, w.name "
        q += "         FROM mutex_watchdog w, pdb_mutex m "
        q += "        WHERE w.pdb_mutex = m.id "
        q += "          AND m.holder_session = :sesn "
        q += "          AND w.name = :name "
        q += "          AND w.pdb_mutex = :mutex "
        q += "      )"

        affected = self.db.put(q, mutex=self.my_id, sesn=session_id, 
                                 name=name, warn=warn_time, err=err_time)

        if affected == 1:
            return

        if self.has_watchdog(name):
            raise PDBMutexNotHeldError()
        else:
            raise PDBNoSuchMutexWatchdogError()

    def has_watchdog(self, name):
        q = "SELECT 1 "
        q += " FROM mutex_watchdog "
        q += "WHERE pdb_mutex=:mutex "
        q += "  AND name=:name "

        return bool(self.db.get(q, mutex=self.my_id, name=name))

    def get_watchdog(self, session_id, name):
        q = "SELECT w.warning_at, w.error_at "
        q += " FROM mutex_watchdog w, pdb_mutex m "
        q += "WHERE w.pdb_mutex = :mutex "
        q += "  AND w.name = :name "
        q += "  AND m.id = w.pdb_mutex "
        q += "  AND m.holder_session = :sesn "
        
        res = self.db.get(q, mutex=self.my_id, sesn=session_id, name=name)

        if not res:
            if self.has_watchdog(name):
                raise PDBMutexNotHeldError()
            else:
                raise PDBNoSuchMutexWatchdogError()

        (warn_at, err_at) = res[0]
        if warn_at is None:
            return {"running": False}

        warn_in = warn_at - self.now
        err_in = err_at - self.now

        return {"running": True, 
                "warn_minutes": warn_in.days * 1440 + int(1 + warn_in.seconds / 60.0), 
                "err_minutes": err_in.days * 1440 + int(1 + err_in.seconds / 60.0), 
                }

    def list_watchdogs(self, session_id):
        q = "SELECT m.id, w.name"
        q += " FROM pdb_mutex m LEFT OUTER JOIN mutex_watchdog w "
        q += "          ON (m.id=w.pdb_mutex AND m.holder_session=:sesn) "

        ret = self.db.get(q, sesn=session_id)

        if not ret:
            raise PDBMutexNotHeldError()

        return [var for (dummy, var) in ret if var is not None]

    def destroy_watchdog(self, session_id, name):
        # Possible outcomes:
        # (a) Mutex not held
        # (b) Mutex held, watchdog does not exist
        # (c) Mutex held, watchdog removed

        q = "DELETE FROM mutex_watchdog "
        q += " WHERE (pdb_mutex, name) IN ( "
        q += "         SELECT w.pdb_mutex, w.name "
        q += "           FROM mutex_watchdog w, pdb_mutex m "
        q += "          WHERE m.id=:mutex "
        q += "            AND m.id=w.pdb_mutex "
        q += "            AND m.holder_session=:sesn "
        q += "            AND w.name=:name "
        q += "       )"

        affected = self.db.put(q, mutex=self.my_id, sesn=session_id,
                                 name=name)

        if affected == 1:
            return

        if self.has_watchdog(name):
            raise PDBMutexNotHeldError()
        else:
            raise PDBNoSuchMutexWatchdogError()



class MutexManager(model.Manager):
    name = "mutex_manager"
    manages = Mutex
    model_lookup_error = default_error.ExtNoSuchMutexError

    def base_query(self, dq):
        dq.select("name", "id", "holder_session", "holder_public")
        dq.select("last_change", "forced")
        dq.table("rpcc_mutex")

