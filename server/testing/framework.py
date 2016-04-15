#!/usr/bin/env python
""" ADHOC API test framework
    This is a framework for the ADHOC-API test suites.
    
    To use this framework, it has to be imported into a script that defines the tests to be run using

    from framework import *

    The test script then has to end with:
    if __name__ == "__main__":
        sys.exit(main())

    The framework defines a number of accounts to use when executing the tests. Each account 
    will have one proxy, that manages a session with the RPCC server. 
    Each test defines which access privileges and level of authentication that is expected for the tested function to succeed.
    When the test is run, the expected privileges are compared withe the actual privileges of the testing proxy, and it is determined
    whether we expect an exception or not. This is done by the AssertAccessError class which should be wrapping the actual server execution
    using the python "with" statement like:

        with AssertAccessError(self):
            self.proxy.some_rpcc_function(...)


    The expected privileges for a test can be specified in either of three ways:
    1) By inheriting from a subclass of tests, e.g. AuthTests, Superusertests etc
    2) By explicitly setting self.expected_access, self.sufficient_privs, self.expected_admin, and self.expected_authenticated in the test.
       This way, different expectations may be set for different parts of the test.
    3) By giving the one of the parameters expected_admin, expected_access, sufficient_privs or expected_authenticated to the AssertAccessError invocation.
    Parameters override explicit settings which overrides inheritance.

    The framework also includes an "engine" for running the tests. Each test is a class having a a method named do(). The testing engine introspects the
    test script to find out which classes have a di() method. Before running the tests the engine sorts the found classes alphabetically so that there
    is a defined order in which the tests are run, this is why the test classes are prefixed with a Tnnnn_ part.
    All the tests are run for a specific test user (proxy) before another user is used. (This goes within each script, as as each script is a self contained unit)

    Before running any tests, the test users have to be logged in. This is done using the generic pasword that has to be found in the environment variable 
    ADHOC_GENERIC_PASSWORD, which is also used by the RPCC server under test.

    The method setup_proxies returns a tuple defining the proxies that has been set up and the order of which the proxies are meant to be
    used. The order is:
         self.nouser,       A proxy that is not authenticated. Almost all tests should fail for this user.

    All these proxies may be used explicitly within a test, but the test engine will assign self.proxy as the proxy to use normally. In another proxy
    is used, the access checking mechanism would have to be specified using parameters (3) above.
    The proxy setup will also make sure that the accounts for the test users exists. If they do not, they are created as secondary accounts to the super user, 
    with the exception of normaluser2 that has to be set up manually.

    The test engine is of the same class as the tests. When a test is run, the attribute "parent" is set up for the test object, The parent points to the test engine.
    This allows for the use of the engine to store things between tests, which comes in handy when testing sequences of operations like lock-unlock scenarios.

    """

import os
import datetime
import pprint
from types import *
sys.path.append(os.environ["ADHOC_RUNTIME_HOME"] + "/client")
import test_rpcc_client
import rpcc_client


def main(argv=None):
    """ Main function called from the bottom of this script"""
    tests = MyTests()  # Create a mother object within which all tests are run
    tests.setup()  # Do the necessary setup
    tests.dotests()  # Run the tests
    tests.finish()  # Finish up, print reports


