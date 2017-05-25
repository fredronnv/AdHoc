import getpass

import rpcc_client


def connect(url="https://adhoc.ita.chalmers.se:8877", user="bernerus"):
    try:
        return connect_krb5(url)
    except Exception, e:
        print e
    return do_connect(url, user=user)


def do_connect(url, user):
    global p
    print "Connecting to", url
    p = rpcc_client.RPCC(url)
    # print "Enter password for "+user
    pw = getpass.getpass()
    if not p.session_auth_login(user, pw):
            raise ValueError
    print "Connected to", url
    return p
    # print p.server_list_functions()


def connect_krb5(url="https://adhoc.ita.chalmers.se:8877"):
    global p
    p = rpcc_client.RPCC(url)
    p.session_auth_kerberos()
    return p
