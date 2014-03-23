from rpcc import *
import socket




class DhcpdConfProtocol(Protocol):
    def fake_session(self, api_version, remote_ip, httphandler):
        api = self.server.api_handler.get_api(api_version)
        funobj = api.get_function_object("dhcp_server_fetch", httphandler)
        funobj.call_time=datetime.datetime.now()
        
        if not self.server.database:
            raise ExtInternalError("Function %s uses database, but no database is defined" % (funobj,))
        funobj.set_db_link(self.server.database.get_link())
        
        session_manager = funobj.session_manager
        session = session_manager.create_session(remote_ip)
        return session
            
    def request(self, httphandler, path, data):
        # [/dhcpd/api][/auto]
        #print "PATH=", path, " DATA=", data
        pathcomp = path.split("/")
        
        if len(pathcomp) < 1:
            return HTTPResponse("400 Bad request. path=%s"%path, ctype="text/plain", code=400)

        api_version = int(pathcomp[0])
        auto=False
        if len(pathcomp) > 1 and pathcomp[1] == 'auto':
            auto=True
        try:
            
            remote_ip = httphandler.client_address[0]
            (remote_dns, revip, ip)  = socket.gethostbyaddr(remote_ip)
            #print "Remote DNS=",remote_dns
            session = self.fake_session(api_version, remote_ip, httphandler)
            try:
                res = self.server.call_rpc(httphandler, "dhcp_server_dig", [session, {'dns': remote_dns}, {'dhcp_server':True, "dns":True, "latest_fetch":True}], api_version)
            except Exception, e:
                print "dhcp_server_fetch error", e
                raise
            if not "result" in res:
                print "dhcp_server_fetch error:", res["error"]
                return HTTPResponse("500 Internal server error.", ctype="text/plain", code=500)

            if len(res["result"])== 0:
                   return HTTPResponse("403 Forbidden. Data is only accessible for registered hosts", code=403)
            #return HTTPResponse("543 Debug stop. res=%s"%res, ctype="text/plain", code=543)
            dhcp_server_id = res["result"][0]["dhcp_server"]
            latest_fetch = res["result"][0]["latest_fetch"]
                
            res = self.server.call_rpc(httphandler, "event_get_max_app_id",[session], api_version)
            if "result" in res:
                maxid = res["result"]
            else:
                print "event_get_max_id error", res["error"]
                return HTTPResponse("500 Internal server error.", ctype="text/plain", code=500)
        
            if auto and maxid <= latest_fetch:
                return HTTPResponse(("Nothing new since last fetch at event id %d."%(latest_fetch)).encode("utf-8"), ctype="text/html", encoding="utf-8")
                
            db = self.server.database.get_link()
            q = "UPDATE dhcp_servers SET latest_fetch=:maxid WHERE id=:id"
            db.put(q, maxid=maxid, id=dhcp_server_id)
            db.commit()
            
            res = self.server.call_rpc(httphandler, "dhcpd_config", [dhcp_server_id], api_version)
            s=res["result"]
            return HTTPResponse(s.encode("utf-8"), ctype="text/html", encoding="utf-8")
        
        except Exception, e:
            print e
            raise
            return HTTPResponse("500 Internal server error.", ctype="text/plain", code=500)
