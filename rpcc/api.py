

from exterror import ExtFunctionNotFoundError
from interror import IntAPINotFoundError, IntAPIValidationError
from function import Function
from exttype import ExtStruct, ExtList, ExtType, ExtNull
from xmlnode import XMLNode

import model
import function

class API(object):
    """Encapsulates an API version.

    An API version is a specific mapping of external function and type
    names to Function/Type subclasses. The same Type or Function can
    be present in multiple API:s, as long as it does not create a
    collision (multiple Functions and Types may not have the same
    external name in a particular API).
    """

    def __init__(self, handler, version):
        self.handler = handler
        self.server = handler.server
        self.version = version

        # Indexed by public names
        self.functions = {}
        self.types = {}
        #self.soap_fundefs = {}
        #self.soap_typedefs = {}
        #self.soap_request_elements = {}
        self.fun_by_elemname = {}
        self.categories = {}
        self.cat_by_fun = {}
        self.fun_by_cat = {}

    def next_version(self):
        """Create a new API version object, and register all functions
        from this version which should be valid there as well with the
        new object."""

        next = self.__class__(self.handler, self.version + 1)
        for funclass in self.functions.values():
            if funclass.to_version > self.version:
                next.add_function(funclass)
        for catclass in self.categories.values():
            if catclass.to_version > self.version:
                next.add_category(catclass)
        return next

    def add_function(self, funclass):
        # Check API version of added Function
        if funclass.from_version > self.version or \
               funclass.to_version < self.version:
            raise IntAPIValidationError()

        # By using the capsified name internally, we make sure that
        # two Functions do not implement foo_bar and fooBar
        # independently.
        funname = ExtType.capsify(funclass._name())
        if not funname:
            raise IntAPIValidationError("Cannot register %s - it has no extname!" % (funclass,))

        if funname in self.functions:
            if self.functions[funname] == funclass:
                return            
            raise IntAPIValidationError("Both %s and %s implement public name %s for version %d" % (funclass, self.functions[funname], funname, self.version))

        self.functions[funname] = funclass

        for (pname, ptype, pdesc) in funclass.get_parameters():
            try:
                self.add_type(ptype)
            except IntAPIValidationError as e:
                raise IntAPIValidationError("%s parameter %s: %s" % (funclass, pname, e.args[0]))

        try:
            self.add_type(funclass._returns()[0])
        except IntAPIValidationError as e:
            raise TypeError("%s return type: %s" % (funclass, e.args[0]))
        except:
            print "Defunct return type:", funclass.returns
            raise

    def get_function(self, funname):
        try:
            return self.functions[ExtType.capsify(funname)]
        except KeyError:
            raise ExtFunctionNotFoundError(funname)

    def get_function_object(self, funname, httphandler, db):
        cls = self.get_function(funname)
        fun = cls(self.server, httphandler, self, db)
        return fun

    def has_function(self, funname):
        return (ExtType.capsify(funname) in self.functions)

    def get_visible_function_names(self):
        return sorted([cls._name() for cls in self.get_visible_functions()])
        
    def get_visible_functions(self):
        return [cls for cls in self.functions.values() if cls.extvisible]

    def add_type(self, typething):
        typ = ExtType.instance(typething)
        typename = typ._name()
        minv, maxv = typ._api_versions()

        if minv > self.version or maxv < self.version:
            raise IntAPIValidationError("%s (%d-%d) invalid for version %d" % (typething, typething.from_version, typething.to_version, self.version))

        if typename in self.types:
            if self.types[typename] == typething:
                return            
            raise IntAPIValidationError("Both %s and %s implement public name %s for version %d" % (typething, self.types[typename], typename, self.version))
        
        self.types[typename] = typething

        for (key, subtype) in ExtType.instance(typething)._subtypes():
            try:
                self.add_type(subtype)
            except IntAPIValidationError as e:
                if key:
                    raise IntAPIValidationError("%s attribute %s: %s" % (typething, key, e.args[0]))
                else:
                    raise IntAPIValidationError("%s value type: %s" % (typething, e.args[0]))

    def add_category(self, catclass):
        """Registers a category class, making it available for
        e.g. <:category:name:> includes in the HTML documentation.
    
        The first time the API is asked about functions for a category
        or categories for a function, all registered category classes
        are instantiated and passed all registered RPCTypedFunctions
        to determine the mappings.
        
        """
        
        if catclass.from_version > self.version or \
               catclass.to_version < self.version:
            raise IntAPIValidationError()

        catname = catclass.get_public_name()

        if catname in self.categories:
            if isinstance(self.categories[catname], catclass):
                return
            
            raise IntAPIValidationError("API version mismatch adding %s - %s already implements public name %s for version %d" % (typething, self.types[typename], typename, self.version))

        self.categories[catname] = catclass(self)

    def calculate_category_mappings(self, force=False):
        if self.cat_by_fun and not force:
            return
        
        for cat in self.categories.values():
            for funclass in self.functions.values():
                if cat.contains(funclass):
                    if funclass in self.cat_by_fun:
                        self.cat_by_fun[funclass].append(cat)
                    else:
                        self.cat_by_fun[funclass] = [cat]

                    if cat in self.fun_by_cat:
                        self.fun_by_cat[cat].append(funclass)
                    else:
                        self.fun_by_cat[cat] = [funclass]

    def functions_in_category(self, cat):
        self.calculate_category_mappings()
        return self.fun_by_cat[cat]

    def functions_in_category_named(self, catname):
        return self.functions_in_category(self.categories[catname])

    def categories_for_function(self, fun):
        self.calculate_category_mappings()
        if isinstance(fun, function.Function):
            fun = fun.__class__
        return self.cat_by_fun.get(fun, [])

    def categories_for_function_named(self, funname):
        return self.categories_for_function(self.functions[funname])

    def function_for_element_name(self, elemname):
        return self.fun_by_elemname[elemname]
    
    def get_version_string(self, with_dashes=True):
        if with_dashes:
            return "-V%d" % (self.version,)
        else:
            return "v%d" % (self.version,)

    def get_schema_url(self, mscompat=False):
        if self.server.soap_schema_ns_base:
            base = self.server.soap_schema_ns_base
        else:
            base = self.server.get_server_url() + self.server.service_name + "_"
        base += self.get_version_string(with_dashes=False)
        
        if mscompat:
            return base + "_mscompat.xsd"
        else:
            return base + ".xsd"

    def get_all_schema_urls(self):
        return [self.get_schema_url(False), self.get_schema_url(True)]
        
    def get_wsdl_path(self, mscompat=False):
        url = self.server.service_name
        if self.version > 0:
            url += "-" + self.get_version_string(with_dashes=False)
        if mscompat:
            url += "_mscompat"
        url += ".wsdl"
        return url

    def get_all_wsdl_paths(self):
        return [self.get_wsdl_path(False), self.get_wsdl_path(True)]

    def get_wsdl_url(self, mscompat=False):
        url = self.server.get_server_url()
        url += "WSDL/"
        url += self.get_wsdl_path(mscompat)
        return url
            
    def get_all_wsdl_urls(self):
        return [self.get_wsdl_url(False), self.get_wsdl_url(True)]

    ###
    # WSDL-generation
    #
    # Our WSDL starts with XSD describing all elements. We have one
    # definition per Ext-datatype (foo_bar has name fooBarType), one
    # per request element (tag=functionName) and one per response
    # element (tag=functionNameResponse).
    #
    # Then comes a definition of all messages. There is one message
    # per request element and one per response element
    # (msgFunctionNameInput and msgFunctionNameOutput).
    #
    # Then comes a portType, which contains one operation per function
    # (named functionName), referencing the input/output messages.
    #
    # Then comes a binding, which repeats all operations but does not
    # name the messages.
    #
    # Finally comes a service, which just references a binding.
    #
    # SOAP - design by committee at its finest.
    ###

    def get_wsdl(self, path):
        """If incoming path matches .get_wsdl_url(True), output a WSDL 
        which is bug-compatible with the Microsoft svcutil toolchain, 
        accomplished by renaming all input parameters to <name> + '_in'. 
        The WSDL/SOAP URI:s reflect the compatability mode 
        (/SOAP_mscompat rather than /SOAP for example).
        """

        #self.types = {}
        #self.generate_soap_fundefs()

        # Start by creating the base elements for the respective
        # components. That way we can add specific subelements as we
        # go.

        if path == self.get_wsdl_path(True):
            mssuffix = "_mscompat"
            mscompat = True
        elif path == self.get_wsdl_path(False):
            mssuffix = ""
            mscompat = False
        else:
            print "VOLVO"
            raise IntInternalError()

        wsdl_ns = self.get_wsdl_url(mscompat)
        schema_ns = self.get_schema_url(mscompat)
        
        defattrs = {
            'xmlns:self': wsdl_ns,
            'xmlns:myxsd': schema_ns,
            'xmlns:soap': "http://schemas.xmlsoap.org/wsdl/soap/",
            'xmlns': "http://schemas.xmlsoap.org/wsdl/",
            }

        name_attr = self.server.service_name
        if self.version > 0:
            name_attr += "-" + self.get_version_string(with_dashes=False)

        wsdl_root = XMLNode('definitions',
                            name=name_attr,
                            targetNamespace=wsdl_ns,
                            _other_attributes=defattrs,
                            _space_children=True)

        t = wsdl_root.new('types')
        wsdl_schema_root = t.new('schema',
                                 targetNamespace=schema_ns,
                                 xmlns="http://www.w3.org/2001/XMLSchema",
                                 elementFormDefault="qualified",
                                 _space_children=True)
        
        # Note that the dashes in the version will be removed by
        # capsification later
        p = self.server.service_name
        p += self.get_version_string(with_dashes=True)
        p += mssuffix
        ptname = ExtType.capsify(p + '-port-type')
        srvname = ExtType.capsify(p + 'service')
        bndname = ExtType.capsify(p + '-soap-binding')

        # PortType, Binding and Service are added to the WSDL XML element
        # last, since the <message> elements should come before them, but
        # we want to generate the contents of these three nodes at the
        # same time as the <message> elements.
        
        wsdl_porttype_root = XMLNode('portType', name=ptname,
                                     _space_children=True)
        
        wsdl_binding_root = XMLNode('binding', name=bndname,
                                    type="self:"+ptname,
                                    _space_children=True)
        
        wsdl_binding_root.new('soap:binding', style='document',
                              transport="http://schemas.xmlsoap.org/soap/http")

        wsdl_service_root = XMLNode('service', name=srvname)
        prt = wsdl_service_root.new('port', name=srvname+'Port',
                                    binding="self:"+bndname)
        prt.new('soap:address', location=self.server.get_server_url() + 'SOAP')

        ### TODO ###
        #faultdef = RPCSOAPTypeDefFactory(self).typedef(SOAPFaultDetailType()._docdict())
        #faultmsg = wsdl_root.new("message", name="msgFaultDetail")
        #faultmsg.new("part", name="fault", element="myxsd:soapFaultDetail")

        def add_type(schemaelem, already_added, typething):
            typ = ExtType.instance(typething)
            if typ._name() in already_added:
                return

            already_added.add(typ._name())
            schemaelem.add(typ.xsd())

            for (key, subtyp) in typ._subtypes():
                add_type(schemaelem, already_added, subtyp)

        added_types = set()

        for funcls in self.get_visible_functions():
            wsdl_schema_root.add(funcls.xsd_request(mscompat))
            wsdl_schema_root.add(funcls.xsd_response())

            for (name, typ, desc) in funcls.get_parameters():
                add_type(wsdl_schema_root, added_types, typ)

            (typ, desc) = funcls._returns()
            add_type(wsdl_schema_root, added_types, typ)

            # Doc/lit-wrap input message
            msg = wsdl_root.new('message', name=funcls.input_message_name())
            msg.new('part', name='parameters', element="myxsd:"+funcls.request_element_name())

            # Doc/lit-wrap output message
            msg = wsdl_root.new('message', name=funcls.output_message_name())
            msg.new('part', name='parameters', element="myxsd:"+funcls.response_element_name())

            # PortType operation
            op = wsdl_porttype_root.new('operation', name=funcls.soap_name())
            op.new('input', message="self:" + funcls.input_message_name())
            op.new('output', message="self:" + funcls.output_message_name())
            op.new('fault', message="self:msgFaultDetail", name="soapFaultDetail")

            # SOAP operation
            soapaction = self.server.get_server_url() + "SOAP" + "/" + funcls.soap_name()
            soapns = self.server.get_server_url() + "WSDL" + mssuffix
            
            op2 = wsdl_binding_root.new('operation', name=funcls.soap_name())
            op2.new('soap:operation', soapAction=soapaction)
            op2.new('input').new('soap:body', use='literal')
            op2.new('output').new('soap:body', use='literal')
            op2.new('fault', name="soapFaultDetail").new('soap:fault', use='literal', name="soapFaultDetail")

        # Added here to come after all <message>:s
        wsdl_root.add(wsdl_porttype_root)
        wsdl_root.add(wsdl_binding_root)
        wsdl_root.add(wsdl_service_root)

        return wsdl_root.xml()

    ###
    # Auto-generation for _dig(), _update(), _fetch() et. al.
    ###
    def generate_dynamic_types(self):
        self._template_by_model = {}
        self._data_by_model = {}
        self._update_by_model = {}
        self._search_by_manager = {}

        for modelcls in self.server.get_all_models():
            name = modelcls._name()
            tmpl = modelcls._template_type(self.version)
            self._template_by_model[name] = tmpl
            data = modelcls._data_type(self.version)
            self._data_by_model[name] = data
            update = modelcls._update_type(self.version)
            self._update_by_model[name] = update

        for mgrcls in self.server.get_all_managers():
            search = mgrcls._search_type(self.version)
            self._search_by_manager[mgrcls._name()] = search

        # Resolve template references.
        for tmpl in self._template_by_model.values():
            for (attr, (typ, desc)) in tmpl.mandatory.items():
                if isinstance(typ, model._TmpReference):
                    if typ.nullable:
                        tmpl.mandatory[attr] = (ExtOrNull(self._template_by_model[typ.name]), desc)
                    else:
                        tmpl.mandatory[attr] = (self._template_by_model[typ.name], desc)
            for (attr, (typ, desc)) in tmpl.optional.items():
                if isinstance(typ, model._TmpReference):
                    if typ.nullable:
                        tmpl.optional[attr] = (ExtOrNull(self._template_by_model[typ.name]), desc)
                    else:
                        tmpl.optional[attr] = (self._template_by_model[typ.name], desc)

        # Resolve data references.
        for tmpl in self._data_by_model.values():
            for (attr, (typ, desc)) in tmpl.mandatory.items():
                if isinstance(typ, model._TmpReference):
                    if typ.nullable:
                        tmpl.mandatory[attr] = (ExtOrNull(self._data_by_model[typ.name]), desc)
                    else:
                        tmpl.mandatory[attr] = (self._data_by_model[typ.name], desc)
            for (attr, (typ, desc)) in tmpl.optional.items():
                if isinstance(typ, model._TmpReference):
                    if typ.nullable:
                        tmpl.optional[attr] = (ExtOrNull(self._data_by_model[typ.name]), desc)
                    else:
                        tmpl.optional[attr] = (self._data_by_model[typ.name], desc)

        # Resolve search references.
        for srch in self._search_by_manager.values():
            for (key, (typ, desc)) in srch.optional.items():
                if isinstance(typ, model._TmpReference):
                    srch[key] = (self._search_by_manager[typ.name], desc)
                

    def generate_fetch_functions(self):
        for modelcls in self.server.get_all_models():
            name = modelcls._name()
            capsname = name[0].upper() + name[1:]

            clsattrs = {}
            clsattrs["from_version"] = self.version
            clsattrs["to_version"] = self.version
            clsattrs["extname"] = name + "_fetch"
            clsattrs["params"] = [(name, modelcls.exttype, "The %s to fetch" % (name,)),
                                  ("template", self._template_by_model[name], "Data template")]
            clsattrs["returns"] = (self._data_by_model[name], "Templated data")
            clsattrs["desc"] = "Get data about a particular %s. The template indicates which fields (and optionally sub-fields for linked templates) to return." % (name,)

            fetchcls = type("Fun" + capsname + "Fetch", (function.FetchFunction,), clsattrs)
            self.add_function(fetchcls)


    def generate_update_functions(self):
        for modelcls in self.server.get_all_models():
            name = modelcls._name()
            capsname = name[0].upper() + name[1:]

            clsattrs = dict(from_version = self.version,
                            to_version = self.version,
                            extname = name + "_update",
                            returns = ExtNull)
            clsattrs["params"] = [(name, modelcls.exttype, "The %s to update" % (name,)),
                                  ("updates", self._update_by_model[name], "Fields and updates")]
            clsattrs["desc"] = "Update one or more fields atomically."

            upcls = type("Fun" + capsname + "Update", (function.UpdateFunction,), clsattrs)
            self.add_function(upcls)


    def generate_dig_functions(self):
        for mgrcls in self.server.get_all_managers():
            print mgrcls
            mgrname = mgrcls._name()
            modelname = mgrcls.manages._name()

            capsname = modelname[0].upper() + modelname[1:]

            clsattrs = dict(from_version=self.version,
                            to_version=self.version,
                            extname=modelname + "_dig",
                            returns=self._data_by_model[modelname])

            clsattrs["params"] = [("search", self._search_by_manager[mgrname], "Search options"),
                                  ("template", self._template_by_model[modelname], "Fields and updates")]
            clsattrs["desc"] = "Search and return %ss." % (modelname,)

            digcls = type("Fun" + capsname + "Dig", (function.DigFunction,), clsattrs)
            self.add_function(digcls)

