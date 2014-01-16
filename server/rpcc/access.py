#!/usr/bin/env python

from exterror import ExtAccessDeniedError
from model import Model, Manager, Match

"""
Access control.

The base data type of RPCC access control is the _Decision class, or
rather the specific subclasses AccessGranted, AccessDenied and
DecisionReferred.

_Decisions are returned by the .check(obj, function) method of
Guard:s. The parameters are an object for which the access control is
now running, and the other is the Function instance from which the
protected call is being made.

_Decisions can be cached - they have an attribute specifying what
stability (if any) they have with the special values CacheInFunction
(if the same Function is passed, the result will always be the same),
CacheInObject (if the same object is passed, the result will always be
the same) and NeverCache (no guarantees of a future call can be made).

When _Decisions are cached, they are cached keyed by Guard
instance. When using Guards, applications must therefore ensure that
they reuse the same Guard instances if they want caching to work.

There are some standard Guard chaining classes, which combine several
Guards, returning a combined _Decision with a proper cacheability that
depends on the sub-_Decisions they are based on.

The system works according to a 'perimeter defense' model. When a
protected method's Guard has granted access, a generic pass flag is
set on the Function. When the method returns (either by a 'return' or
an unhandled exception), the flag is cleared. Calls to other protected
methods are allowed, without calling any Guards, as long as the flag
is set. This means that all calls to protected methods performed from
inside a protected method, regardless of intermediate calls to
non-protected methods, are allowed.

This model is thread-safe as long as one Function only runs in one
thread. If Functions spawn off new threads with access to the same
data structures, this won't work. On the other hand, all sorts of
other stuff will break then as well.

To set up an entry point on the perimeter, the @entry(guard) decorator
is used before a method. If, as is frequently the case, the
@entry()-decorated method is also decorated with a @template, @update,
@search, @prefix or @suffix decorator, these decorators can be stacked
in any order. 

"""


# Cacheability constants. The "level" is used when chaining - the
# result when merging two _Decisions will get the _Cacheability from
# the source where the .level is lowest.
class _Cacehability(object):
    """The level is used when chaining. When two decisions have been
    used to make a third one, the result will have the cacheability 
    that has the lowest level.

    If one decision is stable for the Function lifetime and another 
    decision is only stable for each object, a decision that is a merge 
    of these two can only be cached in the object.
    """
    level = None

    def __cmp__(self, other):
        if isinstance(other, _Cacehability):
            return cmp(self.level, other.level)
        raise TypeError("_Cacehability cannot be compared with %s" % (other,))

    __hash__ = None


class CacheInFunction(_Cacehability):
    level = 2


class CacheInObject(_Cacehability):
    level = 1


class NeverCache(_Cacehability):
    level = 0


class _Decision(object): 
    def __init__(self, cacheability=None):
        self.cacheability = cacheability

    def copy(self, cacheability=None):
        if cacheability:
            return self.__class__(cacheability)
        else:
            return self.__class__(self.cacheability)


class AccessGranted(_Decision): 
    pass


class AccessDenied(_Decision): 
    pass


class DecisionReferred(_Decision): 
    pass


class Guard(object):
    """A Guard is posted at an @entry-decorated method. On conditions
    defined in the @entry decorator definition, a Guard is called upon
    to make an access control decision. It is passed the object for 
    which the check is to be made. It is also passed the Function instance
    that started the call.

    The response from .check() must be one of AccessGranted (definitely 
    grant access), AccessDenied (definitely deny access) or 
    DecisionReferred (let someone else decide).
    """

    _instance_cache = {}

    @classmethod
    def instance(cls, other):
        try:
            if isinstance(other, Guard):
                return other
            elif issubclass(other, Guard):
                if other not in cls._instance_cache:
                    cls._instance_cache[other] = other()
                return cls._instance_cache[other]
        except:
            pass

        raise ValueError("Guard.instance() needs to be called with a Guard class or instance - %s is not" % (other,))

    def check(self, obj, function):
        raise NotImplementedError()


class AlwaysAllowGuard(Guard):
    def check(self, obj, function):
        return AccessGranted(CacheInFunction)


class NeverAllowGuard(Guard):
    def check(self, obj, function):
        return AccessDenied(CacheInFunction)


class DefaultSuperuserGuard(Guard):
    """This guard says yes if session.authuser == '#root#', don't-know
    otherwise.

    You can use authentication.SuperuserOnlyAuthenticator to allow access 
    to protected information if you have no authorization model in your 
    application."""

    def check(self, obj, function):
        if function.session.authuser == "#root#":
            return AccessGranted(CacheInFunction)
        return DecisionReferred(CacheInFunction)


class AuthRequiredGuard(Guard):
    def check(self, obj, function):
        if function.session.authuser is not None:
            return AccessGranted(CacheInFunction)
        return DecisionReferred(CacheInFunction)


class SuperuserGuardProxy(Guard):
    def check(self, obj, function):
        return Guard.instance(function.server.superuser_guard).check(obj, function)

# Chain types: 

# * First response that isn't say DecisionReferred (Postfix-style
#   chaining - first Guard that has an opinion wins). Otherwise the
#   default decision is returned.
#
# * First Guard that says Yes wins (Yes if anyone says Yes, default
#   decision otherwise).
#
# * First Guard that says No wins (No if anyone says No, default
#   decision otherwise).


