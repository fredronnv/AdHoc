#!/bin/bash
#
# chkconfig: 35 90 12
# description: AdHoc server
#
# Get function from functions library
. /etc/init.d/functions
# Start the AdHoc server
start() {
        initlog -c "echo -n Starting AdHoc server: "
        . $ADHOC_RUNTIME_PATH/.bashrc
        daemon d -v -r python $ADHOC_RUNTIME_PATH/bin/adhocserver.sh >>/var/log/AdHoc.log
        ### Create the lock file ###
        touch /var/lock/subsys/AdHoc
        success $"AdHoc server startup"
        echo
}
# Restart the service AdHoc
stop() {
        initlog -c "echo -n Stopping AdHoc server: "
        killproc AdHoc
        ### Now, delete the lock file ###
        rm -f /var/lock/subsys/AdHoc
        echo
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
        stop
        start
        ;;
  *)
        echo $"Usage: $0 {start|stop|restart|reload|status}"
        exit 1
esac
exit 0