#!/usr/bin/env python2.6

# $Id$

import struct
from rpcc import *
from room import ExtRoomName
import optionset
import tempfile
import subprocess

from adhoc_version import *
from util import *
from option_def import ExtNoSuchOptionDefError

g_reload = AnyGrants(AllowUserWithPriv("trigger_reload"), AdHocSuperuserGuard)


class ExtDhcpdRejectsConfigurationError(ExtValueError):
    desc = "The resulting configuration is rejected by dhcpd."


class ExtDhcpdCheckConfigurationError(ExtValueError):
    desc = "The AdHoc server is not configured to run dhcpd configuration checks."

    
class DhcpdConf(Function):
    extname = "dhcpd_config"
    params = [("server_id", ExtString),
              ]
    returns = ExtString
    log_call_event = False

    def do(self):
        s = self.dhcp_manager.make_dhcpd_conf(self.server_id)
        return s


class DhcpdReload(SessionedFunction):
    extname = "dhcpd_reload"
    returns = ExtNull
    desc = "Forcibly trigger a reload of the dhcpd configuration on all servers"
    creates_event = True
    
    def do(self):
        self.dhcp_manager.trigger_reload()


class DhcpXfer(SessionedFunction):
    extname = "dhcp_xfer"
    returns = ExtNull
    
    def do(self):
        self.dhcp_manager.transfer_from_old_database(self, self.optionset_manager)
  
        
