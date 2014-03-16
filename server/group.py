#!/usr/bin/env python2.6

from rpcc import *
from optionspace import *
from optionset import *
from option_def import *
from util import *


g_read = AnyGrants(AllowUserWithPriv("read_all_groups"), AdHocSuperuserGuard)
g_write = AnyGrants(AllowUserWithPriv("write_all_groups"), AdHocSuperuserGuard)

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

class ExtGroupList(ExtList):
    name = "group-list"
    desc = "List of group names"
    typ = ExtGroupName
    
class ExtHostCount(ExtOrNull):
    name = "hostcount"
    desc = "Count of avtive hosts in group and its descendants, or NULL if unknown"
    typ = ExtInteger
    
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

class GroupLiteralOptionAdd(GroupFunBase):
    extname = "group_literal_option_add"
    desc = "Add a literal option to a group"
    returns =(ExtInteger, "ID of added literal option")
    params = [("option_text", ExtString, "Text of literal option")]
    
    def do(self):
        return self.group_manager.add_literal_option(self, self.group, self.option_text)
    
    
class GroupLiteralOptionDestroy(GroupFunBase):
    extname = "group_literal_option_destroy"
    desc = "Destroy a literal option from a group"
    returns =(ExtNull)
    params = [("option_id", ExtInteger, "ID of literal option to destroy")]
    
    def do(self):
        return self.group_manager.destroy_literal_option(self, self.group, self.option_id)
        
    
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
        self.group_manager.update_options(self, self.group, self.updates)

