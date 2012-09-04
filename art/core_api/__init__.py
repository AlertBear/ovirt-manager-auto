
import os
import time
import logging
from contextlib import contextmanager
from types import MethodType, FunctionType


logger = logging.getLogger('core_api')


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


def is_action(alias=None):
    def decorator(func, alias=alias):
        ActionSetType.register_test_action(alias, func)
        return func
    return decorator


class TestAction(object):
    def __init__(self, func, name, module):
        self.func = func
        self.name = name
        self.module = module

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class ActionSetType(type):
    SETS = {}
    def __new__(cls, name, bases, dct):
        if name in cls.SETS:
            new_cls = cls.SETS[name]
            new_cls.modules.add(dct['__module__'])
        new_cls = type.__new__(cls, name, bases, dct)
        if name != 'ActionSet':
            # register user's actions set
            new_cls.ACTIONS = dict()
            new_cls.modules = set([new_cls.__module__])
            cls.SETS[name] = new_cls
            logger.info("Register %s for module %s", name, new_cls.__module__)
        return new_cls

    @classmethod
    def register_test_action(cls, alias, func):
        if isinstance(func, FunctionType):
            mod = func.__module__
            if alias is None:
                alias = func.func_name
        elif isinstance(func, MethodType):
            mod = func.__self__.__module__
            if alias is None:
                alias = func.__func__.__name__
        elif callable(func):
            mod = func = func.__module__
            if alias is None:
                alias = func.__name__
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
                if alias in val.ACTIONS:
                    raise ActionColision("%s: %s <-> %s" % \
                            (alias, func, val.ACTIONS[alias]))
                val.ACTIONS[alias] = TestAction(func, alias, mod)
                break
        else:
            msg = "Can not find ActionSet for '%s' from %s" % (alias, mod)
            raise OrphanAction(msg)

    @classmethod
    def load_module(cls, module_path):
        __import__(module_path)

        for val in cls.SETS.values():
            if val.is_submodule(module_path):
                val.load_modules()

    @classmethod
    def actions(cls):
        res = {}
        for val in cls.SETS.values():
            for key, func in val.actions().items():
                if key in res:
                    raise ActionColision("%s: %s <-> %s" % (key, func, res[key]))
                res[key] = func
        return res


class ActionSet(object):
    __metaclass__ = ActionSetType
    ACTIONS = {}
    RECURSIVELY = []
    MODULES = []

    @classmethod
    def actions(cls):
        if not cls.ACTIONS:
            cls.load_modules()
        return cls.ACTIONS

    @classmethod
    def is_submodule(cls, module_path):
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

