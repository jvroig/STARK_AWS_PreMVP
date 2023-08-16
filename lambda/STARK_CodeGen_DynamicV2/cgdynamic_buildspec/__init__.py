#STARK Code Generator component.
#Produces the customized dynamic content for an Azure STARK system 

#Python Standard Library
import base64
import textwrap
import yaml
import boto3
import os

#Private modules
import convert_friendly_to_system as converter


def create(data):

    project_varname = data['project_varname']
    s3  = boto3.client('s3')

    codegen_bucket_name  = os.environ['CODEGEN_BUCKET_NAME']
    response = s3.get_object(
        Bucket=codegen_bucket_name,
        Key=f'STARKConfiguration/STARK_config.yml'
    )
    config = yaml.safe_load(response['Body'].read().decode('utf-8'))

    system_prelaunch_arn = config["PrelaunchV2_ARN"]
    

    source_code = f"""\
        version: 0.2

        env:
            variables:
                ARM_SUBSCRIPTION_ID: "{os.environ["ARM_SUBSCRIPTION_ID"]}"
                ARM_CLIENT_ID: "{os.environ["ARM_CLIENT_ID"]}"
                ARM_CLIENT_SECRET: "{os.environ["ARM_CLIENT_SECRET"]}"
                ARM_TENANT_ID: "{os.environ["ARM_TENANT_ID"]}"
                CODEGEN_BUCKET_NAME: {codegen_bucket_name}

        phases:
            install:
                runtime-versions:
                    python: 3.8
                commands:
                    - curl -s -qL -o terraform_install.zip https://releases.hashicorp.com/terraform/1.4.0/terraform_1.4.0_linux_amd64.zip
                    - unzip terraform_install.zip -d /usr/bin/
                    - chmod +x /usr/bin/terraform
                finally:
                    - terraform --version
            build:
                commands:
                - BUCKET={codegen_bucket_name}
                - sed -i "s/RandomTokenFromBuildScript/$(date)/" template.yml
                - aws s3 sync s3://$BUCKET/codegen_dynamic/{project_varname}/terraform/ terraform/
                - python3 ./packager.py
                - pip install pymongo --target functions_package
                - cd terraform/database
                - terraform init
                - terraform apply --auto-approve
                - python3 ../../terraform_output_utility.py
                - cd ..
                - terraform init
                - terraform apply --auto-approve
                - python ../terraform_output_static_site_url.py
                - python ../store_terraform_files_to_bucket.py
                - aws lambda invoke --function-name {system_prelaunch_arn} --payload file://../cgdynamic_payload.json response.json

        artifacts:
            files:
                - template.yml
                - outputtemplate.yml
                - template_configuration.json
        """

    return textwrap.dedent(source_code)