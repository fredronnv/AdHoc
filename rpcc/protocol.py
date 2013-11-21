
import os
import re
import sys
import time
import traceback
import mimetypes
import xmlrpclib
import json

import xml
import xml.dom
import xml.dom.minidom

from response import HTTPResponse
import exterror


class Protocol(object):
    """An object which handles communications of a certain kind.

    Incoming HTTP requests are decoded into a path, optional data and
    optional header fields, which are then sent to the Server
    instance for dispatch. The Server uses available data to choose an 
    Protocol subclass instance, and passes the request on to that 
    handler's .request() method.

    That method then decodes the request according to the rules
    defined by the (sub)protocol it implements (XMLRPC/SOAP/JSON/other),
    and uses the Server's methods to perform the requested
    action. Finally it encodes any returned data into the wire-format
    defined by the implemented (sub)protocol, passing the result back.
    """

    def __init__(self):
        pass

    def set_server(self, server):
        self.server = server

    def request(self, httphandler, path, data):
        """Handle a request according to the rules defined by the
        protocol implemented by this class.

        Return data for immediate HTTP transport back to the client. Return
        as a tuple (content-type, content-encoding, data).

        The HTTPRequestHandler object responsible for the HTTP
        interchange is available through the httphandler
        argument. That could be used to act on client IP address or
        http request headers for example.

        """

        return ('text/html', None, "<h1>Default response</h1>(invalid HTML)")


class StaticDocumentProtocol(Protocol):
    def __init__(self, docroot):
        self.docroot = docroot
        Protocol.__init__(self)

    def request(self, httphandler, path, data):
        """Returns a document from the docroot, replacing
        special tags with formatted internal information (function
        definitions for example).

        Not a fully featured Web-server, just a very, very simple way of
        getting documentation as XHTML over HTTP from the live server.

        Special tags:

        <:function:server_documentation:>
            Inserts XHTML for the complete documentation of the
            "server_documentation" function.

        """

        if not self.docroot:
            doc = '<html><head><title>XML RPC Server Error</title>'
            doc += '</head><body>'
            doc += '<h1>No doc root set.</h1>'
            doc += '</body></html>'
            return HTTPResponse(ctype='text/html', data=doc)

        if path:
            if ('..' in path or '/.' in path or 
                './' in path or path[0] == '/'):
                return HTTPResponse(ctype='text/html', data='<h1>Invalid path</h1>')
            if path[-1] == '/':
                path += 'index.html'
        else:
            path = 'index.html'

        #for suff in ['.py', '.pm', '.patch']:
        #    if path.endswith(suff):
        #        type, enc = ('text/plain', 'UTF-8')
        #        break
        #else:

        type, enc = mimetypes.guess_type(path)

        #if path.startswith("client/"):
        #    path = '../../' + path

        error404 = ('text/html', None, '<h1>Not Found</h1>')

        try:
            path = os.path.join(self.docroot, path)
            if os.path.exists(path):
                data = file(os.path.join(self.docroot, path)).read()
            else:
                type, enc, data = error404
        except:
            type, enc, data = error404

        if type == 'text/html' and not enc:
            # HTML documents can contain special <:fun:> tags which
            # are automatically expanded.
            ls = re.split('<:([^>]+):>', data)
            data = ""
            while ls:
                if len(ls) == 1:
                    data += ls[0]
                    break

                (raw, special) = ls[:2]
                ls = ls[2:]
                data += raw
                arglist = special.split(':')
                function = arglist[0]
                if function == 'function':
                    data += self.html_function_definition(arglist[1])
                if function == 'category':
                    catname = arglist[1]
                    try:
                        cat = self.server.get_category(catname)
                        flist = self.server.functions_with_category(cat)
                        data += '<div class="catlist">'
                        data += '<div class="catdesc">%s</div>' % (cat.desc,)
                        data += '<ul class="catlist">'
                        for funname in [f.rpcname for f in flist]:
                            data += '<li><a href="/functions/%s" class="funlink">%s</a></li>' % (funname, funname)
                        data += '</ul></div>'
                    except KeyError:
                        data += "INVALID CATEGORY"
                else:
                    data += "INVALID COLON FUNCTION"
            
        return HTTPResponse(ctype=type, encoding=enc, data=data)
        
    def html_function_definition(self, funname):
        try:
            funobj = self.server.get_function(funname, handler=None)
        except KeyError:
            return 'UNKNOWN FUNCTION REFERENCED'

        return funobj.html_documentation()


class FunctionDefinitionProtocol(Protocol):
    def request(self, httphandler, path, data):
        # [/api/]3/funname
        pathcomp = path.split("/")
        
        if len(pathcomp) == 1 and pathcomp[0] == "api.css":
            s = self.server.documentation.css_for_html()
            return HTTPResponse(s.encode("utf-8"), ctype="text/css", encoding="utf-8")

        if len(pathcomp) == 2:
            apivers = int(pathcomp[0])
            funname = pathcomp[1]
            s = self.server.documentation.function_as_html(apivers, funname)
            return HTTPResponse(s.encode("utf-8"), ctype="text/html", encoding="utf-8")

        print "XXX", pathcomp
        

