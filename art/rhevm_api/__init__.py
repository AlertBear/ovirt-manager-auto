import os
import logging
from subprocess  import Popen, PIPE
from art.core_api import ActionSet
from art.test_handler.settings import opts
import art

DATA_STRUCT_PATH = os.path.join('data_struct', 'data_structures.py')


logger = logging.getLogger('rhevm_api')


def __set_xsd_path():
    xsd_path = os.path.join(os.path.dirname(__file__), 'data_struct', 'api.xsd')
    opts['api_xsd'] = xsd_path
__set_xsd_path()


def generate_ds(conf): # do same for orhers_apies
    from art.core_api.http import HTTPProxy
    from art.test_handler.settings import opts

    def __download_xsd(file_path):
        proxy = HTTPProxy(opts)
        res = proxy.GET('/api?schema')
        if res['status'] > 300:
            raise Exception("Failed to download schema: %s " % res['reason'])

        with open(file_path, 'w') as fh:
            fh.write(res['body'])
        logger.info("Downloaded XSD scheme: %s", file_path)

    def __generate_ds(xsd, ds_path):
        repo_path = os.path.dirname(art.__file__)
        ds_exec = os.path.join(repo_path, 'generateDS', 'generateDS.py')
        cmd = ['python', ds_exec, '-f', '-o', ds_path, \
                '--member-specs=dict', xsd]

        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode:
            raise Exception(err)
        logger.info("Generated data structures: %s", ds_path)


    ds_path = os.path.join(os.path.dirname(__file__), DATA_STRUCT_PATH)

    __download_xsd(opts['api_xsd'])
    __generate_ds(opts['api_xsd'], ds_path)


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

