[VALIDATE]
parameters_section_validation = section_exists(section='PARAMETERS', default=True)

[RUN]
engine = option('sdk', 'rest', 'cli', default='rest')
tests_file = path_exists()
data_struct_mod = python_module()
api_xsd = path_exists()
debug = boolean(default=True)
auto_devices = boolean(default=False)
media_type = option('application/xml', default='application/xml')


[REST_CONNECTION]
scheme = option('http', 'https', default='http')
host = is_alive()
port = integer()
user = string()
password = string()
entry_point = string()
user_domain = domain_format()


[PARAMETERS]
test_conf_specs = string_list(default=list())

[REPORT]
has_sub_tests = boolean(default=True)
add_report_nodes = string(default=no)
