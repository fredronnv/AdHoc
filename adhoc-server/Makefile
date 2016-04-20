TOP=..
SUBDIRS=
DISTDIR=${TOP}/dist/adhoc-server
RELEASEDIR=${TOP}/releases
RPCC_DIR=${TOP}/../RPCC/rpcc
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
	git_version=`git rev-list --max-count=1 HEAD`
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	mkdir -p ${DISTDIR};\
	cp -r .  ${DISTDIR};\
	cp -r ${RPCC_DIR} ${DISTDIR};\
	rm -rf ${DISTDIR}/testing ${DISTDIR}/tmp;\
	cp ./fix-files-adhoc-server.sh ${DISTDIR}; \
	chmod +x ${DISTDIR}/fix-files-adhoc-server.sh; \
	sed "s/@@ADHOC_RELEASE@@/$${revno}/" <server_setup.txt >${DISTDIR}/INSTALL.txt;\
	rm ${DISTDIR}/server_setup.txt; \
	rm -f ${DISTDIR}/etc/bashrc.private; \
	echo "adhoc_git_version = \"$${git_version}\"" > ${DISTDIR}/lib/adhoc_version.py;\
	echo "adhoc_release = \"$${revno}\"" >>${DISTDIR}/lib/adhoc_version.py;\
	(cd ${DISTDIR}; find . -name \*.pyc -exec rm {} \;); \
	(cd ${DISTDIR}; find . -name \*.svn -exec rm {} \;); \
	(cd ${DISTDIR}; find . -name \*.git -exec rm {} \;); \
	(cd ${DISTDIR}; find . -name \*.gitignore -exec rm {} \;)

release: install
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	cp ${DISTDIR}/INSTALL.txt ${RELEASEDIR}/INSTALL_adhoc-server.txt ;\
	(cd ${DISTDIR}/..; mv adhoc-server adhoc-server-$${revno};tar cf ${RELEASEDIR}/adhoc-server-$${revno}.tar adhoc-server-$${revno})

patch: gitstatus patchbump install release

minor: gitstatus minorbump install release

major: gitstatus majorbump install release

patchbump:
	(patch=`cat rel_patch`; patch=`expr $${patch} + 1`; echo $${patch} > rel_patch)
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	git commit rel_patch -m "Bumped patch version to $${revno}"

minorbump:
	(minor=`cat rel_minor`; minor=`expr $${minor} + 1`; echo $${minor} > rel_minor; echo 0 > rel_patch)
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	git commit rel_minor rel_patch -m "Bumped minor version to $${revno}"

majorbump:
	(major=`cat rel_major`; major=`expr $${major} + 1`; echo $${major} > rel_major; echo 0 > rel_minor; echo 0 > rel_patch)
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	git commit rel_major rel_minor rel_patch -m "Bumped major version to $${revno}"

gitstatus:
	if git status -s | awk '{print $$1" "$$2}' | grep -v '\.\./' | grep -v Makefile | egrep "A|M|\?\?" >/dev/null ; then \
	    echo "There are untracked or uncommitted new or modified files in adhoc-server, please commit first";\
	    false ; \
	else \
	    git_version=`git rev-list --max-count=1 HEAD .`;\
	    if [ `git rev-list --max-count=1 HEAD rel_patch` =  $${git_version} ]; then \
		true; \
	    else \
		if [ `git rev-list --max-count=1 HEAD rel_minor` = $${git_version} ]; then \
			true; \
		else \
		    if [ `git rev-list --max-count=1 HEAD rel_major` = $${git_version} ]; then \
			true; \
		    else \
			echo "Release number for adhoc-server needs to be bumped"; \
			false; \
		    fi \
		fi \
	    fi \
	fi

	
