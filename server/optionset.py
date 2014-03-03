#!/usr/bin/env python2.6

import sys

sys.path.append("/home/viktor/AdHoc/trunk/server")
sys.path.append("/home/viktor/mysql-connector-python-1.1.5/build/lib")
import rpcc
from util import *


class ExtOptionset(rpcc.ExtInteger):
    name = "optionset"
    desc = "The ID of an optionset"

    def lookup(self, fun, cval):
        return fun.optionset_manager.model(cval)

    def output(self, fun, obj):
        return obj.oid


class ExtNoSuchOptionsetError(rpcc.ExtLookupError):
    desc = "No such optionset exists"
    
    
class ExtNoSuchOptionError(rpcc.ExtLookupError):
    desc = "No such options is defined for the api current API"


class Optionset(rpcc.Model):
    name = "optionset"
    exttype = ExtOptionset
    id_type = int
    
    def init(self, oid):
        self.oid = oid
        self.load_options()
        
    def load_options(self):
        self.options = {}

        q = "SELECT o.name, osv.value "
        q += " FROM option_base o, %(t)s_option so, optionset_%(t)sval osv "
        q += "WHERE osv.optionset=:oset "
        q += "  AND osv.%(t)s_option = so.id "
        q += "  AND so.option_base = o.id "

        strq = q % {"t": "str"}
        for (name, value) in self.db.get(strq, oset=self.oid):
            self.options[name] = value

        intq = q % {"t": "int"}
        for (name, value) in self.db.get(intq, oset=self.oid):
            self.options[name] = value

        boolq = q % {"t": "bool"}
        for (name, value) in self.db.get(boolq, oset=self.oid):
            self.options[name] = (value == 'Y')
        
        ipaddrq = q % {"t": "ipaddr"}
        for (name, value) in self.db.get(ipaddrq, oset=self.oid):
            self.options[name] = (value)

    @rpcc.template("optionset", ExtOptionset)
    def get_optionset(self):
        return self
    
    def list_options(self):
        f = []
        for typ in ["bool", "str", "int", "ipaddr"]:
            q = """SELECT ob.name FROM option_base ob, %s_option so, optionset_%sval osv
                   WHERE ob.id = so.option_base 
                       AND osv.%s_option = so.id 
                       AND osv.optionset = :optionset""" % (typ, typ, typ)
            opts = self.db.get_all(q, optionset=self.oid)
            for (key) in opts:
                f.append(key[0])
        return f        

    @rpcc.auto_template
    def get_option(self, opt):
        return self.options.get(opt, None)

    def set_option_by_name(self, name, value):
        api = self.manager.function.api.version
        (typ, optid, _name, _exttyp, _fromv, _tov, _desc) = self.optionset_manager.get_option_details_by_name(name, api)
        self.set_option(value, typ, optid)
        
    def destroy(self):
        self.optionset_manager.destroy_optionset(self)
      
    @rpcc.auto_update
    @rpcc.entry(rpcc.AuthRequiredGuard)
    def set_option(self, value, typ, optid):
        if value is None:
            q = "DELETE FROM optionset_%sval " % (typ,)
            q += "WHERE %s_option = :optid " % (typ,)
            q += "  AND optionset = :os "
            self.db.put(q, optid=optid, os=self.oid)
            return

        if typ == 'bool':
            if value:
                value = 'Y'
            else:
                value = 'N'

        q = "INSERT INTO optionset_%sval " % (typ,)
        q += "      (%s_option, optionset, value)" % (typ,)
        q += "VALUES (:optid, :os, :val) "
        try:
            self.db.put(q, optid=optid, os=self.oid, val=value)
        except rpcc.IntegrityError:
            q = "UPDATE optionset_%sval " % (typ,)
            q += "  SET value = :val "
            q += "WHERE %s_option = :optid " % (typ,)
            q += "  AND optionset = :os "
            self.db.put(q, optid=optid, os=self.oid, val=value)
                
        # Note! MySQL connector returns the number of rows CHANGED by
        # an "update" query, not the number of rows MATCHED. So trying
        # the update first and then doing the insert if 0 rows are
        # changed won't work. It did in MySQLdb, which returns the
        # number of MATCHED rows...


class NullableBoolCharMatch(rpcc.NullMatchMixin, rpcc.Match):
    @rpcc.suffix("equal", rpcc.ExtBoolean)
    @rpcc.suffix("", rpcc.ExtBoolean)
    def eq(self, fun, q, expr, val):
        if val:
            q.where(expr + " = 'Y'")
        else:
            q.where(expr + " <> 'Y'")

    @rpcc.suffix("not_equal", rpcc.ExtBoolean)
    def neq(self, fun, q, expr, val):
        if val:
            q.where(expr + " <> 'Y'")
        else:
            q.where(expr + " = 'Y'")


class NullableIpAddrMatch(rpcc.NullMatchMixin, rpcc.Match):
    @rpcc.suffix("equal", ExtIPAddress)
    @rpcc.suffix("", ExtIPAddress)
    def eq(self, fun, q, expr, val):
            q.where(expr + " = " + val)
            
    @rpcc.suffix("not_equal", ExtIPAddress)
    def neq(self, fun, q, expr, val):
            q.where(expr + " <> " + val)
        
        
