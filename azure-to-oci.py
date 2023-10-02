#!/usr/bin/env python3

import subprocess
import os
import sys
import json
import time


# Globals
oci_urlspace = "id8hewq9h9im" # Modify as needed, but this is the bucket used for the migration
bucket_name="azure-to-oci"
resource_group = str(sys.argv[2])
compartment_id = str(sys.argv[3])
subnet_id = str(sys.argv[4])
data_disk=str(sys.argv[5])
os_type=str(sys.argv[6])

# Function to retrieve VM configuration from Azure
def get_vm_config(vm_name):
    # Construct the Azure CLI command to get VM details
    cmd = f"az vm show --resource-group {resource_group} --name {vm_name} --query \"[hardwareProfile.vmSize, storageProfile.dataDisks[].diskSizeGb[], storageProfile.osDisk.name, storageProfile.dataDisks[0].name]\""
    result = subprocess.check_output(cmd, shell=True)
    vm_config = json.loads(result)
    return {
        "size": str(vm_config[0]),
        "disk_size": 0,
        "disk_id": vm_config[2],
        "extra_disk": str(vm_config[3])
    }

# Function to create a snapshot of the VM disk in Azure
def azure_create_snapshot(disk_name, vm_name):
    if not data_disk:
        print("Creating snapshot in Azure...")
        disk_id = get_vm_config(vm_name)['disk_id']
        cmd = f"az snapshot create --name {disk_name}-snapshot --resource-group {resource_group} --source {disk_id}"
        subprocess.run(cmd, shell=True, check=True)
    else:
        print("Creating extra disk snapshot in Azure...")
        extra_disk_id = get_vm_config(vm_name)['extra_disk']
        cmd = f"az snapshot create --name {disk_name}-snapshot --resource-group {resource_group} --source {extra_disk_id}"
        subprocess.run(cmd, shell=True, check=True)

# Remove encryptio from snapshot
def azure_remove_encryption(vm_name):
    print("Removing encryption from snapshot...")
    cmd = f"az disk-encryption-set delete --name {vm_name}-snapshot --resource-group {resource_group}"
    subprocess.run(cmd, shell=True, check=True)

# Function to export the VHD of the VM snapshot in Azure
def azure_export_vhd(disk_name):
    print("Exporting VHD from Azure...")
    cmd = f"az snapshot grant-access --name \"{disk_name}-snapshot\" --resource-group \"{resource_group}\" --duration-in-seconds 3600 --query \"accessSas\""
    url = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE)
    return url.stdout.decode('utf-8').strip("\"")

# Function to download the VHD file from Azure
def get_vhd_azure_url(disk_name, snapshot_url):
    print("Downloading VHD from Azure...")
    cmd = f"wget --retry-connrefused --waitretry=1 --read-timeout=20 --timeout=15 -O {disk_name}.vhd {snapshot_url}"
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
    cmd = f"oci compute image import from-object -bn {bucket_name} --file {qcow2_file} --compartment-id {compartment_id} --name {qcow2_file} -ns {oci_urlspace} --operating-system \"{os_type}\" --source-image-type QCOW2 --launch-mode PARAVIRTUALIZED"
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

# Function to map Azure VM size to OCI VM shape
def map_azure_vm_to_oci_shape(azure_size):
    # Extended mapping based on general VM types
    mapping = {
    "Standard_D1_v2": ["1", "3.5"],
    "Standard_D2_v2": ["2", "7"],
    "Standard_D3_v2": ["4", "14"],
    "Standard_D4_v2": ["8", "28"],
    "Standard_D5_v2": ["16", "56"],
    "Standard_DS1_v2": ["1", "3.5"],
    "Standard_DS2_v2": ["2", "7"],
    "Standard_DS3_v2": ["4", "14"],
    "Standard_DS4_v2": ["8", "28"],
    "Standard_F2s_v2": ["2", "4"],
    "Standard_F4s_v2": ["4", "8"],
    "Standard_F8s_v2": ["8", "16"],
    "Standard_F16s_v2": ["16", "32"],
    "Standard_E2_v3": ["2", "16"],
    "Standard_E4_v3": ["4", "32"],
    "Standard_E8_v3": ["8", "64"],
    "Standard_E16_v3": ["16", "128"],
    "Standard_E2s_v3": ["2", "16"],
    "Standard_E4s_v3": ["4", "32"],
    "Standard_E8s_v3": ["8", "64"],
    "Standard_E16s_v3": ["16", "128"],
    "Standard_NC6": ["6", "56"],
    "Standard_NC12": ["12", "112"],
    "Standard_NC24": ["24", "224"],
    "Standard_NC24r": ["24", "224"],
    "Standard_L4s": ["4", "32.0"],
    "Standard_L8s": ["8", "64.0"],
    "Standard_L16s": ["16", "128.0"],
    "Standard_L32s": ["32", "256.0"],
    "Standard_M64s": ["64", "256"],
    }
    return list(mapping.get(azure_size, ["4", "16"]))

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

