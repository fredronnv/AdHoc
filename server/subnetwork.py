#!/usr/bin/env python2.6

from rpcc import *
from shared_network import *
import struct
from optionset import *
from option_def import *

g_write = AnyGrants(AllowUserWithPriv("write_all_subnetworks"), AdHocSuperuserGuard)

class ExtNoSuchSubnetworkError(ExtLookupError):
    desc = "No such subnetwork exists."


class ExtSubnetworkAlreadyExistsError(ExtLookupError):
    desc = "The subnetwork ID is already in use"

    
class ExtSubnetworkInUseError(ExtValueError):
    desc = "The subnetwork is referred to by other objects. It cannot be destroyed"  
    
    
class ExtSubnetworkInvalidError(ExtValueError):
    desc = "the subnetwork specifcation is invalid"  


class ExtSubnetworkID(ExtString):
    name = "subnetwork-id"
    desc = "ID of a subnetwork in CIDR notation. [ipaddress/bitcount]"
    regexp = r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\/(\d|[1-2]\d|3[0-2]))$"

    def lookup(self, fun, cval):
        (_ip, n) = cval.split("/", 1)
        n = int(n)
        if n < 1 or n > 31:
            raise ExtSubnetworkInvalidError("The bitcount of the subnetwork specification is out of range, should be between 1 and 31")
        return cval


class ExtSubnetwork(ExtSubnetworkID):
    name = "subnetwork"
    desc = "A defined subnetwork in CIDR notation. [ipaddress/bitcount]"

    def lookup(self, fun, cval):
        return fun.subnetwork_manager.get_subnetwork(str(cval))

    def output(self, fun, obj):
        return obj.oid
    
    
class SubnetworkFunBase(SessionedFunction):  
    params = [("subnetwork", ExtSubnetwork, "Subnetwork ID")]
    
    
class SubnetworkCreate(SessionedFunction):
    extname = "subnetwork_create"
    params = [("subnetwork", ExtSubnetworkID, "ID of new subnetwork"),
              ("network", ExtNetwork, "Shared network that the subnetwork belongs to"),
              ("info", ExtString, "Subnetwork description")]
    desc = "Creates a subnetwork"
    returns = (ExtNull)

    def do(self):
        self.subnetwork_manager.create_subnetwork(self, self.subnetwork, self.network.oid, self.info)
        

class SubnetworkDestroy(SubnetworkFunBase):
    extname = "subnetwork_destroy"
    desc = "Destroys a subnetwork"
    returns = (ExtNull)

    def do(self):
        self.subnetwork_manager.destroy_subnetwork(self, self.subnetwork)
        
        
class SubnetworkOptionsUpdate(SubnetworkFunBase):
    extname = "subnetwork_options_update"
    desc = "Update option value(s) on a subnetwork"
    returns = (ExtNull)
    
    @classmethod
    def get_parameters(cls):
        pars = super(SubnetworkOptionsUpdate, cls).get_parameters()
        ptype = Optionset._update_type(0)
        ptype.name = "subnetwork-" + ptype.name
        pars.append(("updates", ptype, "Fields and updates"))
        return pars
    
    def do(self):
        self.subnetwork_manager.update_options(self, self.subnetwork, self.updates)
            
            
class Subnetwork(AdHocModel):
    name = "subnetwork"
    exttype = ExtSubnetwork
    id_type = str

    def init(self, *args, **kwargs):
        a = list(args)
        self.oid = a.pop(0)
        self.network = a.pop(0)
        self.info = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)
        self.optionset = a.pop(0)

    @template("subnetwork", ExtSubnetwork, desc="The subnetwork")
    def get_subnetwork(self):
        return self

    @template("network", ExtNetworkName, desc="Which shared network the subnetwork belongs to")
    def get_network(self):
        return self.network
    
    @template("netmask", ExtIpV4Address, desc="The netmask corresponding to bit count of the subnetwork")
    def get_netmask(self):
        (_ip, n) = self.oid.split('/', 1)
        bits = 0xffffffff ^ (1 << 32 - n) - 1
        return socket.inet_ntoa(struct.pack('>I', bits))
    
    @template("start_ip", ExtIpV4Address, desc="The start IP address of the subnetwork")
    def get_start_ip(self):
        (ip, _n) = self.oid.split('/', 1)
        return ip
    
    @template("size", ExtInteger, desc="The number of IP addresses covered by the subnetwork")
    def get_size(self):
        (_ip, n) = self.oid.split('/', 1)
        n = int(n)
        print "Subnetwork get_size: n=", n, "_ip=", _ip
        if n >= 32:
            return 0
        return (1 << 32 - n)
        
    @template("info", ExtString, desc="Subnetwork description")
    def get_info(self):
        return self.info
    
    @template("mtime", ExtDateTime, desc="Time of last change")
    def get_mtime(self):
        return self.mtime
    
    @template("changed_by", ExtString, desc="User who did the last change")
    def get_changed_by(self):
        return self.changed_by
    
    @template("options", ExtOptionKeyList, desc="List of options defined for this subnetwork")
    def list_options(self):
        return self.get_optionset().list_options()
    
    @template("optionset", ExtOptionset, model=Optionset)
    def get_optionset(self):
        return self.optionset_manager.get_optionset(self.optionset)
    
    @update("subnetwork", ExtSubnetworkID)
    @entry(g_write)
    def set_id(self, value):
        q = "UPDATE subnetworks SET id=:value WHERE id=:id"
        self.db.put(q, id=self.oid, value=value)
        self.manager.rename_object(self, value)
        self.event_manager.add("rename",  subnetwork=self.oid, newstr=value, authuser=fun.session.authuser)
        
    @update("network", ExtNetworkName)
    @entry(g_write)
    def set_network(self, value):
        q = "UPDATE subnetworks SET network=:value WHERE id=:id"
        self.db.put(q, id=self.oid, value=value)
        self.event_manager.add("update",  subnetwork=self.oid, network=value, authuser=fun.session.authuser)
              
    @update("info", ExtString)
    @entry(g_write)
    def set_info(self, value):
        q = "UPDATE subnetworks SET info=:value WHERE id=:id"
        self.db.put(q, id=self.oid, value=value)
        self.event_manager.add("update",  subnetwork=self.oid, info=value, authuser=fun.session.authuser)


