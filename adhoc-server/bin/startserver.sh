#!/bin/sh
if [ -e /etc/bashrc.public ]; then
  source /etc/bashrc.public
fi

if [ -e /etc/bashrc.private ]; then
  source /etc/bashrc.private
fi

exec python -u $ADHOC_RUNTIME_HOME/bin/adhocserv.py --host=$ADHOC_SERVER_HOST --port=$ADHOC_SERVER_PORT
