#!/usr/bin/env python2.6

"""
A Model/Manager pair represents some complex data type in the underlying
data model.

A Model instance represents exactly one instance of the underlying type,
such as a particular account, one computer, or a specific individual 
person.

A Manager instance manages models of a certain type as a group - creating 
and destroying individual data objects, returning Model instances for
its type, and performing operations on multiple data objects at one
time.

Every running Function can create a Manager by internal methods, which also
makes sure that there is only one Manager of a particular type for that
Function at any one time.

In a database-backed system, Functions get their own database link (and
therefore their own transaction space). Managers can use the database
link of the Function that created them, as can the Model instances that
a Manager creates. Once a Function completes running, the Managers and
Models it has created are deallocated.

Model classes can also ease the creation of standard Functions and
external data types. They do this by using the @extattr() decorator on
methods named get_*() and set_*(). The decorator specifies the external
data type that is returned/expected, the external attribute name (if other
than what follows get_/set_), and the API versions between which the
attribute is to be defined this way.

@extattr decorators may be nested, and may choose to supply different
descriptions of the attribute by the 'desc' keyword argument. Normally,
however, the description is stable while types and names vary over
API versions. There is therefore a special @extdesc() decorator which
sets a default external description.
"""

from error import IntAPIValidationError
from exttype import ExtType, ExtStruct, ExtList, ExtBoolean, ExtOrNull

class _TemplateReference(object):
    def __init__(self, other, nullable):
        if type(other) == type(type) and issubclass(other, Model):
            other = other._name()
        self.name = other
        self.nullable = nullable

class ExternalAttribute(object):
    # Valid for one particular API version.
    def __init__(self, name, type=None, method=None, desc=None, model=None, args=None, kwargs=None):
        self.extname = name
        self.exttype = type
        self.method = method
        self.extdesc = desc
        self.model = model
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        return "%s attr=%s type=%s method=%s" % (self.__class__.__name__, self.extname, self.exttype, self.method)


class ExternalReadAttribute(ExternalAttribute):
    def fill_template_type(self, tmpl):
        if self.model:
            if isinstance(ExtType.instance(self.exttype), ExtOrNull):
                nullable = True
            else:
                nullable = False
            tmpl.optional[self.extname] = (_TemplateReference(self.model, nullable), self.extdesc)
        else:
            tmpl.optional[self.extname] = (ExtBoolean, self.extdesc)

    def fill_data_type(self, data):
        if self.model:
            if isinstance(ExtType.instance(self.exttype), ExtOrNull):
                nullable = True
            else:
                nullable = False
            data.optional[self.extname] = (_TemplateReference(self.model, nullable), self.extdesc)
        else:
            data.optional[self.extname] = (self.exttype, self.extdesc)

    def fill_update_type(self, upd):
        pass


class ExternalWriteAttribute(ExternalAttribute):
    def fill_template_type(self, tmpl):
        pass

    def fill_data_type(self, data):
        pass

    def fill_update_type(self, upd):
        upd.optional[self.extname] = (self.exttype, self.extdesc)


def template(exttype, name=None, minv=0, maxv=10000, desc=None, model=None, args=[], kwargs={}):
    def decorate(decorated):
        data = dict(name=name, type=exttype, desc=desc, model=model, args=args, kwargs=kwargs)
        if hasattr(decorated, "_update"):
            raise IntAPIValidationError("Both @template and @update cannot be applied to the same method, but are for %s" % (decorated,))

        if hasattr(decorated, "_template"):
            for (submin, submax, subdata) in decorated._template:
                if submin < maxv and submax > minv:
                    raise IntAPIValidationError("Two @template directives have overlapping API versions for %s" % (decorated,))
            decorated._template.append((minv, maxv, data))
        else:
            decorated._template = [(minv, maxv, data)]
        return decorated
    return decorate


def update(exttype, name=None, minv=0, maxv=10000, desc=None):
    def decorate(decorated):
        data = dict(name=name, type=exttype, desc=desc)
        if hasattr(decorated, "_template"):
            raise IntAPIValidationError("Both @template and @update cannot be applied to the same method, but are for %s" % (decorated,))
        if hasattr(decorated, "_update"):
            for (submin, submax, subdata) in decorated._update:
                if submin < maxv and submax > minv:
                    raise IntAPIValidationError("Two @update directives have overlapping API versions for %s" % (decorated,))
            decorated._update.append((minv, maxv, data))
        else:
            decorated._update = [(minv, maxv, data)]
        return decorated
    return decorate