class OptionsetManager(rpcc.Manager):
    name = "optionset_manager"
    manages = Optionset
    model_lookup_error = ExtNoSuchOptionsetError

    def get_optionset(self, optset):
        return self.model(optset)
    
    def get_model(self, optset):
        return self.get_optionset(optset)

    @classmethod
    def on_register(cls, srv, db):
        cls.init_class(db)
        
    @classmethod    
    def init_class(cls, db):
        matchers = {
            "bool": NullableBoolCharMatch,
            "str": rpcc.NullableStringMatch,
            "int": rpcc.NullableIntegerMatch,
            "ipaddr": NullableIpAddrMatch,
            }

        options = []

        q = "SELECT bo.id, o.name, o.info, o.from_api, o.to_api "
        q += " FROM option_base o, bool_option bo "
        q += "WHERE o.id = bo.option_base "

        for (oid, name, desc, fromv, tov) in db.get(q):
            kwargs = dict(name="option_" + name.lower(), desc=desc, from_version=fromv, 
                          to_version=tov)

            exttyp = rpcc.ExtOrNull(rpcc.ExtBoolean(**kwargs), **kwargs)
            options.append( ("bool", oid, name, exttyp, fromv, tov, desc) )

        q = "SELECT so.id, o.name, o.info, o.from_api, o.to_api, "
        q += "      so.regexp_constraint "
        q += " FROM option_base o, str_option so "
        q += "WHERE o.id = so.option_base "

        for (oid, name, desc, fromv, tov, rexp) in db.get(q):
            kwargs = dict(name="option_"+name.lower(), desc=desc, from_version=fromv, 
                          to_version=tov)
            if rexp is not None:
                kwargs["regexp"] = rexp
            exttyp = rpcc.ExtOrNull(rpcc.ExtString(**kwargs), **kwargs)
            options.append( ("str", oid, name, exttyp, fromv, tov, desc) )

        q = "SELECT io.id, o.name, o.info, o.from_api, o.to_api, "
        q += "      io.minval, io.maxval "
        q += " FROM option_base o, int_option io "
        q += "WHERE o.id = io.option_base "

        for (oid, name, desc, fromv, tov, minval, maxval) in db.get(q):
            kwargs = dict(name="option_"+name.lower(), desc=desc, from_version=fromv, 
                          to_version=tov)
            if minval is not None and maxval is not None:
                kwargs["regexp"] = rexp

            exttyp = rpcc.ExtOrNull(rpcc.ExtInteger(**kwargs), **kwargs)
            options.append( ("int", oid, name, exttyp, fromv, tov, desc) )
            
        q = "SELECT ipo.id, o.name, o.info, o.from_api, o.to_api "
        q += " FROM option_base o, ipaddr_option ipo "
        q += "WHERE o.id = ipo.option_base "

        for (oid, name, desc, fromv, tov) in db.get(q):
            kwargs = dict(name="option_"+name.lower(), desc=desc, from_version=fromv, 
                          to_version=tov)

            exttyp = rpcc.ExtOrNull(ExtIPAddress(**kwargs), **kwargs)
            options.append( ("ipaddr", oid, name, exttyp, fromv, tov, desc) )

        cls.options_dict = {}
        
        # Find highetst defined API
        maxapi = db.get_value("SELECT MAX(version) FROM rpcc_api_version")

        for (typ, optid, name, exttyp, fromv, tov, desc) in options:
            Optionset.get_option = rpcc.template(name, exttyp, minv=fromv, maxv=tov, desc=desc, default=True, kwargs=dict(opt=name))(Optionset.get_option)
            Optionset.set_option = rpcc.update(name, exttyp, minv=fromv, maxv=tov, desc=desc, kwargs=dict(typ=typ, optid=optid))(Optionset.set_option)
            #print name, matchers[typ], typ, optid
            cls.search_option = rpcc.search(name, matchers[typ], minv=fromv, maxv=tov, desc=desc, kwargs=dict(optname=name, opttyp=typ, optid=optid))(cls.search_option)
            for api in range(0, maxapi + 1):
                if api in range(fromv, tov + 1):
                    cls.options_dict[(name, api)] = (typ, optid, name, exttyp, fromv, tov, desc)
                    
    def get_option_details_by_name(self, name, api):
       
        try:
            return self.__class__.options_dict[(name, api)]
        except KeyError:
            raise ExtNoSuchOptionError("The option %s is not defined for API %d" % (name, api))

    def base_query(self, dq):
        dq.select("id")
        dq.table("optionset")

    def search_select(self, dq):
        dq.select("os.id")
        dq.table("optionset os")

    @rpcc.auto_search
    def search_option(self, dq, optname, opttyp, optid):
        tbl = "optionset_%sval" % (opttyp,)
        alias = "s_%s" % (optname,)
        var = dq.var(optid)
        optcol = "%s.%s_option" % (alias, opttyp)

        onexpr = "os.id=" + alias + ".optionset AND " + optcol + "=" + var
        dq.outer(tbl + " " + alias, onexpr)
        return alias + ".value"
    
    def create_optionset(self):
        q = """INSERT INTO optionset VALUES()"""
        id = self.db.insert("id", q) 
        return id
    
    def destroy_optionset(self, optset):
        q = """DELETE FROM optionset WHERE id=:optset"""
        self.db.put(q, optset=optset.oid)
       
    def get_optid(self, opt_name):
        optid = self.db.get("SELECT id FROM option_base WHERE name = :name", name=opt_name)
        return optid

if __name__ == '__main__':
    class MyServer(rpcc.Server):
        envvar_prefix = "OPT_"
    
    srv = MyServer("localhost", 7310)
    srv.enable_database(rpcc.MySQLDatabase)
    srv.register_manager(OptionsetManager)
    
    srv.register_manager(rpcc.NullAuthenticationManager)
    srv.register_manager(rpcc.DatabaseBackedSessionManager)
    #srv.register_manager(rpcc.EventManager)

    srv.enable_documentation()
    srv.enable_digs_and_updates()
    srv.serve_forever()
