#!/usr/bin/env python2.6

from model import *
from exttype import *
from function import Function

import server
import access
import authenticator
import database
import session


class DHCPManager(Manager):

    entry_statuses = {}

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

    def make_config(self, serverID):
        """This method extracts relevant data from the database to create a configuration file
           for an ISC dhcp server"""
        
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
        q ="SELECT value FROM optionspaces"
        
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
                    self.emit("option %s code %s = array of %s;" % (name, code, option_type));
                else:
                    self.emit("option %s code %s = %s;" % (name, code, option_type));

            for space in spacearr:
                self.emit("option space %s;" % space)
                
                q = "SELECT name, code, qualifier, type FROM option_defs WHERE optionspace=%(space)"
                for (name, code, qual, option_type) in self.db.get(q):
                    if qual == 'array':
                        self.emit("option %s.%s code %s = array of %s;" % (space, name, code, option_type));
                    else:
                        self.emit("option %s.%s code %s = %s;" % (space, name, code, option_type));
       
        self.emit_classes();
        self.emit_networks();
        self.emit_groups();

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
                    self.emit_allowed_classes(poolname, 0);
                self.emit("shared-network %s {" % netid);
                if authoritative:
                    self.emit("    authoritative;")
                self.emit_option_list(netid, '', 1, 'network')
                self.emit_subnetworks(netid, 0)
                self.emit_pools(netid, 0)
                self.emit("}");
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
            self.emit_literal_options(groupname,  'group', indent+1)
            self.emit_groups(groupname, indent+1);
            self.emit_group_hosts(groupname, indent+1);
            self.emit_group_trailer(indent, parent);
 

    def emit_literal_options(self, ownername, ownertype, indent):
    
        q = "SELECT owner, value FROM literal_options WHERE `owner`=%(ownername) AND owner_type=%(ownertype)"
        
        for (dummy_owner, value) in self.db.get(q, ownername=ownername, ownertype=ownertype):
            self.emit(value, 4*indent)
    
    def emit_group_hosts(self, groupname, indent):
        q = "SELECT id, dns, mac, room, optionspace, entry_status FROM hosts WHERE `group`=%(groupname)"
    
        for (id, dns, mac, room, optionspace, entry_status) in self.db.get(q, groupname=groupname):
            self.emit_host(id, dns, mac, room, entry_status, optionspace, indent)
        
    def emit_host(self, hostid, dns, mac, room, entry_status, optionspace, indent):
        
        comment = ""
        
        if room:
            comment += "# Room %s" % room
            
        if entry_status == 'Active':
            q = "SELECT name, value FROM host_options WHERE `for` = %(hostid) "
            if not self.db.get(q, hostid=hostid):
                self.emit("host %s { hardware ethernet %s; fixed-address %s;} %s" % (hostid, mac, dns), 4*indent)
            
            else:
                self.emit("host %s %s" % (hostid, comment), 4*indent)
                self.emit("{", 4*indent)
                self.emit("hardware ethernet %s" % mac, 4*(indent+1))
                self.emit("fixed-address %s;" % dns, 4*(indent+1))
                self.emit_option_space(optionspace, (4*(indent+1)));
                self.emit_option_list(hostid, optionspace, indent+1, 'host');
                self.emit("}",4*indent);
            continue
    
    
        if entry_status == "Inactive":
            self.emit("#host %s { hardware ethernet %s; fixed-address %s;} # %s,  %s" % (hostid, mac, dns, entry_status, comment), 4*indent-1);
            continue
 

sub
emit_pool($$)
{
    my $pool = shift;
    my $rec_level = shift;

    my $sth;


    $sth=sqlexec("SELECT poolname,max_lease_time,members,optionspace,info FROM pools WHERE poolname='$pool'");

    while( my ($id,$maxlease,$members,$optionspace,$info) = $sth->fetchrow())
    {
        $info = "# Pool: $id. $info";
#    $info = "# $info" if $info;
        if($maxlease || $members || has_allowed_group($id) || has_allowed_host($id))
        {
            emit("$info", 4*($rec_level+1)) if $info;
            my $stj=sqlexec("SELECT start_ip FROM pool_ranges WHERE pool='$id' AND (served_by='$Conf::ServerID' OR served_by IS NULL ) ORDER BY start_ip asc");
            if(! $stj->fetchrow())  # only if there are any IP ranges.
            {
                emit("# Not generated as there are no defined IP ranges",4*($rec_level+1)) if $info;
                next;
            }
        #emit_allowed_classes($pool, $rec_level);
            emit("pool", 4*($rec_level+1));
            emit("{",4*($rec_level+1));
            emit("max-lease-time $maxlease;" ,4*($rec_level+2)) if  $maxlease;
            emit_option_space($optionspace,4*($rec_level+2));
            my @classes=split / /,$members;
            foreach my $m ( split / /, $members)
            {
                emit("allow members of \"$m\";",4*($rec_level+2)) if $m;
            }
            emit_option_list($id, $optionspace, $rec_level+2, 'pool');
            emit_ranges($id,4*($rec_level+2));
        emit_allow_classes($id, 4*($rec_level+2));
            emit("}",4*($rec_level+1));
        }
    }
}

