
"""Simple XML-generation."""

class XMLNode(object):
    @classmethod
    def escape(cls, value):
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def __init__(self, elem, *attrlist, **attrs):
        self.elem = elem
        self.attrs = attrs
        self.cdata_str = None
        self.subelems = []
        
        if self.attrs.has_key('_space_children'):
            self.space_children = self.attrs['_space_children']
            del self.attrs['_space_children']
        else:
            self.space_children = False
            
        if self.attrs.has_key('_other_attributes'):
            o = self.attrs['_other_attributes']
            del self.attrs['_other_attributes']
            self.attrs.update(o)

        if attrlist and type(attrlist[0]) == type({}):
            self.attrs.update(attrlist[0])

    def add(self, node):
        if node is None:
            raise ValueError("None node")
        self.subelems.append(node)
        return node

    def add_attribute(self, name, value):
        self.attrs[name] = value

    def set_namespace(self, shortname, url=None):
        """Alter all non-namespace qualified tags at and below this
        node to have a namespace. Tag <foo> will be altered to
        <shortname:foo>. The url should be given at top level,
        which will output a proper xmlns:shortname attribute.
        
        Elements added later will not get any namespace automatically.
        """

        if url:
            self.add_attribute('xmlns:' + shortname, url)

        if not ':' in self.elem:
            self.elem = shortname + ':' + self.elem

        for child in self.subelems:
            child.set_namespace(shortname)

    def new(self, elem, *attrlist, **attrs):
        subelem = self.__class__(elem, *attrlist, **attrs)
        self.subelems.append(subelem)
        return subelem
    
    def cdata(self, cdata):
        if type(cdata) not in [type(''), type(u'')]:
            raise ValueError("Cannot set %s as cdata!" % (cdata,))
        self.cdata_str = cdata

    def xml(self, indentation=0):
        s = '  ' * indentation
        s += '<' + self.elem

        attrnames = self.attrs.keys()
        attrnames.sort()
        for special in ["type", "name"]:
            if special in attrnames:
                attrnames.remove(special)
                attrnames = [special] + attrnames

        for name in attrnames:
            value = self.attrs[name].replace('&', '&amp;')

            try:
                value = value.encode('utf-8')
            except UnicodeDecodeError:
                value = value.decode('iso-8859-1').encode('utf-8')
                
            if "'" in value:
                if '"' in value:
                    s += " %s='%s'" % (name, value.replace("'", '&apos;'))
                s += ' %s="%s"' % (name, value)
            else:
                s += " %s='%s'" % (name, value)

        if self.cdata_str is None and len(self.subelems) == 0:
            s += '/>\n'
        else:
            s += '>'
            if self.cdata_str:
                try:
                    s += self.cdata_str.encode('utf-8')
                except UnicodeDecodeError:
                    s += self.cdata_str.decode('iso-8859-1').encode('utf-8')
            else:
                s += '\n'
                subxml = [sub.xml(indentation+1) for sub in self.subelems]
                if self.space_children:
                    s += "\n".join(subxml)
                else:
                    s += "".join(subxml)

            if s[-1] == '\n':
                s += '  ' * indentation
            s += '</%s>\n' % (self.elem,)

        return s

