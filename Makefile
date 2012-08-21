SETUP_ACTION="bdist_rpm"
RHEVM_API="setup_rhevm_api.py"
GLUSTER_API="setup_gluster_api.py"
JASPER_API="setup_jasper_api.py"

all: core_rpm rhevm_api_rpm gluster_api_rpm jasper_api_rpm plugins_rpms

core_rpm:
	python setup.py $(SETUP_ACTION)

rhevm_api_rpm:
	python setup_rhevm_api.py $(SETUP_ACTION)

gluster_api_rpm:
	python setup_gluster_api.py $(SETUP_ACTION)

jasper_api_rpm:
	python setup_jasper_api.py $(SETUP_ACTION)

plugins_rpms:
	python setup_plugins.py $(SETUP_ACTION)

install_yum:
	python setup.py install_yum
	python $(RHEVM_API) install_yum
	python $(GLUSTER_API) install_yum
	python $(JASPER_API) install_yum

install_pip:
	python setup.py install_pip
	python $(RHEVM_API) install_pip
	python $(GLUSTER_API) install_pip
	python $(JASPER_API) install_pip

install_deps: install_yum install_pip

clean:
	rm -rf build dist results
	find . -type f -regex '.*[.]py[co]$$' -exec rm -rf {} \;
	find . -type d -regex '.*/results$$' -exec rm -rf {} \;
