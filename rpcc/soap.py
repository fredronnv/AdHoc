

from exttype import *


def xml_escape(desc):
    desc = desc.replace("&", "&amp;")
    desc = desc.replace("<", "&lt;")
    desc = desc.replace(">", "&gt;")
    return desc


class SOAPError(Exception):
    soapcode = None
    soaptext = None

    def __init__(self, error=None):
        self.args = error

        if isinstance(error, dict):
            self.rpcerr = error
            self.soaptext = None
        else:
            self.rpcerr = None
            self.soaptext = error

    def fix_header(self, header):
        pass

    def get_envelope(self, schema_url):
        env = XMLNode("Envelope")
        header = env.new("Header")
        self.fix_header(header)

        body = env.new("Body")
        fault = body.new("Fault")
        #fault = body.new("Fault", _other_attributes={"xmlns":""})
        env.set_namespace("env", "http://schemas.xmlsoap.org/soap/envelope/")
        fault.new("faultcode").cdata("env:" + self.soapcode)

        if self.soaptext:
            errtxt = self.soaptext
        elif self.rpcerr:
            errtxt = self.rpcerr['desc']
        else:
            errtxt = ""

        fault.new("faultstring").cdata(errtxt)

        det = fault.new("detail")

        if self.rpcerr:
            err = det.new("soapFaultDetail")

            err.new("errorId").cdata(self.rpcerr['id'])
            err.new("errorName").cdata(self.rpcerr['name'])

            #if self.rpcerr['traceback']:
            #    tb = err.new("argumentTraceback")
            #    for item in self.rpcerr['traceback']:
            #        if isinstance(item, int):
            #            tb.new("index").cdata(str(item))
            #        else:
            #            tb.new("key").cdata(item)
            # TODO: Follwoing line has reference errors for server and mssuffix
            err.set_namespace("e", server.get_schema_url(mssuffix))  # @UndefinedVariable

        return env


class SOAPVersionMismatchError(SOAPError):
    soapcode = "VersionMismatch"

    def fix_header(self, header):
        header.new("Upgrade").new("SupportedEnvelope",
                                  {"xmlns:ns1": "http://scemas.xmlsoap.org/soap/envelope"},
                                  qname="ns1:Envelope")


class SOAPMustUnderstandError(SOAPError):
    soapcode = "MustUnderstand"
    soaptext = "Client sent mustUnderstand header which was not understood"


class SOAPDataEncodingUnknownError(SOAPError):
    soapcode = "DataEncodingUnknown"


class SOAPServerError(SOAPError):
    soapcode = "Server"


class SOAPClientError(SOAPError):
    soapcode = "Client"


class SOAPFaultDetailType(ExtStruct):
    name = 'soap-fault-detail'
    desc = "The detail element of a SOAP Fault message"

    mandatory = {
        'errorName': ExtString,
        'errorID': ExtInteger,
    }


class SOAPParseError(SOAPClientError):
    name = 'SOAPParseError'
    desc = 'The received SOAP request does not conform to the WSDL.'


class SOAPGenerationError(SOAPServerError):
    name = 'SOAPGenerationError'
    desc = 'The return value cannot be converted to the correct SOAP response.'


