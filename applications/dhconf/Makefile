TOP=../..
SUBDIRS=
DISTDIR=${TOP}/dist/dhconf
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
	cp INSTALL.txt dhconfproxy.py ${TOP}/client/rpcc_client.py ${DISTDIR};\
	sed "s/@@ADHOC_RELEASE@@/$${revno}/" < dhconf | \
	sed "s/@@ADHOC_SVN_VERSION@@/$${svn_version}/" > ${DISTDIR}/dhconf ;\
	(cd ${DISTDIR}; chmod +x dhconf; ./dhconf Release; mv ./dhconf-* ./dhconf ) ;\
	(cd ${DISTDIR}; find . -name \*.pyc -exec rm {} \;)

release: install
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	cp ${DISTDIR}/INSTALL.txt ${RELEASEDIR}/INSTALL_dhconf.txt ;\
	(cd ${DISTDIR}/..; mv dhconf dhconf-$${revno};tar cf ${RELEASEDIR}/dhconf-$${revno}.tar dhconf-$${revno};)
	
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
	if svn status | awk '{print $$1}' | grep 'M' ; then \
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
	    	    	echo "Release number for dhconf needs to be bumped"; \
	    		false; \
	    	    fi \
	    	fi \
	    fi \
	fi
