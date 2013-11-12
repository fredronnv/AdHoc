
import sys
import time
import random
import string
import threading

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

    All sessions contain the three default attributes 'authuser', 
    'privs' and 'lastuse'. 
    """

    def __init__(self, store, sesn, attrs):
        self.store = store
        self.session_id = sesn
        self.init_defaults()
        self.init(attrs)
        self.locked = True

    def init_defaults(self):
        self.authuser = None
        self.privs = []
        self.lastuse = None

    def init(self, attrs):
        for (key, value) in attrs.items():
            self.key = value

    def __setattr__(self, attr, newval):
        if hasattr(self, "locked") and self.locked:
            raise ValueError("Cannot write to session instances - use the .store")
        object.__setattr__(self, attr, newval)
            

class SessionStore(object):
    session_id_length = 40
    max_session_age = 8.0 * 60.0 * 60.0

    def __init__(self, server):
        self.server = server
        self.cache = {}
        self.cache_list = []
        self.init()

    def create_session_id(self):
        chars = string.ascii_letters + string.digits
        l = self.session_id_length
        newid = "".join([random.choice(sesnid_chars) for a in [0,]*l])
        return newid

    def init(self):
        self.session_data = {}

    def remove_expired(self):
        toremove = []
        for (sesn, data) in self.session_data.items():
            if data["last_use"] < (time.time() - max_session_age):
                toremove.append(sesn)
        for sesn in toremove:
            del self.session_data[sesn]

    def create_session(self):
        newid = self.create_session_id()
        self.session_data[newid] = dict()

    def destroy_session(self, sesn):
        """Override point"""
        del self.session_data[sesn]

    def set_session_attr(self, sesn, attr, newval):
        """Override"""
        self.session_data[sesn][attr] = newval

    def unset_session_attr(self, sesn, attr):
        """Override"""
        del self.session_data[sesn][attr]

    def login(self, function, user, password):
        # if ...:
        #    self.store.set_attribute(self.session_id, "authuser", user) 
        #    self.store.set_attribute(self.session_id, "privs", get_privs())
        raise NotImplementedError()

    def logout(self, fun, user, password):
        #    self.store.set_attribute(self.session_id, "authuser", None) 
        #    self.store.set_attribute(self.session_id, "privs", [])
        raise NotImplementedError()

    

        




    def __init__(self, remote_ip, function=None, temporary=False, max_age=None):
        # Note! The session _must_not_ retain a reference to the function!!
        #       The session has a longer life-span than the function.
        #       It is OK to extract the server and keep a reference to
        #       that, since the server object lives "forever".
        self.remote_ip = remote_ip
        self.temporary = temporary
        self.create_time = time.time()

        if max_age:
            self.max_age = max_age
            self.expiry_time = self.create_time + self.max_age
        else:
            self.extend_expiry_time()

        self.id = self.create_session_id()
        self.init_authuser(function)
        if function:
            self.server = function.server
        self.start()

    def allow_remote_ip(self, remote_ip):
        return self.remote_ip == remote_ip

    def get_id(self):
        return self.id

    def get_create_time(self):
        return self.create_time

    def get_remote_ip(self):
        return self.remote_ip

    def get_expiry_time(self):
        return self.expiry_time

    def extend_expiry_time(self):
        timeout = 8.0 * 60.0 * 60.0
        self.expiry_time = time.time() + timeout

    def expired(self):
        return time.time() >= self.expiry_time

    def datadict(self):
        return {'id': self.id, 'create_time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))}

    def init_authuser(self, function):
        self.authuser = None

        if not function:
            return
        
        if not function.handler.headers.has_key('authorization'):
            return

        auth_header = function.handler.headers['authorization']
        if auth_header[:10].lower() != 'negotiate ':
            return

        auth_token = auth_header[10:]

        try:
            import kerberos
        except ImportError:
            raise RPCKerberosAuthNotAvailableError()

        ctx = None
        try:
            server_principal = "HTTP@" + function.server.instance_address
            (res, ctx) = kerberos.authGSSServerInit(server_principal)
            res = kerberos.authGSSServerStep(ctx, auth_token)
            if res != kerberos.AUTH_GSS_COMPLETE:
                raise RPCKerberosAuthFailedError()
            
            authprinc = kerberos.authGSSServerUserName(ctx)
            sys.stderr.write("--> Kerberos SPNEGO auth: %s\n" % (authprinc,))
            if '@' in authprinc:
                authprinc = authprinc.split('@')[0]
            self.authuser = authprinc
        finally:
            if ctx:
                kerberos.authGSSServerClean(ctx)

    def login(self, username, password):
        raise NotImplementedError

    def logout(self):
        raise NotImplementedError

    def start(self):
        pass

    def stop(self):
        pass
    

class SessionStore(object):
    """Handles sessions across RPC invocations.

    When an incoming call has a session id in it, the SessionStore
    singleton is asked (under a mutex external to it)
    """
    
    session_class = Session

    # A new session may only be created from a particular IP address
    # if that IP address has created less than .throttle_session_count
    # sessions in the last throttle_session_time seconds.
    throttle_session_count = 1000
    throttle_session_time = 10

    def __init__(self, server, session_class=None):
        self.server = server
        if session_class:
            self.session_class = session_class

        self.thread_lock = threading.RLock()
        self.sessions_by_id = {}
        self.sessions_by_ip = {}

    def clean_expired_sessions(self):
        """Remove all sessions whose .expired() method returns a true value."""

        with self.thread_lock:
            for (key, sesn) in self.sessions_by_id.items():
                if sesn.expired():
                    self.kill_session(sesn)

    def check_throttle(self, remote_ip):
        """Check session creation throttling for the supplied IP address.
        """
        with self.thread_lock:
            if not self.throttle_session_count or not self.throttle_session_time:
                return

            if not self.sessions_by_ip.has_key(remote_ip):
                return

            sesnlist = self.sessions_by_ip[remote_ip]
            since = time.time() - self.throttle_session_time

            count = len([a for a in sesnlist if a.get_create_time() >= since])

            if count > self.throttle_session_count:
                raise RuntimeError, "You are not allowed to create that many sessions."

    def create_session(self, remote_ip, function, temporary):
        """Create a new Session instance, and return it to the caller.

        The Session is saved and later retreivable via a call to
        server.get_session() using the session's id, available through
        the session.get_id() method.

        Before creating a new session, the list of old sessions is
        cleaned of any expired sessions, and then checked to see that
        at least this particular client is not flooding us.

        The temporary flag is passed to the session class' constructor.
        It is intended for sessions that should be removed immediately
        after a call using them is finished, e.g. for Kerberos HTTP SPNEGO-
        authenticated singleton calls.

        The function initiating the creation needs to be passed, since
        the session startup code may initialize e.g. .authuser depending
        on the HTTP request the function call was passed in.

        The session must not retain a reference to the function, since it
        lives between functions.
        """

        with self.thread_lock:
            self.clean_expired_sessions()
            self.check_throttle(remote_ip)

            sesn = self.session_class(remote_ip, function, temporary)
            self.sessions_by_id[sesn.get_id()] = sesn
            try:
                self.sessions_by_ip[sesn.get_remote_ip()].append(sesn)
            except KeyError:
                self.sessions_by_ip[sesn.get_remote_ip()] = [sesn]
            return sesn
            
    def get_session(self, sesnid, remote_ip):
        """Return a session object refered to by the session id.

        The session gets a shot at access control by looking at the
        remote IP. If the session does not think the current remote
        IP address should be able to see it, the server will send back
        the same error as if the session did not exist at all.
        """

        with self.thread_lock:
            self.clean_expired_sessions()
            try:
                sesn = self.sessions_by_id[sesnid]
                if not sesn.allow_remote_ip(remote_ip):
                    raise KeyError
                return sesn
            except KeyError:
                raise ValueError, "No active such session exists for this client."

    def get_all_sessions(self):
        """Return a list of data about all sessions."""

        with self.thread_lock:
            self.clean_expired_sessions()
            try:
                return [sesn.datadict() for sesn in self.sessions_by_id.values()]
            except:
                return []
            
    def kill_session(self, sesn):
        """Immediately invalidate a session object and remove all references
        to it.
        """

        with self.thread_lock:
            sesn.stop()
            sesn_ip = sesn.get_remote_ip()
            sesnlist = self.sessions_by_ip[sesn_ip]
            sesnlist.remove(sesn)
            if not sesnlist:
                del self.sessions_by_ip[sesn_ip]
            del self.sessions_by_id[sesn.get_id()]
