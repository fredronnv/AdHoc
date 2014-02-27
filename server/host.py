#!/usr/bin/env python2.6
from rpcc import *
from optionspace import ExtOptionspace, ExtOrNullOptionspace
from group import ExtGroup
from room import ExtRoomName, ExtRoom
from option_def import ExtOptionDef, ExtOptionNotSetError, ExtOptions
from optionset import *
from util import *
from option_def import *


class ExtNoSuchHostError(ExtLookupError):

    desc = "No such host exists."


class ExtHostAlreadyExistsError(ExtLookupError):
    desc = "The host name already exists"

    
class ExtHostInUseError(ExtValueError):
    desc = "The host is referred to by other objects. It cannot be destroyed"    

 
class ExtHostName(ExtString):
    name = "host-name"
    desc = "Name of a host"
    regexp = r"^[-a-zA-Z0-9_]+$"
    maxlen = 64
    
    
class ExtHostStatus(ExtEnum):
    name = "host-status"
    desc = "Status of host entry"
    values = ["Active", "Inactive", "Dead"]
    

class ExtDNSName(ExtString):
    name = "fqdn"
    desc = "A fully qualified and defined DNS name"
    regexp = r'^([0-9a-zA-Z][-0-9a-zA-Z]+\.)+[a-z0-9\-]{2,15}$'
    maxlen = 255
    
    def lookup(self, fun, cval):
        try:
            dummy = socket.gethostbyname(cval)
            
        except socket.gaierror:
            raise ExtNoSuchDNSNameError()
        return cval
        
    
class ExtHostDns(ExtOrNull):
    name = "host_fqdn"
    desc = "The fully qualified DNS name of a host, if statically allocated"
    typ = ExtString
    regexp = r'^([0-9a-zA-Z][-0-9a-zA-Z]+\.)+[a-z0-9\-]{2,15}$'
    maxlen = 255
    
    
class ExtMacAddress(ExtString):
    name = "mac-address"
    desc = "A valid MAC address"
    regexp = r"^([0-9a-fA-F]{1,2}[\.:-]){5}([0-9A-Fa-f]{1,2})$"
    maxlen = 17


class ExtHost(ExtHostName):
    name = "host"
    desc = "A host instance"

    def lookup(self, fun, cval):
        return fun.host_manager.get_host(cval)

    def output(self, fun, obj):
        return obj.oid
    
    
class ExtHostCreateOptions(ExtStruct):
    name = "host_create_options"
    desc = "Optional parameters when creating a host"
    
    optional = {
                "optionspace": (ExtOptionspace, "Whether the host should declare an option space"),
                "dns": (ExtDNSName, "A DNS name to be used as a fixed address"),
                "group": (ExtGroup, "A Host group to which the host will belong. Default is the group 'plain'"),
                "room": (ExtRoom, "A room name signifying the location of the host"),
                "info": (ExtString, "Information about the host"),
                "status": (ExtHostStatus, "Initial status of the host, default=Active"),
                }
    
    
class ExtHostInfo(ExtOrNull):
    name = "host_info"
    desc = "Information about a host"
    typ = ExtString


class ExtHostRoom(ExtOrNull):
    name = "host_room"
    desc = "Location of a host"
    typ = ExtString


class HostFunBase(SessionedFunction):  
    params = [("host", ExtHost, "Host name")]
    
    
class HostCreate(SessionedFunction):
    extname = "host_create"
    params = [("host_name", ExtHostName, "Name of DHCP host to create"),
              ("mac", ExtMacAddress, "MAC address of the host"),
              ("options", ExtHostCreateOptions, "Create options")]
    desc = "Creates a host"
    returns = (ExtNull)

    def do(self):
        self.host_manager.create_host(self, self.host_name, self.mac, self.options)


class HostDestroy(HostFunBase):
    extname = "host_destroy"
    desc = "Destroys a DHCP host"
    returns = (ExtNull)

    def do(self):
        self.host_manager.destroy_host(self, self.host)


