#!/bin/sh
# Backup the AdHoc mysql database

DATE=`date "+%Y-%m-%d-%H:%M:%S"`
export ADHOC_USER=${ADHOC_USER:-srvadhoc}
ADHOC_USER_HOME=$(eval echo ~${ADHOC_USER})
BACKUPDIR=${ADHOC_USER_HOME}/var/backups
mkdir -p ${BACKUPDIR}
TMPDIR=${ADHOC_USER_HOME}/var/tmp
mkdir -p ${TMPDIR}
export CHALMERS_DEPLOY_LEVEL=install
. ${ADHOC_USER_HOME}/etc/bashrc.private
PWF=`mktemp -t` || exit 1

# Create a temporary config file
cat /etc/my.cnf >${PWF}
echo >>${PWF}
cat >>${PWF} <<EOF
[mysqldump]
user = root
password = ${ADHOC_DB_PASSWORD}
all-databases = TRUE
quote-names = TRUE
create-options = TRUE
disable-keys = TRUE
events = TRUE
flush-logs = TRUE
flush-privileges = TRUE
single-transaction = TRUE
extended-insert = TRUE
EOF

# Backup all databases
mysqldump   --defaults-file=${PWF} > ${BACKUPDIR}/mysql_backup.${DATE}
rm ${PWF}

if [ -s ${BACKUPDIR}/mysql_backup.${DATE} ]; then # If we have a new nonzero size file and we manage to compress it, remove files older than 7 days.
	gzip ${BACKUPDIR}/mysql_backup.${DATE} && \
	chmod go-rw ${BACKUPDIR}/mysql_backup.${DATE}.gz && \
	find ${BACKUPDIR} -type f -mtime +7 -exec rm -f {} \;
fi

