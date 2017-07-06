"""
HE HA test fixtures
"""
import logging
import socket

import pytest

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.sla as ll_sla
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as u_libs
import config as conf
import helpers
import rhevmtests.helpers as rhevm_helpers

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def init_he_ha_test():
    """
    1) Define ISCSI storage type constant
    2) Copy the HE stats script on all hosts
    """
    if not ll_hosts.is_hosted_engine_configured(conf.HOSTS[0]):
        pytest.skip("GE does not configured as HE environment")

    he_storage_domain_type = conf.VDS_HOSTS[0].run_command(
        command=["grep", "domainType", conf.HOSTED_ENGINE_CONF_FILE]
    )[1].strip().split("=")[1]
    conf.IS_ISCSI_STORAGE_DOMAIN = (
        he_storage_domain_type == conf.STORAGE_TYPE_ISCSI
    )

    he_script_path = helpers.locate_he_stats_script()
    for vds in conf.VDS_HOSTS:
        u_libs.testflow.setup(
            "%s: copy the file %s to the %s",
            conf.SLAVE_HOST, he_script_path, vds
        )
        assert conf.SLAVE_HOST.fs.transfer(
            path_src=he_script_path,
            target_host=vds,
            path_dst=conf.SCRIPT_DEST_PATH
        )


@pytest.fixture(scope="class")
def get_host_with_he_vm(request):
    """
    Get the host where runs HE VM
    """
    test_class = request.node.cls
    u_libs.testflow.setup("Get the host where runs HE VM")
    he_stats = helpers.get_he_stats(command_executor=conf.VDS_HOSTS[0])
    test_class.hosts_without_he_vm = []
    for host_name, host_he_params in he_stats.iteritems():
        host_res = helpers.get_resource_by_name(host_name=host_name)
        if host_he_params.get(conf.VM_STATE) == conf.VM_STATE_UP:
            test_class.he_vm_host = host_res
        else:
            test_class.hosts_without_he_vm.append(host_res)
    logger.debug("HE VM runs on the host %s", test_class.he_vm_host)
    assert test_class.he_vm_host and test_class.hosts_without_he_vm
    test_class.command_executor = test_class.hosts_without_he_vm[0]


@pytest.fixture(scope="class")
def prepare_env_for_next_test(request):
    """
    Prepare HE hosts for a next test case

    1) Check hosts up-to-date status
    2) If needed, Drop hosts score to the maximal value
    """
    test_class = request.node.cls
    all_he_hosts = list(test_class.hosts_without_he_vm)
    all_he_hosts.append(test_class.he_vm_host)

    def fin():
        for host_resource in all_he_hosts:
            u_libs.testflow.teardown(
                "%s: check up to date status", host_resource
            )
            assert helpers.get_host_he_stat(
                command_executor=test_class.command_executor,
                host_resource=host_resource,
                he_stat=conf.UP_TO_DATE
            ) or helpers.wait_for_host_he_up_to_date(
                command_executor=test_class.command_executor,
                host_resource=host_resource,
                timeout=conf.WAIT_FOR_STATE_TIMEOUT
            )
            u_libs.testflow.teardown("%s: check HE score", host_resource)
            if helpers.get_host_he_stat(
                command_executor=test_class.command_executor,
                host_resource=host_resource,
                he_stat=conf.SCORE
            ) < conf.MAX_SCORE:
                u_libs.testflow.teardown("%s: drop HE score", host_resource)
                assert helpers.drop_host_he_score_to_max(
                    host_resource=host_resource
                )
        u_libs.testflow.teardown(
            "Check if the engine runs on the host from the list: %s",
            [he_host.ip for he_host in all_he_hosts]
        )
        assert helpers.wait_for_hosts_he_vm_health_state(
            command_executor=test_class.command_executor,
            hosts_resources=all_he_hosts,
            timeout=conf.WAIT_FOR_STATE_TIMEOUT
        )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def restart_host_via_power_management(request):
    """
    Restart host via power management
    """
    test_class = request.node.cls
    he_vm_host_fqdn = test_class.he_vm_host.fqdn
    he_vm_host_pm = rhevm_helpers.get_pm_details(
        host_name=he_vm_host_fqdn
    ).get(he_vm_host_fqdn) or conf.PMS.get(he_vm_host_fqdn)
    if not he_vm_host_pm:
        pytest.skip(
            "%s: does not have power management" % test_class.he_vm_host
        )

    def fin():
        host_name = conf.HOSTS[conf.VDS_HOSTS.index(test_class.he_vm_host)]
        if ll_hosts.get_host_status(host=host_name) != conf.HOST_UP:
            fence_commands = {
                "poweroff": "off",
                "poweron": "on",
            }
            for msg, fence_command in fence_commands.iteritems():
                u_libs.testflow.teardown(
                    "%s: %s via power management", test_class.he_vm_host, msg
                )
                assert helpers.run_power_management_command(
                    command_executor=test_class.command_executor,
                    host_to_fence_pm=he_vm_host_pm,
                    fence_command=fence_command
                )
            u_libs.testflow.teardown(
                "%s: wait for up-to-date status", test_class.he_vm_host
            )
            assert helpers.wait_for_host_he_up_to_date(
                command_executor=test_class.command_executor,
                host_resource=test_class.he_vm_host,
                timeout=conf.POWER_MANAGEMENT_TIMEOUT
            )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def stop_network_on_host_with_he_vm(request):
    """
    Stop the network service on the host with HE VM
    """
    test_class = request.node.cls

    u_libs.testflow.setup("%s: stop network service", test_class.he_vm_host)
    try:
        test_class.he_vm_host.network.if_down(nic=conf.MGMT_BRIDGE)
    except socket.timeout as ex:
        logger.debug("Host unreachable, %s", ex)


