#!/usr/bin/env python2.6

from rpcc.model import *
from rpcc.exttype import *
from rpcc.function import SessionedFunction
from option_def import ExtOptionDef, ExtOptionNotSetError, ExtOptions
from rpcc.access import *
from rpcc.database import IntegrityError
from pool import *
from dhcp_server import *


class ExtNoSuchPoolRangeError(ExtLookupError):
    desc = "No such pool_range exists."
    
    
class ExtPoolRangeAlreadyExistsError(ExtLookupError):
    desc = "The pool_range name is already in use"
    
    
class ExtPoolRangeInUseError(ExtValueError):
    desc = "The pool_range is referred to by other objects. It cannot be destroyed"
    
    
class ExtPoolRangeReversedError(ExtValueError):
    desc = "The end IP address of the range must be higher than the start address"
    
    
class ExtPoolRangeOverlapError(ExtValueError):
    decs = "The specified pool range overlaps another pool range"


class ExtIpV4Address(ExtString):
    name = "ipv4-address"
    desc = "An IPv4 address using dotted decimal representation"
    regexp = "^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"


class ExtPoolRangeName(ExtIpV4Address):
    name = "pool_range-start"
    desc = "Starting IP address of a pool range"


class ExtPoolRange(ExtPoolRangeName):
    name = "pool_range"
    desc = "A DHCP shared pool_range"

    def lookup(self, fun, cval):
        print "LOOKING UP RANGE", str(cval)
        return fun.pool_range_manager.get_pool_range(str(cval))

    def output(self, fun, obj):
        print "Outputting object", obj, obj.__dict__
        return obj.oid
    
    
class PoolRangeFunBase(SessionedFunction):  
    params = [("pool_range_start", ExtPoolRange, "Pool range start address")]
   

class PoolRangeCreate(SessionedFunction):
    extname = "pool_range_create"
    params = [("start_ip", ExtPoolRangeName, "Pool range start address"),
              ("end_ip", ExtIpV4Address, "Pool range end address"),
              ("pool", ExtPool, "Pool where the range lives"),
              ("served_by", ExtDHCPServer, "DHCP server to serve the pool range")]
    desc = "Creates a pool_range"
    returns = (ExtNull)

    def do(self):
        
        if (self.end_ip < self.start_ip):
            raise ExtPoolRangeReversedError()
        
        self.pool_range_manager.create_pool_range(self, self.start_ip, 
                                                        self.end_ip,
                                                        self.pool,
                                                        self.served_by)
        

class PoolRangeDestroy(PoolRangeFunBase):
    extname = "pool_range_destroy"
    desc = "Destroys a shared pool_range"
    returns = (ExtNull)

    def do(self):
        self.pool_range_manager.destroy_pool_range(self, self.pool_range_start)


class PoolRange(Model):
    name = "pool_range"
    exttype = ExtPoolRange
    id_type = str

    def init(self, *args, **kwargs):
        a = list(args)
        print a
        self.oid = a.pop(0)
        self.start_ip = self.oid
        self.end_ip = a.pop(0)
        self.pool = a.pop(0)
        self.served_by = a.pop(0)
        self.mtime = a.pop(0)
        self.changed_by = a.pop(0)
        self.id = a.pop(0)

    @template("start_ip", ExtPoolRange)
    def get_start_ip(self):
        return self
    
    @template("end_ip", ExtIpV4Address)
    def get_end_ip(self):
        return self.end_ip

    @template("pool", ExtPool)
    def get_pool(self):
        return self.pool_manager.get_pool(self.pool)

    @template("served_by", ExtDHCPServer)
    def get_served_by(self):
        return self.dhcp_server_manager.get_dhcp_server(self.served_by)
    
    @template("mtime", ExtDateTime)
    def get_mtime(self):
        return self.mtime
    
    @template("changed_by", ExtString)
    def get_changed_by(self):
        return self.changed_by
    
    @update("start_ip", ExtPoolRangeName)
    @entry(AuthRequiredGuard)
    def set_start_ip(self, value):
        q = "UPDATE pool_ranges SET start_ip=:value WHERE id=:id"
        self.db.put(q, id=self.id, value=value)
        self.manager.rename_pool_range(self, value)
        
    @update("end_ip", ExtIpV4Address)
    @entry(AuthRequiredGuard)
    def set_end_ip(self, value):
        q = "UPDATE pool_ranges SET end_ip=:value WHERE id=:id"
        self.db.put(q, id=self.id, value=value)

    @update("pool", ExtPool)
    @entry(AuthRequiredGuard)
    def set_pool(self, pool):
        q = "UPDATE pool_ranges SET pool=:pool WHERE start_ip=:id"
        self.db.put(q, id=self.oid, pool=pool.oid)
             
    @update("served_by", ExtDHCPServer)
    @entry(AuthRequiredGuard)
    def set_info(self, served_by):
        q = "UPDATE pool_ranges SET served_by=:served_by WHERE start_ip=:id"
        self.db.put(q, id=self.oid, served_by=served_by.oid)
        
    def check_model(self):
        q = "SELECT INET_ATON(:start_ip) > INET_ATON(:end_ip)"
        val = self.db.get_value(q, start_ip=self.start_ip, end_ip=self.end_ip)
        print "VAL=", val
        if val:
            raise ExtPoolRangeReversedError()
        self.manager.checkoverlaps(self.start_ip, self.end_ip)


