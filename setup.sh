#!/usr/bin/env bash

# This script helps you install all deps of ART test framework.
#
# You have to export two env variables:
#   export RHEVM_QE_UTILS_PATH=/path/to/rhevm-qe-utils/repo
#   export STORAGE_API_PATH=/path/to/storage_api/repo
#
# Then run script
#   bash setup.sh
#
# Activate virtualenv
#   source .art/bin/activate
#
# Run pytest
#   py.test -p art --help

set -e
set +x

if hash dnf;
then
  YUM=dnf
else
  YUM=yum
fi

STORAGE_API_PATH=${STORAGE_API_PATH:-}
RHEVM_QE_UTILS_PATH=${RHEVM_QE_UTILS_PATH:-}

if [ -z "$STORAGE_API_PATH" ] ;
then
  echo "STORAGE_API_PATH is required!"
  exit 1
fi
if [ -z "$RHEVM_QE_UTILS_PATH" ] ;
then
  echo "RHEVM_QE_UTILS_PATH is required!"
  exit 1
fi

sudo $YUM install -y \
    python-virtualenv \
    gcc \
    libffi-devel \
    libvirt-devel \
    libxml2-devel \
    libxslt-devel \
    openssl-devel \
    xz-devel \
    python-devel \
    expect \
    vdsm-cli \
    autofs \
    krb5-workstation

rm -rf .art
virtualenv .art

echo "export PYTHONPATH=`pwd`:`pwd`/pytest_customization:$RHEVM_QE_UTILS_PATH:$STORAGE_API_PATH" | tee -a ./.art/bin/activate

source ./.art/bin/activate
pip install -U -rrequirements.txt
python setup_pytest.py build
echo "Run 'source ./.art/bin/activate' to load the virtualenv"
