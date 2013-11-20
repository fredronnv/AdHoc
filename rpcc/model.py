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

import random
import datetime
import functools

from error import IntAPIValidationError
from exttype import *
from default_type import *

class _TmpReference(object):
    def __init__(self, other, nullable=False, islist=False):
        if type(other) == type(type) and issubclass(other, Model):
            other = other._name()
        self.name = other
        self.nullable = nullable
        self.islist = islist

class ExternalAttribute(object):
    # Valid for one particular API version.
    def __init__(self, name, type=None, method=None, desc=None, model=None, args=[], kwargs={}):
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
            tmpl.optional[self.extname] = (_TmpReference(self.model, nullable), self.extdesc)
        else:
            tmpl.optional[self.extname] = (ExtBoolean, self.extdesc)

    def fill_data_type(self, data):
        if self.model:
            if isinstance(ExtType.instance(self.exttype), ExtOrNull):
                nullable, islist = True, False
            elif isinstance(ExtType.instance(self.exttype), ExtList):
                nullable, islist = False, True
            else:
                nullable, islist = False, False
                
            data.optional[self.extname] = (_TmpReference(self.model, nullable, islist), self.extdesc)
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


# NOTE! In order for @entry and @template to be stackable in arbitrary
# order, @entry needs to know about (and copy) the _template method
# attribute.
def template(name, exttype, minv=0, maxv=10000, desc=None, model=None, args=[], kwargs={}):
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


# NOTE! In order for @entry and @update to be stackable in arbitrary
# order, @entry needs to know about (and copy) the _update method
# attribute.
def update(name, exttype, minv=0, maxv=10000, desc=None):
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
    name = ""

    # The ID type determines, among other things, which result set
    # table will be used. Valid values are str/int (the Python types).
    id_type = str

    def __init__(self, manager, *args, **kwargs):
        if not isinstance(manager, Manager):
            raise ValueError("The first argument to all Model instances must be the Manager that created them - received %s instead" % (manager,))
        self.manager = manager
        self.function = manager.function
        self.db = manager.function.db
        self._templated = {}

        # Dict of Model-stable _Decision:s, indexed by Guard instance.
        self._decision_cache = {}

        if len(args) == 0:
            raise ValueError("There must be a second argument to a Model instance  - the object id - but none was received by %s." % (self.__class__.__name__,))
        if not isinstance(args[0], self.id_type):
            raise ValueError("The object id %s is not of type %s, which %s.id_type says it should be." % (args[0], self.id_type, self.__class__.__name__))

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
        # _TmpReference object is used in the templates on an
        # "<attr>_data" attribute. _TmpReferences are used as
        # placeholders, to resolve mutual references between template
        # types.

        try:
            return cls._attributes_cache[api_version]
        except KeyError:
            cls._attributes_cache[api_version] = ({}, {})
        except AttributeError:
            cls._attributes_cache = {api_version: ({}, {})}

        for candname in dir(cls):
            candidate = getattr(cls, candname)
            if hasattr(candidate, "_template"):
                attrcls = ExternalReadAttribute
                defs = candidate._template
                dest = cls._attributes_cache[api_version][0]
            elif hasattr(candidate, "_update"):
                attrcls = ExternalWriteAttribute
                defs = candidate._update
                dest = cls._attributes_cache[api_version][1]
            else:
                continue

            for (minv, maxv, data) in defs:
                if api_version >= minv and api_version <= maxv:
                    break
            else:
                continue

            name = data.pop("name")
            if name in dest:
                raise IntAPIValidationError("Multiple @template/@update definitions uses the public name %s for API version %d" % (name, api_version))

            typminv, typmaxv = ExtType.instance(data["type"])._api_versions()
            if api_version < typminv or api_version > typmaxv:
                raise IntAPIValidationError("@template/@update definition on method %s.%s says its valid through API versions (%d, %d), but the type %s it uses is valid through (%d, %d) making it invalid for version %d" % (cls, candname, minv, maxv, data["type"], typminv, typmaxv, api_version))

            data["method"] = candidate

            if "model" in data and data["model"]:
                dest[name + "_data"] = attrcls(name + "_data", **data)

            dummy = data.pop("model", None)
            dest[name] = attrcls(name, **data)

        return cls._attributes_cache[api_version]

    @classmethod
    def _read_attributes(cls, api_version):
        return cls._attributes(api_version)[0]

    @classmethod
    def _write_attributes(cls, api_version):
        return cls._attributes(api_version)[1]

    @classmethod
    def _template_type(cls, api_version):
        tmpl = ExtStruct()
        tmpl.from_version = api_version
        tmpl.to_version = api_version
        tmpl.name = cls.name + "-data-template"

        for attr in cls._read_attributes(api_version).values():
            attr.fill_template_type(tmpl)
        return tmpl

    @classmethod
    def _data_type(cls, api_version):
        data = ExtStruct()
        data.from_version = api_version
        data.to_version = api_version
        data.name = cls.name + "-templated-data"
        
        for attr in cls._read_attributes(api_version).values():
            attr.fill_data_type(data)
        return data

    @classmethod
    def _update_type(cls, api_version):
        upd = ExtStruct()
        upd.from_version = api_version
        upd.to_version = api_version
        upd.name = cls.name + "-update"

        for attr in cls._write_attributes(api_version).values():
            attr.fill_update_type(upd)
        return upd

    def apply_update(self, api_version, updates):
        writeattrs = self._write_attributes(api_version)
        for (name, newval) in updates.items():
            attr = writeattrs[name]
            attr.method(self, newval, *attr.args, **attr.kwargs)

    def apply_template(self, api_version, tmpl):
        # Note: many different other Model instances may call
        # .apply_template on this instance, with the same or another
        # template instance (remember that templates may be nested
        # arbitrarily deep by the client). They should all get the
        # same data for the same template - make sure it is cached!

        tmplidx = str(tmpl)
        if (api_version, tmplidx) in self._templated:
            return self._templated[(api_version, tmplidx)]

        out = {}
        readattrs = self._read_attributes(api_version)
        for (name, tmpl_value) in tmpl.items():
            if tmpl_value == False:
                continue

            # The ExternalAttribute instance has a reference to the
            # method (directly from the class, i.e. unbound so we need
            # to pass self explicitly) and any parameters to
            # it.
            attr = readattrs[name]
            value = attr.method(self, *attr.args, **attr.kwargs)

            if value is None:
                if "_remove_nulls" in tmpl and tmpl["_remove_nulls"]:
                    continue
                out[attr.name] = None
                continue

            if attr.model:
                subtmpl = tmpl_value
                if "_remove_nulls" in tmpl and "_remove_nulls" not in subtmpl:
                    subtmpl = subtmpl.copy()
                    subtmpl["_remove_nulls"] = tmpl["_remove_nulls"]
                
                if isinstance(ExtType.instance(attr.exttype), ExtList):
                    out[name] = [d.apply_template(api_version, subtmpl) for d in value]
                else:
                    out[name] = value.apply_template(api_version, subtmpl)
            else:
                out[name] = value
        self._templated[(api_version, tmplidx)] = out
        return out

    def init(self, *args, **kwargs):
        return



