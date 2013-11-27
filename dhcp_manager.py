#!/usr/bin/env python2.6

from model import *
from exttype import *
from function import Function

import server
import access
import authenticator
import database
import session


class DHCPConfManager(Manager):

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
        q = "SELECT `group` from hosts where id=%(host) limit 1"
        dhcp_group = self.db.get(q, host=host)
        return dhcp_group
    
    def dhcp_parent_group(self, dhcp_group):
        q = "SELECT parent_group from groups WHERE groupname = %(dhcp_group) LIMIT 1"
        parent_group = self.db.get(q, dhcp_group=dhcp_group)[0][0]
        return parent_group
    
    def lookup(self, table, key, where):
        q = "SELECT %(key) FROM %(table) WHERE %(where) LIMIT 1"
        row = self.db.get(q, dhcp_group=dhcp_group)[0]
        return row

    def make_dhcpd_conf(self):

        self.dhcpd_conf = ""  # String where we collect the config output
   
        self.emit("# dhcpd.conf - automatically generated")
        self.emit("")
        
        q = "SELECT value from global_options WHERE name='domain_name_servers'"
        iparr = []
        for ip in self.db.get(q):
            if ip:
                iparr.append(ip)
        if iparr:
            s = "option domain-name-servers "
            s += ', '.join(iparr)
            self.emit(s)

        q = "SELECT value from global_options WHERE name='routers'"
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
                emit(cmd+" "+arg+";")

#M =item option definitions
#M
    my @spacearr;
    my $space;
    $sth=sqlexec("select value from optionspaces");
    while (my ($space) = $sth->fetchrow)
    {
        if( $space)
        {
            push @spacearr, $space;
        }
    }
    if (scalar(@spacearr))
    {
        my $sth=sqlexec("select name,code,qualifier,type from $Conf::dhcp_option_defs where optionspace is null and code is not null and scope='dhcp'");
        while (my ($name, $code, $qual, $type)  =  $sth->fetchrow)
        {
        next if ($code == 43); ## NOTE This prevents us from overloading the vendor-encapsulated-options option If this is to be used
                   ## Define vendor-encapsulated-options with code 43 in the database and use that option. If anyone
                   ## defines another option with code 43, that one won't make it into the options definitoons and any
                   ## use of that option will cause a syntax error, which is a feature compared to the bug that will otherwise be
                   ## triggered.
#    trace("Option $name, qualifier=$qual\n",4);
            if($qual eq 'array' )
            {
                emit("option $name code $code = array of $type;");
            }
            else
            {n
                emit("option $name code $code = $type;");
            }
        }

        while ($space = shift @spacearr)
        {
            emit("option space $space;");

            my $sth=sqlexec("select name,code,qualifier,type from $Conf::dhcp_option_defs where optionspace='$space' and scope='dhcp'");
            while (my ($name, $code, $qual, $type) =  $sth->fetchrow)
            {
                if($qual eq 'array' )
                {
                    emit("option $space.$name code $code = array of $type;");
                }
                else
                {
                    emit("option $space.$name code $code = $type;");
                }
            }
        }
    }

#M =item classes
#M
    emit_classes();

#M =item networks possibly containing pools
#M
    emit_networks();

#M =item groups, possibly containing fixed-address hosts
#M
#M There are no global hosts as those are contained in a pseudo group internally named 'plain'. This group is generated
#M only as a comment.
#M
#M =back
#M
    emit_groups('NULL', 0);

}

sub
emit_classes()
{
    my $sth;

    $sth=sqlexec("select * from classes");

    while(my ($classname, $filename, $optionspace, $next_server, $server_name, $server_id, $vendorclass) = $sth->fetchrow())
    {
        if($classname)
        {
            emit_class($classname, $filename, $optionspace, $next_server, $server_name, $server_id, $vendorclass);
        }
    }
}

sub
emit_networks()
{

    my $sth=sqlexec("select * from networks");
    while(my ($id, $subnet_mask, $next_server, $server_name, $authoritative, $pools, $info) = $sth->fetchrow)
    {
        emit("# $info") if $info;
        my $sts=sqlexec("select * from subnetworks where `network`='$id'");
        my $haspools=has_pools($id);
        if($sts->fetchrow() || $haspools )
        {
        foreach my $poolname (get_network_pools($id))
            {
            emit_allowed_classes($poolname, 0);
        }
            emit("shared-network $id {");
            emit("    authoritative;") if $authoritative;
            emit("    option subnet-mask $subnet_mask;") if $subnet_mask;
            emit("    next-server $next_server;") if $next_server;
            emit("    server-name \"$server_name\";") if $server_name;
            emit_option_list($id, '', 1, 'network');
            emit_subnetworks($id, 0);
            emit_pools($id, 0);

            emit("}");
        }
        else
        {
            emit("#shared-network $id {} # Empty, no pools or subnetworks");
        }
    }
}

