#!/usr/bin/env python2.6
from model import *
from exttype import *

import socket
import struct


class DHCPManager(Manager):
    
    name = "dhcp_manager"
    models = None

    generated_allocation_group_classes = {}
    generated_allocation_host_classes = {}

    def openlog(self):
        try:
            self.LogFile = open(self.logfilename, "a", 0)
        except IOError:
            print "mkdhcp.pl: Log file " + self.logfilename + " cannot be opened"

    def closelog(self):
        if self.LogFile:
            self.LogFile.close()

    def init(self, serverID):
        self.serverID = serverID
        self.generated_allocation_group_classes = set()
              
    def resolve_option_host(self, option_value, host, option_key):
        return option_value or self.resolve_option_group(self.dhcp_group(host), option_key)
    
    def resolve_option_group(self, group, option_key):
        if not group: 
            return ""
        return self.option_group(group, option_key) or self.resolve_option_group(self.dhcp_parent_group(group), option_key)

    def option_host(self, host, option_key):
        q = "SELECT value FROM host_options WHERE for = %(host) AND name = %(option_key)"
        option_value = self.db.get(q, host=host, name=option_key)[0][0]
        return option_value

    def option_group(self, group, option_key):
        q = "SELECT value FROM group_options WHERE for = %(group) AND name = %(option_key)"
        option_value = self.db.get(q, group=group, name=option_key)[0][0]
        return option_value

    def dhcp_group(self, host):
        q = "SELECT `group` FROM hosts WHERE id=%(host) limit 1"
        dhcp_group = self.db.get(q, host=host)
        return dhcp_group
    
    def dhcp_parent_group(self, dhcp_group):
        q = "SELECT parent_group FROM groups WHERE groupname = %(dhcp_group) LIMIT 1"
        parent_group = self.db.get(q, dhcp_group=dhcp_group)[0][0]
        return parent_group
    
    def lookup(self, table, key, where):
        q = "SELECT %(key) FROM %(table) WHERE %(where) LIMIT 1"
        row = self.db.get(q, key=key, table=table, where=where)[0]
        return row

    def make_dhcpd_conf(self):

        self.dhcpd_conf = ""  # String where we collect the config output
   
        self.emit("# dhcpd.conf - automatically generated")
        self.emit("")
        
        q = "SELECT value FROM global_options WHERE name='domain_name_servers'"
        iparr = []
        for ip in self.db.get(q):
            if ip:
                iparr.append(ip)
        if iparr:
            s = "option domain-name-servers "
            s += ', '.join(iparr)
            self.emit(s)

        q = "SELECT value FROM global_options WHERE name='routers'"
        iparr = []
        for ip in self.db.get(q):
            if ip:
                iparr.append(ip)
        if iparr:
            s = "option routers "
            s += ', '.join(iparr)
            self.emit(s)

        q = "SELECT command, arg FROM basic_commands"
        
        for (cmd, arg) in self.db.get(q):
            if cmd:
                self.emit("%s %s;" % (cmd, arg))

