#!/usr/bin/env python3

import subprocess
import os
import sys
import json
import time


# Globals
oci_urlspace = "id8hewq9h9im" 
bucket_name="azure-to-oci" # Modify as needed, but this is the bucket used for the migration


# Function to retrieve VM configuration from Azure
def get_vm_config(vm_name):
    # Construct the Azure CLI command to get VM details
    cmd = f"az vm show --resource-group {resource_group} --name {vm_name} --query \"[storageProfile.osDisk.name, storageProfile.dataDisks[0].name]\""
    result = subprocess.check_output(cmd, shell=True)
    vm_config = json.loads(result)
    return {
        "boot_disk": str(vm_config[0]),
        "data_disk": str(vm_config[1])
    }

# Function to create a snapshot of the VM disk in Azure
def azure_create_snapshot(disk_name, vm_name):
        print("Creating snapshot in Azure...")
        disk_id = get_vm_config(vm_name)['data_disk']
        cmd = f"az snapshot create --name {disk_name}-snapshot --resource-group {resource_group} --source {disk_id}"
        subprocess.run(cmd, shell=True, check=True)

# Remove encryptio from snapshot
def azure_remove_encryption(vhd_name):
    print("Removing encryption from snapshot...")
    cmd = f"az disk-encryption-set delete --name {vhd_name}-snapshot --resource-group {resource_group}"
    subprocess.run(cmd, shell=True, check=True)

# Function to export the VHD of the VM snapshot in Azure
def azure_export_vhd(disk_name):
    print("Exporting VHD from Azure...")
    cmd = f"az snapshot grant-access --name \"{disk_name}-snapshot\" --resource-group \"{resource_group}\" --duration-in-seconds 3600 --query \"accessSas\""
    url = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE)
    return url.stdout.decode('utf-8').strip("\"").strip("\n")

# Function to download the VHD file from Azure
def get_vhd_azure_url(disk_name, snapshot_url):
    print("Downloading VHD from Azure...")
    cmd = f"wget --retry-connrefused --waitretry=1 --read-timeout=20 --timeout=15 -O {disk_name} \"{snapshot_url}"
    subprocess.run(cmd, shell=True, check=True)

# Function to convert VHD file to QCOW2 format
def convert_vhd_to_qcow2(vhd_name, qcow2_file):
    print("Converting VHD to QCOW2...")
    cmd = f"qemu-img convert -p -f vpc -O qcow2 {vhd_name} {qcow2_file}"
    subprocess.run(cmd, shell=True, check=True)

# Function to upload QCOW2 file to OCI object storage
def oci_upload_image(qcow2_file):
    print("Uploading QCOW2 to OCI object storage...")
    bucket_url = "oci-migration"  # Modify as needed
    cmd = f"oci os object put -bn {bucket_name} --file {qcow2_file} -ns {oci_urlspace}"
    try:
        subprocess.run(cmd, shell=True, check=True)
    except:
        pass

# Function to import QCOW2 file as an image in OCI compute
def oci_import_image(qcow2_file):
    print("Importing QCOW2 to OCI compute...")
    cmd = f"oci compute image import from-object -bn {bucket_name} --compartment-id {compartment_id} --name {qcow2_file} -ns {oci_urlspace} display-name {qcow2_file} --operating-system \"{os_type}\" --source-image-type QCOW2 --launch-mode PARAVIRTUALIZED"
    try:
        subprocess.run(cmd, shell=True, check=True)
    except:
        print("Image already exists. Skipping...")
        pass

# Function to check the if the image status is AVAILABLE
def oci_check_image_status(qcow2_file):
    print("Checking OCI image status...")
    cmd = f"oci compute image list --compartment-id {compartment_id} --display-name {qcow2_file} --query 'data[0].\"lifecycle-state\"'"
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8').strip().strip('"')

# Check image id
def oci_check_image_id(qcow2_file):
    cmd = f"oci compute image list --compartment-id {compartment_id} --display-name {qcow2_file} --query \"data[0].id\""
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
    return str(result.stdout.decode('utf-8').strip().strip('"'))

# Function to get the id of the image from the bucket
def oci_get_image_id(qcow2_file):
    print("Getting image id...")
    cmd = f"oci compute image list --compartment-id {compartment_id} --display-name {qcow2_file} --query \"data[0].id\""
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
    return str(result.stdout.decode('utf-8').strip().strip('"'))

