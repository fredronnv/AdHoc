
import exttype
import default_type
import default_error

from function import Function, SessionedFunction


class FunServerURLAPI(Function):
    extname = 'server_url_api'

    desc = "Returns a struct indicating the protocol version of this URL. The version number is increased whenever changes programmatically visible to clients are made."
    params = []
    returns = (default_type.ExtServerVersion, "API version for current URL")
    grants = None

    uses_database = False
    log_call_event = False
    creates_event = False

    def do(self):
        return {'service': self.server.service_name,
                'major': str(self.server.major_version),
                'minor': str(self.server.minor_version)}


class FunServerNodeName(Function):
    extname = "server_node_name"
    params = []
    returns = exttype.ExtString
    desc = "Returns the host name of the currently connected server."
    uses_database = False  # Not needed
    log_call_event = False
    creates_event = False

    def do(self):
        import socket
        return socket.gethostname()


class FunPing(Function):
    extname = 'server_ping'
    params = []
    rettype = exttype.ExtNull
    uses_database = True  # I'll do it myself
    log_call_event = False
    creates_event = False

    desc = """Checks that the server is alive.

    This includes for example contacting the database to check that the
    connection is working."""

    def do(self):
        for api in self.server.api_handler.apis:
            print api.get_version_string()
 
        self.db.get('SELECT 1')


class FunServerListAPIVersions(Function):
    extname = 'server_list_api_versions'
    params = []
    returns = exttype.ExtList(default_type.ExtAPIVersionInfo)
    uses_database = False

    desc = """Returns a list of all API versions, together with their
current state and public comments."""

    def do(self):
        ret = []
        states = {"X": "Experimental",
                  "P": "Production",
                  "D": "Deprecated",
                  "R": "Removed"}
        for api in self.server.api_handler.apis:
            ret.append({"version": api.version,
                        "state": states[api.state],
                        "comment": api.comment})

        return ret


class FunSessionStart(Function):
    """Default function to create a new session."""

    extname = 'session_start'
    params = []
    desc = "Creates a new session (execution context) for further calling. Returns an ID valid for a limited time for the current client address only."
    returns = (default_type.ExtSession, "A string that must be the first argument of any furter calls to perform in the context of this session.")
    uses_database = True  # This actaly depends on which session manager we're using.

    def do(self):
        remote_ip = self.http_handler.client_address[0]
        sesnid = self.session_manager.create_session(remote_ip)
        # Below makes the session id be logged together with the
        # session_start() call in the call log.
        self.session = self.session_manager.model(sesnid)
        return self.session


class FunSessionStop(SessionedFunction):
    extname = 'session_stop'
    params = []
    desc = "Invalidates a session (execution context), making it unavailable for any furhter calls."
    returns = exttype.ExtNull
    uses_database = False

    def do(self):
        self.session_manager.destroy_session(self.session)


class FunSessionInfo(SessionedFunction):
    extname = 'session_info'
    returns = (default_type.ExtSessionInfo, "Information about the supplied session")
    desc = "Returns information about the session (execution context)."
    uses_database = True
    log_call_event = False
    creates_event = False

    def do(self):
        return {'session': self.session,
                'expires': self.session.expires,
                'authuser': self.session.authuser}


class FunSessionAuthLogin(SessionedFunction):
    extname = 'session_auth_login'
    params = [('username', exttype.ExtString, 'Username to authenticate as'),
              ('password', exttype.ExtString, 'Password to authenticate with')]

    returns = (exttype.ExtBoolean, "Will always be True - a failed login is returned as an error")

    desc = "Authenticates a session (execution context). If successful, further calls done in that context count as being made by the user whose username was given as argument to this call."

    def log_arguments(self, args):
        return (args[0], args[1], '****')

    def do(self):

        ath = self.authentication_manager
        ath.login(self.session, self.username, self.password, self.server.generic_password)
        return True
    
    
class FunSessionAuthKerberos(SessionedFunction):
    extname = 'session_auth_kerberos'
    params = [('token', exttype.ExtString, "Kerberos token")]
    returns = (exttype.ExtBoolean, "Note: Failed authentications raise an error.")

    desc = """Authenticate a session using Kerberos.

The argument to the call is the same authentication token you would send
in an SPNEGO Authorization header.

If you want SPNEGO, use the session_auth_spnego call instead.
"""

    def do(self):
        ath = self.authentication_manager
        ath.login_krb5(self.session, self.token)
        return True


class FunSessionAuthSPNEGO(SessionedFunction):
    extname = 'session_auth_spnego'
    params = []
    returns = (exttype.ExtNull, "Note: Failed authentications raise an error.")

    desc = """Authenticate a session using HTTP Negotiate (SPNEGO) Kerberos authentication.

When calling this method, the 'Authorization' HTTP header must be set,
to 'negotiate' and an authentication token. If that header is not set,
a 401 HTTP response is sent with the 'WWW-Authentication' header set to
'negotiate'.

If the token checks out, the session is authenticated and True is returned.
Otherwise False is returned and the session continues to be un-authenticated.
"""

    def do(self):
        pass


