"""
This plugin run parametrized tests with storage matrix

USAGE:
You can decorate class or base class with @storage decorator as is in example
bellow:

# All storage types available that test can run with
@storages(('nfs', 'iscsi')) # or @storages(('N/A',)) if it's not applicable
@pytest.mark.usefixtures('storage') # this is not needed in function
class BaseTestCase(object):
    pass

You can also see how it is used it in art/unittest_lib/common.py file.

It is also possible to use some other pytest.mark which can be related to
specific storage. (e.g.  for NFS storage you want to have different polarion ID
than for Glusterfs storage). You can follow example below, to see how decorator
should look like:

@storages(
    (
        pytest.param(config.STORAGE_TYPE_NFS, marks=polarion("RHEVM-18289")),
        pytest.param(
            config.STORAGE_TYPE_GLUSTER, marks=polarion("RHEVM-21589")
        ),
    )
)

If you have specified class members 'storages' like it is in example bellow, it
will also work, because this plugin supports backward compatibility:

class TestClass(BaseTestCase):
    # it has higher priority than decorator @storages(('nfs',))
    storages = set(['nfs', 'iscsi'])

It is possible overwrite also storages only for method inside class.


class TestClass(BaseTestCase):
    @storages((config.STORAGE_TYPE_NFS, config.STORAGE_TYPE_GLUSTER))
    def test_storage(self, storage):
        pass
"""

import logging
from art.test_handler import settings

from _pytest.mark import ParameterSet


__all__ = ["pytest_artconf_ready"]

logger = logging.getLogger("pytest.art.matrix")

NOT_APPLICABLE = 'N/A'


class ARTMatrix(object):
    """
    Parametrizes tests based on STORAGES
    """
    storage_parameter_set = dict()

    def __init__(self):
        super(ARTMatrix, self).__init__()
        self._storages_defined_in_conf = set(
            settings.ART_CONFIG['RUN']['storages']
        )

    def get_storages_from_marks(self, marks):
        """
        Return set of storages from pytest mark storages

        Args:
            marks(list): list of pytest marks

        Returns:
            set: storages
        """
        reverse_marks = marks[:]
        reverse_marks.reverse()
        for mark in reverse_marks:
            if mark.name == "storages":
                storages = mark.args[0]
                storage_list = []
                for storage in storages:
                    # this part is for ussage other pytest.mark for specific
                    # storage type (e.g. polarion)
                    if isinstance(storage, ParameterSet):
                        _storage = storage.values[0]
                        storage_list.append(_storage)
                        self.storage_parameter_set[_storage] = storage
                    else:
                        storage_list.append(storage)
                return set(storage_list)
        return set()

    def parametrize_storage_tests(self, metafunc):
        """
        This method will parametrize tests which are decorated with @storages
        """

        self.storage_parameter_set = dict()
        # Use markers from function if defined
        storages = self.get_storages_from_marks(
            getattr(metafunc.function, 'pytestmark', [])
        )
        if not storages:
            # For backward compatibility we first check storages defined in
            # class and if they are defined we use them.
            storages = set(getattr(metafunc.cls, 'storages', []))
        if not storages and hasattr(metafunc, 'cls'):
            # Use markers from class if defined
            storages = self.get_storages_from_marks(
                getattr(metafunc.cls, 'pytestmark', [])
            )
            if not storages:
                return
        if NOT_APPLICABLE in storages:
            return
        # We have to do intersection with storages defined in art config
        storages = [
            [storage] for storage in set(storages).intersection(
                self._storages_defined_in_conf
            )
        ]
        if storages:
            if self.storage_parameter_set:
                storages = [
                    self.storage_parameter_set.get(storage[0], storage[0]) for
                    storage in storages
                ]
            metafunc.parametrize(
                ['storage'], storages, indirect=True, scope="class"
            )

    def pytest_generate_tests(self, metafunc):
        if 'storage' in metafunc.fixturenames:
            self.parametrize_storage_tests(metafunc)


def pytest_artconf_ready(config):
    """
    Register ARTMatrix plugin in case multiplier is enabled.
    """
    enabled = settings.ART_CONFIG.get(
        'MATRIX'
    ).get('enabled')
    if enabled:
        config.pluginmanager.register(ARTMatrix())