class HostOptionsUpdate(HostFunBase):
    extname = "host_options_update"
    desc = "Update option value(s) on a host"
    returns = (ExtNull)
    
    @classmethod
    def get_parameters(cls):
        pars = super(HostOptionsUpdate, cls).get_parameters()
        ptype = Optionset._update_type(0)
        ptype.name = "host-" + ptype.name
        pars.append(("updates", ptype, "Fields and updates"))
        return pars
    
    def do(self):
        omgr = self.optionset_manager
        optionset = omgr.get_optionset(self.host.optionset)
        for (key, value) in self.updates.iteritems():
            optionset.set_option_by_name(key, value)


class Host(Model):
    name = "host"
    exttype = ExtHost
    id_type = unicode

    def init(self, *args, **kwargs):
        a = list(args)
        #print "Host.init", a
        self.oid = a.pop(0)
        self.dns = a.pop(0)
        self.group = a.pop(0)
        self.mac = a.pop(0)
        self.room = a.pop(0)
        self.optionspace = a.pop(0)
        self.info = a.pop(0)
        self.status = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)
        self.optionset = a.pop(0)

    @template("host", ExtHost)
    def get_host(self):
        #print "GET_GROUP"
        return self

    @template("group", ExtGroup)
    def get_group(self):
        p = self.group_manager.get_group(self.group)
        return p
    
    @template("optionspace", ExtOrNullOptionspace)
    def get_optionspace(self):
        return self.optionspace
    
    @template("dns", ExtHostDns)
    def get_dns(self):
        return self.dns
    
    @template("mac", ExtMacAddress)
    def get_mac(self):
        return self.mac
    
    @template("room", ExtHostRoom)
    def get_room(self):
        return self.room
    
    @template("status", ExtHostStatus)
    def get_status(self):
        return self.status
    
    @template("info", ExtHostInfo)
    def get_info(self):
        return self.info
    
    @template("mtime", ExtDateTime, desc="Time of last change")
    def get_mtime(self):
        return self.mtime
    
    @template("changed_by", ExtString, desc="User who did the last change")
    def get_changed_by(self):
        return self.changed_by
    
    @template("options", ExtOptionKeyList, desc="List of options defined for this host")
    def list_options(self):
        return self.get_optionset().list_options()
    
    @template("optionset", ExtOptionset, model=Optionset)
    def get_optionset(self):
        return self.optionset_manager.get_optionset(self.optionset)
    
    @update("host", ExtString)
    @entry(AuthRequiredGuard)
    def set_name(self, host_name):
        nn = str(host_name)
        q = "UPDATE hosts SET id=:value WHERE id=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=nn)
        #print "Host %s changed Name to %s" % (self.oid, nn)
        self.manager.rename_host(self, nn)
        
    @update("info", ExtString)
    @entry(AuthRequiredGuard)
    def set_info(self, value):
        q = "UPDATE hosts SET info=:value WHERE id=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=value)
        #print "Host %s changed Info to %s" % (self.oid, value)
    
    @update("group", ExtGroup)
    @entry(AuthRequiredGuard)
    def set_parent(self, value):
        q = "UPDATE hosts SET `group`=:value WHERE id=:name"
        self.db.put(q, name=self.oid, value=value.oid)
        
    @update("optionspace", ExtOrNullOptionspace)
    @entry(AuthRequiredGuard)
    def set_optionspace(self, value):
        q = "UPDATE hosts SET optionspace=:value WHERE id=:name"
        self.db.put(q, name=self.oid, value=value)
        
    @update("mac", ExtMacAddress)
    @entry(AuthRequiredGuard)
    def set_mac(self, value):
        q = "UPDATE hosts SET mac=:value WHERE id=:name"
        self.db.put(q, name=self.oid, value=value)
    
    @update("room", ExtRoomName)
    @entry(AuthRequiredGuard)
    def set_room(self, value):
        try:
            q = "UPDATE hosts SET room=:value WHERE id=:name"
            self.db.put(q, name=self.oid, value=value)
        except IntegrityError as e:
            self.room_manager.create_room(self.function, value, None, "Auto-created by host_set_room")
            self.db.put(q, name=self.oid, value=value)
            
    @update("dns", ExtDNSName)
    @entry(AuthRequiredGuard)
    def set_dns(self, value):
        q = "UPDATE hosts SET dns=:value WHERE id=:name"
        self.db.put(q, name=self.oid, value=value)
        
    @update("status", ExtHostStatus)
    @entry(AuthRequiredGuard)
    def set_status(self, value):
        q = "UPDATE hosts SET entry_status=:value WHERE id=:name"
        self.db.put(q, name=self.oid, value=value)
            