# This routine emits the allow statements for allowed groups and hosts
sub
emit_allow_classes($$)
{
    my $pool = shift;
    my $rec_level = shift;

    my $sth;
    
    if(has_allowed_group($pool))
    {
        $sth=sqlexec("SELECT groupname FROM pool_allow_group WHERE poolname='$pool' ORDER BY groupname asc");
    
    while( my ($groupname) = $sth->fetchrow())
    {
        my $groupclass = "allocation-class-group-$groupname";
        emit("allow members of \"$groupclass\";",$rec_level) if $groupclass;
    }
    }
    if(has_allowed_host($pool))
    {
        $sth=sqlexec("SELECT host_id FROM pool_allow_host WHERE poolname ='$pool' ORDER BY host_id asc");
    while( my ($hostname) = $sth->fetchrow())
    {
        my $hostclass = "allocation-class-host-$hostname";
        emit("allow members of \"$hostclass\";",$rec_level) if $hostclass;
    }
    }
}

# This routine emits the classes used to store the mac addresses for the groups AND hosts that are to
# be allowed into a pool

sub
emit_allowed_classes($$)
{
    my $pool = shift;
    my $rec_level = shift;
    my $sth;
    our %generated_allocation_group_classes;
    our %generated_allocation_host_classes;
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
    if(has_allowed_group($pool))
    {
        $sth=sqlexec("SELECT groupname FROM pool_allow_group WHERE poolname='$pool' ORDER BY groupname asc");
    
    while( my ($groupname) = $sth->fetchrow())
    {
        my $groupclass = "allocation-class-group-$groupname";
        next if(defined($generated_allocation_group_classes{$groupclass}));

        emit("class \"$groupclass\" {",  4*($rec_level));
        emit("match pick-first-value (option dhcp-client-identifier, hardware);", 4*($rec_level+1));
        emit("}", 4*($rec_level));

        my $sti=sqlexec("SELECT id,mac FROM hostlist WHERE `group`='$groupname'");

            while( my ($id,$mac) = $sti->fetchrow())
            {
        emit("subclass \"$groupclass\" 1:$mac; # $id",  4*($rec_level));
            }
        $generated_allocation_group_classes{$groupclass} = 1;
        }
    }
    if(has_allowed_host($pool))
    {
        $sth=sqlexec("SELECT host_id FROM pool_allow_host WHERE poolname='$pool' ORDER BY host_id asc");
    while( my ($hostname) = $sth->fetchrow())
    {
        my $hostclass = "allocation-class-host-$hostname";
        next if(defined($generated_allocation_host_classes{$hostclass}));

        emit("class \"$hostclass\" {",  4*($rec_level));
        emit("match pick-first-value (option dhcp-client-identifier, hardware);", 4*($rec_level+1));
        emit("}", 4*($rec_level));

        my $sti=sqlexec("SELECT id, mac FROM hostlist WHERE id='$hostname'");

            while( my ($id,$mac) = $sti->fetchrow())
            {
            emit("subclass \"$hostclass\" 1:$mac; #$id", 4*($rec_level));
        }
        $generated_allocation_host_classes{$hostclass} = 1;
    }
    }
}

sub
emit_pools($$)
{
    my $network = shift;
    my $rec_level = shift;

    my $sth;

    $sth=sqlexec("SELECT poolname FROM pools WHERE network='$network'");

    while( my($poolname) = $sth->fetchrow())
    {
        emit_pool($poolname, $rec_level);
    }
}

