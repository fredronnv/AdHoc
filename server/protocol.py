
from response import HTTPResponse

class DhcpdConfProtocol(Protocol):
    def request(self, httphandler, path, data):
        # [/dhcpd/]servername
        print "PATH=", path, " DATA=", data
        pathcomp = path.split("/")
        
        if len(pathcomp) != 2:
            return HTTPResponse("400 Bad request.", ctype="text/plain", code=400)

        
        apivers = int(pathcomp[0])
        dhcp_server_name = pathcomp[1]
        funobj = self.server.get_function("dhcpd_config", dhcp_server_name)
        try:
            s = funobj.do()
            return HTTPResponse(s.encode("utf-8"), ctype="text/html", encoding="utf-8")
        except:
            return HTTPResponse("500 Internal server error.", ctype="text/plain", code=500)