class WSDLProtocol(Protocol):
    mscompat = False
    def request(self, httphandler, path, data):
        if not path:
            data = "<html><body><h1>Available WSDL:s</h1><ul>"
            for url in self.server.api_handler.get_all_wsdl_urls():
                data += '<li><a href="%s">%s</a></li>' % (url, url)
            data += "</ul></body></html>"
            return HTTPResponse(data, encoding="utf-8", ctype="text/html")

        try:
            data = self.server.api_handler.get_wsdl(path)
            return HTTPResponse(data, encoding='utf-8', ctype='text/xml')
        except:
            raise
            return HTTPResponse("404 Not Found.", ctype="text/plain", code=404)


class MicrosoftWorkaroundWSDLProtocol(WSDLProtocol):
    """Microsoft are a little too clever, and we have to cover for them.

    If both the request and the response to a SOAP call contain an
    element/variable/parameter with the same name, Microsofts wsdl.exe
    and svcutil.exe tools consider that variable to be an "in+out"
    variable.

    This leads to the possibility of valid WSDL:s generating code 
    that won't compile (for example if the input is a parameter called 
    "group" and the output is a list of elements called "group").

    In other cases, functions can gain extra parameters compared to
    what the WSDL says.

    Our normal WSDL is every bit standards compliant, but Microsofts
    toolchain can't always handle it anyways. To make it usable from
    .NET clients, we supply special URL:s, where both the WSDL and the
    SOAP modify the names of the input variable names, so that they
    never match the output names.
    """
    
    mscompat = True

#
# To implement Kerberos HTTP SPNEGO authentication, the XMLRPC request handler
# accepts an incoming "Authorization: Negotiate <token>" header if present. Some
# clients might need to get a 401 from the same URL to force them into sending
# this header, so a special Protocol sends such a response if no
# Authorization: Negotiate header is present and just calls the request handler
# below otherwise.
#

def od(s):
    chunks = [""]
    for char in s:
        if len(chunks[-1]) == 16:
            chunks.append("")
        chunks[-1] += char
    for chunk in chunks:
        for char in chunk:
            print "%02x" % (ord(char),),
        print "   " * (16 - len(chunk)),
        print chunk.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    print

class XMLRPCProtocol(Protocol):
    def request(self, httphandler, path, data):
        response = None
        try:
            params, function = xmlrpclib.loads(data)
            if function is None:
                raise ValueError
            #if function == "person_update":
            #    od(data)
            #    print type(params[-1]["lastname"])
            #    od(params[-1]["lastname"])
        except:
            traceback.print_exc()
            response = ({'error': exterror.ExtMalformedXMLRPCError().struct()},)

        if not response:
            mo = re.search("\?v([0-9]+)", path)
            if mo:
                api_version = int(mo.groups()[0])
            else:
                api_version = 0

            response = self.server.call_rpc(httphandler, function, params, api_version)
            response = (response,)

        try:
            retdata = xmlrpclib.dumps(response, methodresponse=1,
                                      allow_none=1, encoding='ISO-8859-1')
        except:
            sys.stderr.write("Exception caugt when seralizing response for %s#%d(%s)\n" % (function, api_version, params))
            raise

        return HTTPResponse(data=retdata, encoding='iso-8859-1',
                               ctype='application/xml+rpc')

class ApacheXMLRPCProtocol(XMLRPCProtocol):
    def request(self, httphandler, path, data):
        data = data.replace('<ex:nil', '<nil')

        resp = XMLRPCProtocol.request(self, httphandler, path, data)

        resp.set_data(resp.data.replace('<nil/>', '<ex:nil/>'))
        resp.set_data(resp.data.replace('<methodResponse>', "<methodResponse xmlns:ex='http://ws.apache.org/xmlrpc/namespaces/extensions'>"))

        return resp

class KRB5XMLRPCProtocol(XMLRPCProtocol):
    def request(self, httphandler, path, data):
        if not httphandler.headers.has_key('authorization'):
            return HTTPResponse(code=401, data="<h1>401 Authentication Required</h1>",
                                   headers=[('WWW-Authentication', 'Negotiate')],
                                   ctype="text/html")

        return XMLRPCProtocol.request(self, httphandler, path, data)

class KRB5ApacheXMLRPCProtocol(ApacheXMLRPCProtocol):
    def request(self, httphandler, path, data):
        if not httphandler.headers.has_key('authorization'):
            return HTTPResponse(code=401, data="<h1>401 Authentication Required</h1>",
                                   headers=[('WWW-Authentication', 'Negotiate')],
                                   ctype="text/html")

        return ApacheXMLRPCProtocol.request(self, httphandler, path, data)

# JSON is a QUITE much smaller encoding format with the same
# properties as XMLRPC (undeclared encoding of strings, numbers,
# structs and lists).
#
# For a typical response - say a "person_get()" - the XMLRPC encoding
# transfers about 1350 bytes. The same value encoded using JSON is
# only 340.

# However, JSON is ONLY an encoding format, and does not specify any
# convention for calling functions. We therefore define our own.