sub
get_network_pools($)
{
    my $network = shift;

    my $sth;
    my @pools;

    $sth=sqlexec("SELECT poolname FROM pools WHERE network='$network'");

    while( my($poolname) = $sth->fetchrow())
    {
    push @pools, $poolname;
    }
    return @pools;
}

sub
emit_ranges($$)
{
    my $pool = shift;
    my $rec_level = shift;

    my $sth;

    $sth=sqlexec("SELECT start_ip,end_ip FROM pool_ranges WHERE pool='$pool' AND (served_by='$Conf::ServerID' OR served_by IS NULL ) ORDER BY start_ip asc");


    while( my($start,$end) = $sth->fetchrow())
    {
        emit("range $start $end;",$rec_level);
    }
}

sub
emit_subnetworks($$)
{
    my $network = shift;
    my $rec_level = shift;

    my $sth;

    $sth=sqlexec("SELECT * FROM subnetworks WHERE `network`='$network'");

    while( my ($id,$netmask,$subnet_mask,$next_server,$server_name,$server_id,$network,$info) = $sth->fetchrow())
    {
        $id=sprintf  "%-15s",$id;
        $netmask=sprintf  "%-15s",$netmask;
        $info = "# $info" if $info;
        my $hasoptionlist=has_option_list($id, '', 1, 'subnetwork');
        if($next_server || $server_name || $server_id || $subnet_mask || $hasoptionlist)
        {
            emit("subnet $id netmask $netmask     $info", 4*($rec_level+1));
            emit("{", 4*($rec_level+1));
            emit("option subnet-mask $subnet_mask;" ,4*($rec_level+2)) if  $subnet_mask;
            emit("next-server $next_server;",4*($rec_level+2)) if $next_server;
            emit("server-name \"$server_name\";",4*($rec_level+2)) if $server_name;
            emit("server-identifier $server_id;",4*($rec_level+2)) if $server_id;
            emit_option_list($id, '', $rec_level+2, 'subnetwork') if $hasoptionlist;
            emit("}",4*($rec_level+1));
        }
        else
        {
            emit("subnet $id netmask $netmask { } $info", 4*($rec_level+1));
        }
    }
}

sub
emit_class($$$$$$$$)
{
    my $classname = shift;
    my $filename = shift;
    my $optionspace = shift;
    my $next_server = shift;
    my $server_name = shift;
    my $server_id = shift;
    my $vendor_class_id = shift;

    emit("class \"$classname\"" ,0);
    emit("{",0);
    if ($vendor_class_id)
    {
        my $len=length($vendor_class_id);
        emit("match if substring (option vendor-class-identifier, 0, $len) = \"$vendor_class_id\";",4);
    }
#    emit("match if option vendor-class-identifier = \"$vendor_class_id\";",4) if $vendor_class_id;
    emit("filename \"$filename\";",4) if $filename;
    emit_option_space($optionspace,4);
    emit("next-server $next_server;",4) if $next_server;
    emit("server-name \"$server_name\";",4) if $server_name;
    emit("server-identifier $server_id;",4) if $server_id;
    emit_literal_options($classname,  'class', 1);
    emit_option_list($classname, $optionspace, 1, 'class');
    emit("}",0);
}

sub emit_option_space($$)
{
    my $optionspace=shift;
    my $rec_level = shift;

    if(length($optionspace))
    {
        my $sth=sqlexec("SELECT type FROM optionspaces WHERE `value` = '$optionspace'");
        if( my($type) = $sth->fetchrow)
        {
            if($type eq 'site')
            {
                emit("site-option-space \"$optionspace\";",$rec_level)
            }
            if($type eq 'vendor')
            {
                emit("vendor-option-space $optionspace;",$rec_level)
            }
        }
    }
}


sub
emit_group_header($$$$$$)
{
    my $groupname = shift;
    my $parent = shift;
    my $filename = shift;
    my $optionspace = shift;
    my $rec_level = shift;
    my $next_server = shift;
    my $server_name = shift;
    my $server_id = shift;

#    emit("#group name '$groupname'");

    if ($parent)
    {
        emit("group \"$groupname\"",4*$rec_level);
        emit("{",4*$rec_level);
        emit("    filename \"$filename\";",4*$rec_level) if $filename;
#        emit("    vendor-option-space $optionspace;",4*$rec_level) if $optionspace;
        emit_option_space($optionspace,4*($rec_level+1));
        emit("next-server $next_server;",4*($rec_level+1)) if $next_server;
        emit("server-name \"$server_name\";",4*($rec_level+1)) if $server_name;
        emit("server-identifier $server_id;",4*($rec_level+1)) if $server_id;
        emit_option_list($groupname, $optionspace, $rec_level+1,'group');
    }

}

