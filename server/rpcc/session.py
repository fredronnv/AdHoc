
import random
import string
import datetime
import threading

import model
import default_error
import default_type

"""
The session mechanism is used to give clients a call context that
survives across calls. Although the intention is that only a single 
thread of a single client uses a particular session at any one time, 
the system mustn't break if clients disregard this advice.

From the client's perspective, it asks the server for a new session id,
which it then passes in a series of requests. In this series some
calls may affect the context, for example authenticating it. Finally, the
client asks the server to dispose of the session.

From the Function implementor's perspective, a Function subclass only 
needs to have a first parameter of type exttypes.SessionType in order 
for a .session attribute to be set to a readonly Session instance before 
.do() is called.

On the server, all session id:s and Session instances are handled by a 
SessionStore singleton. It is responsible for creating, removing and 
garbagecollecting session id:s. It is also responsible for instantiating 
the Session instances that the Functions use. Session instances can live 
for one or many calls, but the call context that the session id and
Session represent must live until the session id is garbage collected.

The default Session handles name/value pairs, where the value is either a 
single string or a list of strings. Storing and loading these pairs is done 
by the SessionStore - you shouldn't need to subclass both Session and
SessionStore to implement a new storage mechanism.

There are three default SessionStores. The SessionStore base class only
stores session data in memory. The FileSessionStore class stores data
on disk, local to one server. The DatabaseSessionStore stores sessions
in a database.

"""


class Session(model.Model):
    """Class used for stateful interactions with an RPC client.

    HTTP is stateless, and a session mechanism therefore needs to be
    implemented on top of ordinary HTTP/XMLRPC to allow stateful 
    operations such as authentication.

    Session instances are read-only. Value changes are performed
    through the SessionStore (session.store).
    """

    exttype = default_type.ExtSession
    name = "session"

    def init(self, sid, expires):
        self.oid = sid
        self.expires = expires
        for (key, value) in self.manager.get_session_values(sid):
            setattr(self, key, value)
        self.locked = True

    def __setattr__(self, attr, newval):
        if hasattr(self, "locked") and self.locked and attr != "locked":
            raise ValueError("Cannot write to session instances - use the session store")
        object.__setattr__(self, attr, newval)

    def set(self, var, val):
        self.manager.set_session_attribute(self.oid, var, val)
        self.locked = False
        self.reload()

    def unset(self, var):
        self.manager.unset_session_attribute(self.oid, var)
        self.locked = False
        self.reload()


class SessionManager(model.Manager):
    name = "session_manager"
    manages = Session
    model_lookup_error = default_error.ExtNoSuchSessionError

    session_id_length = 40
    session_lifetime = datetime.timedelta(hours=8)

    # "id" and "expires" are implicit.
    default_attrs = {"authuser": None}

    def new_session_id(self):
        chars = string.ascii_letters + string.digits
        l = self.session_id_length
        newid = "".join([random.choice(chars) for _a in [0, ] * l])
        return newid

    def get_session_values(self, sid):
        raise NotImplementedError()

    def create_session(self, remote_ip):
        raise NotImplementedError()

    def destroy_session(self, sid):
        raise NotImplementedError()

    def set_session_attribute(self, sid, attr, value):
        raise NotImplementedError()

    def unset_session_attribute(self, sid, attr):
        raise NotImplementedError()

    def delete_expired(self):
        raise NotImplementedError()