@pytest.fixture(scope="class")
def block_connection_to_storage(request):
    """
    Block the connection to the HE storage domain via iptables
    """
    test_class = request.node.cls

    if conf.IS_ISCSI_STORAGE_DOMAIN:
        pytest.skip(conf.HE_ISCSI_STORAGE_DOMAIN_MSG)

    def fin():
        u_libs.testflow.teardown(
            "%s: wait for status UP", test_class.he_vm_host
        )
        helpers.wait_for_host_he_up_to_date(
            command_executor=test_class.command_executor,
            host_resource=test_class.he_vm_host,
            timeout=conf.WAIT_FOR_STATE_TIMEOUT
        )

        cmd = ['iptables-restore', conf.IPTABLES_BACKUP_FILE]
        u_libs.testflow.teardown(
            "%s: restore iptables from the file %s",
            test_class.he_vm_host, conf.IPTABLES_BACKUP_FILE
        )
        test_class.he_vm_host.run_command(command=cmd)

        service_executor = test_class.he_vm_host.service(conf.AGENT_SERVICE)
        u_libs.testflow.teardown(
            "%s: check if the %s service up",
            test_class.he_vm_host, conf.AGENT_SERVICE
        )
        if not service_executor.status():
            u_libs.testflow.teardown(
                "%s: start the %s service",
                test_class.he_vm_host, conf.AGENT_SERVICE
            )
            service_executor.start()
    request.addfinalizer(fin)

    cmd = ['iptables-save', '>>', conf.IPTABLES_BACKUP_FILE]
    u_libs.testflow.setup(
        "%s: save iptables to the file %s",
        test_class.he_vm_host, conf.IPTABLES_BACKUP_FILE
    )
    assert not test_class.he_vm_host.run_command(command=cmd)[0]

    cmd = ["grep", "storage=", conf.HOSTED_ENGINE_CONF_FILE]
    out = test_class.he_vm_host.run_command(command=cmd)[1]
    ip_to_block = out.split("=")[1].split(":")[0].strip('\n')
    u_libs.testflow.setup(
        "%s: block connection to the storage with IP %s",
        test_class.he_vm_host, ip_to_block
    )
    cmd = ["iptables", "-I", "INPUT", "-s", ip_to_block, "-j", "DROP"]
    assert not test_class.he_vm_host.run_command(command=cmd)[0]


