[PARAMETERS]
shared_iso_domain_path = string(default='/volumes/shafan/ci-eng-shared-iso')
shared_iso_domain_address = domain_format(default='shafan.eng.lab.tlv.redhat.com')

cobbler_address = is_alive(default='ci-cobbler.eng.lab.tlv.redhat.com')

[STORAGE]
storage_pool=force_list(default=list('10.35.148.12', '10.35.16.26', '10.35.16.27'))

[LOGSTASH]
site = string(default='http://log-server.eng.lab.tlv.redhat.com:9292')
