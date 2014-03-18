#!/bin/bash
#
# chkconfig: 35 90 12
# description: AdHoc server
#
# Get function from functions library
. /etc/init.d/functions
# Start the AdHoc server

export ADHOC_RUNTIME_HOME=${ADHOC_RUNTIME_HOME:-/server/AdHoc}
export ADHOC_USER=${ADHOC_USER:-srvadhoc}
PIDDIR=${ADHOC_RUNTIME_HOME}/var/run
LOGDIR=${ADHOC_RUNTIME_HOME}/var/log
start() 
{
    echo -n Starting AdHoc server:
    . $ADHOC_RUNTIME_HOME/.bashrc
	
    /usr/local/bin/daemon -P ${PIDDIR} --name=adhoc -r --user=${ADHOC_USER} --delay=1800 -outlog=${LOGDIR}/AdHoc.log -- python -u ${ADHOC_RUNTIME_HOME}/bin/adhocserv.py ${ADHOC_SERVER_HOST}:${ADHOC_SERVER_PORT} 
    ### Create the lock file ###
    success "AdHoc server startup"
    echo
}
# Stop the service AdHoc
stop() 
{
    echo -n Stopping AdHoc server:
    /usr/local/bin/daemon -P ${ADHOC_RUNTIME_HOME}/var/run --name=adhoc --stop
    echo
}

restart() 
{
	echo -n "Restarting AdHoc server: "
	. $ADHOC_RUNTIME_PATH/.bashrc
	/usr/local/bin/daemon -P ${ADHOC_RUNTIME_HOME}/var/run --name=adhoc --restart
}

status()
{
	if /usr/local/bin/daemon -P ${ADHOC_RUNTIME_HOME}/var/run --name=adhoc --running; then
		echo The AdHoc server is running
	else
		echo The AdHoc server is not running
	fi
}

### main logic ###
case "$1" in
  start)
        start
        ;;
  stop)
        stop
        ;;
  status)
        status AdHoc
        ;;
  restart|reload|condrestart)
        restart
        ;;
  *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
esac
exit 0
