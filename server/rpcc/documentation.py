#!/usr/bin/env python
"""

Text documentation:
---
Synopsis (API v.0-3):
  person_update(session, person, updates)

Description:
  Does cool things.

Returns: 
  <null>

Parameters:
  session  <session>        Execution context   
  person   <person>         The person to update
  updates  <person-update>  Fields and updates  

Types:
  # Execution context. See session_start().
  <session> ::= String matching regexp [a-z0-9]{40}

  # ID of one person in the system.
  <person> ::= String matching regexp [a-z0-9]{2,8}

  # Update options
  <person-update> ::= Struct (optional keys in parentheses)
      (firstname) = <string>
      (lastname)  = <string>
      (account)   = <account> or <null>
      # List of the fake types this fake fakes.
      (fake)      = [<account>, ...]

  # ID of one account in the system.
  <account> ::= String matching regexp [a-z0-9]{1,9}

  <string> ::= String with any content.
---

Structured documentation:

{"function": "funname",
 "parameters": [<param>],
 "returns": <param>,
 "description": "Does cool stuff",
 "types": {"name": <type>}}

# A param is a (name, typ, desc) tuple, where <typ> is a reference to
# the function's "types" dictionary.
param ::= {
 "name": <string>,
 "type": "typename",
 "description": <string> or None,
}

# The content of the type dictionary defines what named types look like.
type ::= {
 "description": <string>,
 "base": ["string", "enum", "integer", "bool", "struct", "list", "nullable"],
 # Only for strings
 "regexp": <string> or None,
 "maxlen": <intger> or None,
 # Only for enums
 "values": [<string>, ...]
 # Only for integers
 "min": <integer> or None,
 "max": <integer> or None,
 # Only for lists and nullable
 "subtype": <typename>,
 # Only for structs
 "mandatory": [<param>, ...]
 "optional": [<param>, ...]
}

HTML documentation:

<head>
<title>Definition of (url) function (name) for API v.(version)</title>
</head>
<body>
  <h1>get_foo(foo, bar) [API version 2]</h1>
  <table>
  <tr><td>Description</td>
      <td>...</td></tr>
  <tr><td>Definition</td>
      <td>get_foo(foo, bar)</td></tr>
  </table>
</body>
"""

from exttype import *
from xmlnode import HTMLNode


