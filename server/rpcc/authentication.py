
"""
A Server instance has exactly one Authenticator instance. 

Subclass Authenticator to handle specific authentication mechanisms.

The default session_auth_login() and session_auth_logout() RPC:s calls
the .login() and .logout() methods on the Authenticator. On success, they
normally call .auth_session() and .deauth_session() respectively.
"""

import exterror
import model


class AuthenticationManager(model.Manager):
    """Supplies two default methods: 
       .login(session, username, password)
       .logout(session)

    Implementations MUST set the 'authuser' attribute of the sessions
    if authentication succeeds, but are allowed to set other attributes 
    as well."""

    name = "authentication_manager"
    models = None

    def model(self, oid):
        # DO NOT IMPLEMENT THIS - it is a model-less manager!
        raise NotImplementedError()

    def login(self, session, username, password):
        raise NotImplementedError()

    def logout(self, session):
        raise NotImplementedError()


class NullAuthenticationManager(AuthenticationManager):
    def login(self, session, username, password):
        if username == password:
            session.set("authuser", username)
        else:
            raise exterror.ExtAuthenticationFailedError()

    def logout(self, session):
        session.unset("authuser")


class SuperuserOnlyAuthenticationManager(AuthenticationManager):
    def login(self, session, username, password):
        if username == '#root#' and password == self.server.config("SUPERUSER_PASSWORD"):
            session.set("authuser", "#root#")
        else:
            raise exterror.ExtAuthenticationFailedError()

    def logout(self, session):
        session.unset("authuser")
