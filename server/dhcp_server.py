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
    
    
class DHCPServerCreate(SessionedFunction):
    extname = "dhcp_server_create"
    params = [("dhcp_server_id", ExtDHCPServerID, "DHCPServer ID to create"),
              ("dns", ExtString, "The DNS name of the DHCP server"),
              ("info", ExtString, "DHCP Server description")]
    desc = "Creates a record for a DHCP server"
    returns = (ExtNull)

    def do(self):
        self.dhcp_server_manager.create_dhcp_server(self, self.dhcp_server_id, self.dns, self.info)


class DHCPServerDestroy(SessionedFunction):
    extname = "dhcp_server_destroy"
    params = [("dhcp_server", ExtDHCPServer, "DHCPServer to destroy")]
    desc = "Destroys a DHCP server record"
    returns = (ExtNull)

    def do(self):
        self.dhcp_server_manager.destroy_dhcp_server(self, self.dhcp_server)


class DHCPServer(Model):
    name = "dhcp_server"
    exttype = ExtDHCPServer
    id_type = unicode

    def init(self, *args, **kwargs):
        a = list(args)
        #print "DHCPServer.init", a
        self.oid = a.pop(0)
        self.dns = a.pop(0)
        self.info = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)

    @template("dhcp_server", ExtDHCPServer)
    def get_dhcp_server(self):
        return self

    @template("dns", ExtString)
    def get_dns(self):
        return self.dns

    @template("info", ExtString)
    def get_info(self):
        return self.info
    
    @template("mtime", ExtDateTime)
    def get_mtime(self):
        return self.mtime
    
    @template("changed_by", ExtString)
    def get_changed_by(self):
        return self.changed_by
    
    @update("dns", ExtString)
    def set_dns(self, dns):
        q = "UPDATE dhcp_servers SET name=:name WHERE id=:dhcp_id"
        self.db.put(q, dhcp_id=self.oid, name=dns)
        self.db.commit()
        
    @update("info", ExtString)
    def set_info(self, info):
        q = "UPDATE dhcp_servers SET info=:info WHERE id=:dhcp_id"
        self.db.put(q, dhcp_id=self.oid, info=info)
        self.db.commit()


class DHCPServerManager(Manager):
    name = "dhcp_server_manager"
    manages = DHCPServer

    model_lookup_error = ExtNoSuchDHCPServerError

    def init(self):
        self._model_cache = {}
        
    def base_query(self, dq):
        dq.select("ds.id", "ds.name", "ds.info", "ds.mtime", "ds.changed_by")
        dq.table("dhcp_servers ds")
        return dq

    def get_dhcp_server(self, dhcp_server_id):
        return self.model(dhcp_server_id)

    def search_select(self, dq):
        dq.table("dhcp_servers ds")
        dq.select("ds.id")

    @search("dhcp_server", StringMatch)
    def s_net(self, dq):
        dq.table("dhcp_servers ds")
        return "ds.id"
    
    def create_dhcp_server(self, fun, dhcp_server_id, dns, info):
        q = "INSERT INTO dhcp_servers (id, name, info, changed_by) VALUES (:id, :name, :info, :changed_by)"
        self.db.put(q, id=dhcp_server_id, name=dns, info=info, changed_by=fun.session.authuser)
        print "DHCPServer created, id=", dhcp_server_id
        self.db.commit()
        
    def destroy_dhcp_server(self, fun, dhcp_server):
        q = "DELETE FROM dhcp_servers WHERE id=:id LIMIT 1"
        self.db.put(q, id=dhcp_server.oid)
        print "DHCPServer destroyed, id=", dhcp_server.oid
        self.db.commit()