class SOAPTypeDef(object):
    visible = True

    def __init__(self, server, docdict):
        self.server = server
        self.docdict = docdict
        try:
            self.desc = docdict['description'].strip() or None
        except AttributeError:
            self.desc = None
        except KeyError:
            self.desc = None
        self.basetype = docdict['dict_type']

        self.init_specials()
        self.init_names()
        self.wsdlrefname = "myxsd:" + self.wsdlname
        if self.visible:
            self.server.add_soap_typedef(self)

    def init_names(self):
        self.name = self.docdict['name']
        self.wsdlname = self.server.capsify_name(self.name) + 'Type'

    def init_specials(self):
        pass

    def wsdl_base_element(self):
        return XMLNode('simpleType', name=self.wsdlname)

    def wsdl_element(self):
        elem = self.wsdl_base_element()
        if self.desc:
            desc = xml_escape(self.desc)
            elem.new('annotation').new('documentation').cdata(desc)
        self.wsdl_add_restriction(elem)
        return elem

    def factory(self):
        return SOAPTypeDefFactory(self.server)

    def XXXsoap_parse(self, elem):
        # Most elements just have text or cdata content, so this base
        # class implements reading that. Override in struct/list
        # subclasses.

        #print "default typedef:", elem.tagName
        stringdata = ''
        for child in elem.childNodes:
            if child.nodeType not in [child.TEXT_NODE, child.CDATA_SECTION_NODE]:
                raise SOAPParseError("Invalid child element type, must be text or cdata")
            stringdata += child.data
        return self.soap_parse_string(stringdata)

    def XXXsoap_parse_string(self, rawstring):
        raise NotImplementedError()

    def soap_tag(self, elem):
        name = elem.tagName
        if ':' in name:
            name = name.split(':', 1)[1]
        return name

    # The name of the element is unknown to the type, since it is
    # defined by the struct key/list type/response that has a value
    # of the type. The parent therefore creates the element and
    # passes it down.
    def XXXsoap_encode(self, element, value):
        # Base class implementation handles string values.
        element.cdata(self.soap_encode_as_string(value))

    def XXXsoap_encode_as_string(self, value):
        raise NotImplementedError()


class SOAPStringTypeDef(SOAPTypeDef):

    def init_specials(self):
        self.regexp = self.docdict.get('regexp', None)
        self.maxlen = self.docdict.get('maxlen', None)

    def XXXwsdl_add_restriction(self, base):
        r = base.new('restriction', base='string')
        if self.regexp is not None:
            r.new('pattern', value=self.regexp)
        if self.maxlen is not None:
            r.new('maxLength', value=str(self.maxlen))

    def XXXsoap_parse_string(self, rawstring):
        return rawstring

    def XXXsoap_encode_as_string(self, value):
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class SOAPEnumTypeDef(SOAPTypeDef):

    def init_specials(self):
        self.values = self.docdict['values']

    def XXXwsdl_add_restriction(self, base):
        r = base.new('restriction', base='string')
        for v in self.values:
            r.new('enumeration', value=v)

    def XXXsoap_parse_string(self, rawstring):
        return rawstring

    def XXXsoap_encode_as_string(self, value):
        return value


class SOAPIntegerTypeDef(SOAPTypeDef):

    def init_specials(self):
        self.minval = self.docdict.get('min_value', None)
        self.maxval = self.docdict.get('max_value', None)

    def XXXwsdl_add_restriction(self, base):
        r = base.new('restriction', base='integer')
        if self.minval is not None:
            r.new('minInclusive', value=str(self.minval))
        if self.maxval is not None:
            r.new('maxInclusive', value=str(self.maxval))

    def XXXsoap_parse_string(self, rawstring):
        return int(rawstring)

    def XXXsoap_encode_as_string(self, value):
        try:
            return '%d' % (value,)
        except:
            print value
            raise


class SOAPBoolTypeDef(SOAPTypeDef):

    def XXXwsdl_add_restriction(self, base):
        base.new('restriction', base='boolean')

    def XXXsoap_parse_string(self, rawstring):
        if rawstring in ['true', '1']:
            return True
        if rawstring in ['false', '0']:
            return False
        raise SOAPParseError("Invalid boolean")

    def XXXsoap_encode_as_string(self, value):
        if value:
            return "true"
        return "false"


class SOAPListTypeDef(SOAPTypeDef):

    def init_specials(self):
        itemdd = self.docdict['value_type']
        self.value_type = self.factory().typedef(itemdd)
        self.elemname = self.value_type.wsdlname[:-4]

    def wsdl_base_element(self):
        return XMLNode('complexType', name=self.wsdlname)

    def XXXwsdl_add_restriction(self, base):
        # A sequence of elements, each named after the type name of
        # the element type, minus the "Type" suffix.
        seq = base.new('sequence')
        seq.new('element', name=self.elemname,
                type=self.value_type.wsdlrefname,
                minOccurs='0', maxOccurs='unbounded')

    def XXXsoap_parse(self, elem):
        parsed_list = []

        for child in elem.childNodes:
            if self.soap_tag(child) != self.elemname:
                raise SOAPParseError("List child has wrong tag name")
            parsed_list.append(self.value_type.soap_parse(child))

        return parsed_list

    def XXXsoap_encode(self, element, value):
        for subval in value:
            try:
                child = element.new(self.elemname)
                self.value_type.soap_encode(child, subval)
            except:
                print subval
                raise