# NOTE! In order for @entry and @suffix to be stackable in arbitrary
# order, @entry needs to know about (and copy) the _matchers method
# attribute.
def suffix(suff, exttype, desc="", minv=0, maxv=10000):
    def decorate(decorated):
        data = dict(prefix=None, suffix=suff, exttype=exttype, desc=desc, 
                    minv=minv, maxv=maxv)

        if hasattr(decorated, "_matchers"):
            decorated._matchers.append(data)
        else:
            decorated._matchers = [data]
        return decorated
    return decorate


# NOTE! In order for @entry and @prefix to be stackable in arbitrary
# order, @entry needs to know about (and copy) the _matchers method
# attribute.
def prefix(pref, exttype, desc="", minv=0, maxv=10000):
    def decorate(decorated):
        data = dict(prefix=pref, suffix=None, exttype=exttype, desc=desc,
                    minv=minv, maxv=maxv)

        if hasattr(decorated, "_matchers"):
            decorated._matchers.append(data)
        else:
            decorated._matchers = [data]
        return decorated
    return decorate


class Match(object):
    """When searches are performed, each incoming key is mapped
    to a combination of a Match subclass method and a Manager 
    subclass method. The Manager subclass method adds to a search 
    query by adding necessary tables and returning the expression
    the Match subclass method is to work with. The Match subclass
    method then updates the query by adding the search expression.

    As an example, a 'firstname_like' search parameter might map
    to a StringMatch method .like() and a PersonManager method
    .firstname_search(). .firstname_search(query) adds some tables
    to the query, then returns 'p.fname'. .firstname_search(query, 
    searchopt) adds the condition 'p.fname LIKE searchopt'.
    """

    def _keys_for(self, api_version, name, desc):
        # [ (key, clsmeth, exttype, desc) ]
        ret = []
        prefixes = {}
        suffixes = {}

        for candname in dir(self):
            candidate = getattr(self, candname)
            if not hasattr(candidate, "_matchers"):
                continue

            for m in candidate._matchers:
                # Only one decorator in the entire class
                # (independently of which method it is on) may claim a
                # particular prefix/suffix for a particular API
                # version.

                if m["prefix"]:
                    if m["prefix"] in prefixes:
                        raise IntAPIValidationError("Two @prefix decorators (on %s and %s) both claim the prefix %s for version %d of the API" % (candidate, prefixes[m["prefix"]], m["prefix"], api_version))
                    prefixes[m["prefix"]] = candidate
                    key = m["prefix"] + "_" + name
                elif m["suffix"]:
                    if m["suffix"] in suffixes:
                        raise IntAPIValidationError("Two @suffix decorators (on %s and %s) both claim the suffix %s for version %d of the API" % (candidate, suffixes[m["suffix"]], m["suffix"], api_version))
                    suffixes[m["suffix"]] = candidate
                    key = name + "_" + m["suffix"]
                else:
                    if "" in suffixes:
                        raise IntAPIValidationError("Two @suffix decorators (on %s and %s) both claim the empty suffix for version %d of the API" % (candidate, suffixes[""], api_version))
                    suffixes[""] = candidate
                    key = name

                if m["desc"]:
                    desc = desc + "(" + m["desc"] + ")"
                    
                ret.append( (key, candidate, m["exttype"], desc) )
        return ret

    def __init__(self):
        pass


