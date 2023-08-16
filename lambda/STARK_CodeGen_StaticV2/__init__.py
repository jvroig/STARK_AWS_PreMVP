#STARK Code Generator component.
#Produces the customized static content for a STARK system.

#Python Standard Library
import base64
import json
import pickle
import os
import textwrap

#Extra modules
import yaml
import boto3

#Private modules
import importlib

prepend_dir = ""
if 'libstark' in os.listdir():
    prepend_dir = "libstark.STARK_CodeGen_Static."

cg_js_app    = importlib.import_module(f"{prepend_dir}cgstatic_js_app")  
cg_js_view   = importlib.import_module(f"{prepend_dir}cgstatic_js_view")  
cg_js_many   = importlib.import_module(f"{prepend_dir}cgstatic_js_many")  
cg_js_login  = importlib.import_module(f"{prepend_dir}cgstatic_js_login")  
cg_js_home   = importlib.import_module(f"{prepend_dir}cgstatic_js_homepage")  
cg_js_stark  = importlib.import_module(f"{prepend_dir}cgstatic_js_stark")  
cg_css_login = importlib.import_module(f"{prepend_dir}cgstatic_css_login")  
cg_git       = importlib.import_module(f"{prepend_dir}cgstatic_gitignore")  
cg_add       = importlib.import_module(f"{prepend_dir}cgstatic_html_add")   
cg_edit      = importlib.import_module(f"{prepend_dir}cgstatic_html_edit")  
cg_view      = importlib.import_module(f"{prepend_dir}cgstatic_html_view")  
cg_login     = importlib.import_module(f"{prepend_dir}cgstatic_html_login")  
cg_delete    = importlib.import_module(f"{prepend_dir}cgstatic_html_delete")  
cg_listview  = importlib.import_module(f"{prepend_dir}cgstatic_html_listview")  
cg_homepage  = importlib.import_module(f"{prepend_dir}cgstatic_html_homepage")  
cg_report    = importlib.import_module(f"{prepend_dir}cgstatic_html_report")   

import convert_friendly_to_system as converter
import get_relationship as get_rel

s3   = boto3.client('s3')
api  = boto3.client('apigatewayv2')
git  = boto3.client('codecommit')
cdpl = boto3.client('codepipeline')

