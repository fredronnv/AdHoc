#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

import re
import traceback
import datetime

from exterror import *
from error import IntAPIValidationError
from xmlnode import XMLNode

"""
ExtType subclasses - the base classes for externally visible data types.

Incoming calls are first converted by a Protocol to a common type 
space - the type space that XMLRPC and JSON handle (represented as native 
Python strings, ints, floats, dicts, bools and Nones). 

ExtTypes are used to convert between this type space and the server 
application's type space. The values coming from the Protocol are
fed into .check() for type and validity checks, then to 
.convert()/.lookup() to be converted to application type space.

On output, a native value is sent to .output() to be converted back
to the Protocol common type space.

If the transport lacks native native data types, as SOAP does, ExtType 
also needs to assist. Each ExtType defines an XML format, which it can
represent as XSD (.xsd() method). It can also take a DOM element to
convert to the Protocol-common type space (.from_xml() method), and 
convert values from that type-space to XML.

As long as you compose your external interfaces from subtypes of the 
ExtType bases, you needn't worry about more than implementing .lookup() 
and .output().
"""


# .parse() now calls three methods:
#
# .check()
#    Checks integer ranges, string regexps etcetera. For lists it
#    recursively checks all elements. For structs it checks keys, and
#    recursively checks values.
#
# .convert()
#    For simple values this returns the raw value. For lists and
#    structs, sub-values are recursively parsed and looked up.
#
# .lookup()
#    The final value from .convert() can be converted to an internal
#    object here (integers converted to some object type with an
#    integer-ID etc.)
class ExtType(object):
    """Base class for all types used in RPCTypedFunctions."""

    # Note! The "name" attribute is NOT inherited wrt public
    #   naming. It is more important that auto-generation of public
    #   names work than that they are inherited.
    name = None
    desc = None

    # First/last API version where this ExtType is valid. If left as
    # None, simple types will count as valid from 0..10000. Complex
    # types will count as valid for the most limited overlap between
    # subtypes' versions. Complex types may set
    # from_version/to_version, but only to limit validity further.
    from_version = None
    to_version = None

    # If automatic name generation is requested (name == None), this
    # prefix/suffix will be removed from the class name if they are
    # present.
    prefix = "Ext"
    suffix = None

    # CLASS-level caching for the class-method .instance().
    _instance_cache = dict()
    _list_cache = dict()
    _ornull_cache = dict()

    def parse(self, function, rawval):
        self.check(function, rawval)
        converted = self.convert(function, rawval)
        return self.lookup(function, converted)

    def check(self, function, rawval):
        """Perform consistency checks on the incoming intermediate value
           (after protocol decoding)."""

        raise NotImplementedError()

    def convert(self, function, rawval):
        """Convert the intermediate value to a class-local form, performing
        lookup on sub-values (but not on the value itself)."""

        return rawval

    def lookup(self, function, cval):
        """Lookup the class-local form, and returning the final
        system-internal form."""

        return cval

    def output(self, function, value):
        try:
            self.check(function, value)
        except ExtError as e:
            raise ExtOutputError(self, ".check() returned error: %s %s %s" % (e.__class__, e.desc, e.value))
        return value

    def _name(self):
        if "name" in self.__dict__:
            return self.name

        if "name" in self.__class__.__dict__:
            return self.__class__.name

        name = self.__class__.__name__
        if self.prefix and name.startswith(self.prefix):
            name = name[len(self.prefix):]
        if self.suffix and name.endswith(self.suffix):
            name = name[:len(self.suffix)]
        return name

    def _subtypes(self):
        return []

    def _api_versions(self):
        return (self.from_version or 0, self.to_version or 10000)

    @classmethod
    def instance(cls, typ):
        """Return a unified instance of the ExtType class or object 'typ'.

        If 'typ' is a class an instance of 'typ' is returned - the same
        instance if this method is called several times.

        If 'typ' is an ExtList or ExtOrNull instance, the wrapped type
        is looked up, and the _same_ ExtList or ExtOrNull instance (which
        may be another one) is always returned. One list-of-foo and another
        list-of-foo are always the same thing.

        Otherwise if 'typ' is an ExtType instance, it is just returned
        as-is.
        """

        # Both struct keys and return types may be tuples (typ, desc),
        # simplify other code by unpacking here.
        if isinstance(typ, tuple):
            typ = typ[0]

        # Two different ExtList or ExtOrNull instances covering the
        # same underlying type should return the same instance.
        if isinstance(typ, ExtList):
            if typ.typ not in cls._list_cache:
                cls._list_cache[typ.typ] = typ
            return cls._list_cache[typ.typ]

        if isinstance(typ, ExtOrNull):
            if typ.typ not in cls._ornull_cache:
                cls._ornull_cache[typ.typ] = typ
            return cls._ornull_cache[typ.typ]

        if isinstance(typ, ExtType):
            return typ
        elif (type(typ) == type(type) or type(typ) == _StructMetaClass) and issubclass(typ, ExtType):
            if typ not in cls._instance_cache:
                cls._instance_cache[typ] = typ()
            return cls._instance_cache[typ]
        else:
            raise TypeError("Not an ExtType subclass or object: %s" % (typ,))

    # SOAP helpers
    @classmethod
    def get_element_string(cls, elem):
        stringdata = ''
        for child in elem.childNodes:
            if child.nodeType == child.COMMENT_NODE:
                continue
            if child.nodeType not in [child.TEXT_NODE, child.CDATA_SECTION_NODE]:
                raise ExtSOAPNonTextNodeError(elem)
            stringdata += child.data
        return stringdata

    @classmethod
    def capsify(cls, name):
        # The name is split into parts:
        #    * '-' or '_' marks an explicit split between two letters.
        #    * A capital letter following a non-capital marks a break
        #      between the letters.
        #    * Two capital letters followed by a non-capital marks a
        #      break between the two capital letters.
        #
        # The return is all parts joined, studly-capsed.

        if name == '_':
            return "X"

        # Split into parts
        parts = [[]]
        namelen = len(name)
        for idx in range(0, namelen):
            # '_', '-' and '.' are explicit split points.
            if name[idx] in '_-.':
                parts.append([])
                continue

            if idx < namelen - 2:
                if name[idx].isupper() and name[idx + 1].isupper() \
                       and name[idx + 2].islower():
                    parts[-1].append(name[idx].lower())
                    parts.append([])
                    continue

            if idx < namelen - 1:
                if name[idx].islower() and name[idx + 1].isupper():
                    parts[-1].append(name[idx])
                    parts.append([])
                    continue

            parts[-1].append(name[idx].lower())

        # Return studly-capsed join of the parts.
        conv = ''.join(parts[0])
        for part in parts[1:]:
            conv += part[0].upper() + ''.join(part[1:])

        return conv

    @classmethod
    def child_elements(cls, elem):
        children = []
        for child in elem.childNodes:
            if child.nodeType == child.COMMENT_NODE:
                continue

            if child.nodeType == child.TEXT_NODE and child.data.strip() == "":
                continue

            if child.nodeType != child.ELEMENT_NODE:
                raise ExtSOAPUnexpectedNodeTypeError(child, "Expected an element.")
            children.append(child)
        return children

    def xsd_name(self):
        return self.capsify(self._name()) + "Type"

    def xsd_simple_type(self):
        node = XMLNode('simpleType', name=self.xsd_name())
        if self.desc:
            node.new('annotation').new('documentation').cdata(XMLNode.escape(self.desc))
        return node

    def xsd_complex_type(self):
        node = XMLNode('complexType', name=self.xsd_name())
        if self.desc:
            node.new('annotation').new('documentation').cdata(XMLNode.escape(self.desc))
        return node

    @classmethod
    def _namevers(cls):
        if cls.to_version == 1000000:
            tovers = 'oo'
        else:
            tovers = '%d' % (cls.to_version,)
        return "%s (%s@%d-%s)" % (cls.__name__, cls.name,
                                  cls.from_version, tovers)

    @classmethod
    def get_public_name(cls):
        return cls.name

    @classmethod
    def verify_api_version(cls, minv, maxv, typenames):
        """Verify that this type is valid in API versions minv through maxv.
        Also verify that no other type uses the same public name
        for the API versions where this type is valid.
        """
        
        if cls.from_version > minv or cls.to_version < maxv:
            raise ValueError(cls._namevers() + " API version range too narrow")

        if not cls.name:
            # Invisible type class, no API version is relevant
            return
            
        if cls.name not in typenames:
            typenames[cls.name] = [cls]
            return

        if cls in typenames[cls.name]:
            return
        
        mymin, mymax = cls.from_version, cls.to_version
        for othercls in typenames[cls.name]:
            hermin, hermax = othercls.from_version, othercls.to_version
            if hermax < mymin or hermin > mymax:
                continue
            raise ValueError("API competition between %s and %s" % (cls._namevers(), othercls._namevers()))

        typenames[cls.name].append(cls)

        if hasattr(cls, "verify_subtypes_api_version"):
            cls.verify_subtypes_api_version(minv, maxv, typenames)


