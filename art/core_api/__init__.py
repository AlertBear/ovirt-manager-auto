
import os
import sys
import time
import logging
from contextlib import contextmanager
from types import MethodType, FunctionType
from configobj import ConfigObj
import art


logger = logging.getLogger('core_api')

RELATIVE_CACHE_PATH = os.path.join('conf', 'actions.conf')

@contextmanager
def measure_time(): # should be some appropiate params
    '''
    Context manager to log request response time
    '''
    from art.test_handler.settings import initPlmanager
    plmanager = initPlmanager()
    plmanager.time_measurement.on_start_measure()
    try:
        st = time.clock()
        yield
    finally:
        responseTime = time.clock() - st
        plmanager.time_measurement.on_stop_measure(responseTime)
        logger.debug("Request response time: %0.3f" % (responseTime))


class ActionDiscoveryError(Exception):
    pass


class ActionColision(ActionDiscoveryError):
    pass


class OrphanAction(ActionDiscoveryError):
    pass


def is_action(alias=None, module=None, id_name=None):
    """
    Decorator which is dedicated to mark function as test_action
    """
    if module is None:
        f = sys._getframe(1)
        module = f.f_globals.get('__name__', None)
    def decorator(func, alias=alias, module=module, id_name=id_name):
        if id_name is not None:
            func.__id_name = id_name
        ActionSetType.register_test_action(alias, func, module)
        return func
    return decorator


class TestAction(object):
    """
    Class encapsulates test_actions, in order to generalize access to
    different types of functions (function, method, callable_object)
    """
    def __init__(self, func, name, module):
        """
        C'tor
        Parameters:
         * func - callable object
         * name - alias of function
         * module - module path to that function
        """
        self._func = func
        self.name = name
        self.module = module

    def real_func_name(self):
        """
        Retrieves real name of function (name as it was declared)
        """
        if isinstance(self._func, FunctionType):
            name = self._func.func_name
        elif isinstance(self._func, MethodType):
            name = self._func.__func__.__name__
        elif callable(self._func):
            #name = self._func.__class__.__name__
            # NOTE: this is hack due to callable classes
            name = getattr(self._func, '__id_name', None)
            if not name:
                name = self.name
        else:
            raise ActionDiscoveryError("%s: %s is not callable" % (func, type(func)))
        return name

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)

    def __str__(self):
        func_name = self.real_func_name()
        return "%s.%s" % (self.module, func_name)

    def __eq__(self, obj):
        return obj.module == self.module and obj.name == self.name

    def __ne__(self, obj):
        return not self.__eq__(obj)


class LazyTestAction(TestAction):
    """
    Extends TestAction to be able to import test_action when it should be
    executed.
    """
    def __call__(self, *args, **kwargs):
        if isinstance(self._func, basestring):
            m = __import__(self.module, fromlist=[self._func])
            self._func = getattr(m, self._func)
        return super(LazyTestAction, self).__call__(*args, **kwargs)

    def __str__(self):
        if isinstance(self._func, basestring):
            return "%s.%s" % (self.module, self._func)
        return super(LazyTestAction, self).__str__()


