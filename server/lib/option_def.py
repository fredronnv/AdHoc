#!/usr/bin/env python2.6

# $Id$

from rpcc import *
from optionspace import *
from util import *
import optionset


g_write = AnyGrants(AllowUserWithPriv("write_all_option_defs"), AdHocSuperuserGuard)


class ExtNoSuchOptionDefError(ExtLookupError):
    desc = "No such option_def exists."
    

class ExtOptionDefAlreadyExistsError(ExtLookupError):
    desc = "The option definition already exists"
    
   
class ExtOptionDefInUseError(ExtValueError):
    desc = "The option definition is in use. It cannot be destroyed"    

    
class ExtOptionDefError(ExtValueError):
    desc = "The option definition is illegal"
    
    
class ExtOptionNotSetError(ExtLookupError):
    desc = "The given option was not set"


class ExtOptionDefName(ExtString):
    name = "option_def-name"
    desc = "Name of an option definition"
    regexp = "^[-a-zA-Z0-9_]+$"
    maxlen = 32


class ExtOptionDefCode(ExtOrNull):
    name = "option_def-code"
    desc = "DHCP code, or Null"
    range = (0, 255)
    typ = ExtInteger


class ExtOptionDef(ExtOptionDefName):
    name = "option_def"
    desc = "A defined option identified by its name"

    def lookup(self, fun, cval):
        return fun.option_def_manager.get_option_def(str(cval))

    def output(self, fun, obj):
        return obj.oid
    
    
class ExtOptionValue(ExtStruct):
    name = "option_value"
    desc = "An option name-value pair"
    
    mandatory = {"name": (ExtString, "Option name"),
                 "value": (ExtString, "Option value")
                 }
 
    
class ExtOptionValueList(ExtList):
    name = "option_value_list"
    desc = "List of options and their values"
    typ = ExtOptionValue
    
    
class ExtOptionKey(ExtString):
    name = "option_key"
    desc = "the name of an option"
    
    
class ExtOptionKeyList(ExtList):
    name = "option_key_list"
    desc = "List of options and their values"
    typ = ExtOptionKey
    
    
class ExtOptions(ExtDict):
    typ = ExtString
    name = "options"
    desc = "Options defined for the object"
    
    
class ExtOptionType(ExtEnum):
    name = "option_type"
    desc = "The type of an option"
    values = ["ip-address",
              "text",
              "unsigned integer 8",
              "unsigned integer 16",
              "unsigned integer 32",
              "integer 8",
              "integer 16",
              "integer 32",
              "string",
              "boolean"]


class OptionDefQuals(ExtEnum):
    name = "option_qualifier_values"
    desc = "The qualifier for the option, if any"
    values = [u"array",
              u"parameter",
              u"parameter-array"]
  
    
class ExtOptionDefQualifier(ExtOrNull):
    name = "option_qualifier"
    desc = "The qualifier for the option, if any"
    typ = OptionDefQuals
    
    
class ExtOptionDefStruct(ExtOrNull):
    name = "option_def_struct"
    desc = "An option record, or null"
    typ = ExtList(ExtOptionType)
    
    
class ExtOptionDefCreateOptions(ExtStruct):
    name = "option_create_options"
    desc = "Optional parameters when defining an option"
    
    optional = {"qualifier": (ExtOptionDefQualifier, "Defines what kind of data the option holds"),
                "optionspace": (ExtOptionspace, "Whether the option belongs to a defined option space"),
                "encapsulate": (ExtOptionspace, "Whether this option encapsulates the defined option space"),
                "struct": (ExtList(ExtOptionType), "Defines a record type, or structure, that the values of this option should adhere to")
                }
 

class OptionDefCreate(SessionedFunction):
    extname = "option_def_create"
    params = [("option_def", ExtOptionDefName, "OptionDef name to create"),
              ("code", ExtOptionDefCode, "DHCP code value, or Null"),
              ("type", ExtOptionType, "The type of option"),
              ("info", ExtString, "OptionDef description"),
              ("options", ExtOptionDefCreateOptions, "Create options")]
    desc = "Creates an option definition"
    returns = (ExtNull)

    def do(self):
        qual = self.options.get("qualifier", None)
        if not self.code:
            if not qual or not qual.startswith("parameter"):
                raise ExtOptionDefError("Codeless options must be qualified as a parameter or a parameter array")
            
        self.option_def_manager.create_option_def(self, self.option_def, self.code, self.type, self.info, self.options)


class OptionDefDestroy(SessionedFunction):
    extname = "option_def_destroy"
    params = [("option_def", ExtOptionDef, "OptionDef to destroy")]
    desc = "Destroys an option definition"
    returns = (ExtNull)

    def do(self):
        self.option_def_manager.destroy_option_def(self.option_def)