class MyTests(object):
    """ Mother class for all the tests. The class contains definitions and methods used by many of the tests and also includes
        the main methods for driving the test sequence."""
    # Whether to skip the test or not
    skip = False
        
    # Default access and privilege expectations for all tests. These expectations are most likely altered by subclassing or explicit definitions
    expected_authenticated = False
    sufficient_privs = []
    expected_access = ["unauth"]
    expected_admin = False
    expected_loa = False
    expected_exception_name = None
    possible_exception_name = None
    
    # Some groups and accounts used by the tests.
    normal_group_1 = "vtest-entry-1"
    normal_group_2 = "vtest-entry-2"
    internal_group = "_vtest_entry-1"
    
    normal_user_id = "vtest-01"  # A privlesss normal user
    admin_user_id = "vtest-02"  # A privless normal user logged in as /admin!
    registrator_user_id = "vtest-03"  # A registrator logged in normally
    registrator_admin_user_id = "vtest-04"  # A registrator logged in  as /admin
    normal_user2_id = "fbq"  # A privless normal user not owned by the superuser
    noloa_admin = "testsys"  # Used as a non-identified superuser logged in as /admin
    scratch_admin = "aeb"  # A scracthcard admin
    
    # The actual access and privileges for each test as fetched from the server
    actual_access = None
    actual_privs = None
    actual_loa = None
    actual_admin = False

    # Attributes checked
    public_attributes = ["group", "admin_group", "description", "valid_to", "unix_gid"]
    protected_attributes = ["public_sv", "public_en", "it_billing", "file_intpath", "file_quota_mb", "file_reserved_mb"]
    group_protected_attributes = ["it_billing", "file_intpath", "file_quota_mb", "file_reserved_mb"]
    
    # Test phases information
    phaseinfo = [""]
    
    # Override to make the test run twice, once with asmember argument set to true. 
    do_as_group_member_test = False
    
    # 
    superuser_test_may_fail = False  # Normally superusers tests should succeed, but there is an exception

    # When a test is instantiated it may be given a proxy to use as agent for the test. If no proxy is given, it will
    # create its own unauthenticated proxy. If the test is created by the mother test object, this is given as the parent
    # so that data within that parent may be accesed

    def __init__(self, proxy=None, parent=None):
        # self.set_proxy(proxy)
        self.parent = parent

    def prepare_test(self):
        pass  # Toe be overridden if needed
    
    def cleanup_test(self):
        pass  # To be overridden if needed
    
    def set_proxy(self, proxy):
        if not proxy:
            self.proxy = test_rpcc_client.RPCC(None, "", None, 3, basic_exceptions=False)
        else:
            self.proxy = proxy

    # Fetch the actual privs if authenticated
        if self.proxy._auth:
            pass
#             try:
#                 self.actual_access = self.proxy.get_from_cache("actual_access")
#             except KeyError:
#                 self.actual_access = self.proxy.session_get_access()
#                 self.proxy.put_into_cache("actual_access", self.actual_access)
                 
            try:
                self.actual_privs = self.proxy.get_from_cache("actual_privs")
            except KeyError:
                self.actual_privs = self.proxy.session_get_privileges()
                self.proxy.put_into_cache("actual_privs", self.actual_privs)
            if self.proxy == self.superuser:
                self.actual_access = {"anyauth": True, "unauth": True, "superusers": True}
            else:
                self.actual_access = {"anyauth": True, "unauth": True, "superusers": False}
            
            # self.actual_privs = []
            self.actual_admin = self.proxy._auth.endswith("/admin")

    def establish_user(self, userid):
        """ Establish accounts to be used as agents unless they already exists. The accounts are created as secondary
            accounts to the super user"""
        superu = self.superuser
        super_userid = superu.username()

        try:
            dummy_acc = superu.account_get(userid)
            return
        except:
            pass
        super.account_create_secondary(userid, super_userid, {"create_group": True})

    def establish_group(self, groupid):
        """ Establish groups to be used as testing objects, unless they already exist"""
        superu = self.superuser

        try:
            dummy_grp = superu.group_get(groupid)
            return
       
        except rpcc_client.RPCCError as e:
            if e[0]["name"] == "LookupError::NoSuchGroup":
                pass
            else:
                raise
        except:
            raise
        super.group_create(groupid, "Group for testing purposes", None)
        
    def setup(self):
        self.setup_proxies()  # Set up the proxies
        # Put in attribute values into the groups used so that refused reads become clear and distinguished from attributed having the null value
