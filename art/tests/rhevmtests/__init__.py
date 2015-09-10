"""
This package contains RHEVM tests
"""
import helpers
import config
from art.rhevm_api import resources


def setup_package():
    """ Set unfinished jobs to FINISHED status before run tests """
    helpers.clean_unfinished_jobs_on_engine()

    # order the rhel/rhevh hosts in case of GE
    if config.GOLDEN_ENV:
        config.HOSTS = []
        config.HOSTS_IP = []
        config.VDS_HOSTS = []
        for host_obj in config.HOST_OBJS:
            vds_obj = resources.VDS(host_obj.ip, host_obj.password)
            os_info = vds_obj.get_os_info()
            if "hypervisor" in os_info['dist'].lower():
                config.HOSTS_RHEVH.append(host_obj)
            else:
                config.HOSTS_RHEL.append(host_obj)
        config.HOST_OBJS = config.HOSTS_RHEL + config.HOSTS_RHEVH
        if ('host_order' in config.PARAMETERS and
                config.PARAMETERS['host_order'] == 'rhevh_first'):
            config.HOST_OBJS = config.HOSTS_RHEVH + config.HOSTS_RHEL

        for host in config.HOST_OBJS:
            config.HOSTS.append(host.name)
            config.HOSTS_IP.append(host.ip)
            config.VDS_HOSTS.append(resources.VDS(host.ip, host.password))
        config.logger.info("The host order is: %s", config.HOSTS_IP)


def teardown_package():
    """ Check unfinished jobs after all tests """
    helpers.get_unfinished_jobs_list()
