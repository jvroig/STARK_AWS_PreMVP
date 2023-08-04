#STARK Code Generator component.
#Produces the customized dynamic content for a STARK system (Lambda / serverless resources)

#Python Standard Library
import base64
import json
import pickle
import os
import textwrap
import importlib

#Extra modules
import yaml
import boto3
from crhelper import CfnResource

#Private modules
prepend_dir = ""
if 'libstark' in os.listdir():
    prepend_dir = "libstark.STARK_CodeGen_Dynamic."

cg_login     = importlib.import_module(f"{prepend_dir}cgdynamic_login")
cg_logout    = importlib.import_module(f"{prepend_dir}cgdynamic_logout")
cg_builder   = importlib.import_module(f"{prepend_dir}cgdynamic_builder")
cg_ddb       = importlib.import_module(f"{prepend_dir}cgdynamic_dynamodb")
cg_build     = importlib.import_module(f"{prepend_dir}cgdynamic_buildspec")
cg_auth      = importlib.import_module(f"{prepend_dir}cgdynamic_authorizer")
cg_sam       = importlib.import_module(f"{prepend_dir}cgdynamic_sam_template")
cg_conf      = importlib.import_module(f"{prepend_dir}cgdynamic_template_conf")

cg_analytics  = importlib.import_module(f"{prepend_dir}cgdynamic_analytics")
cg_etl_script = importlib.import_module(f"{prepend_dir}cgdynamic_etl_script")

cg_conftest = importlib.import_module(f"{prepend_dir}cgdynamic_conftest")
cg_test     = importlib.import_module(f"{prepend_dir}cgdynamic_test_cases")
cg_fixtures = importlib.import_module(f"{prepend_dir}cgdynamic_test_fixtures")

import convert_friendly_to_system as converter
import get_relationship as get_rel

s3   = boto3.client('s3')
lmb  = boto3.client('lambda')
git  = boto3.client('codecommit')
cdpl = boto3.client('codepipeline')

helper = CfnResource() #We're using the AWS-provided helper library to minimize the tedious boilerplate just to signal back to CloudFormation