sub
emit_group_trailer($$)
{
    my $rec_level = shift;
    my $parent = shift;

    emit("}",4*$rec_level) if ($parent);
}

sub
has_pools($)
{
    my $network = shift;

    if (! defined ($network) )
    {
        return 0;
    }

    my $sth=sqlexec("SELECT poolname FROM pools WHERE `network` = '$network'");

    if( my($name) = $sth->fetchrow)
    {
        return 1;
    }
    return 0;
}

sub
has_allowed_group($)
{
    my $poolname = shift;

    if (! defined ($poolname) )
    {
        return 0;
    }

    my $sth=sqlexec("SELECT groupname FROM pool_allow_group WHERE `poolname` = '$poolname'");

    if( my($name) = $sth->fetchrow)
    {
        return 1;
    }
    return 0;
}

sub
has_allowed_host($)
{
    my $poolname = shift;

    if (! defined ($poolname) )
    {
        return 0;
    }

    my $sth=sqlexec("SELECT host_id FROM pool_allow_host WHERE `poolname` = '$poolname'");

    if( my($name) = $sth->fetchrow)
    {
        return 1;
    }
    return 0;
}

sub
has_option_list($$$$)
{
    my $optionlist = shift;
    my $optionspace = shift;
    my $rec_level = shift;
    my $gtype = shift;
    my $spaceprefix;

    if (! defined ($optionlist) )
    {
        return 0;
    }

    if(defined($optionspace))
    {
        $spaceprefix .= $optionspace.'.';
    }

    my $sth=sqlexec("SELECT name FROM optionlist WHERE `group` = '$optionlist' AND gtype = '$gtype'");

    if( my($name) = $sth->fetchrow)
    {
        return 1;
    }
}

sub
emit_option_list($$$$)
{
    my $optionlist = shift;
    my $optionspace = shift;
    my $rec_level = shift;
    my $gtype = shift;
    my $spaceprefix;

    if (! defined ($optionlist) )
    {
        return;
    }

    if(defined($optionspace))
    {
        $spaceprefix .= $optionspace.'.';
    }

    my $sth=sqlexec("SELECT name,value FROM optionlist WHERE `group` = '$optionlist' AND gtype = '$gtype'");

    while( my($name, $value) = $sth->fetchrow)
    {
        my $sti = sqlexec("SELECT optionspace,type,qualifier,scope FROM $Conf::dhcp_option_defs WHERE name = '$name'");
        my ($space,$type,$qual,$scope)=$sti->fetchrow;
    next if ($scope ne 'dhcp');
    my $opt;
    if($qual ne "parameter" && $qual ne "parameter-array")
    {
        $opt = 'option ';
    }
        $space .= "." if $space;
        if ($type eq 'text')
        {
            emit ("$opt$space$name \"$value\";",4*$rec_level);
        }
        else
        {
            emit ("$opt$space$name $value;",4*$rec_level);
        }
    }
}

#
# Convert seconds to ISO 8601 time string
#
sub
Epoch2Iso($)
{
    my $ep = shift (@_);
    my ($s,$m,$h,$dd,$mm,$yyyy,$wday,$yday,$isdst) = localtime($ep);
    return sprintf("%04d-%02d-%02d %02d:%02d:%02d",$yyyy+1900,$mm+1,$dd,$h,$m,$s);
}

sub
db_changed()
{
    my @tables;
    my $table;

    my $sti = sqlexec("SELECT `mtime` FROM `timestamp` WHERE `id` = 'reconf.$Conf::ServerID'");
    my ($lastread) = $sti->fetchrow();
    if (!length($lastread))
    {
        sqlexec("insert into timestamp values('reconf.$Conf::ServerID',0,'flum',now())");
    }

# Find tables that have timestamp columns
    my $sth = sqlexec("show tables");
    while( my($tablename) = $sth->fetchrow)
    {
        $sti=sqlexec("describe $tablename");
        while( my ($field) = $sti->fetchrow() )
        {
#            print STDERR "Table $tablename, field $field\n";
            if ( $field eq 'mtime' )
            {
                push @tables, $tablename;
                last;
            }
        }
    }
# Check the timestamps, if one have changed, the database has changed as well
    foreach $table (@tables)
    {
        next if $table eq 'timestamp';
        $sti=sqlexec("SELECT mtime FROM $table WHERE `mtime` > '$lastread' ");
        while( my ($id) = $sti->fetchrow() )
        {
            trace("Database table $table was changed since $lastread\n",1);
            return 1;
        }
    }
    return 0;
}