class ActionSetType(type):
    """
    Type of ActionsSet, it is responsible for ActionSet's registration.
    """
    SETS = {}
    CACHE_PATH = os.path.join(os.path.dirname(art.__file__), RELATIVE_CACHE_PATH)
    CACHE = ConfigObj(infile=CACHE_PATH)

    def __new__(cls, name, bases, dct):
        if name in cls.SETS: # ActionSet already registered, just add new module path
            new_cls = cls.SETS[name]
            new_cls.modules.add(dct['__module__'])
        else:
            new_cls = type.__new__(cls, name, bases, dct)
            if name != 'ActionSet':
                # register user's actions set
                new_cls.ACTIONS = dict()
                new_cls.modules = set([new_cls.__module__])
                cls.SETS[name] = new_cls
        if name != 'ActionSet':
            logger.info('Registering %s for %s modules', name, new_cls.modules)
        return new_cls

    @classmethod
    def reset_cache(cls):
        """
        Resets action_cache
        """
        cls.CACHE.clear()

    @classmethod
    def register_test_action(cls, alias, func, mod):
        """
        Assigns test_action to appropiate ActionSet
        Parameters:
         * alias - name of test_action
         * func - test_action
         * mod - module path to test_action
        """
        if isinstance(func, FunctionType):
            mod = mod or func.__module__
            alias = alias or func.func_name
        elif isinstance(func, MethodType):
            mod = mod or func.__self__.__module__
            alias = alias or func.__func__.__name__
        elif callable(func):
            mod = mod or func.__module__
            alias = alias or func.__class__.__name__
        else:
            raise ActionDiscoveryError(\
                    "%s: %s is not callable" % (alias, func))

        try:
            cls._assign_test_action(mod, alias, func)
        except OrphanAction: # try to find ActionSet on its module_path
            sub_mod = []
            for part in mod.split('.'):
                sub_mod.append(part)
                mod_path = '.'.join(sub_mod)
                __import__(mod_path)
            cls._assign_test_action(mod, alias, func)

    @classmethod
    def _assign_test_action(cls, mod, alias, func):
        for val in cls.SETS.values():
            if val.is_submodule(mod):
                ta = TestAction(func, alias, mod)
                if alias in val.ACTIONS:
                    if not isinstance(val.ACTIONS[alias], LazyTestAction)\
                            and ta != val.ACTIONS[alias]:
                        raise ActionColision("%s: %s <-> %s" % \
                                (alias, func, val.ACTIONS[alias]))
                val.ACTIONS[alias] = ta
                break
        else:
            for name, set_ in cls.SETS.items():
                logger.info("%s collects actions from %s modules", name, set_.modules)
            msg = "Can not find ActionSet for '%s' from %s" % (alias, mod)
            raise OrphanAction(msg)

    @classmethod
    def load_module(cls, module_path):
        """
        Loads trigger loading procedure for all ActionSets which resides on
        top of passed module
        Parameters:
         * module_path - path to module
        """
        __import__(module_path)

        for val in cls.SETS.values():
            if val.is_submodule(module_path):
                val.load_modules()

    @classmethod
    def actions(cls):
        """
        Returns all collected test_actions from all ActionSets
        """
        res = {}
        for val in cls.SETS.values():
            for key, func in val.actions().items():
                if key in res:
                    raise ActionColision("%s: %s <-> %s" % (key, func, res[key]))
                res[key] = func
        return res


class ActionSet(object):
    """
    Base class of ActionSets
    """
    __metaclass__ = ActionSetType
    ACTIONS = {}
    RECURSIVELY = []
    MODULES = []

    @classmethod
    def actions(cls):
        """
        Returns all collected test_actions from this ActionSet
        """
        if not cls.ACTIONS:
            cls.load_modules()
        if cls.__name__ not in ActionSetType.CACHE:
            ActionSetType.CACHE[cls.__name__] = {}
        ActionSetType.CACHE[cls.__name__].update(cls.ACTIONS)
        with open(ActionSetType.CACHE_PATH, 'w') as fh:
            ActionSetType.CACHE.write(fh)
        return cls.ACTIONS

    @classmethod
    def is_submodule(cls, module_path):
        """
        Returns True when module_path is submodule of this ActionSet
        Parameters:
         * module_path - path to module
        """
        for mod in cls.modules:
            if module_path.startswith(mod):
                return True
        return False

    @classmethod
    def _import_module(cls, mod):
        try:
            pack, it = mod.rsplit('.', 1)
        except ValueError:
            it = mod
            pack = mod
        m = __import__(pack, fromlist=[it])
        mod = mod.split('.')
        if len(mod) > 1:
            m = getattr(m, mod[-1])
        return m

    @classmethod
    def load_modules(cls):
        """
        Goes over all modules from MODULES and RECURSIVELY lists and loads them
        """
        if ActionSetType.CACHE.get(cls.__name__, {}):
            for name, value in ActionSetType.CACHE[cls.__name__].items():
                module = value.rsplit('.', 1)
                func = module[-1]
                if len(module) > 1:
                    module = module[0]
                else:
                    module = ''
                cls.ACTIONS[name] = LazyTestAction(func, name, module)
            return
        modules = set(cls.MODULES)
        for mod in set(cls.RECURSIVELY):
            mod = cls._import_module(mod)
            path = os.path.dirname(mod.__file__)
            for root, dirs, files in os.walk(path):
                for fol in dirs[:]:
                    if fol.startswith('.'):
                        dirs.remove(fol)
                _root = [x for x in root[len(path):].split(os.sep) if x]
                for name in files:
                    if not name.endswith('.py'):
                        continue
                    name = name[:-3]
                    if name in ('__init__', '__main__'):
                        continue
                    m_path = [mod.__name__]
                    m_path.extend(_root)
                    m_path.append(name)
                    modules.add('.'.join(m_path))

        for mod in modules:
            __import__(mod)
        logger.debug("Loaded actions from %s: %s", cls.__name__, cls.ACTIONS)
        logger.info("Loaded %s test actions from package '%s'", \
                len(cls.ACTIONS), cls.__name__)

