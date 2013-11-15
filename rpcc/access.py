
from exterror import ExtAccessError

"""

"""

class BorderAccess(object):
    """Class representing one particular border access control for a 
    Function.

    Border-checks are done when a Function is called. They are by 
    necessity very broad, mostly of the type 'only authenticated 
    users'. For any serious access control tasks you instead use @guard:s, 
    which can guard access to individual attributes on individual objects.

    Functions will check with all BorderAccess classes registered
    with them, and if one of them says yes, access is allowed.

    BorderAccess classes do not retain state between calls, and
    the checks are therefore done in class methods.
    """

    # The name and description visible in external documentation.
    name = ''
    desc = ''

    @classmethod
     def delegate(cls, function)
         """Delegate decision to another Access class."""
         cls.check(function)

    @classmethod
    def check(cls, function):
        raise ExtAccessError("Access denied")

class Privilege(object):
    """A Privilege represents some form o privilege that a logged in
    user can have. Whenever the session.authuser attribute is set,
    the SessionStore also gets the option of setting session.privileges
    to a set of Privilege instances.

    There really are no attributes to set by default - the presence of 
    the class or an instance of it in the set session.privileges is 
    adequate.
    """

    pass

###
# Method access control
#
# Method access control is performed using the @entry() decorator. 
#
# Each method decorated by @entry is a possible entry point into the
# data model, and is guarded by one Guard. When a call is made to such
# a method, the Guard determines if access is to be allowed.
#
# Once "inside" the data model, no further checks are made - calling
# one @entry-decorated method from inside another does not perform an
# additional access check on the inner one.
###

class _Cacehability(object):
    pass

class CacheInFunction(_Cacehability):
    pass

class CacheInObject(_Cacehability):
    pass

class NeverCache(_Cacehability):
    pass


class _Decision(object): 
    def __init__(self, cache=None):
        self.cache = cache

    @classmethod
    def instance(cls, other, cache_override=None):
        if isinstance(other, _Decision):
            if cache_override and _Decision.cache != cache:
                ret = other.__class__(cache_override)
            else:
                ret = other
        else:
            if cache_override:
                ret = other(cache_override)
            else:
                ret = other()

        ret.cache = cache
        return ret

class AccessGranted(_Decision): 
    pass

class AccessDenied(_Decision): 
    pass

class AccessReferred(_Decision): 
    pass

class Guard(object):
    """A Guard is posted at an @entry-decorated method. On conditions
    defined in the @entry decorator definition, a Guard is called upon
    to make an access control decision. It is passed the object for 
    which the check is to be made. It is also passed the session of
    the function, since it will almost always want to use that anyways.

    The response from .check() must be AccessGranted (definitely grant 
    access), AccessDenied (definitely deny access) or DecisionReferred 
    (let someone else decide).
    """

    @classmethod
    def instance(cls, other):
        try:
            if isinstance(other, Guard):
                return other
            elif issubclass(other, Guard):
                return other()
        except:
            pass

        raise ValueError("Guard.instance() needs to be called with a Guard class or instance - %s is not" % (other,))

    def check(self, obj, function):
        raise NotImplementedError()


class PrivilegeGuard(Guard):
    """A Guard, instantiated with a single Privilege. If the session's
    .privileges set contains the Privilege, the Guard answers AccessGranted.
    Otherwise it answers self.default_decision (AccessReferred if not 
    overriden).
    """

    priv = None
    default_decision = AccessReferred(CacheInFunction)

    def __init__(self, priv=None, default=None):
        if priv:
            self.priv = priv
        if default:
            self.default_decision = default

    def check(self, obj, function, *args, **kwargs):
        if self.priv in function.session.privileges:
            return AccessGranted(CacheInFunction)
        else:
            return self.default_decision

class AlwaysAllowGuard(Guard):
    def check(self, obj, function, *args, **kwargs):
        return AccessGranted(CacheInFunction)

