#STARK Code Generator component.
#Produces the customized static content for a STARK system.

#Python Standard Library
import json
import os
import textwrap

#Extra modules
import yaml

#Private modules
import importlib
prepend_dir = ""
if 'libstark' in os.listdir():
    prepend_dir = "libstark.STARK_CodeGen_Static."

cg_js_app    = importlib.import_module(f"{prepend_dir}cgstatic_js_app")  
cg_js_view   = importlib.import_module(f"{prepend_dir}cgstatic_js_view")  
cg_js_stark  = importlib.import_module(f"{prepend_dir}cgstatic_js_stark")  
cg_add       = importlib.import_module(f"{prepend_dir}cgstatic_html_add")   
cg_edit      = importlib.import_module(f"{prepend_dir}cgstatic_html_edit")  
cg_view      = importlib.import_module(f"{prepend_dir}cgstatic_html_view")  
cg_delete    = importlib.import_module(f"{prepend_dir}cgstatic_html_delete")  
cg_listview  = importlib.import_module(f"{prepend_dir}cgstatic_html_listview")
cg_report    = importlib.import_module(f"{prepend_dir}cgstatic_html_report")
cg_js_many   = importlib.import_module(f"{prepend_dir}cgstatic_js_many")   

##unused imports
# import cgstatic_html_homepage as cg_homepage
# import cgstatic_css_login as cg_css_login
# import cgstatic_js_login as cg_js_login
# import cgstatic_js_homepage as cg_js_home
# import cgstatic_html_login as cg_login

import convert_friendly_to_system as converter
import get_relationship as get_rel

def create(cloud_resources, current_cloud_resources, project_basedir):
    models = cloud_resources["Data Model"]
    entities = []
    for entity in models:
        entities.append(entity)

    project_name    = cloud_resources["Project Name"]
    web_bucket_name = cloud_resources["S3 webserve"]["Bucket Name"]
    project_varname = converter.convert_to_system_name(project_name)

    #FIXME: API G is now in our `cloud_resources`` file, update this code
    #The endpoint of our API Gateway is not saved anywhere
    #   except in the main STARK.js file, so the only thing we can do is
    #   edit that file directly and get the endpoint URL from there
    endpoint = ''
    with open("../static/js/STARK.js", "r") as f:
        for line in f:
            code = line.strip()
            if code[0:14] == "api_endpoint_1":
                data     = code.partition("=")
                endpoint = data[2].strip()[1:-1] #slicing is to remove the quotes around the endpoint string

    #Collect list of files to commit to project repository
    files_to_commit = []

    #For each entity, we'll create a set of HTML and JS Files
    for entity in models:
        pk   = models[entity]["pk"]
        cols = models[entity]["data"]
        relationships = get_rel.get_relationship(models, entity)
        rel_model = {}
        for relationship in relationships.get('has_many', []):
            if relationship.get('type') == 'repeater':
                rel_col = models.get(relationship.get('entity'), '')
                rel_model.update({(relationship.get('entity')) : rel_col})

        cgstatic_data = { "Entity": entity, "PK": pk, "Columns": cols, "Project Name": project_name, "Relationships" : relationships, "Rel Model": rel_model }
        entity_varname = converter.convert_to_system_name(entity)
        for rel in rel_model:
            pk   = rel_model[rel]["pk"]
            cols = rel_model[rel]["data"]
            many_entity_varname = converter.convert_to_system_name(rel)
            cgstatic_many_data = { "Entity": rel, "PK": pk, "Columns": cols, "Project Name": project_name, "Relationships": relationships }
            add_to_commit(source_code=cg_js_many.create(cgstatic_many_data), key=f"js/many_{many_entity_varname}.js", files_to_commit=files_to_commit, file_path='static')

        add_to_commit(source_code=cg_add.create(cgstatic_data), key=f"{entity_varname}_add.html", files_to_commit=files_to_commit, file_path='static')
        add_to_commit(source_code=cg_edit.create(cgstatic_data), key=f"{entity_varname}_edit.html", files_to_commit=files_to_commit, file_path='static')
        add_to_commit(source_code=cg_delete.create(cgstatic_data), key=f"{entity_varname}_delete.html", files_to_commit=files_to_commit, file_path='static')
        add_to_commit(source_code=cg_view.create(cgstatic_data), key=f"{entity_varname}_view.html", files_to_commit=files_to_commit, file_path='static')
        add_to_commit(source_code=cg_listview.create(cgstatic_data), key=f"{entity_varname}.html", files_to_commit=files_to_commit, file_path='static')
        add_to_commit(source_code=cg_report.create(cgstatic_data), key=f"{entity_varname}_report.html", files_to_commit=files_to_commit, file_path='static')
        add_to_commit(source_code=cg_js_app.create(cgstatic_data), key=f"js/{entity_varname}_app.js", files_to_commit=files_to_commit, file_path='static')
        add_to_commit(source_code=cg_js_view.create(cgstatic_data), key=f"js/{entity_varname}_view.js", files_to_commit=files_to_commit, file_path='static')


    #STARK main JS file - modify to add new models.
    #   Requires a list of the old models from existing cloud_resources
    combined_models = current_cloud_resources["Data Model"].copy()
    combined_models.update(models)

    data = { 'API Endpoint': endpoint, 'Entities': combined_models, "Bucket Name": web_bucket_name }
    add_to_commit(cg_js_stark.create(data), key=f"js/STARK.js", files_to_commit=files_to_commit, file_path='static')

    ##################################################
    #Write files
    for code in files_to_commit:
        filename = project_basedir + code['filePath']
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "wb") as f:
            f.write(code['fileContent'])


def add_to_commit(source_code, key, files_to_commit, file_path=''):

    if type(source_code) is str:
        source_code = source_code.encode()

    if file_path == '':
        full_path = key
    else:
        full_path = f"{file_path}/{key}"

    files_to_commit.append({
        'filePath': full_path,
        'fileContent': source_code
    })
