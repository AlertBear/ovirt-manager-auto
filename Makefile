RELEASE ?= 1
VERSION ?= 1.0
#CHANGELOG ?= $(shell date +"* %a %b %d %Y Generated <rhevm-qe-dept@redhat.com>")

SETUP_ACTION="bdist_rpm"
SETUP_ACTION_OPTS=--release="$(RELEASE)" #--changelog="$(CHANGELOG)"
RHEVM_API="setup_rhevm_api.py"
GLUSTER_API="setup_gluster_api.py"
JASPER_API="setup_jasper_api.py"
PLUGINS="setup_plugins.py"
CORE="setup.py"

all: core_rpm rhevm_api_rpm gluster_api_rpm jasper_api_rpm plugins_rpms

core_rpm:
	python $(CORE) $(SETUP_ACTION) $(SETUP_ACTION_OPTS)

rhevm_api_rpm:
	python $(RHEVM_API) $(SETUP_ACTION) $(SETUP_ACTION_OPTS)

gluster_api_rpm:
	python $(GLUSTER_API) $(SETUP_ACTION) $(SETUP_ACTION_OPTS)

jasper_api_rpm:
	python $(JASPER_API) $(SETUP_ACTION) $(SETUP_ACTION_OPTS)

plugins_rpms:
	python $(PLUGINS) $(SETUP_ACTION) $(SETUP_ACTION_OPTS)

install_yum:
	python $(CORE) install_yum
	python $(RHEVM_API) install_yum
	python $(GLUSTER_API) install_yum
	python $(JASPER_API) install_yum

install_pip:
	python $(CORE) install_pip
	python $(RHEVM_API) install_pip
	python $(GLUSTER_API) install_pip
	python $(JASPER_API) install_pip

install_deps: install_yum install_pip

clean:
	rm -rf build dist results
	find . -type f -regex '.*[.]py[co]$$' -exec rm -rf {} \;
	find . -type d -regex '.*/results$$' -exec rm -rf {} \;
