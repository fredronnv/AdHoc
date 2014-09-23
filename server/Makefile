TOP=..
SUBDIRS=
DISTDIR=${TOP}/dist/adhoc-server
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
	sed "s/@@ADHOC_RELEASE@@/$${revno}/" < ./lib/adhoc_version.template  | \
	sed "s/@@ADHOC_SVN_VERSION@@/$${svn_version}/" > ./lib/adhoc_version.py ;\
	cp -r .  ${DISTDIR};\
	rm -rf ${DISTDIR}/testing ${DISTDIR}/tmp;\
	sed "s/@@ADHOC_RELEASE@@/$${revno}/" <server_setup.txt >${DISTDIR}/INSTALL-server.txt;\
	rm ${DISTDIR}/server_setup.txt; \
	rm ${DISTDIR}/etc/bashrc.private; \
	echo "adhoc_svn_version = \"$${svn_version}\"" > ${DISTDIR}/lib/adhoc_version.py;\
	echo "adhoc_release = \"$${revno}\"" >>${DISTDIR}/lib/adhoc_version.py;\
	(cd ${DISTDIR}; find . -name \*.pyc -exec rm {} \;); \
	(cd ${DISTDIR}; find . -name \*.svn -exec rm {} \;); \
	(cd ${DISTDIR}; find . -name \*.gitignore -exec rm {} \;)
	
release: install
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	(cd ${DISTDIR}/..; mv adhoc-server adhoc-server-$${revno};tar cf ${RELEASEDIR}/adhoc-server-$${revno}.tar adhoc-server-$${revno})

patch: svnstatus patchbump install release

minor: svnstatus minorbump install release

major: svnstatus majorbump install release

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
	    	    	echo "Release number for server needs to be bumped"; \
	    		false; \
	    	    fi \
	    	fi \
	    fi \
	fi
	
svnmajor:
	svn_version=`svnversion | cut -f2 -d:`;\
	