class SOAPStructItemTypeDef(SOAPTypeDef):
    visible = False

    def init_specials(self):
        self.type = self.factory().typedef(self.docdict['type'])
        self.optional = self.docdict['optional']

    def wsdl_add_element(self, base):
        if self.optional:
            elem = base.new('element', name=self.get_element_name(),
                            type=self.type.wsdlrefname,
                            minOccurs='0', maxOccurs='1')
        else:
            elem = base.new('element', name=self.get_element_name(),
                            type=self.type.wsdlrefname)

        if self.desc:
            desc = xml_escape(self.desc)
            elem.new('annotation').new('documentation').cdata(desc)

    def get_element_name(self):
        return self.wsdlname[:-4]

    def soap_parse(self, elem):
        return self.type.soap_parse(elem)

    def soap_encode(self, element, value):
        child = element.new(self.get_element_name())
        self.type.soap_encode(child, value)


class SOAPStructTypeDef(SOAPTypeDef):

    def init_specials(self):
        self.element_to_key = {}
        self.key_to_element = {}

        self.mandatory = {}
        self.mandatory_order = []

        mand_dd = self.docdict['mandatory']
        mand_dd.sort(lambda a, b: cmp(a['name'], b['name']))
        for d in mand_dd:
            itemdef = SOAPStructItemTypeDef(self.server, d)
            elemname = itemdef.get_element_name()
            self.mandatory[elemname] = itemdef
            self.mandatory_order.append(elemname)
            self.element_to_key[elemname] = d['name']
            self.key_to_element[d['name']] = elemname

        self.optional = {}
        self.optional_order = []

        opt_dd = self.docdict['optional']
        opt_dd.sort(lambda a, b: cmp(a['name'], b['name']))
        for d in opt_dd:
            itemdef = SOAPStructItemTypeDef(self.server, d)
            elemname = itemdef.get_element_name()
            self.optional[elemname] = itemdef
            self.optional_order.append(elemname)
            self.element_to_key[elemname] = d['name']
            self.key_to_element[d['name']] = elemname

    def wsdl_base_element(self):
        return XMLNode('complexType', name=self.wsdlname)

    def wsdl_add_restriction(self, base):
        seq = base.new('sequence')
        for key in self.mandatory_order:
            typedef = self.mandatory[key]
            typedef.wsdl_add_element(seq)
        opt = seq.new('element', name='optionalElements')
        optseq = opt.new('complexType').new('sequence')
        for key in self.optional_order:
            typedef = self.optional[key]
            typedef.wsdl_add_element(optseq)

    def soap_parse(self, elem):
        mandatory_defs = self.mandatory.copy()
        optional_defs = self.optional.copy()
        parsed = {}

        def parse_elem(defdict, targetdict, elem, kind):
            name = self.soap_tag(elem)
            if name in targetdict:
                raise SOAPParseError("Duplicate %s element %s" % (kind, name))

            try:
                typedef = defdict.pop(name)
            except KeyError:
                raise SOAPParseError("Unknown %s element %s" % (kind, name))

            value = typedef.soap_parse(elem)
            targetdict[self.element_to_key[name]] = value

        for child in elem.childNodes:
            if child.nodeName == "#text" and not child.wholeText.strip():
                continue
            if self.soap_tag(child) == 'optionalElements':
                for opt in child.childNodes:
                    if opt.nodeName == "#text" and not opt.wholeText.strip():
                        continue
                    parse_elem(optional_defs, parsed, opt, "optional")
            else:
                parse_elem(mandatory_defs, parsed, child, "mandatory")

        if mandatory_defs:
            raise SOAPParseError("Mandatory elements missing.")

        return parsed

    def soap_encode(self, element, value):
        # Value is key -> value mapping to encode.
        valcopy = value.copy()

        # For each mandatory element, find the corresponding key in the
        # value mapping and remove it when found. If a mandatory key
        # is not found, it is an error.
        for elemname in self.mandatory_order:
            key = self.element_to_key[elemname]
            if key in valcopy:
                self.mandatory[elemname].soap_encode(element, valcopy[key])
                del valcopy[key]
            else:
                # This is not a SOAP-error, but will be converted to
                # one when responding.
                raise ValueError("Mandatory key %s missing from response" % (key,))

        # For each optional element, find the key and remove from the
        # mapping if found. If not found, everything is OK (it's optional).

        optional = element.new('optionalElements')
        for elemname in self.optional_order:
            key = self.element_to_key[elemname]
            if key in valcopy:
                if valcopy[key] is not None:
                    self.optional[elemname].soap_encode(optional, valcopy[key])
                del valcopy[key]

        # If there are keys left after encoding, it is an error.
        if valcopy:
            # This is not a SOAP-error, but will be converted to
            # one when responding.
            raise ValueError("Undocumented response keys %s in result" % (", ".join(valcopy.keys()),))

        #for (key, v) in value.items():
        #    k = self.key_to_element[key]
        #    if k in self.mandatory:
        #        self.mandatory[k].soap_encode(element, v)
        #    elif k in self.optional:
        #        self.optional[k].soap_encode(optional, v)
        #    else:
        #        raise ValueError("Unknown response key %s in dict %s" % (k, value))