#M =item option definitions
#M
        spacearr = []
        q = "SELECT value FROM optionspaces"
        
        for space in self.db.get(q):
            if space:
                spacearr.append(space)
                
        if spacearr:
            q = "SELECT name,code,qualifier,type FROM option_defs WHERE optionspace IS NULL AND code IS NOT NULL"
            for (name, code, qual, option_type) in self.db.get(q):
                """ NOTE The following prevents us from overloading the vendor-encapsulated-options option.
                     If this is to be used define vendor-encapsulated-options with code 43 in the database and use that option. 
                     If anyone defines another option with code 43, that one won't make it into the options definitions and any
                     use of that option will cause a syntax error, which could be cosidered feature compared 
                     to the bug that will otherwise be triggered.
                """
                if code == 43: 
                    continue
                if qual == 'array':
                    self.emit("option %s code %s = array of %s;" % (name, code, option_type))
                else:
                    self.emit("option %s code %s = %s;" % (name, code, option_type))

            for space in spacearr:
                self.emit("option space %s;" % space)
                
                q = "SELECT name, code, qualifier, type FROM option_defs WHERE optionspace=%(space)"
                for (name, code, qual, option_type) in self.db.get(q):
                    if qual == 'array':
                        self.emit("option %s.%s code %s = array of %s;" % (space, name, code, option_type))
                    else:
                        self.emit("option %s.%s code %s = %s;" % (space, name, code, option_type))
       
        self.emit_classes()
        self.emit_networks()
        self.emit_groups()

    def emit_classes(self):
        q = "SELECT classname, optionspace, vendor_class_id FROM classes"

        for (classname, optionspace, vendorclass) in self.db.get(q):
            if classname:
                self.emit_class(classname, optionspace, vendorclass)

    def emit_networks(self):
        q = "SELECT id, authoritative, info FROM networks"
        for (netid, authoritative, info) in self.db.get(q):
            if info:
                self.emit("# " + info)
            q = "SELECT id, network, info FROM subnetworks WHERE network=%(network)"
            if self.db.get(q, network=netid) or self.has_pools(netid):
                for poolname in self.get_network_pools(netid):
                    self.emit_allowed_classes(poolname, 0)
                self.emit("shared-network %s {" % netid)
                if authoritative:
                    self.emit("    authoritative;")
                self.emit_option_list(netid, '', 1, 'network')
                self.emit_subnetworks(netid, 0)
                self.emit_pools(netid, 0)
                self.emit("}")
            else:
                self.emit("#shared-network %s {} # Empty, no pools or subnetworks" % id)

    def emit_groups(self, parent=None, indent=0):
        if not parent:
            q = "SELECT groupname, parent, optionspace FROM groups WHERE parent_group IS NULL"
            rows = self.db.get(q)
        else:
            q = "SELECT groupname, parent, optionspace FROM groups WHERE parent_group=%(parent)"
            rows = self.db.get(q, parent=parent)
        for (groupname, parent, optionspace) in rows:
            if not groupname:
                continue
            self.emit_group_header(groupname, parent, optionspace, indent)
            self.emit_literal_options(groupname, 'group', indent + 1)
            self.emit_groups(groupname, indent + 1)
            self.emit_group_hosts(groupname, indent + 1)
            self.emit_group_trailer(indent, parent)
 
    def emit_literal_options(self, ownername, ownertype, indent):
        q = "SELECT owner, value FROM literal_options WHERE `owner`=%(ownername) AND owner_type=%(ownertype)"
        
        for (dummy_owner, value) in self.db.get(q, ownername=ownername, ownertype=ownertype):
            self.emit(value, 4 * indent)
    
    def emit_group_hosts(self, groupname, indent):
        q = "SELECT id, dns, mac, room, optionspace, entry_status FROM hosts WHERE `group`=%(groupname)"
    
        for (hostid, dns, mac, room, optionspace, entry_status) in self.db.get(q, groupname=groupname):
            self.emit_host(hostid, dns, mac, room, entry_status, optionspace, indent)
        
    def emit_host(self, hostid, dns, mac, room, entry_status, optionspace, indent):
        
        comment = ""
        
        if room:
            comment += "# Room %s" % room
            
        if entry_status == 'Active':
            q = "SELECT name, value FROM host_options WHERE `for` = %(hostid) "
            if not self.db.get(q, hostid=hostid):
                self.emit("host %s { hardware ethernet %s; fixed-address %s;} %s" % (hostid, mac, dns), 4 * indent)
            
            else:
                self.emit("host %s %s" % (hostid, comment), 4 * indent)
                self.emit("{", 4 * indent)
                self.emit("hardware ethernet %s" % mac, 4 * (indent + 1))
                self.emit("fixed-address %s;" % dns, 4 * (indent + 1))
                self.emit_option_space(optionspace, (4 * (indent + 1)))
                self.emit_option_list(hostid, optionspace, indent + 1, 'host')
                self.emit("}", 4 * indent)
            return
    
        if entry_status == "Inactive":
            self.emit("#host %s { hardware ethernet %s; fixed-address %s;} # %s,  %s" % (hostid, mac, dns, entry_status, comment), 4 * indent - 1)
            return
 
    def emit_pool(self, poolid, indent):
        
        q = "SELECT poolname, optionspace, info FROM pools WHERE poolname=%(poolid)"
    
        (poolname, optionspace, poolinfo) = self.db.get(q, poolid=poolid)[0]
        
        info = "# Pool: $id. $info" % (poolname, poolinfo)
        
        maxlease = self.db.get("SELECT value FROM pool_options WHERE `for`= %(poolid) AND name = 'max-lease-time'", 
                               poolid=poolid)

        if maxlease or self.has_allowed_group(poolid) or self.has_allowed_host(poolid):

            if info:
                self.emit("%s", 4 * (indent + 1))
            
            q = "SELECT start_ip FROM pool_ranges WHERE pool=%(poolid) AND (served_by=%(served_by) OR served_by IS NULL ) ORDER BY start_ip asc"
            if not self.db.get(q, poolid=poolid, served_by=self.serverID):
                if info:
                    self.emit("# Not generated as there are no defined IP ranges", 4 * (indent + 1))
                return
             
            self.emit("pool", 4 * (indent + 1))
            self.emit("{", 4 * (indent + 1))
            #if maxlease: self.emit("max-lease-time %s;" % maxlease[0] ,4 * (indent+2))
            self.emit_option_space(optionspace, 4 * (indent + 2))
            self.emit_option_list(poolid, optionspace, indent + 2, 'pool')
            self.emit_ranges(poolid, 4 * (indent + 2))
            self.emit_allow_classes(poolid, 4 * (indent + 2))
            self.emit("}", 4 * (indent + 1))

    def emit_allow_classes(self, poolid, indent):
        if self.has_allowed_group(poolid):
            q = "SELECT groupname FROM pool_group_map WHERE poolname=%(poolid) ORDER BY groupname ASC"
            for groupname in self.db.get(q, poolid=poolid):
                groupclass = "allocation-class-group-%s" % groupname
                self.emit("allow members of \"%s\";" % groupname, indent)
                self.generated_allocation_group_classes.add(groupclass)
    
    def emit_allowed_classes(self, poolid, indent):
        self.generated_allocation_group_classes
    
