
import exttype
import default_type
import default_error

from function import Function, SessionedFunction


class FunServerURLAPI(Function):
    extname = 'server_url_api'

    desc = "Returns a struct indicating the protocol version of this URL. The version number is increased whenever changes programmatically visible to clients are made."
    params = []
    returns = (default_type.ExtServerVersion, "API version for current URL")
    uses_database = False

    grants = None

    def do(self):
        return {'service': self.server.service_name,
                'major': self.server.major_version,
                'minor': self.server.minor_version}


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
    uses_database = False

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
        ath.login(self.session, self.username, self.password)
        return True


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

    def do(self):
        return self.api.get_visible_function_names()


class FunServerDocumentation(Function):
    extname = "server_documentation"
    params = [("function", default_type.ExtFunctionName, "Name of function to document")]
    returns = exttype.ExtString
    desc = "Returns a text-version of the documentation for a function."
    uses_database = False

    def do(self):
        return self.server.documentation.function_as_text(self.api.version, self.function)


class FunServerFunctionDefinition(Function):
    extname = "server_function_definition"
    params = [("function", default_type.ExtFunctionName, "Name of function to document")]
    returns = default_type.ExtDocFunction
    desc = "Returns a structured definition of the named function"
    uses_database = False

    def do(self):
        t = self.server.documentation.function_as_struct(self.api.version, self.function)
        return t




class FunServerListMutexes(SessionedFunction):
    extname = "server_list_mutexes"
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


class FunMutexCreateString(_MutexFunction):
    extname = "mutex_create_string"
    params = [("varname", default_type.ExtMutexVarName, "Name of mutex string variable to create")]
    returns = exttype.ExtNull
    desc = """Create a new string variable on a mutex. The name must not be in use by any variable on that mutex."""

    def do(self):
        self.mutex.create_string_variable(self.varname)


class FunMutexListStrings(_MutexFunction):
    extname = "mutex_list_strings"
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


class FunMutexCreateStringset(_MutexFunction):
    extname = "mutex_create_stringset"
    params = [("varname", default_type.ExtMutexVarName, "Name of mutex stringset variable to create")]
    returns = exttype.ExtNull
    desc = """Create a new stringset variable on a mutex. The name must not be in use by any variable on that mutex."""

    def do(self):
        self.mutex.create_stringset_variable(self.varname)


class FunMutexListStringsets(_MutexFunction):
    extname = "mutex_list_stringsets"
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


class FunMutexStringsetDestroy(_MutexStringsetFunction):
    extname = "mutex_stringset_destroy"
    params = []
    returns = exttype.ExtNull
    desc = """Destroy a mutex stringset variable."""

    def do(self):
        self.mutex.destroy_stringset_variable(self.var.name)


class FunMutexListWatchdogs(_MutexFunction):
    extname = "mutex_list_watchdogs"
    params = []
    returns = exttype.ExtList(default_type.ExtWatchdog)
    desc = """Return all watchdogs belonging to the mutex."""

    def do(self):
        self.mutex.get_all_watchdogs()


class FunMutexCreateWatchdog(_MutexFunction):
    extname = "mutex_create_watchdog"
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

