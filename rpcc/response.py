
class HTTPResponse(object):
    def __init__(self, data=None, ctype=None, encoding=None, code=None,
                 headers=[]):
        self.set_data(data)
        self.set_ctype(ctype)
        self.set_encoding(encoding)
        self.set_code(code)
        self.add_headers(headers)

    def set_data(self, data):
        self.data = data

    def set_ctype(self, ctype):
        self.ctype = ctype

    def set_encoding(self, cenc):
        self.encoding = cenc

    def set_code(self, code):
        self.code = code

    def add_headers(self, headlist):
        if not hasattr(self, 'headers'):
            self.headers = []
        self.headers.extend(headlist)

class HTTP404(HTTPResponse):
    def __init__(self):
        HTTPResponse.__init__(self, "404 Not Found", ctype="text/plain", encoding="UTF-8", code=404)



