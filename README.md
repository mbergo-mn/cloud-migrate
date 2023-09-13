# VM Migration from Azure to OCI

This script facilitates the process of migrating a VM from Azure to Oracle Cloud Infrastructure (OCI). It does so by snapshotting the Azure VM, exporting the snapshot, converting the image for compatibility with OCI, uploading the image to OCI Object Storage, and finally importing the image to OCI VMs.

## Prerequisites

1. Install `azure-cli`, `oci-cli`, and `qemu-img`.
   - For azure-cli: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli
   - For oci-cli: https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm
   - For qemu-img: Install via package manager depending on your OS (e.g., `apt-get install qemu-utils` for Debian/Ubuntu)

2. Ensure you're authenticated for both `azure-cli` and `oci-cli` on your machine.

3. Modify the script to include your specific details like Azure resource group, storage account, OCI namespace, and bucket.

## Usage

Ensure the script is executable:

