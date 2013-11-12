
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

    def auth_session(self, session, username):
        self.server.session_store.set_session_attr(session, "authuser", username)

    def deauth_session(self, session):
        self.server.session_store.unset_session_attr(session, "authuser")

    def login(self, session, username, password):
        raise NotImplementedError()

    def logout(self, session):
        self.deauth_session(session)


class NullAuthenticator(Authenticator):
    def login(self, session, username, password):
        if username == password:
            self.auth_session(session, username)
        else:
            raise exterror.ExtAuthenticationFailedError("Supplied username or password was invalid")