class Chain(Guard):
    """Chain multiple Guards together.

    Chained Guards are asked in turn, and the first response which is not 
    AccessReferred is returned.

    If all guards return AccessReferred, self.default_decision is returned.

    """
    default_decision = AccessReferred(NeverCache)

    def __init__(self, *guards, default=None):
        self.guards = [Guard.instance(g) for g in guards]
        if default:
            self.default_decision = default

    def check(self, obj, function, *args, **kwargs):
        cacheability = None
        for guard in self.guards:
            decision = None
            if args or kwargs:
                # With arguments, the response cannot be cached.
                decision = guard.check(obj, fun, *args, **kwargs)
            else:
                if self in function._guard_decision_cache:
                    decision = function._guard_decision_cache[self]
                elif self in obj._guard_decision_cache:
                    decision = obj._guard_decision_cache[self]
                else:
                    decision = guard.check(obj, fun, *args, **kwargs)
                    if decision.cache == CacheInFunction:
                        function._guard_decision_cache[self] = decision
                    elif decision.cache == CacheInObject:
                        obj._guard_decision_cache[self] = decision

            if decision.cache == None or decision.cache == NeverCache:
                cacheability = NeverCache

            elif decision.cache == CacheInObject and cacheability == CacheInFunction:
                cacheability = CacheInObject
            elif decision.cache == CacheInFunction and cacheability is None:
                cacheability = CacheInFunction
            else:
                # should not happen
                raise ValueError()

            if decision != AccessReferred:
                return _Decision.instance(decision, cacheability)

        return AccessReferred(cacheability or NeverCache)


# When the decorator is used, which is in when the "class" statement
# is being run, entry() is called. It returns a copy of
# checked_method_maker, where that copy also includes the "guard"
# variable's value passed to entry().

# This copy is then called and given the method that's being decorated
# as its only argument. It returns a copy of actually_called where
# wrapped_method is defined and contains a reference to the decorated
# method.

# On method call, the copy of actually_called is what is being
# executed. That copy contains (and can use) both "guard" and
# wrapped_method. On execution, the arguments to actually_called are
# the arguments to the method - and since this is a method call, the
# first parameter will be "self" of the instance.

# The actually_called copy performs the access control, then calls
# wrapped_method and returns the return value from it.

# Notes about optimization (which actually matters in this function): 
# 
# * isinstance(x, Guard) 
#   hasattr(x, "check")
#   try: x.check() except AttributeError: 
#
#   are equally fast if the respective statement is true. But when
#   false, the latter two has to search the entire inheritance chain,
#   and are therefore slower if the statement is false (hasattr 2x
#   slower, try/except 5x slower).
#
# * if x not in cache
#   try: dec = cache[x] except: cache[x] = ...
#
#   are also equally fast on cache hit, but on cache miss the
#   try/except is 7x slower.

# check_args and check_kwargs are passed to Guard.check. A Chain guard
# passes them to all its subguards, so they all need to accept these
# arguments and know what to do with them.

def entry(guard, *check_args, **check_kwargs):
    guard = Guard.instance(guard)

    def checked_method_maker(wrapped_method):
        def actually_called(obj, *args, **kwargs):
            if isinstance(obj, Model):
                function = obj.function
            elif isinstance(obj, Manager):
                function = obj.function
            elif isinstance(obj, Match):
                function = args[0]
            else:
                function = obj.get_entry_function()

            if function._entry_granted:
                return wrapped_method(obj, *args, **kwargs)

            decision = guard.check(obj, function, *check_args, **check_kwargs)
                
            ### Guard per-object caching?
            if decision == Yes:
                try:
                    old_bypass = fun.bypass_guards
                    fun.bypass_guards = set_bypass
                    return wrapped_method(obj, *args, **kwargs)
                finally:
                    fun.bypass_guards = old_bypass
            elif decision in [No, Pass]:
                raise PDBInadequatePrivilegesError("Checked: " + ", ".join(fun.checked_privs))
            else:
                raise ValueError("Rugbyboll" + str(decision))
        return actually_called
    return checked_method_maker