# Main function
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: script_url.py <vm-id> <resource-group> <compartment-id> <subnet-id>")
        sys.exit(1)

    # url of the VM on Azure
    vm_name = sys.argv[1]

    # image qcow2 file name
    qcow2_file = f"{vm_name}.qcow2"

    # image vhd file name
    vhd_name = f"{vm_name}.vhd"

    # create the snapshot of the VM disk
    azure_create_snapshot(vhd_name, vm_name)

    # remove encryption from snapshot
    azure_remove_encryption(vhd_name)

    # get the snapshot url of the VM disk
    vhd_url = azure_export_vhd(vhd_name)

    # shape instance to be create on OCI
    az_size = get_vm_config(vm_name)["size"]
    oci_shape = "VM.Standard3.Flex"
    oci_shape_config = {
        "Ocpus": int(map_azure_vm_to_oci_shape(az_size)[0])/2,
        "MemoryInGBs": int(map_azure_vm_to_oci_shape(az_size)[1])
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

    # # create the VM from the imported image
    oci_disk_size = get_vm_config(vm_name)["disk_size"]
    custom_image_id = oci_get_image_id(qcow2_file)
    oci_create_vm_from_image(custom_image_id, oci_shape, int(oci_disk_size))
    if data_disk:
        extra_disk = get_vm_config(vm_name)["extra_disk"]
        # Take a snaoshot of the extra disk
        azure_create_snapshot(extra_disk, vm_name)
        # Remove encryption from the snapshot
        azure_remove_encryption(extra_disk)
        # Get the snapshot url of the extra disk
        vhd_url = azure_export_vhd(extra_disk)
        # download the VHD file
        get_vhd_azure_url(extra_disk, vhd_url)
        # convert the VHD file to QCOW2
        qcow2_extra = f"{extra_disk}.qcow2"
        convert_vhd_to_qcow2(extra_disk, qcow2_extra)
        # upload to the oci object storage
        oci_upload_image(qcow2_extra)
        # import the QCOW2 file to OCI compute
        oci_import_image(qcow2_extra)
        # check if the image is available
        while True:
            if oci_check_image_status(qcow2_extra) == "AVAILABLE":
                break
            else:
                print("Waiting for image to be available...")
                time.sleep(60)

        # get the image id
        cutom_image_id = oci_check_image_id(qcow2_extra) 
        # spawn a instance with the image
        oci_create_vm_from_image(custom_image_id, oci_shape, int(oci_disk_size))
        # get the instance id
        instance_id = oci_get_image_id(vm_name)
        # destroy the instance without removing the boot volume
        cmd = f"oci compute instance terminate --instance-id {instance_id} --preserve-boot-volume true"
        subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE)
        # get the id of the boot volume
        cmd = f"oci compute boot-volume-attachment list --instance-id {instance_id} --query \"data[0].bootVolumeId\""
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
        # Attach the boot volume to the main instance
        cmd = f"oci compute boot-volume-attachment attach --instance-id {instance_id} --boot-volume-id {result.stdout.decode('utf-8').strip().strip('{{').strip('}}')} --device \"/dev/sdb\""

        subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE)
        # reboot the original instance
        cmd = f"oci compute instance reboot --instance-id {instance_id}"
        subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE)
