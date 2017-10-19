#!/usr/bin/env bash

# This script helps you install all deps of ART test framework.
#
# You have to export two env variables with existing paths to your
# copies of rhevm-qe-utils and storage-api repositories:
#   export RHEVM_QE_UTILS_PATH=/path/to/rhevm-qe-utils/repo
#   export STORAGE_API_PATH=/path/to/storage_api/repo
#
# Then run script from art repository. Note you are supposed to run it from
# the root of repository, that means from same directory where the setup.sh
# script is located.
#   bash setup.sh
#
# Activate virtualenv by running folowing command
#   source .art/bin/activate
#
# Run pytest
#   py.test -p art --help
#
# When you want to deactivate virtual environment for your session just run:
#   deactivate
#
# In case you need additional informations related to virtual env, please
# visit documentation: https://virtualenv.pypa.io/en/stable

set -e
set +x

if hash dnf;
then
  YUM=dnf
else
  YUM=yum
fi

if [ "$EUID" != "0" ];
then
  YUM="sudo $YUM"
fi

STORAGE_API_PATH=${STORAGE_API_PATH:-}
RHEVM_QE_UTILS_PATH=${RHEVM_QE_UTILS_PATH:-}

if [ -z "$STORAGE_API_PATH" ] ;
then
  echo "STORAGE_API_PATH variable is not exported into environment!"
  exit 1
fi
# NOTE: eval because of possible unexpanded variables, what we do on jenkins
if [ ! -d "$( eval echo $STORAGE_API_PATH )" ] ;
then
  echo "$STORAGE_API_PATH is not existing directory";
  exit 1
fi
if [ -z "$RHEVM_QE_UTILS_PATH" ] ;
then
  echo "RHEVM_QE_UTILS_PATH variable is not exported into environment!"
  exit 1
fi
if [ ! -d "$( eval echo $RHEVM_QE_UTILS_PATH )" ] ;
then
  echo "$RHEVM_QE_UTILS_PATH is not existing directory";
  exit 1
fi
if [ -z "$ART_PATH" ] ;
then
  ART_PATH=`pwd`
fi
if [ ! -d "$( eval echo $ART_PATH )" ] ;
then
  echo "$ART_PATH is not existing directory";
  exit 1
fi

export PYCURL_SSL_LIBRARY=nss

$YUM install -y \
    autofs \
    expect \
    gcc \
    libcurl \
    libcurl-devel \
    libffi-devel \
    libvirt-devel \
    libxml2-devel \
    libxslt-devel \
    nfs-utils \
    openssl-devel \
    python-cffi \
    python-devel \
    python-jinja2 \
    python-pip \
    python-virtualenv \
    PyYAML \
    redhat-rpm-config \
    vdsm-client \
    xz-devel

rm -rf .art
virtualenv --system-site-packages .art

echo "export PYTHONPATH=$ART_PATH:$ART_PATH/pytest_customization:$RHEVM_QE_UTILS_PATH:$STORAGE_API_PATH" | tee -a ./.art/bin/activate

source ./.art/bin/activate
# update pip and its dependencies
pip install pip -IU
# install ART's requirements
pip install -IU -rrequirements.txt
# install RHEVM_QE_UTILS's requirements
pip install -IU -r"$( eval echo $RHEVM_QE_UTILS_PATH )"/requirements.txt
# install STORAGE_API's requirements
pip install -IU -r"$( eval echo $STORAGE_API_PATH )"/requirements.txt
# build pytest customization
python setup_pytest.py install

virtualenv --relocatable .art
echo "Run 'source ./.art/bin/activate' to load the virtualenv"
