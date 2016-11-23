TOP=../..
SUBDIRS=
DISTDIR=${TOP}/dist/printermap
RELEASEDIR=${TOP}/releases
RPCC_DIR=${TOP}/RPCC/client_libs

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
	
	git_version=`git rev-list --max-count=1 HEAD`;\
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	mkdir -p ${DISTDIR} 
        mkdir -p ${DISTDIR} ${DISTDIR}/etc/ ${DISTDIR}/bin/ ;\
	cp INSTALL.txt .bashrc {DISTDIR}; \
	cp bin/run ${RPCC_DIR}/rpcc_client.py ${DISTDIR}/bin;\
	sed "s/@@ADHOC_RELEASE@@/$${revno}/" < printermap.py | \
	sed "s/@@ADHOC_GIT_VERSION@@/$${git_version}/" > ${DISTDIR}/printermap.py ;\
	(cd ${DISTDIR}; chmod +x printermap.py) ;\
	(cd ${DISTDIR}; find . -name \*.pyc -exec rm {} \;)

release: install
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	cp ${DISTDIR}/INSTALL.txt ${RELEASEDIR}/INSTALL.txt ;\
	(cd ${DISTDIR}/..; mv printermap printermap-$${revno};tar cf ${RELEASEDIR}/printermap-$${revno}.tar printermap-$${revno})
	
patch: gitstatus patchbump install

minor: gitstatus minorbump install

major: gitstatus majorbump install

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
	    echo "There are untracked or uncommitted new or modified files in dhconf, please commit first";\
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
			echo "Release number for dhconf needs to be bumped"; \
			false; \
		    fi \
		fi \
	    fi \
	fi
