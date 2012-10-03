# -*- coding: utf-8 -*-
#
# Copyright (C) 2003-2011 Edgewall Software
# Copyright (C) 2003-2004 Jonas Borgström <jonas@edgewall.com>
# Copyright (C) 2004-2005 Christopher Lenz <cmlenz@gmx.de>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://trac.edgewall.org/wiki/TracLicense.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://trac.edgewall.org/log/.
#
# Author: Jonas Borgström <jonas@edgewall.com>
#         Christopher Lenz <cmlenz@gmx.de>

__all__ = ['Component', 'ExtensionPoint', 'implements', 'Interface',
           'TracError']

import logging
import threading

logger = logging.getLogger('plmanagement')

class PluginError(Exception):
    name = None

    def __str__(self):
        if self.name is not None:
            return "%s: %s" % (self.name, super(PluginError, self).__str__())
        return super(PluginError, self).__str__()

def N_(string):
    """No-op translation marker, inlined here to avoid importing from
    `trac.util`.
    """
    return string


class TracError(Exception):
    """Exception base class for errors in Trac."""

    title = N_('Trac Error')

    def __init__(self, message, title=None, show_traceback=False):
        """If message is a genshi.builder.tag object, everything up to
        the first <p> will be displayed in the red box, and everything
        after will be displayed below the red box.  If title is given,
        it will be displayed as the large header above the error
        message.
        """
        #from trac.util.translation import gettext
        Exception.__init__(self, message)
        self._message = message
        self.title = title #or gettext(self.title)
        self.show_traceback = show_traceback

    message = property(lambda self: self._message,
                       lambda self, v: setattr(self, '_message', v))

    def __unicode__(self):
        return unicode(self.message)


class Interface(object):
    """Marker base class for extension point interfaces."""


class CallebleList(list):

    def __getattribute__(self, name):
        try:
            return super(CallebleList, self).__getattribute__(name)
        except AttributeError:
            def caller(*args, **kwargs):
                for ex in sorted(self, cmp=self.__cmp):
                    func = getattr(ex, name)
                    try:
                        func(*args, **kwargs)
                    except PluginError as err:
                        err.name = ex.name
                        raise
            return caller

    def __cmp(self, a, b):
        return getattr(a, 'priority', 0) - getattr(b, 'priority', 0)


class ExtensionPoint(property):
    """Marker class for extension points in components."""

    def __init__(self, interface):
        """Create the extension point.

        :param interface: the `Interface` subclass that defines the
                          protocol for the extension point
        """
        #property.__init__(self, self.extensions)
        super(ExtensionPoint, self).__init__(self.extensions)
        self.interface = interface
        self.__doc__ = ("List of components that implement `~%s.%s`" %
                        (self.interface.__module__, self.interface.__name__))

    def extensions(self, component):
        """Return a list of components that declare to implement the
        extension point interface.
        """
        classes = ComponentMeta._registry.get(self.interface, ())
        components = [component.compmgr[cls] for cls in classes]
        return CallebleList([c for c in components if c])

    def __repr__(self):
        """Return a textual representation of the extension point."""
        return '<ExtensionPoint %s>' % self.interface.__name__


class ComponentMeta(type):
    """Meta class for components.

    Takes care of component and extension point registration.
    """
    _components = []
    _registry = {}

    def __new__(mcs, name, bases, d):
        """Create the component class."""

        new_class = type.__new__(mcs, name, bases, d)
        if name == 'Component':
            # Don't put the Component base class in the registry
            return new_class

        if d.get('abstract'):
            # Don't put abstract component classes in the registry
            return new_class

        if [i for i in ComponentMeta._components if i.__name__ == name]:
            # Do not put same components
            return new_class

        ComponentMeta._components.append(new_class)
        registry = ComponentMeta._registry
        for cls in new_class.__mro__:
            for interface in cls.__dict__.get('_implements', ()):
                classes = registry.setdefault(interface, [])
                if new_class not in classes:
                    classes.append(new_class)

        return new_class

    def __call__(cls, *args, **kwargs):
        """Return an existing instance of the component if it has
        already been activated, otherwise create a new instance.
        """
        # If this component is also the component manager, just invoke that
        if issubclass(cls, ComponentManager):
            self = cls.__new__(cls)
            self.compmgr = self
            self.__init__(*args, **kwargs)
            return self

        # The normal case where the component is not also the component manager
        compmgr = args[0]
        self = compmgr.components.get(cls)
        # Note that this check is racy, we intentionally don't use a
        # lock in order to keep things simple and avoid the risk of
        # deadlocks, as the impact of having temporarily two (or more)
        # instances for a given `cls` is negligible.
        if self is None:
            self = cls.__new__(cls)
            self.compmgr = compmgr
            compmgr.component_activated(self)
            self.__init__()
            # Only register the instance once it is fully initialized (#9418)
            compmgr.components[cls] = self
        return self


