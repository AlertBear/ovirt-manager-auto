from art.core_api import ActionSet

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

