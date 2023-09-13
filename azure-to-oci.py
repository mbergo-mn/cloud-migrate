#!/usr/bin/env python3

import subprocess
import os
import sys
import json

def azure_create_snapshot(vm_id):
    snapshot_name = "mysnapshot"  # Modify as needed
    cmd = f"az vm snapshot create --resource-group MyResourceGroup --vm-name {vm_id} --name {snapshot_name}"
    subprocess.run(cmd, shell=True, check=True)

def azure_export_vhd(snapshot_name):
    # Modify the storage account and container as needed
    storage_account = "mystorageaccount"
    container_name = "mycontainer"
    vhd_name = f"{snapshot_name}.vhd"
    cmd = f"az snapshot export --name {snapshot_name} --resource-group MyResourceGroup --destination https://account.blob.core.windows.net/container/{vhd_name}"
    subprocess.run(cmd, shell=True, check=True)
    return vhd_name

def convert_vhd_to_qcow2(vhd_path):
    qcow2_path = vhd_path.replace(".vhd", ".qcow2")
    cmd = f"qemu-img convert -f vpc -O qcow2 {vhd_path} {qcow2_path}"
    subprocess.run(cmd, shell=True, check=True)
    return qcow2_path

def oci_upload_image(qcow2_path):
    bucket_name = "mybucket"  # Modify as needed
    cmd = f"oci os object put --bucket-name {bucket_name} --file {qcow2_path} --name {os.path.basename(qcow2_path)}"
    subprocess.run(cmd, shell=True, check=True)

def oci_import_image(qcow2_name):
    # Modify the required parameters as needed
    cmd = f"oci compute image import from-object --namespace mynamespace --bucket-name mybucket --name {qcow2_name} --source-image-type qcow2"
    subprocess.run(cmd, shell=True, check=True)

def get_vm_config(vm_id):
    cmd = f"az vm show --resource-group MyResourceGroup --name {vm_id} --query '[hardwareProfile.vmSize, storageProfile.osDisk.diskSizeGb]'"
    result = subprocess.check_output(cmd, shell=True)
    vm_config = json.loads(result)
    return {
        "size": vm_config[0],
        "disk_size": vm_config[1]
    }

def map_azure_vm_to_oci_shape(azure_size):
    # Extended mapping based on general VM types
    mapping = {
        # General purpose Azure VMs to OCI VM shapes
        "Standard_DS1_v2": "VM.Standard2.1",
        "Standard_DS2_v2": "VM.Standard2.2",
        "Standard_DS3_v2": "VM.Standard2.4",
        "Standard_DS4_v2": "VM.Standard2.8",
        "Standard_DS5_v2": "VM.Standard2.16",

        # Compute optimized Azure VMs to OCI VM shapes
        "Standard_F2s_v2": "VM.Standard.E3.Flex",
        "Standard_F4s_v2": "VM.Standard.E3.Flex",
        "Standard_F8s_v2": "VM.Standard.E3.Flex",
        "Standard_F16s_v2": "VM.Standard.E3.Flex",

        # Memory optimized Azure VMs to OCI VM shapes
        "Standard_E2_v3": "VM.Standard.E3.Flex",
        "Standard_E4_v3": "VM.Standard.E3.Flex",
        "Standard_E8_v3": "VM.Standard.E3.Flex",
        "Standard_E16_v3": "VM.Standard.E3.Flex",

        # GPU optimized Azure VMs to OCI VM shapes
        "Standard_NC6": "VM.GPU2.1",
        "Standard_NC12": "VM.GPU2.2",
        "Standard_NC24": "VM.GPU3.1",
        "Standard_NC24r": "VM.GPU3.2",

        # High performance Azure VMs to OCI VM shapes
        "Standard_H8": "VM.Standard2.16",
        "Standard_H16": "VM.Standard2.24",
        "Standard_H8m": "VM.Standard2.16",
        "Standard_H16m": "VM.Standard2.24",

        # Storage optimized Azure VMs to OCI VM shapes (Note: OCI doesn't have exact matches, so mapping to general shapes)
        "Standard_L4s": "VM.Standard2.8",
        "Standard_L8s": "VM.Standard2.16",
        "Standard_L16s": "VM.Standard2.24",
        "Standard_L32s": "VM.Standard2.48",

        # ... this is propably enough for our needs

    }
    return mapping.get(azure_size, "VM.Standard2.1")  # default to VM.Standard2.1 if not found


def oci_create_vm_from_image(qcow2_name, oci_shape):
    # Modify parameters as needed
    compartment_id = "YOUR_OCI_COMPARTMENT_ID"
    subnet_id = "YOUR_SUBNET_ID"
    cmd = f"oci compute instance launch --availability-domain XYZ:PHX-AD-1 --compartment-id {compartment_id} --shape {oci_shape} --image-id {qcow2_name} --subnet-id {subnet_id} --assign-public-ip true --wait-for-state RUNNING"
    subprocess.run(cmd, shell=True, check=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: script_name.py <vm-id>")
        sys.exit(1)

    vm_id = sys.argv[1]
    azure_create_snapshot(vm_id)
    vhd_name = azure_export_vhd(vm_id)
    qcow2_path = convert_vhd_to_qcow2(vhd_name)
    oci_upload_image(qcow2_path)
    oci_import_image(os.path.basename(qcow2_path))

    vm_config = get_vm_config(vm_id)
    oci_shape = map_azure_vm_to_oci_shape(vm_config["size"])
    oci_create_vm_from_image(os.path.basename(qcow2_path), oci_shape)
