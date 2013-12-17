
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
    uses_database = False

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
        if not self.mutex.acquire(self.session.id, self.public_name, self.force):
            raise default_error.ExtMutexHeldError()


class FunMutexRelease(_MutexFunction):
    extname = "mutex_release"
    params = [("force", exttype.ExtBoolean, "Should the acquisition be forced even if the mutex wasn't held by the session calling?")]
    returns = exttype.ExtNull
    desc = """Attempt to release a mutex.

If you pass force=False, the mutex will only be released if your session was the current holder of it.

If release fails, a MutexNotHeld error will be returned.
"""

    def do(self):
        if not self.mutex.release(self.session.id, self.force):
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
