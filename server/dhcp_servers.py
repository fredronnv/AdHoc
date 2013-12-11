#!/usr/bin/env python2.6

from rpcc.model import *
from rpcc.exttype import *
from rpcc.function import Function, SessionedFunction


class ExtNoSuchDHCPServerError(ExtLookupError):
    desc = "No such dhcp_server exists."


class ExtDHCPServerID(ExtString):
    name = "dhcp-server-id"
    desc = "ID of a DHCP server"
    regexp = "^[A-Z]$"


class ExtDHCPServer(ExtDHCPServerID):
    name = "dhcp-server"
    desc = "A DHCP server instance"

    def lookup(self, fun, cval):
        return fun.dhcp_server_manager.get_dhcp_server(cval)

    def output(self, fun, obj):
        return obj.oid
    
    
class DHCPServerFunBase(SessionedFunction):  
    params = [("dhsp_server_id", ExtDHCPServerID, "DHCPServer ID to create")]
    
    
class DHCPServerCreate(DHCPServerFunBase):
    extname = "dhcp_server_create"
    params = [("name", ExtString, "The DNS name of the DHCP server"),
              ("info", ExtString, "DHCP Server description")]
    desc = "Creates a record for a DHCP server"
    returns = (ExtNull)

    def do(self):
        self.dhcp_server_manager.create_dhcp_server(self, self.netid, self.authoritative, self.info)


class DHCPServerDestroy(DHCPServerFunBase):
    extname = "dhcp_server_destroy"
    desc = "Destroys a DHCP server record"
    returns = (ExtNull)

    def do(self):
        self.dhcp_server_manager.destroy_dhcp_server(self, self.netid)


class DHCPServer(Model):
    name = "dhcp_server"
    exttype = ExtDHCPServer
    id_type = unicode

    def init(self, dhcp_id, name, info):
        #print "DHCPServer.init", dhcp_id, name, info
        self.oid = dhcp_id
        self.name = name
        self.info = info

    @template("dhcp_server", ExtDHCPServer)
    def get_dhcp_server(self):
        return self

    @template("name", ExtBoolean)
    def get_name(self):
        return self.name

    @template("info", ExtString)
    def get_info(self):
        return self.info
    
    @update("name", ExtString)
    def set_name(self, newname):
        q = "UPDATE dhcp_servers SET name=:name WHERE id=:dhcp_id"
        self.db.put(q, dhcp_id=self.oid, name=newname)
        self.db.commit()
        
    @update("info", ExtString)
    def set_info(self, newinfo):
        q = "UPDATE dhcp_servers SET info=:info WHERE id=:netid"
        self.db.put(q, netid=self.oid, info=newinfo)
        self.db.commit()


class DHCPServerManager(Manager):
    name = "dhcp_server_manager"
    manages = DHCPServer

    model_lookup_error = ExtNoSuchDHCPServerError

    def init(self):
        self._model_cache = {}

    def base_query(self, dq):
        dq.select("ds.id", "ds.name", "ds.info")
        dq.table("dhcp_servers ds")
        return dq

    def get_dhcp_server(self, netid):
        return self.model(netid)

    def search_select(self, dq):
        dq.table("dhcp_servers ds")
        dq.select("ds.id")

    @search("dhcp_server", StringMatch)
    def s_net(self, dq):
        dq.table("dhcp_servers ds")
        return "ds.id"
    
    def create_dhcp_server(self, fun, netid, name, info):
        q = "INSERT INTO dhcp_servers (id, name, info, changed_by) VALUES (:id, :name, :info, :changed_by)"
        self.db.put(q, id=netid, name=name, info=info, changed_by=fun.session.authuser)
        print "DHCPServer created, id=", netid
        self.db.commit()
        
    def destroy_dhcp_server(self, fun, netid):
        q = "DELETE FROM dhcp_servers WHERE id=:id LIMIT 1"
        self.db.put(q, id=netid)
        print "DHCPServer destroyed, id=", netid
        self.db.commit()
