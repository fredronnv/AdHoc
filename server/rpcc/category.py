class FunctionCategory(object):
    """Subclasses of this class are used to identify functions that
    are somehow related.

    Used to auto-generate links in the HTML documentation's "See also"
    section.

    It is an FunctionCategory object's responsibility to determine
    which TypedFunctions belong to it. ExtTypedFunctions have a
    .categories attribute which can assist the category in this
    decision.

    One instance of every registered FunctionCategory subclass will
    be created for every API version the category is visible in
    (determined through it's .from_version and .to_version
    attributes). Every such instance will have all RPCTypedFunction:s
    available in the same API version passed to its .contains()
    method.

    The RPCAPI object will keep track of the mappings between
    categories and functions.
    """

    # name is used for the <:category:name:> include tag. Can be for
    # example "group" or "search".
    name = ''

    # desc is shown on the webpage. Can be for example "Functions working
    # with groups" or "Functions used for searching".
    desc = ''

    from_version = 0
    to_version = 10000

    def __init__(self, api):
        self.api = api
        self.server = api.server

    @classmethod
    def get_public_name(cls):
        return cls.name

    def match(self, funclass):
        return False

    def contains(self, funclass):
        if hasattr(funclass, 'categories'):
            if self.__class__ in funclass.categories:
                return True
        return self.match(funclass)