class Model(object):
    # The name attribute is used when cross-referencing between
    # templates, and in auto-generation by the server. 

    # * Types <name>-data-template, <name>-templated-data,
    #   <name>-search-options and <name>-update options will be
    #   created (using @template and @update decorators on methods in
    #   the subclass).  

    # * Function subclasses for RPCs named <name>_dig(),
    #   <name>_fetch() and <name>_update() will also be created.

    # * When auto-generating, the Ext<Name> type must exist, and
    #   represent one instance of <name> externally.
    
    # It cannot be changed between API versions (since we, in
    # principle, never change the model completely, we only modify it
    # and adapt the API with which that model is accessed). Choose
    # carefully.
    name = None

    def __init__(self, manager, *args, **kwargs):
        if not isinstance(manager, Manager):
            raise ValueError("The first argument to all Model instances must be the Manager that created them - received %s instead" % (manager,))
        self.manager = manager
        self.function = manager.function
        self.db = manager.function.db
        self._templated = {}
        self.init(*args, **kwargs)

    def __getattr__(self, attr):
        if attr.endswith("_manager"):
            setattr(self, attr, getattr(self.manager, attr))
            return getattr(self, attr)
        else:
            raise AttributeError(attr)

    @classmethod
    def _name(cls):
        return cls.name

    @classmethod
    def _attributes(cls, api_version):
        # Note: the result is cached in the _class_ object, and
        # therefore only ever calculated once.

        # Note 2: If the attribute has a "model" attribute, the
        # _TemplateReference object is used in the templates on an
        # "<attr>-data" attribute. _TemplateReferences are used to
        # resolve mutual references between several template types.

        try:
            return cls._attributes_cache[api_version]
        except KeyError:
            cls._attributes_cache[api_version] = {}
        except AttributeError:
            cls._attributes_cache = {api_version: {}}

        for candname in dir(cls):
            candidate = getattr(cls, candname)
            if hasattr(candidate, "_template"):
                attrcls = ExternalReadAttribute
                defs = candidate._template
            elif hasattr(candidate, "_update"):
                attrcls = ExternalWriteAttribute
                defs = candidate._update
            else:
                continue

            for (minv, maxv, data) in defs:
                if api_version >= minv and api_version <= maxv:
                    break
            else:
                continue

            name = data.pop("name", None) or candname[4:]
            if name in cls._attributes_cache[api_version]:
                raise IntAPIValidationError("Multiple @template/@update definitions uses the public name %s for API version %d" % (name, api_version))

            data["method"] = candidate

            typminv, typmaxv = ExtType.instance(data["type"])._api_versions()
            if api_version < typminv or api_version > typmaxv:
                raise IntAPIValidationError("@template/@update definition on method %s.%s says its valid through API versions (%d, %d), but the type %s it uses is valid through (%d, %d) making it invalid for version %d" % (cls, candname, minv, maxv, data["type"], typminv, typmaxv, api_version))

            if "model" in data and data["model"]:
                cls._attributes_cache[api_version][name + "-data"] = attrcls(name + "-data", **data)

            dummy = data.pop("model", None)
            cls._attributes_cache[api_version][name] = attrcls(name, **data)

        return cls._attributes_cache[api_version].values()

    @classmethod
    def _template_type(cls, api_version):
        tmpl = ExtStruct()
        tmpl.from_version = api_version
        tmpl.to_version = api_version
        tmpl.name = ExtType.capsify(cls.name + "-data-template")

        for attr in cls._attributes(api_version):
            attr.fill_template_type(tmpl)
        return tmpl

    @classmethod
    def _data_type(cls, api_version):
        data = ExtStruct()
        data.from_version = api_version
        data.to_version = api_version
        data.name = ExtType.capsify(cls.name + "-templated-data")
        
        for attr in cls._attributes(api_version).values():
            attr.fill_data_type(data)
        return data

    @classmethod
    def _update_type(cls, api_version):
        upd = ExtStruct()
        upd.from_version = api_version
        upd.to_version = api_version
        upd.name = ExtType.capsify(cls.name + "-update")
        
        for attr in cls._attributes(api_version).values():
            attr.fill_update_type(upd)
        return upd

    def apply_template(self, api_version, tmpl):
        # Note: many different other Model instances may call
        # .apply_template on this instance, with the same or another
        # template instance (remember that templates may be nested
        # arbitrarily deep by the client). They should all get the
        # same data for the same template - make sure it is cached!

        tmplidx = str(tmpl)
        if (api_version, tmplidx) in self._templated:
            return self._templated[(api_version, tmplidx)]

        # _attributes_cache will be filled in the _class_ object when
        # the server generates the template types, and therefore
        # always available to instances when applying information
        # parsed by such a type.

        out = {}
        for (name, attr) in self._attributes_cache[api_version].items():
            # Does the client want data for this template key? Note:
            # "not tmpl[name]" would be wrong - an empty subtemplate
            # should generate an emtpy sub-data.

            if name not in tmpl or tmpl[name] == False:
                continue

            # The ExternalAttribute instance has a reference to the
            # method (directly from the class, i.e. unbound so we need
            # to pass self explicitly) and any parameters to
            # it.

            value = attr.method(self, *attr.args, **attr.kwargs)

            if value is None:
                if "_remove_nulls" in tmpl and tmpl["_remove_nulls"]:
                    continue
                out[name] = None
                continue

            if attr.model:
                subtmpl = tmpl[name]
                if "_remove_nulls" in tmpl and "_remove_nulls" not in subtmpl:
                    subtmpl = subtmpl.copy()
                    subtmpl["_remove_nulls"] = tmpl["_remove_nulls"]
                out[name] = value.apply_template(api_version, subtmpl)
            else:
                out[name] = value #ExtType.instance(attr.exttype).output(self.function, value)
        self._templated[(api_version, tmplidx)] = out
        print out
        return out

    def init(self, *args, **kwargs):
        return


