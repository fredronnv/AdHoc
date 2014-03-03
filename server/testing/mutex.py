#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" RPCC API test suite
    This suite tests the different mutex_ functions in RPCC"""
from framework import *
from util import *


class MutexTests(AuthTests):
    mandatory_keys = ["held", "last_change"]
    optional_keys = ["access_group", "current_owner", "stolen"]

    static_mandatory_keys = ["id"]
    static_optional_keys = ["access_group"]

    result_mandatory = ["acquired", "current_owner", "last_change", "stolen"]
    result_optional = []

    watchdog_mandatory_keys = ["running"]
    watchdog_optional_keys = ["err_minutes", "warn_minutes"]

    def assert_static_keys(self, md):
        self.assertindict(md, self.static_mandatory_keys, optional=self.static_optional_keys)

    def assert_watchdog_keys(self, wdd):
        self.assertindict(wdd, self.watchdog_mandatory_keys, optional=self.watchdog_optional_keys)

    def assert_mutex_keys(self, md):
        self.assertindict(md, self.mandatory_keys, optional=self.optional_keys)

    def assert_mutex_result_keys(self, rd):
        self.assertindict(rd, self.result_mandatory, optional=self.result_optional)

    def prepare_test(self):
        """ prepare_test is always run by the framework before the do() method"""
        super(MutexTests, self).prepare_test()
        username = self.proxy.username()
        if not username:
                self.superuser_test_may_fail = True
                self.expected_exception_name = "AccessError::MutexAccessDenied"

        mutex_list = self.superuser.mutex_list()

        self.mutexes_tested = 0
        self.mutexes_acquired = 0
        self.mutexes_held_before = 0
        self.mutexes_free = 0

        # print mutex_list
        for mutex in mutex_list:
            self.testmutex = mutex["id"]
            try:
                md = self.superuser.mutex_get_status(self.testmutex)
            except:
                continue
            if "access_group" in md and md["access_group"]:
                continue
            self.held_before = md["held"]
            self.mutexes_free += 1
            if self.held_before:
                self.mutexes_held_before += 1
            else:
                break

    def cleanup_test(self):
        """ cleanup_test is always run by the framework after the do() method"""
        super(MutexTests, self).cleanup_test()
        assert self.mutexes_free > 0, "No free mutexes found to be tested"
        if self.mutexes_tested:
            assert self.mutexes_acquired > 0, "No mutexes were acquired"
        pass

    def assume_superusership(self, g=None):
        if not hasattr(self, "sumships"):
            self.sumships = []
        if g == None:
            g = self.admingroup
        if g:
            try:
                self.sumships.append(self.superuser.membership_create(g, self.superuser.username(), {}))
            except rpcc_client.RPCCError as e:
                if e[0]["name"] == "ValueError::MembershipWouldOverlap":
                    pass
                else:
                    raise

    def relinguish_superusership(self):
        if hasattr(self, "sumships"):
            if len(self.sumships):
                sumship = self.sumships.pop()
                self.superuser.membership_destroy(sumship)
        # print "   Finished phase", self.testphase

    def get_mutex_access_group(self):
        """ Run the only guaranteed way th get hold of which access group a mutex has."""

        mutex_list = self.superuser.mutex_list()

        for m in mutex_list:
            if m["id"] == self.testmutex:
                if "access_group" in m:
                    return m["access_group"]
                return None
        assert False, "Test mutex not found while loking for access group"

    def release_mutex(self):
        g = self.get_mutex_access_group()
        if g:
            self.assume_superusership(g)
        try:
            self.superuser.mutex_acquire(self.testmutex, "PDBAPI mutex_releaser", 0)  # Steal it if necessary
            self.superuser.mutex_release(self.testmutex)  # Then release
        except:
                pass
        self.relinguish_superusership()

    def remove_access_group(self):
        g = self.get_mutex_access_group()
        if g:
            self.assume_superusership(g)
        try:
            self.superuser.mutex_acquire(self.testmutex, "PDBAPI access_group_remover", 0)
            self.superuser.mutex_unset_access_group(self.testmutex)
            self.superuser.mutex_release(self.testmutex)  # Then release
        except:
            pass
        self.relinguish_superusership()


class MutexAdminTests(MutexTests):  # GroupTests):
    do_as_group_member_test = True
    phaseinfo = ["without mutex having access group",
                 "while being member of the mutex' access group",
                 "while not being member of the mutex' access group"]

    superuser_test_may_fail = True
    
    def prepare_test(self):
        """ Method to be called to prepare a test as an admin user."""
        super(MutexAdminTests, self).prepare_test()
        # print "   Preparing phase",self.testphase," for mutex", self.testmutex
        username = self.proxy.username()
        self.admingroup = None

#         if self.testphase > 0:
#             self.admingroup = None
#             if not username and self.testphase == 1:
#                 print "As access group member test is not applicable as unauthenticated"
#                 return
#             self.admingroup = self.makeGroup("s_pdbapitest_guinea_pig_mutex_group")  # Make an admin group
#             pxmship = None
#             sumship = None
# 
#             # self.superuser.group_set_admin_group(self.testgroup, self.admingroup)
#             if self.testphase == 1:
#                 pxmship = self.superuser.membership_create(self.admingroup, username, {})
#             if self.superuser != self.proxy or self.testphase != 1:
#                 sumship = self.superuser.membership_create(self.admingroup, self.superuser.username(), {})
#             self.superuser.mutex_acquire(self.testmutex, "PDBAPI superuser", None)
#             self.superuser.mutex_set_access_group(self.testmutex, self.admingroup)
#             self.superuser.mutex_release(self.testmutex)
#             # Phases 0 and 1 should succeed if authenticated
# 
#             self.sufficient_privs = []
#             self.expected_access = ["anyauth"]
#             self.expected_admin = False
#             self.superuser_test_may_fail = True
#             # Phase 2 should fail
#             if self.testphase == 2:
#                 if sumship:
#                     self.superuser.membership_destroy(sumship)
#                 if pxmship:
#                     self.superuser.membership_destroy(pxmship)
#                 self.expected_exception_name = "AccessError::MutexAccessDenied"
#         # print "   Prepared phase",self.testphase," for mutex", self.testmutex

    def cleanup_test(self):
        # print "   Finishing phase", self.testphase
        if self.testphase > 0:
            try:
                self.superuser.membership_create(self.admingroup, self.superuser.username(), {})
            except rpcc_client.RPCCError as e:
                if e[0]["name"] == "ValueError::MembershipWouldOverlap":
                    pass
                else:
                    raise

            self.superuser.mutex_acquire(self.testmutex, "PDBAPI superuser", None)
            self.superuser.mutex_unset_access_group(self.testmutex)
            self.superuser.mutex_release(self.testmutex)
            if self.testphase > 0 and self.admingroup:
                self.teardownGroup(self.admingroup)

        super(MutexAdminTests, self).cleanup_test()


    def setupCollection(self):
        """ Sets up a test collection."""

        self.assume_superusership()
        rd = self.superuser.mutex_acquire(self.testmutex, "PDBAPI setup", 2)
        assert rd["acquired"], "Failed to acquire mutex hile creating collection"
        try:
            self.testcollection = "rpccapitest"
            self.superuser.mutex_collection_create(self.testmutex, self.testcollection)
            # print "Created collection %s in %s"%(self.testcollection, self.testmutex)
        except rpcc_client.RPCCError as e:
            if e[0]["name"] == u"ValueError::MutexCollectionAlreadyExists":
                pass
            else:
                raise
        self.superuser.mutex_release(self.testmutex)
        self.relinguish_superusership()

    def teardownCollection(self):
        self.assume_superusership()
        try:
            self.superuser.mutex_acquire(self.testmutex, "PDBAPI cleaner", 0)
            self.superuser.mutex_collection_destroy(self.testmutex, self.testcollection)
        except:
            pass
        self.relinguish_superusership()

    def release_mutex(self):
        self.assume_superusership()
        super(MutexAdminTests, self).release_mutex()
        self.relinguish_superusership()

    def setupVariable(self, value=None):
        """ Sets up a test variable."""

        self.assume_superusership()
        rd = self.superuser.mutex_acquire(self.testmutex, "PDBAPI setup", 2)
        assert rd["acquired"], "Failed to acquire mutex hile creating variable"
        try:
            self.testvariable = "rpccapitest"
            self.superuser.mutex_variable_create(self.testmutex, self.testvariable)
            # print "Created variable %s in %s"%(self.testvariable, self.testmutex)
        except rpcc_client.RPCCError as e:
            if e[0]["name"] == u"ValueError::MutexVariableAlreadyExists":
                pass
            else:
                raise
        if value:
            self.superuser.mutex_variable_set(self.testmutex, self.testvariable, value)
        self.superuser.mutex_release(self.testmutex)
        self.relinguish_superusership()

    def teardownVariable(self):
        self.assume_superusership()
        try:
            self.superuser.mutex_acquire(self.testmutex, "PDBAPI cleaner", 0)
            self.superuser.mutex_variable_destroy(self.testmutex, self.testvariable)
        except:
            pass
        self.relinguish_superusership()

    def setupWatchdog(self, value=None):
        """ Sets up a test watchdog."""

        self.assume_superusership()
        rd = self.superuser.mutex_acquire(self.testmutex, "PDBAPI setup", 0)
        assert rd["acquired"], "Failed to acquire mutex while creating watchdog"
        try:
            self.testwatchdog = "rpccapitest"
            self.superuser.mutex_watchdog_create(self.testmutex, self.testwatchdog)
            # print "Created watchdog %s in %s"%(self.testwatchdog, self.testmutex)
        except rpcc_client.RPCCError as e:
            if e[0]["name"] == u"ValueError::MutexWatchdogAlreadyExists":
                pass
            else:
                raise
        if value:
            self.superuser.mutex_watchdog_set(self.testmutex, self.testwatchdog, value[0], value[1])
        self.superuser.mutex_release(self.testmutex)
        self.relinguish_superusership()

    def teardownWatchdog(self):
        self.assume_superusership()
        try:
            self.superuser.mutex_acquire(self.testmutex, "PDBAPI cleaner", 0)
            self.superuser.mutex_watchdog_destroy(self.testmutex, self.testwatchdog)
        except:
            pass
        self.relinguish_superusership()



class T11000_MutexList(MutexTests, SuperUserTests):
    """ Test mutex_list."""

    # Preparing is unnecessary here
    def prepare_test(self):
        pass
    
    def cleanup_test(self):
        pass
    
    def do(self):
        with AssertAccessError(self):
            mutex_list = self.proxy.mutex_list()
            assert type(mutex_list) is list, "Mutex list is not a list"
            for m in mutex_list:
                self.assert_static_keys(m)
                assert type(m["id"]) is unicode, "Mutex is not a unicode string"


class T11010_MutexGetStatus(MutexTests):
    """ Test mutex_get_status."""

    mandatory_keys = ["held", "last_change"]
    optional_keys = ["access_group", "current_owner", "stolen"]

    def do(self):
        mutex_list = self.superuser.mutex_list()
        with AssertAccessError(self):
            for m in mutex_list:
                md = self.proxy.mutex_get_status(m["id"])
                self.assert_mutex_keys(md)


class T11020_MutexAcquireRelease(MutexAdminTests):
    """ Test mutex_acquire and release."""

    def do(self):
        with AssertAccessError(self):
                    pubname = "PDBAPI tester %s" % (self.proxy.username())
                    self.times_before = self.superuser.session_get_time()
                    rd = self.proxy.mutex_acquire(self.testmutex, pubname, None)
                    self.mutexes_tested += 1
                    self.times_after = self.superuser.session_get_time()
                    self.assert_mutex_result_keys(rd)
                    # print "rd="
                    # pprint.pprint(rd)
                    acquired = rd["acquired"]
                    # print "acq=",acquired

                    expected_data = {
                                     "acquired": not self.held_before,
                                     "stolen": False}

                    if acquired:
                        self.mutexes_acquired += 1
                        # print "self.acq=",self.mutexes_acquired
                        expected_data["current_owner"] = pubname
                        self.assert_within_time(rd)
                    else:
                        self.assert_not_within_time(rd)

                    self.assert_expected_data(rd, expected_data)

                    md = self.superuser.mutex_get_status(self.testmutex)
                    self.assert_mutex_keys(md)

                    expected_data = {
                                     "held": True
                                    }
                    if acquired:
                        expected_data["current_owner"] = pubname
                        self.assert_within_time(md)
                    else:
                        self.assert_not_within_time(md)

                    self.assert_expected_data(md, expected_data)

                    self.times_before = self.superuser.session_get_time()
                    if not acquired:
                        with AssertRPCCError("ValueError::MutexNotHeld", True):
                            rd = self.proxy.mutex_release(self.testmutex)
                    else:
                        rd = self.proxy.mutex_release(self.testmutex)
                    self.times_after = self.superuser.session_get_time()

                    md = self.superuser.mutex_get_status(self.testmutex)
                    self.assert_mutex_keys(md)

                    expected_data = {
                                     "held": self.held_before,
                                    }
                    self.assert_expected_data(md, expected_data)
                    if acquired:
                        self.assert_within_time(md)
                    else:
                        self.assert_not_within_time(md)


class T11030_MutexCollectionCreate(MutexAdminTests):
    """ Test mutex_collection_create."""

    def do(self):

            self.testcollection = "rpccapitest"
            try:
                with AssertAccessError(self):
                    rd = self.proxy.mutex_acquire(self.testmutex, "PDBAPI tester", None)
                    assert rd["acquired"], "Failed to acquire test mutex"

                    self.proxy.mutex_collection_create(self.testmutex, self.testcollection)
                    collections = self.proxy.mutex_list_collections(self.testmutex)

                    assert type(collections) is list, "Mutex collections is not a list"
                    assert self.testcollection in collections, "Created collection not found"
                    self.proxy.mutex_collection_destroy(self.testmutex, self.testcollection)
                    collections = self.proxy.mutex_list_collections(self.testmutex)
                    assert self.testcollection not in collections, "Destroying test collection failed"
                    self.proxy.mutex_release(self.testmutex)

            finally:
                self.teardownCollection()
                self.release_mutex()


class T11030_MutexListCollections(MutexAdminTests):
    """ Test mutex_collection_list."""

    def do(self):

        m = self.testmutex
        try:
            self.setupCollection()

            with AssertAccessError(self):
                rd = self.proxy.mutex_acquire(m, "PDBAPI tester", None)
                assert rd["acquired"], "Failed to acquire test mutex"
                collections = self.proxy.mutex_list_collections(m)
                assert type(collections) is list, "Mutex collections is not a list"
                for collection in collections:
                    assert type(collection) is unicode, "Returned collection is not of type unicode"
                assert self.testcollection in collections, "Test collection not found in list"
                # print "Destroying mutex collection rpccapitest for mutex "+m
                self.proxy.mutex_collection_destroy(m, self.testcollection)
                collections = self.proxy.mutex_list_collections(m)
                assert self.testcollection not in collections, "Destroying test collection failed"
                self.proxy.mutex_release(m)

        finally:
            self.teardownCollection()
            self.release_mutex()


class T11030_MutexCollectionDestroy(MutexAdminTests):
    """ Test mutex_collection_destroy."""

    def do(self):

        m = self.testmutex
        try:
            self.setupCollection()

            with AssertAccessError(self):
                rd = self.proxy.mutex_acquire(m, "PDBAPI tester", None)
                assert rd["acquired"], "Failed to acquire test mutex"
                # print "Destroying mutex collection rpccapitest for mutex "+m
                self.proxy.mutex_collection_destroy(m, self.testcollection)
                collections = self.proxy.mutex_list_collections(m)
                assert self.testcollection not in collections, "Destroying test collection failed"
                self.proxy.mutex_release(m)
        finally:
            self.teardownCollection()
            self.release_mutex()


class T11040_MutexCollectionAdd(MutexAdminTests):
    """ Test mutex_collection_add."""

    def do(self):
        m = self.testmutex
        try:
            self.setupCollection()

            with AssertAccessError(self):
                rd = self.proxy.mutex_acquire(m, "PDBAPI tester", None)
                assert rd["acquired"], "Failed to acquire test mutex"
                valuelist = []
                for n in range(1, 15):
                    valuelist.append("Collectionvalue_%d" % (n))

                for val in valuelist:
                    self.proxy.mutex_collection_add(m, self.testcollection, val)

                self.proxy.mutex_release(m)

                rd = self.proxy.mutex_acquire(m, "PDBAPI tester", None)

                assert rd["acquired"], "Failed to acquire test mutex"
                read_values = self.proxy.mutex_collection_get(m, self.testcollection)
                assert len(read_values) == len(valuelist), "Not same length of written and read valued in mutex collection"
                for val in valuelist:
                    assert val in read_values, "Re-read value from collection missing:%s" % (val)
                self.proxy.mutex_release(m)
        finally:
            self.teardownCollection()
            self.release_mutex()


class T11040_MutexCollectionGet(MutexAdminTests):
    """ Test mutex_collection_get."""

    def do(self):
        m = self.testmutex
        try:
            self.setupCollection()
            self.assume_superusership()
            rd = self.superuser.mutex_acquire(m, "PDBAPI setup", 2)
            assert rd["acquired"], "Failed to acquire test mutex"
            valuelist = []
            for n in range(1, 15):
                valuelist.append("Collectionvalue_%d" % (n))

            for val in valuelist:
                self.superuser.mutex_collection_add(m, self.testcollection, val)
            self.superuser.mutex_release(m)
            self.relinguish_superusership()

            with AssertAccessError(self):

                rd = self.proxy.mutex_acquire(m, "PDBAPI tester", None)
                assert rd["acquired"], "Failed to acquire test mutex"
                read_values = self.proxy.mutex_collection_get(m, self.testcollection)
                assert len(read_values) == len(valuelist), "Not same length of written and read valued in mutex collection"
                for val in valuelist:
                    assert val in read_values, "Re-read value from collection missing:%s" % (val)

                self.proxy.mutex_release(m)
        finally:
            self.teardownCollection()
            self.release_mutex()


class T11050_MutexCollectionRemove(MutexAdminTests):
    """ Test mutex_collection_remove."""

    def do(self):
        m = self.testmutex
        try:
            self.setupCollection()
            self.assume_superusership()
            rd = self.superuser.mutex_acquire(m, "PDBAPI setup", 2)
            assert rd["acquired"], "Failed to acquire test mutex"
            valuelist = []
            for n in range(1, 15):
                valuelist.append("Collectionvalue_%d" % (n))

            for val in valuelist:
                self.superuser.mutex_collection_add(m, self.testcollection, val)
            self.superuser.mutex_release(m)
            self.relinguish_superusership()

            with AssertAccessError(self):

                rd = self.proxy.mutex_acquire(m, "PDBAPI tester", None)
                assert rd["acquired"], "Failed to acquire test mutex"
                for val in valuelist:
                    self.proxy.mutex_collection_remove(m, self.testcollection, val)

                read = self.proxy.mutex_collection_get(m, self.testcollection)
                assert len(read) == 0, "mutex_collection_remove failed"

                self.proxy.mutex_release(m)
        finally:
            self.teardownCollection()
            self.release_mutex()


class T11060_MutexVariableCreate(MutexAdminTests):
    """ Test mutex_variable_create."""

    def do(self):

        self.testvariable = "rpccapitest"
        try:
            with AssertAccessError(self):
                rd = self.proxy.mutex_acquire(self.testmutex, "PDBAPI tester", None)

                assert rd["acquired"], "Failed to acquire test mutex"
                self.proxy.mutex_variable_create(self.testmutex, self.testvariable)
                variables = self.proxy.mutex_list_variables(self.testmutex)

                assert type(variables) is list, "Mutex variables is not a list"
                for variable in variables:
                    assert type(variable) is unicode, "Returned variable is not of type unicode"
                assert self.testvariable in variables, "Created variable not found"
                self.proxy.mutex_variable_destroy(self.testmutex, "rpccapitest")
                variables = self.proxy.mutex_list_variables(self.testmutex)
                for variable in variables:
                    assert variable is not "rpccapitest", "Destroying test variable failed"
                self.proxy.mutex_release(self.testmutex)
        finally:
            self.teardownVariable()
            self.release_mutex()


class T11070_MutexListVariables(MutexAdminTests):
    """ Test mutex_list_variables."""

    def do(self):
        m = self.testmutex
        try:
            self.setupVariable()
            with AssertAccessError(self):
                rd = self.proxy.mutex_acquire(m, "PDBAPI tester", None)
                assert rd["acquired"], "Failed to acquire test mutex"
                variables = self.proxy.mutex_list_variables(m)
                assert type(variables) is list, "Mutex variables is not a list"
                for variable in variables:
                    assert type(variable) is unicode, "Returned variable is not of type unicode"
                assert self.testvariable in variables, "Test variable not found in variable list"
                self.proxy.mutex_variable_destroy(self.testmutex, self.testvariable)
                variables = self.proxy.mutex_list_variables(m)
                assert self.testvariable not in variables, "Destroying test variable failed"
                self.proxy.mutex_release(m)
        finally:
            self.teardownVariable()
            self.release_mutex()


class T11080_MutexVariableDestroy(MutexAdminTests):
    """ Test mutex_variable_destroy."""

    def do(self):

        m = self.testmutex
        try:
            self.setupVariable()
            with AssertAccessError(self):
                rd = self.proxy.mutex_acquire(m, "PDBAPI tester", None)
                assert rd["acquired"], "Failed to acquire test mutex"
                # print "Destroying mutex variable rpccapitest for mutex "+m
                self.proxy.mutex_variable_destroy(m, self.testvariable)
                variables = self.proxy.mutex_list_variables(m)
                assert self.testvariable not in variables, "Destroying test variable failed"
                self.proxy.mutex_release(m)
        finally:
            self.teardownVariable()
            self.release_mutex()


class T11090_MutexVariableSet(MutexAdminTests):
    """ Test mutex_variable_set."""

    def do(self):

        m = self.testmutex
        try:
            self.setupVariable()
            with AssertAccessError(self):
                rd = self.proxy.mutex_acquire(m, "PDBAPI tester", None)
                assert rd["acquired"], "Failed to acquire test mutex"
                val = "Variablevalue_19"
                self.proxy.mutex_variable_set(m, self.testvariable, val)
                self.proxy.mutex_release(m)

                rd = self.proxy.mutex_acquire(m, "PDBAPI tester", None)
                assert rd["acquired"], "Failed to acquire test mutex"
                read_value = self.proxy.mutex_variable_get(m, self.testvariable)
                assert val == read_value, "Re-read value unexpected:%s" % (read_value)
                self.proxy.mutex_release(m)
        finally:
            self.teardownVariable()
            self.release_mutex()


class T11100_MutexVariableGet(MutexAdminTests):
    """ Test mutex_variable_get."""

    def do(self):

        m = self.testmutex
        try:
            val = "Variablevalue_11100"
            self.setupVariable(value=val)
            with AssertAccessError(self):
                rd = self.proxy.mutex_acquire(m, "PDBAPI tester", None)
                assert rd["acquired"], "Failed to acquire test mutex"
                read_value = self.proxy.mutex_variable_get(m, self.testvariable)
                assert val == read_value, "Re-read value unexpected:%s" % (read_value)
                self.proxy.mutex_release(m)
        finally:
            self.teardownVariable()
            self.release_mutex()


class T11110_MutexWatchdogCreate(MutexAdminTests):
    """ Test mutex_watchdog_create."""

    def do(self):
        self.testwatchdog = "rpccapitest"
        try:
            with AssertAccessError(self):
                rd = self.proxy.mutex_acquire(self.testmutex, "PDBAPI tester", None)

                assert rd["acquired"], "Failed to acquire test mutex"
                self.proxy.mutex_watchdog_create(self.testmutex, self.testwatchdog)
                watchdogs = self.proxy.mutex_list_watchdogs(self.testmutex)

                assert type(watchdogs) is list, "Mutex watchdogs is not a list"
                for watchdog in watchdogs:
                    assert type(watchdog) is unicode, "Returned watchdog is not of type unicode"
                assert self.testwatchdog in watchdogs, "Created watchdog not found"
                self.proxy.mutex_watchdog_destroy(self.testmutex, "rpccapitest")
                watchdogs = self.proxy.mutex_list_watchdogs(self.testmutex)
                for watchdog in watchdogs:
                    assert watchdog is not "rpccapitest", "Destroying test watchdog failed"
                self.proxy.mutex_release(self.testmutex)
        finally:
            self.teardownWatchdog()
            self.release_mutex()


class T11120_MutexListWatchdogs(MutexAdminTests):
    """ Test mutex_list_watchdogs."""

    def do(self):
        m = self.testmutex
        try:
            self.setupWatchdog()
            with AssertAccessError(self):
                rd = self.proxy.mutex_acquire(m, "PDBAPI tester", None)
                assert rd["acquired"], "Failed to acquire test mutex"
                watchdogs = self.proxy.mutex_list_watchdogs(m)
                assert type(watchdogs) is list, "Mutex watchdogs is not a list"
                for watchdog in watchdogs:
                    assert type(watchdog) is unicode, "Returned watchdog is not of type unicode"
                assert self.testwatchdog in watchdogs, "Test watchdog not found in watchdog list"
                self.proxy.mutex_watchdog_destroy(self.testmutex, self.testwatchdog)
                watchdogs = self.proxy.mutex_list_watchdogs(m)
                assert self.testwatchdog not in watchdogs, "Destroying test watchdog failed"
                self.proxy.mutex_release(m)
        finally:
            self.teardownWatchdog()
            self.release_mutex()


class T11130_MutexWatchdogDestroy(MutexAdminTests):
    """ Test mutex_watchdog_destroy."""

    def do(self):

        m = self.testmutex
        try:
            self.setupWatchdog()
            with AssertAccessError(self):
                rd = self.proxy.mutex_acquire(m, "PDBAPI tester", None)
                assert rd["acquired"], "Failed to acquire test mutex"
                # print "Destroying mutex variable rpccapitest for mutex "+m
                self.proxy.mutex_watchdog_destroy(m, self.testwatchdog)
                watchdogs = self.proxy.mutex_list_watchdogs(m)
                assert self.testwatchdog not in watchdogs, "Destroying test watchdog failed"
                self.proxy.mutex_release(m)
        finally:
            self.teardownWatchdog()
            self.release_mutex()


class T11140_MutexWatchdogSet(MutexAdminTests):
    """ Test mutex_watchdog_set."""

    def do(self):
        m = self.testmutex
        try:
            self.setupWatchdog()
            with AssertAccessError(self):
                rd = self.proxy.mutex_acquire(m, "PDBAPI tester", None)
                assert rd["acquired"], "Failed to acquire test mutex"
                self.proxy.mutex_watchdog_set(m, self.testwatchdog, 1, 2)
                self.proxy.mutex_release(m)

                rd = self.proxy.mutex_acquire(m, "PDBAPI tester", None)
                assert rd["acquired"], "Failed to acquire test mutex"
                wdd = self.proxy.mutex_watchdog_get(m, self.testwatchdog)
                self.assert_watchdog_keys(wdd)
                expected_data = {
                                 "err_minutes": 2,
                                 "running": True,
                                 "warn_minutes": 1
                                 }
                self.assert_expected_data(wdd, expected_data)
                self.proxy.mutex_release(m)
        finally:
            self.teardownWatchdog()
            self.release_mutex()


class T11150_MutexWatchdogGet(MutexAdminTests):
    """ Test mutex_watchdog_get."""

    def do(self):
        m = self.testmutex

        try:
            self.setupWatchdog(value=(1, 2))
            with AssertAccessError(self):
                rd = self.proxy.mutex_acquire(m, "PDBAPI tester", None)
                assert rd["acquired"], "Failed to acquire test mutex"
                wdd = self.proxy.mutex_watchdog_get(m, self.testwatchdog)
                self.assert_watchdog_keys(wdd)
                expected_data = {
                                 "err_minutes": 2,
                                 "running": True,
                                 "warn_minutes": 1
                                 }
                self.assert_expected_data(wdd, expected_data)
                self.proxy.mutex_release(m)
        finally:
            self.teardownWatchdog()
            self.release_mutex()


class T11150_MutexWatchdogClear(MutexAdminTests):
    """ Test mutex_watchdog_clear."""

    def do(self):
        m = self.testmutex

        try:
            self.setupWatchdog(value=(1, 2))
            with AssertAccessError(self):
                    rd = self.proxy.mutex_acquire(m, "PDBAPI tester", None)
                    assert rd["acquired"], "Failed to acquire test mutex"
                    self.proxy.mutex_watchdog_clear(m, self.testwatchdog)
                    wdd = self.proxy.mutex_watchdog_get(m, self.testwatchdog)
                    self.assert_watchdog_keys(wdd)
                    expected_data = {
                                     "running": False
                                     }
                    self.assert_expected_data(wdd, expected_data)
                    self.proxy.mutex_release(m)
        finally:
            self.teardownWatchdog()
            self.release_mutex()


class T11160_MutexSetUnsetAccessGroup(MutexAdminTests, GroupTests):
    """ Test mutex_set_access_group and mutex_unset_access_group."""

    def do(self):
        m = self.testmutex

        try:
            self.setupGroup()
            with AssertAccessError(self):
                self.times_before = self.superuser.session_get_time()
                rd = self.proxy.mutex_acquire(m, "PDBAPI tester", None)
                self.times_after = self.superuser.session_get_time()
                assert rd["acquired"], "Failed to acquire test mutex"

                with AssertRPCCError("ValueError::MutexMightBeInaccessible"):
                    self.proxy.mutex_set_access_group(m, self.testgroup)
                self.superuser.membership_create(self.testgroup, self.proxy.username(), {})
                if(self.proxy != self.superuser):
                    self.superuser.membership_create(self.testgroup, self.superuser.username(), {})
                with AssertRPCCError("ValueError::MutexMightBeInaccessible", False):
                    self.proxy.mutex_set_access_group(m, self.testgroup)
                    md = self.superuser.mutex_get_status(m)
                    self.assert_mutex_keys(md)
                    expected_data = {
                                 "held": True,
                                 "access_group": self.testgroup,
                                 "current_owner": "PDBAPI tester",
                                 "stolen": False
                                 }
                    self.assert_expected_data(md, expected_data)
                    self.assert_within_time(md)

                    self.proxy.mutex_unset_access_group(m)

                    md = self.superuser.mutex_get_status(m)
                    self.assert_mutex_keys(md)
                    expected_data = {
                                 "held": True,
                                 "access_group": None,
                                 "current_owner": "PDBAPI tester",
                                 "stolen": False
                                 }
                    self.assert_expected_data(md, expected_data)
                    self.assert_within_time(md)

                    self.proxy.mutex_release(m)
        finally:
            self.remove_access_group()
            self.release_mutex()
            self.teardownGroup()

if __name__ == "__main__":
    sys.exit(main())
