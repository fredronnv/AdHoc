#!/bin/bash
#
# chkconfig: 35 90 12
# description: AdHoc server
#
# Get function from functions library
. /etc/init.d/functions
# Start the AdHoc server

ADHOC_RUNTIME_HOME=${ADHOC_RUNTIME_HOME:-/server/AdHoc}
start() 
{
        echo -n Starting AdHoc server:
        . $ADHOC_RUNTIME_HOME/.bashrc
        /usr/local/bin/daemon --name=adhoc -d -v -r --user=srvadhoc--delay=1800  -l /var/log/AdHoc.log python $ADHOC_RUNTIME_PATH/bin/adhocserver.sh >>/var/log/AdHoc.log
        ### Create the lock file ###
        success $"AdHoc server startup"
        echo
}
<<<<<<< .mine
# Stop the service AdHoc
stop() {
        initlog -c "echo -n Stopping AdHoc server: "
        /usr/local/bin/daemon --name=adhoc --stop
        echo
}

restart() 
{
		initlog -c "Restarting AdHoc server: "
		. $ADHOC_RUNTIME_PATH/.bashrc
		/usr/local/bin/daemon --name=adhoc --restart
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
        echo "Usage: $0 {start|stop|restart|reload|status}"
        exit 1
esac
exit 0
