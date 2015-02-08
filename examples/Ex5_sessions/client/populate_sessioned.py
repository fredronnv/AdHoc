#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

from rpcc_client import *
from populate_unsessioned import createperson


if __name__ == "__main__":
    proxy=RPCC("http://localhost:12122", 0, attrdicts=True)

    createperson(proxy, "nissehul", "Nisse","Hult", 46)
    createperson(proxy, "nilshult", "Nils","Hult", 5)
    createperson(proxy, "barryo", "Barack","Obama", 53)
    createperson(proxy, "arnie","Arnold","Schwarzenegger", 63)