class DatabaseBackedSessionManager(SessionManager):
    def base_query(self, dq):
        dq.select("id", "expires")
        dq.table("rpcc_session")

    def model(self, sid):
        # Wrap base class call to first remove expired sessions, fetch
        # the session, then update expiry time.
        self.delete_expired()
        session = SessionManager.model(self, sid)
        session.set("expires", self.function.started_at() + self.session_lifetime)
        return session

    def get_session_values(self, sid):
        q = "SELECT name, value "
        q += " FROM rpcc_session_string "
        q += "WHERE session_id=:sesn "
        # If values come from the select, Session.init() will overwrite
        # the default, which are first in the list.
        return self.default_attrs.items() + list(self.db.get(q, sesn=sid))

    def create_session(self, remote_ip):
        self.delete_expired()
        newid = self.new_session_id()
        expires = self.function.started_at() + self.session_lifetime
        q = "INSERT INTO rpcc_session (id, expires) "
        q += " VALUES (:sesn, :exp) "
        self.db.put(q, sesn=newid, exp=expires)
        self.db.commit()
        return newid

    def destroy_session(self, sesnid):
        # When destroying a session, all mutexes held by it are first
        # released, if mutexes are enabled in the server. This counts
        # as a forced release (the sesssion should have released the
        # mutex explicitly).
        if isinstance(sesnid, Session):
            sesnid = sesnid.oid

        if self.server.mutexes_enabled:
            q = "UPDATE rpcc_mutex "
            q += "  SET holder_session=NULL, "
            q += "      holder_public=NULL, "
            q += "      forced='Y' "
            q += "WHERE holder_session=:sesn "
            self.db.put(q, sesn=sesnid)

        # Remove session variables.
        q = "DELETE FROM rpcc_session_string "
        q += " WHERE session_id=:sesn "
        self.db.put(q, sesn=sesnid)

        # Remove the session itself.
        q = "DELETE FROM rpcc_session "
        q += " WHERE id=:sesn "
        self.db.put(q, sesn=sesnid)
        self.db.commit()

    def set_session_attribute(self, sesnid, attr, value):
        if attr == 'oid':
            raise ValueError("Cannot change the ID of a session")

        if attr == 'expires':
            q = "UPDATE rpcc_session "
            q += "  SET expires=:value "
            q += "WHERE id=:sesn "
            self.db.put(q, sesn=sesnid, value=value)
            self.db.commit()
            return

        q = "UPDATE rpcc_session_string "
        q += "  SET value=:value "
        q += "WHERE name=:attr "
        q += "  AND session_id=:sesn "

        affected = self.db.put(q, sesn=sesnid, attr=attr, value=value)
        if affected == 0:
            q = "INSERT INTO rpcc_session_string (session_id, name, value) "
            q += " VALUES (:sesn, :attr, :value) "
            self.db.put(q, sesn=sesnid, attr=attr, value=value)

        self.db.commit()

    def unset_session_attribute(self, sesnid, attr):
        if attr in ('expires', 'oid'):
            raise ValueError("Cannot remove the 'expires' or 'id' attributes of sessions")

        q = "DELETE FROM rpcc_session_string "
        q += "WHERE session_id=:sesn "
        q += "  AND name=:attr "
        self.db.put(q, sesn=sesnid, attr=attr)
        self.db.commit()

    def delete_expired(self):
        q = "SELECT id "
        q += " FROM rpcc_session "
        q += "WHERE expires < :now "
        for (sid,) in self.db.get_all(q, now=self.function.started_at()):
            self.destroy_session(sid)


# This isn't working.
class XXMemoryBackedSessionManager(SessionManager):
    def init(self):
        self.session_data = {}
        self.lock = threading.Lock()

    def model(self, sid):
        try:
            return Session(self, sid, self.session_data[sid]["expires"])
        except:
            raise self.model_lookup_error(value=sid)

    def get_session_values(self, sid):
        with self.lock:
            return self.default_attrs.items() + self.session_data[sid].items()

    def create_session(self, remote_ip):
        self.delete_expired()
        newid = self.new_session_id()
        expires = self.function.started_at() + self.session_lifetime
        with self.lock:
            self.session_data[newid] = {"oid": newid, "expires": expires}
            print "LKJ", self.session_data
        return newid
        
    def destroy_session(self, sid):
        if isinstance(sid, Session):
            sid = sid.oid

        with self.lock:
            del self.session_data[sid]

    def set_session_attribute(self, sid, attr, value):
        if attr == "oid":
            raise ValueError("Cannot change ID of a session")

        with self.lock:
            self.session_data[sid][attr] = value

    def unset_session_attribute(self, sid, attr, value):
        if attr in ("oid", "expires"):
            raise ValueError("Cannot remove 'id' or 'expires' attributes of a session")

        with self.lock:
            del self.session_data[sid][attr]

    def delete_expired(self):
        with self.lock:
            now = self.function.started_at()
            todel = []
            for (sid, data) in self.session_data.items():
                if data["expires"] < now:
                    todel.append(sid)
            for sid in todel:
                del self.session_data[sid]
