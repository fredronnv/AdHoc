from rpcc import *


class DhcpdConfProtocol(Protocol):
    def request(self, httphandler, path, data):
        # [/dhcpd/]servername
        print "PATH=", path, " DATA=", data
        pathcomp = path.split("/")
        
        if len(pathcomp) != 2:
            return HTTPResponse("400 Bad request.", ctype="text/plain", code=400)

        
        api_version = int(pathcomp[0])
        dhcp_server_name = pathcomp[1]
        
        try:
            res = self.server.call_rpc(httphandler, "dhcpd_config", [dhcp_server_name], api_version)
            s=res["result"]
            return HTTPResponse(s.encode("utf-8"), ctype="text/html", encoding="utf-8")
        except:
            return HTTPResponse("500 Internal server error.", ctype="text/plain", code=500)
