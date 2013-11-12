
import sys
import time
import random
import string
import datetime
import threading

import function

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

class Session(object):
    """Class used for stateful interactions with an RPC client.

    HTTP is stateless, and a session mechanism therefore needs to be
    implemented on top of ordinary HTTP/XMLRPC to allow stateful 
    operations such as authentication.

    Session instances are read-only. Value changes are performed
    through the SessionStore (session.store).
    """

    def __init__(self, store, sesn, attrs):
        self.store = store
        self.id = sesn
        self.load(attrs)

    def init(self, attrs):
        for (key, value) in attrs.items():
            setattr(self, key, value)

    def load(self, attrs):
        self.locked = False
        self.init(attrs)
        self.locked = True

    def __setattr__(self, attr, newval):
        if hasattr(self, "locked") and self.locked and attr != "locked":
            raise ValueError("Cannot write to session instances - use the session store")
        object.__setattr__(self, attr, newval)
            

class SessionStore(object):
    session_id_length = 40
    session_lifetime = datetime.timedelta(hours=8)
    session_class = Session
    # "id" and "expires" are implicit.
    default_attrs = {"authuser": None}

    def __init__(self, server):
        self.server = server
        self.cache = {}
        self.cache_list = []
        self.init()

    def new_session_id(self):
        chars = string.ascii_letters + string.digits
        l = self.session_id_length
        newid = "".join([random.choice(chars) for a in [0,]*l])
        return newid

    def init(self):
        pass

    def get_default_attributes(self, fun):
        return self.default_attrs

    def create_session(self, fun, remote_ip):
        self.delete_expired(fun)
        newid = self.new_session_id()
        newattrs = self.default_attrs.copy()
        newattrs["expires"] = fun.started_at() + self.session_lifetime
        self.store_create(fun, newid, newattrs)
        return newid

    def destroy_session(self, fun, sesnid):
        self.store_delete(fun, sesnid)

    def set_session_attribute(self, fun, sesnid, attr, value):
        self.store_update(fun, sesnid, attr, value)

    def get_session(self, fun, sesnid):
        if not isinstance(fun, function.Function):
            raise ValueError(fun)
        self.set_session_attribute(fun, sesnid, "expires", fun.started_at() + datetime.timedelta(hours=8))
        data = self.load(fun, sesnid)
        return self.session_class(self, sesnid, data)

    def delete_expired(self, fun):
        for sesnid in self.find_expired(fun):
            self.destroy_session(sesnid)

    def auth_login(self, fun, sesnid, user, password):
        if self.login(fun, user, password):
            self.set_session_attribute(fun, sesnid, "authuser", user)

    def deauth(self, fun, sesnid):
        self.set_session_attribute(fun, sesnid, "authuser", None)


class MemorySessionStore(SessionStore):
    def init(self):
        self.session_data = {}
        self.lock = threading.Lock()

    def store_create(self, fun, sesnid, attrs):
        with self.lock:
            self.session_data[sesnid] = attrs.copy()
            print self.session_data
        
    def store_update(self, fun, sesnid, key, newval):
        with self.lock:
            self.session_data[sesnid][key] = newval

    def store_delete(self, fun, sesnid):
        with self.lock:
            del self.session_data[sesnid]

    def load(self, fun, sesnid):
        with self.lock:
            print "URHJ", self.session_data[sesnid]
            return self.session_data[sesnid]

    def find_expired(self, fun):
        with self.lock:
            todel = []
            for (sesnid, data) in self.session_data.items():
                if data["expires"] > fun.started_at():
                    todel.append(sesnid)
            return todel


class DatabaseSessionStore(SessionStore):
    """Required tables:

    CREATE TABLE rpcc_session (
      id VARCHAR(40) NOT NULL PRIMARY KEY,
      expires TIMESTAMP
    );

    CREATE TABLE rpcc_session_string (
      session_id VARCHAR(40) NOT NULL,
        FOREIGN KEY (session_id) REFERENCES rpcc_session(id),
      name VARCHAR(30) NOT NULL,
      value VARCHAR(30)
    )

    No thread locking needed - the SQL queries are against one Function's
    db link and that link's transaction.

    """

    def store_create(self, fun, sesnid, attrs):
        q = "INSERT INTO rpcc_session (id, expires) VALUES (:i, :e)"
        fun.db.put(q, i=sesnid, e=attrs["expires"])

        for (key, value) in attrs.items():
            if key == "expires":
                continue
            q = "INSERT INTO rpcc_session_string (session_id, name, value) "
            q += "VALUES (:s, :k, :v) "
            fun.db.put(q, s=sesnid, k=key, v=value)

    def store_update(self, fun, sesnid, key, value):
        if key == "expires":
            q = "UPDATE rpcc_session SET expires=:e WHERE id=:i"
            fun.db.put(q, e=value, i=sesnid)
        elif key == "id":
            raise ValueError()
        else:
            q = "UPDATE rpcc_session_string SET value=:v "
            q += "WHERE session_id=:i AND name=:k "
            fun.db.put(q, v=value, i=sesnid, k=key)

    def store_delete(self, fun, sesnid):
        q = "DELETE FROM rpcc_session_string WHERE session_id=:i"
        fun.db.put(q, i=sesnid)

        q = "DELETE FROM rpcc_session WHERE id=:i"
        fun.db.put(q, i=sesnid)

    def load(self, fun, sesnid):
        ret = {'id': sesnid}
        q = "SELECT expires FROM rpcc_session WHERE id=:i"
        ((expires,),) = fun.db.get(q, i=sesnid)
        ret["expires"] = expires
        q = "SELECT name, value FROM rpcc_session_string WHERE session_id=:i"
        for (key, value) in fun.db.get(q, i=sesnid):
            ret[key] = value

        return ret

    def find_expired(self, fun):
        q = "SELECT id FROM rpcc_session WHERE expires > :n"
        return [s for (s,) in fun.db.get(q, n=fun.started_at())]

