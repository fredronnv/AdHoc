
from exttype import *  # @UnusedWildImport
from default_type import *  # @UnusedWildImport
from default_error import *  # @UnusedWildImport
from function import Function, SessionedFunction


class FunServerURLAPI(Function):
    extname = 'server_url_api'

    desc = "Returns a struct indicating the protocol version of this URL. The version number is increased whenever changes programmatically visible to clients are made."
    params = []
    returns = (ExtServerVersion, "API version for current URL")

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
    returns = (ExtSession, "A string that must be the first argument of any furter calls to perform in the context of this session.")

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
    returns = ExtNull

    def do(self):
        self.session_manager.destroy_session(self.session)


class FunSessionInfo(SessionedFunction):
    extname = 'session_info'
    returns = (ExtSessionInfo, "Information about the supplied session")
    desc = "Returns information about the session (execution context)."

    def do(self):
        return {'session': self.session,
                'expires': self.session.expires,
                'authuser': self.session.authuser}


class FunSessionAuthLogin(SessionedFunction):
    extname = 'session_auth_login'
    params = [('username', ExtString, 'Username to authenticate as'),
              ('password', ExtString, 'Password to authenticate with')]

    returns = (ExtBoolean, "Will always be True - a failed login is returned as an error")

    desc = "Authenticates a session (execution context). If successful, further calls done in that context count as being made by the user whose username was given as argument to this call."

    def log_arguments(self, args):
        return ('*', args[1], '****')

    def do(self):
        ath = self.authentication_manager
        ath.login(self.session, self.username, self.password)
        return True


class FunSessionStartWithLogin(Function):
    extname = 'session_start_with_login'
    params = [('username', ExtString, 'Username to authenticate as'),
              ('password', ExtString, 'Password to authenticate with')]
    returns = (ExtSession, "Authenticated call context")

    desc = "Create a session and attempt to authenticate it returning the session if authentication succeeded."

    def log_arguments(self, args):
        return (args[0], '****')

    def do(self):
        remote_ip = self.handler.client_address[0]
        sesnid = self.session_manager.create_session(remote_ip)
        self.session = self.session_manager.model(sesnid)

        try:
            ath = self.authentication_manager
            ath.login(self.session, self.username, self.password)
            return self.session
        except:
            self.session_manager.destroy_session(self.session)
            raise


class FunSessionDeauth(SessionedFunction):
    extname = 'session_deauth'
    params = []
    returns = ExtNull

    desc = "De-authenticate, leavning the session unauthenticated."

    def do(self):
        self.authentication_manager.logout(self.session)


class FunServerListFunctions(Function):
    extname = 'server_list_functions'
    params = []
    returns = ExtList(ExtString)
    desc = 'Return a list of function names available on this server.'
    grants = None

    def do(self):
        return self.api.get_all_function_names()


class FunServerDocumentation(Function):
    extname = "server_documentation"
    params = [("function", ExtFunctionName, "Name of function to document")]
    returns = ExtString
    desc = "Returns a text-version of the documentation for a function."

    def do(self):
        return self.server.documentation.function_as_text(self.api.version, self.function)


class FunServerFunctionDefinition(Function):
    extname = "server_function_definition"
    params = [("function", ExtFunctionName, "Name of function to document")]
    returns = ExtDocFunction
    desc = "Returns a structured definition of the named function"

    def do(self):
        t = self.server.documentation.function_as_struct(self.api.version, self.function)
        return t


class _MutexFunction(SessionedFunction):
    params = [("mutex", ExtMutex, "Mutex")]


class FunMutexAcquire(_MutexFunction):
    extname = "mutex_acquire"
    params = [("public_name", ExtString, "This is the name that will be shown as the holder in mutex_info() calls"),
              ("force", ExtBoolean, "Should the acquisition be forced even if the mutex was already held?")]
    returns = ExtNull
    desc = """Attempt to acquire a mutex.

Only one session can hold a particular mutex at any one time. If you pass force=False, the mutex will be acquired by your session only if it was not already held by another session.

If the acquisition fails, a MutexHeld error will be returned.
"""

    def do(self):
        if not self.mutex.acquire(self.session.id, self.public_name, self.force):
            raise ExtMutexHeldError()


class FunMutexRelease(_MutexFunction):
    extname = "mutex_release"
    params = [("force", ExtBoolean, "Should the acquisition be forced even if the mutex wasn't held by the session calling?")]
    returns = ExtNull
    desc = """Attempt to release a mutex.

If you pass force=False, the mutex will only be released if your session was the current holder of it.

If release fails, a MutexNotHeld error will be returned.
"""

    def do(self):
        if not self.mutex.release(self.session.id, self.force):
            raise ExtMutexNotHeldError()


class FunMutexInfo(_MutexFunction):
    extname = "mutex_info"
    params = []
    returns = ExtMutexInfo
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
