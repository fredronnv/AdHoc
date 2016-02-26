#!/usr/bin/env python2.6

# $Id$

from rpcc import *
from optionspace import *
from room import *
from optionset import *
from util import *
from option_def import *
from group import ExtGroup, ExtNoSuchGroupError
from datetime import date

g_read = AnyGrants(AllowUserWithPriv("write_all_hosts"), AllowUserWithPriv("read_all_hosts"), AdHocSuperuserGuard)
g_write = AnyGrants(AllowUserWithPriv("write_all_hosts"), AdHocSuperuserGuard)


class ExtNoSuchHostError(ExtLookupError):
    desc = "No such host exists."


class ExtHostAlreadyExistsError(ExtLookupError):
    desc = "The host name already exists"


class ExtDNSUsedByOtherMacError(ExtValueError):
    desc = "The DNS address is already in use by a host with another MAC address"


class ExtHostInUseError(ExtValueError):
    desc = "The host is referred to by other objects. It cannot be destroyed"    

 
# class ExtHostName(ExtString): is defined in util.py to break an import loop
 
    
class ExtHostStatus(ExtEnum):
    name = "host-status"
    desc = "Status of host entry"
    values = ["Active", "Inactive", "Dead"]
    

class ExtDNSName(ExtString):
    name = "fqdn"
    desc = "A fully qualified and defined DNS name"
    regexp = r'^([0-9a-zA-Z][-0-9a-zA-Z]*\.)+[a-zA-Z0-9\-]{2,15}$'
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
    typ = ExtDNSName
    regexp = r'^([0-9a-zA-Z][-0-9a-zA-Z]*\.)+[a-zA-Z0-9\-]{2,15}$'
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


class ExtNewHostName(ExtHostName):
    name = "host"
    desc = "A host name not present in the database"
   
    def lookup(self, fun, cval):
        if fun.host_manager.get_host(cval):
            raise ExtHostAlreadyExistsError()
 
 
class ExtHostInfo(ExtOrNull):
    name = "host_info"
    desc = "Information about a host"
    typ = ExtString


class ExtHostRoom(ExtOrNull):
    name = "host_room"
    desc = "Location of a host"
    typ = ExtRoomName
    
    
class ExtHostAccount(ExtOrNull):
    name = "host_account"
    desc = "Host owner or responsible"
    typ = ExtString
    
    def lookup(self, fun, cval):
        if cval is None:
            return None
        
        fun.account_manager.get_account(str(cval))  # We don't look up the account here, just checking that it exists
        return cval
    
    
class ExtHostCreateOptions(ExtStruct):
    name = "host_create_options"
    desc = "Optional parameters when creating a host"
    
    optional = {"optionspace": (ExtOptionspace, "Whether the host should declare an option space"),
                "dns": (ExtDNSName, "A DNS name to be used as a fixed address"),
                "group": (ExtGroup, "A Host group to which the host will belong. Default is the group 'plain'"),
                "room": (ExtRoom, "A room name signifying the location of the host"),
                "info": (ExtString, "Information about the host"),
                "status": (ExtHostStatus, "Initial status of the host, default=Active"),
                "same_as": (ExtHost, "Create host entry as an instance of this host"),
                "cid": (ExtHostAccount, "Account of the owner or responsible person")
                }
    

class HostFunBase(SessionedFunction):  
    params = [("host", ExtHost, "Host name")]
    
    
class HostCreateWithName(SessionedFunction):
    extname = "host_create_with_name"
    params = [("host_name", ExtHostName, "Name of DHCP host to create"),
              ("mac", ExtMacAddress, "MAC address of the host"),
              ("options", ExtHostCreateOptions, "Create options")]
    desc = "Creates a host"
    returns = (ExtNull)

    def do(self):
        self.host_manager.create_host(self, self.host_name, self.mac, self.options)
  
        
class HostCreate(SessionedFunction):
    extname = "host_create"
    params = [("mac", ExtMacAddress, "MAC address of the host"),
              ("options", ExtHostCreateOptions, "Create options")]
    desc = "Creates a host"
    returns = (ExtHostName)

    def do(self):
        return self.host_manager.create_host(self, None, self.mac, self.options)