class OptionDef(AdHocModel):
    name = "option_def"
    exttype = ExtOptionDef
    id_type = unicode

    def init(self, *args, **kwargs):
        a = list(args)
        # print "OptionDef.init", a
        self.oid = a.pop(0)
        self.code = a.pop(0)
        self.qualifier = a.pop(0)
        self.type = a.pop(0)
        self.optionspace = a.pop(0)
        self.encapsulate = a.pop(0)
        self.struct = a.pop(0)
        self.info = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)
        self.id = a.pop(0)

    @template("option_def", ExtOptionDef)
    def get_option_def(self):
        return self

    @template("code", ExtOptionDefCode)
    def get_code(self):
        return self.code
    
    @template("qualifier", ExtOptionDefQualifier)
    def get_qualifier(self):
        return self.qualifier
    
    @template("type", ExtOptionType)
    def get_type(self):
        return self.type
    
    @template("optionspace", ExtOrNullOptionspace)
    def get_optionspace(self):
        return self.optionspace
    
    @template("encapsulate", ExtOrNullOptionspace)
    def get_encapsulate(self):
        return self.encapsulate
    
    @template("struct", ExtOptionDefStruct)
    def get_struct(self):
        struct = self.struct
        if not struct:
            return None
        struct = struct.lstrip("{ ")
        struct = struct.rstrip(" }")
        types = struct.split(",")
        
        list = []
        for s in types:
            t = ExtOptionType()
            t.value = s
            list.append(t)
        
        return list

    @template("info", ExtString)
    def get_info(self):
        return self.info
    
    @template("mtime", ExtDateTime)
    def get_mtime(self):
        return self.mtime
    
    @template("changed_by", ExtString)
    def get_changed_by(self):
        return self.changed_by
    
    @update("option_def", ExtString)
    @entry(g_write)
    def set_option_def(self, value):
        nn = str(value)
        q = "UPDATE option_base SET name=:value WHERE name=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=nn)
        
        # print "OptionDef %s changed Name to %s" % (self.oid, nn)
        self.manager.rename_object(self, nn)
        self.event_manager.add("rename", option=self.oid, newstr=value, authuser=self.function.session.authuser)
        
    @update("info", ExtString)
    @entry(g_write)
    def set_info(self, value):
        q = "UPDATE option_base SET info=:value WHERE name=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update", option=self.oid, info=value, authuser=self.function.session.authuser)
        
        # print "OptionDef %s changed Info to %s" % (self.oid, value)
    
    @update("code", ExtString)
    @entry(g_write)
    def set_code(self, value):
        q = "UPDATE option_base SET code=:value WHERE name=:name"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update", option=self.oid, code=value, authuser=self.function.session.authuser)
             
    @update("qualifier", ExtOptionDefQualifier)
    @entry(g_write)
    def set_qualifier(self, value):
        q = "UPDATE option_base SET qualifier=:value WHERE name=:name"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update", option=self.oid, qualifier=value, authuser=self.function.session.authuser)
             
    @update("type", ExtOptionType)
    @entry(g_write)
    def set_type(self, value):
        q = "UPDATE option_base SET type=:value WHERE name=:name"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update", option=self.oid, type=value, authuser=self.function.session.authuser)
             
    @update("optionspace", ExtOrNullOptionspace)
    @entry(g_write)
    def set_optionspace(self, value):
        q = "UPDATE option_base SET encapsulate=:value WHERE name=:name"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update", option=self.oid, optionspace=value, authuser=self.function.session.authuser)
        
    @update("encapsulate", ExtOrNullOptionspace)
    @entry(g_write)
    def set_encapsulate(self, value):
        q = "UPDATE option_base SET encapsulate=:value WHERE name=:name"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update", option=self.oid, encapsulate=value, authuser=self.function.session.authuser)
           
    @update("struct", ExtList(ExtOptionType))
    @entry(g_write)
    def set_struct(self, value):
        q = "UPDATE option_base SET struct=:value WHERE name=:name"
        
        if not value:
            struct = None  # In case there were no elements in the list
        else:
            struct = "{ " + ",".join([x.value for x in value.value]) + " }"
            
        self.db.put(q, name=self.oid, value=struct)
        self.event_manager.add("update", option=self.oid, struct=struct, authuser=self.function.session.authuser)
        