class SOAPOrNullTypeDef(SOAPTypeDef):

    def init_specials(self):
        self.value_type = self.factory().typedef(self.docdict['otherwise'])

    def init_names(self):
        self.name = self.value_type.name + '-ornull'
        self.wsdlname = self.value_type.wsdlname[:-4] + 'OptionalType'

    def wsdl_element(self):
        elem = XMLNode('complexType', name=self.wsdlname)
        chelem = elem.new('choice')
        chelem.new('element', name='set', type=self.value_type.wsdlrefname)
        chelem.new('element', name='notSet', type="myxsd:nullType")
        return elem

    def soap_parse(self, elem):
        if len(elem.childNodes) != 1:
            raise SOAPParseError()
        elem = elem.childNodes[0]
        if elem.tagName == 'set':
            return self.value_type.soap_parse(elem)
        elif elem.tagName == 'notSet':
            return None
        else:
            raise SOAPParseError()

    def soap_encode(self, element, value):
        if value is None:
            element.new('notSet')
        else:
            child = element.new('set')
            self.value_type.soap_encode(child, value)


class SOAPNullTypeDef(SOAPTypeDef):

    def wsdl_element(self):
        elem = XMLNode('complexType', name=self.wsdlname)
        elem.new('sequence')
        return elem

    def soap_parse(self, elem):
        return None

    def soap_encode_as_string(self, value):
        return ""


class SOAPRecursionMarkerTypeDef(SOAPTypeDef):
    visible = False


class SOAPTypeDefFactory(object):

    def __init__(self, server):
        self.server = server

    def typedef(self, docdict):
        typ = docdict['dict_type']

        typemap = {
            'integer-type': SOAPIntegerTypeDef,
            'string-type': SOAPStringTypeDef,
            'boolean-type': SOAPBoolTypeDef,
            'list-type': SOAPListTypeDef,
            'struct-type': SOAPStructTypeDef,
            'ornull-type': SOAPOrNullTypeDef,
            'null-type': SOAPNullTypeDef,
            'enum-type': SOAPEnumTypeDef,
            'recursion-marker': SOAPRecursionMarkerTypeDef
        }

        typedef = typemap[typ](self.server, docdict)
        return typedef


class SOAPParameterDefinition(object):

    def __init__(self, function, index, docdict):
        self.function = function
        self.server = self.function.server
        self.index = index
        self.docdict = docdict
        self.name = docdict['name']
        self.soapname = self.server.capsify_name(self.name)
        self.desc = docdict['desc'].strip() or None
        self.type = SOAPTypeDefFactory(self.server).typedef(docdict['type'])

    def wsdl_element(self, mscompat):
        if mscompat:
            elem = XMLNode('element', name=self.soapname + "_in",
                           type=self.type.wsdlrefname)
        else:
            elem = XMLNode('element', name=self.soapname,
                           type=self.type.wsdlrefname)

        if self.desc:
            desc = xml_escape(self.desc)
            elem.new('annotation').new('documentation').cdata(desc)

        return elem

    def get_index(self):
        return self.index

    def soap_parse(self, elem):
        return self.type.soap_parse(elem)