def lambda_handler(event, context):
    #Project, bucket name and API Gateway ID from our CF template
    repo_name       = event.get('ResourceProperties', {}).get('RepoName','')
    bucket_name     = event.get('ResourceProperties', {}).get('Bucket','')
    project_name    = event.get('ResourceProperties', {}).get('Project','') 
    project_varname = converter.convert_to_system_name(project_name)
    #Bucket for our cloud resources document
    codegen_bucket_name = os.environ['CODEGEN_BUCKET_NAME']

    #Cloud resources document
    response = s3.get_object(
        Bucket=codegen_bucket_name,
        Key=f'codegen_dynamic/{project_varname}/{project_varname}.yaml'
    )

    #FIXME: Remove raw for now since we need to update cloud_resources with API gateway URL - hopefully using sort_keys=False will remove the need for the raw version) 
    #raw_cloud_resources = response['Body'].read().decode('utf-8')
    #cloud_resources     = yaml.safe_load(raw_cloud_resources) 
    cloud_resources = yaml.safe_load(response['Body'].read().decode('utf-8')) 

    #Get relevant info from cloud_resources
    models = cloud_resources["Data Model"]
    endpoint = cloud_resources['API Gateway']['URL']

    #Collect list of files to commit to project repository
    files_to_commit = []

    #STARK main JS file
    data = { 'API Endpoint': endpoint, 'Entities': models, "Bucket Name": bucket_name, 'Project Name': project_varname }
    add_to_commit(cg_js_stark.create(data), key=f"js/STARK.js", files_to_commit=files_to_commit, file_path='static')

    #For each entity, we'll create a set of HTML and JS Files and uploaded folder
    for entity in models:
        # print(models)
        pk   = models[entity]["pk"]
        cols = models[entity]["data"]
        relationships = get_rel.get_relationship(models, entity)
        rel_model = {}
        
        for relationship in relationships.get('has_many', []):
            if relationship.get('type') == 'repeater':
                rel_col = models.get(relationship.get('entity'), '')
                rel_model.update({(relationship.get('entity')) : rel_col})
            
        cgstatic_data = { "Entity": entity, "PK": pk, "Columns": cols, "Project Name": project_name, "Relationships": relationships, "Rel Model": rel_model }
        entity_varname = converter.convert_to_system_name(entity)
        # print('static rel_model')
        # print(rel_model)
        for rel in rel_model:
            # print('static rel_model')
            # print(rel_model)
            pk   = rel_model[rel]["pk"]
            cols = rel_model[rel]["data"]
            many_entity_varname = converter.convert_to_system_name(rel)
            cgstatic_many_data = { "Entity": rel, "PK": pk, "Columns": cols, "Project Name": project_name, "Relationships": relationships }
            add_to_commit(source_code=cg_js_many.create(cgstatic_many_data), key=f"js/many_{many_entity_varname}.js", files_to_commit=files_to_commit, file_path='static')

        seq = {}
        if "sequence" in models[entity]:
            seq = models[entity]["sequence"]
        cgstatic_data["Sequence"] = seq
        
        print('cgstatic_data')
        print(cgstatic_data)
        add_to_commit(source_code=cg_add.create(cgstatic_data), key=f"{entity_varname}_add.html", files_to_commit=files_to_commit, file_path='static')
        add_to_commit(source_code=cg_edit.create(cgstatic_data), key=f"{entity_varname}_edit.html", files_to_commit=files_to_commit, file_path='static')
        add_to_commit(source_code=cg_delete.create(cgstatic_data), key=f"{entity_varname}_delete.html", files_to_commit=files_to_commit, file_path='static')
        add_to_commit(source_code=cg_view.create(cgstatic_data), key=f"{entity_varname}_view.html", files_to_commit=files_to_commit, file_path='static')
        add_to_commit(source_code=cg_listview.create(cgstatic_data), key=f"{entity_varname}.html", files_to_commit=files_to_commit, file_path='static')
        add_to_commit(source_code=cg_report.create(cgstatic_data), key=f"{entity_varname}_report.html", files_to_commit=files_to_commit, file_path='static')
        add_to_commit(source_code=cg_js_app.create(cgstatic_data), key=f"js/{entity_varname}_app.js", files_to_commit=files_to_commit, file_path='static')
        add_to_commit(source_code=cg_js_view.create(cgstatic_data), key=f"js/{entity_varname}_view.js", files_to_commit=files_to_commit, file_path='static')
        add_to_commit(source_code=f"{entity} Uploaded files", key=f"uploaded_files/{entity_varname}/README.txt", files_to_commit=files_to_commit, file_path='')
        
    #HTML+JS for our homepage
    homepage_data = { "Project Name": project_name }
    add_to_commit(source_code=cg_homepage.create(homepage_data), key=f"home.html", files_to_commit=files_to_commit, file_path='static')
    add_to_commit(source_code=cg_js_home.create(homepage_data), key=f"js/STARK_home.js", files_to_commit=files_to_commit, file_path='static')

    #Login HTML+JS+CSS
    login_data = { "Project Name": project_name }
    add_to_commit(source_code=cg_login.create(homepage_data), key=f"index.html", files_to_commit=files_to_commit, file_path='static')
    add_to_commit(source_code=cg_js_login.create(homepage_data), key=f"js/login.js", files_to_commit=files_to_commit, file_path='static')
    add_to_commit(source_code=cg_css_login.create(homepage_data), key=f"css/login.css", files_to_commit=files_to_commit, file_path='static')
    
    #TMP folder
    add_to_commit(source_code="Temporary files", key=f"tmp/README.txt", files_to_commit=files_to_commit, file_path='')

    ##########################################
    #Add cloud resources document to our files
    add_to_commit(source_code=yaml.dump(cloud_resources, sort_keys=False), key="cloud_resources.yml", files_to_commit=files_to_commit, file_path='')


    ###############################################
    #Get pre-built static files from codegen bucket
    prebuilt_static_files = []
    list_prebuilt_static_files(codegen_bucket_name, prebuilt_static_files)
    for static_file in prebuilt_static_files:
        #We don't want to include the "STARKWebSource/" prefix in our list of keys, hence the string slice in static_file
        add_to_commit(source_code=get_file_from_bucket(codegen_bucket_name, static_file), key=static_file[15:], files_to_commit=files_to_commit, file_path='static')

    ####################################################
    #Create static files from the source_files directory
    #   These are HTML files for built-in STARK modules like user management, permissions, sessions...
    #   Right now they need to be modified by the generator a bit just to replace the Project/System Name in the headers
    dir = "source_files"
    html_files = os.listdir(dir)
    for html_file in html_files:
        with open(dir + os.sep + html_file) as f:
            #replace all occurences of "[[STARK_PROJECT_NAME]]" with project_name
            source_code = f.read().replace("[[STARK_PROJECT_NAME]]", project_name)
            add_to_commit(source_code=source_code, key=html_file, files_to_commit=files_to_commit, file_path='static')

    ##################################################################
    #Get pre-built utilities, layers and helpers for local development
    prebuilt_utilities = []
    list_prebuilt_utilities(codegen_bucket_name, prebuilt_utilities)
    for static_file in prebuilt_utilities:
        #We don't want to include the "STARKUtilities/" prefix in our list of keys, hence the string slice in static_file
        add_to_commit(source_code=get_file_from_bucket(codegen_bucket_name, static_file), key=static_file[15:], files_to_commit=files_to_commit, file_path='bin')

    prebuilt_layers = []
    list_packaged_layers(codegen_bucket_name, prebuilt_layers)
    for key in prebuilt_layers:
        static_file = key['file_name']
        file_size   = key['file_size']
        #We don't want to include the "STARKLambdaLayers/" prefix in our list of keys, hence the string slice in static_file
        add_to_commit(source_code=get_file_from_bucket(codegen_bucket_name, static_file), key=static_file[18:], files_to_commit=files_to_commit, file_path='lambda/packaged_layers', file_size = file_size)

    prebuilt_helpers = []
    list_prebuilt_helpers(codegen_bucket_name, prebuilt_helpers)
    for static_file in prebuilt_helpers:
        #We don't want to include the "STARKLambdaHelpers/" prefix in our list of keys, hence the string slice in static_file
        add_to_commit(source_code=get_file_from_bucket(codegen_bucket_name, static_file), key=static_file[19:], files_to_commit=files_to_commit, file_path='lambda/helpers')

    #######################################################################
    #Get our STARK_Config.yml from the CodeGen bucket - needed by STARK CLI
    response = s3.get_object(
        Bucket=codegen_bucket_name,
        Key=f'STARKConfiguration/STARK_config.yml'
    )
    source_code = response['Body'].read()
    add_to_commit(source_code=source_code, key=f"STARK_config.yml", files_to_commit=files_to_commit, file_path='bin/libstark')

    ####################################################################################################
    #Create the .gitignore file for the project repo - so that cruft doesn't get into commits by default
    add_to_commit(source_code=cg_git.create(), key=f".gitignore", files_to_commit=files_to_commit, file_path='')

    ##############################################
    #Commit our prebuilt files to the project repo
    #   There's a codecommit limit of 100 files - this will fail if more than 100 static files are needed,
    #   such as if a dozen or so entities are requested for code generation. Implement commit chunking here for safety.
    ctr                 = 0
    key                 = 0
    chunked_commit_list = []
    current_chunk = []
    current_chunk_size = 0
    file_size_limit     = 6 * 1024 * 1024 ## 6 MB

    for item in files_to_commit:
        if (
            ctr == 100
            or (
                not item.get("file_size")
                and current_chunk
                and current_chunk[-1].get("file_size")
            )
            or (
                item.get("file_size")
                and current_chunk_size + item["file_size"] > file_size_limit
            )
        ):
            key += 1
            ctr = 0
            chunked_commit_list.append(current_chunk)
            current_chunk = []
            current_chunk_size = 0
        ctr += 1
        if "file_size" in item:
            current_chunk_size += item["file_size"]

        #Create new dictionary to remove file size in the chunks stored
        new_item = {
            'filePath': item['filePath'],
            'fileContent': item['fileContent']
            }
        current_chunk.append(new_item)

    if current_chunk:
        chunked_commit_list.append(current_chunk)


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
            authorName='STARK::CGStatic',
            email='STARK@fakedomainstark.com',
            commitMessage=f"Initial commit of static and prebuilt files (commit {ctr} of {batch_count})",
            putFiles=commit_batch
        )

    ##################################################
    # Optimization Attempt
    #   After we commit code to the repo, re-enable the Pipeline's source stage change detection 
    #   We need to get current working settings

    response = s3.get_object(
        Bucket=codegen_bucket_name,
        Key=f'codegen_dynamic/{project_varname}/{project_varname}_pipeline.pickle'
    )
    pipeline_definition = pickle.loads(response['Body'].read()) 
    print(pipeline_definition)
    response = cdpl.update_pipeline(pipeline=pipeline_definition['pipeline'])
    cdpl.start_pipeline_execution(name=f"STARK_{project_varname}_pipeline")


