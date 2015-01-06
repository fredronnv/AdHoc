
"""Simple XML-generation."""


class _DataNode(object):
    def __init__(self, data, _space_children=False):
        self.space_children = _space_children
        self.data = data

    def xml(self, indentation=0):
        s = self.data.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if self.space_children:
            return s + "\n"
        else:
            return s


class XMLNode(object):
    @classmethod
    def escape(cls, value):
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def __init__(self, elem, *attrlist, **attrs):
        self.elem = elem
        self.attrs = attrs
        self.cdata_str = None
        self.subelems = []
        
        self.space_children = self.attrs.pop('_space_children', False)
            
        if "_other_attributes" in self.attrs:
            o = self.attrs.pop('_other_attributes')
            self.attrs.update(o)

        if "_cdata" in self.attrs:
            self.cdata_str = self.attrs.pop("_cdata")

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
        if "_space_children" not in attrs:
            attrs["_space_children"] = self.space_children
        subelem = self.__class__(elem, *attrlist, **attrs)
        self.subelems.append(subelem)
        return subelem
    
    def cdata(self, cdata):
        #if type(cdata) not in [type(''), type(u'')]:
        #    raise ValueError("Cannot set %s as cdata!" % (cdata,))
        self.subelems.append(_DataNode(cdata))

    def xml(self, indentation=0):
        if self.space_children:
            s = "\n" + "  " * indentation
        else:
            s = ""
        s += '<' + self.elem

        if "cls" in self.attrs:
            self.attrs["class"] = self.attrs.pop("cls")

        attrnames = self.attrs.keys()
        attrnames.sort()
        for special in ["type", "name"]:
            if special in attrnames:
                attrnames.remove(special)
                attrnames = [special] + attrnames

        for name in attrnames:
            value = self.attrs[name]
            if isinstance(value, int):
                value = str(value)
            value = value.replace('&', '&amp;')

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

        if self.subelems:
            subxml = [sub.xml(indentation + 1) for sub in self.subelems]
            ss = ">" + "".join(subxml)
            s += ss
            if self.space_children and len(ss) > 80:
                s += "\n" + "  " * indentation
            s += "</%s>" % (self.elem,)
        else:
            s += "/>"

        return s


class HTMLNode(XMLNode):
    tags = ["a", "abbr", "address", "area", "article", "aside", "audio",
            "b", "base", "bdi", "bdo", "blockquote", "body", "br", 
            "button", "canvas", "caption", "cite", "code", "col", "colgroup", 
            "command", "datalist", "dd", "del", "details", "dfn", "dialog",
            "div", "dl", "dt", "em", "embed", "fieldset", "figcaption", 
            "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6",
            "head", "header", "hr", "html", "i", "iframe", "img", "input",
            "ins", "kbd", "keygen", "label", "legend", "li", "link", 
            "map", "mark", "menu", "meta", "meter", "nav", "noscript", 
            "object", "ol", "optgroup", "option", "output", "p", "param",
            "pre", "progress", "q", "s", "samp", "script", "section",
            "select", "small", "source", "span", "strong", "style", "sub",
            "summary", "sup", "table", "tbody", "td", "textarea", "tfoot",
            "th", "thead", "time", "title", "tr", "track", "tt", "u", "ul",
            "var", "video", "wbr"]

    class _adder(object):
        def __init__(self, node, tag):
            self.node = node
            self.tag = tag

        def __call__(self, *args, **kwargs):
            return self.node.new(self.tag, *args, **kwargs)

    def __getattr__(self, attr):
        if attr in self.tags:
            return self._adder(self, attr)
        raise AttributeError(attr)
