#!/usr/bin/env python

from api import API
from default_error import ExtNoSuchAPIVersionError
from category import FunctionCategory


class APIHandler(object):
    def __init__(self, server):
        self.server = server
        self.logger = self.server.logger
        self.all_funclasses_added = []
        self.initialize()

    def initialize(self):
        self.api_by_schema_url = {}
        self.api_by_wsdl_path = {}

        base_api = API(self, 0)
        self.apis = [base_api]
        self.store_soap_data(base_api)

    def store_soap_data(self, api):
        for path in api.get_all_wsdl_paths():
            self.api_by_wsdl_path[path] = api

        for url in api.get_all_schema_urls():
            self.api_by_schema_url[url] = api

    def add_function(self, funclass):
        self.all_funclasses_added.append(funclass)

        while len(self.apis) < funclass.from_version + 1:
            newapi = self.apis[-1].next_version()
            self.apis.append(newapi)
            self.store_soap_data(newapi)

        for api in self.apis[funclass.from_version:funclass.to_version + 1]:
            try:
                api.add_function(funclass)
            except:
                self.logger.error("Defunct function class:", funclass)
                raise

    def get_function_class(self, funname, api_version):
        return self.get_api(api_version).get_function(funname)

    def get_function_object(self, funname, api_version, httphandler):
        return self.get_api(api_version).get_function_object(funname, httphandler)

    def any_api_has_function(self, funname):
        """See if at least one API has a function of the given name."""

        for api in self.apis:
            if api.has_function(funname):
                return True
        return False

    def get_api(self, version):
        try:
            return self.apis[version]
        except IndexError:
            raise ExtNoSuchAPIVersionError(str(version))

    def list_all_versions(self):
        all_versions = []
        for i in range(len(self.apis)):
            try:
                all_versions.append((i, self.server.api_version_comments[i]))
            except KeyError:
                all_versions.append((i, None))
        return all_versions           

    def add_category(self, catclass):
        """Adds an RPCFunctionCategory subclass to all API versions
        it is valid for. When new API versions are created/detected,
        RPCFunctionCategories are added to the new versions as
        appropriate.
        """

        while len(self.apis) < catclass.from_version + 1:
            self.apis.append(self.apis[-1].next_version())

        for api in self.apis[catclass.from_version:catclass.to_version + 1]:
            api.add_category(catclass)

    def add_categories_from_module(self, mod):
        """Scans an entire module, registering all RPCFunctionCategory
        subclasses in the module using self.add_category().
        """

        import types
        
        for (key, value) in mod.__dict__.items():
            if not isinstance(value, types.TypeType):
                continue
            if not issubclass(value, FunctionCategory):
                continue
            if value == FunctionCategory:
                continue
            
            self.add_category(value)

    def get_wsdl(self, path):
        try:
            return self.api_by_wsdl_path[path].get_wsdl(path)
        except LookupError:
            raise LookupError("Unknown WSDL URL %s" % (path,))

    def get_all_wsdl_urls(self):
        all_urls = []
        for api in self.apis:
            all_urls.extend(api.get_all_wsdl_urls())
        return sorted(all_urls)

    def lookup_soap_namespace(self, namespace):
        if not self.schema_urls:
            self.setup_soap()
            
        try:
            (mscompat, api) = self.schema_urls[namespace]
            return (mscompat, api)
        except LookupError:
            raise LookupError("Unknown SOAP namespace")

    def generate_model_stuff(self):
        for api in self.apis:
            api.generate_dynamic_types()
            api.generate_fetch_functions()
            api.generate_update_functions()
            api.generate_dig_functions()
