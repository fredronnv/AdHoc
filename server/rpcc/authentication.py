
"""
A Server instance has exactly one Authenticator instance. 

Subclass Authenticator to handle specific authentication mechanisms.

The default session_auth_login() and session_auth_logout() RPC:s calls
the .login() and .logout() methods on the Authenticator. On success, they
normally call .auth_session() and .deauth_session() respectively.
"""

import exterror
import model
import os

class AuthenticationManager(model.Manager):
    """Supplies three default methods: 
       .login(session, username, password)
       .login_krb5(session, token)
       .logout(session)

    Implementations MUST set the 'authuser' attribute of the sessions
    if authentication succeeds, but are allowed to set other attributes 
    as well.
    
    Subclasses may add additional login methods.
    """

    name = "authentication_manager"
    models = None

    # Set to the realm(s) from which we accept logins. This is the
    # part of a Kerberos principal following the @-sign.
    krb5_realms = []

    def model(self, oid):
        # DO NOT IMPLEMENT THIS - it is a model-less manager!
        raise NotImplementedError()

    def login(self, session, username, password):
        raise NotImplementedError()

    def logout(self, session):
        raise NotImplementedError()

    @classmethod
    def has_krb5(self):
        try:
            import kerberos
            return True
        except:
            return False


class NullAuthenticationManager(AuthenticationManager):
    def login_null(self, session, username, password):
        if username == password:
            session.set("authuser", username)
        else:
            raise exterror.ExtAuthenticationFailedError()
        
    def login(self, session, username, password):
        if AuthenticationManager.has_krb5():
            import kerberos
            krb_realm=os.environ.get('ADHOC_KRB_REALM','CHALMERS.SE')
            service = "krbtgt/" + self.function.server.instance_address
            if kerberos.checkPassword(username, password, service, krb_realm):
                    session.set("authuser", username)
            else:
                raise exterror.ExtAuthenticationFailedError()
        else:
            raise exterror.ExtAuthenticationFailedError()

    def login_krb5(self, session, token):
        ctx = None
        try:
            server_principal = "HTTP@" + self.function.server.instance_address
            (res, ctx) = kerberos.authGSSServerInit(server_principal)
            res = kerberos.authGSSServerStep(ctx, token)
            if res != kerberos.AUTH_GSS_COMPLETE:
                raise default_error.ExtAccessDeniedError()
            
            principal = kerberos.authGSSServerUserName(ctx)
            sys.stderr.write("--> Kerberos SPNEGO auth: %s\n" % (authprinc,))
            if '@' in principal:
                priminst, realm = authprinc.split('@')[0]
                if "/" in priminst:
                    primary, instance = priminst.split("/")
                else:
                    primary, instance = priminst, ""
            else:
                primary, instance, realm = principal, "", ""

            session.set("authuser", primary)
            session.set("authinst", instance)
            session.set("authrealm", realm)
        finally:
            if ctx:
                kerberos.authGSSServerClean(ctx)

    def logout(self, session):
        session.unset("authuser")
        session.unset("authinst")
        session.unset("authrealm")


class SuperuserOnlyAuthenticationManager(AuthenticationManager):
    def login(self, session, username, password):
        if username == '#root#' and password == self.server.config("SUPERUSER_PASSWORD"):
            session.set("authuser", "#root#")
        else:
            raise exterror.ExtAuthenticationFailedError()

    def logout(self, session):
        session.unset("authuser")