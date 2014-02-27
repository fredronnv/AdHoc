#!/usr/bin/env python2.6

from rpcc.function import Function

import socket
import struct
from rpcc.exttype import *
from rpcc.model import *
import rpcc.database
import optionset
import sys


class DhcpdConf(Function):
    extname = "dhcpd_config"
    params = [("server_id", ExtString),
              ]
    returns = ExtString

    def do(self):
        s = self.dhcp_manager.make_dhcpd_conf(self.server_id)
        return s


class DhcpXfer(Function):
    extname = "dhcp_xfer"
    returns = ExtNull
    
    def do(self):
        self.dhcp_manager.transfer_from_old_database(self.optionset_manager)
 
        
class DHCPManager(Manager):
    
    name = "dhcp_manager"
    models = None

    generated_allocation_group_classes = {}
    generated_allocation_host_classes = {}

    def init(self):
        self.serverID = None
        self.generated_allocation_group_classes = set()
        
    def m2cidr(self, ip, netmask):
        
        socket.inet_aton(ip)
        socket.inet_aton(netmask)
        
        ipaddr = ip.split('.')
        mask = netmask.split('.')
        
        net_start = [str(int(ipaddr[x]) & int(mask[x]))
                for x in range(0, 4)]
        
        binary_str = ''
        for octet in mask:
            binary_str += bin(int(octet))[2:].zfill(8)
        netsize = str(len(binary_str.rstrip('0')))
        
        return '.'.join(net_start) + '/' + netsize
             
    def transfer_from_old_database(self, optionset_manager):
        """ This method clears the DHCP database completely and transfers all of the data
            from the old database while observing the changes in syntac and semantics.
            
            This code is rough and unpolished as it is dead as soon as the new database goes into production
        """
            
        self.optionsetManager = optionset_manager
        user = self.server.config("ODB_USER")
        password = self.server.config("ODB_PASSWORD")
        db = self.server.config("ODB_DATABASE")
        host = self.server.config("ODB_HOST")
        port = self.server.config("ODB_PORT")
        
        self.odbase = rpcc.database.MySQLDatabase(self.server, user=user, password=password, database=db, host=host, port=port)
        
        self.odb = self.odbase.get_link()
        # Beacuse of the interdependencies between the tables,the ytansfer is divided into four strata.
        # All tables of one stratum must be completely transferred before beginning the transfer of any
        # tables in a subsequent stratum.
        
        # Stratum 1: optionspaces, networks, dhcp_servers, global_options, optionset, buildings and rooms
        # Stratum 2: subnetworks, option_base, groups, pools and classes
        # Stratum 3:  pool_ranges, 
        #            group_literal_options, pool_literal_options, class_literal_options,
        #            bool_option, str_option, int_option and hosts
        # Stratum 4: host_literal_options, optionset_boolval, optionset:strval and optionset_intval
        
        # Truncate all tables first, in reverse stratum order
        
        for table in ["host_literal_options", "optionset_boolval", "optionset_strval", "optionset_intval", "optionset_ipaddrval"]:
            self.db.put("TRUNCATE TABLE %s;" % table)
            
        for table in ["pool_ranges", 
                      "group_literal_options", "pool_literal_options", "class_literal_options", "hosts",
                      "bool_option", "str_option", "int_option", "ipaddr_option"]:
            self.db.put("TRUNCATE TABLE %s;" % table)
        
        self.db.put("SET foreign_key_checks=0")
        self.db.put("TRUNCATE TABLE groups")
        self.db.put("SET foreign_key_checks=1")
        
        for table in ["option_base", "pools", "classes", "subnetworks"]:
            self.db.put("TRUNCATE TABLE %s" % table)
            
        for table in ["optionspaces", "networks", "dhcp_servers", "global_options", "buildings", "rooms", "optionset"]:
            self.db.put("TRUNCATE TABLE %s" % table)
            
        
        #
        # Now build the tables in normal stratum order
        # buildings
        print 
        print "BUILDINGS"
        qf = "SELECT id,re,info,changed_by,mtime from buildings"
        qp = "INSERT INTO buildings (`id`,`re`,`info`,`changed_by` ,`mtime` ) VALUES(:id,:re,:info,:changedby,:mtime)"
        
        for (my_id, re, info, changed_by, mtime) in self.odb.get(qf):
            #print my_id, re, info, changed_by, mtime
            self.db.insert(my_id, qp, id=my_id, re=re, info=info, changedby=changed_by, mtime=mtime)
        
        #rooms
        print 
        print "ROOMS"
        rooms = set()  # Save set of rooms for hosts insertions later on
        qf = "SELECT id, info, printer, changed_by, mtime from rooms"
        qp = "INSERT INTO rooms (id, info, printers, changed_by, mtime) VALUES(:id, :info, :printers, :changedby, :mtime)"
        for (my_id, info, printers, changed_by, mtime) in self.odb.get(qf):
            #print my_id, info, printers, changed_by, mtime
            my_id = my_id.upper()
            rooms.add(my_id)
            self.db.insert("id", qp, id=my_id, info=info, printers=printers, changedby=changed_by, mtime=mtime)
    
        #global_options takes input also from the table basic
        print 
        print "GLOBAL OPTIONS"
        qf = "SELECT command, arg, mtime, id FROM basic "
        qp = "INSERT INTO global_options (name, value, changed_by, mtime, id) VALUES (:name, :value, :changedby, :mtime, :id)"
        for(name, value, mtime, my_id) in self.odb.get(qf):
            #print name, value, mtime, my_id
            if name == 'ddns-update-style' and value == 'ad-hoc':
                continue  # This mode is not supported in later versions of the dhcpd server
            self.db.insert("id", qp, name=name, value=value, changedby="DHCP2-ng", mtime=mtime, id=my_id)
        
        qf = "SELECT name, value, changed_by, mtime, id FROM optionlist WHERE gtype='global'"
        qp = "INSERT INTO global_options (name, value, changed_by, mtime, id) VALUES (:name, :value, :changedby, :mtime, :id)"
        for(name, value, changedby, mtime, my_id) in self.odb.get(qf):
            #print name, value, changedby, mtime, my_id
            self.db.insert("id", qp, name=name, value=value, changedby=changedby, mtime=mtime, id=my_id)
        
        #dhcp_servers
        print 
        print "DHCP SERVERS"
        qf = "SELECT id, name, info, changed_by, mtime from dhcp_servers"
        qp = "INSERT INTO dhcp_servers (id, name, info, changed_by, mtime) VALUES (:id, :name, :info, :changedby, :mtime)"
        for(my_id, name, info, changed_by, mtime) in self.odb.get(qf):
            #print my_id, name, info, changed_by, mtime
            self.db.insert("id", qp, id=my_id, name=name, info=info, changedby=changed_by, mtime=mtime)
        
        #networks
        print 
        print "NETWORKS"
        qf = "SELECT id, authoritative, info, changed_by, mtime FROM networks"
        qp = "INSERT INTO networks (id, authoritative, info, changed_by, mtime, optionset) VALUES (:id, :authoritative, :info, :changedby, :mtime, :optset)"
        for(my_id, authoritative, info, changed_by, mtime) in self.odb.get(qf):
            #print my_id, authoritative, info, changed_by, mtime
            optset = self.optionset_manager.create_optionset()
            self.db.insert("id", qp, id=my_id, authoritative=authoritative, info=info, changedby=changed_by, mtime=mtime, optset=optset)
        
        #optionspaces
        print 
        print "OPTION SPACES"
        qf = "SELECT id, type, value, info, changed_by, mtime FROM optionspaces"
        qp = "INSERT INTO optionspaces (id, type, value, info, changed_by, mtime) VALUES (:id, :type, :value, :info, :changedby, :mtime)"
        for(my_id, my_type, value, info, changed_by, mtime) in self.odb.get(qf):
            #print my_id, my_type, value, info, changed_by, mtime
            self.db.insert("id", qp, id=my_id, type=my_type, value=value, info=info, changedby=changed_by, mtime=mtime)
            
        # Table optionset is built when importing other objects.
        
        # Stratum 2:
        #subnetworks
        print 
        print "SUBNETWORKS"
        qf = "SELECT id, netmask, network, info, changed_by, mtime FROM subnetworks"
        qp = "INSERT INTO subnetworks (id, network, info, changed_by, mtime, optionset) VALUES(:id, :network, :info, :changedby, :mtime, :optset)"
        for(my_id, netmask, network, info, changed_by, mtime) in self.odb.get(qf):
            my_id = self.m2cidr(my_id, netmask)
            #print my_id, netmask, network, info, changed_by, mtime
            optset = self.optionset_manager.create_optionset()
            self.db.insert("id", qp, id=my_id, network=network,
                           info=info, changedby=changed_by, mtime=mtime, optset=optset)
            
        # option_base is built from the dhcp_option_defs table
        print "OPTION DEFINITIONS"
        qf = """SELECT id, name, code, qualifier, type, optionspace, info, changed_by, mtime 
                FROM dhcp_option_defs WHERE scope='dhcp'"""
        qp2 = """INSERT INTO option_base (name, code, qualifier, type, optionspace, info, changed_by, mtime)
                               VALUES(:name, :code, :qualifier, :type, :optionspace, :info, :changedby, :mtime)"""
                               
        for(my_id, name, code, qualifier, my_type, optionspace, info, changed_by, mtime) in self.odb.get(qf):
            #print my_id, name, code, qualifier, my_type, optionspace, info, changed_by, mtime
            
            id = self.db.insert("id", qp2, name=name, code=code, qualifier=qualifier, type=my_type, optionspace=optionspace,
                           info=info, changedby=changed_by, mtime=mtime)
            if my_type.startswith("integer") or my_type.startswith("unsigned"):
                qp3 = """INSERT INTO int_option (option_base, minval, maxval) 
                         VALUES (:option_base, :minval, :maxval)"""

                if my_type.endswith(' 8'):
                    u_maxval = 255
                    i_maxval = 127
                    i_minval = -127
                if my_type.endswith(' 16'):
                    u_maxval = 16383
                    i_maxval = 8191
                    i_minval = -8191
                if my_type.endswith(' 32'):
                    u_maxval = 4294967295
                    i_maxval = 2147483647
                    i_minval = -2147483647
                if my_type.startswith("unsigned"):
                    minval = 0
                    maxval = u_maxval
                else:
                    minval = i_minval
                    maxval = i_maxval
                self.db.put(qp3, option_base=id, minval=minval, maxval=maxval)
            
            if my_type == 'string' or my_type == 'text':
                qp3 = """INSERT INTO str_option (option_base) 
                         VALUES (:option_base)"""
                self.db.put(qp3, option_base=id)
            
            if my_type == 'boolean':
                qp3 = """INSERT INTO bool_option (option_base) 
                         VALUES (:option_base)"""
                self.db.put(qp3, option_base=id)
                
            if my_type == 'ip-address':
                qp3 = """INSERT INTO ipaddr_option (option_base) 
                         VALUES (:option_base)"""
                self.db.put(qp3, option_base=id)
        
        optionset.OptionsetManager.init_class(self.db)  # Reinitialize class with new options in the table
        #groups
        print 
        print "GROUPS"
        group_targets = set()  # Save set of groups for checking insertions later on
        qf = "SELECT groupname, parent_group, optionspace, info, changed_by, mtime FROM groups"
        qp = """INSERT INTO groups (groupname,  parent_group, optionspace, info, changed_by, mtime, optionset)
                       VALUES(:groupname, :parentgroup, :optionspace, :info, :changedby, :mtime, :optset)"""
        self.db.put("SET foreign_key_checks=0")
        for(groupname, parent_group, optionspace, info, changed_by, mtime) in self.odb.get(qf):
            #print groupname, parent_group, optionspace, info, changed_by, mtime
            if not parent_group:
                parent_group = 'plain'
            group_targets.add(groupname)
            optset = self.optionsetManager.create_optionset()
            self.db.insert("id", qp, groupname=groupname, parentgroup=parent_group, 
                           optionspace=optionspace, info=info, changedby=changed_by, mtime=mtime, optset=optset)
        self.db.put("SET foreign_key_checks=1")

        #pools
        print 
        print "POOLS"
        qf = "SELECT poolname, optionspace, network, info, changed_by, mtime FROM pools"
        qp = """INSERT INTO pools (poolname, optionspace, network, info, changed_by, mtime, optionset)
                       VALUES(:poolname, :optionspace, :network, :info, :changedby, :mtime, :optset)"""
        for(poolname, optionspace, network, info, changed_by, mtime) in self.odb.get(qf):
            optset = self.optionsetManager.create_optionset()
            #print poolname, optionspace, network, info, changed_by, mtime
            self.db.insert("id", qp, poolname=poolname, optionspace=optionspace, 
                           network=network, info=info, changedby=changed_by, mtime=mtime, optset=optset)
        #classes
        print 
        print "CLASSES"
        qf = "SELECT classname, optionspace, vendor_class_id, info, changed_by, mtime FROM classes"
        qp = """INSERT INTO classes (classname, optionspace, vendor_class_id, info, changed_by, mtime, optionset)
                       VALUES(:classname, :optionspace, :vendorclassid, :info, :changedby, :mtime, :optset)"""
        for(classname, optionspace, vendor_class_id, info, changed_by, mtime) in self.odb.get(qf):
            optset = self.optionsetManager.create_optionset()
            #print classname, optionspace, network, info, changed_by, mtime
            self.db.insert("id", qp, classname=classname, optionspace=optionspace, 
                           vendorclassid=vendor_class_id, info=info, changedby=changed_by, mtime=mtime, optset=optset)
        
        # Stratum 3: group_options, pool_options, network_options, subnetwork_options, pool_ranges, 
        #            pool_literal_options, class_literal_optrions, class_options and hosts
        #group_options
        #pool
        #network_options
        #subnetwork_options
        #class_options
        for tbl in [("group", "groups", "groupname"),
                    ("pool", "pools", "poolname"), 
                    ("network", "networks", "id"),
                    ("subnetwork", "subnetworks", "id"), 
                    ("class", "classes", "classname")]:
            qf = """SELECT o.`group`, o.name, o.value, o.changed_by, o.mtime, o.id FROM optionlist o, dhcp_option_defs d
                    WHERE o.name=d.name AND d.scope='dhcp' AND o.gtype='%s'""" % tbl[0]
            #qp = """INSERT INTO %s_options (`for`, name, value, changed_by, mtime, id) 
            #VALUES (:address, :name, :value, :changedby, :mtime, :id)""" % tbl[0]
            print
            print "OPTION TABLE FOR %s" % tbl[0]
            targets = {}
            rows = self.db.get_all("SELECT %s from %s" % (tbl[2], tbl[1]))
            for row in rows:
                if tbl[0] == "subnetwork":
                    (ip, size) = row[0].split("/")
                    targets[ip] = size
                else:
                    targets[row[0]] = True
            #print targets 
            for(address, name, value, changed_by, mtime, my_id) in self.odb.get(qf):
                if address in targets:
                    #print address, name, value, changed_by, mtime, my_id
                    
                    if tbl[0] == 'group':
                        target = self.group_manager.get_group(unicode(address))
                    if tbl[0] == 'pool':
                        target = self.pool_manager.get_pool(unicode(address))
                    if tbl[0] == 'network':
                        target = self.network_manager.get_network(unicode(address))
                    if tbl[0] == 'subnetwork':
                        address = address + '/' + targets[address]
                        target = self.subnetwork_manager.get_subnetwork(address)
                    if tbl[0] == 'class':
                        target = self.host_class_manager.get_host_class(unicode(address))
                        
                    if address in targets:
                        target.get_optionset().set_option_by_name(name, value)
        
        #pool_ranges
        qf = "SELECT pool, start_ip, end_ip, served_by, changed_by, mtime FROM pool_ranges"
        qp = """INSERT INTO pool_ranges (pool, start_ip, end_ip, served_by, changed_by, mtime)
                VALUES (:pool, :start_ip, :end_ip, :served_by, :changed_by, :mtime)"""
        print 
        print "POOL RANGES"
        for (pool, start_ip, end_ip, served_by, changed_by, mtime) in self.odb.get(qf):
            #print pool, start_ip, end_ip, served_by, changed_by, mtime
            self.db.insert(start_ip, qp, pool=pool, start_ip=start_ip, end_ip=end_ip, 
                           served_by=served_by, changed_by=changed_by, mtime=mtime)
            
        #pool_literal_options
        #class_literal_options
        #group_literal_options
        
        for tbl in [("group", "groups", "groupname"),
                    ("pool", "pools", "poolname"), 
                    ("class", "classes", "classname")]:
            qf = """SELECT `owner`, value, changed_by, mtime  FROM literal_options WHERE owner_type='%s'""" % tbl[0]
            qp = """INSERT INTO %s_literal_options (`for`, value, changed_by, mtime) 
                           VALUES (:address, :value, :changed_by, :mtime)""" % tbl[0]
            print
            print "LITERAL OPTIONS TABLE FOR %s" % tbl[0]
            targets = set()
            rows = self.db.get_all("SELECT %s from %s" % (tbl[2], tbl[1]))
            for row in rows:
                if tbl[0] == "subnetwork":
                    targets.add(row[0].split("/")[0])
                else:
                    targets.add(row[0])
            #print targets 
            for(address, value, changed_by, mtime) in self.odb.get(qf):
                if address in targets:
                    #print address, value, changed_by, mtime
                    self.db.put(qp, address=address, value=value, changed_by=changed_by, mtime=mtime)
        
        #hosts
        qf = "SELECT id, `group`, mac, room, optionspace, changed_by, mtime, info, entry_status FROM hostlist"
        qp = """INSERT INTO hosts (id, dns, `group`, mac, room, optionspace, changed_by, mtime, info, entry_status, optionset)
        VALUES (:id, :dns, :group, :mac, :room, :optionspace, :changed_by, :mtime, :info, :entry_status, :optset)"""
        print
        print "HOSTS"
        for(my_id, group, mac, room, optionspace, changed_by, mtime, info, entry_status) in self.odb.get(qf):
            dns = my_id
            my_id = dns.replace('.', '_')
            # Handle room value quirks such as zero length rooms or rooms being just blanks
            if not room or not bool(room.strip()):
                room = None
            else:
                room = room.upper()
            # Add yet unseen rooms into the rooms table    
            if room and room not in rooms:
                self.db.insert(id, "INSERT INTO rooms (id, info, changed_by) VALUES (:id, :info, :changed_by)",
                               id=room, info="Auto inserted on hosts migration", changed_by="dhcp2-ng")
                rooms.add(room)
            
            optset = self.optionsetManager.create_optionset()
            
            #print "'%s','%s','%s','%s','%s','%s','%s','%s','%s','%s'" % (my_id, dns, group, mac, room, optionspace, changed_by, mtime, info, entry_status)
            #print my_id, dns, group, mac, room, optionspace, changed_by, mtime, info, entry_status
            self.db.insert(id, qp, id=my_id, dns=dns, group=group, mac=mac, room=room, 
                               optionspace=optionspace, changed_by=changed_by, mtime=mtime, info=info, entry_status=entry_status, optset=optset)
        
        # Stratum 4: host_literal_options and host_options
        qf = """SELECT `owner`, value, changed_by, mtime  FROM literal_options WHERE owner_type='host'"""
        qp = """INSERT INTO host_literal_options (`for`, value, changed_by, mtime) 
                       VALUES (:address, :value, :changed_by, :mtime)"""
        print
        print "LITERAL OPTIONS TABLE FOR hosts"
        targets = set()
        rows = self.db.get_all("SELECT id from hosts")
        for row in rows:
                targets.add(row[0])
        #print targets 
        for(address, value, changed_by, mtime) in self.odb.get(qf):
            address = address.replace('.', '_')
            if address in targets:
                #print address, value, changed_by, mtime
                self.db.put(qp, address=address, value=value, changed_by=changed_by, mtime=mtime)
                
            if address in targets:
                #print address, name, value, changed_by, mtime, my_id
                self.db.put(qp, address=address, value=value, changed_by=changed_by, mtime=mtime)
                 
        # host_options
        qf = """SELECT o.`group`, o.name, o.value, o.changed_by, o.mtime, o.id FROM optionlist o, dhcp_option_defs d
                    WHERE o.name=d.name AND d.scope='dhcp' AND o.gtype='host'"""
        #print
        print "OPTION TABLE FOR host"
        #using targets from last operation
        #print targets 
        for(address, name, value, changed_by, mtime, my_id) in self.odb.get(qf):
            address = address.replace('.', '_')
            
            if address in targets:
                host = self.host_manager.get_host(unicode(address))
                host.get_optionset().set_option_by_name(name, value)
               
        # Pick up options formerly encoded in the data model tables:
        # groups had: filename, next_server, server_name, server_identifier
        # classes had filename, next_server, server_name
        # pools had max_lease_time
        # networks had next_server, server_name
        # subnetworks had subnet_mask
        
        # These option and parameter definitions has been entered to the old database and should now be transferred to the new using
        # the code above. However, the actual usage must be transferred into the xxx_options tables from the classes, groups etc tables.
        qf = """SELECT groupname, filename, next_server, server_name, server_identifier FROM groups
                WHERE filename IS NOT NULL OR next_server IS NOT NULL OR server_name IS NOT NULL OR server_identifier IS NOT NULL"""
        
        print
        print "GROUP PARAMETERS:"        
        for(name, filename, next_server, server_name, server_identifier) in self.odb.get(qf):
            #print name, filename, next_server, server_name, server_identifier
            target = self.group_manager.get_group(unicode(name))
            oset = target.get_optionset()
            if filename:
                oset.set_option_by_name("filename", filename)
            if next_server:
                oset.set_option_by_name("next-server", next_server)
            if server_name:
                oset.set_option_by_name("server-name", server_name)
            if server_identifier:
                oset.set_option_by_name("server-identifier", server_identifier)
                
        qf = """SELECT classname, filename, next_server, server_name, server_identifier FROM classes
                WHERE filename IS NOT NULL OR next_server IS NOT NULL OR server_name IS NOT NULL OR server_identifier IS NOT NULL"""
        print
        print "CLASS PARAMETERS"
        for(name, filename, next_server, server_name, server_identifier) in self.odb.get(qf):
            #print name, filename, next_server, server_name, server_identifier
            target = self.host_class_manager.get_host_class(unicode(name))
            oset = target.get_optionset()
            if filename:
                oset.set_option_by_name("filename", filename)
            if next_server:
                oset.set_option_by_name("next-server", next_server)
            if server_name:
                oset.set_option_by_name("server-name", server_name)
        
        qf = """SELECT id, subnet_mask, next_server, server_name FROM networks
                WHERE  server_name IS NOT NULL """
        print
        print "NETWORK PARAMETERS"
        for(name, subnet_mask, next_server, server_name) in self.odb.get(qf):
            #print name, subnet_mask, next_server, server_name
            target = self.network_manager.get_network(unicode(name))
            oset = target.get_optionset()
            if subnet_mask:
                oset.set_option_by_name("subnet-mask", subnet_mask)
            if next_server:
                oset.set_option_by_name("next-server", next_server)
            if server_name:
                oset.set_option_by_name("server-name", server_name)
        
        qf = """SELECT id, netmask, subnet_mask, next_server, server_name, server_identifier FROM subnetworks
                WHERE subnet_mask IS NOT NULL OR next_server IS NOT NULL OR server_name IS NOT NULL OR server_identifier IS NOT NULL"""
        print
        print "SUBNETWORK PARAMETERS"
        for(my_id, netmask, subnet_mask, next_server, server_name, server_identifier) in self.odb.get(qf):
            my_id = self.m2cidr(my_id, netmask)
            #print my_id, subnet_mask, next_server, server_name, server_identifier
            target = self.subnetwork_manager.get_subnetwork(my_id)
            oset = target.get_optionset()
            if subnet_mask:
                oset.set_option_by_name("subnet-mask", subnet_mask)
            if next_server:
                oset.set_option_by_name("next-server", next_server)
            if server_name:
                oset.set_option_by_name("server-name", server_name)
        
        qf = """SELECT poolname, max_lease_time FROM pools
                WHERE max_lease_time IS NOT NULL"""
        print
        print "POOL PARAMETERS"
        for(name, max_lease_time) in self.odb.get(qf):
            #print name, max_lease_time
            target = self.pool_manager.get_pool(unicode(name))
            oset = target.get_optionset()
            if max_lease_time:
                oset.set_option_by_name("max-lease-time", max_lease_time)
         
        return None
              
    def resolve_option_host(self, option_value, host, option_key):
        return option_value or self.resolve_option_group(self.dhcp_group(host), option_key)
    
    def resolve_option_group(self, group, option_key):
        if not group: 
            return ""
        return self.option_group(group, option_key) or self.resolve_option_group(self.dhcp_parent_group(group), option_key)

    def option_host(self, host, option_key):
        q = "SELECT value FROM host_options WHERE for = :host AND name = :option_key"
        option_value = self.get_value(q, host=host, name=option_key)
        return option_value

    def option_group(self, group, option_key):
        q = "SELECT value FROM group_options WHERE for = :group AND name = :option_key"
        option_value = self.db.get_value(q, group=group, name=option_key)
        return option_value

    def dhcp_group(self, host):
        q = "SELECT `group` FROM hosts WHERE id=:host limit 1"
        dhcp_group = self.db.get_all(q, host=host)
        return dhcp_group
    
    def dhcp_parent_group(self, dhcp_group):
        q = "SELECT parent_group FROM groups WHERE groupname = :dhcp_group LIMIT 1"
        parent_group = self.db.get_value(q, dhcp_group=dhcp_group)
        return parent_group
    
    def lookup(self, table, key, where):
        q = "SELECT :key FROM :table WHERE :where LIMIT 1"
        row = self.db.get_all(q, key=key, table=table, where=where)[0]
        return row

    def make_dhcpd_conf(self, serverID=None):
        timing_array = []
        b4start = datetime.datetime.now()
        
        timing_array.append(("Start", datetime.datetime.now(), datetime.datetime.now() - datetime.datetime.now()))
        
        self.serverID = serverID
        self.dhcpd_conf = []  # Array where we collect the config output strings
   
        self.emit("# dhcpd.conf - automatically generated", 0)
        self.emit("", 0)
        
        q = "SELECT value FROM global_options WHERE name='domain-name-servers'"
        iparr = []
        for (ip,) in self.db.get_all(q):
            if ip:
                iparr.append(ip)
        if iparr:
            s = "option domain-name-servers "
            s += ', '.join(iparr)
            s += ";"
            self.emit(s)
        timing_array.append(("Global-options 1", datetime.datetime.now(), datetime.datetime.now() - timing_array[-1][1]))
        q = "SELECT value FROM global_options WHERE name='routers'"
        iparr = []
        for (ip,) in self.db.get_all(q):
            if ip:
                iparr.append(ip)
        if iparr:
            s = "option routers "
            s += ', '.join(iparr)
            s += ";"
            self.emit(s)

        timing_array.append(("Global-options 2", datetime.datetime.now(), datetime.datetime.now() - timing_array[-1][1]))