class EqualityMatchMixin(object):
    @suffix("equal", ExtString)
    @suffix("", ExtString)
    def eq(self, fun, q, expr, val):
        q.where(expr + "=" + q.var(val))

    @suffix("not_equal", ExtString)
    def neq(self, fun, q, expr, val):
        q.where(expr + "<>" + q.var(val))


class StringMatch(EqualityMatchMixin, Match):
    @suffix("maxlen", ExtInteger)
    def maxlen(self, fun, q, expr, val):
        q.where("LENGTH(" + expr + ") <= " + q.var(val))

    @suffix("like", ExtLikePattern)
    def like(self, fun, q, expr, val):
        q.where(expr + " LIKE " + q.var(val))

    @suffix("nocase_equal", ExtString)
    def nceq(self, fun, q, expr, val):
        q.where("LOWER(" + expr + ") = LOWER(" + q.var(val) + ") ")

    @suffix("nocase_not_equal", ExtString)
    def ncneq(self, fun, q, expr, val):
        q.where("LOWER(" + expr + ") <> LOWER(" + q.var(val) + ") ")


class IntegerMatch(Match):
    @prefix("max", ExtInteger)
    def max(self, fun, q, expr, val):
        q.where(expr + "<=" + q.var(val))
    
    @prefix("min", ExtInteger)
    def min(self, fun, q, expr, val):
        q.where(expr + ">=" + q.var(val))


# NOTE! In order for @entry and @search to be stackable in arbitrary
# order, @entry needs to know about (and copy) the _searches method
# attribute.
def search(name, matchcls, minv=0, maxv=10000, desc=None, manager=None):
    def decorate(decorated):
        data = dict(name=name, matchcls=matchcls, desc=desc, manager=manager)
        if hasattr(decorated, "_searches"):
            for (submin, submax, subdata) in decorated._searches:
                if submin < maxv and submax > minv:
                    raise IntAPIValidationError("Two @template directives have overlapping API versions for %s" % (decorated,))
            decorated._searches.append((minv, maxv, data))
        else:
            decorated._searches = [(minv, maxv, data)]
        return decorated
    return decorate


class _Subsearch(object):
    def __init__(self, manager_name):
        self.manager_name = manager_name

    def subsearch(self, fun, dq, expr, val):
        mgr = getattr(fun, self.manager_name)
        subq = dq.subquery(expr)
        mgr.inner_search(subq, val)