@pytest.fixture(scope="class")
def change_he_gateway_address(request):
    """
    Change the HE gateway address on the host
    """
    test_class = request.node.cls
    he_vm_host = test_class.he_vm_host

    def fin():
        cmd = [
            conf.COPY_CMD,
            conf.HOSTED_ENGINE_CONF_FILE_BACKUP,
            conf.HOSTED_ENGINE_CONF_FILE
        ]
        u_libs.testflow.teardown(
            "%s: restore HE configuration file", he_vm_host
        )
        test_class.he_vm_host.run_command(command=cmd)

        u_libs.testflow.teardown(
            "%s: remove the file %s",
            he_vm_host, conf.HOSTED_ENGINE_CONF_FILE_BACKUP
        )
        he_vm_host.fs.remove(path=conf.HOSTED_ENGINE_CONF_FILE_BACKUP)

        u_libs.testflow.setup(
            "%s: restart the %s service", he_vm_host, conf.AGENT_SERVICE
        )
        he_vm_host.service(conf.AGENT_SERVICE).restart()
    request.addfinalizer(fin)

    cmd = [
        conf.COPY_CMD,
        conf.HOSTED_ENGINE_CONF_FILE,
        conf.HOSTED_ENGINE_CONF_FILE_BACKUP
    ]
    u_libs.testflow.setup(
        "%s: make the file %s backup",
        he_vm_host, conf.HOSTED_ENGINE_CONF_FILE
    )
    assert not test_class.he_vm_host.run_command(command=cmd)[0]

    cmd = [
        "sed", "-i", "s/^gateway=.*/gateway=1.1.1.1/",
        conf.HOSTED_ENGINE_CONF_FILE
    ]
    u_libs.testflow.setup(
        "%s: change HE gateway under the file %s",
        he_vm_host, conf.HOSTED_ENGINE_CONF_FILE
    )
    assert not test_class.he_vm_host.run_command(command=cmd)[0]

    u_libs.testflow.setup(
        "%s: restart the %s service", he_vm_host, conf.AGENT_SERVICE
    )
    assert he_vm_host.service(conf.AGENT_SERVICE).restart()


@pytest.fixture(scope="class")
def load_host_cpu_to_maximum(request):
    """
    Load the host CPU to the maximum value
    """
    test_class = request.node.cls
    he_vm_host = test_class.he_vm_host

    def fin():
        u_libs.testflow.teardown(
            "%s: release the CPU from the load", he_vm_host
        )
        ll_sla.stop_cpu_load_on_resources(resources=[he_vm_host])

        u_libs.testflow.step(
            "%s: wait for the HE score %s", he_vm_host, conf.MAX_SCORE
        )
        helpers.wait_for_host_he_score(
            command_executor=test_class.hosts_without_he_vm[0],
            host_resource=he_vm_host,
            expected_score=conf.MAX_SCORE,
            timeout=conf.CPU_SCORE_TIMEOUT
        )
    request.addfinalizer(fin)

    u_libs.testflow.setup(
        "%s: load the CPU to the 100 percent", he_vm_host
    )
    assert ll_sla.load_resources_cpu(resources=[he_vm_host], load=100)


@pytest.fixture(scope="class")
def enable_local_maintenance_on_host(request):
    """
    Enable LocalMaintenance on the host with the HE VM
    """
    test_class = request.node.cls
    he_vm_host = test_class.he_vm_host

    def fin():
        u_libs.testflow.teardown("%s: disable local maintenance", he_vm_host)
        helpers.set_he_maintenance_mode(
            host_resource=he_vm_host, mode=conf.MAINTENANCE_NONE
        )

        u_libs.testflow.step(
            "%s: wait for the HE score %s", he_vm_host, conf.MAX_SCORE
        )
        helpers.wait_for_host_he_score(
            command_executor=test_class.hosts_without_he_vm[0],
            host_resource=he_vm_host,
            expected_score=conf.MAX_SCORE,
            timeout=conf.CPU_SCORE_TIMEOUT
        )
    request.addfinalizer(fin)

    u_libs.testflow.setup("%s: enable local maintenance", he_vm_host)
    helpers.set_he_maintenance_mode(
        host_resource=he_vm_host, mode=conf.MAINTENANCE_LOCAL
    )


@pytest.fixture(scope="class")
def enable_global_maintenance_on_host(request):
    """
    Enable GlobalMaintenance on the host with the HE VM
    """
    test_class = request.node.cls
    he_vm_host = test_class.he_vm_host
    all_hosts = list(test_class.hosts_without_he_vm)
    all_hosts.append(he_vm_host)

    def fin():
        u_libs.testflow.teardown("%s: disable global maintenance", he_vm_host)
        helpers.set_he_maintenance_mode(
            host_resource=he_vm_host, mode=conf.MAINTENANCE_NONE
        )

        u_libs.testflow.teardown("Wait for the engine health to be good")
        helpers.wait_for_hosts_he_vm_health_state(
            command_executor=test_class.command_executor,
            hosts_resources=all_hosts,
        )
    request.addfinalizer(fin)

    u_libs.testflow.setup("%s: enable global maintenance", he_vm_host)
    helpers.set_he_maintenance_mode(
        host_resource=he_vm_host, mode=conf.MAINTENANCE_GLOBAL
    )


