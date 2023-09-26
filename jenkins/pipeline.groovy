pipeline {
    agent any
    
    stages {
        stage('AzureToOCI') {
            steps {
                script {
                    def vm_name = 'your_vm_name'
                    def resource_group = 'your_resource_group'
                    def compartment_id = 'your_compartment_id'
                    def subnet_id = 'your_subnet_id'
                    
                    // Execute the shell script for the AzureToOCI job
                    sh "./azure-to-oci.py ${vm_name} ${resource_group} ${compartment_id%\\ -*} ${subnet_id%\\ -*}"
                    
                    // Trigger the second job "Migrate Extra Disks"
                    def migrateExtraDisks = build(
                        job: 'Migrate Extra Disks',
                        parameters: [
                            string(name: 'vm_name', value: vm_name),
                            string(name: 'resource_group', value: resource_group),
                            string(name: 'compartment_id', value: compartment_id),
                            string(name: 'subnet_id', value: subnet_id)
                        ]
                    )
                }
            }
        }
    }
}
pipeline {
    agent any
    
    stages {
        stage('AzureToOCI') {
            steps {
                script {
                    def vm_name = 'your_vm_name'
                    def resource_group = 'your_resource_group'
                    def compartment_id = 'your_compartment_id'
                    def subnet_id = 'your_subnet_id'
                    
                    // Execute the shell script for the AzureToOCI job
                    sh "./azure-to-oci.py ${vm_name} ${resource_group} ${compartment_id%\\ -*} ${subnet_id%\\ -*}"
                    
                    // Trigger the second job "Migrate Extra Disks"
                    def migrateExtraDisks = build(
                        job: 'Migrate Extra Disks',
                        parameters: [
                            string(name: 'vm_name', value: vm_name),
                            string(name: 'resource_group', value: resource_group),
                            string(name: 'compartment_id', value: compartment_id),
                            string(name: 'subnet_id', value: subnet_id)
                        ]
                    )
                }
            }
        }
    }
}

