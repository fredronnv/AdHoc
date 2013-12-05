#!/usr/bin/env python2.6

"""

class Person(model.Model):
   def update_event(self, attr, old, new):
      if isinstance(old, basestring):
         self.event_manager.create("update", attribute=attr, oldstr=old, newstr=new)
      else:
         self.event_manager.create("update", attribute=attr, oldint=old, newint=new)

   @update("firstname")
   @entry(g_modify)
   def set_firstname(self, newname):
      self.event("update", attribute="firstname", old=self.firstname, new=newname)

      self.update_event("firstname", self.firstname, new)


evmgr = self.event_manager
funev = evmgr.start("a_function")
self.db.commit()

ev = evmgr.add("create", membership=13313)
evmgr.add("update", membership=13313, attribute="group", newstr='hult', parent=ev)
evmgr.add("update", membership=13313, attribute="account", newstr='hult', parent=ev)
evmgr.add("got_member", account='nisse', group='hult', membership=13313, parent=ev)

"""

import datetime

import default_type
import access

from model import Model, Manager, template, update, search, IntegerMatch, StringMatch
from access import entry
from exttype import ExtOrNull, ExtString, ExtInteger, ExtDateTime, ExtEnum


class _TEST_ViktorGuard(access.Guard):
    def check(self, obj, fun):
        if fun.session.authuser == 'viktor':
            return access.AccessGranted(access.CacheInFunction)
        return access.DecisionDeferred(access.CacheInFunction)


class Event(Model):
    name = "event"
    id_type = int
    exttype = default_type.ExtEvent

    # This is filled automatically by EventManager.on_register()
    event_type_enum = ExtEnum()
    
    def init(self, oid, typ, created, parent, **kwargs):
        self.oid = oid
        self.typ = typ
        self.created = created
        self.parent = parent
        self.other = kwargs

    @template("event", ExtInteger, default=True)
    def get_event(self):
        return self.oid

    @template("type", event_type_enum, default=True)
    def get_type(self):
        return self.typ

    @template("created", ExtDateTime)
    def get_created(self):
        return self.created

    @template("parent", ExtOrNull(ExtInteger))
    def get_parent(self):
        return self.parent

    # On server startup, all event attributes will be fetched from the
    # database, and dynamically added as @template:d methods on the
    # Event subclass.
    #
    # The following rules apply:
    #
    #   * If a method called get_<attrname> already exists in the
    #     subclass, whether decorated with a @template or not, no
    #     automatic generation will be performed for that attribute.
    #
    #   * Integer attributes will have type ExtOrNull(ExtInteger),
    #     string attributes ExtOrNull(ExtString).
    #
    #   * No guards will be set, and they will not be default.
    #
    #   * In order to override some part of the @template definition,
    #     or supply an @entry, define the get_<attrname> method 
    #     yourself. It will not be overwritten.
    #
    #   * In order to make an existing attribute non-templateable, 
    #     supply your own get_<attrname> method which does not have an 
    #     @template decorator.
    
    @template("function", ExtOrNull(default_type.ExtFunctionName))
    def get_function(self):
        return self.other.get("function", None)

    @template("params", ExtOrNull(ExtString))
    @entry(access.SuperuserProxy)
    def get_params(self):
        return self.other.get("params", None)

    @template("session", ExtOrNull(default_type.ExtSession))
    @entry(access.SuperuserProxy)
    def get_session(self):
        return self.other.get("session", None)

    @template("elapsed_ms", ExtOrNull(ExtInteger))
    @entry(access.SuperuserProxy)
    def get_elapsed(self):
        return self.other.get("elapsed", None)

    @template("result_len", ExtOrNull(ExtInteger))
    @entry(access.SuperuserProxy)
    def get_result_len(self):
        return self.other.get("result_len", None)

    @template("error", ExtOrNull(ExtString))
    @entry(access.SuperuserProxy)
    def get_error(self):
        return self.other.get("error", None)

    @template("errval", ExtOrNull(ExtString))
    @entry(access.SuperuserProxy)
    def get_errval(self):
        return self.other.get("errval", None)

    @template("where", ExtOrNull(ExtString))
    @entry(access.SuperuserProxy)
    def get_where(self):
        return self.other.get("where", None)

    @template("stack", ExtOrNull(ExtString))
    @entry(access.SuperuserProxy)
    def get_stack(self):
        return self.other.get("stack", None)


# In .start(), an EventManager writes a marker event (if needed),
# saving the ID, and creates a "call" master event.

# .add_event() adds subevents to the current master event, all events
# in the tree are really just kept in a list of lists (of lists and so
# on) in memory.

# In .stop(), the initial master event is updated with attributes such
# as elapsed time and result/error. If the call failed, only the
# events marked as "keep_on_error" are written. If a marker event was
# created, it is removed.

# The EventManager does not commit anything, the caller needs to do
# that.