#         q = "SELECT command, arg FROM basic_commands"
#         
#         for (cmd, arg) in self.db.get_all(q):
#             if cmd:
#                 self.emit("%s %s;" % (cmd, arg))
#         
#         timing_array.append(("Global-options 3", datetime.datetime.now(), datetime.datetime.now() - timing_array[-1][1]))
        spacearr = []
        q = "SELECT value FROM optionspaces"
        
        for (space,) in self.db.get_all(q):
            if space:
                spacearr.append(space)
        #print "SPACEARR=", spacearr    
        if spacearr:
            q = "SELECT name,code,qualifier,type FROM option_base WHERE optionspace IS NULL AND code IS NOT NULL"
            for (name, code, qual, option_type) in self.db.get_all(q):
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
                
                q = "SELECT name, code, qualifier, type FROM option_base WHERE optionspace=:space"
                for (name, code, qual, option_type) in self.db.get_all(q, space=space):
                    if qual == 'array':
                        self.emit("option %s.%s code %s = array of %s;" % (space, name, code, option_type))
                    else:
                        self.emit("option %s.%s code %s = %s;" % (space, name, code, option_type))
        
        timing_array.append(("Optionspaces", datetime.datetime.now(), datetime.datetime.now() - timing_array[-1][1]))
        self.emit_classes()
        
        timing_array.append(("Classes", datetime.datetime.now(), datetime.datetime.now() - timing_array[-1][1]))
        self.emit_networks()
        
        timing_array.append(("Networks", datetime.datetime.now(), datetime.datetime.now() - timing_array[-1][1]))
        b4groups = datetime.datetime.now()
        self.emit_groups(timing_array=timing_array)
        aftgroups = datetime.datetime.now()
        timing_array.append(("Groups", datetime.datetime.now(), datetime.datetime.now() - b4groups))
        endtime = datetime.datetime.now()
        timing_array.append(("Total", datetime.datetime.now(), datetime.datetime.now() - b4start))
        timing_array.sort(key=lambda tup: tup[2])
        for (what, when, time) in timing_array:
            pass
            #print what, when, time
        grouptime = aftgroups - b4groups
        tottime = endtime - b4start
        groupsshare = grouptime.total_seconds() / tottime.total_seconds()
        #print "Groups share=", groupsshare
        s = u"".join(self.dhcpd_conf)
        #print s
        return s

    def emit_classes(self):
        q = "SELECT classname, optionspace, vendor_class_id FROM classes"

        for (classname, optionspace, vendorclass) in self.db.get_all(q):
            if classname:
                self.emit_class(classname, optionspace, vendorclass)

    def emit_networks(self):
        q = "SELECT id, authoritative, info FROM networks ORDER BY (CONVERT(id USING latin1) COLLATE latin1_swedish_ci)"
        for (netid, authoritative, info) in self.db.get_all(q):
            if info:
                self.emit("# " + info)
            q = "SELECT id, network, info FROM subnetworks WHERE network=:network"
            if self.db.get_all(q, network=netid) or self.has_pools(netid):
                for poolname in self.get_network_pools(netid):
                    self.emit_allowed_classes(poolname, 0)
                self.emit("shared-network %s {" % netid)
                if authoritative:
                    self.emit("    authoritative;")
                network = self.network_manager.get_network(netid)
                self.emit_optlist(network, 1)
                #self.emit_option_list(netid, '', 1, 'network')
                self.emit_subnetworks(netid, 0)
                self.emit_pools(netid, 0)
                self.emit("}")
            else:
                self.emit("#shared-network %s {} # Empty, no pools or subnetworks" % id)

    def emit_groups(self, parent=None, indent=0, timing_array=None):
        
        if not parent:
            q = "SELECT groupname, parent_group, optionspace FROM groups WHERE groupname='plain' ORDER BY (CONVERT(groupname USING latin1) COLLATE latin1_swedish_ci)"
            rows = self.db.get_all(q)
        else:
            q = "SELECT groupname, parent_group, optionspace FROM groups WHERE parent_group=:parent AND groupname!='plain' ORDER BY (CONVERT(groupname USING latin1) COLLATE latin1_swedish_ci)"
            rows = self.db.get_all(q, parent=parent)
            
        for (groupname, parent, optionspace) in rows:
            if not groupname:
                continue
            #print "Emitting group ", groupname
            self.emit_group_header(groupname, parent, optionspace, indent)
            self.emit_literal_options(groupname, 'group', indent + 1)
            self.emit_groups(groupname, indent + 1, timing_array=timing_array)
            self.emit_group_hosts(groupname, indent + 1)
            self.emit_group_footer(groupname, indent, parent)
            timing_array.append(("Group %s" % groupname, datetime.datetime.now(), datetime.datetime.now() - timing_array[-1][1]))
 
    def emit_literal_options(self, ownername, ownertype, indent):
        q = "SELECT `for`, value FROM %s_literal_options WHERE `for`=:ownername" % (ownertype)
        
        for (dummy_owner, value) in self.db.get_all(q, ownername=ownername, ownertype=ownertype):
            self.emit(value, 4 * indent)
    
    def emit_group_hosts(self, groupname, indent):
        q = "SELECT id, dns, mac, room, optionspace, entry_status, info FROM hosts WHERE `group`= :groupname"
    
        for (hostid, dns, mac, room, optionspace, entry_status, info) in self.db.get(q, groupname=groupname):
            self.emit_host(hostid, dns, mac, room, entry_status, optionspace, info, indent)
        
    def emit_host(self, hostid, dns, mac, room, entry_status, optionspace, info, indent):
        
        comment = ""
        if info:
            comment = info
        
        if room:
            comment += "# Room %s" % room
            
        if entry_status == 'Active':
            host = self.host_manager.get_host(hostid)
            if self.has_optlist(host):
                self.emit("host %s %s" % (hostid, comment), 4 * indent)
                self.emit("{", 4 * indent)
                self.emit("hardware ethernet %s" % mac, 4 * (indent + 1))
                self.emit("fixed-address %s;" % dns, 4 * (indent + 1))
                self.emit_option_space(optionspace, (4 * (indent + 1)))
                self.emit_optlist(host, indent + 1)
                #self.emit_option_list(hostid, optionspace, indent + 1, 'host')
                self.emit("}", 4 * indent)
            else:
                self.emit("host %s { hardware ethernet %s; fixed-address %s;} %s" % (hostid, mac, dns, comment), 4 * indent)
            return
    
        if entry_status == "Inactive":
            self.emit("#host %s { hardware ethernet %s; fixed-address %s;} # %s,  %s" % (hostid, mac, dns, entry_status, comment), 4 * indent - 1)
            return
   
    def emit_pool(self, poolid, indent):
        
        q = "SELECT poolname, optionspace, info FROM pools WHERE poolname=:poolid"
    
        (poolname, optionspace, poolinfo) = self.db.get_all(q, poolid=poolid)[0]
        
        info = "# Pool: %s. %s" % (poolname, poolinfo)
        
        maxlease = None
        
        row = self.db.get_all("SELECT value FROM pool_options WHERE `for`= :poolid AND name = 'max-lease-time'", 
                               poolid=poolid)
        if row:
            maxlease = row[0]
            
        if maxlease or self.has_allowed_group(poolid):

            if info:
                self.emit("%s" % info, 4 * (indent + 1))
            
            q = "SELECT start_ip FROM pool_ranges WHERE pool=:poolid AND (served_by=:served_by OR served_by IS NULL ) ORDER BY start_ip asc"
            if not self.db.get_all(q, poolid=poolid, served_by=self.serverID):
                if info:
                    self.emit("# Not generated as there are no defined IP ranges", 4 * (indent + 1))
                return
             
            self.emit("pool", 4 * (indent + 1))
            self.emit("{", 4 * (indent + 1))
            #if maxlease: self.emit("max-lease-time %s;" % maxlease[0] ,4 * (indent+2))
            self.emit_option_space(optionspace, 4 * (indent + 2))
            pool = self.pool_manager.get_pool(poolname)
            self.emit_optlist(pool, indent + 2)
            #self.emit_option_list(poolid, optionspace, indent + 2, 'pool')
            self.emit_ranges(poolid, 4 * (indent + 2))
            self.emit_allow_classes(poolid, 4 * (indent + 2))
            self.emit("}", 4 * (indent + 1))

    def emit_allow_classes(self, poolid, indent):
        if self.has_allowed_group(poolid):
            q = "SELECT groupname FROM pool_group_map WHERE poolname=:poolid ORDER BY groupname ASC"
            for (groupname,) in self.db.get_all(q, poolid=poolid):
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
            q = "SELECT groupname FROM pool_group_map WHERE poolname=:poolid ORDER BY groupname ASC"
            for (groupname,) in self.db.get_all(q, poolid=poolid):
                groupclass = "allocation-class-group-%s" % groupname
                if groupclass in self.generated_allocation_group_classes:
                    continue

                self.emit("class \"%s\" {" % groupclass, 4 * indent)
                self.emit("match pick-first-value (option dhcp-client-identifier, hardware);", 4 * (indent + 1))
                self.emit("}", 4 * (indent))

                q = "SELECT id, mac FROM hostlist WHERE `group`= :groupname"
                
                for (hostid, mac) in self.db.get_all(q, groupname=groupname):
                    self.emit("subclass \"%s\" 1:%s; # %s" % (groupclass, mac, hostid), 4 * (indent))
            self.generated_allocation_group_classes.add(groupclass)
    
    def emit_pools(self, network, indent):
        for poolname in self.get_network_pools(network):
            self.emit_pool(poolname, indent)

    def get_network_pools(self, netid):
        pools = set()
        q = "SELECT poolname FROM pools WHERE network=:netid"

        for (pool,) in self.db.get_all(q, netid=netid):
            pools.add(pool)
        return pools

    def emit_ranges(self, poolid, indent):
        q = "SELECT start_ip,end_ip FROM pool_ranges WHERE pool=:poolid "
        q += " AND (served_by=:server_id OR served_by IS NULL ) ORDER BY start_ip ASC"

        for(start, end) in self.db.get_all(q, poolid=poolid, server_id=self.serverID):
            self.emit("range %s %s;" % (start, end), indent)

    def emit_subnetwork(self, subnet_id, network, info, indent): 
            #print "em:",network,subnet_id,info  
            if info:
                info = "# " + info
            else:
                info = ""
            (subnet_addr, mask_length) = subnet_id.split('/')
            subnet_mask = socket.inet_ntoa(struct.pack(">L", (1 << 32) - (1 << 32 >> int(mask_length))))
            
            subnetwork = self.subnetwork_manager.get_subnetwork(subnet_id)
            if self.has_optlist(subnetwork):
                self.emit("subnet %s netmask %s     %s" % (subnet_addr, subnet_mask, info), 4 * (indent + 1))
                self.emit("{", 4 * (indent + 1))
                #self.emit("option subnet-mask %s;" % subnet_mask, 4 * (indent + 2))
                self.emit_optlist(subnetwork, indent + 1)
                #self.emit_option_list(subnet_id, '', indent + 2, 'subnetwork')
                self.emit("}", 4 * (indent + 1))
            
            else:
                self.emit("subnet %s netmask %s { } %s" % (subnet_addr, subnet_mask, info), 4 * (indent + 1))
                
    def emit_subnetworks(self, network, indent):   
        q = "SELECT id, network, info FROM subnetworks WHERE `network`=:network ORDER BY (CONVERT(id USING latin1) COLLATE latin1_swedish_ci)"
    
        for (subnet_id, network, info) in self.db.get_all(q, network=network):
            self.emit_subnetwork(subnet_id, network, info, indent)

    def emit_class(self, classname, optionspace, vendor_class_id):

        self.emit("class \"%s\"" % classname, 0)
        self.emit("{", 0)
        
        if vendor_class_id:
            length = len(vendor_class_id)
            self.emit("match if substring (option vendor-class-identifier, 0, %d) = \"%s\";" % (length, vendor_class_id), 4)
        
        self.emit_option_space(optionspace, 4)
        self.emit_literal_options(classname, 'class', 1)
        host_class = self.host_class_manager.get_host_class(classname)
        self.emit_optlist(host_class, 1)
        #self.emit_option_list(classname, optionspace, 1, 'class')
        self.emit("}", 0)

    def emit_option_space(self, optionspace, indent):
    
        if optionspace:
            q = "SELECT type FROM optionspaces WHERE `value` = :optionspace"
            
            row = self.db.get_all(q, optionspace=optionspace)
            #print "Option space %s", optionspace, "row=", row
            if row:
                space_type = row[0][0]
                if space_type == 'site':
                    self.emit("site-option-space \"%s\";" % optionspace, indent)

                if space_type == 'vendor':
                    self.emit("vendor-option-space %s;" % optionspace, indent)

    def emit_group_header(self, groupname, parent, optionspace, indent):
    
        if parent and groupname != 'plain':
            self.emit("group \"%s\"" % groupname, 4 * indent)
            self.emit("{", 4 * indent)
            self.emit_option_space(optionspace, 4 * (indent + 1))
            group = self.group_manager.get_group(groupname)
            self.emit_optlist(group, indent + 1)
            #self.emit_option_list(groupname, optionspace, indent + 1, 'group')
    
    def emit_group_footer(self, groupname, indent, parent):
        if parent and groupname != 'plain':
            self.emit("}", 4 * indent)

    def has_pools(self, network):
        if not network:
            return False
    
        q = "SELECT poolname FROM pools WHERE `network` = :network"
        return bool(self.db.get_all(q, network=network))

    def has_allowed_group(self, poolname):
        if not poolname:
            return False
        return bool(self.db.get_all("SELECT groupname FROM pool_group_map WHERE `poolname` = :poolname", poolname=poolname))
            
    def emit_optlist(self, object, indent):
        option_names = object.list_options()
        if len(option_names) == 0:
            return False
        optionset = object.get_optionset()
        for name in option_names:
            value = optionset.get_option(name)
            (space, opt_type, qual) = self.db.get_all("SELECT optionspace, type, qualifier FROM option_base WHERE name = :name ", name=name)[0]
            opt = ""
            if qual != "parameter" and qual != "parameter-array":
                opt = "option "
            if space:
                space += "."
            else:
                space = ""
            if opt_type == 'text':
                self.emit("%s%s%s \"%s\";" % (opt, space, name, value), 4 * indent)
            else:
                self.emit("%s%s%s %s;" % (opt, space, name, value), 4 * indent)
            
    def has_optlist(self, object):
        option_names = object.list_options()
        if len(option_names) == 0:
            return False
        return True
            
    def emit(self, msg, indent=0):
        #msg = msg.rstrip() + "\n"
        self.dhcpd_conf.append("%s%s\n" % (' ' * indent, msg))
        #self.dhcpd_conf.append(msg.rstrip() + "\n")
        #self.dhcpd_conf.append("\n")
