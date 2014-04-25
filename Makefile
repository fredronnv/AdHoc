TOP=`pwd`
SUBDIRS=
subdirs:
	for dir in $(SUBDIRS); do \
	    TOP=${TOP} $(MAKE) -e -C $$dir ${MAKEFLAGS} ;\
	done

clean:	
	rm -rf dist/*
	for dir in $(SUBDIRS); do \
	    TOP=${TOP} $(MAKE) -e -C $$dir ${MAKEFLAGS}  clean;\
	done

install: svnstatus clean
	for dir in $(SUBDIRS); do \
	    TOP=${TOP} $(MAKE) -e -C $$dir ${MAKEFLAGS}  install;\
	done
	svn_version=`svnversion | cut -f2 -d:`;\
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	mkdir -p dist/server dist/adhoc-connect dist/dhcp2;\
	cp -r server dist;\
	cp -r adhoc-connect dist;\
	cp -r applications/dhcp2 dist;\
	cp client/rpcc_client.py dist/dhcp2;\
	(cd dist; find . -name .svn -exec rm -rf {} \;);\
	echo "global_svn_version = \"$${svn_version}\"" > dist/server/version.py;\
	echo "global_release = \"$${revno}\"" >>dist/server/version.py;\
	echo "global_svn_version = \"$${svn_version}\"" > dist/adhoc-connect/version.py;\
	echo "global_release = \"$${revno}\"" >>dist/adhoc-connect/version.py;\
	echo "RELEASE=\"$${revno}\"" >dist/dhcp2/version.sh;\
	echo "GLOBAL_SVN_VERSION=\"$${svn_version}\"" >> dist/dhcp2/version.sh
	
release: svnstatus install
	revno=`cat rel_major`.`cat rel_minor`.`cat rel_patch`;\
	(cd dist; mv server adhoc-server-$${revno}; tar cf ../releases/adhoc-server-$${revno}.tar adhoc-server-$${revno});\
	(cd dist; mv adhoc-connect adhoc-connect-$${revno};tar cf ../releases/adhoc-connect-$${revno}.tar adhoc-connect-$${revno});\
	(cd dist; mv dhcp2 dhcp2-$${revno}; tar cf ../releases/dhcp2-$${revno}.tar dhcp2-$${revno})

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
	    true; \
	fi