class FunSessionDeauth(SessionedFunction):
    extname = 'session_deauth'
    params = []
    returns = exttype.ExtNull
    uses_database = False

    desc = "De-authenticate, leavning the session unauthenticated."

    def do(self):
        self.authentication_manager.logout(self.session)


class FunServerListFunctions(Function):
    extname = 'server_list_functions'
    params = []
    returns = exttype.ExtList(exttype.ExtString)
    desc = 'Return a list of function names available on this server.'
    grants = None
    uses_database = False
    log_call_event = False
    creates_event = False

    def do(self):
        return self.api.get_visible_function_names()


class FunServerDocumentation(Function):
    extname = "server_documentation"
    params = [("function", default_type.ExtFunctionName, "Name of function to document")]
    returns = exttype.ExtString
    desc = "Returns a text-version of the documentation for a function."
    uses_database = False
    log_call_event = False
    creates_event = False

    def do(self):
        return self.server.documentation.function_as_text(self.api.version, self.function)


class FunServerFunctionDefinition(Function):
    extname = "server_function_definition"
    params = [("function", default_type.ExtFunctionName, "Name of function to document")]
    returns = default_type.ExtDocFunction
    desc = "Returns a structured definition of the named function"
    uses_database = False
    log_call_event = False
    creates_event = False

    def do(self):
        t = self.server.documentation.function_as_struct(self.api.version, self.function)
        return t


class FunMutexList(SessionedFunction):
    extname = "mutex_list"
    params = []
    returns = exttype.ExtList(default_type.ExtMutex)

    def do(self):
        return self.mutex_manager.list_mutex_names()


class FunMutexCreate(SessionedFunction):
    extname = "mutex_create"
    params = [("name", default_type.ExtMutexName)]
    returns = exttype.ExtNull

    def do(self):
        self.mutex_manager.create_mutex(self.name)


class FunMutexDestroy(SessionedFunction):
    extname = "mutex_destroy"
    params = [("mutex", default_type.ExtMutex)]
    returns = exttype.ExtNull

    def do(self):
        self.mutex_manager.destroy_mutex(self.mutex.oid)


class _MutexFunction(SessionedFunction):
    params = [("mutex", default_type.ExtMutex, "Mutex")]


class FunMutexAcquire(_MutexFunction):
    extname = "mutex_acquire"
    params = [("public_name", exttype.ExtString, "This is the name that will be shown as the holder in mutex_info() calls"),
              ("force", exttype.ExtBoolean, "Should the acquisition be forced even if the mutex was already held?")]
    returns = exttype.ExtNull
    desc = """Attempt to acquire a mutex.

Only one session can hold a particular mutex at any one time. If you pass force=False, the mutex will be acquired by your session only if it was not already held by another session.

If the acquisition fails, a MutexHeld error will be returned.
"""

    def do(self):
        if not self.mutex.acquire(self.public_name, self.force):
            raise default_error.ExtMutexHeldError()


class FunMutexRelease(_MutexFunction):
    extname = "mutex_release"
    params = [("force", exttype.ExtBoolean, "Should the release be forced even if the mutex wasn't held by the session calling?")]
    returns = exttype.ExtNull
    desc = """Attempt to release a mutex.

If you pass force=False, the mutex will only be released if your session was the current holder of it.

If release fails, a MutexNotHeld error will be returned.
"""

    def do(self):
        if not self.mutex.release(self.force):
            raise default_error.ExtMutexNotHeldError()


class FunMutexInfo(_MutexFunction):
    extname = "mutex_info"
    params = []
    returns = default_type.ExtMutexInfo
    desc = """Get information about a mutex."""

    def do(self):
        ret = {"mutex": self.mutex,
               "last_change": self.mutex.last_change,
               "forced": self.mutex.forced}

        if self.mutex.holder:
            ret["state"] = "held"
            ret["holder"] = self.mutex.holder_public or ""
        else:
            ret["state"] = "free"

        return ret


class FunMutexStringCreate(_MutexFunction):
    extname = "mutex_string_create"
    params = [("varname", default_type.ExtMutexVarName, "Name of mutex string variable to create")]
    returns = exttype.ExtNull
    desc = """Create a new string variable on a mutex. The name must not be in use by any variable on that mutex."""

    def do(self):
        self.mutex.create_string_variable(self.varname)


class FunMutexStringList(_MutexFunction):
    extname = "mutex_string_list"
    params = []
    returns = exttype.ExtList(default_type.ExtMutexVarName)
    desc = """Return the names of all string variables for the mutex."""

    def do(self):
        return self.mutex.get_string_variable_names()


class _MutexStringFunction(_MutexFunction):
    params = [("var", default_type.ExtMutexStringVar, "The name of a mutex string variable belonging to the mutex")]


class FunMutexStringGet(_MutexStringFunction):
    extname = "mutex_string_get"
    returns = (exttype.ExtOrNull(exttype.ExtString), "Current value, if any")
    desc = """Return the current value of a mutex string variable, or None if no value is set."""

    def do(self):
        return self.var.get_value()


class FunMutexStringSet(_MutexStringFunction):
    extname = "mutex_string_set"
    params = [("value", exttype.ExtString, "New value to set")]
    returns = exttype.ExtNull
    desc = """Set a new value for a mutex string variable."""

    def do(self):
        self.var.set_value(self.value)


