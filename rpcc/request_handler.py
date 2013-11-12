
import sys
import time
import socket
import datetime
import traceback
import BaseHTTPServer

from response import HTTPResponse

class RawRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """Raw equest handler. Dispatches to RPCServer, handles exceptions.

    If you do want logging, override the log_request(), log_error() and
    log_message() methods in a subclass, and register it with the server
    by subclassing RPCServer.
    """

    wbufsize = 8192
    
    def setup(self):
        self.connection = self.request
        self.rfile = socket._fileobject(self.request, "rb", self.rbufsize)
        self.wfile = socket._fileobject(self.request, "wb", self.wbufsize)

    def finish(self):
        try:
            BaseHTTPServer.BaseHTTPRequestHandler.finish(self)
        except socket.error, e:
            sys.stderr.write(self.time() + " Error flushing output to %s: %s\n", self.client_address, e)
            if hasattr(self, "last_data"):
                sys.stderr.write(self.time() + " Last input: " + self.last_data)

    def time(self):
        return datetime.datetime.now().isoformat()

    def do_GET(self):
        """Receive a HTTP(S) GET request, passing it to the RPCServer
        for dispatch. The returned RPCHTTPResponse object is passed to
        send_response() for finalization."""

        try:
            path = self.path[1:]
            resp = self.server.dispatch(self, path, data=None)
            self.handle_response(resp)
        except:
            sys.stderr.write("Uncaught exception in do_GET().\n")
            traceback.print_exc()
            self.send_response(500)
            self.end_headers()

    def do_POST(self):
        """Receive a HTTP(S) POST request, passing it to the RPCServer
        for dispatch. The returned RPCHTTPResponse object is passed to
        send_response() for finalization."""

        try:
            path = self.path[1:]
            if False and "expect" in self.headers:
                if "100-continue" in self.headers['expect'].lower():
                    # Force a 100 Continue down the write pipe.
                    self.wfile.write("HTTP/1.1 100 Continue\r\n\r\n")
                    self.wfile.flush()

            data = self.rfile.read(int(self.headers["content-length"]))
            self.last_data = data
            resp = self.server.dispatch(self, path, data)
            self.handle_response(resp)
        except:
            sys.stderr.write("Uncaught exception in do_POST().\n")
            traceback.print_exc()
            self.send_response(500)
            self.end_headers()

    def handle_response(self, resp):
        """Translate a RPCHTTPResponse object into an actual HTTP
        response."""

        if isinstance(resp, str):
            resp = RPCHTTPResponse(resp, "text/plain")
        
        if resp.code is None:
            self.send_response(200)
        else:
            self.send_response(resp.code)
            
        if resp.ctype is not None:
            self.send_header("Content-type", resp.ctype)
        else:
            self.send_header("Content-type", "text/plain")

        if resp.encoding:
            self.send_header("Content-encoding", resp.encoding)

        if resp.data:
            self.send_header("Content-length", str(len(resp.data)))

        if resp.headers:
            for (name, value) in resp.headers:
                self.send_header(name, value)
        self.end_headers()

        self.wfile.write(resp.data)
        sys.stdout.flush()
        if False:
            print type(resp.data)
            l = 0
            for c in resp.data:
                if ord(c) < 32:
                    print " ",
                else:
                    print c,
                print hex(ord(c))[-2:],
                l += 1
                if (l % 16) == 0:
                    print
            print

        # shut down the connection
        self.wfile.flush()

        if self.server.ssl_enabled:
            self.connection.shutdown()
        
    # BaseHTTPServer logging override.
    def log_message(self, *args):
        pass

    def log_request(self, *args):
        pass

    def log_error(self, *args):
        pass
