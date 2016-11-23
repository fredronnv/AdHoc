# .bashrc

# Source global definitions
if [ -f /etc/bashrc ]; then
    . /etc/bashrc
fi

# Uncomment the following line if you don't like systemctl's auto-paging feature:
# export SYSTEMD_PAGER=

# User specific aliases and functions

export CHALMERS_DEPLOY_LEVEL=${CHALMERS_DEPLOY_LEVEL:-devel}
export INSTALL_HOME=${PRINTERMAP_RUNTIME_HOME:-~}

. $INSTALL_HOME/printermap/etc/bashrc.public
. $INSTALL_HOME/printermap/etc/bashrc.private
