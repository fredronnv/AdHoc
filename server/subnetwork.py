#!/usr/bin/env python2.6

from rpcc.model import *
from rpcc.exttype import *
from rpcc.function import SessionedFunction
from shared_network import ExtNetwork, ExtNetworkName


class ExtNoSuchSubnetworkError(ExtLookupError):
    desc = "No such subnetwork exists."


class ExtSubnetworkID(ExtString):
    name = "subnetwork-id"
    desc = "ID of a subnetwork"
    regexp = r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\/(\d|[1-2]\d|3[0-2]))$"


class ExtSubnetwork(ExtSubnetworkID):
    name = "subnetwork"
    desc = "A defined subnetwork"

    def lookup(self, fun, cval):
        return fun.subnetwork_manager.get_subnetwork(str(cval))

    def output(self, fun, obj):
        return obj.oid
    
    
class SubnetworkFunBase(SessionedFunction):  
    params = [("id", ExtSubnetworkID, "Subnetwork to create")]
    
    
class SubnetworkCreate(SubnetworkFunBase):
    extname = "subnetwork_create"
    params = [("network", ExtNetwork, "Shared network that the subnetwork belongs to"),
              ("info", ExtString, "Subnetwork description")]
    desc = "Creates a subnetwork"
    returns = (ExtNull)

    def do(self):
        self.subnetwork_manager.create_subnetwork(self, self.id, self.network.oid, self.info)
        

class SubnetworkDestroy(SubnetworkFunBase):
    extname = "subnetwork_destroy"
    desc = "Destroys a subnetwork"
    returns = (ExtNull)

    def do(self):
        self.subnetwork_manager.destroy_subnetwork(self, self.id)


class Subnetwork(Model):
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

    @template("id", ExtSubnetwork)
    def get_id(self):
        return self

    @template("network", ExtNetworkName)
    def get_network(self):
        return self.network

    @template("info", ExtString)
    def get_info(self):
        return self.info
    
    @template("mtime", ExtDateTime)
    def get_mtime(self):
        return self.mtime
    
    @template("changed_by", ExtString)
    def get_changed_by(self):
        return self.changed_by
    
    @update("id", ExtSubnetworkID)
    def set_id(self, value):
        q = "UPDATE subnetworks SET id=:value WHERE id=:id"
        self.db.put(q, id=self.oid, value=value)
        self.db.commit()
        self.manager.rename_subnetwork(self, value)
        
    @update("network", ExtNetworkName)
    def set_network(self, value):
        q = "UPDATE subnetworks SET network=:value WHERE id=:id"
        self.db.put(q, id=self.oid, value=value)
        self.db.commit()
        
    @update("info", ExtString)
    def set_info(self, value):
        q = "UPDATE subnetworks SET info=:value WHERE id=:id"
        self.db.put(q, id=self.oid, value=value)
        self.db.commit()


class SubnetworkManager(Manager):
    name = "subnetwork_manager"
    manages = Subnetwork

    model_lookup_error = ExtNoSuchSubnetworkError
    
    def init(self):
        self._model_cache = {}
        
    def base_query(self, dq):
        dq.table("subnetworks nw")
        dq.select("nw.id", "nw.network", "nw.info", "nw.mtime", "nw.changed_by")
        return dq

    def get_subnetwork(self, id):
        return self.model(id)

    def search_select(self, dq):
        dq.table("subnetworks nw")
        dq.select("nw.id")

    @search("subnetwork", StringMatch)
    def s_net(self, dq):
        dq.table("subnetworks nw")
        return "nw.id"
    
    def create_subnetwork(self, fun, id, network, info):
        q = "INSERT INTO subnetworks (id, network, info, changed_by) VALUES (:id, :network, :info, :changed_by)"
        print "PARAMS: id=",id,"network=",network
        self.db.put(q, id=id, network=network, info=info, changed_by=fun.session.authuser)
        print "Subnetwork created, id=", id
        self.db.commit()
        
    def destroy_subnetwork(self, fun, id):
        q = "DELETE FROM subnetworks WHERE id=:id LIMIT 1"
        self.db.put(q, id=id)
        print "Subnetwork destroyed, id=", id
        self.db.commit()

    def rename_subnetwork(self, obj, newid):
        oid = obj.oid
        obj.oid = newid
        del(self._model_cache[oid])
        self._model_cache[newid] = obj