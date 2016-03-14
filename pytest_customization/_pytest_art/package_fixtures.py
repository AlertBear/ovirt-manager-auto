"""
Since we use many setup_package fixtures,
and we couldn't find good replacement for that,
we decided to extend pytest-setup to exec these fixtures for us.

We can remove this customization once we got rid of all setup_package
functions.
"""
import pytest


__all__ = [
    "pytest_configure",
]


def get_entry(path):
    if not path.isdir():
        path = path.dirpath()
    e = Entry.get(path)
    if not e:
        package = path.pyimport()
        setup = getattr(package, 'setup_package', None)
        teardown = getattr(package, 'teardown_package', None)
        e = Entry(path, setup, teardown)
        Entry.allentries.add(e)
    return e


class Entry(object):
    """
    This class holds setup & teardown function per each __init__.py
    """
    allentries = set()

    @classmethod
    def get(cls, path):
        for e in cls.allentries:
            if e.path == path:
                return e
        return None

    def __init__(self, path, setup, teardown, parent=None):
        """
        :param path: path to package
        :type path: string
        :param setup: setup function
        :type setup: callable or None
        :param teardown: teardown function
        :type teardown: callable or None
        """
        super(Entry, self).__init__()
        if parent is None and str(path) != '/':
            if path.pypkgpath() != path:
                ppath = path.dirpath()
                parent = get_entry(ppath)
        self.parent = parent
        self.path = path
        self._setup = setup
        self.setup_done = False
        self._setup_exc = None
        self._teardown = teardown
        self.teardown_done = False
        self._teardown_exc = None
        self._entries = None
        self.itrefs = 0

    @property
    def entries(self):
        if self._entries is None:
            dirs = [
                Entry.get(p)
                for p in self.path.listdir(fil=lambda x: x.isdir())
            ]
            self._entries = [e for e in dirs if e is not None]
        return self._entries

    @property
    def items(self):
        allit = self.itrefs
        for e in self.entries:
            allit += e.items
        return allit

    def setup(self):
        """
        Run setup package
        """
        assert not self.setup_done
        if self._setup is None:
            self.setup_done = True
            return

        if self._setup_exc is not None:
            raise self._setup_exc
        pytest.config.hook.pytest_package_setup(entry=self)
        try:
            self._setup()
        except Exception as ex:
            self._setup_exc = ex
            raise
        self.setup_done = True

    def ensuresetup(self):
        entries = []
        parent = self
        while parent and not parent.setup_done:
            entries.append(parent)
            parent = parent.parent

        for entry in entries[::-1]:
            entry.setup()

    def ensureteardown(self):
        self.itrefs -= 1
        if self.items > 0:
            return
        entries = [self]
        parent = self.parent
        while parent and not parent.teardown_done and parent.items <= 0:
            entries.append(parent)
            parent = parent.parent

        for entry in entries:
            entry.teardown()

    def teardown(self):
        """
        Run teardown package
        """
        assert self.itrefs == 0
        assert not self.teardown_done
        if self._teardown is None:
            self.teardown_done = True
            return

        if self._teardown_exc is not None:
            raise self._teardown_exc
        try:
            self._teardown()
        except Exception as ex:
            self._teardown_exc = ex
            raise
        finally:
            pytest.config.hook.pytest_package_teardown(entry=self)
        self.teardown_done = True

    def __cmp__(self, o):
        """
        Define how to order these objects, according to 'path' attribute.
        """
        return cmp(self.path, o.path)

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self.path)

    def __repr__(self):
        return str(self)


class SetupPackage(object):
    """
    Binding to relevant pytest's interfaces, in order to execute
    setup/teardown package.
    """
    def __init__(self):
        super(SetupPackage, self).__init__()
        self.root = None

    @pytest.mark.trylast
    def pytest_collection_modifyitems(self, session, config, items):
        """
        Build entries tree
        """
        if not items:
            return
        if self.root is None:
            self.root = get_entry(items[0].fspath)
        for i in items:
            self._add_item(i)

    @pytest.mark.tryfirst
    def pytest_runtest_setup(self, item):
        """
        Look up all relevant setups for item, and excute them.
        """
        e = get_entry(item.fspath)
        e.ensuresetup()

    @pytest.mark.trylast
    def pytest_runtest_teardown(self, item, nextitem):
        """
        Look up all relevant teardowns for item, and excute them
        in case the test is leaving package.
        """
        e = get_entry(item.fspath)
        e.ensureteardown()

    def pytest_unconfigure(self, config):
        Entry.allentries.clear()

    def _add_item(self, item):
        e = get_entry(item.fspath)
        e.itrefs += 1


class FixturesLoader(object):
    """
    This class deal with loading fixtures automatically,
    after ART gets initialialized.
    I can not happen before because we don't have DS ready yet.
    """
    def __init__(self):
        super(FixturesLoader, self).__init__()
        self.fixture_modules = []

    def pytest_ignore_collect(self, path, config):
        """
        Collect all fixtures.py files to load them afterwards.
        """
        if path.basename == 'fixtures.py':
            self.fixture_modules.append(path)
            return True  # return True to skip file
        return False

    def pytest_collection_finish(self, session):
        """
        Load all fixtures.py and register them.
        """
        while self.fixture_modules:
            path = self.fixture_modules.pop()
            m = path.pyimport()
            nodeid = path.dirpath().relto(session.config.rootdir)
            if path.sep != "/":
                nodeid = nodeid.replace(path.sep, "/")
            session._fixturemanager.parsefactories(m, nodeid)


def pytest_configure(config):
    """
    Register plugin.
    """
    config.pluginmanager.register(SetupPackage())
    config.pluginmanager.register(FixturesLoader())