sub
emit_conf4($,$)
{
    my $msg = shift;
    my $indent = shift;

    $|=1;
    chomp $msg;
    $msg = $msg."\n";
    
    if($Conf::HostConf4)
    {
        print CONFOUT ' 'x$indent."$msg";
    }
    else
    {
        print ' 'x$indent."$msg";
    }
}

sub
emit_conf3($,$)
{
    my $msg = shift;
    my $indent = shift;
    
    $|=1;
    chomp $msg;
    $msg = $msg."\n";
    
    if($Conf::HostConf3)
    {
        print CONFOUT ' 'x$indent."$msg";
    }
    else
    {
        print ' 'x$indent."$msg";
    }

}

sub
emit_conf($,$)
{
    my $msg = shift;
    my $indent = shift;
    
    $|=1;
    chomp $msg;
    $msg = $msg."\n";
    
    print CONFOUT ' 'x$indent."$msg";
}

sub
emit($,$)
{
    my $msg = shift;
    my $indent = shift;

    $|=1;
    chomp $msg;
    $msg = $msg."\n";
    
    if($Conf::DhcpConfig)
    {
    print OUT ' 'x$indent."$msg";
    }
    else
    {
        print ' 'x$indent."$msg";
    }
}


sub
sqlexec($)
{
    my $sql = shift;
#    print "$sql\n";
    my $sth = $Conf::dbh->prepare($sql)  or die "Can't prepare statement: \n$sql\n$DBI::errstr";
    my $rc = $sth->execute or die "Can't execute statement:\n$sql\n$DBI::errstr";
    return $sth;
}

sub
trace($:$)
{
    my $msg = shift;
    my $minlevel = shift;

    if(!defined($minlevel)) 
    {
        $minlevel=1;
    }
    $|=1;
    chomp $msg;
    $msg = $msg."\n";
    my $datestr=Epoch2Iso(time);
    my $indent="  "x$minlevel;
    print "$datestr:$indent$msg" if ($Conf::Trace >= $minlevel || $minlevel == 0);
    if($Conf::LogFileOpen)
    {
        print LOG "$datestr [$$]:$indent$msg" if($Conf::LogTrace >= $minlevel);
    }
}

sub
sql_open()
{
    $Conf::todolist=();
}

sub
sql_do($)
{
    my $t = shift;
    push @Conf::todolist,$t;
#    print("Added $t to todo list\n");
}

sub
sql_done()
{
    $Conf::dbh->{AutoCommit} = 0;
    $Conf::dbh->{RaiseError} = 1;
    eval
    {
        for my $sql (@Conf::todolist)
        {
            my $sth= $Conf::dbh->prepare($sql);
            $sth->execute;
        }
        $Conf::dbh->commit;
    };
    if($@)
    {
        print("Transaction aborted because $@, rolling back all changes.");
# now rollback to undo the incomplete changes
# but do it in an eval{} as it may also fail
        eval { $Conf::dbh->rollback };
# add other application on-error-clean-up code here
    }
    $Conf::dbh->{AutoCommit} = 1;
    $Conf::dbh->{RaiseError} = 0;
}    

#use sigtrap qw(die untrapped normal-signals error-signals);

$SIG{INT} = sub { print "Please do not interrupt!\n"; };
$SIG{QUIT} = sub { print "We never quit\n"; };
$SIG{TERM} = sub { print "Terminate someone else!\n"; };
$SIG{HUP} = sub { print "Don't hang up on me!\n"; };
$SIG{PIPE} = sub { };
$Conf::tolock="/var/run/mkdhcp.lock";

Main(@ARGV);


END
{
    if (length($Conf::locktoremove))
    {
        unlink($Conf::locktoremove."/pid");
        rmdir($Conf::locktoremove);
    }
}
#M =head1 AUTHOR
#M 
#M Christer Bernerus, bernerus@medic.chalmers.se
#M 
#M =head1 SEE ALSO
#M 
#M perl(1), dhcpd(1)
#M 
#M =cut
