SETUP_ACTION="bdist_rpm"
SETUP_ACTION_OPTS?=--source-only
RHEVM_API="setup_rhevm_api.py"
RHEVM_QE_TESTS="setup_rhevm_qe_tests.py"
GLUSTER_API="setup_gluster_api.py"
JASPER_API="setup_jasper_api.py"
PLUGINS="setup_plugins.py"
CORE="setup.py"
TARGET_BRANCH?=origin/master

all: core_rpm rhevm_api_rpm gluster_api_rpm jasper_api_rpm plugins_rpms rhevm_qe_tests_rpm

test:
	git diff $(TARGET_BRANCH) | flake8 --diff
	flake8 art/tests
	flake8 nose_customization

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

rhevm_qe_tests_rpm:
	python $(RHEVM_QE_TESTS) $(SETUP_ACTION) $(SETUP_ACTION_OPTS)

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
	$(RM) -r build dist results
	find . -type f -regex '.*[.]py[co]$$' -exec rm -rf {} \;
	find . -type d -regex '.*/results$$' -exec rm -rf {} \;