#         for g in (self.normal_group_1, self.normal_group_2, self.internal_group):
#             self.establish_group(g)
#             self.superuser.group_set_it_billing(g, "96023")
#             self.superuser.group_set_file_reserved_mb(g, 42) 
#             self.superuser.group_set_file_quota_mb(g, 4242)
#             self.superuser.group_set_file_intpath(g, "/dev/null")

    def setup_proxies(self):
        """ Setup the proxies or agents to use when testing. The superuser is treated specially. Its proxy is given to all other
            proxies so that the tests may use the superuser's privileges to set up and tear down things for the tests"""
        
        adhoc_superuser = os.environ.get("ADHOC_SUPERUSER", "bernerus")
        generic_password = os.environ.get("ADHOC_GENERIC_PASSWORD", None)
        url = None
        
        try:
            self.nouser = test_rpcc_client.RPCC(None, "", None, 0, basic_exceptions=False)
            self.superuser = test_rpcc_client.RPCC(url, adhoc_superuser, generic_password, 0, basic_exceptions=False)
            
            self.superuser.add_privilege("write_all_host_classes")
            self.superuser.add_privilege("write_all_rooms")
            self.superuser.add_privilege("write_all_hosts")
            self.superuser.add_privilege("write_all_networks")
            self.superuser.add_privilege("write_all_subnetworks")
            self.superuser.add_privilege("write_all_pools")
            self.superuser.add_privilege("write_all_optionspaces")
            self.superuser.add_privilege("write_all_buildings")
            
            self.reguser = test_rpcc_client.RPCC(url, "fbq", generic_password, 0, basic_exceptions=False, superuser=self.superuser)
            self.flooradmin = test_rpcc_client.RPCC(url, "flooradm", generic_password, 0, basic_exceptions=False, superuser=self.superuser)
            self.flooradmin.set_privileges("write_all_hosts", 
                                           "admin_all_pools",
                                           "write_all_rooms")
            self.servicedesk = test_rpcc_client.RPCC(url, "sdadm", generic_password, 0, basic_exceptions=False, superuser=self.superuser)
            self.servicedesk.set_privileges("write_all_hosts", 
                                            "write_all_groups", 
                                            "admin_all_pools",
                                            "write_all_host_classes",
                                            "write_all_rooms",
                                            "write_all_buildings",
                                            )
            self.networkadmin = test_rpcc_client.RPCC(url, "nwadm", generic_password, 0, basic_exceptions=False, superuser=self.superuser)
            self.networkadmin.set_privileges("write_all_hosts", 
                                             "write_all_groups", 
                                             "write_all_networks", 
                                             "write_all_subnetworks", 
                                             "write_all_pools",
                                             "admin_all_pools",
                                             "write_all_rooms",
                                             "write_all_optionspaces",
                                             "write_all_host_classes",
                                             "write_all_buildings",
                                             "write_all_global_options",
                                             "write_all_pool_ranges")
            # regular_users = (self.reguser,)
            regular_users = (self.reguser, self.servicedesk, self.flooradmin, self.servicedesk, self.networkadmin)
            
