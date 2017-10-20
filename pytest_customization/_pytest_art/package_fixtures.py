"""
Since we use many setup_package fixtures,
and we couldn't find good replacement for that,
we decided to extend pytest-setup to exec these fixtures for us.

We can remove this customization once we got rid of all setup_package
functions.
"""

__all__ = [
    "pytest_configure",
]


class FixturesLoader(object):
    """
    This class deal with loading fixtures automatically,
    after ART gets initialialized.
    I can not happen before because we don't have DS ready yet.
    """
    def __init__(self):
        super(FixturesLoader, self).__init__()
        self.fixture_modules = []

    def _add_fixture(self, path):
        for p in self.fixture_modules:
            if p.samefile(path):
                break
        else:
            self.fixture_modules.append(path)

    def pytest_collect_file(self, path, parent):
        """
        Collect all fixtures.py files to load them afterwards.
        """
        if path.basename == 'fixtures.py':
            self._add_fixture(path)
        else:
            new_path = path.dirpath().join('fixtures.py')
            if new_path.exists():
                self._add_fixture(new_path)

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
    config.pluginmanager.register(FixturesLoader())