class DHCPManager(AdHocManager):
    
    name = "dhcp_manager"
    models = None

    generated_allocation_group_classes = {}
    generated_allocation_host_classes = {}

    def init(self):
        self.serverID = None
        self.generated_allocation_group_classes = set()
        
    @classmethod
    def base_query(self, dq):
        return None  # Dummy method
        
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
    
    @entry(AdHocSuperuserGuard)          
    def transfer_from_old_database(self, fun, optionset_manager):
        """ This method clears the DHCP database completely and transfers all of the data
            from the old database while observing the changes in syntax and semantics.
            
            This code is rough and unpolished as it is dead as soon as the new database goes into production
        """
            
        self.optionsetManager = optionset_manager
        user = self.server.config("ODB_USER")
        password = self.server.config("ODB_PASSWORD")
        db = self.server.config("ODB_DATABASE")
        host = self.server.config("ODB_HOST")
        port = self.server.config("ODB_PORT")
        
        arrayoptions = []
        optiontypes = {}
        
        self.odbase = database.MySQLDatabase(self.server, user=user, password=password, database=db, host=host, port=port)
        
        self.odb = self.odbase.get_link()
        # Beacuse of the interdependencies between the tables,the ytansfer is divided into four strata.
        # All tables of one stratum must be completely transferred before beginning the transfer of any
        # tables in a subsequent stratum.
        
        # Stratum 1: optionspaces, networks, dhcp_servers, global_options, optionset, buildings and rooms
        # Stratum 2: subnetworks, option_base, groups, pools and classes
        # Stratum 3: pool_ranges, 
        #            group_literal_options, pool_literal_options, class_literal_options,
        #            bool_option, str_option, int_option and hosts
        # Stratum 4: host_literal_options, optionset_boolval, optionset:strval and optionset_intval
        # Truncate all tables first, in reverse stratum order
        
        # Stratum 4
        for table in ["host_literal_options", 
                      "optionset_boolval", 
                      "optionset_strval", 
                      "optionset_intval", 
                      "optionset_ipaddrval", 
                      "optionset_ipaddrarrayval", 
                      "optionset_intarrayval"]:
            self.db.put("TRUNCATE TABLE %s;" % table)
         
        # Stratum 3   
        for table in ["pool_ranges", 
                      "group_literal_options", 
                      "pool_literal_options", 
                      "class_literal_options", 
                      "hosts",
                      "bool_option", 
                      "str_option", 
                      "int_option", 
                      "ipaddr_option", 
                      "ipaddrarray_option", 
                      "intarray_option"]:
            self.db.put("TRUNCATE TABLE %s;" % table)
        
        # Stratum 2. The groups table references itself, so we have to turn off foreign key checks
        self.db.put("SET foreign_key_checks=0")
        self.db.put("TRUNCATE TABLE groups")
        self.db.put("TRUNCATE TABLE group_groups_flat")
        self.db.put("SET foreign_key_checks=1")
        
        for table in ["option_base", 
                      "pools", 
                      "classes", 
                      "subnetworks",
                      "rpcc_event_str",
                      "rpcc_event_int"]:
            self.db.put("TRUNCATE TABLE %s" % table)
        
        self.db.put("DELETE FROM accounts WHERE account != 'srvadhoc' AND account != 'int_0002'")
            
        # Stratum 1
        for table in ["optionspaces", 
                      "networks", 
                      "dhcp_servers", 
                      "global_options", 
                      "buildings", 
                      "rooms", 
                      "optionset",
                      "dnsmac",
                      "rpcc_event"]:
            self.db.put("TRUNCATE TABLE %s" % table)
            
        #
        # Now build the tables in normal stratum order
        # buildings
        # print 
        # print "BUILDINGS"
        qf = "SELECT id,re,info,changed_by,mtime from buildings"
        qp = "INSERT INTO buildings (`id`,`re`,`info`,`changed_by` ,`mtime` ) VALUES(:id,:re,:info,:changedby,:mtime)"
        
        for (my_id, re, info, changed_by, mtime) in self.odb.get(qf):
            # print my_id, re, info, changed_by, mtime
            self.db.insert(my_id, qp, id=my_id, re=re, info=info, changedby=changed_by, mtime=mtime)
        
        # rooms
        # print 
        # print "ROOMS"
        rooms = set()  # Save set of rooms for hosts insertions later on
        qf = "SELECT id, info, printer, changed_by, mtime from rooms"
        qp = "INSERT INTO rooms (id, info, printers, changed_by, mtime) VALUES(:id, :info, :printers, :changedby, :mtime)"
        for (my_id, info, printers, changed_by, mtime) in self.odb.get(qf):
            # print my_id, info, printers, changed_by, mtime
            my_id = my_id.upper()
            printers = printers.lower()
            rooms.add(my_id)
            self.db.insert("id", qp, id=my_id, info=info, printers=printers, changedby=changed_by, mtime=mtime)
    
        # global_options takes input also from the table basic
        # print 
        # print "BASIC  OPTIONS"
                       
        qf = "SELECT command, arg, mtime, id FROM basic "
        qp = "INSERT INTO global_options (name, value, basic, changed_by, mtime, id) VALUES (:name, :value, 1, :changedby, :mtime, :id)"
              
        for(name, value, mtime, my_id) in self.odb.get(qf):
            # print name, value, mtime, my_id
            if name == 'ddns-update-style' and value == 'ad-hoc':
                continue  # This mode is not supported in later versions of the dhcpd server
            self.db.insert("id", qp, name=name, value=value, changedby="DHCONF-ng", mtime=mtime, id=my_id)
            self.option_def_manager.define_option("", "DHCONF-ng", mtime, name, "text", None, "parameter", None)
        
        # Global options
        qf = "SELECT name, value, changed_by, mtime, id FROM optionlist WHERE gtype='global'"
        qp = "INSERT INTO global_options (name, value, basic, changed_by, mtime, id) VALUES (:name, :value, 0, :changedby, :mtime, :id)"
        for(name, value, changedby, mtime, my_id) in self.odb.get(qf):
            # print name, value, changedby, mtime, my_id
            if name == 'dhcp2_timestamp':
                continue  # Not needed
            
            # In case it has already been defined by the glopal options, remove it here
            try:
                odef = self.option_def_manager.get_option_def(name)
                self.option_def_manager.destroy_option_def(fun, odef)
            except ExtNoSuchOptionDefError:
                pass
            
            if not changedby:
                changedby = "DHCONF-ng"
            self.db.insert("id", qp, name=name, value=value, changedby=changedby, mtime=mtime, id=my_id)
            self.option_def_manager.define_option("", changedby, mtime, name, "text", None, "parameter", None)
            
        self.db.insert("id", "INSERT INTO global_options (name, value, basic, changed_by, id) VALUES (:name, :value, 1, :changedby, :id)",
                       name="log-facility", value="local5", changedby="DHCONF-ng", id=my_id + 1)
        
        self.option_def_manager.define_option("", "DHCONF-ng", mtime, "log-facility", "text", None, "parameter", None)
        
        # dhcp_servers
        # print 
        # print "DHCP SERVERS"
        qf = "SELECT id, name, info, changed_by, mtime from dhcp_servers"
        qp = "INSERT INTO dhcp_servers (id, name, info, changed_by, mtime) VALUES (:id, :name, :info, :changedby, :mtime)"
        for(my_id, name, info, changed_by, mtime) in self.odb.get(qf):
            # print my_id, name, info, changed_by, mtime
            # UGLY HACK, but required by jol@chalmers.se
            if name.startswith("dhcp"):
                name = "dhcp-ng" + name[4:]
            self.db.insert("id", qp, id=my_id, name=name, info=info, changedby=changed_by, mtime=mtime)
        
        # networks
        # print 
        # print "NETWORKS"
        qf = "SELECT id, authoritative, info, changed_by, mtime FROM networks"
        qp = "INSERT INTO networks (id, authoritative, info, changed_by, mtime, optionset) VALUES (:id, :authoritative, :info, :changedby, :mtime, :optset)"
        for(my_id, authoritative, info, changed_by, mtime) in self.odb.get(qf):
            # print my_id, authoritative, info, changed_by, mtime
            optset = self.optionsetManager.create_optionset(fun)
            self.db.insert("id", qp, id=my_id, authoritative=authoritative, info=info, changedby=changed_by, mtime=mtime, optset=optset)
        
        # optionspaces
        # print 
        # print "OPTION SPACES"
        qf = "SELECT id, type, value, info, changed_by, mtime FROM optionspaces"
        qp = "INSERT INTO optionspaces (id, type, value, info, changed_by, mtime) VALUES (:id, :type, :value, :info, :changedby, :mtime)"
        for(my_id, my_type, value, info, changed_by, mtime) in self.odb.get(qf):
            # print my_id, my_type, value, info, changed_by, mtime
            self.db.insert("id", qp, id=my_id, type=my_type, value=value, info=info, changedby=changed_by, mtime=mtime)
            
        # Table optionset is built when importing other objects.
        
        # Stratum 2:
        # subnetworks
        # print 
        # print "SUBNETWORKS"
        qf = "SELECT id, netmask, network, info, changed_by, mtime FROM subnetworks"
        qp = "INSERT INTO subnetworks (id, network, info, changed_by, mtime, optionset) VALUES(:id, :network, :info, :changedby, :mtime, :optset)"
        for(my_id, netmask, network, info, changed_by, mtime) in self.odb.get(qf):
            my_id = self.m2cidr(my_id, netmask)
            # print my_id, netmask, network, info, changed_by, mtime
            optset = self.optionsetManager.create_optionset(fun)
            self.db.insert("id", qp, id=my_id, network=network,
                           info=info, changedby=changed_by, mtime=mtime, optset=optset)
            
        # option_base is built from the dhcp_option_defs table
        # print "OPTION DEFINITIONS"
        qf = """SELECT id, name, code, qualifier, type, optionspace, info, changed_by, mtime 
                FROM dhcp_option_defs WHERE scope='dhcp' OR name='dhcp2_timestamp'"""
                                    
        for (my_id, name, code, qualifier, my_type, optionspace, info, changed_by, mtime) in self.odb.get(qf):
            # print my_id, name, code, qualifier, my_type, optionspace, info, changed_by, mtime
            # dhcp2_timestamp is a special option for internal use by AdHoc
            if name == 'dhcp2_timestamp':
                continue  # Not needed
            
            # In case it has already been defined by the glopal options, remove it here
            try:
                odef = self.option_def_manager.get_option_def(name)
                self.option_def_manager.destroy_option_def(fun, odef)
            except ExtNoSuchOptionDefError:
                pass
            if not changed_by:
                changed_by = "DHCONF-ng"
            self.option_def_manager.define_option(info, changed_by, mtime, name, my_type, code, qualifier, optionspace)
            
            # Save option info for later usage when adding options
            optiontypes[name] = my_type
            if qualifier and "array" in qualifier:
                arrayoptions.append(name)
        
        optionset.OptionsetManager.init_class(self.db)  # Reinitialize class with new options in the table
        # self.db.commit() # Warning! committing here may render your server unstartable. If that happens, manuallt trincate the option_def table, or maybe all tables.
        # groups
        # print 
        # print "GROUPS"
        group_targets = set()  # Save set of groups for checking insertions later on
        qf = "SELECT groupname, parent_group, optionspace, info, changed_by, mtime FROM groups"
        qp = """INSERT INTO groups (groupname,  parent_group, optionspace, info, changed_by, mtime, optionset)
                       VALUES(:groupname, :parentgroup, :optionspace, :info, :changedby, :mtime, :optset)"""
        self.db.put("SET foreign_key_checks=0")
        for(groupname, parent_group, optionspace, info, changed_by, mtime) in self.odb.get(qf):
            # print groupname, parent_group, optionspace, info, changed_by, mtime
            if not parent_group:
                parent_group = 'plain'
            group_targets.add(groupname)
            optset = self.optionsetManager.create_optionset(fun)
            self.db.insert("id", qp, groupname=groupname, parentgroup=parent_group, 
                           optionspace=optionspace, info=info, changedby=changed_by, mtime=mtime, optset=optset)
        
        # Build the group_groups_flat table
        qif = "INSERT INTO group_groups_flat (groupname, descendant) VALUES (:groupname, :descendant)"
        all_groups = self.db.get("SELECT groupname FROM groups")
        all_groups = [x[0] for x in all_groups]
        for g in all_groups:
            self.db.put(qif, groupname=g, descendant=g)  # The group itself
            g2 = g
            # Traverse the tree upward and fill in the group for every node traversed
            while True:
                parent = self.db.get("SELECT parent_group FROM groups WHERE groupname=:groupname", groupname=g2)[0][0]
                # print parent, g
                if not parent or parent == g2:
                    break
                self.db.put(qif, groupname=parent, descendant=g)
                g2 = parent
        self.db.put("SET foreign_key_checks=1")

        # pools
        # print 
        # print "POOLS"
        qf = "SELECT poolname, optionspace, network, info, changed_by, mtime FROM pools"
        qp = """INSERT INTO pools (poolname, optionspace, network, info, changed_by, mtime, optionset, open)
                       VALUES(:poolname, :optionspace, :network, :info, :changedby, :mtime, :optset, 1)"""
        for(poolname, optionspace, network, info, changed_by, mtime) in self.odb.get(qf):
            optset = self.optionsetManager.create_optionset(fun)
            # print poolname, optionspace, network, info, changed_by, mtime
            self.db.insert("id", qp, poolname=poolname, optionspace=optionspace, 
                           network=network, info=info, changedby=changed_by, mtime=mtime, optset=optset)
        # classes
        # print 
        # print "CLASSES"
        qf = "SELECT classname, optionspace, vendor_class_id, info, changed_by, mtime FROM classes"
        qp = """INSERT INTO classes (classname, optionspace, vendor_class_id, info, changed_by, mtime, optionset)
                       VALUES(:classname, :optionspace, :vendorclassid, :info, :changedby, :mtime, :optset)"""
        for(classname, optionspace, vendor_class_id, info, changed_by, mtime) in self.odb.get(qf):
            optset = self.optionsetManager.create_optionset(fun)
            # print classname, optionspace, network, info, changed_by, mtime
            self.db.insert("id", qp, classname=classname, optionspace=optionspace, 
                           vendorclassid=vendor_class_id, info=info, changedby=changed_by, mtime=mtime, optset=optset)
        
        # Stratum 3: group_options, pool_options, network_options, subnetwork_options, pool_ranges, 
        #            pool_literal_options, class_literal_optrions, class_options and hosts
        # group_options
        # pool
        # network_options
        # subnetwork_options
        # class_options
        for tbl in [("group", "groups", "groupname"),
                    ("pool", "pools", "poolname"), 
                    ("network", "networks", "id"),
                    ("subnetwork", "subnetworks", "id"), 
                    ("class", "classes", "classname")]:
            qf = """SELECT o.`group`, o.name, o.value, o.changed_by, o.mtime, o.id FROM optionlist o, dhcp_option_defs d
                    WHERE o.name=d.name AND d.scope='dhcp' AND o.gtype='%s'""" % tbl[0]
            # qp = """INSERT INTO %s_options (`for`, name, value, changed_by, mtime, id) 
            # VALUES (:address, :name, :value, :changedby, :mtime, :id)""" % tbl[0]
            # print
            # print "OPTION TABLE FOR %s" % tbl[0]
            targets = {}
            rows = self.db.get_all("SELECT %s from %s" % (tbl[2], tbl[1]))
            for row in rows:
                if tbl[0] == "subnetwork":
                    (ip, size) = row[0].split("/")
                    targets[ip] = size
                else:
                    targets[row[0]] = True
            # print targets 
            for(address, name, value, changed_by, mtime, my_id) in self.odb.get(qf):
                if address in targets:
                    # print address, name, value, changed_by, mtime, my_id
                    
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
                        if name in arrayoptions:
                            value = [y.strip() for y in value.split(",")]
                            if "integer" in optiontypes[name]:
                                value = [ int(x) for x in value]  # Convert elements to integers
                        target.get_optionset().set_option_by_name(name, value)
        
        # pool_ranges
        qf = "SELECT pool, start_ip, end_ip, served_by, changed_by, mtime FROM pool_ranges"
        qp = """INSERT INTO pool_ranges (pool, start_ip, end_ip, served_by, changed_by, mtime)
                VALUES (:pool, :start_ip, :end_ip, :served_by, :changed_by, :mtime)"""
        # print 
        # print "POOL RANGES"
        for (pool, start_ip, end_ip, served_by, changed_by, mtime) in self.odb.get(qf):
            # print pool, start_ip, end_ip, served_by, changed_by, mtime
            self.db.insert(start_ip, qp, pool=pool, start_ip=start_ip, end_ip=end_ip, 
                           served_by=served_by, changed_by=changed_by, mtime=mtime)
            
        # pool_literal_options
        # class_literal_options
        # group_literal_options
        
        for tbl in [("group", "groups", "groupname"),
                    ("pool", "pools", "poolname"), 
                    ("class", "classes", "classname")]:
            qf = """SELECT `owner`, value, changed_by, mtime  FROM literal_options WHERE owner_type='%s'""" % tbl[0]
            qp = """INSERT INTO %s_literal_options (`for`, value, changed_by, mtime) 
                           VALUES (:address, :value, :changed_by, :mtime)""" % tbl[0]
            # print
            # print "LITERAL OPTIONS TABLE FOR %s" % tbl[0]
            targets = set()
            rows = self.db.get_all("SELECT %s from %s" % (tbl[2], tbl[1]))
            for row in rows:
                if tbl[0] == "subnetwork":
                    targets.add(row[0].split("/")[0])
                else:
                    targets.add(row[0])
            # print targets 
            for(address, value, changed_by, mtime) in self.odb.get(qf):
                if address in targets:
                    # print address, value, changed_by, mtime
                    self.db.put(qp, address=address, value=value, changed_by=changed_by, mtime=mtime)
        
        # hosts
        qf = "SELECT id, `group`, mac, room, optionspace, changed_by, mtime, info, entry_status, owner_CID FROM hostlist"
        qp = """INSERT INTO hosts (id, dns, `group`, mac, room, optionspace, changed_by, mtime, info, entry_status, optionset, cid)
        VALUES (:id, :dns, :group, :mac, :room, :optionspace, :changed_by, :mtime, :info, :entry_status, :optset, :cid)"""
        # print
        # print "HOSTS"
        # datecounts = {}
        cids = set()
        for(my_id, group, mac, room, optionspace, changed_by, mtime, info, entry_status, cid) in self.odb.get(qf):
            dns = my_id.lower()
            
            mdate = mtime.strftime("%Y%m%d")
            
            my_id = self.host_manager.generate_host_name(mac, today=mdate)
                
            # Handle room value quirks such as zero length rooms or rooms being just blanks
            if not room or not bool(room.strip()):
                room = None
            else:
                room = room.upper()
                
            if re.match(ExtRoomName.regexp, room):
                   
                # Add yet unseen rooms into the rooms table    
                if room and room not in rooms:
                    self.db.insert(id, "INSERT INTO rooms (id, info, changed_by) VALUES (:id, :info, :changed_by)",
                                   id=room, info="Auto inserted on hosts migration", changed_by="AdHoc_server")
                    rooms.add(room)
                else:
                    self.server.logger.warning("WARNING! Room code %s not accepted")
                
            # Handle cid quirks
            if not cid or cid == 'root' or cid == 'nobody':
                cid = None
            else:
                cid = cid.lower()
                
            if cid and cid not in cids:
                self.db.insert(id, "INSERT INTO accounts (account, status) VALUES (:cid, NULL)",
                               cid=cid)
                cids.add(cid)
            
            optset = self.optionsetManager.create_optionset(fun)
            
            # print "'%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s'" % (my_id, dns, group, mac, room, optionspace, changed_by, mtime, info, entry_status, cid)
            # print my_id, dns, group, mac, room, optionspace, changed_by, mtime, info, entry_status, cid
            self.db.insert(id, qp, 
                           id=my_id, 
                           dns=dns, 
                           group=group,
                           mac=mac, 
                           room=room, 
                           optionspace=optionspace, 
                           changed_by=changed_by, 
                           mtime=mtime, 
                           info=info, 
                           entry_status=entry_status, 
                           optset=optset, 
                           cid=cid)
            self.db.insert(id, "INSERT INTO dnsmac (dns, mac) VALUES (:dns, :mac)", dns=dns, mac=mac)
        self.group_manager.gather_stats()
        # Stratum 4: host_literal_options and host_options
        qf = """SELECT `owner`, value, changed_by, mtime  FROM literal_options WHERE owner_type='host'"""
        qp = """INSERT INTO host_literal_options (`for`, value, changed_by, mtime) 
                       VALUES (:address, :value, :changed_by, :mtime)"""
        # print
        # print "LITERAL OPTIONS TABLE FOR hosts"
        targets = set()
        rows = self.db.get_all("SELECT id from hosts")
        for row in rows:
                targets.add(row[0])
        # print targets 
        for(address, value, changed_by, mtime) in self.odb.get(qf):
            address = address.replace('.', '_')
            if address in targets:
                # print address, value, changed_by, mtime
                self.db.put(qp, address=address, value=value, changed_by=changed_by, mtime=mtime)
                
            if address in targets:
                # print address, name, value, changed_by, mtime, my_id
                self.db.put(qp, address=address, value=value, changed_by=changed_by, mtime=mtime)
                 
        # host_options
        qf = """SELECT o.`group`, o.name, o.value, o.changed_by, o.mtime, o.id FROM optionlist o, dhcp_option_defs d
                    WHERE o.name=d.name AND d.scope='dhcp' AND o.gtype='host'"""
        # print
        # print "OPTION TABLE FOR host"
        # using targets from last operation
        # print targets 
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
        
        # print
        # print "GROUP PARAMETERS:"        
        for(name, filename, next_server, server_name, server_identifier) in self.odb.get(qf):
            # print name, filename, next_server, server_name, server_identifier
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
        # print
        # print "CLASS PARAMETERS"
        for(name, filename, next_server, server_name, server_identifier) in self.odb.get(qf):
            # print name, filename, next_server, server_name, server_identifier
            target = self.host_class_manager.get_host_class(unicode(name))
            oset = target.get_optionset()
            if filename:
                oset.set_option_by_name("filename", filename)
            if next_server:
                oset.set_option_by_name("next-server", next_server)
            if server_name:
                oset.set_option_by_name("server-name", server_name)
        
        qf = """SELECT id, subnet_mask, next_server, server_name FROM networks
                WHERE  server_name IS NOT NULL OR subnet_mask IS NOT NULL OR next_server IS NOT NULL"""
        # print
        # print "NETWORK PARAMETERS"
        for(name, subnet_mask, next_server, server_name) in self.odb.get(qf):
            # print name, subnet_mask, next_server, server_name
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
        # print
        # print "SUBNETWORK PARAMETERS"
        for(my_id, netmask, subnet_mask, next_server, server_name, server_identifier) in self.odb.get(qf):
            my_id = self.m2cidr(my_id, netmask)
            # print my_id, subnet_mask, next_server, server_name, server_identifier
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
        # print
        # print "POOL PARAMETERS"
        for(name, max_lease_time) in self.odb.get(qf):
            # print name, max_lease_time
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
        # b4start = datetime.datetime.now()
        
        # timing_array.append(("Start", datetime.datetime.now(), datetime.datetime.now() - datetime.datetime.now()))
        
        self.serverID = serverID
        self.dhcpd_conf = []  # Array where we collect the config output strings
        self.generated_allocation_group_classes = set()
        
        eventid = self.event_manager.get_max_id()
   
        self.emit("# dhcpd.conf - Rev: %d Automatically generated for DHCP server %s by AdHoc server %s (svn %s). Do not edit!" % (eventid, serverID, adhoc_release, adhoc_svn_version), 0)
       
        #self.emit("", 0)
        #self.emit("log-facility local4;")
        #self.emit("", 0)
            
        # timing_array.append(("Global-options 1A", datetime.datetime.now(), datetime.datetime.now() - timing_array[-1][1]))
        q = "SELECT name, value FROM global_options WHERE basic = 1"
        for (name, value) in self.db.get_all(q):
            s = name + " " + value + ";"
            self.emit(s)

        spacearr = []
        q = "SELECT value FROM optionspaces"
        
        for (space,) in self.db.get_all(q):
            if space:
                spacearr.append(space)
        # print "SPACEARR=", spacearr    
        
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
                    
        if spacearr:
            for space in spacearr:
                self.emit("option space %s;" % space)
                
                q = "SELECT name, code, qualifier, type FROM option_base WHERE optionspace=:space"
                for (name, code, qual, option_type) in self.db.get_all(q, space=space):
                    if qual == 'array':
                        self.emit("option %s.%s code %s = array of %s;" % (space, name, code, option_type))
                    else:
                        self.emit("option %s.%s code %s = %s;" % (space, name, code, option_type))
                        
        # timing_array.append(("Global-options 1A", datetime.datetime.now(), datetime.datetime.now() - timing_array[-1][1]))
        q1 = "SELECT DISTINCT name FROM global_options WHERE basic = 0"
        for (name,) in self.db.get_all(q1):
            #print "GLOBAL OPTION NAMED:", name
            value_list = []
            q2 = "SELECT value FROM global_options WHERE name = :name"
            for (value,) in self.db.get_all(q2, name=name):
                #print "GLOBAL OPTION NAME, VALUE=", name, value
                if value:
                    value_list.append(value)
            if value_list:
                s = "option %s " % name
                s += ', '.join(value_list)
                s += ";"
                self.emit(s)

        
        # timing_array.append(("Optionspaces", datetime.datetime.now(), datetime.datetime.now() - timing_array[-1][1]))
        self.emit_classes()
        
        # timing_array.append(("Classes", datetime.datetime.now(), datetime.datetime.now() - timing_array[-1][1]))
        self.emit_networks()
        
        # timing_array.append(("Networks", datetime.datetime.now(), datetime.datetime.now() - timing_array[-1][1]))
        # b4groups = datetime.datetime.now()
        self.emit_groups(timing_array=timing_array)
        # aftgroups = datetime.datetime.now()
        # timing_array.append(("Groups", datetime.datetime.now(), datetime.datetime.now() - b4groups))
        # endtime = datetime.datetime.now()
        # timing_array.append(("Total", datetime.datetime.now(), datetime.datetime.now() - b4start))
        # timing_array.sort(key=lambda tup: tup[2])
        # for (what, when, time) in timing_array:
        #      pass
        #      print what, when, time
        # grouptime = aftgroups - b4groups
        # tottime = endtime - b4start
        # groupsshare = grouptime.total_seconds() / tottime.total_seconds()
        # print "Groups share=", groupsshare
        s = u"".join(self.dhcpd_conf)
        # print s
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
            
            subnetworks = self.db.get_all(q, network=netid)
            pools = self.get_network_pools(netid)
            classes = 0
            for poolname in self.get_network_pools(netid):
                    classes += self.emit_allowed_classes(poolname, 0) 
                    
            if len(subnetworks) + classes > 0:
                self.emit("shared-network %s {" % netid)
                if authoritative:
                    self.emit("    authoritative;")
                network = self.network_manager.get_network(netid)
                self.emit_optlist(network, 1)
                # self.emit_option_list(netid, '', 1, 'network')
                self.emit_subnetworks(netid, 0)
                self.emit_pools(netid, 0)
                self.emit("}")
            else:
                self.emit("#shared-network %s {} # Empty, no pools or subnetworks" % netid)

    def emit_groups(self, parent=None, indent=0, timing_array=None):
        
        if not parent:
            q = "SELECT groupname, parent_group, optionspace FROM groups WHERE groupname='plain' ORDER BY (CONVERT(groupname USING latin1) COLLATE latin1_swedish_ci)"
            rows = self.db.get_all(q)
        else:
            q = "SELECT groupname, parent_group, optionspace FROM groups WHERE parent_group=:parent AND groupname!='plain' AND hostcount > 0 ORDER BY (CONVERT(groupname USING latin1) COLLATE latin1_swedish_ci)"
            rows = self.db.get_all(q, parent=parent)
            
        for (groupname, parent, optionspace) in rows:
            if not groupname:
                continue
            # print "Emitting group ", groupname
            self.emit_group_header(groupname, parent, optionspace, indent)
            self.emit_literal_options(groupname, 'group', indent + 1)
            self.emit_groups(groupname, indent + 1, timing_array=timing_array)
            self.emit_group_hosts(groupname, indent + 1)
            self.emit_group_footer(groupname, indent, parent)
            # timing_array.append(("Group %s" % groupname, datetime.datetime.now(), datetime.datetime.now() - timing_array[-1][1]))
 
    def emit_literal_options(self, ownername, ownertype, indent):
        q = "SELECT `for`, value FROM %s_literal_options WHERE `for`=:ownername" % (ownertype)
        
        for (dummy_owner, value) in self.db.get_all(q, ownername=ownername, ownertype=ownertype):
            self.emit(value, 4 * indent)
    
    def emit_group_hosts(self, groupname, indent):
        """ The bulk of the hosts have no options, which takes a while to dig out, therefore
            the host generation is split into two parts, the bulk is selected with one SQL qnd the rest with another."""
            
        qslow = """SELECT id, dns, mac, room, optionspace, entry_status, info, 'yes' FROM hosts h WHERE `group`= :groupname
            AND  
            ( h.entry_status = 'Active' AND
                (
                    EXISTS (SELECT * FROM optionset_boolval bv WHERE bv.optionset = h.optionset) OR
                    EXISTS (SELECT * FROM optionset_strval sv WHERE sv.optionset = h.optionset) OR
                    EXISTS (SELECT * FROM optionset_intval iv WHERE iv.optionset = h.optionset) OR
                    EXISTS (SELECT * FROM optionset_ipaddrval iav WHERE iav.optionset = h.optionset) OR
                    EXISTS (SELECT * FROM optionset_ipaddrarrayval iaav WHERE iaav.optionset = h.optionset) OR
                    EXISTS (SELECT * FROM optionset_intarrayval inav WHERE inav.optionset = h.optionset)
                )
            )
        """
        qfast = """
                   SELECT h.id, h.dns, h.mac, h.room, h.optionspace, h.entry_status, h.info, 'no' FROM `hosts` h
                   WHERE `group`= :groupname AND
                   h.entry_status != 'Dead' AND
                   (
                       h.entry_status = 'Inactive' OR NOT
                       (
                           EXISTS (SELECT * FROM optionset_boolval bv WHERE bv.optionset = h.optionset) OR
                           EXISTS (SELECT * FROM optionset_strval sv WHERE sv.optionset = h.optionset) OR
                           EXISTS (SELECT * FROM optionset_intval iv WHERE iv.optionset = h.optionset) OR
                           EXISTS (SELECT * FROM optionset_ipaddrval iav WHERE iav.optionset = h.optionset) OR
                           EXISTS (SELECT * FROM optionset_ipaddrarrayval iaav WHERE iaav.optionset = h.optionset) OR
                           EXISTS (SELECT * FROM optionset_intarrayval inav WHERE inav.optionset = h.optionset)
                       )
                    )"""
        allhosts = self.db.get(qfast, groupname=groupname)    
        allhosts.extend(self.db.get(qslow, groupname=groupname))
        
        # Sort them and emit
        for (hostid, dns, mac, room, optionspace, entry_status, info, hasopts) in sorted(allhosts, key=lambda x: x[0].lower()):
            self.emit_host(hostid, dns, mac, room, entry_status, optionspace, info, hasopts, indent)
        
    def emit_host(self, hostid, dns, mac, room, entry_status, optionspace, info, hasopts, indent):
        
        comment = ""
        if info:
            comment = info
        
        if room:
            if comment:
                comment += ", "
            comment += "Room %s" % room
            
        if comment:
            comment = "# " + comment
            
        if entry_status == 'Active':
            # host = self.host_manager.get_host(hostid)
            if hasopts == 'yes':
                self.emit("host %s %s" % (hostid, comment), 4 * indent)
                self.emit("{", 4 * indent)
                self.emit("hardware ethernet %s;" % mac, 4 * (indent + 1))
                if dns:
                    self.emit("fixed-address %s;" % dns, 4 * (indent + 1))
                self.emit_option_space(optionspace, (4 * (indent + 1)))
                host = self.host_manager.get_host(hostid)
                self.emit_optlist(host, indent + 1)
                # self.emit_option_list(hostid, optionspace, indent + 1, 'host')
                self.emit("}", 4 * indent)
            else:
                if dns:
                    self.emit("host %s { hardware ethernet %s; fixed-address %s;} %s" % (hostid, mac, dns, comment), 4 * indent)
                else:
                    self.emit("host %s { hardware ethernet %s;} %s" % (hostid, mac, comment), 4 * indent)
            return
    
        if entry_status == "Inactive":
            if dns:
                self.emit("#host %s { hardware ethernet %s; fixed-address %s;} # %s,  %s" % (hostid, mac, dns, entry_status, comment), 4 * indent - 1)
            else:
                self.emit("#host %s { hardware ethernet %s;} # %s,  %s" % (hostid, mac, entry_status, comment), 4 * indent - 1)
            return
   
    def emit_pool(self, poolname, optionspace, poolinfo, indent):
        
        info = "# Pool: %s. %s" % (poolname, poolinfo)
        pool = self.pool_manager.get_pool(poolname)
        
        optionset = pool.get_optionset()
        maxlease = optionset.get_option('max-lease-time')
            
        if maxlease or self.has_allowed_group(poolname):

            if info:
                self.emit("%s" % info, 4 * (indent + 1))
            
            q = "SELECT start_ip FROM pool_ranges WHERE pool=:poolname"
            sqlparams = {"poolname": poolname}
            if self.serverID:
                q += " AND (served_by=:served_by OR served_by IS NULL ) "
                sqlparams["served_by"] = self.serverID
            q += " ORDER BY start_ip asc"
            
            ret = self.db.get_all(q, **sqlparams)
            
            if not ret:
                if info:
                    self.emit("# Not generated as there are no defined IP ranges", 4 * (indent + 1))
                return
            
            if not self.has_grants(poolname) and not pool.open:
                if info:
                    self.emit("# Not generated as there are no defined grants to a closed pool", 4 * (indent + 1))
                return
             
            self.emit("pool", 4 * (indent + 1))
            self.emit("{", 4 * (indent + 1))
            # if maxlease: self.emit("max-lease-time %s;" % maxlease[0] ,4 * (indent+2))
            self.emit_option_space(optionspace, 4 * (indent + 2))
            
            self.emit_optlist(pool, indent + 2)
            # self.emit_option_list(poolname, optionspace, indent + 2, 'pool')
            self.emit_ranges(poolname, 4 * (indent + 2))
            self.emit_allow_classes(poolname, 4 * (indent + 2))
            self.emit("}", 4 * (indent + 1))
            
    def has_grants(self, poolname):
        q = "SELECT groupname FROM pool_group_map WHERE poolname=:poolname"
        grants = self.db.get_all(q, poolname=poolname)
        if grants:
            return True
        q = "SELECT classname FROM pool_class_map WHERE poolname=:poolname"
        grants = self.db.get_all(q, poolname=poolname)
        if grants:
            return True
        q = "SELECT hostname FROM pool_host_map WHERE poolname=:poolname"
        grants = self.db.get_all(q, poolname=poolname)
        if grants:
            return True
        return False
               
    def emit_allow_classes(self, poolname, indent):
        if self.has_allowed_group(poolname):
            q = "SELECT groupname FROM pool_group_map WHERE poolname=:poolname ORDER BY groupname ASC"
            for (groupname,) in self.db.get_all(q, poolname=poolname):
                groupclass = "allocation-class-group-%s" % (groupname)
                self.emit("allow members of \"%s\";" % groupclass, indent)
                
        q = "SELECT classname FROM pool_class_map WHERE poolname=:poolname ORDER BY classname ASC"
        for (classname,) in self.db.get_all(q, poolname=poolname):
            self.emit("allow members of \"%s\";" % classname, indent)
                
        q = "SELECT hostname FROM pool_host_map WHERE poolname=:poolname"
        hosts = self.db.get_all(q, poolname=poolname)
        if len(hosts):
            hostclass = "allocation-class-host-%s" % (poolname)
            self.emit("allow members of \"%s\";" % hostclass, indent)
              
    def emit_allowed_classes(self, poolname, indent):
    
