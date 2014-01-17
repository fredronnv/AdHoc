#!/usr/bin/env python
# -*- coding: utf8 -*-

""" ADHOC option_def API test suite"""
from framework import *
from util import *


class T1000_OptionDefList(UnAuthTests):
    """ Test option_def listing """

    def do(self):
        with AssertAccessError(self):
            ret = self.proxy.option_def_dig({}, {"code": True,
                                                 "qualifier": True,
                                                 "type": True,
                                                 "optionspace": True,
                                                 "encapsulate": True,
                                                 "struct": True,
                                                 "info": True, 
                                                 "option_def": True,
                                                 "changed_by": True,
                                                 "mtime": True})
            
            assert len(ret) > 0, "Too few option_defs returned"
            #for ds in ret:
                #print ds.re, ds.option_def, ds.info
  
  
class T1010_OptionDefFetch(UnAuthTests):
    """ Test option_def_fetch """
    
    def do(self):
        option_defs = [x.option_def for x in self.superuser.option_def_dig({}, {"option_def":True})]
        
        n = 0
        for option_def in option_defs:
            ret = self.proxy.option_def_fetch(option_def, {"code": True, "info": True, "option_def": True})
            assert "code" in ret, "Key code missing in returned struct from option_def_fetch"
            assert "info" in ret, "Key info missing in returned struct from option_def_fetch"
            assert "option_def" in ret, "Key option_def missing in returned struct from option_def_fetch"
            n += 1
            if n > 50:  # There are too many option_defs to check, 50 is enough
                break
            
            
class T1020_OptionDefCreate(AuthTests):
    """ Test option_def_create """
    
    def do(self):  
        try:
            self.superuser.option_def_destroy("QZ1243A")
        except:
            pass
        with AssertAccessError(self):
            try:
                self.proxy.option_def_create('QZ1243A', 253, 'text', "TestOptionDef", {})
                template = {
                            "option_def": True, 
                            "code": True,
                            "qualifier": True,
                            "type": True,
                            "optionspace": True,
                            "encapsulate": True,
                            "struct": True,
                            "info": True,
                            "changed_by": True,
                            "mtime": True
                          }
                ret = self.superuser.option_def_fetch('QZ1243A', template)
                
                self.assertindict(ret, template.keys(), exact=True)
                
                assert ret.option_def == "QZ1243A", "Bad option_def, is % should be %s" % (ret.option_def, "QZ1243A")
                assert ret.code == 253, "Code is %s but should be 253" % ret.code
                assert ret.type == "text", "Type is " + ret.type + " but should be 'text'"
                assert ret.info == "TestOptionDef", "Info is " + ret.info + "but should be 'TestOptionDef'"
            finally:
                try:
                    self.superuser.option_def_destroy('QZ1243A')
                except:
                    pass
        
        
class T1030_OptionDefDestroy(AuthTests):
    """ Test option_def destroy """
    
    def do(self):
        self.superuser.option_def_create('QZ1243A', 253, 'text', "TestOptionDef", {})
        try:
            with AssertAccessError(self):
                self.proxy.option_def_destroy('QZ1243A')
                with AssertRPCCError("LookupError::NoSuchOptionDef", True):
                    self.superuser.option_def_fetch('QZ1243A', {"option_def": True})
        finally:
            try:
                self.superuser.option_def_destroy('QZ1243A')
            except:
                pass
            
        
class T1040_OptionDefSetID(AuthTests):
    """ Test setting option_def of a option_def"""
    
    def do(self):
        self.superuser.option_def_create('QZ1243A', 253, 'text', "TestOptionDef", {})
        try:
            with AssertAccessError(self):
                self.proxy.option_def_update('QZ1243A', {"option_def": 'ZQ1296'})
                nd = self.superuser.option_def_fetch('ZQ1296', {"type": True, "info": True, "option_def": True})
                assert nd.option_def == "ZQ1296", "Bad option_def"
                assert nd.type == 'text', "Bad type"
                assert nd.info == "TestOptionDef", "Bad info"
        finally:
            try:
                self.superuser.option_def_destroy('ZQ1296')
            except:
                pass
            try:
                self.superuser.option_def_destroy('QZ1243A')
            except:
                pass
                
                
class T1050_OptionDefSetInfo(AuthTests):
    """ Test setting info on a option_def"""
    
    def do(self):
        self.superuser.option_def_create('QZ1243A', 253, 'text', "TestOptionDef", {})
        with AssertAccessError(self):
            try:
                self.proxy.option_def_update('QZ1243A', {"info": "ZQ1296 option"})
                nd = self.superuser.option_def_fetch('QZ1243A', {"type": True, "info": True, "option_def": True})
                assert nd.option_def == "QZ1243A", "Bad option_def"
                assert nd.type == 'text', "Bad type"
                assert nd.info == "ZQ1296 option", "Bad info"
            finally:
                try:
                    self.superuser.option_def_destroy('QZ1243A')
                except:
                    pass
                
                
class T1050_OptionDefSetType(AuthTests):
    """ Test setting type on a option_def"""
    
    def do(self):
        self.superuser.option_def_create('QZ1243A', 253, 'text', "TestOptionDef", {})
        with AssertAccessError(self):
            try:
                self.proxy.option_def_update('QZ1243A', {"type": "boolean"})
                nd = self.superuser.option_def_fetch('QZ1243A', {"type": True, "info": True, "option_def": True})
                assert nd.option_def == "QZ1243A", "Bad option_def"
                assert nd.type == 'boolean', "Bad type"
                assert nd.info == "TestOptionDef", "Bad info"
            finally:
                try:
                    self.superuser.option_def_destroy('QZ1243A')
                except:
                    pass
        
if __name__ == "__main__":
    sys.exit(main())
