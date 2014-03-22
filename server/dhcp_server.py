#!/usr/bin/env python2.6

from rpcc import *
from util import *


class ExtNoSuchDHCPServerError(ExtLookupError):
    desc = "No such dhcp_server exists."


class ExtDHCPServerAlreadyExistsError(ExtLookupError):
    desc = "The DHCP server ID is already in use"
    
    
class ExtDHCPServerInUseError(ExtValueError):
    desc = "The DHCP server is referred to by other objects. It cannot be destroyed"    

    
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
        #print "DHCP-server output", obj, obj.__dict__
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


class DHCPServer(AdHocModel):
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
    @entry(AdHocSuperuserGuard)
    def set_dns(self, dns):
        q = "UPDATE dhcp_servers SET name=:name WHERE id=:dhcp_id"
        self.db.put(q, dhcp_id=self.oid, name=dns)
        self.event_manager.add("update",  dhcp_server=self.oid, dns=dns, authuser=self.session.authuser)
        
    @update("info", ExtString)
    @entry(AdHocSuperuserGuard)
    def set_info(self, info):
        q = "UPDATE dhcp_servers SET info=:info WHERE id=:dhcp_id"
        self.db.put(q, dhcp_id=self.oid, info=info)
        self.event_manager.add("update",  dhcp_server=self.oid, info=info, authuser=self.session.authuser)
        
        
class DHCPServerManager(AdHocManager):
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
    
    @entry(AdHocSuperuserGuard)
    def create_dhcp_server(self, fun, dhcp_server_id, dns, info):
        q = "INSERT INTO dhcp_servers (id, name, info, changed_by) VALUES (:id, :name, :info, :changed_by)"
        try:
            self.db.put(q, id=dhcp_server_id, name=dns, info=info, changed_by=fun.session.authuser)
        except IntegrityError:
            raise ExtDHCPServerAlreadyExistsError()
        self.event_manager.add("create", dhcp_server=dhcp_server_id, dns=dns, info=info)
        #print "DHCPServer created, id=", dhcp_server_id
        
    @entry(AdHocSuperuserGuard)
    def destroy_dhcp_server(self, fun, dhcp_server):
        try:
            q = "DELETE FROM dhcp_servers WHERE id=:id LIMIT 1"
            self.db.put(q, id=dhcp_server.oid)
        except IntegrityError:
            raise ExtDHCPServerInUseError()
        self.event_manager.add("destroy", dhcp_server=dhcp_server.oid)