sub
emit_groups($$)
{
    my $parent= shift;
    my $rec_level= shift;
    my $sth;

    if($parent eq 'NULL')
    {
        $sth=sqlexec("select * from groups where parent_group is NULL");
    } 
    else
    {
        $sth=sqlexec("select * from groups where parent_group='$parent'");
    } 

    while(my ($groupname,$parent,$filename, $optionspace, $next_server, $server_name, $server_id) = $sth->fetchrow())
    {
        if($groupname)
        {
            emit_group_header($groupname, $parent, $filename, $optionspace, $rec_level, $next_server, $server_name, $server_id);
            emit_literal_options($groupname,  'group', $rec_level+1);
#        if ($groupname eq 'bat' || $groupname eq 'bat-test')
#        {
#        emit ('');
#        emit ('        # B-hack 2006-01-04:');
#        emit ('        if exists dhcp-parameter-request-list {');
#        emit ('            option dhcp-parameter-request-list = concat(option dhcp-parameter-request-list,d0,d1,d2,d3);');
#        emit ('        }');
#        emit ('');
#            }
            emit_groups($groupname, $rec_level+1);
            emit_group_hosts($groupname, $rec_level+1);
            emit_group_trailer($rec_level, $parent);
        }
    }
}

sub
emit_literal_options($$$)
{
    my $ownername = shift;
    my $ownertype = shift;
    my $rec_level = shift;

    my $sth;

    $sth=sqlexec("select owner,value from literal_options where `owner`='$ownername' and owner_type='$ownertype'");

    while( my ($owner,$value) = $sth->fetchrow())
    {
        emit($value,4*$rec_level);
    }
}

sub
emit_group_hosts($$)
{
    my $groupname = shift;
    my $rec_level = shift;

    my $sth;

    $sth=sqlexec("select id,mac,owner_CID,room,unix_timestamp(`expdate`),optionspace,entry_status from hostlist where `group`='$groupname'");

    while( my ($id,$mac,$owner,$room,$expdate,$optionspace,$entry_status) = $sth->fetchrow())
    {
        emit_host($id,$mac,$owner,$room,$expdate,$entry_status,$optionspace,$rec_level);
    }
}

sub
emit_host($$$$$$$)
{
    my $id = shift;
    my $mac = shift;
    my $owner = shift;
    my $room = shift;
    my $expdate = shift;
    my $entry_status = shift;
    my $optionspace = shift;
    my $rec_level = shift;
    my $comment;

    if ( $owner || $room )
    {
        $comment .= "# ";
        $comment .= "$owner " if $owner;
        $comment .= "$room " if $room;
    }

    if ( $entry_statuses{$entry_status} eq "entry" )
    {
        if (($expdate != 0) && (time() gt $expdate) )
        {
            $entry_status="Expired";
        }
    }

    if ( $entry_statuses{$entry_status} eq "entry" )
    {
        my $sth=sqlexec("select name,value from optionlist where `group` = '$id' and gtype = 'host'");
        my($name, $value) = $sth->fetchrow;
        if(length($name) == 0)
        {
            emit ("host $id { hardware ethernet $mac; fixed-address $id;} $comment", 4*$rec_level);
        }
        else
        {
            emit("host $id $comment", 4*$rec_level);
            emit("{",4*$rec_level);
            emit("hardware ethernet $mac;",4*($rec_level+1));
            emit("fixed-address $id;",4*($rec_level+1));
            emit_option_space($optionspace,(4*($rec_level+1)));
            emit_option_list($id, $optionspace, $rec_level+1, 'host');
            emit("}",4*$rec_level);
        }
        next;
    }

    if ( $entry_statuses{$entry_status} eq "commented_entry" )
    {
        emit ("#host $id { hardware ethernet $mac; fixed-address $id;} # $entry_status.  $comment",  4*$rec_level-1);
        next;
    }
}

