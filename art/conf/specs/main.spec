[VALIDATE]
parameters_section_validation = section_exists(section='PARAMETERS', default=True)

[RUN]
engines = force_list(default=list('sdk', 'rest', 'cli', 'java'))
system_engine = option('sdk', 'rest', 'cli', 'java', default='rest')
debug = boolean(default=True)
media_type = option('application/xml', default='application/xml')
in_parallel = force_list(default=list())
parallel_timeout = integer(default=3600)
parallel_configs = force_list(default=list())
parallel_sections = force_list(default=list())
secure=boolean(default=True)
ssl_key_store_password = string(default="123456")
elements_conf = path_to_config(default='conf/elements.conf')
validate=boolean(default=True)
vdsm_transport_protocol = option('xml', 'stomp', default=None)
storages = force_list(default=list('nfs', 'iscsi', 'glusterfs'))
storage_type = option('nfs', 'iscsi', 'fcp', 'glusterfs', 'posixfs_nfs', 'posixfs_gluster', 'posixfs_mixed', 'localfs', 'posixfs_pnfs', default=None)

[REST_CONNECTION]
scheme = option('http', 'https', default='http')
host = is_alive()
port = integer(default=80)
user = string()
password = string()
entry_point = string(default='api')
user_domain = domain_format()
persistent_auth = boolean(default=True)
session_timeout = integer(default=3600)
filter = boolean(default=False)

[CLI_CONNECTION]
tool = option('ovirt-shell', 'rhevm-shell', default='rhevm-shell')
cli_log_file = string(default='/tmp/cli_log.log')
validate_cli_command = boolean(default=True)
optional_params = string(default='')
cli_exit_timeout = integer(default=240)

[JAVA_SDK]
#request_timeout = integer(default=100)

[REPORT]
has_sub_tests = boolean(default=True)
add_report_nodes = string(default=no)
