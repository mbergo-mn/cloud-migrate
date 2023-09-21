import pytest
from unittest.mock import patch
import azure_to_oci  # Import the script as a module

def test_get_vm_config():
    with patch('azure_to_oci.subprocess') as mock_subprocess:
        mock_subprocess.check_output.return_value = b'["Standard_DS2_v2", [30], "osDiskName"]'
        result = azure_to_oci.get_vm_config('vm_name')
        assert result == {"size": "Standard_DS2_v2", "disk_size": "[30]", "disk_id": "osDiskName"}