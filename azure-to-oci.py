#!/usr/bin/env python3

import subprocess
import os
import sys
import json


# Globals
oci_urlspace = "id8hewq9h9im" # Modify as needed, but this is the bucket used for the migration
bucket_url="azure-to-oci"
resource_group = str(sys.argv[2])
compartment_id = str(sys.argv[3])
subnet_id = str(sys.argv[4])


# Function to retrieve VM configuration from Azure
def get_vm_config(vm_name):
    # Construct the Azure CLI command to get VM details
    cmd = f"az vm show --resource-group {resource_group} --name {vm_name} --query \"[hardwareProfile.vmSize, storageProfile.dataDisks[].diskSizeGb[], storageProfile.osDisk.name]\""
    result = subprocess.check_output(cmd, shell=True)
    vm_config = json.loads(result)
    return {
        "size": vm_config[0],
        "disk_size": str(vm_config[1]),
        "disk_id": vm_config[2]
    }

# Function to create a snapshot of the VM disk in Azure
def azure_create_snapshot(vm_name):
    print("Creating snapshot in Azure...")
    disk_id = get_vm_config(vm_name)['disk_id']
    cmd = f"az snapshot create --name {vm_name}-snapshot --resource-group {resource_group} --source {disk_id}"
    subprocess.run(cmd, shell=True, check=True)

# Function to export the VHD of the VM snapshot in Azure
def azure_export_vhd(vm_name):
    print("Exporting VHD from Azure...")
    cmd = f"az snapshot grant-access --name \"{vm_name}-snapshot\" --resource-group \"{resource_group}\" --duration-in-seconds 3600 --query \"accessSas\""
    url = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE)
    return url.stdout.decode('utf-8').strip("\"")

# Function to download the VHD file from Azure
def get_vhd_azure_url(vm_name, snapshot_url):
    print("Downloading VHD from Azure...")
    vhd_name = f"{vm_name}.vhd"
    cmd = f"wget --retry-connrefused --waitretry=1 --read-timeout=20 --timeout=15 -O \"{vhd_name}\" \"{snapshot_url}\""
    subprocess.run(cmd, shell=True, check=False)

# Function to convert VHD file to QCOW2 format
def convert_vhd_to_qcow2(vhd_name, qcow2_file):
    print("Converting VHD to QCOW2...")
    cmd = f"qemu-img convert -f vpc -O qcow2 {vhd_name} {qcow2_file}"
    subprocess.run(cmd, shell=True, check=False)

# Function to upload QCOW2 file to OCI object storage
def oci_upload_image(qcow2_file):
    print("Uploading QCOW2 to OCI object storage...")
    bucket_url = "oci-migration"  # Modify as needed
    cmd = f"oci os object put --name {qcow2_file} -ns {oci_urlspace} --file {qcow2_file} -bn {bucket_url} --file {qcow2_file}"
    subprocess.run(cmd, shell=True, check=True)

# Function to import QCOW2 file as an image in OCI compute
def oci_import_image(qcow2_file):
    print("Importing QCOW2 to OCI compute...")
    cmd = f"oci compute image import from-object --namespace myurlspace --bucket-url mybucket --name {qcow2_file} --source-image-type qcow2 --wait-for-state AVAILABLE"
    subprocess.run(cmd, shell=True, check=True)

# Function to map Azure VM size to OCI VM shape
def map_azure_vm_to_oci_shape(azure_size):
    print("Mapping Azure VM size to OCI VM shape...")
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

# Function to create a VM in OCI from the imported image
def oci_create_vm_from_image(qcow2_file, oci_shape, oci_disk_size):
    print("Creating VM in OCI...")
    cmd = f"oci compute instance launch --availability-domain XYZ:PHX-AD-1 --compartment-id {compartment_id} --shape {oci_shape} --image-id {qcow2_file} --subnet-id {subnet_id} --assign-public-ip true --boot-volume-size-in-gbs {oci_disk_size} --wait-for-state RUNNING"
    subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE)

# Main function
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: script_url.py <vm-id> <compartment-id> <subnet-id>")
        sys.exit(1)

    # url of the VM on Azure
    vm_name = sys.argv[1]

    # image qcow2 file name
    qcow2_file = f"{vm_name}.qcow2"

    # image vhd file name
    vhd_name = f"{vm_name}.vhd"

    # create the snapshot of the VM disk
    azure_create_snapshot(vm_name)

    # get the snapshot url of the VM disk
    vhd_url = azure_export_vhd(vm_name)

    # download the VHD file
    get_vhd_azure_url(vm_name, vhd_url)

    # convert the VHD file to QCOW2
    convert_vhd_to_qcow2(vhd_name, qcow2_file)

    # upload the QCOW2 file to OCI object storage
    oci_upload_image(qcow2_file)

    # import the QCOW2 file to OCI compute
    oci_import_image(qcow2_file)

    # create the VM from the imported image
    oci_shape = map_azure_vm_to_oci_shape(vm_name)["size"]
    oci_disk_size = get_vm_config(vm_name)["disk_size"]
    oci_disk = + oci_disk_size + (oci_disk_size*50/100)
    oci_create_vm_from_image(qcow2_file, oci_shape, oci_disk)

