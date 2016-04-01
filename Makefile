TOP=`pwd`
SUBDIRS=applications/dhconf adhoc-connect server
DISTDIR=${TOP}/dist

subdirs:
	for dir in $(SUBDIRS); do \
	    TOP=${TOP} $(MAKE) -e -C $$dir ${MAKEFLAGS} ;\
	done

clean:	
	for dir in $(SUBDIRS); do \
	    TOP=${TOP} $(MAKE) -e -C $$dir ${MAKEFLAGS}  clean;\
	done

install: clean
	for dir in $(SUBDIRS); do \
	    if TOP=${TOP} $(MAKE) -S -e -C $$dir ${MAKEFLAGS}  install;\
	        then :; \
	        else echo "Failed to build $$dir"; exit 1;\
	    fi;\
	done
	
release: svnstatus install
	rm -rf ${DISTDIR}/*
	for dir in $(SUBDIRS); do \
	    TOP=${TOP} $(MAKE) -S -e -C $$dir ${MAKEFLAGS}  svnstatus release || exit 1;\
	done

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
	for dir in $(SUBDIRS); do \
	    if TOP=${TOP} $(MAKE) -s -e -C $$dir ${MAKEFLAGS}  svnstatus; \
	        then :;\
	        else  echo "SVN status in $$dir must be fixed"; exit 1;\
	    fi;\
	done