# TODO: write the code to dig out the mac adderesses
# Typically:

# class "allocation-class-1" {
#  match pick-first-value (option dhcp-client-identifier, hardware);
# }
# class "allocation-class-2" {
#  match pick-first-value (option dhcp-client-identifier, hardware);
# }
# subclass "allocation-class-1" 1:8:0:2b:4c:39:ad;
# subclass "allocation-class-2" 1:8:0:2b:a9:cc:e3;
# subclass "allocation-class-2" 1:0:1c:c0:06:7e:84;
        count = 0
        if self.has_allowed_group(poolname):
            q = "SELECT groupname FROM pool_group_map WHERE poolname=:poolname ORDER BY groupname ASC"
            for (groupname,) in self.db.get_all(q, poolname=poolname):
                groupclass = "allocation-class-group-%s" % groupname
                if groupclass in self.generated_allocation_group_classes:
                    continue
                count += 1
                self.emit("class \"%s\" {" % groupclass, 4 * indent)
                self.emit("match pick-first-value (option dhcp-client-identifier, hardware);", 4 * (indent + 1))
                self.emit("}", 4 * (indent))
                g0 = "SELECT descendant FROM group_groups_flat WHERE groupname=:groupname"
                groups = [ x[0] for x in self.db.get(g0, groupname=groupname)]
                for g in groups:
                    q = "SELECT id, mac FROM hosts WHERE `group`= :groupname"
                
                    for (hostid, mac) in self.db.get_all(q, groupname=g):
                        self.emit("subclass \"%s\" 1:%s; # %s" % (groupclass, mac, hostid), 4 * (indent))
                self.generated_allocation_group_classes.add(groupclass)
                
        q = "SELECT hostname FROM pool_host_map WHERE poolname=:poolname"
        hosts = self.db.get_all(q, poolname=poolname)
        hosts = [x[0] for x in hosts]
        if len(hosts):
            hostclass = "allocation-class-host-%s" % (poolname)
            if hostclass in self.generated_allocation_group_classes:
                return
            count += 1
            self.emit("class \"%s\" {" % hostclass, 4 * indent)
            self.emit("match pick-first-value (option dhcp-client-identifier, hardware);", 4 * (indent + 1))
            self.emit("}", 4 * (indent))
            for h in hosts:
                q = "SELECT id, mac FROM hosts WHERE id=:id"
                for (hostid, mac) in self.db.get_all(q, id=h):
                    self.emit("subclass \"%s\" 1:%s; # %s" % (hostclass, mac, hostid), 4 * (indent))
        return count
    
    def emit_pools(self, network, indent):
        q = "SELECT poolname, optionspace, info FROM pools WHERE network=:network"
        
        for (poolname, optionspace, poolinfo) in self.db.get_all(q, network=network):
            self.emit_pool(poolname, optionspace, poolinfo, indent)

    def get_network_pools(self, netid):
        pools = set()
        q = "SELECT poolname FROM pools WHERE network=:netid"

        for (pool,) in self.db.get_all(q, netid=netid):
            pools.add(pool)
        return pools

    def emit_ranges(self, poolname, indent):
        
        argdict = {"poolname": poolname}
        q = "SELECT start_ip,end_ip FROM pool_ranges WHERE pool=:poolname "
        if self.serverID:
            q += " AND (served_by=:server_id OR served_by IS NULL ) "
            argdict["server_id"] = self.serverID
        q += " ORDER BY start_ip ASC"

        for(start, end) in self.db.get_all(q, **argdict):
            self.emit("range %s %s;" % (start, end), indent)

    def emit_subnetwork(self, subnet_id, network, info, hasopts, indent): 
            # print "em:",network,subnet_id,info  
            if info:
                info = "# " + info
            else:
                info = ""
            (subnet_addr, mask_length) = subnet_id.split('/')
            subnet_mask = socket.inet_ntoa(struct.pack(">L", (1 << 32) - (1 << 32 >> int(mask_length))))
            
            if hasopts == 'yes':
                subnetwork = self.subnetwork_manager.get_subnetwork(subnet_id)
                self.emit("subnet %s netmask %s     %s" % (subnet_addr, subnet_mask, info), 4 * (indent + 1))
                self.emit("{", 4 * (indent + 1))
                # self.emit("option subnet-mask %s;" % subnet_mask, 4 * (indent + 2))
                self.emit_optlist(subnetwork, indent + 2)
                # self.emit_option_list(subnet_id, '', indent + 2, 'subnetwork')
                self.emit("}", 4 * (indent + 1))
            
            else:
                self.emit("subnet %s netmask %s { } %s" % (subnet_addr, subnet_mask, info), 4 * (indent + 1))
                
    def emit_subnetworks(self, network, indent):   
        # q = "SELECT id, network, info FROM subnetworks WHERE `network`=:network ORDER BY (CONVERT(id USING latin1) COLLATE latin1_swedish_ci)"
        
        qslow = """ SELECT id, network, info, 'yes' FROM subnetworks s 
                    WHERE `network`=:network
                    AND  
                        (
                            EXISTS (SELECT * FROM optionset_boolval bv WHERE bv.optionset = s.optionset) OR
                            EXISTS (SELECT * FROM optionset_strval sv WHERE sv.optionset = s.optionset) OR
                            EXISTS (SELECT * FROM optionset_intval iv WHERE iv.optionset = s.optionset) OR
                            EXISTS (SELECT * FROM optionset_ipaddrval iav WHERE iav.optionset = s.optionset) OR
                            EXISTS (SELECT * FROM optionset_ipaddrarrayval iaav WHERE iaav.optionset = s.optionset) OR
                            EXISTS (SELECT * FROM optionset_intarrayval inav WHERE inav.optionset = s.optionset)
                        )
                    ORDER BY (CONVERT(id USING latin1) COLLATE latin1_swedish_ci)
                """
        qfast = """ SELECT id, network, info, 'no' FROM subnetworks s 
                    WHERE `network`=:network
                    AND NOT
                       (
                           EXISTS (SELECT * FROM optionset_boolval bv WHERE bv.optionset = s.optionset) OR
                           EXISTS (SELECT * FROM optionset_strval sv WHERE sv.optionset = s.optionset) OR
                           EXISTS (SELECT * FROM optionset_intval iv WHERE iv.optionset = s.optionset) OR
                           EXISTS (SELECT * FROM optionset_ipaddrval iav WHERE iav.optionset = s.optionset) OR
                           EXISTS (SELECT * FROM optionset_ipaddrarrayval iaav WHERE iaav.optionset = s.optionset) OR
                           EXISTS (SELECT * FROM optionset_intarrayval inav WHERE inav.optionset = s.optionset)
                       )
                    ORDER BY (CONVERT(id USING latin1) COLLATE latin1_swedish_ci)
                """
            
        allsubnetworks = self.db.get(qfast, network=network)    
        allsubnetworks.extend(self.db.get(qslow, network=network))
        
        # Sort them and emit
        for (subnet_id, network, info, hasopts) in sorted(allsubnetworks, key=lambda x: x[0].lower()):
            self.emit_subnetwork(subnet_id, network, info, hasopts, indent)

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
        # self.emit_option_list(classname, optionspace, 1, 'class')
        self.emit("}", 0)

    def emit_option_space(self, optionspace, indent):
    
        if optionspace:
            q = "SELECT type FROM optionspaces WHERE `value` = :optionspace"
            
            row = self.db.get_all(q, optionspace=optionspace)
            # print "Option space %s", optionspace, "row=", row
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
            # self.emit_option_list(groupname, optionspace, indent + 1, 'group')
    
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
            if type(value) is list:
                value = ", ".join([str(x) for x in value])
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
        # msg = msg.rstrip() + "\n"
        self.dhcpd_conf.append("%s%s\n" % (' ' * indent, msg))
        # self.dhcpd_conf.append(msg.rstrip() + "\n")
        # self.dhcpd_conf.append("\n")
        
    def check_config(self):

        if self.server.config("SKIP_DHCPD_CHECKS", default=None):
            self.server.logger.warning("WARNING! DHCPD Check skipped")
        else:
            if self.server.config("DHCPD_PATH", default=None):
                s = self.make_dhcpd_conf(None)
                of = tempfile.NamedTemporaryFile(bufsize=0)
                of.write(s.encode('utf-8'))
                filename = of.name
                rv = subprocess.call([self.server.config("DHCPD_PATH", default=None), "-t", "-cf", filename])
                if rv:
                    # print s.encode('utf-8')
                    raise ExtDhcpdRejectsConfigurationError()
            else:
                raise ExtDhcpdCheckConfigurationError()
            
    @entry(g_reload)        
    def trigger_reload(self):
        self.event_manager.add("reload", authuser=self.function.session.authuser)