class PoolRangeManager(Manager):
    name = "pool_range_manager"
    manages = PoolRange

    model_lookup_error = ExtNoSuchPoolRangeError
    
    def init(self):
        self._model_cache = {}
        
    def base_query(self, dq):
        dq.table("pool_ranges pr")
        dq.select("pr.start_ip", "pr.end_ip", "pr.pool", "pr.served_by", "pr.mtime", "pr.changed_by", "pr.id")
        return dq

    def get_pool_range(self, pool_range_name):
        print "GET_POOL_RANGE", pool_range_name
        return self.model(pool_range_name)

    def search_select(self, dq):
        dq.table("pool_ranges pr")
        dq.select("pr.start_ip")

    @search("pool_range", StringMatch)
    def s_pool_range(self, dq):
        dq.table("pool_ranges pr")
        return "pr.start_ip"
    
    @entry(AuthRequiredGuard)
    def create_pool_range(self, fun, start_ip, end_ip, pool, served_by):
        q = "INSERT INTO pool_ranges (start_ip, end_ip, pool, served_by, changed_by) VALUES (:start_ip, :end_ip, :pool, :served_by, :changed_by)"
        if end_ip < start_ip:
            raise ExtPoolRangeReversedError()
        self.checkoverlaps(start_ip, end_ip)
        try:
            self.db.put(q, start_ip=start_ip, end_ip=end_ip, pool=pool.oid, served_by=served_by.oid, changed_by=fun.session.authuser)
        except IntegrityError:
            raise ExtPoolRangeAlreadyExistsError()
            
    @entry(AuthRequiredGuard)
    def destroy_pool_range(self, fun, pool_range):
        try:
            q = "DELETE FROM pool_ranges WHERE start_ip=:start_ip LIMIT 1"
        except IntegrityError:
            raise ExtPoolRangeInUseError()
        self.db.put(q, start_ip=pool_range.oid)
         
    def rename_pool_range(self, obj, newid):
        oid = obj.oid
        obj.oid = newid
        del(self._model_cache[oid])
        self._model_cache[newid] = obj
        
    def getoverlaps(self, start_ip, end_ip):
        q = """SELECT start_ip, end_ip FROM pool_ranges WHERE
                (INET_ATON(:start_ip) BETWEEN INET_ATON(start_ip) AND INET_ATON(end_ip)) OR
                (INET_ATON(:end_ip) BETWEEN INET_ATON(start_ip) AND INET_ATON(end_ip)) OR
                (INET_ATON(start_ip) BETWEEN INET_ATON(:start_ip) AND INET_ATON(:end_ip)) OR
                (INET_ATON(end_ip) BETWEEN INET_ATON(:start_ip) AND INET_ATON(:end_ip))
                """
        overlaps = self.db.get_all(q, start_ip=start_ip, end_ip=end_ip)
        q1 = """SELECT start_ip, end_ip FROM pool_ranges"""
        ranges = self.db.get_all(q1)
        return overlaps
    
    def checkoverlaps(self, start_ip, end_ip):
        overlaps = self.getoverlaps(start_ip, end_ip)
        
        true_overlaps = []
        for overlap in overlaps:
            if overlap[0] != start_ip or overlap[1] != end_ip:
                true_overlaps.append(overlap)
        if true_overlaps:
                print "RAISING OVERLAP ERROR:", true_overlaps
                raise ExtPoolRangeOverlapError("The range would overlap the ranges: %s" % ",".join(elem[0] for elem in true_overlaps))