#             for px in regular_users:
#                 px.clear_privileges()
#                 px.clear_access()

        except test_rpcc_client.ADHOCNotATestSystem as _e: 
            print "Not a test system"
            sys.exit(2)
        
        except rpcc_client.RPCCError as _e:
            print "One or more accounts needed for testing could not be logged in to"
            raise
            sys.exit(2)

        # Return the tuple of proxies to be used when testing. Order matters here.
        self.proxies = (self.superuser, self.nouser) + regular_users
        # self.proxies = (self.superuser,self.scratchadmin)

    def timestamp(self, label):
        t = datetime.datetime.now().isoformat()
        print " %s: %s" % (t, label)

    def finish(self):
        all_rpcs = self.superuser.server_list_functions()
        rpcs_called = set()
        rpcs_succeeded = set()  # @UnusedVariable
        for px in self.proxies:
            pxname = "None"
            if px:
                pxname = px.username()
            print "RPCs executed by ", pxname, ": ", len(px.rpcs_called)
            print "RPCs succeeded by ", pxname, ": ", len(px.rpcs_succeeded)
            for x in px.rpcs_called: 
                rpcs_called.add(x)

        print "RPCs not executed:"
        for rpc in all_rpcs:
            if rpc not in rpcs_called:
                print "   ", rpc

    def dotests(self):
        """ Main engine for testing, called from the outside. The tests to be run is determined usin python introspection and te test order
            is determined using the class name of each test. Therefore, the class names of the tests are prefixed with a number in order to
            sort them correctly"""
        classes = []
        for cls_ in self.get_subsubclasses_for(self.__class__):
            if hasattr(cls_, "do") and callable(getattr(cls_, "do")):
                classes.append(cls_)
       
        classes.sort(self.__lt__, None, True)
        
        # For all of the proxies run all tests, in the test order, one proxy at a time.
        tests_run = 0
        test_phases_run = 0
        tests_skipped = 0
        for px in self.proxies:
            namelen = 0
            onlywips = False
            for cls_ in classes:
                if len(cls_.__name__) > namelen:
                    namelen = len(cls_.__name__)
                if hasattr(cls_, "wip"):
                    onlywips = True
            for cls_ in classes:
                testobject = cls_(proxy=px, parent=self)  # Create a test object
                testobject.superuser = self.superuser  # Give the test object an easy handle to the superuser
                testobject.set_proxy(px)
                if hasattr(cls_, "do") and callable(getattr(cls_, "do")):
                    fmt = "[%%%ds] %%s as %%s" % (namelen + 1)
                    doc = cls_.__doc__
                    if doc:
                        doc = doc.rstrip('.')  # Remove any final dots
                    skip = False
                    if testobject.skip:
                        doc = " TEST SKIPPED"
                        skip = True
                    if onlywips and not hasattr(cls_, "wip"):
                        # doc = " TEST NOT WORK IN PROGRESS"
                        doc = None
                        skip = True

                    proxyname = px.username()

                    # Inject a test info string to the test which can be used for logging or e.g. setting the description of created memberships

                    if not skip:
                        testobject.testphase = 0

                        while testobject.testphase < len(testobject.phaseinfo):
                            if not proxyname and testobject.testphase > 0:
                                break
                            if doc:
                                print datetime.datetime.now(), fmt % (cls_.__name__, doc, proxyname), testobject.phaseinfo[testobject.testphase]
                            if px.username():
                                testobject.testinfo = cls_.__name__ + " by " + proxyname
                            else:
                                testobject.testinfo = cls_.__name__ + " by Nobody"
                            testobject.prepare_test()  # Prepare
                            try:
                                testobject.do()  # Run the test phase
                            finally:
                                testobject.cleanup_test()  # Cleanup
                            testobject.testphase += 1
                            test_phases_run += 1
                        tests_run += 1
                    else:
                        tests_skipped += 1
                else:
                    pass
                    # print "No do() method in ", cls_
            print "==============="
        print "Tests run=%d, phases=%d, skipped=%d" % (tests_run, test_phases_run, tests_skipped)

    def function(self):
        return self.proxy.last_function

    def assertnotindict(self, value, items):
        """ Asserts that 'value' is a RPCC Attribute dictionary and that it does not contain the items given in the list 'items'"""
        assert type(value) is rpcc_client.AttrDict, "%s response is not a RPCC attribute dictionary, it is a %s" % (self.function(), type(value))

        for item in items:
            assert item not in value, "%s returned by %s" % (item, self.function())

    def assertindict(self, value, items, optional=[], exact=True):
        """ Asserts that 'value' is a RPCC Attribute dictionary and that it contains exactly the items given in the list 'items'
            To make the test more lenient and allow more items, set 'exact' to False"""
        assert type(value) is rpcc_client.AttrDict, "%s response is not a RPCC attribute dictionary, it is a %s" % (self.function(), type(value))
        
        minval = 0
        for item in items:
            if not item.startswith('_'):
                minval += 1
        if exact:
            maxval = minval + len(optional)
            if "_remove_nulls" in items:
                minval = 0
            if(len(value) < minval or len(value) > maxval):
                pprint.pprint(value)
                pprint.pprint(items)
            assert len(value) >= minval and len(value) <= maxval, "%s returns %d items, should be between %d and %d" % (self.function(), len(value), minval, maxval)
        else:
            assert len(value) >= minval, "%s returns %d items, should be at least %d" % (self.function(), len(value), minval)
        
        if "_remove_nulls" not in items:
            for item in items:
                if item.startswith('_'):
                    continue
                assert item in value, "Mandatory %s not returned by %s" % (item, self.function())

        if(exact):
            for item in value:
                assert item in items or item in optional, "Item %s returned by %s but should not be" % (item, self.function())

    def assertinlist(self, value, items, exact="True"):
        """ Asserts that 'value' is a list and that the values given in 'items' is in the list. If 'exact' is True, it is also checked that
            the length of the list is exactly the length of the 'items' list, or larger if 'eact' is False."""
        assert type(value) is list, "%s response is not a list" % (self.function())
        if exact:
            assert len(value) == len(items), "%s returns %d items, should be %d" % (self.function(), len(value), len(items))
        else:
            assert len(value) >= len(items), "%s returns %d items, should be %d" % (self.function(), len(value), len(items))

        for item in items:
            assert item in value, "%s not returned by %s" % (item, self.function())

    def assert_expected_data(self, data, expected):
        """ Assert that the given data is what is expected, recursively for lists and dicts"""
        # print " Asserting that:"
        # pprint.pprint(data)
        # print "IS"
        # pprint.pprint(expected)

        if type(expected) is list:
            assert type(data) is list, "Data type is not a list"
            for i in range(len(expected)):
                self.assert_expected_data(data[i], expected[i])
            return
        if type(expected) is dict:
            for k, v in expected.iteritems():
                # print "DICT assertion, k=",k, "v=",v, "data=",data[k]
                if type(v) is type(rpcc_client.AttrDict()):
                    assert type(data[k]) is type(rpcc_client.AttrDict()), "Data type for key '%s' is not a rpcc_client.AttrDict" % (k)
                    self.assert_expected_data(data[k], v)
                if type(v) is dict:
                    # pprint.pprint(data[k])
                    assert (type(data[k]) is dict or
                            type(data[k]) is type(rpcc_client.AttrDict())), "Data type for key '%s' is not a dict" % (k)
                    self.assert_expected_data(data[k], v)
                    continue
                if type(v) is list:
                    assert type(data[k]) is list, "Data type for key '%s' is not a list" % (k)
                    for i in range(len(v)):
                        # print "We have:"
                        # pprint.pprint(data[k][i])
                        # print "We expect"
                        # pprint.pprint(v[i])
                        self.assert_expected_data(data[k][i], v[i])
                    continue

                assert type(data[k]) is not dict, "Data type for key %s is a dict but is not expected to"
                assert type(data[k]) is not list, "Data type for key %s is a list but is not expected to"
                assert data[k] == v, "Data for key %s is %s, expected=%s" % (k, data[k], v)
                continue
            return
        assert data == expected, "Data is: %s expected: %s" % (repr(data), repr(expected))

    def assert_within_time(self, data, kind="db", key="last_change",):
        t = data[key]
        tb4 = self.times_before[kind][:19]
        taft = self.times_after[kind][:19]
        assert t >= tb4 and t <= taft, "Wrong %s time: %s, should be between %s and %s" % (key, t, tb4, taft)

    def assert_not_within_time(self, data, kind="db", key="last_change"):
        t = data[key]
        tb4 = self.times_before[kind][:19]
        taft = self.times_after[kind][:19]
        assert not (t >= tb4 and t <= taft), "Wrong %s time: %s, should not be between %s and %s" % (key, t, tb4, taft)
   
    def get_subsubclasses_for(self, klass):
        """ Returns a list of all subclasses to 'klass', recursively"""
        subclasses = []

        for cls in klass.__subclasses__():
            subclasses.append(cls)

            if len(cls.__subclasses__()) > 0:
                subclasses.extend(self.get_subsubclasses_for(cls))

        return subclasses

    def __lt__(self, a, b):
        """ Compares the names of self and other. This operator is used by the sorting function, specifically to sort the list of subclasses to order the
            tests."""
        if a.__name__ == b.__name__:
                return 0
        ret = a.__name__ < b.__name__
        if ret:
            return 1
        return -1
        # return a.__name__ < b.__name__

    def suffice_privs(self, sufficient_privs=None):
        """ Returns the given expected privileges or, if None the expected privileges of the current test object"""
        # print "Expected_privs=",sufficient_privs
        # print "self.Expected_privs=",self.sufficient_privs
        if sufficient_privs is None:
            return self.sufficient_privs
        return sufficient_privs

    def expect_access(self, expected_access=None):
        """ Returns the given expected access or, if None the expected access of the current test object"""
        if expected_access is None:
            return self.expected_access
        return expected_access
        
    def expect_admin(self, expected_admin=None):
        """ Returns whether we expect the proxy to be logged in as /admin or not. The method is used by expect_exception below"""
        if expected_admin is None:
            return self.expected_admin
        return expected_admin

    def expect_loa(self, expected_loa=None):
        """ Returns whether we expect th proxy to have a LoA level >1 """
        if expected_loa is None:
            return self.expected_loa
        return expected_loa
    
    def expect_authenticated(self, expected_authenticated=None):
        """ Returns whether we expect the proxy to be logged in or not. The method is used by expect_exception below"""
        if expected_authenticated is None:
            return self.expected_authenticated
        return expected_authenticated
    
    def expect_exception_name(self, expected_exception_name=None):
        """ Returns the expected exception name, if any"""
        if expected_exception_name is None:
            return self.expected_exception_name
        return expected_exception_name
    
    def get_possible_exception_name(self, possible_exception_name=None):
        """ Returns the possible exception name, if any"""
        if possible_exception_name is None:
            return self.possible_exception_name
        return possible_exception_name

    def expect_exception(self, expected_access=None,
                         sufficient_privs=None,
                         expected_admin=None,
                         expected_authenticated=None,
                         expected_loa=None,
                         expected_exception_name=None,
                         possible_exception_name=None):
        """ Gathers the expected access, privileges and /admin-login and checks whether the expectations are met by the actual
            status of the current proxy. The method returns a tuple consisting of a boolean and a list of RPCCError exception names. I
            If the boolean is true, we will expect that a certain RPCC operation will fail with one of the errors found in the list of exception names.
            The method is used within AssertRPCCError below and possibly also within the tests to determine wether a specific test should fail or not.
            The expectation is normally derived from the instance variables in the test class but may be overridden by specifying them
            in the parameter list.
            The expectations are evaluated in the order authentication, /admin, access and privileges. Whenever it is found that one expectation is not
            met, the evaluation stops and (True, [exception_name,...]) is returned"""

        # # Argh, this code has grown beyond all proportions and should be re-written from scratch....
        expected_access = self.expect_access(expected_access)
        sufficient_privs = self.suffice_privs(sufficient_privs)
        expected_admin = self.expect_admin(expected_admin)
        expected_authenticated = self.expect_authenticated(expected_authenticated)
        expected_loa = self.expect_loa(expected_loa)
        expected_exception_name = self.expect_exception_name(expected_exception_name)
        possible_exception_name = self.get_possible_exception_name(possible_exception_name)
        # pprint.pprint(expected_exception_name)

        errs = set()
        # If we are not authenticated:
        if not self.proxy._auth:
            # print "NOT AUTHENTICATED"
            if sufficient_privs:
                errs.add("RuntimeError::AccessDenied")
            if expected_exception_name:
                errs.add(expected_exception_name)
                return(expected_authenticated or sufficient_privs, errs, possible_exception_name)
            errs.add("RuntimeError::AccessDenied")
            return(expected_authenticated or sufficient_privs, errs, possible_exception_name)

        if expected_admin and not self.proxy._auth.endswith("/admin"):
            errs.add("RuntimeError::AccessDenied")
            errs.add("AccessError::AccessErrorInAuthenticationSystemError")
            return(True, errs, possible_exception_name)

        # Check if we have access rights
        exception_expected = True
        for access in expected_access:
            if access in self.actual_access and self.actual_access[access]:
                # print "ACCESS RIGHTS ",access, " FOUND"
                exception_expected = False

        # If we hadn't the needed access rights, no need to check privs.
        if exception_expected or expected_exception_name:
            if expected_exception_name:
                return(True, ("AccessError", expected_exception_name), possible_exception_name)
            return(True, ("RuntimeError::AccessDenied",), possible_exception_name)

        if exception_expected:
            if possible_exception_name:
                return(True, ("AccessError", possible_exception_name), possible_exception_name)
            return(True, ("AccessError",), possible_exception_name)

        # If we do not expect any needed privs, just check for LoA  and we're done
        if not sufficient_privs:
            # print "NO EXPECTED PRIVS"
            if not expected_loa:
                return(False, None, possible_exception_name)
            # print "LOA EXPECTED"
            if self.actual_loa > "1":
                return(False, None, possible_exception_name)
            return (True, ("AccessError::LoA2Required",), possible_exception_name)

        # Check that we have one of the needed priv
        errs.add("RuntimeError::AccessDenied")
        for priv in sufficient_privs:
            if priv == "search_with_regexp":
                errs.add("AccessError")
            # print "LOOKING FOR ",priv," IN ",self.actual_privs
            if priv in self.actual_privs:
                # print "PRIVILEGE ",priv, " FOUND"
                if not expected_loa or self.actual_loa > "1":
                    # print "No exception expected"
                    return(False, None, possible_exception_name)
                else:
                    # print "Expect LOA exception"
                    return (True, ("AccessError::LoA2Required",), possible_exception_name)
        return(True, errs, possible_exception_name)

  
