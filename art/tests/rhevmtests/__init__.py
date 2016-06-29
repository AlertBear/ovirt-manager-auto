"""
This package contains RHEVM tests
"""
import helpers
import logging
from rhevmtests import config
from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts
from art.rhevm_api.tests_lib.high_level import hosts as hl_hosts
from art.rhevm_api import resources
from art.rhevm_api.utils.inventory import Inventory

logger = logging.getLogger(__name__)


def setup_package():
    """ Set unfinished jobs to FINISHED status before run tests """
    helpers.clean_unfinished_jobs_on_engine()

    if not config.GOLDEN_ENV:
        return

    # in case of golden environment, reorder the rhel/rhevh hosts
    host_objs = ll_hosts.HOST_API.get(absLink=False)
    if host_objs:
        logger.info(
            "This GE includes the following hosts: %s",
            [host_obj.name for host_obj in host_objs]
        )
    else:
        raise EnvironmentError("This environment doesn't include hosts")

    host_order = config.PARAMETERS.get('host_order')
    if host_order in ('rhevh_first', 'rhel_first'):
        # sort the host_objs by rhevh_first if rhevh_first else rhel_first
        rhevh_first = host_order == 'rhevh_first'
        host_objs.sort(key=lambda host: host.get_type(), reverse=rhevh_first)

        # change the names of hosts to be able to rename it to new order
        for host_obj in host_objs:
            host_name = host_obj.name
            new_name = "temp_%s" % host_name
            if ll_hosts.updateHost(True, host_name, name=new_name):
                host_obj.name = new_name

        # run on GE yaml structure (dcs > clusters > hosts)
        # to be able to rename the hosts and move it to different cluster
        # if necessary
        i = 0
        for dc in config.dcs:
            for cluster in dc['clusters']:
                for host in cluster['hosts']:
                    new_name = host['name']
                    host_name = host_objs[i].name
                    if ll_hosts.updateHost(True, host_name, name=new_name):
                        host_objs[i].name = new_name
                    cluster_name = cluster['name']

                    if cluster_name != ll_hosts.getHostCluster(new_name):
                        hl_hosts.move_host_to_another_cluster(
                            new_name, cluster_name
                        )
                    i += 1
    hosts_type = []
    for host in host_objs:
        config.HOSTS.append(host.name)
        config.HOSTS_IP.append(host.address)
        host_type = host.get_type()
        if host_type == 'rhel':
            config.HOSTS_RHEL.append(host)
        elif host_type == 'rhev-h':
            config.HOSTS_RHEVH.append(host)
        hosts_type.append(host_type)

    logger.info(
        "The hosts order is: %s",
        zip(config.HOSTS, config.HOSTS_IP, hosts_type)
    )
    config.VDS_HOSTS.extend(
        [resources.VDS(h, config.HOSTS_PW) for h in config.HOSTS_IP]
    )
    logger.info("The vds hosts list: %s", config.VDS_HOSTS)

    if host_order == 'rhevh_first' and not config.HOSTS_RHEVH:
        raise EnvironmentError(
            "This environment doesn't include rhev-h hosts"
        )

    # set best cpu family model for all hosts
    # TODO remove the comments below when capabilities issue would fix
    # cpu_model = helpers.determine_best_cpu_model(
    #     config.VDS_HOSTS,
    #     config.COMP_VERSION,
    # )
    # if cpu_model:
    #     config.CPU_NAME = cpu_model

    helpers.storage_cleanup()

    # setup inventory reporter
    reporter = Inventory.get_instance()
    reporter.get_setup_inventory_report(
        print_report=True,
        check_inventory=True,
        rhevm_config_file=config
    )


def teardown_package():
    """
    Teardown after all tests
    """
    # Check unfinished jobs after all tests
    helpers.get_unfinished_jobs_list()

    # Clean up all storage domains which are not in GE yaml
    if config.GOLDEN_ENV:
        helpers.storage_cleanup()
