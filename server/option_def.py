#!/usr/bin/env python2.6

from rpcc.model import *
from rpcc.exttype import *
from rpcc.function import SessionedFunction
from optionspace import ExtOptionspace, ExtOptionspaceName, ExtOrNullOptionspace


class ExtNoSuchOptionDefError(ExtLookupError):
    desc = "No such option_def exists."
    
    
class ExtOptionDefError(ExtValueError):
    desc = "The option definition is illegal"


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
    desc = "A option_def instance"

    def lookup(self, fun, cval):
        return fun.option_def_manager.get_option_def(str(cval))

    def output(self, fun, obj):
        return obj.oid
    
    
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
    
    optional = {
                "qualifier": (ExtOptionDefQualifier, "Defines what kind of data the option holds"),
                "optionspace": (ExtOptionspace, "Whether the option belongs to a defined option space"),
                "encapsulate": (ExtOptionspace, "Whether this option encapsulates the defined option space"),
                "struct": (ExtList(ExtOptionType), "Defines a record type, or structure, that the values of this option should adhere to")
                }
 
    
class OptionDefFunBase(SessionedFunction):  
    params = [("name", ExtOptionDefName, "OptionDef name to create")]
    
    
class OptionDefCreate(OptionDefFunBase):
    extname = "option_def_create"
    params = [("code", ExtOptionDefCode, "DHCP code value, or Null"),
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
            
        self.option_def_manager.create_option_def(self, self.name, self.code, self.type, self.info, self.options)


class OptionDefDestroy(OptionDefFunBase):
    extname = "option_def_destroy"
    desc = "Destroys an option definition"
    returns = (ExtNull)

    def do(self):
        self.option_def_manager.destroy_option_def(self, self.name)


class OptionDef(Model):
    name = "option_def"
    exttype = ExtOptionDef
    id_type = str

    def init(self, *args, **kwargs):
        a = list(args)
        #print "OptionDef.init", a
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

    @template("name", ExtOptionDef)
    def get_name(self):
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
    
    @update("name", ExtString)
    def set_name(self, value):
        nn = str(value)
        q = "UPDATE option_defs SET name=:value WHERE name=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=nn)
        self.db.commit()
        print "OptionDef %s changed Name to %s" % (self.oid, nn)
        self.manager.rename_option_def(self, nn)
        
    @update("info", ExtString)
    def set_info(self, value):
        q = "UPDATE option_defs SET info=:value WHERE name=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=value)
        self.db.commit()
        print "OptionDef %s changed Info to %s" % (self.oid, value)
    
    @update("code", ExtString)
    def set_code(self, value):
        q = "UPDATE option_defs SET code=:value WHERE name=:name"
        self.db.put(q, name=self.oid, value=value)
        self.db.commit()
        
    @update("qualifier", ExtOptionDefQualifier)
    def set_qualifier(self, value):
        q = "UPDATE option_defs SET qualifier=:value WHERE name=:name"
        self.db.put(q, name=self.oid, value=value)
        self.db.commit()
        
    @update("type", ExtOptionType)
    def set_type(self, value):
        q = "UPDATE option_defs SET type=:value WHERE name=:name"
        self.db.put(q, name=self.oid, value=value)
        self.db.commit()
        
    @update("optionspace", ExtOrNullOptionspace)
    def set_optionspace(self, value):
        q = "UPDATE option_defs SET encapsulate=:value WHERE name=:name"
        self.db.put(q, name=self.oid, value=value)
        self.db.commit()
        
    @update("encapsulate", ExtOrNullOptionspace)
    def set_encapsulate(self, value):
        q = "UPDATE option_defs SET encapsulate=:value WHERE name=:name"
        self.db.put(q, name=self.oid, value=value)
        self.db.commit()
        
    @update("struct", ExtList(ExtOptionType))
    def set_struct(self, value):
        q = "UPDATE option_defs SET struct=:value WHERE name=:name"
        
        if not value:
            struct = None  # In case there were no elements in the list
        else:
            struct = "{ " + ",".join([x.value for x in value.value]) + " }"
            
        self.db.put(q, name=self.oid, value=struct)
        self.db.commit()


class OptionDefManager(Manager):
    name = "option_def_manager"
    manages = OptionDef

    model_lookup_error = ExtNoSuchOptionDefError

    def init(self):
        self._model_cache = {}
        
    def base_query(self, dq):
        dq.select("r.name", "r.code", "r.qualifier", "r.type", "r.optionspace",
                  "r.encapsulate", "r.struct", "r.info", "r.mtime", "r.changed_by")
        dq.table("option_defs r")
        return dq

    def get_option_def(self, name):
        return self.model(name)

    def search_select(self, dq):
        dq.table("option_defs r")
        dq.select("r.name")
    
    @search("name", StringMatch)
    def s_name(self, dq):
        dq.table("option_defs r")
        return "r.name"
    
    def create_option_def(self, fun, name, code, type, info, options):
        if options == None:
            options = {}
        qualifier = options.get("qualifier", None)
        optionspace = options.get("optionspace", None)
        encapsulate = options.get("encapsulate", None)
        structlist = options.get("struct", None)
        
        if not structlist:
            struct = None  # In case there were no elements in the list
        else:
            struct = "{ " + ",".join([x.value for x in structlist.value]) + " }"
            
        q = """INSERT INTO option_defs (name, code, qualifier, type, optionspace, encapsulate, struct, info, changed_by) 
               VALUES (:name, :code, :qualifier, :type, :optionspace, :encapsulate, :struct, :info, :changed_by)"""
        self.db.insert("id", q, name=name, code=code, 
                       qualifier=qualifier, optionspace=optionspace,
                       encapsulate=encapsulate, struct=struct, type=type,
                       info=info, changed_by=fun.session.authuser)
        print "OptionDef created, name=", name
        self.db.commit()
        
    def destroy_option_def(self, fun, name):
        q = "DELETE FROM option_defs WHERE name=:name LIMIT 1"
        self.db.put(q, name=name)
        print "OptionDef destroyed, name=", name
        self.db.commit()
        
    def rename_option_def(self, obj, newname):
        oid = obj.oid
        obj.oid = newname
        del(self._model_cache[oid])
        self._model_cache[newname] = obj
