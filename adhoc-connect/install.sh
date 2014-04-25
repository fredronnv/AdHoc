#!/bin/bash

# $Id:$
LOGFILE=/var/log/adhoc-connect-install.log
ADHOC_RELEASE="@@ADHOC_RELEASE@@"
ADHOC_SVN_VERSION="@@ADHOC_SVN_VERSION@@"



log()
{
        msg="`date '+%F %T'` INFO  $@"
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
        touch $2 || fatal "Cannot touch $2"
        if cmp $1 $2 >/dev/null 2>&1; then
                log "$1 needed no update"
        else
                cp $1 $2 || fatal "Cannot install or update $1"

                if [ -n "$3" ]; then
                        chmod $3 $2 || fatal "Cannot set mode on $2"
                fi
                log "$1 $ADHOC_RELEASE installed into $2"
        fi
}

update adhoc-connect.sh /cdg/sbin/adhoc-connect 744
update adhoc-connect.cron /etc/cron.d/adhoc-connect 644