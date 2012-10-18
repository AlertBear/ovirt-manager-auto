[VALIDATE]
parameters_section_validation = section_exists(section='PARAMETERS', default=True)

[RUN]
engine = option('sdk', 'rest', 'cli', default='rest')
#tests_file = path_exists()
data_struct_mod = python_module()
api_xsd = path_exists()
debug = boolean(default=True)
auto_devices = boolean(default=False)
auto_devices_cleanup = boolean(default=True)
media_type = option('application/xml', default='application/xml')
in_parallel = force_list(default=list())
parallel_configs = force_list(default=list())
parallel_sections = force_list(default=list())
secure=boolean(default=False)

[REST_CONNECTION]
scheme = option('http', 'https', default='http')
host = is_alive()
port = integer(default=80)
user = string()
password = string()
entry_point = string(default='api')
user_domain = domain_format()

[CLI_CONNECTION]
tool = option('ovirt-shell', 'rhevm-shell', default='rhevm-shell')
optional_params = string(default='')

[SDK_CONNECTION]


[PARAMETERS]
test_conf_specs = string_list(default=list())

[REPORT]
has_sub_tests = boolean(default=True)
add_report_nodes = string(default=no)