sub
emit_pool($$)
{
    my $pool = shift;
    my $rec_level = shift;

    my $sth;


    $sth=sqlexec("select poolname,max_lease_time,members,optionspace,info from pools where poolname='$pool'");

    while( my ($id,$maxlease,$members,$optionspace,$info) = $sth->fetchrow())
    {
        $info = "# Pool: $id. $info";
#    $info = "# $info" if $info;
        if($maxlease || $members || has_allowed_group($id) || has_allowed_host($id))
        {
            emit("$info", 4*($rec_level+1)) if $info;
            my $stj=sqlexec("select start_ip from pool_ranges where pool='$id' and (served_by='$Conf::ServerID' or served_by IS NULL ) order by start_ip asc");
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
        $sth=sqlexec("select groupname from pool_allow_group where poolname='$pool' order by groupname asc");
    
    while( my ($groupname) = $sth->fetchrow())
    {
        my $groupclass = "allocation-class-group-$groupname";
        emit("allow members of \"$groupclass\";",$rec_level) if $groupclass;
    }
    }
    if(has_allowed_host($pool))
    {
        $sth=sqlexec("select host_id from pool_allow_host where poolname ='$pool' order by host_id asc");
    while( my ($hostname) = $sth->fetchrow())
    {
        my $hostclass = "allocation-class-host-$hostname";
        emit("allow members of \"$hostclass\";",$rec_level) if $hostclass;
    }
    }
}

# This routine emits the classes used to store the mac addresses for the groups and hosts that are to
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
        $sth=sqlexec("select groupname from pool_allow_group where poolname='$pool' order by groupname asc");
    
    while( my ($groupname) = $sth->fetchrow())
    {
        my $groupclass = "allocation-class-group-$groupname";
        next if(defined($generated_allocation_group_classes{$groupclass}));

        emit("class \"$groupclass\" {",  4*($rec_level));
        emit("match pick-first-value (option dhcp-client-identifier, hardware);", 4*($rec_level+1));
        emit("}", 4*($rec_level));

        my $sti=sqlexec("select id,mac from hostlist where `group`='$groupname'");

            while( my ($id,$mac) = $sti->fetchrow())
            {
        emit("subclass \"$groupclass\" 1:$mac; # $id",  4*($rec_level));
            }
        $generated_allocation_group_classes{$groupclass} = 1;
        }
    }
    if(has_allowed_host($pool))
    {
        $sth=sqlexec("select host_id from pool_allow_host where poolname='$pool' order by host_id asc");
    while( my ($hostname) = $sth->fetchrow())
    {
        my $hostclass = "allocation-class-host-$hostname";
        next if(defined($generated_allocation_host_classes{$hostclass}));

        emit("class \"$hostclass\" {",  4*($rec_level));
        emit("match pick-first-value (option dhcp-client-identifier, hardware);", 4*($rec_level+1));
        emit("}", 4*($rec_level));

        my $sti=sqlexec("select id, mac from hostlist where id='$hostname'");

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

    $sth=sqlexec("select poolname from pools where network='$network'");

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

    $sth=sqlexec("select poolname from pools where network='$network'");

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

    $sth=sqlexec("select start_ip,end_ip from pool_ranges where pool='$pool' and (served_by='$Conf::ServerID' or served_by IS NULL ) order by start_ip asc");


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

    $sth=sqlexec("select * from subnetworks where `network`='$network'");

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
        my $sth=sqlexec("select type from optionspaces where `value` = '$optionspace'");
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

    my $sth=sqlexec("select poolname from pools where `network` = '$network'");

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

    my $sth=sqlexec("select groupname from pool_allow_group where `poolname` = '$poolname'");

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

    my $sth=sqlexec("select host_id from pool_allow_host where `poolname` = '$poolname'");

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

    my $sth=sqlexec("select name from optionlist where `group` = '$optionlist' and gtype = '$gtype'");

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

    my $sth=sqlexec("select name,value from optionlist where `group` = '$optionlist' and gtype = '$gtype'");

    while( my($name, $value) = $sth->fetchrow)
    {
        my $sti = sqlexec("select optionspace,type,qualifier,scope from $Conf::dhcp_option_defs where name = '$name'");
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

    my $sti = sqlexec("select `mtime` from `timestamp` where `id` = 'reconf.$Conf::ServerID'");
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
        $sti=sqlexec("select mtime from $table where `mtime` > '$lastread' ");
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