class AssertRPCCError(object):
        """ This class implements a simple context manager in which the tests wraps operations using the python 'with' statement.
        Given a RPCCError eception name and a boolean to tell whether we expect the operation to fail or not, the method 
        will silently swallow operations that behave as expected. For operations that do not behave as expected, the raised exception
        is sent through or an Exception is raised to signal that an expected exception did NOT occur.
        """
        def __init__(self, name, expected=True):
            self.exception_name = name
            self.exception_expected = expected

        def __enter__(self):
            return True
        
        def __exit__(self, ex_type, value, traceback):
            if self.exception_expected:
                if not ex_type:
                    raise Exception("RPCCError %s expected", self.exception_name)
                if ex_type == rpcc_client.RPCCError and value[0]["name"] == self.exception_name:
                    return True
                return False
            else:
                if not ex_type:
                    return True
                return False

           
class AllowRPCCError(object):
        """ This class implements a simple context manager in which the tests wraps operations using the python 'with' statement.
        Given a RPCCError exception name the method 
        will silently swallow exception of the staring with the given name. 
        """
        def __init__(self, name):
            self.exception_name = name

        def __enter__(self):
            return True
        
        def __exit__(self, ex_type, value, traceback):
            if not ex_type:
                return True
            if ex_type == rpcc_client.RPCCError and value[0]["name"].startswith(self.exception_name):
                return True
            return False
          
            
