#!/usr/bin/env python
""" Subclass of rpcc_client that requires that the connection is done to a test system. A test system is tagged by having a person namend 'THIS IS A', 'TEST SYSTEM'
    with the cid='testsys' and person number 1234567890."""
import getpass
import os
import sys

import rpcc_client


sys.path.append(os.environ["ADHOC_RUNTIME_HOME"] + "/rpcc_client")



class ADHOCNotATestSystem(Exception):
    def is_type(self, name):
        if "::" in name:
            return bool(self.args[0]["name"].startswith(name))
        else:
            return bool(self.args[0]["namelist"][-1] == name)


class ADHOCSuperUserError(Exception):
    def is_type(self, name):
        if "::" in name:
            return bool(self.args[0]["name"].startswith(name))
        else:
            return bool(self.args[0]["namelist"][-1] == name)


class RPCC(rpcc_client.RPCC):

    class FunctionProxy(rpcc_client.RPCC.FunctionProxy):

        def __call__(self, *args, **kwdict):
            # Prepare
            # print "Testclient calling. rpc=", self.funname
            self.proxy.rpcs_called.add(self.funname)   # Remember rpcs successfully executed, for statistics
            ret = super(RPCC.FunctionProxy, self).__call__(*args, **kwdict)
            if(self.funname != "server_function_definition"):
                # docdict = 
                self.proxy._server_docdict(self.funname)
                # pprint.pprint(docdict)
#                 try:
#                     self.proxy.check_type(ret, docdict.returns, path=[])
#                 except AssertionError as e:
#                     pprint.pprint(e)
#                     print "Return check of function %s:" % (self.funname)
#                     print "Docdict="
#                     pprint.pprint(docdict)
#                     print "Value="
#                     pprint.pprint(ret)
#                     raise
            else:
                # pprint.pprint(ret)
                pass
            self.proxy.rpcs_succeeded.add(self.funname)  # Remember rpcs successfully executed, for statistics
            # print "Testclient called"
            # Finish
            return ret

    def __getattr__(self, name):
        if name[0] != '_':
            self.last_function = name
        fn = super(RPCC, self).__getattr__(name)
        return fn

    def __init__(self, url, user=None, password=None, api_version=None, return_attrdicts=True, convert_digs=False, _try_json=True, basic_exceptions=True, superuser=None):
        self._return_attrdicts = return_attrdicts
        self._convert_digs = convert_digs
        self._basic_exceptions = basic_exceptions
        self._docdicts = {}
        self.superuser = superuser
        self.actual_cache = {}

        self.rpcs_called = set()
        self.rpcs_succeeded = set()
        self.api_version = api_version

        if not url:
            url = os.environ.get("ADHOC_SERVER_URL", "http://localhost:4433")

        # print "Connecting to server at ",url
        if user is None:
            user = os.environ.get('ADHOC_USER', None)
            if not user:
                print "ADHOC user not defined, please define ADHOC_USER"
                exit(2)
        if user != '' and not password:
            password = os.environ.get("ADHOC_GENERIC_PASSWORD", None)
            if not password:
                try:
                    password = os.environ['ADHOC_USER_PW']
                except KeyError:
                    print "Enter password for '%s'" % user
                    password = getpass.getpass()

        rpcc_client.RPCC.__init__(self, url,
                                  api_version=api_version,
                                  attrdicts=return_attrdicts,
                                  pyexceptions=basic_exceptions)

        try:
            if(user != ""):
                self.session_auth_login(user, password)
                self.password = password
        except Exception, e:
            print "Can not log on to server as ", user, " using ******"
            print e
            raise
        if(user != ""):
            self.validate_test_system()

    def _server_docdict(self, funname):
        """Store the type information for a particular RPCC RPC.
        Intended use is for command-line speedups and simplifications."""

        if funname not in self._docdicts:
            self._docdicts[funname] = self.server_function_definition(funname)
        return self._docdicts[funname]

    def get_from_cache(self, what):
        return self.actual_cache[what]

    def put_into_cache(self, what, value):
        self.actual_cache[what] = value

    def validate_test_system(self):
        """ Validates that the server we are working on is connected to a database designed for testing. This is to guard
            the production system from accidentally running the possibly destructive tests there"""
        return   # No way to test this yet
        try:
            res = self.person_search_public({"primary_account": "testsys", "firstname": "THIS IS A", "lastname": "TEST SYSTEM"})
        except rpcc_client.RPCCError, _e:
            raise ADHOCNotATestSystem("Lookup error")
        if len(res) != 1:
            raise ADHOCNotATestSystem("Too many results")

        testperson = res[0]

        if testperson["primary_account"] != "testsys":
            raise ADHOCNotATestSystem("Wrong primary account")

        if testperson["firstname"] != "THIS IS A":
            raise ADHOCNotATestSystem("Wrong first name")

        if testperson["lastname"] != "TEST SYSTEM":
            raise ADHOCNotATestSystem("Wrong last name")

    def username(self):
        if not self._auth:
            return None
        if "/" in self._auth:
            return self._auth.split("/")[0]
        return self._auth

    def clear_privileges(self, reset=True):
        if not self._auth:
            raise ValueError()

        if not self.superuser:
            raise ADHOCSuperUserError("The proxy for %s has no superuser proxy defined" % (self.username()))

        if self.username() == self.superuser.username():
            raise ADHOCSuperUserError("Removing the privileges of the superuser is a very bad idea")

#         for m in self.superuser.membership_dig({"group_pattern": "_rpcc_priv_*", "account": self.username(), "valid_now": True}, {"group": True, "membership": True}):
#             self.superuser.membership_expire(m.membership)
        try:   
            privs = self.superuser.account_fetch(self.username(), {"granted_privileges": True})["granted_privileges"]
            for p in privs:
                self.superuser.privilege_revoke(p, self.username())
        except rpcc_client.RPCCError, e:
            if not e.is_error("NoSuchAccount"):
                raise
        
        if reset:
            self.reset_session()

    def clear_access(self, reset=True):
        if not self._auth:
            raise ValueError()
        
        if reset:
            self.reset_session()

    def add_privilege(self, priv):
        superu = self.superuser  # If we have a superuser, use that
        if not superu:
            superu = self  # otherwise we're probably the superuser ourselves
        try:
            superu.account_create(self.username(), "Fornamn", "Efternamn")
        except rpcc_client.RPCCError, e:
            if not e.is_error("AccountAlreadyExists"):
                raise
            
        try:
            superu.privilege_create(priv, "Do not know what this is for")
        except rpcc_client.RPCCError, e:
            if not e.is_error("PrivilegeAlreadyExists"):
                raise
        try:
            superu.privilege_grant(priv, self.username())
        except rpcc_client.RPCCError, e:
            if not e.is_error("PrivilegeAlreadyGranted"):
                raise
        print "Granted privilege %s for %s" % (priv, self.username())
        
    def set_privileges(self, *privs):
        self.clear_privileges(reset=False)

        for priv in privs:
            self.add_privilege(priv)
        self.reset_session()

    def reset_session(self, password=None):
        if not password and self.password:
                rpcc_client.RPCC.reset(self, self.password)
        else:
                rpcc_client.RPCC.reset(self, password)
