#!/usr/bin/env python2.6

import sys

sys.path.append("/home/viktor/AdHoc/trunk/server")
sys.path.append("/home/viktor/mysql-connector-python-1.1.5/build/lib")
import rpcc

class ExtOptionset(rpcc.ExtInteger):
    name = "optionset"
    desc = "The ID of an optionset"

    def lookup(self, fun, cval):
        return fun.optionset_manager.model(cval)

    def output(self, fun, obj):
        return obj.oid

class ExtNoSuchOptionsetError(rpcc.ExtLookupError):
    desc = "No such optionset exists"

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

    @rpcc.template("optionset", ExtOptionset)
    def get_optionset(self):
        return self

    @rpcc.auto_template
    def get_option(self, opt):
        return self.options.get(opt, None)

    @rpcc.auto_update
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

        
class OptionsetManager(rpcc.Manager):
    name = "optionset_manager"
    manages = Optionset
    model_lookup_error = ExtNoSuchOptionsetError

    @classmethod
    def on_register(cls, srv, db):
        matchers = {
            "bool": NullableBoolCharMatch,
            "str": rpcc.NullableStringMatch,
            "int": rpcc.NullableIntegerMatch
            }

        options = []

        q = "SELECT bo.id, o.name, o.description, o.from_api, o.to_api "
        q += " FROM option_base o, bool_option bo "
        q += "WHERE o.id = bo.option_base "

        for (oid, name, desc, fromv, tov) in db.get(q):
            kwargs = dict(name=name, desc=desc, from_version=fromv, 
                          to_version=tov)

            exttyp = rpcc.ExtOrNull(rpcc.ExtBoolean(**kwargs))
            options.append( ("bool", oid, name, exttyp, fromv, tov) )

        q = "SELECT so.id, o.name, o.description, o.from_api, o.to_api, "
        q += "      so.regexp_constraint "
        q += " FROM option_base o, str_option so "
        q += "WHERE o.id = so.option_base "

        for (oid, name, desc, fromv, tov, rexp) in db.get(q):
            kwargs = dict(name=name, desc=desc, from_version=fromv, 
                          to_version=tov)
            if rexp is not None:
                kwargs["regexp"] = rexp

            exttyp = rpcc.ExtOrNull(rpcc.ExtString(**kwargs))
            options.append( ("str", oid, name, exttyp, fromv, tov) )

        q = "SELECT io.id, o.name, o.description, o.from_api, o.to_api, "
        q += "      io.minval, io.maxval "
        q += " FROM option_base o, int_option io "
        q += "WHERE o.id = io.option_base "

        for (oid, name, desc, fromv, tov, minval, maxval) in db.get(q):
            kwargs = dict(name=name, desc=desc, from_version=fromv, 
                          to_version=tov)
            if minval is not None and maxval is not None:
                kwargs["regexp"] = rexp

            exttyp = rpcc.ExtOrNull(rpcc.ExtInteger(**kwargs))
            options.append( ("int", oid, name, exttyp, fromv, tov) )

        for (typ, optid, name, exttyp, fromv, tov) in options:
            Optionset.get_option = rpcc.template(name, exttyp, minv=fromv, maxv=tov, kwargs=dict(opt=name))(Optionset.get_option)
            Optionset.set_option = rpcc.update(name, exttyp, minv=fromv, maxv=tov, kwargs=dict(typ=typ, optid=optid))(Optionset.set_option)
            print name, matchers[typ], typ, optid
            cls.search_option = rpcc.search(name, matchers[typ], minv=fromv, maxv=tov, kwargs=dict(optname=name, opttyp=typ, optid=optid))(cls.search_option)

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