class HostDestroy(HostFunBase):
    extname = "host_destroy"
    desc = "Destroys a DHCP host"
    returns = (ExtNull)

    def do(self):
        self.host_manager.destroy_host(self, self.host)


class HostLiteralOptionAdd(HostFunBase):
    extname = "host_literal_option_add"
    desc = "Add a literal option to a host"
    returns = (ExtInteger, "ID of added literal option")
    params = [("option_text", ExtString, "Text of literal option")]
    
    def do(self):
        return self.host_manager.add_literal_option(self, self.host, self.option_text)
    
    
class HostLiteralOptionDestroy(HostFunBase):
    extname = "host_literal_option_destroy"
    desc = "Destroy a literal option from a host"
    returns = (ExtNull)
    params = [("option_id", ExtInteger, "ID of literal option to destroy")]
    
    def do(self):
        return self.host_manager.destroy_literal_option(self, self.host, self.option_id)
        
    
class HostOptionsUpdate(HostFunBase):
    extname = "host_option_update"
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
        self.host_manager.update_options(self, self.host, self.updates)


class Host(AdHocModel):
    name = "host"
    exttype = ExtHost
    id_type = unicode

    def init(self, *args, **kwargs):
        a = list(args)
        # print "Host.init", a
        self.oid = a.pop(0)
        self.dns = a.pop(0)
        self.group = a.pop(0)
        self.mac = a.pop(0)
        self.cid = a.pop(0)
        self.room = a.pop(0)
        self.optionspace = a.pop(0)
        self.info = a.pop(0)
        self.status = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)
        self.optionset = a.pop(0)

    @template("host", ExtHost)
    def get_host(self):
        # print "GET_HOST"
        return self

    @template("group", ExtGroup, desc="Group which the host belongs to")
    def get_group(self):
        p = self.group_manager.get_group(self.group)
        return p
    
    @template("optionspace", ExtOrNullOptionspace)
    def get_optionspace(self):
        return self.optionspace
    
    @template("dns", ExtHostDns, desc="The Domain Name System address of the host")
    def get_dns(self):
        return self.dns
    
    @template("cid", ExtHostAccount, desc="Account of the owner or responsible person")
    def get_cid(self):
        if self.cid:
            a = self.account_manager.get_account(self.cid)
            return a.oid
        return None
    
    @template("mac", ExtMacAddress, desc="The Media Access Control address of the host")
    def get_mac(self):
        return self.mac
    
    @template("room", ExtHostRoom, desc="Expected location of the host")
    def get_room(self):
        return self.room
    
    @template("status", ExtHostStatus, desc="Status of the host")
    def get_status(self):
        return self.status
    
    @template("info", ExtHostInfo, desc="Notes about the host")
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
        # print self, self.optionset
        return self.optionset_manager.get_optionset(self.optionset)
    
    @template("literal_options", ExtLiteralOptionList, desc="List of literal options defined for this host")
    def get_literal_options(self):
        q = "SELECT value, changed_by, id FROM host_literal_options WHERE `for`= :host"
        ret = []
        for (value, changed_by, id) in self.db.get(q, host=self.oid):
            d = {"value": value,
                 "changed_by": changed_by,
                 "id": id}
            ret.append(d)
        return ret
    
    @update("host", ExtString)
    @entry(g_write)
    def set_name(self, host_name):
        nn = str(host_name)
        q = "UPDATE hosts SET id=:value WHERE id=:name LIMIT 1"
        try:
            self.db.put(q, name=self.oid, value=nn)
        except IntegrityError as e:
            self.server.logger.error(str(e))
            raise ExtHostAlreadyExistsError()
        # print "Host %s changed Name to %s" % (self.oid, nn)
        self.manager.rename_object(self, nn)
        self.event_manager.add("rename", host=self.oid, newstr=nn, authuser=self.function.session.authuser)
        
    @update("info", ExtHostInfo)
    @entry(g_write)
    def set_info(self, value):
        q = "UPDATE hosts SET info=:value WHERE id=:name LIMIT 1"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update", host=self.oid, info=value, authuser=self.function.session.authuser)
        # print "Host %s changed Info to %s" % (self.oid, value)
    
    @update("group", ExtGroup)
    @entry(g_write)
    def set_group(self, new_group):
        q = "UPDATE hosts SET `group`=:new_group WHERE id=:name"
        self.db.put(q, name=self.oid, new_group=new_group.oid)
        self.group_manager.adjust_hostcount(self.get_group(), -1)
        self.group_manager.adjust_hostcount(new_group, +1)
        self.event_manager.add("disconnect", host=self.oid, parent_object=self.group, authuser=self.function.session.authuser)
        self.event_manager.add("connect", host=self.oid, parent_object=new_group.oid, authuser=self.function.session.authuser)
        
    @update("optionspace", ExtOrNullOptionspace)
    @entry(g_write)
    def set_optionspace(self, value):
        q = "UPDATE hosts SET optionspace=:value WHERE id=:name"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update", host=self.oid, optionspace=value, authuser=self.function.session.authuser)
        
    @update("mac", ExtMacAddress)
    @entry(g_write)
    def set_mac(self, value):
        
        if self.dns:
            if not self.db.get("SELECT dns FROM hosts WHERE dns=:value AND id != :name", value=self.dns, name=self.oid):
                self.db.put("DELETE FROM dnsmac WHERE dns=:dns", dns=self.dns)
            try:
                self.db.put("INSERT INTO dnsmac (dns, mac) VALUES (:dns, :mac)", dns=self.dns, mac=value)
            except IntegrityError, e:
                raise ExtDNSUsedByOtherMacError()
        
        q = "UPDATE hosts SET mac=:value WHERE id=:name"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update", host=self.oid, mac=value, authuser=self.function.session.authuser)
    
    @update("room", ExtHostRoom)
    @entry(g_write)
    def set_room(self, value):
        try:
            q = "UPDATE hosts SET room=:value WHERE id=:name"
            self.db.put(q, name=self.oid, value=value)
        except IntegrityError as e:
            self.room_manager.create_room(self.function, value, None, "Auto-created by host_set_room")
            self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update", host=self.oid, room=value, authuser=self.function.session.authuser)
            
    @update("dns", ExtHostDns)
    @entry(g_write)
    def set_dns(self, value):
        if self.dns:
            if not self.db.get("SELECT dns FROM hosts WHERE dns=:value AND id != :name", value=self.dns, name=self.oid):
                self.db.put("DELETE FROM dnsmac WHERE dns=:dns", dns=self.dns)
        if value:
            if not self.db.get("SELECT dns, mac FROM dnsmac WHERE dns=:dns and mac=:mac", dns=value, mac=self.mac):
                try:    
                    self.db.put("INSERT INTO dnsmac (dns, mac) VALUES (:dns, :mac)", dns=value, mac=self.mac)
                except IntegrityError as e:
                    raise ExtDNSUsedByOtherMacError()
        q = "UPDATE hosts SET dns=:value WHERE id=:name"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update", host=self.oid, dns=value, authuser=self.function.session.authuser)
        
    @update("cid", ExtHostAccount)
    @entry(g_write)
    def set_cid(self, account):
        q = "UPDATE hosts SET cid=:value WHERE id=:name"
        self.db.put(q, name=self.oid, value=account)
        self.event_manager.add("update", host=self.oid, cid=account, authuser=self.function.session.authuser)
        
    @update("status", ExtHostStatus)
    @entry(g_write)
    def set_status(self, value):
        if self.status == "Active" and value != "Active":
            self.group_manager.adjust_hostcount(self.get_group(), -1)
        if self.status != "Active" and value == "Active":
            self.group_manager.adjust_hostcount(self.get_group(), 1)
        q = "UPDATE hosts SET entry_status=:value WHERE id=:name"
        self.db.put(q, name=self.oid, value=value)
        self.event_manager.add("update", host=self.oid, entry_status=value, authuser=self.function.session.authuser)
            