###
# String
#
# Internal format: unicode
# SOAP: CDATA or text
# XSD: <simpleType name='self.xsd_name()'>
#         <annotation>...</annotation>
#         <restriction base='string'>
#            <pattern value='self.regexp'/>
#            <maxLength value='str(self.maxlen)'/>
#         </restriction>
#      </simpleType>
###
class ExtString(ExtType):
    name = "string"
    #desc = "A string."

    regexp = None
    regexp_flags = 0
    maxlen = None

    # If only_iso_chars is True, then incoming unicode characters must
    # be encodable as iso-8895-15 in order to be accepted (but they
    # are NOT stored as such).
    only_iso_chars = False

    def _regexp(self):
        if self.regexp:
            rexp = self.regexp
            if rexp[0] != '^':
                rexp = '^' + rexp
            if rexp[-1] != '$':
                rexp = rexp + '$'
            return rexp
        return None

    def check(self, function, rawval):
        #import codecs
        
        if not isinstance(rawval, unicode):
            if isinstance(rawval, str):
                try:
                    rawval = rawval.decode("ascii")
                except:
                    traceback.print_exc()
                    raise ExtInternalError(desc="On input (or output) ExtString returned a non-ascii str instance instead of unicode")
            else:
                raise ExtExpectedStringError(value=rawval)

        # A simple hack to avoid non-iso-8859-1-encodable characters, 
        # if the service implementor so wishes.
        if self.only_iso_chars:
            try:
                dummy = rawval.encode("iso-8859-1")
            except:
                raise ExtUnhandledCharactersError(value=rawval)

            rawval = isostring

        if self.maxlen is not None and len(rawval) > self.maxlen:
            raise ExtStringTooLongError(self.maxlen, value=rawval)
        
        if self._regexp():
            mo = re.match(self._regexp(), rawval, self.regexp_flags)
            if not mo:
                raise ExtRegexpMismatchError(self._regexp(), value=rawval)

    # SOAP 
    def xsd(self):
        xsd = self.xsd_simple_type()
        res = xsd.new('restriction', base='string')
        if self.regexp is not None:
            res.new('pattern', value=self._regexp())
        if self.maxlen is not None:
            res.new('maxLength', value=str(self.maxlen))
        return xsd

    def from_xml(self, element):
        return self.get_element_string(element)

    def to_xml(self, element, value):
        element.cdata(value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


###
# Enumeration
#
# Internal format: unicode
# SOAP: CDATA or text
# XSD: <simpleType name='self.xsd_name()'>
#         <annotation>...</annotation>
#         <restriction base='string'>
#             <enumeration value='val1'/>
#             <enumeration value='val2'/>
#         </restriction>
#      </simpleType>
###
class ExtEnum(ExtString):
    values = []
    name = "enum"
    #desc = "A string with a number of valid values"

    # SOAP
    def xsd(self):
        xsd = self.xsd_simple_type()
        res = xsd.new('restriction', base='string')
        for v in self.values:
            res.new('enumeration', value=v)
        return xsd

    def check(self, function, rawval):
        if rawval not in self.values:
            raise ExtStringNotInEnumError(self.values, value=rawval)


class ExtDateTime(ExtString):
    name = "datetime"
    desc = 'A date and time in YYYY-MM-DDTHH:MM:SS format, e.g. 2007-04-14T13:54:22'

    def lookup(self, fun, cval):
        ymd, hms = cval.split("T")
        y, mo, d = [int(p) for p in ymd.split("-")]
        h, mi, s = [int(p) for p in hms.split(":")]
        return datetime.datetime(y, mo, d, h, mi, s)

    def output(self, fun, val):
        return val.isoformat()[:19]


###
# Integer
#
# Internal format: int
# SOAP: CDATA or text containing integer
# XSD: <simpleType name='self.xsd_name()'>
#         <annotation>...</annotation>
#         <restriction base='integer'>
#      </simpleType>
###
class ExtInteger(ExtType):
    range = None
    name = 'integer'
    #desc = "Signed Integer"

    def check(self, function, rawval):
        if not isinstance(rawval, int):
            raise ExtExpectedIntegerError(value=rawval)

        if self.range:
            if rawval < self.range[0] or rawval > self.range[1]:
                raise ExtIntegerOutOfRangeError(self.range, value=rawval)

    # SOAP
    def xsd(self):
        xsd = self.xsd_simple_type()
        res = xsd.new('restriction', base='integer')
        if self.range:
            res.new('minInclusive', value=str(self.range[0]))
            res.new('maxInclusive', value=str(self.range[1]))
        return xsd

    def from_xml(self, element):
        try:
            return int(self.get_element_string(element))
        except ValueError:
            raise ExtSOAPMalformedTextNodeError(element, "Expected something parsable as an integer.")

    def to_xml(self, element, value):
        element.cdata('%d' % (value,))


###
# Boolean
#
# Internal format: bool
# SOAP: CDATA or text containing 'true', '1', 'false' or '0'
# XSD: <simpleType name='self.xsd_name()'>
#         <annotation>...</annotation>
#         <restriction base='boolean'>
#      </simpleType>
###
class ExtBoolean(ExtType):
    name = 'boolean'
    #desc = "True or False"
    
    def check(self, function, rawval):
        """ The checking for Booleans is made complicated by the fact that MySQL does not have a  boolean type.
            instead, booleans are implemented using tinyint(1) which is returned as an integer, so
            strictly checking the type vill fail."""
        if isinstance(rawval, bool):
            return
        if isinstance(rawval, int) and rawval in [0, 1]:
            return  
        raise ExtExpectedBooleanError(value=rawval)

    # SOAP
    def xsd(self):
        xsd = self.xsd_simple_type()
        xsd.new('restriction', base='boolean')
        return xsd

    def from_xml(self, element):
        raw = self.get_element_string(element)
        if raw in ['true', '1']:
            return True
        if raw in ['false', '0']:
            return False
        raise ExtSOAPMalformedTextNodeError(element, "Expected 'true' or 'false'")

    def to_xml(self, element, value):
        if value:
            element.cdata("true")
        else:
            element.cdata("false")


class ExtNull(ExtType):
    name = 'null'
    #desc = 'Null type'
    
    def check(self, function, rawval):
        if not rawval is None:
            raise ExtExpectedNullError(value=rawval)
        return rawval

    def xsd(self):
        node = self.xsd_complex_type()
        node.new("sequence").new("element", name="null", min_occurs=1, max_occurs=1)
        return node

    def from_xml(self, elem):
        try:
            (child,) = self.child_elements(elem)
        except:
            raise ExtExpectedNullError("Expected exactly one element - <null>")

        if child.tagName.split(":")[-1] != "null":
            raise ExtExpectedNullError("Element %s found instead" % (child.tagName))

        return None

    def to_xml(self, element, value):
        if value is not None:
            raise ExtInternalError("Expected None, got %s instead" % (value,))
        element.new("null")


class _StructMetaClass(type):
    """By having ExtStructType be a class of this meta-class, a
    class-attribute "optional" or "mandatory" is created upon first
    access in a ExtStructType subclass, if one does not exist.
    """    
    
    def __getattr__(cls, attr): 
        if attr == 'mandatory':
            cls.mandatory = {}
            return cls.mandatory
        elif attr == 'optional':
            cls.optional = {}
            return cls.optional
        else:
            return type.__getattr__(cls, attr)
  
        
###
# Struct
#
# Internal format: dict()
# SOAP: <...> (named by context)
#         <mandatoryKey> (content defined by subtype) </mandatoryKey>
#         <optionals>
#            <optionalKey> (content defined by subtype> </optionalKey>
#         </optionals>
#      <...>
# XSD: <complexType>
#         <sequence>
#            <element name="mandatoryKey" type="(subtype xsd name)">
#                <annotation>...</annotation>
#            </element>
#            <element name="optionals">
#               <complexType>
#                  <sequence>
#                     <element name="optionalKey" type="(subtype xsd name)"
#                              minOccurs=0 maxOccurs=1/>
#                  </sequence>
#               </complexType>
#            </element>
#         </sequence>
#      <complexType>
###
class ExtStruct(ExtType):
    __metaclass__ = _StructMetaClass
    #mandatory = {}
    #optional = {}
    
    def __init__(self, mandatory={}, optional={}):
        if mandatory:
            self.mandatory = mandatory
        if optional:
            self.optional = optional

    def __getattr__(self, name):
        if name == 'mandatory':
            self.mandatory = {}
            return self.mandatory
        elif name == 'optional':
            self.optional = {}
            return self.optional
        else:
            raise AttributeError(name)

    def _subtypes(self):
        return [(k, t) for (_o, k, t, _c) in self._all_items()]

    def _all_items(self):
        """List of (optional, key, type, comment)."""
        ret = []
        for (k, v) in self.mandatory.items():
            if isinstance(v, tuple):
                ret.append( (False, k, v[0], v[1]) )
            else:
                ret.append( (False, k, v, None) )
        for (k, v) in self.optional.items():
            if isinstance(v, tuple):
                ret.append( (True, k, v[0], v[1]) )
            else:
                ret.append( (True, k, v, None) )
        return ret

    def _api_versions(self):
        return (self.from_version or 0, self.to_version or 10000)
    
        minv, maxv = (0, 10000)
        for (dummy, subt) in self._subtypes():
            submin, submax = ExtType.instance(subt)._api_versions()
            minv = max(minv, submin)
            maxv = min(maxv, submax)
            if minv > maxv:
                raise IntAPIValidationError("Type %s contains subtypes whose validity do not overlap - detected when reading validity of %s" % (self, subt))

        if self.from_version is not None:
            if self.from_version >= minv:
                minv = self.from_version
            else:
                raise IntAPIValidationError("Type %s sets .from_version to be lower than the highest of its subtypes' .from_version" % (self,))

        if self.to_version is not None:
            if self.to_version <= maxv:
                maxv = self.to_version
            else:
                raise IntAPIValidationError("Type %s sets .to_version to be higher than the lowest of its subtypes' .to_version" % (self,))
        
        return (minv, maxv)

    def check(self, function, rawval):
        if not isinstance(rawval, dict):
            raise ExtExpectedStructError(value=rawval)
        
        for key in self.mandatory:
            if key not in rawval:
                raise ExtIncompleteStructError(key, value=rawval)

        for key in rawval:
            if key not in self.mandatory and key not in self.optional:
                print '"' + key + '"'
                print self.__class__.__name__
                print "mandatory:", self.mandatory.keys()
                print "optional:", self.optional.keys()
                raise ExtUnknownStructKeyError(value=key)

        for (key, val) in rawval.items():
            typ = self.mandatory.get(key, None) or self.optional[key]
            try:
                ExtType.instance(typ).check(function, val)
            except ExtError as e:
                e.add_traceback(key)
                raise

    def convert(self, function, rawval):
        converted = {}
        for (key, val) in rawval.items():
            typ = self.mandatory.get(key, None) or self.optional[key]
            typ = ExtType.instance(typ)
            try:
                tmp = typ.convert(function, val)
                converted[key] = typ.lookup(function, tmp)
            except ExtError as e:
                e.add_traceback(key)
                raise
        return converted

    def output(self, function, value):
        converted = {}
        inval = value.copy()
        for (key, typ) in self.mandatory.items():
            typ = ExtType.instance(typ)

            try:
                subval = inval.pop(key)
            except KeyError:
                raise ExtOutputError(self, "Mandatory key '%s' missing." % (key,))

            try:
                converted[key] = typ.output(function, subval)
            except ExtOutputError as e:
                e.add_trace(self, "While converting key '%s'" % (key,))
                raise

        for (key, subval) in inval.items():
            try:
                typ = self.optional[key]
            except KeyError:
                raise ExtOutputError(self, "Key '%s' is present but not defined." % (key,))

            typ = ExtType.instance(typ)
            try:
                converted[key] = typ.output(function, subval)
            except ExtOutputError as e:
                e.add_trace(self, "While converting key '%s'" % (key,))
                raise

        return converted
            
    @classmethod
    def verify_subtypes_api_version(cls, minv, maxv, typenames):
        for (key, spec) in cls.mandatory.items() + cls.optional.items():
            if isinstance(spec, tuple):
                subtype = spec[0]
            else:
                subtype = spec

            try:
                subtype.verify_api_version(minv, maxv, typenames)
            except ValueError, e:
                raise ValueError("%s for key %s of %s" % (e.args[0], key,
                                                          cls._namevers()))

    # SOAP
    def xsd(self):
        base = self.xsd_complex_type()
        seq = base.new('sequence')

        for (key, sub) in sorted(self.mandatory.items()):
            if isinstance(sub, tuple):
                typ, desc = ExtType.instance(sub[0]), sub[1]
            else:
                typ, desc = ExtType.instance(sub), None

            x = seq.new("element", name=key, type="myxsd:" + typ.xsd_name())
            if desc:
                x.new('annotation').new('documentation').cdata(XMLNode.escape(desc))

        opt = seq.new('element', name='optionals')
        optseq = opt.new('complexType').new('sequence')
        for (key, sub) in sorted(self.optional.items()):
            if isinstance(sub, tuple):
                typ, desc = ExtType.instance(sub[0]), sub[1]
            else:
                typ, desc = ExtType.instance(sub), None

            elemname = self.capsify(key)
            x = optseq.new("element", name=elemname, 
                           type="myxsd:" + typ.xsd_name(),
                           maxOccurs="1", minOccurs="0")
            if desc:
                x.new('annotation').new('documentation').cdata(XMLNode.escape(desc))

        return base

    def from_xml(self, elem):
        ret = {}

        mand = {}
        for (key, typ) in self.mandatory.items():
            mand[self.capsify(key)] = (key, ExtType.instance(typ))

        optelem = None
        for child in self.child_elements(elem):
            elemname = child.tagName.split(":")[-1]
            
            if elemname == "optionals":
                optelem = child
                continue

            if elemname not in mand:
                raise ExtSOAPUnexpectedElementError(child, "Expected a mandatory struct key.")

            key, typ = mand[elemname]
            ret[key] = typ.from_xml(child)

        if not optelem:
            return ret

        opt = {}
        for (key, typ) in self.optional.items():
            opt[self.capsify(key)] = (key, ExtType.instance(typ))

        for child in self.child_elements(optelem):
            elemname = child.tagName.split(":")[-1]
            if key not in opt:
                    raise ExtSOAPUnexpectedElementError(child, "Unknown struct key")
            key, typ = opt[child.tagName.split(":")[-1]]
            ret[key] = typ.from_xml(child)

        return ret

    def to_xml(self, elem, value):
        def out(elem, order, defs):
            for (key, value) in order:
                typ = ExtType.instance(defs[key])
                sub = elem.new(self.capsify(key))
                typ.to_xml(sub, value)
                
        mand = []
        opt = []
        for (key, subval) in value.items():
            if key in self.mandatory:
                mand.append((key, subval))
            elif key in self.optional:
                opt.append((key, subval))
            else:
                raise ExtInternalError()

        out(elem, sorted(mand), self.mandatory)
        if opt:
            optelem = elem.new("optionals")
            out(optelem, sorted(opt), self.optional)


###
# OrNull
#
# Internal format: None or subtype
# SOAP: <notSet/>
#       <set>(subtype encoded)</set>
# XSD: <complexType name='self.xsd_name()'>
#         <annotation>...</annotation>
#         <choice>
#            <element name="notSet" type="myxsd:nullType"/>
#            <element name="set" type="subtype.xsd_name()"/>
#         </choice>
#      </simpleType>
###
class ExtOrNull(ExtType):
    typ = None

    def __init__(self, typ=None):
        if typ is not None:
            if self.typ is not None:
                raise TypeError("When an ExtOrNull subclass has its .typ set, you cannot override it on instantiation. You use an ExtOrNull subclass just like an ExtString or ExtInteger subclass.")
            self.typ = typ
        # Use the original object's class name as prefix for the "|null" if present, Otherwise name clashes will occur when typ
        # is set explicitly and not via this constructor.
        if self.name:
            self.name = self.name + '|null'
        else:
            self.name = ExtType.instance(self.typ)._name() + '|null'

            
        
    def _subtypes(self):
        return [(None, self.typ)]

    def _api_versions(self):
        minv, maxv = ExtType.instance(self.typ)._api_versions()
        if self.from_version is not None:
            if self.from_version < minv:
                raise IntAPIValidationError("%s has a .from_version which is lower than its subtype's." % (self,))
            minv = self.from_version
        if self.to_version is not None:
            if self.to_version > maxv:
                raise IntAPIValidationError("%s has a .to_version which is higher than its subtype's." % (self,))
            maxv = self.to_version
        return (minv, maxv)

    def check(self, function, rawval):
        if rawval is not None:
            ExtType.instance(self.typ).check(function, rawval)

    def convert(self, function, rawval):
        if rawval is None:
            return None

        # The expected semantic is to get None or a looked-up
        # object. There will be no need to define a specific lookup()
        # which handles a conversion of this "None or Foo" into yet
        # another object.

        typ = ExtType.instance(self.typ)
        converted = typ.convert(function, rawval)
        return typ.lookup(function, converted)

    def output(self, function, value):
        try:
            if value is None:
                return None
            return ExtType.instance(self.typ).output(function, value)
        except ExtOutputError as e:
            e.add_trace(self, "The non-null alternative")
            raise

    # SOAP
    def xsd(self):
        xsd = self.xsd_complex_type()
        choice = xsd.new('complexType').new('choice')
        choice.new('element', name='notSet', type='myxsd:nullType')
        typ = ExtType.instance(self.typ)
        choice.new('element', name='set', type='myxsd:' + typ.xsd_name())
        return xsd

    def from_xml(self, elem):
        children = self.child_elements(elem)
        try:
            (child,) = children
        except:
            raise ExtSOAPUnexpectedElementError(elem, "Only one child element expected.")

        tag = child.tagName.split(":")[-1]
        if tag == "notSet":
            return None
        elif tag == "set":
            return ExtType.instance(self.typ).from_xml(child)
        else:
            raise ExtSOAPUnexpectedElementError(elem, "Only <set> or <notSet> expected.")


class ExtList(ExtType):
    typ = None
    
    def __init__(self, typ=None):            
        if typ:
            self.typ = typ

        if self.typ:
            self.name = typ.name + '-list'
        else:
            self.name = None

    def _name(self):
        return ExtList.instance(self.typ)._name() + "-list"

    def check(self, function, rawval):
        if not isinstance(rawval, list) and not isinstance(rawval, tuple):
            raise ExtExpectedListError(value=rawval)

        typ = ExtType.instance(self.typ)
        for subval in rawval:
            typ.check(function, subval)

    def convert(self, function, rawval):
        converted = []

        typ = ExtType.instance(self.typ)
        for subval in rawval:
            tmp = typ.convert(function, subval)
            converted.append(typ.lookup(function, tmp))

        return converted

    def output(self, function, value):
        out = []
        typ = ExtType.instance(self.typ)
        if not isinstance(value, tuple) and not isinstance(value, list):
            raise ExtOutputError("Expected sequence, got %s" % (value,))
        for subval, subidx in zip(value, range(len(value))):
            try:
                out.append(typ.output(function, subval))
            except ExtOutputError as e:
                e.add_trace(self, "List element at index %d" % (subidx,))
                raise
            
        return out
            
    @classmethod
    def verify_subtypes_api_version(cls, minv, maxv, typenames):
        try:
            cls.typ.verify_api_version(cls, minv, maxv, typenames)
        except ValueError, e:
            raise ValueError("%s for item type of %s" % (e.args[0], cls._namevers()))
            
    def _subtypes(self):
        return [(None, self.typ)]

    def _api_versions(self):
        minv, maxv = ExtType.instance(self.typ)._api_versions()
        if self.from_version is not None:
            if self.from_version < minv:
                raise IntAPIValidationError("%s has a .from_version which is lower than its subtype's." % (self,))
            minv = self.from_version
        if self.to_version is not None:
            if self.to_version > maxv:
                raise IntAPIValidationError("%s has a .to_version which is higher than its subtype's." % (self,))
            maxv = self.to_version
        return (minv, maxv)

    # SOAP
    def item_tag(self):
        return self.xsd_name()[:-4] + "Item"

    def xsd_name(self):
        return ExtType.instance(self.typ).xsd_name()[:-4] + "List"

    def xsd(self):
        xsd = self.xsd_complex_type()
        typ = ExtType.instance(self.typ)

        seq = xsd.new('sequence')
        seq.new('element', name=self.item_tag(),
                type="myxsd:" + typ.xsd_name(),
                minOccurs='0', maxOccurs='unbounded')
        return xsd

    def from_xml(self, elem):
        ret = []
        typ = ExtType.instance(self.typ)
        tag = self.item_tag()

        for child in self.child_elements(elem):
            if child.tagName.split(":")[-1] != tag:
                raise ExtSOAPUnexpectedElementError(child, "Expected <%s>." % (elem,))

            ret.append(typ.from_xml(child))
        return ret

    def to_xml(self, element, value):
        typ = ExtType.instance(self.typ)
        for subval in value:
            child = element.new(self.item_tag())
            typ.to_xml(child, subval)


if __name__ == '__main__':
    class ExtName03(ExtString):
        to_version = 3

    class ExtName25(ExtString):
        from_version = 2
        to_version = 5

    class ExtName48(ExtString):
        from_version = 4
        to_version = 8

    class ExtCombo(ExtStruct):
        mandatory = {
            "a": ExtName25
            }
        optional = {
            "b": ExtName25
            }

    assert ExtCombo()._api_versions() == (2, 5)

    class ExtCombo(ExtStruct):
        from_version = 3
        mandatory = {
            "a": ExtName25,
            "b": ExtName25
            }

    assert ExtCombo()._api_versions() == (3, 5)

    class ExtCombo(ExtStruct):
        to_version = 4
        mandatory = {
            "a": ExtName25,
            "b": ExtName25
            }

    assert ExtCombo()._api_versions() == (2, 4)

    class ExtCombo(ExtStruct):
        from_version = 1
        mandatory = {
            "a": ExtName25,
            "b": ExtName25
            }

    try:
        dummy = ExtCombo()._api_versions()
        raise AssertionError()
    except IntAPIValidationError:
        pass

    class ExtCombo(ExtStruct):
        to_version = 6
        mandatory = {
            "a": ExtName25,
            "b": ExtName25
            }

    try:
        dummy = ExtCombo()._api_versions()
        raise AssertionError()
    except IntAPIValidationError:
        pass

    class ExtCombo(ExtStruct):
        mandatory = {
            "a": ExtName03,
            "b": ExtName48
            }

    try:
        dummy = ExtCombo()._api_versions()
        raise AssertionError()
    except IntAPIValidationError:
        pass

    class Person(object):
        def __init__(self, myid):
            self.id = myid

        def __str__(self):
            return "<Person %s>" % (self.id,)

    class ExtPerson(ExtString):
        desc = "The ID of a person"

        regexp = "person-[a-z]{1,8}"

        def convert(self, function, value):
            return value[7:]

        def lookup(self, function, value):
            return Person(value)

        def output(self, function, value):
            if not isinstance(value, Person):
                raise ExtOutputError("ExtPerson.output() takes a Person instance.", value)
            return ExtString.output(self, function, u"person-" + value.id)

    class ExtPersonData(ExtStruct):
        desc = "Information about a person"

        mandatory = {
            'person': ExtPerson,
            'friends': ExtList(ExtPerson),
            }

        optional = {
            'name': ExtString
            }

    p = ExtPerson().parse(0, u"person-viktor")
    print p

    print ExtPerson().output(0, p)

    try:
        print ExtPerson().output(0, "apa")
    except ExtOutputError as e:
        pass

    print ExtPersonData().xsd().xml()

    try:
        pd = ExtPersonData().parse(0, dict(person=u"viktor", friends=[u"mort", u"niklas"], name=u"Viktor Fougstedt"))
    except ExtRegexpMismatchError:
        pass

    pd = ExtPersonData().parse(0, dict(person=u"person-viktor", friends=[u"person-mort", u"person-niklas"], name=u"Viktor Fougstedt"))
        
    print pd

    resp = XMLNode("response")
    ExtPersonData().to_xml(resp, ExtPersonData().output(0, pd))
    soap = resp.xml()
    print soap

    import xml.dom.minidom
    dom = xml.dom.minidom.parseString(soap)

    tmp = ExtPersonData().from_xml(dom.documentElement)
    print tmp
    print ExtPersonData().parse(0, tmp)
