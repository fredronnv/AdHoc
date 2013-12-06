#!/usr/bin/env python
""" ADHOC basic API test suite"""
from framework import *
from util import *
import urllib2

from xml.sax._exceptions import SAXParseException

import xml.etree.ElementTree as ET


class T0000_PingTest(UnAuthTests):
    """ Test server responsiveness"""

    def do(self):
        with AssertAccessError(self):
            self.proxy.server_ping()


class T0010_ServerVersion(UnAuthTests):
    """ Test server_version """
    def do(self):

        with AssertAccessError(self):
            ver = self.proxy.server_version()
        self.assertindict(ver, ["major", "minor", "service"])

        # print "Service %s version %s.%s"%(ver["service"],ver["major"],ver["minor"])

        assert ver["major"] == '0', "Major version is not 0"
        assert ver["minor"] == '1', "Minor version is not 1"
        assert ver["service"] == "AdHoc", "Service is not AdHoc"


class T0020_SessionGetInfo(UnAuthTests):
    """ Test session_get_info """
    def dont(self):
        # Run session_get_info
        with AssertAccessError(self):
            res = self.proxy.session_info()

        self.assertindict(res, ["authuser", "expires", "startup", "id", "temporary"])
        assert res["authuser"] == self.proxy.username(), "Auth user should be %s, not %s" % (self.proxy.username(), res["authuser"])
        assert type(res["startup"]) == FloatType, "Startup time is not a float"
        assert type(res["expires"]) == FloatType, "Expiry time is not a float"
        assert type(res["id"]) == unicode, "ID is not a Unicode String"
        assert type(res["temporary"]) == BooleanType, "Temporary is not a boolean"
        assert res["id"] == self.proxy._sid, "ID does not match the session ID used"


class T0030_Sleep(AuthTests):
    """ Test the sleep function for 1 second"""
    def dont(self):
        # print "Sleeping for 1 second"
        with AssertAccessError(self):
            self.proxy.sleep(1)


class T0040_SessionGetAccess(AuthTests):
    """ Test session_get_access"""
    def dont(self):
        # Run session_get_access
        with AssertAccessError(self):
            res = self.proxy.session_get_access()
            self.assertindict(res, ["unauth", "superusers", "registrator", "scratch", "anyauth"])


class T0050_SessionGetPrivileges(AuthTests):
    """ Test session_get_privileges"""
    def dont(self):
    # Run session_get_privileges
        with AssertAccessError(self):
            res = self.proxy.session_get_privileges()
            assert res != None


class T0092_ServerLastSourceEdit(UnAuthTests):
    """ Test server_last_source_edit"""

    def dont(self):
        with AssertAccessError(self):
            last_edit = self.proxy.server_last_source_edit()
            # print last_edit
            assert type(last_edit) is type(u'xx'), "Returned last source edit is not a string, it is a %s" % (type(last_edit))


class T0093_ServerListFunctions(UnAuthTests):
    """ Test server_list_functions."""

    def do(self):
        with AssertAccessError(self):
            fnlist = self.proxy.server_list_functions()

            assert type(fnlist) is list, "Function list is not a list"

            for fn in fnlist:
                
                assert type(fn) is unicode, "Function name is not unicode"
                if fn == "sleep":
                    continue
                assert '_' in fn, "Function name does not contain any underscores (_)"


class T0094_ServerNodeName(UnAuthTests):
    """ Test server_node_name."""

    def do(self):
        with AssertAccessError(self):
            node_name = self.proxy.server_node_name()
            # print node_name
            assert type(node_name) is type(u'xx'), "Returned last source edit is not a string, it is a %s" % (type(node_name))
            assert "." in node_name, "Node name does not contain any dot"


class T0095_SessionGetTime(AuthTests):
    """ Test session_get_time."""
    def dont(self):
        # local_now = datetime.datetime.now()
        with AssertAccessError(self):
            times = self.proxy.session_get_time()
            self.assertindict(times, ["db", "server"], exact=True)
            assert len(times["db"]) == 19, "Time string for database time has wrong length"
            assert len(times["server"]) == 26, "Time string for server time has wrong length"
            # print local_now
            # print times


class T0096_WSDL_list(UnAuthTests):
    """ Test fetching the WSDL list"""

    def do(self):
        resp = urllib2.urlopen("http://nile.medic.chalmers.se:12121/WSDL")
        html = resp.read()

        l = html.split("<li>")
        found_wsdls = len(l) - 1

        apiver = self.superuser.api_version
        expected_wsdls = 2 * (apiver + 1)
        #print html

        assert found_wsdls == expected_wsdls, "Found %d WSDLs, expected %d" % (found_wsdls, expected_wsdls)


class T0097_WSDL(UnAuthTests):
    """ Test fetching the WSDL."""
    functions = 0

    def countFunctions(self, node):
        if "soapAction" in node.attrib:
            self.functions += 1
        for child in node:
            self.countFunctions(child)

    def do(self):
        resp = urllib2.urlopen("http://nile.medic.chalmers.se:12121/WSDL/AdHoc.wsdl")
        xml = resp.read()
        # xml = unicodedata.normalize('NFKD', xml).encode('ascii', 'ignore')
        # pprint.pprint(xml)
        try:
            root = ET.fromstring(xml)
            # self.pprec(root, 0)
            self.countFunctions(root)

        except SAXParseException:
            print "XML for WSDL is not well formed"
            print xml

        # print "Found %d functions"%(self.functions)
        res = self.superuser.server_list_functions()
        assert  len(res) == self.functions, "Found %d functions in WSDL, expected %d" % (self.functions, len(res))

if __name__ == "__main__":
    sys.exit(main())
