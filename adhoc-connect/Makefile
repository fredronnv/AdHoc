TOP=../..
SUBDIRS=
DISTDIR=${TOP}/dist/adhoc-connect
RELEASEDIR=${TOP}/releases
subdirs:
	for dir in $(SUBDIRS); do \
	    TOP=${TOP} $(MAKE) -e -C $$dir ${MAKEFLAGS} ;\
	done

clean:	
	rm -rf ${DISTDIR}
	for dir in $(SUBDIRS); do \
	    TOP=${TOP} $(MAKE) -e -C $$dir ${MAKEFLAGS}  clean;\
	done

install: clean
	for dir in $(SUBDIRS); do \
	    TOP=${TOP} $(MAKE) -e -C $$dir ${MAKEFLAGS}  install;\
	done
	svn_version=`svnversion | cut -f2 -d:`;\
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	mkdir -p ${DISTDIR};\
	cp -r INSTALL dhcpd-snmp  ${DISTDIR};\
	sed "s/@@ADHOC_RELEASE@@/$${revno}/" < ./adhoc-connect.sh | \
	sed "s/@@ADHOC_SVN_VERSION@@/$${svn_version}/" > ${DISTDIR}/adhoc-connect.sh ;\
	sed "s/@@ADHOC_RELEASE@@/$${revno}/" < ./install.sh | \
	sed "s/@@ADHOC_SVN_VERSION@@/$${svn_version}/" > ${DISTDIR}/install.sh ;\
	sed "s/@@ADHOC_RELEASE@@/$${revno}/" < ./adhoc-connect.cron | \
	sed "s/@@ADHOC_SVN_VERSION@@/$${svn_version}/" > ${DISTDIR}/adhoc-connect.cron
	
release: svnstatus install
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	(cd ${DISTDIR}/..; mv adhoc-connect adhoc-connect-$${revno};tar cf ${RELEASEDIR}/adhoc-connect-$${revno}.tar adhoc-connect-$${revno})

patchbump:
	(patch=`cat rel_patch`; patch=`expr $${patch} + 1`; echo $${patch} > rel_patch)
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	svn commit rel_patch -m "Bumped patch version to $${revno}"

minorbump:
	(minor=`cat rel_minor`; minor=`expr $${minor} + 1`; echo $${minor} > rel_minor; echo 0 > rel_patch)
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	svn commit rel_minor rel_patch -m "Bumped minor version to $${revno}"

majorbump:
	(major=`cat rel_major`; major=`expr $${major} + 1`; echo $${major} > rel_major; echo 0 > rel_minor; echo 0 > rel_patch)
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	svn commit rel_major rel_minor rel_patch -m "Bumped major version to $${revno}"

svnstatus:
	if svn status | grep '^M' ; then \
	    false ; \
	else \
	    svn_version=`svnversion | cut -f2 -d:`;\
	    if [ `svnversion rel_patch` -ge $${svn_version} ]; then \
	    	true; \
	    else \
	    	if [ `svnversion rel_minor` -ge $${svn_version} ]; then \
	    		true; \
	    	else \
	    	    if [ `svnversion rel_major` -ge $${svn_version} ]; then \
	    		true; \
	    	    else \
	    	    	echo "Release number for adhoc-connect needs to be bumped"; \
	    		false; \
	    	    fi \
	    	fi \
	    fi \
	fi