class IPV4Match(Match):
    @suffix("covers", ExtIpV4Address)
    def covers(self, fun, q, expr, val):
        q1 = "INET_ATON("
        q1 += q.var(val)
        q1 += ") >= INET_ATON(SUBSTRING_INDEX(id,'/',1)) AND INET_ATON("
        q1 += q.var(val)
        q1 += ") <= INET_ATON(SUBSTRING_INDEX(id,'/',1)) + ((1 << (32 - CONVERT(SUBSTRING_INDEX(id,'/',-1), UNSIGNED) ))-1)"
        q.where(q1)
 
        
class SubnetworkManager(AdHocManager):
    name = "subnetwork_manager"
    manages = Subnetwork

    model_lookup_error = ExtNoSuchSubnetworkError
    
    def init(self):
        self._model_cache = {}
        
    def base_query(self, dq):
        dq.table("subnetworks nw")
        dq.select("nw.id", "nw.network", "nw.info", "nw.mtime", "nw.changed_by", "nw.optionset")
        return dq

    def get_subnetwork(self, id):
        return self.model(id)

    def search_select(self, dq):
        dq.table("subnetworks nw")
        dq.select("nw.id")

    @search("subnetwork", StringMatch)
    def s_snet(self, dq):
        dq.table("subnetworks nw")
        return "nw.id"
    
    @search("subnetwork", IPV4Match, desc="Subnetworks covering a given IP address")
    def s_anet(self, dq):
        dq.table("subnetworks nw")
        return "nw.id"
    
    @search("network", StringMatch)
    def s_net(self, dq):
        dq.table("subnetworks nw")
        return "nw.network"
    
    @search("info", StringMatch)
    def s_info(self, dq):
        dq.table("subnetworks nw")
        return "nw.info"
    
    @entry(g_write)
    def create_subnetwork(self, fun, id, network, info):
        
        optionset = self.optionset_manager.create_optionset()
        
        q = """INSERT INTO subnetworks (id, network, info, changed_by, optionset) 
               VALUES (:id, :network, :info, :changed_by, :optionset)"""
        try:
            self.db.put(q, id=id, network=network, info=info, 
                        changed_by=fun.session.authuser, optionset=optionset)
        except IntegrityError:
            raise ExtSubnetworkAlreadyExistsError()
        self.event_manager.add("create", subnetwork=id, parent_object=network, info=info, 
                        authuser=fun.session.authuser, optionset=optionset)
    @entry(g_write)
    def destroy_subnetwork(self, fun, subnetwork):
        
        subnetwork.get_optionset().destroy()
        
        try:
            q = "DELETE FROM subnetworks WHERE id=:id LIMIT 1"
            self.db.put(q, id=subnetwork.oid)
        except IntegrityError:
            raise ExtSubnetworkInUseError()
        
        self.event_manager.add("destroy", subnetwork=subnetwork.oid)
        
        #print "Subnetwork destroyed, id=", id
        
    @entry(g_write)
    def set_option(self, fun, subnetwork, option, value):
        q = """INSERT INTO subnetwork_options (`for`, name, value, changed_by) VALUES (:id, :name, :value, :changed_by)
               ON DUPLICATE KEY UPDATE value=:value"""
        self.db.put(q, id=subnetwork.oid, name=option.oid, value=value, changed_by=fun.session.authuser)
        
    @entry(g_write)
    def unset_option(self, fun, subnetwork, option):
        q = """DELETE FROM subnetwork_options WHERE `for`=:id AND name=:name"""
        if not self.db.put(q, id=subnetwork.oid, name=option.oid):
            raise ExtOptionNotSetError()

    @entry(g_write)
    def update_options(self, fun, subnetwork, updates):
        omgr = fun.optionset_manager
        optionset = omgr.get_optionset(subnetwork.optionset)
        for (key, value) in updates.iteritems():
            optionset.set_option_by_name(key, value)