@pytest.fixture(scope="class")
def stop_services(request):
    """
    Stop the given services on the host with the HE VM
    """
    services_to_start = request.node.cls.services_to_start
    services_to_stop = request.node.cls.services_to_stop
    he_vm_host = request.node.cls.he_vm_host

    def fin():
        for service_name in services_to_start:
            service = he_vm_host.service(
                name=service_name, timeout=conf.STOP_TIMEOUT
            )
            u_libs.testflow.teardown(
                "%s: start the service %s", he_vm_host, service_name
            )
            service.start()
    request.addfinalizer(fin)

    for service_name in services_to_stop:
        service = he_vm_host.service(
            name=service_name, timeout=conf.STOP_TIMEOUT
        )
        u_libs.testflow.setup(
            "%s: stop the service %s", he_vm_host, service_name
        )
        service.stop()


@pytest.fixture(scope="class")
def prepare_env_for_power_management_test(request):
    """
    1) Update regular VM to be HA
    2) Configure PM on the host
    3) Start the HA VM on the host
    4) Poweroff of the host
    """
    he_vm_host_resource = request.node.cls.he_vm_host
    he_vm_host_fqdn = he_vm_host_resource.fqdn
    host_name = conf.HOSTS[conf.VDS_HOSTS.index(he_vm_host_resource)]
    he_vm_host_pm = rhevm_helpers.get_pm_details(
        host_name=he_vm_host_fqdn
    ).get(he_vm_host_fqdn) or conf.PMS.get(he_vm_host_fqdn)
    if not he_vm_host_pm:
        pytest.skip(
            "Host %s does not have power management" % host_name
        )
    options = {
        "slot": he_vm_host_pm.get(conf.PM_SLOT),
        "port": he_vm_host_pm.get(conf.PM_PORT)
    }
    agent_options = {}
    for option_name, option_value in options.iteritems():
        if option_value:
            agent_options[option_name] = option_value
    agent = {
        "agent_type": he_vm_host_pm.get(conf.PM_TYPE),
        "agent_address": he_vm_host_pm.get(conf.PM_ADDRESS),
        "agent_username": he_vm_host_pm.get(conf.PM_USERNAME),
        "agent_password": he_vm_host_pm.get(conf.PM_PASSWORD),
        "concurrent": False,
        "order": 1,
        "options": agent_options
    }

    def fin():
        results = []
        u_libs.testflow.teardown("Stop the VM %s", conf.VM_NAME[0])
        results.append(ll_vms.stop_vms_safely([conf.VM_NAME[0]]))

        u_libs.testflow.teardown("Disable HA on the VM %s", conf.VM_NAME[0])
        results.append(
            ll_vms.updateVm(
                positive=True,
                vm=conf.VM_NAME[0],
                highly_available=False
            )
        )

        u_libs.testflow.teardown(
            "Remove power management from the host %s", host_name
        )
        results.append(hl_hosts.remove_power_management(host_name=host_name))

        assert all(results)
    request.addfinalizer(fin)

    u_libs.testflow.setup("Enable HA on the VM %s", conf.VM_NAME[0])
    assert ll_vms.updateVm(
        positive=True,
        vm=conf.VM_NAME[0],
        highly_available=True
    )

    u_libs.testflow.setup("Configure PM on the host %s", host_name)
    assert hl_hosts.add_power_management(
        host_name=host_name, pm_agents=[agent]
    )

    u_libs.testflow.setup(
        "Start the VM %s on the host %s", conf.VM_NAME[0], host_name
    )
    assert ll_vms.runVmOnce(positive=True, vm=conf.VM_NAME[0], host=host_name)

    he_vm_host_resource.add_power_manager(pm_type="ssh")
    u_libs.testflow.setup("Poweroff the host %s", host_name)
    he_vm_host_resource.get_power_manager().poweroff("-f")