class SOAPFunctionDefiniton(object):
    """A class which represents a function definition, with
    SOAP information such as request and response element name etc."""

    def __init__(self, server, funname, funclass):
        self.server = server

        # Funname is the XMLRPC function name (.rpcname attribute
        # of the RPCFunction class)
        self.name = funname
        self.funclass = funclass
        self.funclass_encoding = funclass.encoding
        self.docdict = server.get_docdict(funclass)

        # SOAP-name is a capsified version of the funname, since
        # underscores work poorly with SOAP.
        self.soapname = self.capsify_name(funname)

        # WSDL Message names
        self.input_message = self.capsify_name("msg-" + funname + "-input")
        self.input_message_ref = "self:" + self.input_message
        self.output_message = self.capsify_name("msg-" + funname + "-output")
        self.output_message_ref = "self:" + self.output_message

        # SOAP message element tagNames
        self.request_element = self.soapname
        self.request_element_ref = "myxsd:" + self.soapname
        self.response_element = self.request_element + "Response"
        self.response_element_ref = "myxsd:" + self.response_element

        # Parameters, by name and as list
        self.params_by_name = {}
        self.params_by_index = {}
        self.params = []

        l = self.docdict['parameters']
        for (idx, paramdd) in zip(range(len(l)), l):
            pardef = SOAPParameterDefinition(self, idx, paramdd)
            self.params.append(pardef)
            self.params_by_name[pardef.soapname] = pardef
            self.params_by_index[idx] = pardef.soapname

        self.return_type = SOAPTypeDefFactory(self.server).typedef(self.docdict['return_type'])

    def capsify_name(self, name):
        return self.server.capsify_name(name)

    def dencode_strings(self, val, encoding, encode=True):
        if isinstance(val, unicode) and encode:
            return val.encode(encoding)
        elif isinstance(val, str):
            if encode:
                return val
            else:
                return val.decode(encoding)
        elif type(val) in [bool, int]:
            return val
        elif val is None:
            return val
        elif isinstance(val, list):
            return [self.dencode_strings(v, encoding, encode) for v in val]
        elif isinstance(val, dict):
            new = {}
            for (k, v) in val.items():
                if encode:
                    key = k.encode(encoding)
                else:
                    key = k.decode(encoding)
                new[key] = self.dencode_strings(v, encoding, encode)
            return new
        raise ValueError(
            "Cannot decode/encode received value %s as the target function class encoding %s" % (val, encoding))

    def fix_error_traceback(self, errdict):
        if errdict['traceback']:
            errdict['traceback'][0] = self.params_by_index[errdict['traceback'][0]]

    def parse_dom_parameters(self, elemlist_in, mscompat):
        elemlist = [elem for elem in elemlist_in if elem.nodeType == elem.ELEMENT_NODE]
        parsed_params = [None, ] * len(self.params)
        numparsed = 0

        for elem in elemlist:
            if ":" in elem.tagName:
                tagName = elem.tagName.split(":", 1)[1]
            else:
                tagName = elem.tagName
            if mscompat:
                if not tagName.endswith("_in"):
                    raise SOAPParseError("Unknown parameter %s" % tagName)
                tagName = tagName[:-3]
            pardef = self.params_by_name[tagName]
            parsed_value = pardef.soap_parse(elem)
            if self.funclass_encoding:
                parsed_value = self.dencode_strings(parsed_value,
                                                    self.funclass_encoding,
                                                    True)
            parsed_params[pardef.get_index()] = parsed_value
            numparsed += 1

        if len(self.params) != numparsed:
            raise SOAPParseError("Wrong number of parameters")

        return parsed_params

    def encode_response(self, value, mscompat):
        if self.funclass_encoding:
            value = self.dencode_strings(value, self.funclass_encoding, False)

        ret = XMLNode(self.response_element)

        if mscompat and type(self.return_type) in [SOAPStringTypeDef, SOAPIntegerTypeDef, SOAPBoolTypeDef]:
            top = ret.new("value")
        else:
            top = ret

        self.return_type.soap_encode(top, value)
        return ret
