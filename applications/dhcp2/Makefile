TOP=../..
SUBDIRS=
DISTDIR=${TOP}/dist/dhcp2
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
	cp dhcp2proxy.py ${TOP}/client/rpcc_client.py ${DISTDIR};\
	sed "s/@@ADHOC_RELEASE@@/$${revno}/" < dhcp2 | \
	sed "s/@@ADHOC_SVN_VERSION@@/$${svn_version}/" > ${DISTDIR}/dhcp2 ;\
	(cd ${DISTDIR}; chmod +x dhcp2; ./dhcp2 Release; mv ./dhcp2-* ./dhcp2)

release: install
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	(cd ${DISTDIR}/..; mv dhcp2 dhcp2-$${revno};tar cf ${RELEASEDIR}/dhcp2-$${revno}.tar dhcp2-$${revno})
	
patch: svnstatus patchbump install

minor: svnstatus minorbump install

major: svnstatus majorbump install

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
	    	    	echo "Release number for dhcp2 needs to be bumped"; \
	    		false; \
	    	    fi \
	    	fi \
	    fi \
	fi