def add_to_commit(source_code, key, files_to_commit, file_path='', file_size = 0):

    if type(source_code) is str:
        source_code = source_code.encode()

    if file_path == '':
        full_path = key
    else:
        full_path = f"{file_path}/{key}"

    files_to_commit.append({
        'filePath': full_path,
        'fileContent': source_code,
        'file_size': file_size
    })

def list_prebuilt_static_files(bucket_name, prebuilt_static_files):
    response = s3.list_objects_v2(
        Bucket = bucket_name,
        Prefix = "STARKWebSource/",
    )

    for static_file in response['Contents']:
        prebuilt_static_files.append(static_file['Key'])

def list_prebuilt_helpers(bucket_name, prebuilt_static_files):
    response = s3.list_objects_v2(
        Bucket = bucket_name,
        Prefix = "STARKLambdaHelpers/",
    )

    for static_file in response['Contents']:
        prebuilt_static_files.append(static_file['Key'])

def list_prebuilt_utilities(bucket_name, prebuilt_static_files):
    response = s3.list_objects_v2(
        Bucket = bucket_name,
        Prefix = "STARKUtilities/",
    )

    for static_file in response['Contents']:
        prebuilt_static_files.append(static_file['Key'])

def list_packaged_layers(bucket_name, prebuilt_static_files):
    response = s3.list_objects_v2(
        Bucket = bucket_name,
        Prefix = "STARKLambdaLayers/",
    )

    for layer in response['Contents']:
        prebuilt_static_files.append({'file_name':layer['Key'], 'file_size': layer['Size']})

def get_file_from_bucket(bucket_name, static_file):
    response = s3.get_object(
        Bucket = bucket_name,
        Key = static_file
    )

    source_code = response['Body'].read()
    return source_code
