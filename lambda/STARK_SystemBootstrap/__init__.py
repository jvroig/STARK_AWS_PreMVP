#This will create files needed to bootstrap a new system after the CI/CD pipeline for it is created by STARK,
#   but before the actual system infra is laid out.

#Python Standard Library
import base64
import json
import os
import textwrap

#Extra modules
import yaml
import boto3
import botocore
from crhelper import CfnResource

#Private modules
import bootstrap_sam_template as boot_sam
import bootstrap_template_conf as boot_conf
import convert_friendly_to_system as converter

s3   = boto3.client('s3')
lmb  = boto3.client('lambda')
git  = boto3.client('codecommit')

helper = CfnResource() #We're using the AWS-provided helper library to minimize the tedious boilerplate just to signal back to CloudFormation

@helper.create
@helper.update
def create_handler(event, context):
    project_name    = event.get('ResourceProperties', {}).get('Project','')
    repo_name       = event.get('ResourceProperties', {}).get('RepoName','')
    cicd_bucket     = event.get('ResourceProperties', {}).get('CICDBucket','')
    
    project_varname = converter.convert_to_system_name(project_name)

    #DynamoDB table name from our CF template
    ddb_table_name = event.get('ResourceProperties', {}).get('DDBTable','')

    #Bucket for our generated lambda deploymentment packages and cloud resources document
    codegen_bucket_name = os.environ['CODEGEN_BUCKET_NAME']

    #Cloud resources document
    response = s3.get_object(
        Bucket=codegen_bucket_name,
        Key=f'codegen_dynamic/{project_varname}/{project_varname}.yaml'
    )
    cloud_resources = yaml.safe_load(response['Body'].read().decode('utf-8')) 
    cloud_provider = cloud_resources["Cloud Provider"]
    
    if cloud_provider == 'AWS':
        import bootstrap_buildspec as boot_build
    else:
        import bootstrap_az_buildspec as boot_build
        import bootstrap_az_initial_resource as boot_initial_resource

    models   = cloud_resources["Data Model"]
    entities = []
    for entity in models: entities.append(entity)

    files_to_commit = []

    ###########################################
    #Create build files we need to bootstrap our pipeline:
    # - template.yml
    # - buildspec.yml
    data = {
        'project_varname': project_varname,
        'cicd_bucket': cicd_bucket
    }

    source_code = boot_build.create(data)
    files_to_commit.append({
        'filePath': "buildspec.yml",
        'fileContent': source_code.encode()
    })
    

    data = { 
        'cloud_resources': cloud_resources,
        'repo_name': repo_name
    }
    source_code = boot_sam.create(data)
    files_to_commit.append({
        'filePath': "template.yml",
        'fileContent': source_code.encode()
    })   

    source_code = boot_conf.create()
    files_to_commit.append({
        'filePath': "template_configuration.json",
        'fileContent': source_code.encode()
    })  

    ##FIXME: For clean up, leave here for the meantime while testing 
    data = {"project_name": project_name}

    if cloud_provider != 'AWS':
        source_code = f"""\
        {{
            "ResourceProperties": {{
                "Project": "{project_name}",
                "DDBTable": "willbechangedtomongodb",
                "CICDBucket": "{cicd_bucket}",
                "Bucket": "TestBucket",
                "RepoName": "{repo_name}"
            }}
        }}"""

        files_to_commit.append({
            'filePath': "cgdynamic_payload.json",
            'fileContent': source_code.encode()
        }) 

        source_code = f"""\
        {{
            "ResourceProperties": {{
                "Project": "{project_name}",
                "DDBTable": "willbechangedtomongodb",
                "CICDBucket": "{cicd_bucket}",
                "Bucket": "TestBucket",
                "RepoName": "{repo_name}",
                "ApiGatewayId": "tobeadded"
            }}
        }}"""

        files_to_commit.append({
            'filePath': "cgstatic_payload.json",
            'fileContent': source_code.encode()
        }) 

        source_code = boot_initial_resource.create_store_terraform_files_to_bucket(data)
        files_to_commit.append({
            'filePath': "store_terraform_files_to_bucket.py",
            'fileContent': source_code.encode()
        }) 

    ############################################
    #Commit our static files to the project repo
    #We have a try-except block here to distringuish a CREATE from an UPDATE.
    #During CF CREATE, there isn't a branch yet, so it goes to the except block
    #During CF UPDATE, we need the parent commit id because it won't be the first commmit anymore

    try:
        response = git.get_branch(
            repositoryName=repo_name,
            branchName='master'        
        )
        commit_id = response['branch']['commitId']
        response = git.create_commit(
            repositoryName=repo_name,
            branchName='master',
            parentCommitId=commit_id,
            authorName='STARK::Bootstrapper',
            email='STARK@fakedomainstark.com',
            commitMessage='Initial commit - bootstrapper',
            putFiles=files_to_commit
        )
    except botocore.exceptions.ClientError as error:
        #Branch doesn't exist yet, because we are in a CREATE op instead of UPDATE.
        #No need for a parent commit id

        response = git.create_commit(
            repositoryName=repo_name,
            branchName='master',
            authorName='STARK::Bootstrapper',
            email='STARK@fakedomainstark.com',
            commitMessage='Initial commit - bootstrapper',
            putFiles=files_to_commit
        )



@helper.delete
def no_op(_, __):
    pass


def lambda_handler(event, context):
    helper(event, context)