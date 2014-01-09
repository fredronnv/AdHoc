#!/usr/bin/env python2.6

from rpcc.model import *
from rpcc.exttype import *
from rpcc.function import SessionedFunction
from option_def import ExtOptionDef, ExtOptionNotSetError, ExtOptions



class ExtNoSuchNetworkError(ExtLookupError):
    desc = "No such network exists."


class ExtNetworkName(ExtString):
    name = "network-name"
    desc = "Name of a DHCP shared network"
    regexp = "^[A-Za-z0-9_][-A-Za-z0-9_]*$"


class ExtNetwork(ExtNetworkName):
    name = "network"
    desc = "A DHCP shared network"

    def lookup(self, fun, cval):
        return fun.network_manager.get_network(cval)

    def output(self, fun, obj):
        return obj.oid
    
    
class NetworkFunBase(SessionedFunction):  
    params = [("network", ExtNetwork, "Shared network name")]
   
     
class NetworkCreate(SessionedFunction):
    extname = "network_create"
    params = [("network_name", ExtNetworkName, "Network ID to create"),
              ("authoritative", ExtBoolean, "Whether the DHCP servers should claim to be authoritative for the network or not"),
              ("info", ExtString, "Network description")]
    desc = "Creates a shared network"
    returns = (ExtNull)

    def do(self):
        self.network_manager.create_network(self, self.network_name, self.authoritative, self.info)
        

class NetworkDestroy(NetworkFunBase):
    extname = "network_destroy"
    desc = "Destroys a shared network"
    returns = (ExtNull)

    def do(self):
        self.network_manager.destroy_network(self, self.network)


class NetworkOptionSet(NetworkFunBase):
    extname = "network_option_set"
    desc = "Set an option value on a network"
    params = [("option_name", ExtOptionDef, "Option name"),
              ("value", ExtString, "Option value")]
    returns = (ExtNull)
    
    def do(self):
        self.network_manager.set_option(self, self.network, self.option_name, self.value)


class NetworkOptionUnset(NetworkFunBase):
    extname = "network_option_unset"
    desc = "Unset an option value on a network"
    params = [("option_name", ExtOptionDef, "Option name")]
    returns = (ExtNull)
    
    def do(self):
        self.network_manager.unset_option(self, self.network, self.option_name)


class Network(Model):
    name = "network"
    exttype = ExtNetwork
    id_type = unicode

    def init(self, *args, **kwargs):
        a = list(args)
        self.oid = a.pop(0)
        self.authoritative = a.pop(0)
        self.info = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)

    @template("network", ExtNetwork)
    def get_network(self):
        return self

    @template("authoritative", ExtBoolean)
    def get_authoritative(self):
        return self.authoritative

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
        q = "SELECT name, value FROM network_options WHERE `for`=:id"
        ret = {}
        res = self.db.get_all(q, id=self.oid)
        for opt in res:
            ret[opt[0]] = opt[1]
        return ret
    
    @update("network", ExtNetworkName)
    def set_natwork(self, value):
        q = "UPDATE snetworks SET id=:value WHERE id=:id"
        self.db.put(q, id=self.oid, value=value)
        self.db.commit()
        self.manager.rename_network(self, value)

    @update("authoritative", ExtBoolean)
    def set_authoritative(self, newauthoritative):
        q = "UPDATE networks SET authoritative=:authoritative WHERE id=:id"
        self.db.put(q, id=self.oid, authoritative=newauthoritative)
        self.db.commit()
        
    @update("info", ExtString)
    def set_info(self, newinfo):
        q = "UPDATE networks SET info=:info WHERE id=:id"
        self.db.put(q, id=self.oid, info=newinfo)
        self.db.commit()


class NetworkManager(Manager):
    name = "network_manager"
    manages = Network

    model_lookup_error = ExtNoSuchNetworkError
    
    def init(self):
        self._model_cache = {}
        
    def base_query(self, dq):
        dq.table("networks nw")
        dq.select("nw.id", "nw.authoritative", "nw.info", "nw.mtime", "nw.changed_by")
        return dq

    def get_network(self, network_name):
        return self.model(network_name)

    def search_select(self, dq):
        dq.table("networks nw")
        dq.select("nw.id")

    @search("network", StringMatch)
    def s_net(self, dq):
        dq.table("networks nw")
        return "nw.id"
    
    def create_network(self, fun, network_name, authoritative, info):
        q = "INSERT INTO networks (id, authoritative, info, changed_by) VALUES (:id, :authoritative, :info, :changed_by)"
        self.db.put(q, id=network_name, authoritative=authoritative, info=info, changed_by=fun.session.authuser)
        print "Network created, network_name=", network_name
        self.db.commit()
        
    def destroy_network(self, fun, network):
        q = "DELETE FROM networks WHERE id=:id LIMIT 1"
        self.db.put(q, id=network.oid)
        print "Network destroyed, name=", network.oid
        self.db.commit()
        
    def rename_network(self, obj, newid):
        oid = obj.oid
        obj.oid = newid
        del(self._model_cache[oid])
        self._model_cache[newid] = obj
        
    def set_option(self, fun, network, option, value):
        q = """INSERT INTO network_options (`for`, name, value, changed_by) VALUES (:id, :name, :value, :changed_by)
               ON DUPLICATE KEY UPDATE value=:value"""
        self.db.put(q, id=network.oid, name=option.oid, value=value, changed_by=fun.session.authuser)
        
    def unset_option(self, fun, network, option):
        q = """DELETE FROM network_options WHERE `for`=:id AND name=:name"""
        if not self.db.put(q, id=network.oid, name=option.oid):
            raise ExtOptionNotSetError()