# Function to create a VM in OCI from the imported image
def oci_create_vm_from_image(qcow2_file, oci_shape):
    print("Creating VM in OCI...")
    cmd = f"oci compute instance launch --availability-domain UIVj:US-ASHBURN-AD-1 --compartment-id {compartment_id} --shape {oci_shape} --shape-config \"{oci_shape_config}\" --image-id {qcow2_file} --subnet-id {subnet_id} --assign-public-ip false --display-name {vm_name}"
    subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE)

# Function to check the status of the instance
def oci_check_instance_status(vm_name):
    print("Checking instance status...")
    cmd = f"oci compute instance list --compartment-id {compartment_id} --display-name {vm_name} --query \"data[0].\"lifecycle-state\""
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8').strip().strip('"')

# Function to attach the boot disk to the instance
def attach_boot_disk(boot_disk_id, vm_name):
    print("Attaching boot disk to instance...")
    cmd = f"oci compute boot-volume-attachment attach --boot-volume-id {boot_disk_id} --instance-id {vm_name} --type PARAVIRTUALIZED"
    subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE)

# Function to terminate the instance
def oci_terminate_instance(vm_name):
    print("Terminating instance...")
    cmd = f"oci compute instance terminate --instance-id {vm_name} --preserve-boot-volume true"
    subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE)

# Function to reboot the instance
def oci_reboot_instance(vm_name):
    print("Rebooting instance...")
    cmd = f"oci compute instance action --action SOFTRESET --instance-id {vm_name}"
    subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE)

# Main function
if __name__ == "__main__":
    if len(sys.argv) < 7:
        print("Usage: azure_to_oci.py <vm-id> <resource-group> <compartment-id> <subnet-id> <data-disk> <os-type>")
        sys.exit(1)

    vm_name = sys.argv[1]
    resource_group = str(sys.argv[2])
    compartment_id = str(sys.argv[3])
    subnet_id = str(sys.argv[4])
    data_disk = bool(sys.argv[5])
    os_type = str(sys.argv[6])

    # image qcow2 file name
    qcow2_file = f"{vm_name}.qcow2"

    # temporary instance name
    vm_name_temp = f"{vm_name}-temp"

    # image vhd file name
    vhd_name = f"{vm_name}.vhd"

    # create the snapshot of the VM disk
    azure_create_snapshot(vhd_name, vm_name)

    # remove encryption from snapshot
    azure_remove_encryption(vhd_name)

    # get the snapshot url of the VM disk
    vhd_url = azure_export_vhd(vhd_name)

    # shape instance to be create on OCI
    oci_shape = "VM.Standard3.Flex"
    oci_shape_config = {
        "Ocpus": int(1),
        "MemoryInGBs": int(16)
    }
    # download the VHD file
    get_vhd_azure_url(vhd_name, vhd_url)

    # convert the VHD file to QCOW2
    convert_vhd_to_qcow2(vhd_name, qcow2_file)

    # upload the QCOW2 file to OCI object storage
    oci_upload_image(qcow2_file)

    # import the QCOW2 file to OCI compute
    oci_import_image(qcow2_file)

    # check if the image is available
    while True:
        if oci_check_image_status(qcow2_file) == "AVAILABLE":
            break
        else:
            print("Waiting for image to be available...")
            time.sleep(60)

    # get the image id
    image_id = oci_check_image_id(qcow2_file)

    # get the disk id
    oci_disk_size = get_vm_config(vm_name_temp)["boot_disk"]
    # get the instance id
    custom_image_id = oci_get_image_id(qcow2_file)
    # spawn a instance with the image
    oci_create_vm_from_image(custom_image_id, oci_shape, int(oci_disk_size))
    # wait for the instance to be in running state
    while True:
        if oci_check_instance_status(vm_name_temp) == "RUNNING":
            break
        else:
            print("Waiting for instance to be running...")
            time.sleep(60)
    # get the boot disk id
    boot_disk_id = get_vm_config(vm_name_temp)["boot_disk"]
    # kill the instance
    oci_terminate_instance(vm_name_temp)
    # attach the boot disk to the instance
    attach_boot_disk(boot_disk_id, vm_name)
    # Reboot the instance
    oci_reboot_instance(vm_name)
    