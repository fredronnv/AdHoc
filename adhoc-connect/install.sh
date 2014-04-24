#!/bin/bash

LOGFILE=/var/log/adhoc-connect-install.log

log()
{
        msg="`date '+%F %T'` INFO  $@"
        echo "$msg" >/dev/stderr
        echo "$msg" >>$LOGFILE
}

err()
{
        msg="`date '+%F %T'` ERROR $@"
        echo "$msg" >/dev/stderr
        echo "$msg" >>$LOGFILE
}

fatal()
{
        msg="`date '+%F %T'` FATAL $@"
        echo "$msg" >/dev/stderr
        echo "$msg" >>$LOGFILE
        exit 1
}

update()
{
        mkdir -p $2 || fatal "Cannot establish destination directory $2"
        touch $2/$1 || fatal "Cannot touch $2/$1"
        if cmp $1 $2/$1 >/dev/null 2>&1; then
                log "$1 needed no update"
        else
                cp $1 $2/$1 || fatal "Cannot or update $1"
                if [ -n "$3" ]; then
                        chmod $3 $2/$1 || fatal "Cannot set mode on $1"
                fi
                log "$1 $rev installed into $2"
        fi
}

cd /cdg/dist/adhoc-connect || fatal "Cannot cd to /cdg/dist/adhoc-connect"
rev=`svn info | grep Revision:`

update adhoc-connect.sh /cdg/sbin 744
update adhoc-connect.cron /etc/cron.d 644
cd README/adhoc-connect; 
update adhoc-connect-auto.txt /cdg/README/adhoc-connect
cd CONF; 
update dhcpd /cdg/README/adhoc-connect/CONF