class _Chain(Guard):
    """Chain multiple Guards together.

    The exact operational mode depends on .mode, which is set in 
    subclasses with better names.

    Common to all modes is that the cacheability of the result
    is set to the minimum cacheability of any decision actually used.
    A decision based only on Function-stable sub-decisions will
    also be Function-stable, regardless of whether any Guards later
    in the chain would return decisions of less cacheability - they will 
    never be reached in a subsequent check.

    If an Object-stable decision was used, however, the combined
    decision is only Object-stable.
    """
    default_decision = DecisionReferred(CacheInFunction)

    # Constants for operational mode, set in subclasses below.
    first_opinion = "o"
    first_yes = "y"
    first_no = "n"

    def __init__(self, *guards, **kwargs):
        self.guards = [Guard.instance(g) for g in guards]
        if "default_decision" in kwargs:
            self.default_decision = kwargs.pop("default_decision")
        if kwargs:
            raise ValueError("Unknown keyword arguments %s" % (kwargs.keys()))

    # Please note that the code below contains repetitions and is
    # rather ugly. But it needs to be ultra-optimized - this code path
    # is a bottleneck on ALL calls to @entry-protected methods.
    def check(self, obj, function):
        combined_cacheability = CacheInFunction

        for guard in self.guards:
            if guard in function._decision_cache:
                des = function._decision_cache[guard]
            elif guard in obj._decision_cache:
                des = function._decision_cache[guard]
            else:
                des = guard.check(obj, function)
                if des.cacheability == CacheInFunction:
                    function._decision_cache[guard] = des
                elif des.cacheability == CacheInObject:
                    obj._decision_cache[guard] = des

            if des.cacheability < combined_cacheability:
                combined_cacheability = des.cacheability

            if self.mode == self.first_opinion and (isinstance(des, AccessGranted) or isinstance(des, AccessDenied)):
                if des.cacheability == combined_cacheability:
                    return des
                else:
                    return des.copy(combined_cacheability)
            
            elif self.mode == self.first_yes and isinstance(des, AccessGranted):
                if des.cacheability == combined_cacheability:
                    return des
                else:
                    return des.copy(combined_cacheability)

            elif self.mode == self.first_no and isinstance(des, AccessDenied):
                if des.cacheability == combined_cacheability:
                    return des
                else:
                    return des.copy(combined_cacheability)

        return self.default_decision.copy(combined_cacheability)


class FirstOpinion(_Chain):
    """Chain guard where the first _Decision which is not DecisionDeferred
    is returned."""
    mode = _Chain.first_opinion


class AnyGrants(_Chain):
    """Chain guard that returns AccessGranted if any sub-guards returned
    AccessGranted, regardless of what other returned."""
    mode = _Chain.first_yes


class NoDenies(_Chain):
    """Chain guard that returns AccessDenied if any of the sub-guards
    returned AccessDenied, regardless of what the other returned."""
    mode = _Chain.first_no


# When the decorator is used, which is in when the "class" statement
# is being run, entry() is called. It returns a copy of
# checked_method_maker, where that copy also includes the "guard"
# variable's value passed to entry().
def entry(guard):
    """@entry decorator, which marks a method as access protected.

    The argument when using the @entry decorator must be a Guard instance.
    If you need to have several Guards checked, use a chain instance.

    When an @entry-decorated method is called, a copy of the actually_called 
    function is run. That copy has the 'guard' argument from the
    @entry statement bound to it.

    The actually_called() function extracts the Function. It passes the
    first argument and the Function to the Guard's .check() method.

    The response from the Guard must be a _Decision instance, with a 
    correctly set cacheability, which is used to determine whether the 
    decision can be cached in the Function, in the decorated method's 
    self, or not at all.

    If the Guard responds with an AccessGranted() instance, a flag is set
    in the Function that access has been granted, and the decorated 
    method is called. Any @entry decorators further down the call chain
    will allow access. When the decorated method returns control, either by
    a return or by an unhandled Exception, the flag is reset.
    """
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

            # Try to find a previous decision, which could be in one
            # of the decision caches. If not found, retreive a new
            # decision, and store it in a cache if the decision is
            # cacheable.

            if guard in function._decision_cache:
                decision = function._decision_cache[guard]
            elif guard in obj._decision_cache:
                decision = obj._decision_cache[guard]
            else:
                decision = guard.check(obj, function)

                if decision.cacheability == CacheInFunction:
                    function._decision_cache[guard] = decision
                elif decision.cacheability == CacheInObject:
                    obj._decision_cache[guard] = decision

            if isinstance(decision, AccessGranted):
                try:
                    function._entry_granted = True
                    return wrapped_method(obj, *args, **kwargs)
                finally:
                    function._entry_granted = False
            elif isinstance(decision, AccessDenied) or isinstance(decision, DecisionReferred):
                raise ExtAccessDeniedError(str(guard))
            else:
                raise ValueError("Rugbyboll" + str(decision))
            
        if hasattr(wrapped_method, "_update"):
            actually_called._update = wrapped_method._update
        if hasattr(wrapped_method, "_template"):
            actually_called._template = wrapped_method._template
        if hasattr(wrapped_method, "_matchers"):
            actually_called._matchers = wrapped_method._matchers
        if hasattr(wrapped_method, "_searches"):
            actually_called._searches = wrapped_method._searches
        return actually_called
    return checked_method_maker
