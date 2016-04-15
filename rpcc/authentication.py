
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

    def login(self, _session, _username, _password, _generic_password):
        raise NotImplementedError()

    def logout(self, _session):
        raise NotImplementedError()

    @classmethod
    def has_krb5(self):
        try:
            import kerberos  # @UnusedImport
            return True
        except:
            return False
        
    @classmethod
    def base_query(cls, dq):  # Dummy method. Do not remove
        return None


class NullAuthenticationManager(AuthenticationManager):
    
    def login(self, session, username, password, _generic_password):
        if username == password:
            session.set("authuser", username)
        else:
            raise exterror.ExtAuthenticationFailedError()
        
    def logout(self, session):
        session.unset("authuser")


class KerberosAuthenticationManager(AuthenticationManager):
        
    def login(self, session, username, password, generic_password):
        krb_realm = self.server.config('KRB_REALM', default='CHALMERS.SE')
        
        if generic_password and password == generic_password:
            session.set("authuser", username)
            session.set("authrealm", krb_realm)
            return
            
        if AuthenticationManager.has_krb5():
            import kerberos
            service = "krbtgt/" + self.function.server.instance_address
            # Get in control of which realm we're using"
            if "@" in username:
                (username,) = username.split('@')
            if kerberos.checkPassword(username, password, service, krb_realm):
                    session.set("authuser", username)
                    session.set("authrealm", krb_realm)
            else:
                raise exterror.ExtAuthenticationFailedError()
        else:
            raise exterror.ExtAuthenticationFailedError()

    def login_krb5(self, session, token):
        ctx = None
        if AuthenticationManager.has_krb5():
            import kerberos
            try:
                server_principal = "HTTP@" + self.function.server.instance_address
                (res, ctx) = kerberos.authGSSServerInit(server_principal)
                res = kerberos.authGSSServerStep(ctx, token)
                if res != kerberos.AUTH_GSS_COMPLETE:
                    raise exterror.ExtAccessDeniedError()
                
                authprinc = kerberos.authGSSServerUserName(ctx)
                if '@' in authprinc:
                    priminst, realm = authprinc.split('@')
                    if "/" in priminst:
                        primary, instance = priminst.split("/")
                    else:
                        primary, instance = priminst, ""
                else:
                    primary, instance, realm = authprinc, "", ""
    
                session.set("authuser", primary)
                session.set("authinst", instance)
                session.set("authrealm", realm)
            finally:
                if ctx:
                    kerberos.authGSSServerClean(ctx)
        else:
            raise exterror.ExtAuthenticationFailedError()

    def logout(self, session):
        session.unset("authuser")
        session.unset("authinst")
        session.unset("authrealm")


class SuperuserOnlyAuthenticationManager(AuthenticationManager):
    def login(self, session, username, password, _generic_password):
        su_password = self.server.config("SUPERUSER_PASSWORD", default=None)
        if not su_password:
            raise exterror.ExtAuthenticationFailedError()
        if username == '#root#' and password == su_password:
            session.set("authuser", "#root#")
        else:
            raise exterror.ExtAuthenticationFailedError()

    def logout(self, session):
        session.unset("authuser")
