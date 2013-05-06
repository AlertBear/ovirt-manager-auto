[ERROR_FETCHER]
enabled = boolean(default=True)

[PUPPET]
enabled = boolean(default=True)

[HOST_NICS_RESOLUTION]
enabled = boolean(default=True)

[CPU_NAME_RESOLUTION]
enabled = boolean(default=True)

[VALIDATE_EVENTS]
enabled = boolean(default=True)

[LOG_CAPTURE]
enabled = boolean(default=True)
fmt = string(default='#(asctime)s - #(threadName)s - #(name)s - #(levelname)s - #(message)s')

[BUGZILLA]
enabled = boolean(default=True)

[GENERATE_DS]
enabled = boolean(default=True)

[LOGSTASH]
enabled = boolean(default=True)
[[vds]]
vdsm=string(default='/var/log/vdsm/vdsm.log')

[[vdc]]
engine=string(default='/var/log/ovirt-engine/engine.log')
bootstrap=string(default='/var/log/ovirt-engine/host-deploy/*')

[TRAC]
enabled = boolean(default=True)

[TCMS]
user = string(default="TCMS/jenkins.qa.lab.tlv.redhat.com")
keytab_files_location = path_exists(default="/etc")
generate_links = boolean(default=True)

[STORAGE]
# TODO: remove false, it remained for backward compatibility
devices_load_balancing = option('capacity', 'random', 'no', 'false', default='random')

[MATRIX_TEST_RUNNER]
discover_action = boolean(default=True)

[VERSION_FETCHER]
enabled = boolean(default=True)
host = string_list(default=list())
vds = string_list(default=list('vdsm', 'libvirt'))

[PUBLISH_TEST_DESC]
enabled = boolean(default=True)
 [[CONFIG_VARS]]
 hosts = string(default="JENKINS.required_hosts")
 macs = string(default="JENKINS.required_macs")
 [[ATTRIBUTES]]
 bz_id = test_attribute(default="case,group:bz:set")
 tcms_plans = test_attribute(default="*:tcms_plan_id:set")