class Documentation(object):
    def __init__(self, server):
        self.server = server

    def typename_as_text(self, t):
        tinst = ExtType.instance(t)
        if isinstance(tinst, ExtOrNull):
            return "%s or <null>" % (self.typename_as_text(tinst.typ),)
        elif isinstance(tinst, ExtList):
            return "[%s, ...]" % (self.typename_as_text(tinst.typ),)
        else:
            return "<%s>" % (tinst._name(),)

    def reflow_text(self, s, ind=2):
        out = []
        for phrase in s.split("\n\n"):
            out.append([" " * ind])
            for token in phrase.split():
                if len(out[-1][-1]) + len(token) > 78 - ind:
                    out[-1].append(" " * ind)
                out[-1][-1] = out[-1][-1] + " " + token
        return "\n\n".join(["\n".join(r) for r in out])

    def css_for_html(self):
        s = "table {border: solid 1px black; border-collapse: collapse} "
        s += "td {font-size: 10pt; padding: 5px 2px} "
        s += "table.typedefs td.type {background: #cac; margin-top: 20px} "
        s += "span.type_name {font-family: monospace} "
        s += "body {font-family: sans-serif; font-size: 10pt;} "
        s += "span.function_name {font-family: monospace} "
        s += "span.enum_value {background: #dbb} "
        return s
        
    def function_as_html(self, apivers, funname):
        api = self.server.api_handler.get_api(apivers)
        funcls = api.get_function(funname)

        def type_name(node, typ):
            name = ExtType.instance(typ)._name()
            s = node.span(cls="type_name")
            s.cdata("<")
            s.a(href="#" + name).cdata(name)
            s.cdata(">")

        def section(tbl, name):
            row = tbl.tr()
            row.td(cls="section_name", valign="top").cdata(name)
            return row

        html = HTMLNode("html", _space_children=True)
        head = html.head()
        head.title().cdata("Definition of %s function %s for API version %d" % (self.server.get_server_url(), funcls._name(), apivers))
        head.link(rel="stylesheet", href="/api/api.css")

        body = html.body()
        body.h1().cdata("%s() [API version %d]" % (funcls._name(), apivers))
        toptbl = body.table(cls="master")

        if funcls.desc:
            row = section(toptbl, "Description")
            row.td().cdata(funcls.desc)

        row = section(toptbl, "Definition")
        sp = row.td().span(cls="function_name")
        sp.cdata(funcls._name() + "(")
        addcomma = False
        for (name, typ, desc) in funcls.get_parameters():
            if addcomma:
                sp.cdata(", ")
            else:
                addcomma = True
            sp.span(cls="parameter_name").cdata(name)
        sp.cdata(")")

        row = section(toptbl, "Parameters")
        ptbl = row.td().new("table")
        for (name, typ, desc) in funcls.get_parameters():
            row = ptbl.tr()
            row.td().span(cls="parameter_name").cdata(name)
            type_name(row.td(), typ)
            row.td().cdata(desc or "")

        row = section(toptbl, "Returns")
        c = row.td()
        typ, desc = funcls._returns()
        type_name(c, typ)
        if desc:
            c.br()
            c.cdata(desc)
        
        row = section(toptbl, "Types")
        ttbl = row.td().table(cls="typedefs")
        for (name, typ) in funcls._subtypes_flat().items():
            typ = ExtType.instance(typ)
            c = ttbl.tr().td(colspan="4", cls="type").span(cls="type_name")
            c.a(name=typ._name())
            c.cdata("<" + typ._name() + ">")

            if typ.desc:
                r = ttbl.tr()
                r.td().cdata("Description")
                r.td(colspan=3).cdata(typ.desc)

            r = ttbl.tr()
            r.td().cdata("Base type")
            if isinstance(typ, ExtEnum):
                r.td().cdata("enumeration")
                r = ttbl.tr()
                r.td().cdata("Values")
                t = r.td(colspan="3")
                for v in typ.values:
                    t.span(cls="enum_value").cdata(v)
                    t.cdata(" ")
            elif isinstance(typ, ExtString):
                c = r.td(colspan=3)
                c.cdata("string")
                if typ.maxlen:
                    c.cdata(", of maximum length %d" % (typ.maxlen,))
                if typ.regexp:
                    c.cdata(", matching regexp ")
                    c.tt().cdata(typ.regexp)
            elif isinstance(typ, ExtInteger):
                c = r.td(colspan=3)
                c.cdata("integer")
                if typ.range:
                    c.cdata(", with values between %d and %d inclusive" % typ.range)
            elif isinstance(typ, ExtNull):
                r.td(colspan=3).cdata("null")
            elif isinstance(typ, ExtBoolean):
                r.td(colspan=3).cdata("boolean")
            elif isinstance(typ, ExtList):
                c = r.td(colspan=3)
                c.cdata("list of ")
                type_name(c, typ.typ)
            elif isinstance(typ, ExtOrNull):
                c = r.td(colspan=3)
                type_name(c, typ.typ)
                c.cdata(" or ")
                type_name(c, ExtNull)
            elif isinstance(typ, ExtStruct):
                r.td(colspan=3).cdata("struct")
                mand, opt = [], []
                for (optflag, key, typ, desc) in typ._all_items():
                    if optflag:
                        opt.append( (key, typ, desc) )
                    else:
                        mand.append( (key, typ, desc) )
                if mand:
                    r = ttbl.tr()
                    r.td(valign="top").cdata("Mandatory")
                    x = False
                    for (key, typ, desc) in sorted(mand):
                        if x:
                            r = ttbl.tr()
                            r.td().cdata("")
                        else:
                            x = True

                        r.td().tt().cdata(key)
                        type_name(r.td(), typ)
                        r.td().cdata(desc or "")
                if opt:
                    r = ttbl.tr()
                    r.td(valign="top").cdata("Optional")
                    x = False
                    for (key, typ, desc) in sorted(mand):
                        if x:
                            r = ttbl.tr()
                            r.td().cdata("")
                        else:
                            x = True

                        r.td().tt().cdata(key)
                        type_name(r.td(), typ)
                        r.td().cdata(desc or "")
                
        return html.xml()

    def function_as_struct(self, apivers, funname):
        api = self.server.api_handler.get_api(apivers)
        funcls = api.get_function(funname)

        ret = {}
        ret["function"] = funcls._name()
        if funcls.desc:
            ret["description"] = funcls.desc
        ret["parameters"] = []
        for (p, t, d) in funcls.get_parameters():
            par = {}
            par["name"] = p
            par["type_name"] = ExtType.instance(t)._name()
            if d:
                par["description"] = d
            ret["parameters"].append(par)
        ret["returns"] = {}
        ret["returns"]["type_name"] = ExtType.instance(funcls._returns()[0])._name()
        if funcls._returns()[1]:
            ret["returns"]["description"] = funcls._returns()[1]
        ret["types"] = []
        for (name, typ) in funcls._subtypes_flat().items():
            tps = {}
            ret["types"].append(tps)
            t = ExtType.instance(typ)
            tps["name"] = t._name()
            if isinstance(t, ExtEnum):
                tps["base"] = "enum"
                tps["values"] = t.values
            elif isinstance(t, ExtString):
                tps["base"] = "string"
                if t.regexp:
                    tps["regexp"] = t.regexp
                if t.maxlen:
                    tps["maxlen"] = t.maxlen
            elif isinstance(t, ExtInteger):
                tps["base"] = "integer"
                if t.range:
                    tps["min"], tps["max"] = t.range[0]
            elif isinstance(t, ExtNull):
                tps["base"] = "null"
            elif isinstance(t, ExtBoolean):
                tps["base"] = "boolean"
            elif isinstance(t, ExtOrNull):
                tps["base"] = "nullable"
                tps["subtype"] = t._name()
            elif isinstance(t, ExtList):
                tps["base"] = "list"
                tps["subtype"] = t._name()
            elif isinstance(t, ExtStruct):
                tps["base"] = "struct"
                tps["mandatory"] = []
                tps["optional"] = []
                for (opt, key, typ, desc) in t._all_items():
                    par = {"name": key,
                           "type_name": ExtType.instance(t)._name()}
                    if desc:
                        par["description"] = desc
                    if opt:
                        tps["optional"].append(par)
                    else:
                        tps["mandatory"].append(par)
        return ret

    def function_as_text(self, apivers, funname):
        api = self.server.api_handler.get_api(apivers)
        funcls = api.get_function(funname)

        v = "%d" % (funcls.from_version,)
        if funcls.to_version == 10000:
            v += "-oo"
        elif funcls.to_version != funcls.from_version:
            v += "-%d" % (funcls.to_version,)
        doc = "\n\nSynopsis (API v.%s):\n  " % (v,)
        p = ", ".join([p for (p, t, d) in funcls.get_parameters()])
        doc += funcls._name() + "(" + p + ")"

        doc += "\n\nDescription:\n" + self.reflow_text(funcls.desc)

        doc += "\n\nParameters:\n"
        pl = []
        for (p, t, d) in funcls.get_parameters():
            pl.append( ("  " + p, "  " + self.typename_as_text(t), "  " + (d or "")) )
        doc += self.text_table(pl)

        (typ, desc) = funcls._returns()
        doc += "\n\nReturns: " + self.typename_as_text(typ)
        if desc:
            doc += " - " + desc

        doc += "\n\nTypes:\n"
        types = funcls._subtypes_flat()
        for tname in sorted(types.keys()):
            typ = types[tname]
            tinst = ExtType.instance(typ)

            if tinst.desc:
                doc += "  # %s\n" % (tinst.desc,)
            doc += "  <%s> ::= " % (tinst._name(),)

            # String
            if isinstance(tinst, ExtString):
                doc += "String"
                if tinst.maxlen:
                    doc += " of max length %d" % (tinst.maxlen,)
                if tinst.regexp:
                    doc += " matching regexp '%s'" % (tinst.regexp.replace("\n", "\\n"),)
                if not tinst.maxlen and not tinst.regexp:
                    doc += " with any content"
            # Enum
            elif isinstance(tinst, ExtEnum):
                doc += "String with content being one of ["
                doc += ", ".join(tinst.values) + "]"
            elif isinstance(tinst, ExtInteger):
                doc += "Integer"
                if tinst.range:
                    doc += " between %d and %d" % tinst.range
            elif isinstance(tinst, ExtBoolean):
                doc += "Boolean"
            elif isinstance(tinst, ExtNull):
                doc += "Null"
            elif isinstance(tinst, ExtStruct):
                doc += "Struct with keys (optional in parenthesis)"
                items = sorted(tinst._all_items())
                keylen = max([len(k) + 2 for (_o, k, t, d) in items])
                for (opt, key, typ, desc) in items:
                    if desc:
                        doc += "\n      # " + desc
                    if opt:
                        doc += "\n      %-*s = %s" % (keylen, "(" + key + ")", self.typename_as_text(typ))
                    else:
                        doc += "\n      %-*s = %s" % (keylen, key, self.typename_as_text(typ))
            elif isinstance(tinst, ExtList):
                doc += "List of " + self.typename_as_text(tinst.typ)
            elif isinstance(tinst, ExtOrNull):
                doc += self.typename_as_text(tinst.typ) + " or <null>"
            doc += "\n\n"
        return doc

    def text_table(self, rows):
        cw = [0, ] * len(rows[0])
        for colidx in range(len(rows[0])):
            cw[colidx] = max([len(r[colidx]) for r in rows])

        return "\n".join(["".join(["%-*s" % (l, c) for (l, c) in zip(cw, r)]) for r in rows])