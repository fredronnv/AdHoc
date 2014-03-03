#!/usr/bin/env python2.6

from rpcc import *
from optionspace import *
from optionset import *
from option_def import *


class ExtNoSuchGroupError(ExtLookupError):
    desc = "No such group exists."


class ExtGroupAlreadyExistsError(ExtLookupError):
    desc = "The group name is already in use"

    
class ExtGroupInUseError(ExtValueError):
    desc = "The group is referred to by other objects. It cannot be destroyed"    


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


class GroupOptionsUpdate(GroupFunBase):
    extname = "group_options_update"
    desc = "Update option value(s) on a group"
    returns = (ExtNull)
    
    @classmethod
    def get_parameters(cls):
        pars = super(GroupOptionsUpdate, cls).get_parameters()
        ptype = Optionset._update_type(0)
        ptype.name = "group-" + ptype.name
        pars.append(("updates", ptype, "Fields and updates"))
        return pars
    
    def do(self):
        omgr = self.optionset_manager
        optionset = omgr.get_optionset(self.group.optionset)
        for (key, value) in self.updates.iteritems():
            optionset.set_option_by_name(key, value)


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
        self.optionset = a.pop(0)

    @template("group", ExtGroup)
    def get_group(self):
        #print "GET_GROUP"
        return self

    @template("parent", ExtGroup)
    def get_parent(self):
        p = self.manager.get_parent(self.parent)
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
    
    @template("options", ExtOptionKeyList, desc="List of options defined for this group")
    def list_options(self):
        return self.get_optionset().list_options()
    
    @template("optionset", ExtOptionset, model=Optionset)
    def get_optionset(self):
        return self.optionset_manager.get_optionset(self.optionset)
    
    @update("group", ExtString)
    @entry(AuthRequiredGuard)
    def set_name(self, group_name):
        nn = str(group_name)
        q = "UPDATE groups SET groupname=:value WHERE groupname=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=nn)
        
        #print "Group %s changed Name to %s" % (self.oid, nn)
        self.manager.rename_group(self, nn)
        
    @update("info", ExtString)
    @entry(AuthRequiredGuard)
    def set_info(self, value):
        q = "UPDATE groups SET info=:value WHERE groupname=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=value)
        
        #print "Group %s changed Info to %s" % (self.oid, value)
    
    @update("parent", ExtString)
    @entry(AuthRequiredGuard)
    def set_parent(self, value):
        q = "UPDATE groups SET parent_group=:value WHERE groupname=:name"
        self.db.put(q, name=self.oid, value=value)
                
    @update("optionspace", ExtOrNullOptionspace)
    @entry(AuthRequiredGuard)
    def set_optionspace(self, value):
        q = "UPDATE groups SET optionspace=:value WHERE groupname=:name"
        self.db.put(q, name=self.oid, value=value)
        

class GroupManager(Manager):
    name = "group_manager"
    manages = Group

    model_lookup_error = ExtNoSuchGroupError

    def init(self):
        self._model_cache = {}
        
    def base_query(self, dq):
        dq.select("g.groupname", "g.parent_group", "g.optionspace",
                  "g.info", "g.mtime", "g.changed_by", "g.optionset")
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
        return "g.parent_group"
    
    @entry(AuthRequiredGuard)
    def create_group(self, fun, group_name, parent, info, options):
        if options == None:
            options = {}
        optionspace = options.get("optionspace", None)
        
        optionset = self.optionset_manager.create_optionset()
            
        q = """INSERT INTO groups (groupname, parent_group, optionspace, info, changed_by, optionset) 
               VALUES (:group_name, :parent, :optionspace, :info, :changed_by, :optionset)"""
        try:
            self.db.insert("id", q, group_name=group_name, parent=parent.oid, optionspace=optionspace,
                       info=info, changed_by=fun.session.authuser, optionset=optionset)
            print "Group created, name=", group_name
            
        except IntegrityError, e:
            raise ExtGroupAlreadyExistsError()
        
    @entry(AuthRequiredGuard)
    def destroy_group(self, fun, group):
        group.get_optionset().destroy()
        q = "DELETE FROM groups WHERE groupname=:groupname LIMIT 1"
        try:
            self.db.put(q, groupname=group.oid)
        except IntegrityError:
            raise ExtGroupInUseError()
        
    def rename_group(self, obj, newname):
        oid = obj.oid
        obj.oid = newname
        del(self._model_cache[oid])
        self._model_cache[newname] = obj
        
    @entry(AuthRequiredGuard)
    def set_option(self, fun, group, option, value):
        q = """INSERT INTO group_options (`for`, name, value, changed_by) VALUES (:id, :name, :value, :changed_by)
               ON DUPLICATE KEY UPDATE value=:value"""
        self.db.put(q, id=group.oid, name=option.oid, value=value, changed_by=fun.session.authuser)
        
    @entry(AuthRequiredGuard)
    def unset_option(self, fun, group, option):
        q = """DELETE FROM group_options WHERE `for`=:id AND name=:name"""
        if not self.db.put(q, id=group.oid, name=option.oid):
            raise ExtOptionNotSetError()