class EventManager(Manager):
    name = "event_manager"
    manages = Event

    class _PendingEvent(object):
        def __init__(self, manager, type_id, attrs):
            self.manager = manager
            self.db = self.manager.db
            self.type_id = type_id
            self.children = []
            self.attrs = {}
            self.always_commit = False
            self.update(attrs)

        def append(self, child):
            if self.always_commit == False and child.always_commit == True:
                raise ValueError("Events that should always be committed cannot be children of events that should not, since that creates a conflict if the parent is not to be written")
            self.children.append(child)

        def update(self, attrs):
            for (key, val) in attrs.items():
                if key == "always_commit": 
                    self.always_commit = val
                    continue

                try:
                    (tbl, attrid) = self.manager.event_attributes[key]
                except KeyError:
                    raise ValueError("Event attribute '%s' cannot be found in the database." % (key,))
                self.attrs[key] = (tbl, attrid, val)

        def write(self, success, curtime, parent_id=None):
            if not success and not self.always_commit:
                return

            q = "INSERT INTO rpcc_event (typ, created, parent) "
            q += " VALUES (:t, :c, :p)"
            myid = self.db.insert("id", q, t=self.type_id, c=curtime, 
                                  p=parent_id)

            for (tbl, attrid, val) in self.attrs.values():
                q = "INSERT INTO %s (event, attr, value) VALUES (:e, :a, :v)" % (tbl,)
                self.db.put(q, e=myid, a=attrid, v=val)
            
            for child in self.children:
                child.write(success, curtime, myid)

    def init(self, *args, **kwargs):
        self.master_event = None
        self.marker_id = None

    @classmethod
    def on_register(cls, srv, db):
        # In order to write events, we need to know the integer ID of
        # each event type. Fetch all event attribute types and their
        # ID:s and store them.
        #
        # We also want the ExtEnum shown in documentation to have the
        # correct values - fill it dynamically.

        cls.event_types = {}
        q = "SELECT id, name FROM rpcc_event_type"
        for (tid, name) in db.get(q):
            cls.event_types[name] = tid
            cls.manages.event_type_enum.values.append(name)

        # In order to write event attributes to the correct table, we
        # need to know what type and id they have.
        cls.event_attributes = {}
        q = "SELECT id, name FROM rpcc_event_str_attr"
        for (aid, name) in db.get(q):
            cls.event_attributes[name] = ("rpcc_event_str", aid)
        q = "SELECT id, name FROM rpcc_event_int_attr"
        for (aid, name) in db.get(q):
            if name in cls.event_attributes:
                raise ValueError("Attribute %s is both a string and an integer attribute according to the database, which is not allowed" % (name,))
            cls.event_attributes[name] = ("rpcc_event_int", aid)

        # Create @template-decorated get_<attrname> methods on the
        # Event subclass for all event attribute types found in the
        # database where the Event subclass does not already have
        # an attribute called "get_" + attrname.

        # HERE BE DRAGONS!
        def new_getter(attr, typ):
            """Create a new 'method', called get_<attr>, wrap it in a
            @template decorator, and return it.

            The body of _get(self) is what is actually called in
            an Event instance, so 'self' is the Event.
            """

            def _get(self):
                return getattr(self, "other").get(attr, None)
            _get.__name__ = "get_" + attr
            _get.__doc__ = "auto-generated getter for %s" % (attr,)
            return template(attr, typ)(_get)

        for (name, (tbl, id)) in cls.event_attributes.items():
            if hasattr(cls.manages, "get_" + name):
                continue
            
            if tbl == 'rpcc_event_str':
                typ = ExtOrNull(ExtString)
            elif tbl == 'rpcc_event_int':
                typ = ExtOrNull(ExtInteger)
            else:
                raise ValueError()

            # Set the Event subclass' get_<attr> attribute to a
            # dynamically created and @template-wrapped function.
            setattr(cls.manages, "get_" + name, new_getter(name, typ))

        def new_searcher(attr, tbl, attrid):
            def _search(self, dq):
                alias = "ss_" + attr
                dq.outer("%(t)s %(a)s", "(e.id=%(a)s.event AND %(a)s.attr=%(i)d)" % {'t': tbl, 'a': alias, 'o': attrid})
                return alias + ".value"
            _search.__name__ = "search_" + attr
            _search.__doc__ = "auto-generated searcher for %s" % (attr,)
            if tbl == 'rpcc_event_str':
                return search(attr, StringMatch)(_search)
            elif tbl == 'rpcc_event_int':
                return search(attr, IntegerMatch)(_search)
            else:
                raise ValueError()

        for (attr, (tbl, attrid)) in cls.event_attributes.items():
            if cls._has_search_attr(attr):
                continue

            if hasattr(cls, "search_" + attr):
                continue

            setattr(cls, "search_" + attr, new_searcher(attr, tbl, attrid))


    def base_query(self, dq):
        dq.select("ev.id")
        dq.select("evt.name", "ev.created", "ev.parent")
        dq.table("rpcc_event ev")
        dq.table("rpcc_event_type evt")
        dq.where("evt.id = ev.typ")

    def kwargs_for_model(self, oid):
        ret = {}

        dq = self.db.dynamic_query()
        dq.select("evsa.name", "evs.value")
        dq.table("rpcc_event_str evs")
        dq.table("rpcc_event_str_attr evsa")
        dq.where("evs.attr = evsa.id")
        dq.where("evs.event = " + dq.var(oid))
        for (name, val) in dq.run():
            ret[name] = val
        
        dq = self.db.dynamic_query()
        dq.select("evia.name", "evi.value")
        dq.table("rpcc_event_int evi")
        dq.table("rpcc_event_int_attr evia")
        dq.where("evi.attr = evia.id")
        dq.where("evi.event = " + dq.var(oid))
        for (name, val) in dq.run():
            ret[name] = val
        
        return ret

    def kwargs_for_result(self, rid):
        ret = {}

        dq = self.db.dynamic_query()
        dq.select("es.event", "sa.name", "es.value")
        dq.table("rpcc_event_str es")
        dq.table("rpcc_event_str_attr sa")
        dq.table("rpcc_result r", self.result_table() + " rv")
        dq.where("r.resid = " + dq.var(rid))
        dq.where("r.manager = " + dq.var(self._shortname()))
        dq.where("rv.resid = r.resid")
        dq.where("rv.value = es.event")
        dq.where("es.attr = sa.id")
        for (evid, attr, val) in dq.run():
            if evid not in ret:
                ret[evid] = {}
            ret[evid][attr] = val
            
        dq = self.db.dynamic_query()
        dq.select("es.event", "sa.name", "es.value")
        dq.table("rpcc_event_int es")
        dq.table("rpcc_event_int_attr sa")
        dq.table("rpcc_result r", self.result_table() + " rv")
        dq.where("r.resid = " + dq.var(rid))
        dq.where("r.manager = " + dq.var(self._shortname()))
        dq.where("rv.resid = r.resid")
        dq.where("rv.value = es.event")
        dq.where("es.attr = sa.id")
        for (evid, attr, val) in dq.run():
            if evid not in ret:
                ret[evid] = {}
            ret[evid][attr] = val
            
        return ret

    def start(self, master_type, **master_attrs):
        if self.master_event is not None:
            raise ValueError("EventManager.start() was called twice, without any EventManager.stop() between the calls.")
        
        a = master_attrs.copy()
        a["always_commit"] = True

        self.master_event = self._PendingEvent(self, self.event_types[master_type], a)
        
    def create_marker(self):
        # Please note: The calling code MUST call .commit() on the
        # shared database link after this call completes, before any
        # subsequent operations.

        q = "INSERT INTO rpcc_event (typ, created) "
        q += " VALUES (:tid, :now) "
        self.marker_id = self.db.insert("id", q, 
                                        tid=self.event_types["marker"], 
                                        now=self.function.started_at())

    def add(self, typ, **attrs):
        attrs = attrs.copy()
        parent = attrs.pop("parent", None)
        
        ev = self._PendingEvent(self, self.event_types[typ], attrs)

        if parent:
            parent.append(ev)
        else:
            self.master_event.append(ev)

    def stop(self, success, **master_attrs):
        """Called to finish a call, writing events and removing possible 
        marker events.

        If <success> is True, the master event and all its subevents
        are written. If it is False, then only the master event and
        the subevents which have 'always_commit' set to True are written.

        The master_attrs dictionary is used to update the master events'
        attributes before it is written.

        Please note: this method needs to be followed by a .commit()
        on the shared database link. Updates that needs to be rolled
        back must be rolled back before calling this method.
        """

        if self.marker_id:
            q = "DELETE FROM rpcc_event WHERE id=:evid"
            self.db.put(q, evid=self.marker_id)

        if self.master_event:
            if master_attrs:
                self.master_event.update(master_attrs)

            self.master_event.write(success, datetime.datetime.now())
        else:
            print "EventManager.stop(): not .start()ed"

    def search_select(self, dq):
        dq.select("e.id")
        dq.table("rpcc_event e")

    @search("event", IntegerMatch)
    def s_event(self, dq):
        return "e.id"

    @search("type", StringMatch)
    def s_type(self, dq):
        dq.table("rpcc_event_type et")
        dq.where("e.typ = et.id")
        return "et.name"

    @search("function", StringMatch)
    def s_function(self, dq):
        (tbl, attrid) = self.event_attributes["function"]
        dq.outer("rpcc_event_str es1", "(e.id=es1.event AND es1.attr=%d)" % (attrid,))
        return "es1.value"

