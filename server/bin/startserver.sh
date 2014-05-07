#!/bin/bash
export CHALMERS_DEPLOY_LEVEL="prod"
export INSTALL_HOME=`(cd ~srvadhoc/adhoc-server; pwd)`
. $INSTALL_HOME/etc/bashrc.public
. $INSTALL_HOME/etc/bashrc.private
exec python -u $ADHOC_RUNTIME_HOME/bin/adhocserv.py `hostname`:8877