#TODO: write the code to dig out the mac adderesses
# Typically:

#class "allocation-class-1" {
#  match pick-first-value (option dhcp-client-identifier, hardware);
#}
#class "allocation-class-2" {
#  match pick-first-value (option dhcp-client-identifier, hardware);
#}
#subclass "allocation-class-1" 1:8:0:2b:4c:39:ad;
#subclass "allocation-class-2" 1:8:0:2b:a9:cc:e3;
#subclass "allocation-class-2" 1:0:1c:c0:06:7e:84;
        if self.has_allowed_group(poolid):
            q = "SELECT groupname FROM pool_group_map WHERE poolname=%(poolid) ORDER BY groupname ASC"
            for groupname in self.db.get(q, poolid=poolid):
                groupclass = "allocation-class-group-%s" % groupname
                if groupclass in self.generated_allocation_group_classes:
                    continue

                self.emit("class \"%s\" {" % groupclass, 4 * indent)
                self.emit("match pick-first-value (option dhcp-client-identifier, hardware);", 4 * (indent + 1))
                self.emit("}", 4 * (indent))

                q = "SELECT id, mac FROM hostlist WHERE `group`= %(groupname)"
                
                for (hostid, mac) in self.db.get(q, groupname=groupname):
                    self.emit("subclass \"%s\" 1:%s; # %s" % (groupclass, mac, hostid), 4 * (indent))
            self.generated_allocation_group_classes.add(groupclass)
    
    def emit_pools(self, network, indent):
        for poolname in self.get_network_pools(network):
            self.emit_pool(poolname, indent)

    def get_network_pools(self, netid):
        pools = set()
        q = "SELECT poolname FROM pools WHERE network=%(netid)"

        for row in self.db.get(q, netid=netid):
            pools.add(row[0])
        return pools

    def emit_ranges(self, poolid, indent):
        q = "SELECT start_ip,end_ip FROM pool_ranges WHERE pool=%(poolid) "
        q += " AND (served_by=%(server_id) OR served_by IS NULL ) ORDER BY start_ip ASC"

        for(start, end) in self.db.get(q, poolid=poolid, server_id=self.server_id):
            self.emit("range, %s %s" % (start, end), indent)

    def emit_subnetworks(self, network, indent):   
        q = "SELECT if, network, info FROM subnetworks WHERE `network`=%(network)"
    
        for (subnet_id, network, info) in self.db.get(q, network=network):
            network_id = "%-15s" % subnet_id
            if info:
                info = "# " + info
            else:
                info = ""
            (subnet_addr, mask_length) = subnet_id.split('/')
            subnet_mask = socket.inet_ntoa(struct.pack(">L", (1 << 32) - (1 << 32 >> mask_length)))
            
            if self.has_option_list(subnet_id, '', 1, 'subnetwork'):
                self.emit("subnet %s netmask %s     %s" % (subnet_addr, subnet_mask, info), 4 * (indent + 1))
                self.emit("{", 4 * (indent + 1))
                self.emit("option subnet-mask %s;" % subnet_mask, 4 * (indent + 2))
                self.emit_option_list(subnet_id, '', indent + 2, 'subnetwork')
                self.emit("}", 4 * (indent + 1))
            
            else:
                self.emit("subnet %s netmask %s { } %s" % (subnet_addr, subnet_mask, info), 4 * (indent + 1))

    def emit_class(self, classname, optionspace, vendor_class_id):

        self.emit("class \"%s\"" % classname, 0)
        self.emit("{", 0)
        
        if vendor_class_id:
            length = len(vendor_class_id)
            self.emit("match if substring (option vendor-class-identifier, 0, %d) = \"%s\";" % (length, vendor_class_id), 4)
        
        self.emit_option_space(optionspace, 4)
        self.emit_literal_options(classname, 'class', 1)
        self.emit_option_list(classname, optionspace, 1, 'class')
        self.emit("}", 0)

    def emit_option_space(self, optionspace, indent):
    
        if optionspace:
            q = "SELECT type FROM optionspaces WHERE `value` = %(optionspace)"
            
            row = self.db.get(q, optionspace=optionspace)
            if row:
                if row[0] == 'site':
                    self.emit("site-option-space \"%s\";" % optionspace, indent)

                if row[0] == 'vendor':
                    self.emit("vendor-option-space %s;" % optionspace, indent)

    def emit_group_header(self, groupname, parent, optionspace, indent):
    
        if parent:
            self.emit("group \"%s\"" % groupname, 4 * indent)
            self.emit("{", 4 * indent)
            self.emit_option_space(optionspace, 4 * (indent + 1))
            self.emit_option_list(groupname, optionspace, indent + 1, 'group')
    
    def emit_group_trailer(self, indent, parent):
        if parent:
            self.emit("}", 4 * indent)

    def has_pools(self, network):
        if not network:
            return False
    
        q = "SELECT poolname FROM pools WHERE `network` = %(network)"
        return bool(self.db.get(q, network=network))

    def has_allowed_group(self, poolname):
        if not poolname:
            return False
        return bool(self.db.get("SELECT groupname FROM pool_group_map WHERE `poolname` = %(poolname)", poolname=poolname))

    def has_option_list(self, optionlist, optionspace, indent, gtype, spaceprefix):

        if not optionlist:
            return False
    
        if optionspace:
            spaceprefix += optionspace + '.'
    
        table = gtype + "_options"
            
        return bool(self.db.get("SELECT name FROM %(table) WHERE `for` = %(optionlist)", table=table, optionlist=optionlist))
    
    def emit_option_list(self, optionlist, optionspace, indent, gtype, spaceprefix):

        if not optionlist:
            return False
    
        if optionspace:
            spaceprefix += optionspace + '.'
    
        table = gtype + "_options"
    
        rows = self.db.get("SELECT name, value FROM %(table) WHERE `for` = %(optionlist)", table=table, optionlist=optionlist)
    
        for (name, value) in rows:
        
            (space, dummy_type, qual) = self.db.get("SELECT optionspace,type,qualifier FROM option_defs WHERE name = %(name)", name=name)[0]
            
            opt = ""
            if qual != "parameter" and qual != "parameter-array":
                opt = "option "
            if space:
                space += "."
                
            if type == 'text':
                self.emit("%s%s%s \"%s\";" % (opt, space, name, value), 4 * indent)
            
            else:
                self.emit("%s%s%s %s;" % (opt, space, name, value), 4 * indent)
            
    def emit(self, msg, indent):
        msg = msg.rstrip() + "\n"
        self.dhcpd_conf += ' ' * indent + msg
