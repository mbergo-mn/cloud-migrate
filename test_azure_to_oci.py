import unittest
from unittest.mock import patch
import azure_to_oci  # Assuming the script is named azure_to_oci.py and is importable

class TestAzureToOCI(unittest.TestCase):

    @patch('subprocess.run')
    def test_azure_create_snapshot(self, mock_run):
        azure_to_oci.azure_create_snapshot("vm_name")
        mock_run.assert_called_with("az snapshot create --name vm_name-snapshot --resource-group YOUR_RESOURCE_GROUP --source YOUR_DISK_NAME", shell=True, check=True)

    @patch('subprocess.run')
    def test_azure_export_vhd(self, mock_run):
        azure_to_oci.azure_export_vhd("snapshot_name")
        mock_run.assert_called_with("az snapshot export --name snapshot_name --resource-group YOUR_RESOURCE_GROUP --destination YOUR_DESTINATION", shell=True, check=True)

    @patch('subprocess.run')
    def test_convert_vhd_to_qcow2(self, mock_run):
        azure_to_oci.convert_vhd_to_qcow2("path/to/file.vhd")
        mock_run.assert_called_with("qemu-img convert -f vpc -O qcow2 path/to/file.vhd path/to/file.qcow2", shell=True, check=True)

    @patch('subprocess.run')
    def test_oci_upload_image(self, mock_run):
        azure_to_oci.oci_upload_image("path/to/file.qcow2")
        mock_run.assert_called_with("oci os object put --bucket-name YOUR_BUCKET_NAME --file path/to/file.qcow2 --name file.qcow2", shell=True, check=True)

    @patch('subprocess.run')
    def test_oci_import_image(self, mock_run):
        azure_to_oci.oci_import_image("file.qcow2")
        mock_run.assert_called_with("oci compute image import from-object --namespace YOUR_NAMESPACE --bucket-name YOUR_BUCKET_NAME --name file.qcow2 --source-image-type qcow2", shell=True, check=True)

    @patch('subprocess.run')
    def test_oci_create_vm_from_image(self, mock_run):
        azure_to_oci.oci_create_vm_from_image("file.qcow2", "VM.Standard2.1")
        mock_run.assert_called_with("oci compute instance launch --availability-domain XYZ:PHX-AD-1 --compartment-id YOUR_OCI_COMPARTMENT_ID --shape VM.Standard2.1 --image-id file.qcow2 --subnet-id YOUR_SUBNET_ID --assign-public-ip true --wait-for-state RUNNING", shell=True, check=True)

if __name__ == '__main__':
    unittest.main()