class AssertAccessError(object):
        """ This class implements an elaboration of AssertRPCCError above. 
            It evaluates the expected behavior using the expect_exception method of the test using this class.
        """
        def __init__(self, thetest, expected_admin=None,
                     expected_access=None,
                     sufficient_privs=None,
                     expected_authenticated=None,
                     expected_loa=None,
                     expected_exception_name=None,
                     possible_exception_name=None,
                     never_fail=None):
            self.expected_access = thetest.expect_access(expected_access)
            self.sufficient_privs = thetest.suffice_privs(sufficient_privs)
            self.expected_admin = thetest.expect_admin(expected_admin)
            self.expected_authenticated = thetest.expect_authenticated(expected_authenticated)
            self.expected_loa = thetest.expect_loa(expected_loa)
            self.expected_exception_name = thetest.expect_exception_name(expected_exception_name)
            self.possible_exception_name = thetest.get_possible_exception_name(possible_exception_name)
            self.never_fail = never_fail
            # pprint.pprint(self.expected_exception_name)
            self.thetest = thetest

            (self.exception_expected, self.exception_names, self.possible_exception) = thetest.expect_exception(expected_access, 
                                                                                                                sufficient_privs, 
                                                                                                                expected_admin, 
                                                                                                                expected_authenticated,
                                                                                                                expected_exception_name,
                                                                                                                possible_exception_name)
            # pprint.pprint(self.exception_names)
            # If we now expect the superuser to fail, we have probably overlooked something
            # unless we explicitly indicated that the test should fail even as superuser
            # pprint.pprint(thetest.superuser_test_may_fail)
            if self.exception_expected and not self.thetest.superuser_test_may_fail:
                assert self.thetest.proxy != self.thetest.superuser, "TEST ERROR! Superuser access expected to fail"
            
            # print "Exceptions expected=",(self.exception_expected, self.exception_names)

        def __enter__(self):
            return True

        def __exit__(self, ex_type, value, traceback):
            if self.never_fail:
                return True
            if self.exception_expected:
                if not ex_type:
                    print "Expected exceptions", self.exception_names, " not raised"
                    print "Sufficient privs=", self.sufficient_privs, "Actual privs=", self.thetest.actual_privs
                    print "Expected access=", self.expected_access, "Actual access=", self.thetest.actual_access
                    print "Expected loa=", self.expected_loa, "Actual loa=", self.thetest.actual_loa
                    print "Expected admin=", self.expected_admin, "Actual admin=", self.thetest.actual_admin
                    raise Exception("RPCCError %s expected", self.exception_names)

                if ex_type == rpcc_client.RPCCError and (value[0]["name"] in self.exception_names or value[0]["name"] == self.possible_exception):
                    return True
                print "An unexpected exception was raised instead of another expected exception:"
                print "Sufficient privs=", self.sufficient_privs, "Actual privs=", self.thetest.actual_privs
                print "Expected access=", self.expected_access, "Actual access=", self.thetest.actual_access
                print "Expected loa=", self.expected_loa, "Actual loa=", self.thetest.actual_loa
                print "Expected admin=", self.expected_admin, "Actual admin=", self.thetest.actual_admin
                print "Expected exceptions were:", self.exception_names
                print "Raised exception is:", ex_type
                return False

            else:
                if not ex_type:
                    return True
                if ex_type == rpcc_client.RPCCError and value[0]["name"] == self.possible_exception:
                    return True
                print "Unexpected exception raised though no exception was expected:"
                print "Sufficient privs=", self.sufficient_privs, "Actual privs=", self.thetest.actual_privs
                print "Expected access=", self.expected_access, "Actual access=", self.thetest.actual_access
                print "Expected loa=", self.expected_loa, "Actual loa=", self.thetest.actual_loa
                print "Expected admin=", self.expected_admin, "Actual admin=", self.thetest.actual_admin
                print "Raised exception is:", ex_type
                return False
        
        
class UnAuthTests(MyTests):
    """ Superclass for tests that do not require any access rights"""


class AuthTests(MyTests):
    """ Superclass for tests that are expected to work for anyone who is authenticated"""
    expected_authenticated = True
    expected_access = ["anyauth"]
    pass


class FloorAdminTests(AuthTests):
    sufficient_privs = ["write_all_hosts", "write_all_rooms"]
   
    
class ServiceDeskTests(AuthTests):
    sufficient_privs = ["write_all_host_classes", 
                        "write_all_buildings",
                        "write_all_groups",
                        "write_all_optionspaces"]
    
    
class NetworkAdminTests(AuthTests):
    sufficient_privs = ["write_all_subnetworks",
                        "write_all_networks",
                        "write_all_global_options"
                        "write_all_pools",
                        "write_all_pool_ranges"]
    
    
class SuperUserTests(AuthTests):
    """ Superclass for tests that are expected to work for anyone who is logged as a superUser"""
    expected_access = ["superusers"]


class MustFailTests(AuthTests):
    """ Superclass for tests that should always fail"""
    sufficient_privs = []
    expected_access = ["OnlyGodHimselfOrAnyoneWithTheSameAuthorityWillHaveThisAuthority"]
    expected_admin = True