class Manager(object):
    # If name="foo_manager", then <function>.foo_manager,
    # <manager>.foo_manager and <model>.foo_manager will return a
    # function-specific manager instance of this class. The
    # name must end in "_manager".
    name = None

    # The model class that this manager creates instances of.
    manages = None

    # The table to insert search results into ("rpcc_result_string" or
    # "rpcc_result_int" depending on data type of the models ID)
    result_table = "rpcc_result_string"

    model_lookup_error = ExtLookupError

    @classmethod
    def _name(cls):
        assert cls.name.endswith("_manager")
        return cls.name

    @classmethod
    def _shortname(cls):
        return cls._name()[:-8]

    @classmethod
    def _search_type(cls, api_version):
        cls._search_lookup = {}
        for candname in dir(cls):
            candidate = getattr(cls, candname)
            if not hasattr(candidate, "_searches"):
                continue

            for (minv, maxv, srch) in candidate._searches:
                if api_version >= minv and api_version <= maxv:
                    break
            else:
                continue

            mo = srch["matchcls"]()
            for (key, meth, exttype, desc) in mo._keys_for(api_version, srch["name"], srch["desc"]):
                if key in cls._search_lookup:
                    raise ValueError("Double search key spec error for %s" % (candidate,))
                cls._search_lookup[key] = (candidate, (mo, meth), exttype, desc)

            if srch["manager"]:
                # When performing searches, the method that is item
                # two of the tuple is called. It needn't be a Match
                # method, really.
                ss = _Subsearch(srch["manager"])
                cls._search_lookup[srch["name"] + "_in"] = (candidate, (ss, ss.subsearch), _TmpReference(srch["manager"], nullable=False), desc)

        styp = ExtStruct()
        styp.from_version = api_version
        styp.to_version = api_version
        styp.name = cls._name()[:-8] + "-search-options"
        for (key, (x, x, exttype, desc)) in cls._search_lookup.items():
            styp.optional[key] = (exttype, desc)

        return styp

    def __init__(self, function, *args, **kwargs):
        self.function = function
        self.db = function.db

        # Dict of Model instances already created, indexed by Model id.
        self._model_cache = {}

        # Dict of Model-stable _Decision:s, indexed by Guard instance.
        self._decision_cache = {}

        self.init(*args, **kwargs)

    def init(self, *args, **kwargs):
        return

    def base_query(self, dq):
        """Fill a supplied empty DynamicQuery instance, to set it up to 
        select the attributes that the model expects as input.

        In the DynamicQuery, the object ID column MUST be the
        first column in the select - the first returned column is used for
        caching and for matching.        
        """
        raise NotImplementedError()

    def model(self, oid):
        """Return one instance of self.manages, created by passing the
        result of self.base_query() to the Model's constructor."""

        if oid not in self._model_cache:
            if not isinstance(oid, self.manages.id_type):
                raise ValueError("%s id must be of type %s - supplied value %s isn't" % (self.manages.__name__, self.manages.id_type, oid))
                
            dq = self.db.dynamic_query()
            self.base_query(dq)
            dq.where(dq.get_select_at(0) + "=" + dq.var(oid))
            try:
                (args,) = dq.run()
            except:
                raise self.model_lookup_error(oid)
            self._model_cache[oid] = self.manages(self, *args)
        return self._model_cache[oid]

    def models_by_result_id(self, rid):
        dq = self.db.dynamic_query()
        self.base_query(dq)
        dq.table("rpcc_result", "rpcc_result_string")
        dq.where("rpcc_result.resid = " + dq.var(rid))
        dq.where("rpcc_result.manager = " + dq.var(self._shortname()))
        dq.where(self.result_table + ".resid = " + dq.var(rid))
        dq.where(self.result_table + ".value = " + dq.get_select_at(0))
        res = []
        for args in dq.run():
            oid = args[0]
            if not oid in self._model_cache:
                self._model_cache[oid] = self.manages(self, *args)
            res.append(self._model_cache[oid])
        return res

    def __getattr__(self, attr):
        if self.name and attr == self.name + "_manager":
            return self
        elif attr.endswith("_manager"):
            setattr(self, attr, getattr(self.function, attr))
            return getattr(self, attr)
        else:
            raise AttributeError(attr)

    def new_result_set(self):
        q = "SELECT resid FROM rpcc_result WHERE expires > :now"
        for expired in self.db.get(q, now=self.function.started_at()):
            q = "DELETE FROM rpcc_result_string WHERE resid=:r"
            self.db.put(q, r=expired)
            q = "DELETE FROM rpcc_result_int WHERE resid=:r"
            self.db.put(q, r=expired)

        while 1:
            rid = random.randint(0, 1<<31)
            q = "SELECT COUNT(*) FROM rpcc_result WHERE resid=:rid"
            if self.db.get_value(q, rid=rid) == 0:
                break

        q = "INSERT INTO rpcc_result (resid, manager, expires) "
        q += "VALUES (:r, :m, :e) "
        self.db.put(q, r=rid, m=self._shortname(), e=self.function.started_at() + datetime.timedelta(hours=1))

        return rid

    def search_select(self, dq):
        raise NotImplementedError()

    def perform_search(self, opts):
        dq = self.db.dynamic_query()
        rid = self.new_result_set()
        dq.store_result("INSERT INTO " + self.result_table + " (resid, value)")
        dq.select(dq.var(rid))
        self.inner_search(dq, opts)
        dq.run()
        return rid

    def inner_search(self, dq, opts):
        self.search_select(dq)
        for (key, opt) in opts.items():
            (mymeth, (mo, matchmeth), x, x) = self._search_lookup[key]
            expr = mymeth(self, dq)
            matchmeth(self.function, dq, expr, opt)
    
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

        


    
