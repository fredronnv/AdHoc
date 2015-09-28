#!/bin/bash

# $Id$

ADHOC_RELEASE="@@ADHOC_RELEASE@@"
ADHOC_SVN_VERSION="@@ADHOC_SVN_VERSION@@"

TMP_CONF=/etc/dhcp/dhcpd.conf.new
DHCPD_CONF=/etc/dhcp/dhcpd.conf
ADHOC_URL=https://adhoc.ita.chalmers.se:8877
ADHOC_API_VERSION=0

ADHOC_USER_HOME=/cdg/adhoc
VARDIR=${ADHOC_USER_HOME}/var
LOGDIR=${VARDIR}/log
LOGFILE=${LOGDIR}/adhoc-connect.log

AUTO=auto

# Prepend a timestamp to the message and send it to the log file
log()
{
    msg="`date '+%F %T'` INFO  $@"
    echo "$msg" >>$LOGFILE
}

# Like log but sent message both to stderr and to the log file
err()
{
    msg="`date '+%F %T'` ERROR $@"
    echo "$msg" >>$LOGFILE
    echo "$msg" >/dev/stderr
}

# Like error but terminate execution afterwards
fatal()
{
    msg="`date '+%F %T'` FATAL $@"
    echo "$msg" >>$LOGFILE
    echo "$msg" >/dev/stderr
    exit 1
}

# like fatal but does not log the error. Use when logging cannot be done
die()
{
    msg="`date '+%F %T'` FATAL $@"
    echo "$msg" >/dev/stderr
    exit 1
}

restart_server()
{
    if /etc/init.d/dhcpd restart >/dev/null 2>&1 ;  then
        :
    else
        err "Failed to restart dhcpd" # This can happen for semantic reasons not caught in syntax check
        mv ${DHCPD_CONF}.bak ${DHCPD_CONF} || fatal "Failed to restore ${DHCPD_CONF} from backup file"
        log "Previous dhcpd.conf file restored"
        /etc/init.d/dhcpd restart >/dev/null 2>&1
        log "dhcpd restarted with previous configuration"
        return
    fi
}

install_conf()
{
    # Do syntax check first
    if /usr/sbin/dhcpd -t -cf ${TMP_CONF} >/dev/null 2>&1; then
        # Save old config in case restarting server fails
        cp -p ${DHCPD_CONF} ${DHCPD_CONF}.bak || fatal "Failed to copy ${DHCPD_CONF} to backup file"
        mv ${TMP_CONF} ${DHCPD_CONF} || fatal "Failing to install fetched dhcpd.conf" 
    else
        fatal "$@ not approved by dhcpd"
    fi
    log "$@ conf installed"
    restart_server
    log "dhcpd restarted with new configuration"
}

main()
{   
    mkdir -p ${LOGDIR} || die "Cannot create directory for $LOGFILE"
    touch $LOGFILE || die "Cannot update $LOGFILE"

    touch ${DHCPD_CONF}  # Makes sure it exists
    if [ `egrep -v '^#' ${DHCPD_CONF} | wc -l` -lt 10 ]; then
        wget -q -O ${TMP_CONF} ${ADHOC_URL}/dhcpd/${ADHOC_API_VERSION} || fatal "Failed fetching dhcpd.conf from ${ADHOC_URL}"
        install_conf "Initial dhcpd.conf"
        exit 0
    fi

    wget -q -O  ${TMP_CONF} ${ADHOC_URL}/dhcpd/${ADHOC_API_VERSION}/${AUTO} || fatal "Failed fetching ${AUTO} dhcpd.conf from ${ADHOC_URL}"
    if [ `cat ${TMP_CONF} | wc -l` -gt 10 ]; then
        install_conf "Updated dhcpd.conf"
        exit 0
    fi
}

delay=`/sbin/ifconfig | grep inet | grep 129.16 | awk '{print $2}' | sed 's/addr://' | sed 's/\./+/g' | bc`
let "delay %= 7"
sleep $delay

main "$@"
#
##[END of File]##