@helper.create
@helper.update
def create_handler(event, context):
    print(event.get('ResourceProperties', {}))
    #Project name from our CF template
    project_name    = event.get('ResourceProperties', {}).get('Project','')
    repo_name       = event.get('ResourceProperties', {}).get('RepoName','')
    website_bucket  = event.get('ResourceProperties', {}).get('Bucket','')
    cicd_bucket     = event.get('ResourceProperties', {}).get('CICDBucket','')

    project_varname = converter.convert_to_system_name(project_name)
    
    s3_analytics_raw_bucket_name = converter.convert_to_system_name(project_varname + '-stark-analytics-raw', 's3')
    s3_analytics_processed_bucket_name = converter.convert_to_system_name(project_varname + '-stark-analytics-processed', 's3')
    s3_analytics_athena_bucket_name = converter.convert_to_system_name(project_varname + '-stark-analytics-athena', 's3')

    #DynamoDB table name from our CF template
    ddb_table_name = event.get('ResourceProperties', {}).get('DDBTable','')

    #Cloud resources document
    codegen_bucket_name = os.environ['CODEGEN_BUCKET_NAME']
    response = s3.get_object(
        Bucket=codegen_bucket_name,
        Key=f'codegen_dynamic/{project_varname}/{project_varname}.yaml'
    )
    cloud_resources = yaml.safe_load(response['Body'].read().decode('utf-8')) 


    models   = cloud_resources["Data Model"]
    entities = []
    for entity in models: entities.append(entity)

    ##########################################
    #Create code for our entity Lambdas (API endpoint backing and test cases)
    files_to_commit = []
    for entity in entities:
        entity_varname = converter.convert_to_system_name(entity) 
        #Step 1: generate source code.
        #Step 1.1: extract relationship
        relationships = get_rel.get_relationship(models, entity, entity)
        rel_model = {}
        for relationship in relationships.get('has_many', []):
            if relationship.get('type') == 'repeater':
                rel_col = models.get(relationship.get('entity'), '')
                rel_model.update({(relationship.get('entity')) : rel_col})
        #FIXME: For double checking 
        for index, items in relationships.items():
            if len(items) > 0:
                for key in items:
                    for value in key:
                        key[value] = converter.convert_to_system_name(key[value]) 
                        
        seq = {}
        if len(models[entity].get("sequence", {})) > 0:
            seq = models[entity]["sequence"]

        data = {
                "Entity": entity, 
                "Sequence": seq, 
                "Columns": models[entity]["data"], 
                "PK": models[entity]["pk"], 
                "DynamoDB Name": ddb_table_name,
                "Bucket Name": website_bucket,
                "Relationships": relationships,
                "Rel Model": rel_model,
                "Raw Bucket Name": s3_analytics_raw_bucket_name,
                "Processed Bucket Name": s3_analytics_processed_bucket_name,
                "Project Name": project_varname
            }
        
            
        print(data)    
        source_code            = cg_ddb.create(data)
        test_source_code       = cg_test.create(data)
        fixtures_source_code   = cg_fixtures.create(data)
        etl_script_source_code = cg_etl_script.create(data)

        #Step 2: Add source code to our commit list to the project repo
        files_to_commit.append({
            'filePath': f"lambda/{entity_varname}/__init__.py",
            'fileContent': source_code.encode()
        })

        

        # test cases
        files_to_commit.append({
            'filePath': f"lambda/test_cases/business_modules/test_{entity_varname.lower()}.py",
            'fileContent': test_source_code.encode()
        })

        # fixtures
        files_to_commit.append({
            'filePath': f"lambda/test_cases/fixtures/{entity_varname}/__init__.py",
            'fileContent': fixtures_source_code.encode()
        })

        # etl scripts
        files_to_commit.append({
            'filePath': f"lambda/STARK_Analytics/ETL_Scripts/{entity_varname}.py",
            'fileContent': etl_script_source_code.encode()
        })

    ###########################################################
    #Create necessary files for test_cases directories
    

    data = {
        "Entities": entities,
        "Models": models,
        "DynamoDB Name": ddb_table_name,
        "Bucket Name": website_bucket
    }
    conftest_code = cg_conftest.create(data)

    files_to_commit.append({
        'filePath': f"lambda/test_cases/conftest.py",
        'fileContent': conftest_code.encode()
    })

    files_to_commit.append({
        'filePath': f"lambda/test_cases/__init__.py",
        'fileContent': "#blank init for test_cases folder"
    })

    files_to_commit.append({
        'filePath': f"lambda/test_cases/business_modules/__init__.py",
        'fileContent': "#blank init for business modules"
    })

    files_to_commit.append({
        'filePath': f"lambda/test_cases/core_modules/__init__.py",
        'fileContent': "#blank init for stark core functions"
    })
    
    files_to_commit.append({
        'filePath': f"lambda/test_cases/fixtures/__init__.py",
        'fileContent': "#blank init for fixtures folder"
    })


    ###########################################################
    #Create our Lambda for the /login and /logout API endpoints
    source_code = cg_login.create({"DynamoDB Name": ddb_table_name})    
    files_to_commit.append({
        'filePath': f"lambda/stark_login/__init__.py",
        'fileContent': source_code.encode()
    })    

    source_code = cg_logout.create({"DynamoDB Name": ddb_table_name})
    files_to_commit.append({
        'filePath': f"lambda/stark_logout/__init__.py",
        'fileContent': source_code.encode()
    })

    #################################################
    #Create our Lambda Authorizer for our API Gateway
    source_code = cg_auth.create({"DynamoDB Name": ddb_table_name})
    files_to_commit.append({
        'filePath': f"lambda/authorizer_default/authorizer_default.py",
        'fileContent': source_code.encode()
    })

    #########################################
    #Create Lambdas of built-in STARK modules 
    #    (Analytics)
    analytics_data = { "Entities": entities, "S3 Bucket Athena" : s3_analytics_athena_bucket_name, "Project_Name" : project_varname }
    analytics_source_code = cg_analytics.create(analytics_data)
    files_to_commit.append({
        'filePath': f"lambda/STARK_Analytics/__init__.py",
        'fileContent': analytics_source_code.encode()
    })

    #    (user management, permissions, etc)
    for root, subdirs, files in os.walk('source_files'):
        for source_file in files:
            with open(os.path.join(root, source_file)) as f:
                source_code = f.read().replace("[[STARK_DDB_TABLE_NAME]]", ddb_table_name)
                source_code = source_code.replace("[[STARK_WEB_BUCKET]]", website_bucket)
                source_code = source_code.replace("[[STARK_RAW_BUCKET]]", s3_analytics_raw_bucket_name)
                source_code = source_code.replace("[[STARK_PROCESSED_BUCKET]]", s3_analytics_processed_bucket_name)
                source_code = source_code.replace("[[STARK_ATHENA_BUCKET]]", s3_analytics_athena_bucket_name)
                source_code = source_code.replace("[[STARK_PROJECT_VARNAME]]", project_varname)
                #We use root[13:] because we want to strip out the "source_files/" part of the root path
                files_to_commit.append({
                    'filePath': f"lambda/" + os.path.join(root[13:], source_file),
                    'fileContent': source_code.encode()
                })



    ############################################
    #Create build files we need for our pipeline:
    # - template.yml
    # - buildspec.yml
    # - template_configuration.json
    # - builder.py
    data = { 'project_varname': project_varname }

    source_code = cg_build.create(data)
    files_to_commit.append({
        'filePath': "buildspec.yml",
        'fileContent': source_code.encode()
    })

    data = { 'cloud_resources': cloud_resources, 'entities': entities }
    source_code = cg_sam.create(data)
    files_to_commit.append({
        'filePath': "template.yml",
        'fileContent': source_code.encode()
    })

    data = {
        'cicd_bucket': cicd_bucket,
        'website_bucket': website_bucket
    }
    source_code = cg_conf.create(data)
    files_to_commit.append({
        'filePath': "template_configuration.json",
        'fileContent': source_code.encode()
    })
    
    source_code = cg_builder.create()
    files_to_commit.append({
        'filePath': "builder.py",
        'fileContent': source_code.encode()
    })
   



    ##################################################
    # Optimization Attempt
    #   Before we commit code to the repo, let's disable the Pipeline's source stage change detection 
    #   to prevent unnecessary runs while the code generator commits code multiple times
    #   We need to get current working settings first and save for retreival later, so that CGStatic can re-enable
    pipeline_definition = cdpl.get_pipeline(name=f"STARK_{project_varname}_pipeline")
    print(pipeline_definition)
    response = s3.put_object(
        Body=pickle.dumps(pipeline_definition),
        Bucket=codegen_bucket_name,
        Key=f'codegen_dynamic/{project_varname}/{project_varname}_pipeline.pickle',
        Metadata={
            'STARK_Description': 'Pickled pipeline definition for this project, with change detection in Source stage.'
        }
    )
    pipeline_definition['pipeline']['stages'][0]['actions'][0]['configuration']['PollForSourceChanges'] = "false"
    updated_pipeline = cdpl.update_pipeline(pipeline=pipeline_definition['pipeline'])
    print(updated_pipeline)

    ##################################################
    #Commit files to the project repo
    #   There's a codecommit limit of 100 files and 7mb - this will fail if more than 100 static files or >7mb are needed,
    #   such as if a dozen or so entities are requested for code generation. Implement commit chunking here for safety.
    ctr                 = 0
    key                 = 0
    total_commit_size   = 0
    total_commit_limit  = 6500000 #we limit to 6500000 bytes
    chunked_commit_list = {}
    for item in files_to_commit:
        total_commit_size += len(item['fileContent'])
        if ctr == 100 or total_commit_size > total_commit_limit:
            key = key + 1
            ctr = 0
            total_commit_size = len(item['fileContent'])
        ctr = ctr + 1
        if chunked_commit_list.get(key, '') == '':
            chunked_commit_list[key] = []
        chunked_commit_list[key].append(item)

    ctr         = 0
    batch_count = key + 1
    for commit_batch in chunked_commit_list:
        ctr = ctr + 1

        response = git.get_branch(
            repositoryName=repo_name,
            branchName='master'        
        )
        commit_id = response['branch']['commitId']

        response = git.create_commit(
            repositoryName=repo_name,
            branchName='master',
            parentCommitId=commit_id,
            authorName='STARK::CGDynamic',
            email='STARK@fakedomainstark.com',
            commitMessage=f'Initial commit of Lambda source codes (commit {ctr} of {batch_count})',
            putFiles=files_to_commit
        )


@helper.delete
def no_op(_, __):
    #Nothing to do, our Lambdas will be deleted by CloudFormation
    pass


def lambda_handler(event, context):
    helper(event, context)