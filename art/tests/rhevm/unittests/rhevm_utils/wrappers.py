
import logging
import configobj

from rhevm_utils import RHEVMUtilities, RHEVMUtilsError

logger = logging.getLogger("rhevm-utils")

USERNAME = 'root'

def runISOUploaderUtility(positive, address, passwd, action=None, files=None, **kwargs):
    """
    Description: Run rehvm-iso-uploader, and verify expected result.
    Parameters:
     * address - address of setup
     * passwd - password
     * action - list, or upload
        * list - prints list of iso-domains
        * upload - uload files to iso-domain
     * files - list of files to be uploaded, by default local file is
               expected which will copy to rhevm-machine. you can use
               prefix to specify that file is already there (rhevm:/path).
     * kwargs - you can specify parameters of rhevm-iso-uploader.
                like: force, config-file, ...; if parameter has no value,
                then use None like: {'force': None}, you should define
                iso-domain or nfs-server; also you can use underscore
                instead of dash.
        * passwd - pasword for vdcadmin
        * user - vdcadmin@domain
        * iso-domain - name of isodomain
          ... and more, please see rhevm-iso-uploader --help
    """
    setup = RHEVMUtilities(host=address, user=USERNAME, passwd=passwd)
    try:
        setup.iso_uploader(action, files, **kwargs)
        setup.iso_uploader.autoTest()
    except RHEVMUtilsError as ex:
        logger.exception(ex)
        if positive:
            return False
    return True


def runLogCollectorUtility(positive, action, address, passwd, **kwargs):
    """
    Parameters:
     * address - address of setup
     * passwd - password
     * action - list, or collect
        * list - prints list of hypervisors which log could be collected from.
                 it could be affected by options -c/-d/-H
        * collect - starts collect logs (rhevm, DB, hypervisors).
                    it could be affected by options -c/-d/-H/pg-dbhost/...
     * kwargs - you can specify parameters of rhevm-log-collector.
                like: config-file, ...; if parameter has no value,
                then use None like: {'quite': None}; also you can use
                underscore instead of dash.
        * passwd - pasword for vdcadmin
        * user - user@domain
          ... and more, please see rhevm-log-collector --help
        NOTE: due to BZ #789040, #788993 don't collect data from hypervisors
              and it returns True even authentization failed.
    """
    setup = RHEVMUtilities(host=address, user=USERNAME, passwd=passwd)
    try:
        setup.log_collector(action, **kwargs)
        setup.log_collector.autoTest()
    except RHEVMUtilsError as ex:
        logger.exception(ex)
        if positive:
            return False
    return True

def runCleanupUtility(positive, address, passwd, **kwargs):
    """
    Parameters:
     * address - address of setup
     * passwd - password
     * kwargs - you can specify parameters of rhevm-cleanup.
                like: config-file, ...; if parameter has no value,
                then use None like: {'quite': None}; also you can use
                underscore instead of dash.
                Please see rhevm-cleanup --help
    """
    setup = RHEVMUtilities(host=address, user=USERNAME, passwd=passwd)
    try:
        setup.cleanup(**kwargs)
        setup.cleanup.autoTest()
    except RHEVMUtilsError as ex:
        logger.exception(ex)
        if positive:
            return False
    return True

def runConfigUtility(positive, address, passwd, **kwargs):
    """
    Parameters:
     * address - address of setup
     * passwd - password
     * kwargs - you can specify parameters of rhevm-config.
                like: config-file, ...; if parameter has no value,
                then use None like: {'quite': None}; also you can use
                underscore instead of dash.
                Please see rhevm-config --help
    """
    setup = RHEVMUtilities(host=address, user=USERNAME, passwd=passwd)
    try:
        setup.config(**kwargs)
        setup.config.autoTest()
    except RHEVMUtilsError as ex:
        logger.exception(ex)
        if positive:
            return False
    return True

def runManageDomainsUtility(positive, address, passwd, **kwargs):
    """
    Parameters:
     * address - address of setup
     * passwd - password
     * kwargs - you can specify parameters of rhevm-manage-domains.
                like: config-file, ...; if parameter has no value,
                then use None like: {'quite': None}; also you can use
                underscore instead of dash.
                Please see rhevm-manage-domains --help
    """
    setup = RHEVMUtilities(host=address, user=USERNAME, passwd=passwd)
    try:
        setup.manage_domains(**kwargs)
        setup.manage_domains.autoTest()
    except RHEVMUtilsError as ex:
        logger.exception(ex)
        if positive:
            return False
    return True

def runUpgradeUtility(positive, address, passwd, **kwargs):
    """
    Parameters:
     * address - address of setup
     * passwd - password
     * kwargs - you can specify parameters of rhevm-upgrade.
                like: config-file, ...; if parameter has no value,
                then use None like: {'quite': None}; also you can use
                underscore instead of dash.
                Please see rhevm-upgrade --help
    """
    setup = RHEVMUtilities(host=address, user=USERNAME, passwd=passwd)
    try:
        setup.upgrade(**kwargs)
        setup.upgrade.autoTest()
    except RHEVMUtilsError as ex:
        logger.exception(ex)
        if positive:
            return False
    return True

def runSetupUtility(positive, address, passwd, **kwargs):
    """
    Parameters:
     * address - address of setup
     * passwd - password
     * kwargs - you can specify parameters of rhevm-setup.
                like: config-file, ...; if parameter has no value,
                then use None like: {'quite': None}; also you can use
                underscore instead of dash.
                Please see rhevm-setup --help
    """
    setup = RHEVMUtilities(host=address, user=USERNAME, passwd=passwd)
    try:
        setup.setup(**kwargs)
        setup.setup.autoTest()
    except RHEVMUtilsError as ex:
        logger.exception(ex)
        if positive:
            return False
    return True

def fillAnswerFile(path, address, passwd, **kwargs):
    """
    Parameters:
     * path - path to answer file on machine, could be None -> then config file
              will be generated, and filled
     * address - address of setup
     * passwd - password
     * kwargs - variables for answer file
    """
    setup = RHEVMUtilities(host=address, user=USERNAME, passwd=passwd)
    try:
        setup.setup(gen_answer_file=path)
        setup.setup.autoTest()
        setup.setup.fillAnswerFile(**kwargs)
    except RHEVMUtilsError as ex:
        logger.exception(ex)
        return False
    return True


