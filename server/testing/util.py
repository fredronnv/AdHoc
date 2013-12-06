#!/usr/bin/env python
# -*- coding: utf-8 -*-
from framework import *


class DigTests(AuthTests):
    
    def prepare_test(self):
        """ prepare_test is always run by the framework before the do() method"""
        self.times_before = self.superuser.session_get_time()
        super(DigTests, self).prepare_test()
        self.setupRelations()
        self.testrelation = self.testrelations[0]
        
        self.testaccount = self.not_my_accounts()[0]
        self.setupCommissions()
        self.testcommission = self.testcommissions[0]
        self.setupGroup()
        self.setupMemberships()
        self.testmembership = self.testmemberships[0]
        self.setupOrgMembership()
        
        # The following tw statement must be the last thing that happens,
        # Otherwise the event_search_verbose test will fail
        self.times_after = self.superuser.session_get_time()
        
    def cleanup_test(self):
        """ cleanup_test is always run by the framework after the do() method"""
        super(DigTests, self).cleanup_test()
    
    def test_all_dig_options(self, rpcname, search_with_match):
        
        self.test_all_search_options(rpcname, {})
        self.test_full_data_template(rpcname, search_with_match)
        
    def test_all_search_options(self, rpcname, dataopt=None):
        
        searchopt = {}

        docdict = self.superuser.server_documentation_struct(rpcname)
        search_dd = docdict.parameters[1]

        untested = []
        for keyspec in search_dd.type.optional:
            val = None

            if keyspec.name.endswith("_is_not_set"):
                continue

            typ = keyspec.type
            if typ.dict_type == 'ornull-type':
                typ = typ.otherwise

            # Values set depending on search key base type name.
            if typ.dict_type == "string-type":
                if "_pattern" in keyspec.name:
                    val = "*X?X*"
                elif "_regexp" in keyspec.name:
                    val = ".*X.X.*"
                elif "personnummer" in keyspec.name:
                    val = self.testpnr
                else:
                    val = "example"
            elif typ.dict_type == "integer-type":
                val = 123456
            elif typ.dict_type == "boolean-type":
                val = True
                
            # Values set depending on search key type name.
            if typ.name == "date":
                val = "2012-12-12"
            if typ.name == "email":
                val = "apa.bepa@cepa.com"
            elif typ.name == "datetime":
                val = '2012-12-12T12:12:12'
            elif typ.name == 'integer-range':
                val = {'from': 1000, 'to': 1005}
            elif typ.name == 'date-range':
                val = {'from': '2001-01-01', 'to': '2001-01-02'}
            elif typ.name == 'date-time-range':
                val = {'from': '2001-01-01T00:00:00',
                       'to': '2001-01-01T01:00:00'}

            # Values set depending on search key name.
            
            if keyspec.name in ['person']:
                val = self.testperson
            elif keyspec.name == 'agreement_version':
                val = '99.999'
            elif keyspec.name == "room":
                val = 'AZ5432C'
            elif keyspec.name in ['person_current_search']:
                val = {'person': self.testperson}
            elif keyspec.name in ['primary_account',
                                  'account',
                                  'owns_account',
                                  'has_admin_group_member',
                                  'filter_for_account'
                                  ]:
                val = self.testaccount
            elif keyspec.name == "status":
                val = "active"
            elif keyspec.name in ['group',
                                  'has_ancestor_group',
                                  'has_child_group',
                                  'has_descendant_group',
                                  'has_parent_group',
                                  'admin_group',
                                  'primary_account_in_group',
                                  'group_descendant_of']:
                val = self.testgroup
            elif keyspec.name in ['group2_current_search', 'group_current_search']:
                val = {'group': self.testgroup}
            elif keyspec.name in ['account_search', 'account_current_search', 'authuser_current_search']:
                val = {"account": self.testaccount}
            elif keyspec.name in ['membership_search', 'membership_current_search']:
                val = {"membership": self.testmembership}
            elif keyspec.name == "membership":
                val = self.testmembership
            elif keyspec.name in ['owner_search', 'person_search']:
                val = {"person": self.testperson}
            elif keyspec.name == 'owner':
                val = self.testperson
            elif keyspec.name == 'relation_search':
                val = {'relation': self.testrelation}
            elif keyspec.name == 'relation_type':
                val = '/testers'
            elif keyspec.name == 'relation_type_pattern':
                val = '/*x*'
            elif keyspec.name in ['reltype2_current_search', 'reltype_current_search']:
                val = {'relation_type': self.testrelationtype}
            elif keyspec.name in ['orgunit_search',
                                  "orgunit2_current_search", 
                                  "orgunit_current_search",
                                  'any_ancestor_search',
                                  'any_child_search',
                                  'any_descendant_search',
                                  'any_parent_search',
                                  'tree_ancestor_search',
                                  'tree_child_search',
                                  'tree_descendant_search',
                                  'tree_parent_search',
                                  ]:
                val = {'orgunit': self.testorgunit}
            elif keyspec.name in ['orgmembership_search']:
                val = {'orgmembership': self.testorgmembership}
            elif keyspec.name == 'commission_type_search':
                val = {'commission_type': self.testcommissiontype}
            elif keyspec.name in ['group_search',
                                  'admin_group_search', 
                                  'ancestor_group_search',
                                  'child_group_search',
                                  'descendant_group_search',
                                  'parent_group_search']:
                val = {"group": self.testgroup}
            elif keyspec.name in ['ancestor_type_search',
                                  'child_type_search',
                                  'descendant_type_search',
                                  'parent_type_search',
                                  'relation_type_search']:
                val = {'relation_type': self.testrelationtype}

            if val is None:
                print "Unhandled search key", keyspec.name, keyspec.type.name
                untested.append(keyspec.name)
            else:
                searchopt[keyspec.name] = val

        if untested:
            print "Untested search keys for %s: %s" % (rpcname, ", ".join(untested))
        if dataopt != None:
            dummy = getattr(self.proxy, rpcname)(searchopt, dataopt)
        else:
            dummy = getattr(self.proxy, rpcname)(searchopt)
        
    def test_full_data_template(self, rpcname, search_with_match):
        docdict = self.superuser.server_documentation_struct(rpcname)
        data_dd = docdict.parameters[2]
        dataopt = {}
        
        untested = []
        for keyspec in data_dd.type.optional:
            val = None

            if keyspec.type.name == 'boolean':
                val = True
            elif keyspec.name.endswith("_data"):
                val = {"_": True}

            if val is None:
                untested.append(keyspec.name)
            else:
                dataopt[keyspec.name] = val

        if untested:
            print "Untested data keys for %s: %s" % (rpcname, ", ".join(untested))
        
        ret = getattr(self.proxy, rpcname)(search_with_match, dataopt)
        return ret