# A function call: {"function": "funname", "params": [...]}
# A succesful return: {"result": ...}
# A failed return: {"error": ...}

# As a special feature, a third key may be submitted with the JSON call:
# {"function": "funname", "params": [...], "session": "abced"}
#   is equivalent to:
# {"function": "funname", "params": ["abced", ...]}
# This eases development with PHP, where prepending a session argument
# leads to ugly code.

class JSONProtocol(Protocol):
    def request(self, httphandler, path, data):
        response = None
        try:
            call = json.loads(data, encoding="utf-8")
            function = call['function']
            params = call['params']
            if 'session' in call:
                params = [call['session']] + params
        except:
            response = {'error': exterror.ExtMalformedJSONError().struct()}

        if not response:
            mo = re.search("\?v([0-9]+)", path)
            if mo:
                api_version = int(mo.groups()[0])
            else:
                api_version = 0

            response = self.server.call_rpc(httphandler, function, tuple(params), api_version)

        try:
            retdata = json.dumps(response, separators=(',', ':'), encoding="utf-8")
        except:
            sys.stderr.write("Exception caught when encoding JSON response for %s#%d(%s)\n" % (function, api_version, params))
            raise

        return HTTPResponse(data=retdata, encoding='utf-8',
                            ctype='application/json')

            
class SOAPProtocol(Protocol):
    mscompat = False
    
    def tag(self, domelem):
        if ":" in domelem.tagName:
            return domelem.tagName.split(':')[1].lower()
        return domelem.tagName.lower()

    def cleancopy(self, elist):
        newlist = []
        for elem in elist:
            if elem.nodeType != elem.TEXT_NODE or elem.data.strip() != '':
                newlist.append(elem)
        return newlist

    def request(self, httphandler, path, data):
        namespace = "https://unknown/name/space"
        try:
            dom = xml.dom.minidom.parseString(data)
            
            top = dom.documentElement
            if self.tag(top) != 'envelope':
                raise ValueError("1")

            if top.namespaceURI != 'http://schemas.xmlsoap.org/soap/envelope/':
                raise SOAPVersionMismatchError()

            header = None
            body = None
            c = self.cleancopy(top.childNodes)

            if self.tag(c[0]) == 'header':
                header = c.pop(0)
            
            if self.tag(c[0]) == 'body':
                body = c.pop(0)
            
            if c:
                raise SOAPServerError("Too many children of envelope")

            if not body:
                raise SOAPServerError("No body")

            if header:
                for hdrelem in self.cleancopy(header.childNodes):
                    try:
                        must = hdrelem.getAttribute("mustUnderstand")
                    except:
                        must = 0

                    if must == '1' or must == 'true':
                        raise SOAPMustUnderstandError()

                    try:
                        enc = hdrelem.getAttribute("encodingStyle")
                    except:
                        enc = None
                    
                    if enc:
                        raise SOAPDataEncodingUnknownError()
                
            bodylist = self.cleancopy(body.childNodes)
            if len(bodylist) != 1:
                raise SOAPClientError("Wrong number of body children")
            
            msgelem = bodylist[0]

            # The message element just extracted determines what
            # Function to instantiate and call. Its namespace
            # determines the API version, and the tag name the
            # function.

            namespace = msgelem.namespaceURI
            elemname = msgelem.tagName

            apihdl = self.server.api_handler
            (mscompat, api) = apihdl.lookup_soap_namespace(namespace)
            funcls = api.function_for_element_name(elemname)

            #fundef = api.get_soap_fundef_for_element(elemname)
            #params = fundef.parse_dom_parameters(msgelem.childNodes, mscompat)
            #params = tuple(params)

            params = funcls.from_xml(msgelem)
            ret = self.server.call_rpc(httphandler, fun._name(), params, api.version)
            if ret.has_key('error'):
                if ret['error']['name'] == 'InternalError':
                    raise ExtSOAPServerError(ret['error'])
                else:
                    raise ExtSOAPClientError(ret['error']['name'])
            retelem = funcls.to_xml_node(retval)
            retelem.set_namespace("m", namespace)

            env = XMLNode("Envelope")
            header = env.new("Header")
            body = env.new("Body")
            env.set_namespace("env", "http://schemas.xmlsoap.org/soap/envelope/")

            body.add(retelem)
        except SOAPError, e:
            env = e.get_envelope(namespace)
        except Exception, e:
            import traceback
            traceback.print_exc()
            srverr = SOAPServerError("Internal server error, contact developer")
            env = srverr.get_envelope(namespace)

        retxml = "<?xml version='1.0' encoding='UTF-8'?>\n" + env.xml()
        
        return HTTPResponse(data=retxml, encoding="UTF-8", ctype="text/xml")

class KRB5SOAPProtocol(SOAPProtocol):
    def request(self, httphandler, path, data):
        if not httphandler.headers.has_key('authorization'):
            return HTTPResponse(code=401, data="<h1>401 Authentication Required</h1>",
                                   headers=[('WWW-Authentication', 'Negotiate')],
                                   ctype="text/html")

        path = path.replace("spnego+", "")
        return SOAPProtocol.request(self, httphandler, path, data)