class GroupGatherStats(SessionedFunction):
    extname = "group_gather_stats"
    returns = ExtNull
    
    def do(self):
        self.group_manager.gather_stats()

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
        self.hostcount = a.pop(0)

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
    
    @template("hostcount", ExtHostCount)
    def get_hostcount(self):
        return self.hostcount
    
    @template("literal_options", ExtLiteralOptionList, desc="List of literal options defined for this group")
    def get_literal_options(self):
        q = "SELECT value, changed_by, id FROM group_literal_options WHERE `for`= :group"
        ret = []
        for (value, changed_by, id) in self.db.get(q, group=self.oid):
            d = {"value":value,
                 "changed_by":changed_by,
                 "id": id}
            ret.append(d)
        return ret
    
    @update("group", ExtString)
    @entry(g_write)
    def set_name(self, group_name):
        nn = str(group_name)
        
        #print "Group %s changed Name to %s" % (self.oid, nn)
        self.manager.rename_group(self, nn)
        
    @update("info", ExtString)
    @entry(g_write)
    def set_info(self, value):
        q = "UPDATE groups SET info=:value WHERE groupname=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=value)
        
        #print "Group %s changed Info to %s" % (self.oid, value)
    
    @update("parent", ExtString)
    @entry(g_write)
    def set_parent(self, value):
        q = "UPDATE groups SET parent_group=:value WHERE groupname=:name"
        self.db.put(q, name=self.oid, value=value)
                
    @update("optionspace", ExtOrNullOptionspace)
    @entry(g_write)
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
                  "g.info", "g.mtime", "g.changed_by", "g.optionset", "g.hostcount")
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
    
    @entry(g_write)
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
        
      # Build the group_groups_flat table
        self.add_group_to_group_groups_flat(group_name, parent)
  
    def add_group_to_group_groups_flat(self, group_name, parent):
        qif = "INSERT INTO group_groups_flat (groupname, descendant) VALUES (:groupname, :descendant)"
        self.db.put(qif, groupname=group_name, descendant=group_name) # The group itself
        g2 = group_name # Traverse the tree upward and fill in the group for every node traversed
        while True:
            parent = self.db.get("SELECT parent_group FROM groups WHERE groupname=:groupname", groupname=g2)[0][0] 
            if not parent or parent == g2:
                break
            self.db.put(qif, groupname=parent, descendant=group_name)
            g2 = parent

         
    @entry(g_write)
    def destroy_group(self, fun, group):
        optionset =  group.get_optionset()
        q = "DELETE FROM groups WHERE groupname=:groupname LIMIT 1"
        try:
            self.db.put(q, groupname=group.oid)
        except IntegrityError:
            raise ExtGroupInUseError()
        optionset.destroy()
   
    @entry(g_rename)    
    def rename_group(self, obj, newname):
        
        oldname = obj.oid
        
        self.db.put("SET foreign_key_checks=0")
        self.db.put("UPDATE groups SET groupname=:value WHERE groupname=:name", name=oldname, value=newname)
        self.db.put("UPDATE group_groups_flat SET descendant=:newname WHERE descendant=:groupname", newname=newname, groupname=oldname)
        self.db.put("UPDATE group_groups_flat SET groupname=:newname WHERE groupname=:groupname", newname=newname, groupname=oldname)
        self.db.put("SET foreign_key_checks=1")
         
        obj.oid = newname
        del(self._model_cache[oldname])
        self._model_cache[newname] = obj
        
    @entry(g_write)
    def set_option(self, fun, group, option, value):
        q = """INSERT INTO group_options (`for`, name, value, changed_by) VALUES (:id, :name, :value, :changed_by)
               ON DUPLICATE KEY UPDATE value=:value"""
        self.db.put(q, id=group.oid, name=option.oid, value=value, changed_by=fun.session.authuser)
        
    @entry(g_write)
    def unset_option(self, fun, group, option):
        q = """DELETE FROM group_options WHERE `for`=:id AND name=:name"""
        if not self.db.put(q, id=group.oid, name=option.oid):
            raise ExtOptionNotSetError()
   
    @entry(g_write_literal_option)
    def add_literal_option(self, fun, group, option_text):
        q = "INSERT INTO group_literal_options (`for`, value, changed_by) VALUES (:groupname, :value, :changed_by)"
        id = self.db.insert("id", q, groupname=group.oid, value=option_text, changed_by=fun.session.authuser)
        return id
    
    @entry(g_write_literal_option)
    def destroy_literal_option(self, fun, group, id):
        q = "DELETE FROM group_literal_options WHERE `for`=:groupname AND id=:id LIMIT 1"
        self.db.put(q, groupname=group.oid, id=id)
    
    @entry(g_write)
    def update_options(self, fun, group, updates):
        omgr = fun.optionset_manager
        optionset = omgr.get_optionset(group.optionset)
        for (key, value) in updates.iteritems():
            optionset.set_option_by_name(key, value)
            
    @entry(AdHocSuperuserGuard)
    def gather_stats(self, parent=None):
        """ Walk through the group tree, count the number of hosts assigned directly or indirectly
            to the group. This count is used primarily for deciding which groups to generate configuration for."""
        if not parent:
            q = "SELECT groupname, parent_group FROM groups WHERE groupname='plain' ORDER BY (CONVERT(groupname USING latin1) COLLATE latin1_swedish_ci)"
            rows = self.db.get_all(q)
        else:
            q = "SELECT groupname, parent_group FROM groups WHERE parent_group=:parent AND groupname!='plain' ORDER BY (CONVERT(groupname USING latin1) COLLATE latin1_swedish_ci)"
            rows = self.db.get_all(q, parent=parent)
        hostcount = 0   
        for (groupname, parent) in rows:
            if not groupname:
                continue
            print "Gather stats for group ", groupname
            hostcount = self.db.get("SELECT COUNT(*) from hosts WHERE `group`= :groupname AND entry_status='Active'", groupname=groupname)[0][0]
            print "Direct host count for %s is %d"%(groupname, hostcount)
            indirect = self.gather_stats(parent=groupname)
            print "Indirect host count for %s is %d"%(groupname, indirect)
            hostcount += indirect
            self.db.put("UPDATE groups SET hostcount=:hostcount WHERE groupname=:groupname", groupname=groupname, hostcount=hostcount)
            print "Group %s has %d active hosts"%(groupname, hostcount)
        return hostcount
 