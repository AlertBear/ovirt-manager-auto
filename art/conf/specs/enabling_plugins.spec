[ERROR_FETCHER]
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

[TRAC]
enabled = boolean(default=True)

[TCMS]
user = string(default="TCMS/jenkins.qa.lab.tlv.redhat.com")
keytab_files_location = path_exists(default="/etc")

[MATRIX_TEST_RUNNER]
discover_action = boolean(default=True)
