#!/usr/bin/env python3
import subprocess
import os
import sys

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

