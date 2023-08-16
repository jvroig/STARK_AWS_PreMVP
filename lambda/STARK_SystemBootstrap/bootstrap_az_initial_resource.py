#STARK Code Generator component.
#Produces the customized dynamic content for a STARK system

#Python Standard Library
import base64
import textwrap

#Private modules
import convert_friendly_to_system as converter

def create_store_terraform_files_to_bucket(data):

    source_code = f"""\
    import boto3
    import os

    s3  = boto3.client('s3')
    codegen_bucket_name  = os.environ['CODEGEN_BUCKET_NAME']
    project_varname      = '{converter.convert_to_system_name(data["project_name"])}'

    def put_to_s3_terraform_directory(filename, file_content):
        response = s3.put_object(
            Body=file_content,
            Bucket=codegen_bucket_name,
            Key=f'codegen_dynamic/{{project_varname}}/terraform/{{filename}}'
        )
      
    directory_path = "."
    # Traverse the directory and collect file paths
    file_paths = []
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_paths.append(file_path)

    # Collect files to store in s3
    for file_path in file_paths:
        filename = os.path.basename(file_path)
        tf_script_and_state_files = [
                                'main.tf', 'database.tf', 'terraform.tfstate', '.terraform.lock.hcl', 'terraform.tfstate.backup',
                                'api_management.tf', 'stark_modules_collection.tf', 'business_modules_collection.tf', 'functions.tf',
                                'static_site_hosting.tf', 'resource_group.tf', 'variables.tf'
        ]
        if filename in tf_script_and_state_files:
            with open(file_path, 'r') as file:
                file_content = file.read()
                put_to_s3_terraform_directory(filename, file_content)
    """

    return textwrap.dedent(source_code)