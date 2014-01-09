#!/usr/bin/env python2.6

from rpcc.model import *
from rpcc.exttype import *
from rpcc.function import SessionedFunction
from optionspace import ExtOptionspace, ExtOrNullOptionspace
from rpcc.database import  IntegrityError
from option_def import ExtOptionDef, ExtOptionNotSetError, ExtOptions


class ExtNoSuchGroupError(ExtLookupError):
    desc = "No such group exists."


class ExtGroupError(ExtValueError):
    desc = "The group name is invalid or in use"


class ExtGroupName(ExtString):
    name = "group-name"
    desc = "Name of a group"
    regexp = "^[-a-zA-Z0-9_]+$"
    maxlen = 64


class ExtGroup(ExtGroupName):
    name = "group"
    desc = "A group instance"

    def lookup(self, fun, cval):
        return fun.group_manager.get_group(cval)

    def output(self, fun, obj):
        return obj.oid
    
    
class ExtGroupCreateOptions(ExtStruct):
    name = "group_create_options"
    desc = "Optional parameters when creating a group"
    
    optional = {
                "optionspace": (ExtOptionspace, "Whether the group should declare an option space"),
                }


class GroupFunBase(SessionedFunction):  
    params = [("group", ExtGroup, "Group name")]
    
    
class GroupCreate(SessionedFunction):
    extname = "group_create"
    params = [("group_name", ExtGroupName, "Name of DHCP group to create"),
              ("parent", ExtGroup, "Parent group"),
              ("info", ExtString, "Group description"),
              ("options", ExtGroupCreateOptions, "Create options")]
    desc = "Creates a group"
    returns = (ExtNull)

    def do(self):
        self.group_manager.create_group(self, self.group_name, self.parent, self.info, self.options)


class GroupDestroy(GroupFunBase):
    extname = "group_destroy"
    desc = "Destroys a DHCP group"
    returns = (ExtNull)

    def do(self):
        self.group_manager.destroy_group(self, self.group)


class GroupOptionSet(GroupFunBase):
    extname = "group_option_set"
    desc = "Set an option value on a group"
    params = [("option_name", ExtOptionDef, "Option name"),
              ("value", ExtString, "Option value")]
    returns = (ExtNull)
    
    def do(self):
        self.group_manager.set_option(self, self.group, self.option_name, self.value)


class GroupOptionUnset(GroupFunBase):
    extname = "group_option_unset"
    desc = "Unset an option value on a group"
    params = [("option_name", ExtOptionDef, "Option name")]
    returns = (ExtNull)
    
    def do(self):
        self.group_manager.unset_option(self, self.group, self.option_name)


class Group(Model):
    name = "group"
    exttype = ExtGroup
    id_type = unicode

    def init(self, *args, **kwargs):
        a = list(args)
        #print "Group.init", a
        self.oid = a.pop(0)
        self.parent = a.pop(0)
        self.optionspace = a.pop(0)
        self.info = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)

    @template("group", ExtGroup)
    def get_group(self):
        #print "GET_GROUP"
        return self

    @template("parent", ExtGroup)
    def get_parent(self):
        #print "GET_PARENT:", self.parent
        p = self.manager.get_parent(self.parent)
        print "GET_PARENT 2:", p
        return p
    
    @template("optionspace", ExtOrNullOptionspace)
    def get_optionspace(self):
        return self.optionspace

    @template("info", ExtString)
    def get_info(self):
        return self.info
    
    @template("mtime", ExtDateTime)
    def get_mtime(self):
        return self.mtime
    
    @template("changed_by", ExtString)
    def get_changed_by(self):
        return self.changed_by
    
    @template("options", ExtOptions)
    def get_options(self):
        q = "SELECT name, value FROM group_options WHERE `for`=:id"
        ret = {}
        res = self.db.get_all(q, id=self.oid)
        for opt in res:
            ret[opt[0]] = opt[1]
        return ret

    @update("group", ExtString)
    def set_name(self, group_name):
        nn = str(group_name)
        q = "UPDATE groups SET groupname=:value WHERE groupname=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=nn)
        self.db.commit()
        print "Group %s changed Name to %s" % (self.oid, nn)
        self.manager.rename_group(self, nn)
        
    @update("info", ExtString)
    def set_info(self, value):
        q = "UPDATE groups SET info=:value WHERE groupname=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=value)
        self.db.commit()
        print "Group %s changed Info to %s" % (self.oid, value)
    
    @update("parent", ExtString)
    def set_parent(self, value):
        q = "UPDATE groups SET parent_group=:value WHERE groupname=:name"
        self.db.put(q, name=self.oid, value=value)
        self.db.commit()
        
    @update("optionspace", ExtOrNullOptionspace)
    def set_optionspace(self, value):
        q = "UPDATE groups SET optionspace=:value WHERE groupname=:name"
        self.db.put(q, name=self.oid, value=value)
        self.db.commit()


class GroupManager(Manager):
    name = "group_manager"
    manages = Group

    model_lookup_error = ExtNoSuchGroupError

    def init(self):
        self._model_cache = {}
        
    def base_query(self, dq):
        dq.select("g.groupname", "g.parent_group", "g.optionspace",
                  "g.info", "g.mtime", "g.changed_by")
        dq.table("groups g")
        return dq

    def get_group(self, group_name):
        return self.model(group_name)
    
    def get_parent(self, parent_name):
        return self.model(parent_name)

    def search_select(self, dq):
        dq.table("groups g")
        dq.select("g.groupname")
    
    @search("group", StringMatch)
    def s_name(self, dq):
        dq.table("groups g")
        return "g.groupname"
    
    @search("parent", StringMatch)
    def s_parent(self, dq):
        dq.table("groups g")
        return "g.parent"
    
    def create_group(self, fun, group_name, parent, info, options):
        if options == None:
            options = {}
        optionspace = options.get("optionspace", None)
            
        q = """INSERT INTO groups (groupname, parent_group, optionspace, info, changed_by) 
               VALUES (:group_name, :parent, :optionspace, :info, :changed_by)"""
        try:
            self.db.insert("id", q, group_name=group_name, parent=parent.oid, optionspace=optionspace,
                       info=info, changed_by=fun.session.authuser)
            print "Group created, name=", group_name
            self.db.commit()
        except IntegrityError, e:
            print "SKAPELSEFEL A:", e
            raise ExtGroupError("The group name is already in use")
        except Exception, e:
            print "SKAPELSEFEL:", e
            raise
        
    def destroy_group(self, fun, group):
        q = "DELETE FROM groups WHERE groupname=:groupname LIMIT 1"
        self.db.put(q, groupname=group.oid)
        print "Group destroyed, name=", group.oid
        self.db.commit()
        
    def rename_group(self, obj, newname):
        oid = obj.oid
        obj.oid = newname
        del(self._model_cache[oid])
        self._model_cache[newname] = obj
        
    def set_option(self, fun, group, option, value):
        q = """INSERT INTO group_options (`for`, name, value, changed_by) VALUES (:id, :name, :value, :changed_by)
               ON DUPLICATE KEY UPDATE value=:value"""
        self.db.put(q, id=group.oid, name=option.oid, value=value, changed_by=fun.session.authuser)
        
    def unset_option(self, fun, group, option):
        q = """DELETE FROM group_options WHERE `for`=:id AND name=:name"""
        if not self.db.put(q, id=group.oid, name=option.oid):
            raise ExtOptionNotSetError()
