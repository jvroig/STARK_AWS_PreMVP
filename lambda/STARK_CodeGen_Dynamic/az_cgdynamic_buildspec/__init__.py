#STARK Code Generator component.
#Produces the customized dynamic content for an Azure STARK system 

#Python Standard Library
import base64
import textwrap

#Private modules
import convert_friendly_to_system as converter


def create(data):

    project_varname = data['project_varname']
    

    source_code = f"""\
        version: 0.2

        env:
            variables:
                ARM_SUBSCRIPTION_ID: "6e672af2-b111-49d2-8291-46038afe5f04"
                ARM_CLIENT_ID: "77514469-7062-46da-9d6b-6fc027e7722a"
                ARM_CLIENT_SECRET: "aBx8Q~M2x~tFFQGWxD-AFd3WcIpwvfTLT5sQOcCm"
                ARM_TENANT_ID: "c2051487-3f8f-4ee3-b98b-c6d53c2daf07"

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
                - BUCKET=$(cat template_configuration.json | python3 -c "import sys, json; print(json.load(sys.stdin)['Parameters']['UserCICDPipelineBucketNameParameter'])")
                - WEBSITE=$(cat template_configuration.json | python3 -c "import sys, json; print(json.load(sys.stdin)['Parameters']['UserWebsiteBucketNameParameter'])")
                - sed -i "s/RandomTokenFromBuildScript/$(date)/" template.yml
                - cp -R lambda lambda_src
                - pip install pyyaml
                - python3 ./builder.py
                - terraform init
                - terraform plan

        artifacts:
            files:
                - template.yml
                - outputtemplate.yml
                - template_configuration.json
        """

    return textwrap.dedent(source_code)