class HostManager(Manager):
    name = "host_manager"
    manages = Host

    model_lookup_error = ExtNoSuchHostError

    def init(self):
        self._model_cache = {}
        
    def base_query(self, dq):
        dq.select("h.id", "h.dns", "h.`group`", "h.mac", "h.room", 
                  "h.optionspace", "h.info", "h.entry_status", 
                  "h.mtime", "h.changed_by", "h.optionset")
        dq.table("hosts h")
        return dq
        
    def get_host(self, host_name):
        return self.model(host_name)

    def search_select(self, dq):
        dq.table("hosts h")
        dq.select("h.id")
    
    @search("host", StringMatch)
    def s_name(self, dq):
        dq.table("hosts h")
        return "h.id"
    
    @search("group", StringMatch)
    def s_parent(self, dq):
        dq.table("hosts h")
        return "h.`group`"
    
    @search("status", StringMatch)
    def s_status(self, dq):
        dq.table("hosts h")
        return "h.`entry_status`"
    
    @search("info", StringMatch)
    def s_info(self, dq):
        dq.table("hosts h")
        return "h.`info`"
    
    @search("room", StringMatch)
    def s_room(self, dq):
        dq.table("hosts h")
        return "h.`room`"
    
    @search("mac", StringMatch)
    def s_mac(self, dq):
        dq.table("hosts h")
        return "h.`mac`"
    
    @search("dns", StringMatch)
    def s_dns(self, dq):
        dq.table("hosts h")
        return "h.`dns`"
    
    @entry(AuthRequiredGuard)
    def create_host(self, fun, host_name, mac, options):
        if options == None:
            options = {}
            
        optionspace = options.get("optionspace", None)
        dns = options.get("dns", None)
        group = options.get("group", self.group_manager.get_group(u"plain"))
        room = options.get("room", None)
        if room:
            room = room.oid
        info = options.get("info", None)
        status = options.get("status", "Active")
        
        optionset = self.optionset_manager.create_optionset()
            
        q = """INSERT INTO hosts (id, dns, `group`, mac, room, optionspace, info, entry_status, changed_by, optionset) 
               VALUES (:host_name, :dns, :group, :mac, :room, :optionspace, :info, :entry_status, :changed_by, :optionset)"""
        try:
            self.db.put(q, host_name=host_name, dns=dns, group=group.oid, 
                        mac=mac, room=room, optionspace=optionspace,
                        info=info, changed_by=fun.session.authuser,
                        entry_status=status,
                        optionset=optionset)
            
        except IntegrityError, e:
            print e
            raise ExtHostAlreadyExistsError()
        
    @entry(AuthRequiredGuard)
    def destroy_host(self, fun, host):
        
        host.get_optionset().destroy()
        
        q = "DELETE FROM hosts WHERE id=:hostname LIMIT 1"
        try:
            self.db.put(q, hostname=host.oid)
        except IntegrityError:
            raise ExtHostInUseError
        
        #print "Host destroyed, name=", host.oid
        
    def rename_host(self, obj, newname):
        oid = obj.oid
        obj.oid = newname
        del(self._model_cache[oid])
        self._model_cache[newname] = obj