class Component(object):
    """Base class for components.

    Every component can declare what extension points it provides, as
    well as what extension points of other components it extends.
    """
    __metaclass__ = ComponentMeta

    @staticmethod
    def implements(*interfaces):
        """Can be used in the class definition of `Component`
        subclasses to declare the extension points that are extended.
        """
        import sys

        frame = sys._getframe(1)
        locals_ = frame.f_locals

        # Some sanity checks
        assert locals_ is not frame.f_globals and '__module__' in locals_, \
               'implements() can only be used in a class definition'

        locals_.setdefault('_implements', []).extend(interfaces)


implements = Component.implements


class ComponentManager(object):
    """The component manager keeps a pool of active components."""

    def __init__(self):
        """Initialize the component manager."""
        self.components = {}
        self.enabled = {}
        if isinstance(self, Component):
            self.components[self.__class__] = self

    def __contains__(self, cls):
        """Return wether the given class is in the list of active
        components."""
        return cls in self.components

    def __getitem__(self, cls):
        """Activate the component instance for the given class, or
        return the existing instance if the component has already been
        activated.
        """
        if not self.is_enabled(cls):
            return None
        component = self.components.get(cls)
        if not component:
            if cls not in ComponentMeta._components:
                raise TracError('Component "%s" not registered' % cls.__name__)
            try:
                component = cls(self)
            except TypeError, e:
                raise TracError('Unable to instantiate component %r (%s)' %
                                (cls, e))
        return component

    def is_enabled(self, cls):
        """Return whether the given component class is enabled."""
        if cls not in self.enabled:
            self.enabled[cls] = self.is_component_enabled(cls)
        return self.enabled[cls]

    def disable_component(self, component):
        """Force a component to be disabled.

        :param component: can be a class or an instance.
        """
        if not isinstance(component, type):
            component = component.__class__
        self.enabled[component] = False
        self.components[component] = None

    def component_activated(self, component):
        """Can be overridden by sub-classes so that special
        initialization for components can be provided.
        """

    def is_component_enabled(self, cls):
        """Can be overridden by sub-classes to veto the activation of
        a component.

        If this method returns `False`, the component was disabled
        explicitly.  If it returns `None`, the component was neither
        enabled nor disabled explicitly. In both cases, the component
        with the given class will not be available.
        """
        if not isinstance(cls, type):
            cls = cls.__class__
        return self.enabled.get(cls, True)
        #return True


def get_logger(name):
    return logging.getLogger(logger.name + '.' + name)


class ThreadScope(object):
    """
    Allocate for each thread its own value
    """
    def __init__(self):
        super(ThreadScope, self).__init__()
        self._val = {}

    def __th_key(self):
        th = threading.current_thread()
        key = "%s-%s" % (th.ident, th.name)
        return key

    def __getattribute__(self, key):
        try:
            return super(ThreadScope, self).__getattribute__(key)
        except AttributeError:
            th = self.__th_key()
            if th not in self._val:
                return None
            else:
                try:
                    return self._val[th].get(key)
                except KeyError:
                    raise AttributeError(key)

    def __setattr__(self, key, val):
        if key.startswith('_'):
            super(ThreadScope, self).__setattr__(key, val)
        else:
            th = self.__th_key()
            if th not in self._val:
                self._val[th] = {}
            self._val[th][key] = val

    def __delattr__(self, key):
        if key.startswith('_'):
            super(ThreadScope, self).__delattr__(key)
        else:
            try:
                th = self.__th_key()
                del self._val[th][key]
                if not self._val:
                    del self._val[th]
            except KeyError:
                pass

