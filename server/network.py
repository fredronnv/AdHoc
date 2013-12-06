#!/usr/bin/env python2.6

from rpcc.model import *
from rpcc.exttype import *


class ExtNoSuchNetworkError(ExtLookupError):
    desc = "No such network exists."


class ExtNetwork(ExtString):
    name = "network"
    desc = "ID of a DHCP network"

    def lookup(self, fun, cval):
        return fun.network_manager.get_network(cval)

    def output(self, fun, obj):
        return obj.oid


class Network(Model):
    name = "network"
    exttype = ExtNetwork
    id_type = str

    def init(self, netid):
        print "Network.init", netid
        self.oid = netid
        self.authoritative = True
        self.info = None

    @template("network", ExtNetwork)
    def get_account(self):
        return self

    @template("authoritative", ExtBoolean)
    def get_authoritative(self):
        return self.authoritative

    @template("info", ExtString)
    def get_owner(self):
        return self.info


class NetworkManager(Manager):
    name = "network_manager"
    manages = Network

    result_table = "rpcc_result_string"
    model_lookup_error = ExtNoSuchNetworkError

    def init(self):
        self._model_cache = {}

    def base_query(self, dq):
        dq.select("nw.id", "nw.authoritative", "nw.info")
        dq.table("networks nw")
        return dq

    def get_network(self, netid):
        return self.model(netid)

    def search_select(self, dq):
        dq.table("networks nw")
        dq.select("nw.id")

    @search("network", StringMatch)
    def s_net(self, dq):
        dq.table("networks nw")
        return "nw.id"
