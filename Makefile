TOP=`pwd`
SUBDIRS=applications/dhconf adhoc-connect adhoc-server applications/printermap
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
	
release: gitstatus install
	rm -rf ${DISTDIR}/*
	for dir in $(SUBDIRS); do \
	    TOP=${TOP} $(MAKE) -S -e -C $$dir ${MAKEFLAGS}  gitstatus release || exit 1;\
	done

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
	for dir in $(SUBDIRS); do \
	    if TOP=${TOP} $(MAKE) -s -e -C $$dir ${MAKEFLAGS}  gitstatus; \
	        then :;\
	        else  echo "Git status in $$dir must be fixed"; exit 1;\
	    fi;\
	done; \
	if git status -s | awk '{print $$1" "$$2}' | grep -v '\.\./' | grep -v Makefile | egrep "A|M|\?\?" >/dev/null ; then \
            echo "There are untracked or uncommitted new or modified files in main section, please commit first";\
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
                        echo "Release number for main section needs to be bumped"; \
                        false; \
                    fi \
                fi \
            fi \
        fi
	
