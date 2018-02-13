import shlex

Q35_MACHINE_TYPE = 'q35'
Q35_VM_NAME = 'q35_machine'
PCIE_VERIFY_CMD_ON_VM = shlex.split("lspci -v | grep \"PCIe Root port\"")
PCIE_VERIFY_CMD_ON_HOST = shlex.split(
    "virsh -r dumpxml {vm_name} | grep \"pcie-root-port\"".format(
        vm_name=Q35_VM_NAME
    )
)
