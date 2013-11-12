
"""
A Server instance has exactly one Authenticator instance. 

Subclass Authenticator to handle specific authentication mechanisms.

The default session_auth_login() and session_auth_logout() RPC:s calls
the .login() and .logout() methods on the Authenticator. On success, they
normally call .auth_session() and .deauth_session() respectively.
"""

import exterror

class Authenticator(object):
    def __init__(self, server):
        self.server = server
        self.init()

    def init(self):
        pass

    def auth_session(self, fun, session_id, username):
        self.server.session_store.set_session_attribute(fun, session_id, "authuser", username)

    def deauth_session(self, fun, session_id):
        self.server.session_store.set_session_attribute(fun, session_id, "authuser", None)

    def login(self, fun, session_id, username, password):
        raise NotImplementedError()

    def logout(self, fun, session_id):
        self.deauth_session(fun, session_id)


class NullAuthenticator(Authenticator):
    def login(self, fun, session_id, username, password):
        if username == password:
            self.auth_session(fun, session_id, username)
        else:
            raise exterror.ExtAuthenticationFailedError("Supplied username or password was invalid")