class HostManager(AdHocManager):
    name = "host_manager"
    manages = Host

    model_lookup_error = ExtNoSuchHostError

    def init(self):
        self._model_cache = {}
        
    @classmethod
    def base_query(cls, dq):
        dq.select("h.id", "h.dns", "h.`group`", "h.mac", "h.cid", "h.room", 
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
    
    @search("current_member_of", StringMatch)
    def s_current_member_of(self, dq):
        dq.table("hosts h")
        dq.table("group_groups_flat ggf")
        dq.where("h.`group` = ggf.descendant")
        return ("ggf.groupname")
    
    @search("status", StringMatch)
    def s_status(self, dq):
        dq.table("hosts h")
        return "h.`entry_status`"
    
    @search("info", NullableStringMatch)
    def s_info(self, dq):
        dq.table("hosts h")
        return "h.`info`"
    
    @search("cid", NullableStringMatch)
    def s_cid(self, dq):
        dq.table("hosts h")
        return "h.`cid`"
    
    @search("room", NullableStringMatch)
    def s_room(self, dq):
        dq.table("hosts h")
        return "h.`room`"
    
    @search("mac", StringMatch)
    def s_mac(self, dq):
        dq.table("hosts h")
        return "h.`mac`"
    
    @search("dns", NullableStringMatch)
    def s_dns(self, dq):
        dq.table("hosts h")
        return "h.`dns`"
    
    # Note: This seems to do the trick I want, but I don't understand why...
    @search("granted_for", StringMatch)
    def s_granted_for(self, q):
        q.table("pool_host_map phm")
        q.where("h.id = phm.hostname")
        return "phm.poolname"
    
    @search("optionset", IntegerMatch, desc="Server internal option set number")
    def s_optionset(self, dq):
        dq.table("hosts h")
        return "h.optionset"
    
    def generate_host_name(self, mac, today=None, same_as=None):
        """ Generates a free host name according to standard naming devised by the networking group"""
        
        if not today:
            today = date.today().strftime("%Y%m%d")
            
        if not same_as:
            q = """SELECT DISTINCT SUBSTR(id,1,12) FROM hosts WHERE id LIKE '%s-%%%%' ORDER BY id""" % today
            
            res = self.db.get(q)
            
            found_id = None
            for row in res:
                found_id = row[0]
            if found_id:
                index = int(found_id[9:12])
                new_index = index + 1
            else:
                new_index = 1
            name = today + "-%03d" % new_index
            
            if mac == "00:00:00:00:00:00":
                return name + "A"  # This mac is so special so we do not squeeze these macs togetrer.
            
            q = """SELECT DISTINCT substr(id, 1, 12)  mac FROM hosts WHERE mac=:mac"""
            res = self.db.get(q, mac=mac)
            if len(res) == 0:
                return name + "A"  # No contenders
            if len(res) > 1:
                raise ExtInternalError("piano")
            name = res[0][0]

            q = """SELECT id, mac from hosts WHERE substr(id, 1, 12) = :name"""
            res = self.db.get(q, name=name)
            if len(res) < 1:
                raise ExtInternalError("taklampa")
            count = len(res)
                  
        else:
            name = same_as.oid[0:12]
            q = """SELECT id, mac from hosts WHERE substr(id, 1, 12) = :name"""
            res = self.db.get(q, name=name)
            if len(res) < 1:
                raise ExtInternalError("skrivbordslampa")
            count = len(res)

        if count > 0:
            name = res[0][0][0:12]  # Pick old ID prefix if mac or name already found
            
        r = ""
        while count > 0:
            r = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[count % 26] + r
            count //= 26
        if r == "":
            name += "A"
        else:
            name += r
        
        return name
            
    @entry(g_write)
    def create_host(self, fun, host_name, mac, options):
        if options is None:
            options = {}
        
        optionspace = options.get("optionspace", None)
        dns = options.get("dns", None)
        group = options.get("group", self.group_manager.get_group(u"plain"))
        room = options.get("room", None)
        if room:
            room = room.oid
        info = options.get("info", None)
        status = options.get("status", "Active")
        same_as = options.get("same_as", None)
        cid = options.get("cid", None)
        
        if not host_name:
            host_name = self.generate_host_name(mac, same_as=same_as)
        
        optionset = self.optionset_manager.create_optionset(fun)
        
        if dns:
            res = self.db.get("SELECT dns, mac FROM dnsmac WHERE dns=:dns", dns=dns)
            if not res:
                try:    
                    self.db.put("INSERT INTO dnsmac (dns, mac) VALUES (:dns, :mac)", dns=dns, mac=mac)
                except IntegrityError as e:
                    raise ExtDNSUsedByOtherMacError()
            else:
                dns, stored_mac = res[0]
                if mac != stored_mac:
                    raise ExtDNSUsedByOtherMacError()        
            
        q = """INSERT INTO hosts (id, dns, `group`, mac, room, optionspace, info, entry_status, cid, changed_by, optionset) 
               VALUES (:host_name, :dns, :group, :mac, :room, :optionspace, :info, :entry_status, :cid, :changed_by, :optionset)"""
        try:
            self.db.put(q, host_name=host_name, dns=dns, group=group.oid, 
                        mac=mac, room=room, optionspace=optionspace,
                        info=info, changed_by=fun.session.authuser,
                        entry_status=status,
                        cid=cid, optionset=optionset)
            
        except IntegrityError, e:
            self.logger.error(str(e))
            raise ExtHostAlreadyExistsError()
        
        self.event_manager.add("create", host=host_name, 
                               dns=dns, group=group.oid, 
                               mac=mac, room=room, optionspace=optionspace,
                               info=info, authuser=fun.session.authuser,
                               entry_status=status, cid=cid,
                               optionset=optionset)
        if status == "Active":
            self.group_manager.adjust_hostcount(group, 1)
        return host_name
        
    @entry(g_write)
    def destroy_host(self, fun, host):
        
        host.get_optionset().destroy()
        
        # First check if we shoudl remove the mac-dns entry
        
        if host.dns:
            q = """SELECT dns, mac FROM hosts WHERE id != :hostname AND dns=:dns"""
            res = self.db.get(q, hostname=host.oid, dns=host.dns)
        
            if not res:
                self.db.put("DELETE FROM dnsmac WHERE dns=:dns", dns=host.dns)
            
        try:
            q = "DELETE FROM hosts WHERE id=:hostname LIMIT 1"
            self.db.put(q, hostname=host.oid)
        except IntegrityError:
            raise ExtHostInUseError
        
        q = "DELETE FROM host_literal_options WHERE `for`=:hostname"
        self.db.put(q, hostname=host.oid)
        
        self.event_manager.add("destroy", host=host.oid, dns=host.dns, mac=host.mac, authuser=fun.session.authuser)
        
        if host.status == "Active":
            gm = self.group_manager
            try:
                grp = gm.get_group(host.group)
                self.group_manager.adjust_hostcount(grp, -1)
            except ExtNoSuchGroupError:
                pass
        
        # print "Host destroyed, name=", host.oid
       
    @entry(g_write_literal_option)
    def add_literal_option(self, fun, host, option_text):
        q = "INSERT INTO host_literal_options (`for`, value, changed_by) VALUES (:hostname, :value, :changed_by)"
        id = self.db.insert("id", q, hostname=host.oid, value=option_text, changed_by=fun.session.authuser)
        self.approve_config = True
        self.approve()
        self.event_manager.add("create", host=host.oid, literal_option_id=id, literal_option_value=unicode(option_text), authuser=fun.session.authuser)
        return id
    
    @entry(g_write_literal_option)
    def destroy_literal_option(self, fun, host, id):
        q = "DELETE FROM host_literal_options WHERE `for`=:hostname AND id=:id LIMIT 1"
        self.db.put(q, hostname=host.oid, id=id)
        self.event_manager.add("destroy", host=host.oid, literal_option_id=id, authuser=fun.session.authuser)
        
    @entry(g_write)
    def update_options(self, fun, host, updates):
        omgr = fun.optionset_manager
        optionset = omgr.get_optionset(host.optionset)
        for (key, value) in updates.iteritems():
            optionset.set_option_by_name(key, value)
            self.event_manager.add("update", host=host.oid, option=key, option_value=unicode(value), authuser=fun.session.authuser)

