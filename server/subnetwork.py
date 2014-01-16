#!/usr/bin/env python2.6

from rpcc.model import *
from rpcc.exttype import *
from rpcc.function import SessionedFunction
from shared_network import ExtNetwork, ExtNetworkName
from option_def import ExtOptionDef, ExtOptionNotSetError, ExtOptions
from rpcc.access import *
from rpcc.database import IntegrityError


class ExtNoSuchSubnetworkError(ExtLookupError):
    desc = "No such subnetwork exists."


class ExtSubnetworkAlreadyExistsError(ExtLookupError):
    desc = "The subnetwork ID is already in use"


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
        

class SubnetworkOptionSet(SubnetworkFunBase):
    extname = "subnetwork_option_set"
    desc = "Set an option value on a subnetwork"
    params = [("option_name", ExtOptionDef, "Option name"),
              ("value", ExtString, "Option value")]
    returns = (ExtNull)
    
    def do(self):
        self.subnetwork_manager.set_option(self, self.subnetwork, self.option_name, self.value)


class SubnetworkOptionUnset(SubnetworkFunBase):
    extname = "subnetwork_option_unset"
    desc = "Unset an option value on a subnetwork"
    params = [("option_name", ExtOptionDef, "Option name")]
    returns = (ExtNull)
    
    def do(self):
        self.subnetwork_manager.unset_option(self, self.subnetwork, self.option_name)


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
    
    @template("options", ExtOptions)
    def get_options(self):
        q = "SELECT name, value FROM subnetwork_options WHERE `for`=:id"
        ret = {}
        res = self.db.get_all(q, id=self.oid)
        for opt in res:
            ret[opt[0]] = opt[1]
        return ret
    
    @update("id", ExtSubnetworkID)
    @entry(AuthRequiredGuard)
    def set_id(self, value):
        q = "UPDATE subnetworks SET id=:value WHERE id=:id"
        self.db.put(q, id=self.oid, value=value)
        self.db.commit()
        self.manager.rename_subnetwork(self, value)
        
    @update("network", ExtNetworkName)
    @entry(AuthRequiredGuard)
    def set_network(self, value):
        q = "UPDATE subnetworks SET network=:value WHERE id=:id"
        self.db.put(q, id=self.oid, value=value)
        self.db.commit()
        
    @update("info", ExtString)
    @entry(AuthRequiredGuard)
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
    
    @entry(AuthRequiredGuard)
    def create_subnetwork(self, fun, id, network, info):
        q = "INSERT INTO subnetworks (id, network, info, changed_by) VALUES (:id, :network, :info, :changed_by)"
        try:
            self.db.put(q, id=id, network=network, info=info, changed_by=fun.session.authuser)
        except IntegrityError:
            raise ExtSubnetworkAlreadyExistsError()
        self.db.commit()
        
    @entry(AuthRequiredGuard)
    def destroy_subnetwork(self, fun, subnetwork):
        q = "DELETE FROM subnetworks WHERE id=:id LIMIT 1"
        self.db.put(q, id=subnetwork.oid)
        print "Subnetwork destroyed, id=", id
        self.db.commit()

    def rename_subnetwork(self, obj, newid):
        oid = obj.oid
        obj.oid = newid
        del(self._model_cache[oid])
        self._model_cache[newid] = obj
        
    @entry(AuthRequiredGuard)
    def set_option(self, fun, subnetwork, option, value):
        q = """INSERT INTO subnetwork_options (`for`, name, value, changed_by) VALUES (:id, :name, :value, :changed_by)
               ON DUPLICATE KEY UPDATE value=:value"""
        self.db.put(q, id=subnetwork.oid, name=option.oid, value=value, changed_by=fun.session.authuser)
        
    @entry(AuthRequiredGuard)
    def unset_option(self, fun, subnetwork, option):
        q = """DELETE FROM subnetwork_options WHERE `for`=:id AND name=:name"""
        if not self.db.put(q, id=subnetwork.oid, name=option.oid):
            raise ExtOptionNotSetError()