class Manager(object):
    # If name="foo_manager", then <function>.foo_manager,
    # <manager>.foo_manager and <model>.foo_manager will return a
    # function-specific manager instance of this class. The
    # name must end in "_manager".
    name = None

    # The model class that this manager creates instances of.
    manages = None

    @classmethod
    def _name(cls):
        assert cls.name.endswith("_manager")
        return cls.name

    def __init__(self, function, *args, **kwargs):
        self.function = function
        self.db = function.db
        self.init(*args, **kwargs)

    def init(self, *args, **kwargs):
        return

    def __getattr__(self, attr):
        if self.name and attr == self.name + "_manager":
            return self
        elif attr.endswith("_manager"):
            setattr(self, attr, getattr(self.function, attr))
            return getattr(self, attr)
        else:
            raise AttributeError(attr)

    
if __name__ == "__main__":
    from exttype import *

    class ExtName03(ExtString):
        to_version = 3
        desc = "A person's name (either firstname or lastname)"
        regexp = "[A-Z][a-z]+"

    class ExtName25(ExtName03):
        from_version = 2
        to_version = 5

    class ExtName48(ExtName03):
        from_version = 4
        to_version = 8

    class ExtAccount(ExtString):
        pass

    class ExtPerson(ExtString):
        pass

    class Person(Model):
        name = "person"

        def get_int(self):
            return "int"

        @template(ExtName03, maxv=3)
        @template(ExtName48, minv=4, name="newapa")
        def get_apa(self):
            pass

        @update(ExtName03, maxv=2)
        def set_apa(self):
            pass

        @template(ExtAccount, model="account")
        def get_account(self):
            pass


    class Account(Model):
        name = "account"

        @template(ExtString, model="person")
        def get_owner(self):
            pass


    for v in range(0, 5):
        print
        print v
        print "tmpl", Person._template_type(v).optional
        print "data", Person._data_type(v).optional
        print "update", Person._update_type(v).optional
        print "tmpl", Account._template_type(v).optional
        print "data", Account._data_type(v).optional
        print "update", Account._update_type(v).optional

        


    
