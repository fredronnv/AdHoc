#!/usr/bin/env python2.6
import os
import sys

sys.path.append(os.environ.get("ADHOC_RUNTIME_HOME","/Users/bernerus/work/proj/workspace/AdHoc/client"))

import rpcc_client
import getpass
import urllib2
def connect(url="http://venus.ita.chalmers.se:8877",api=0, user="bernerus"):

    urls = [url, "http://nile.its.chalmers.se:12121/api/0"]

    for u in urls:
	n=0
	while True:
	    try:
	        p = do_connect(u, api, user)
	        if p:
		    print "Authenticated as %s to %s"%(user,u)
		    return p
		break
	    except urllib2.URLError:
		print "URLERROR"
		break
	    except Exception, e:
		print e 
		n += 1
	    if n > 2:
		p=rpcc_client.RPCC(u, api)
		print "Connected unauthenticated to %s"% u
		return p
    

def do_connect(url, api, user):
    print "Connecting to",url
    p=rpcc_client.RPCC(url, api)
    if not p.session_auth_kerberos():
        print "Enter password for "+user
        pw=getpass.getpass()
        if len(pw)==0:
	    return None
        if not p.session_auth_login(user, pw):
            raise ValueError
    return p
    #print p.server_list_functions()

def connect_krb5(url="http://localhost:12121",api=0):
    global p
    p=pdbclient.RPCC_Krb5(url, api)
    return p

if __name__ == "__main__":
    p=connect()

