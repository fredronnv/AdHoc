#!/usr/bin/env python2.6

from rpcc.model import *
from rpcc.exttype import *
from rpcc.function import SessionedFunction


class ExtNoSuchNetworkError(ExtLookupError):
    desc = "No such network exists."


class ExtNetworkName(ExtString):
    name = "network-id"
    desc = "ID of a DHCP shared network"
    regexp = "^[A-Za-z0-9_][-A-Za-z0-9_]*$"


class ExtNetwork(ExtNetworkName):
    name = "network"
    desc = "A DHCP shared network"

    def lookup(self, fun, cval):
        return fun.network_manager.get_network(cval)

    def output(self, fun, obj):
        return obj.oid
    
    
class NetworkFunBase(SessionedFunction):  
    params = [("netid", ExtNetworkName, "Network ID to create")]
    
    
class NetworkCreate(NetworkFunBase):
    extname = "network_create"
    params = [("authoritative", ExtBoolean, "Whether the DHCP servers should claim to be authoritative for the network or not"),
              ("info", ExtString, "Network description")]
    desc = "Creates a shared network"
    returns = (ExtNull)

    def do(self):
        self.network_manager.create_network(self, self.netid, self.authoritative, self.info)
        

class NetworkDestroy(NetworkFunBase):
    extname = "network_destroy"
    desc = "Destroys a shared network"
    returns = (ExtNull)

    def do(self):
        self.network_manager.destroy_network(self, self.netid)


class Network(Model):
    name = "network"
    exttype = ExtNetwork
    id_type = unicode

    def init(self, netid, authoritative, info):
        #print "Network.init", netid, authoritative, info
        self.oid = netid
        self.authoritative = authoritative
        self.info = info

    @template("network", ExtNetwork)
    def get_network(self):
        return self

    @template("authoritative", ExtBoolean)
    def get_authoritative(self):
        return self.authoritative

    @template("info", ExtString)
    def get_info(self):
        return self.info
    
    @update("authoritative", ExtBoolean)
    def set_authoritative(self, newauthoritative):
        q = "UPDATE networks SET authoritative=:authoritative WHERE id=:netid"
        self.db.put(q, netid=self.oid, authoritative=newauthoritative)
        self.db.commit()
        
    @update("info", ExtString)
    def set_info(self, newinfo):
        q = "UPDATE networks SET info=:info WHERE id=:netid"
        self.db.put(q, netid=self.oid, info=newinfo)
        self.db.commit()


class NetworkManager(Manager):
    name = "network_manager"
    manages = Network

    model_lookup_error = ExtNoSuchNetworkError

    def init(self):
        self._model_cache = {}

    def base_query(self, dq):
        dq.select("nw.id", "nw.authoritative", "nw.info")
        dq.table("networks nw")
        return dq

    def get_network(self, netid):
        return self.model(netid)

    def search_select(self, dq):
        dq.table("networks nw")
        dq.select("nw.id")

    @search("network", StringMatch)
    def s_net(self, dq):
        dq.table("networks nw")
        return "nw.id"
    
    def create_network(self, fun, netid, authoritative, info):
        q = "INSERT INTO networks (id, authoritative, info, changed_by) VALUES (:id, :authoritative, :info, :changed_by)"
        self.db.put(q, id=netid, authoritative=authoritative, info=info, changed_by=fun.session.authuser)
        print "Network created, id=", netid
        self.db.commit()
        
    def destroy_network(self, fun, netid):
        q = "DELETE FROM networks WHERE id=:id LIMIT 1"
        self.db.put(q, id=netid)
        print "Network destroyed, id=", netid
        self.db.commit()