class FunMutexStringUnset(_MutexStringFunction):
    extname = "mutex_string_unset"
    params = []
    returns = exttype.ExtNull
    desc = """Unset a mutex string variable."""

    def do(self):
        self.var.unset_value()


class FunMutexStringDestroy(_MutexStringFunction):
    extname = "mutex_string_destroy"
    params = []
    returns = exttype.ExtNull
    desc = """Destroy a mutex string variable."""

    def do(self):
        self.mutex.destroy_string_variable(self.var.name)


class FunMutexStringsetCreate(_MutexFunction):
    extname = "mutex_stringset_create"
    params = [("varname", default_type.ExtMutexVarName, "Name of mutex stringset variable to create")]
    returns = exttype.ExtNull
    desc = """Create a new stringset variable on a mutex. The name must not be in use by any variable on that mutex."""

    def do(self):
        self.mutex.create_stringset_variable(self.varname)


class FunMutexStringsetList(_MutexFunction):
    extname = "mutex_stringset_list"
    params = []
    returns = exttype.ExtList(default_type.ExtMutexVarName)
    desc = """Return the names of all string variables for the mutex."""

    def do(self):
        return self.mutex.get_stringset_variable_names()


class _MutexStringsetFunction(_MutexFunction):
    params = [("var", default_type.ExtMutexStringsetVar, "The name of a mutex stringset variable belonging to the mutex")]


class FunMutexStringsetGet(_MutexStringsetFunction):
    extname = "mutex_stringset_get"
    returns = (exttype.ExtList(exttype.ExtString), "Current values, if any")
    desc = """Return the current values of a mutex stringset variable."""

    def do(self):
        return self.var.get_values()


class FunMutexStringsetAdd(_MutexStringsetFunction):
    extname = "mutex_stringset_add"
    params = [("value", exttype.ExtString, "Value to add to the set")]
    returns = exttype.ExtNull
    desc = """Add a value to a mutex string set variable. It is OK to add a value multiple times, but it will only be present once in the set."""

    def do(self):
        self.var.add(self.value)


class FunMutexStringsetRemove(_MutexStringsetFunction):
    extname = "mutex_stringset_remove"
    params = [("value", exttype.ExtString, "Value to remove from the set")]
    returns = exttype.ExtNull
    desc = """Remove a value from a mutex string set. It is an error to try remove a value that is currently not in the set."""

    def do(self):
        self.var.remove(self.value)


class FunMutexStringsetRemoveAll(_MutexStringsetFunction):
    extname = "mutex_stringset_remove_all"
    params = []
    returns = exttype.ExtNull
    desc = """Removes all values from a mutex stringset."""

    def do(self):
        self.var.clear()


class FunMutexStringsetDestroy(_MutexStringsetFunction):
    extname = "mutex_stringset_destroy"
    params = []
    returns = exttype.ExtNull
    desc = """Destroy a mutex stringset variable."""

    def do(self):
        self.mutex.destroy_stringset_variable(self.var.name)


class FunMutexWatchdogList(_MutexFunction):
    extname = "mutex_watchdog_list"
    params = []
    returns = exttype.ExtList(default_type.ExtWatchdog)
    desc = """Return all watchdogs belonging to the mutex."""

    def do(self):
        self.mutex.get_all_watchdogs()


class FunMutexWatchdogCreate(_MutexFunction):
    extname = "mutex_watchdog_create"
    params = [("name", default_type.ExtWatchdogName)]
    returns = exttype.ExtNull

    def do(self):
        self.mutex.create_watchdog(self.name)


class _WatchdogFunction(_MutexFunction):
    params = [("watchdog", default_type.ExtWatchdog, "A watchdog belonging to the mutex")]


class FunMutexWatchdogState(_WatchdogFunction):
    extname = "mutex_watchdog_state"
    params = []
    returns = default_type.ExtWatchdogState

    def do(self):
        return self.watchdog.get_state()
    

class FunMutexWatchdogStart(_WatchdogFunction):
    extname = "mutex_watchdog_start"
    params = [("warning_at", exttype.ExtDateTime),
              ("error_at", exttype.ExtDateTime)]
    returns = exttype.ExtNull

    def do(self):
        self.watchdog.start(self.warning_at, self.error_at)


class FunMutexWatchdogStop(_WatchdogFunction):
    extname = "mutex_watchdog_stop"
    params = []
    returns = exttype.ExtNull

    def do(self):
        self.watchdog.stop()


class FunMutexWatchdogInfo(_WatchdogFunction):
    extname = "mutex_watchdog_info"
    params = []
    returns = default_type.ExtWatchdogInfo

    def do(self):
        return {
            "state": self.watchdog.get_state(),
            "warning_at": self.watchdog.warning_at,
            "error_at": self.watchdog.error_at,
            }


class FunMutexWatchdogDestroy(_WatchdogFunction):
    extname = "mutex_watchdog_destroy"
    params = []
    returns = exttype.ExtNull

    def do(self):
        self.mutex.destroy_watchdog(self.watchdog.name)
