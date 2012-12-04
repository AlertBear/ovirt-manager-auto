import os
import logging
from art.core_api import ActionSet
from art.generateDS.setup_ds import GenerateDataStructures
from art.test_handler.settings import opts
import art

DATA_STRUCT_PATH = os.path.join('data_struct', 'data_structures.py')


logger = logging.getLogger('rhevm_api')


class GenerateRhevmDataStructures(GenerateDataStructures):

    def __init__(self, conf):
        super(GenerateRhevmDataStructures, self).__init__(
                     opts, repo_path=os.path.dirname(art.__file__))

    def _set_xsd_path(self):
        xsd_path = os.path.join(os.path.dirname(__file__),
                                'data_struct', 'api.xsd')
        self._ds_path = os.path.join(os.path.dirname(__file__),
                                     DATA_STRUCT_PATH)
        self._xsd_path = xsd_path
        opts['api_xsd'] = xsd_path

generate_ds = GenerateRhevmDataStructures(opts)


class RHEVMActionSet(ActionSet):
    RECURSIVELY = [
            'art.rhevm_api.tests_lib',
            'art.rhevm_api.utils',
            ]
    MODULES = [
            # 'art.rhevm_api.tests_lib.low_level.cleanup'
            # doesn't exist but required by: 'clean': 'art.rhevm_api.tests_lib.low_level.cleanup.removeAll',
            #'art.rhevm_api.tests_lib.low_level.db_integrity',
            # doesn't exist but required by: 'checkDBIntegrity': 'art.rhevm_api.tests_lib.low_level.db_integrity.checkDBIntegrity',
            #'art.rhevm_api.tests_lib.low_level.db_views',
            # doesn't exist but required by: 'vmIsPresentInConfigView': 'art.rhevm_api.tests_lib.low_level.db_views.vmIsPresentInConfigView',
            #'art.rhevm_api.tests_lib.low_level.login',
            # doesn't exist but required by: 'checkDBIntegrity': 'art.rhevm_api.tests_lib.low_level.db_integrity.checkDBIntegrity',
            #       'loginUser': 'art.rhevm_api.tests_lib.low_level.login.loginUser',
            #       'loginUserWithInvalidCredentials': 'art.rhevm_api.tests_lib.low_level.login.loginUserWithInvalidCredentials',
            #       'loginUserWithMissingUsername': 'art.rhevm_api.tests_lib.low_level.login.loginUserWithMissingUsername',
            #       'loginUserWithMissingPassword': 'art.rhevm_api.tests_lib.low_level.login.loginUserWithMissingPassword',
            #'art.rhevm_api.tests_lib.low_level.rest.vms',
            # doesn't exist but required by: 'freeSTAFHandlers': 'art.rhevm_api.tests_lib.low_level.rest.vms.freeSTAFHandlers',
            #'art.rhevm_api.utils.validator',
            # doesn't exist but required by: 'compareStrings': 'art.rhevm_api.utils.validator.compareStrings',
            ]