class OptionDefManager(AdHocManager):
    name = "option_def_manager"
    manages = OptionDef

    model_lookup_error = ExtNoSuchOptionDefError

    def init(self):
        self._model_cache = {}
        
    @classmethod
    def base_query(cls, dq):
        dq.select("r.name", "r.code", "r.qualifier", "r.type", "r.optionspace",
                  "r.encapsulate", "r.struct", "r.info", "r.mtime", "r.changed_by", "r.id")
        dq.table("option_base r")
        return dq

    def get_option_def(self, option_def_name):
        return self.model(unicode(option_def_name))

    def search_select(self, dq):
        dq.table("option_base r")
        dq.select("r.name")
    
    @search("option_def", StringMatch)
    def s_name(self, dq):
        dq.table("option_base r")
        return "r.name"
    
    @entry(g_write)
    def create_option_def(self, fun, option_def_name, code, type, info, options):
        if options is None:
            options = {}
        qualifier = options.get("qualifier", None)
        optionspace = options.get("optionspace", None)
        encapsulate = options.get("encapsulate", None)
        structlist = options.get("struct", None)
        
        if not structlist:
            struct = None  # In case there were no elements in the list
        else:
            struct = "{ " + ",".join([x.value for x in structlist.value]) + " }"
            
        if optionspace:
            optionspace = optionspace.oid
            
        self.define_option(info, fun.session.authuser, None, option_def_name, type, code, qualifier, optionspace, struct=struct, encapsulate=encapsulate)
        optionset.OptionsetManager.init_class(self.db)  # Reinitialize class with new options in the table
        
    @entry(g_write)
    def define_option(self, info, changed_by, mtime, name, my_type, code, qualifier, optionspace, struct=None, encapsulate=None):
        qp1 = "INSERT INTO option_base (name, code, qualifier, type, info, changed_by"
        qp2 = "VALUES(:name, :code, :qualifier, :type, :info, :changed_by"
        
        param_dict = {"name": name, "code": code, "qualifier": qualifier, "type": my_type, "changed_by": changed_by, "info": info}
        if mtime:
            qp1 += ", mtime"
            qp2 += ", :mtime"
            param_dict["mtime"] = mtime
        if struct:
            qp1 += ", struct"
            qp2 += ", :struct"
            param_dict["struct"] = struct
        if encapsulate:
            qp1 += ", encapsulate"
            qp2 += ", :encapsulate"
            param_dict["encapsulate"] = encapsulate.oid
        if optionspace:
            qp1 += ", optionspace"
            qp2 += ", :optionspace"
            param_dict["optionspace"] = optionspace
        qp1 += ") "
        qp2 += ") "
        
        try:
            id = self.db.insert("id", qp1 + qp2, **param_dict)
        except IntegrityError:
            raise ExtOptionDefAlreadyExistsError()
        
        sql_params = {"option_base": id}
        if my_type.startswith("integer") or my_type.startswith("unsigned"):
            if my_type.endswith(' 8'):
                u_maxval = 255
                i_maxval = 127
                i_minval = -127
            if my_type.endswith(' 16'):
                u_maxval = 16383
                i_maxval = 8191
                i_minval = -8191
            if my_type.endswith(' 32'):
                u_maxval = 4294967295
                i_maxval = 2147483647
                i_minval = -2147483647
            if my_type.startswith("unsigned"):
                minval = 0
                maxval = u_maxval
            else:
                minval = i_minval
                maxval = i_maxval
                
            table = "int_option"    
            if qualifier and "array" in qualifier:
                table = "intarray_option" 
                   
            qp3 = """INSERT INTO %s (option_base, minval, maxval) 
                 VALUES (:option_base, :minval, :maxval)""" % (table)
            
            param_dict["authuser"] = param_dict["changed_by"]
            param_dict["option"] = param_dict["name"]
            del(param_dict["changed_by"])
            del(param_dict["name"])
            param_dict["maxval"] = maxval
            param_dict["minval"] = minval
            sql_params["minval"] = minval
            sql_params["maxval"] = maxval
            
        if my_type == 'string' or my_type == 'text':
            qp3 = """INSERT INTO str_option (option_base) 
                 VALUES (:option_base)"""
            param_dict["authuser"] = param_dict["changed_by"]
            param_dict["option"] = param_dict["name"]
            del(param_dict["changed_by"])
            del(param_dict["name"])
            
        if my_type == 'boolean':
            qp3 = """INSERT INTO bool_option (option_base) 
                 VALUES (:option_base)"""
            param_dict["authuser"] = param_dict["changed_by"]
            param_dict["option"] = param_dict["name"]
            del(param_dict["changed_by"])
            del(param_dict["name"])
            
        if my_type == 'ip-address':
            table = "ipaddr_option"
            if qualifier and "array" in qualifier:
                table = "ipaddrarray_option"
                
            qp3 = """INSERT INTO %s (option_base) 
                 VALUES (:option_base)""" % (table)
            param_dict["authuser"] = param_dict["changed_by"]
            param_dict["option"] = param_dict["name"]
            del(param_dict["changed_by"])
            del(param_dict["name"])
            if qualifier:
                param_dict["qualifier"] = qualifier
        
        self.db.put(qp3, **sql_params)
        self.approve_config = True
        self.approve()
        self.event_manager.add("create", **param_dict)
        return id
              
    @entry(g_write)
    def destroy_option_def(self, option_def):
        
        try:
            q = "DELETE FROM option_base WHERE name=:name LIMIT 1"
            self.db.put(q, name=option_def.oid)
        except IntegrityError:
            raise ExtOptionDefInUseError()
        self.approve_config = True
        self.approve()
        self.event_manager.add("destroy", option=option_def.name)
