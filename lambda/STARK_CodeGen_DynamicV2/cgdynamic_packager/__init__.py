#STARK Code Generator component.
#Produces the customized dynamic content for a STARK system

#Python Standard Library
import base64
import textwrap


def create_packager():
    source_code = f"""\
    import os
    import sys
    import json
    import yaml
    
    STARK_folder = os.getcwd() + '/lambda/helpers'
    sys.path = [STARK_folder] + sys.path
    import convert_friendly_to_system as converter

    data = {{
        "bindings" : [
            {{
                "authLevel" : "anonymous",
                "direction" : "in",
                "methods" : [
                "get",
                "post",
                "delete",
                "put"
                ],
                "name" : "req",
                "type" : "httpTrigger"
            }},
            {{
                "direction" : "out",
                "name"      : "$return",
                "type"      : "http"
            }}
        ]
    }}

    file_path = "function.json"
    with open(file_path, "w") as file:
        json.dump(data, file)
    file.close()    

    with open('cloud_resources.yml') as f:
        resources_raw = f.read()
        resources_yml = yaml.safe_load(resources_raw)

    os.system(f"mkdir functions_package")
    os.system(f"echo pymongo==3.12.0 > requirements.txt")
    os.system(f"cp -R lambda/* functions_package")

    for stark_func in resources_yml['Lambda']:
        func_def = resources_yml['Lambda'][stark_func]
        destination_varname = converter.convert_to_system_name(stark_func)
        
        if destination_varname not in ["stark_sysmodules", "STARK_Analytics"]:
            os.system(f"cp function.json functions_package/{{destination_varname}}/function.json")
    
    #FIXME: Temporary code to automatically add the requirements.txt
    #must be dynamically generated depending on the third-party libraries needed
    os.system(f"echo pymongo > functions_package/requirements.txt")
    """
    return textwrap.dedent(source_code)

def create_terraform_output_utility():
    source_code = f"""\
    import os
    import sys
    import json
    import yaml
    import subprocess

    def get_terraform_output():
        output_dict = {{}}
        # Run the `terraform output` command and capture the output
        output = subprocess.check_output(["terraform", "output", "mongodb_connection_string"])
        # Decode the output from bytes to string
        output_str = output.decode("utf-8").strip()
        output_dict['connection_string'] = output_str

        output = subprocess.check_output(["terraform", "output", "mongodb_database_name"])
        # Decode the output from bytes to string
        output_str = output.decode("utf-8").strip()
        output_dict['database_name'] = output_str

        return output_dict
        
    # Call the function to get the Terraform output
    tf_output = get_terraform_output()
    mongodb_database_name     = tf_output['database_name'].strip('"')
    mongodb_connection_string = tf_output['connection_string'].strip('"')

    # Open the JSON file
    with open('../../cgdynamic_payload.json', 'r') as file:
        data = json.load(file)

    # Modify the content by adding a new attribute
    data['ResourceProperties']['DBConnection'] = mongodb_connection_string
    data['ResourceProperties']['DDBTable'] = mongodb_database_name

    # Save the modified data back to the same file
    with open('../../cgdynamic_payload.json', 'w') as file:
        json.dump(data, file)

    ## replace the mongo related information here
    for root, subdirs, files in os.walk('../../functions_package/stark_core/'):
        for source_file in files:
            with open(os.path.join(root, source_file), 'r') as f:
                source_code = f.read().replace("[[STARK_MDB_TABLE_NAME]]", mongodb_database_name)
                source_code = source_code.replace("[[COSMOSDB_CONNECTION_STRING]]", mongodb_connection_string)

            with open(os.path.join(root, source_file), 'w') as f:
                f.write(source_code)
    """
    return textwrap.dedent(source_code)

def get_terraform_output_static_site_url(project_varname):
    source_code = f"""\
    import os
    import sys
    import json
    import yaml
    import subprocess
    import boto3

    s3  = boto3.client('s3')
    codegen_bucket_name = os.environ["CODEGEN_BUCKET_NAME"]
    def get_terraform_output():
        output_dict = {{}}
        # Run the `terraform output` command and capture the output
        output = subprocess.check_output(["terraform", "output", "static_website_url"])
        # Decode the output from bytes to string
        output_str = output.decode("utf-8").strip()
        output_dict['static_website_url'] = output_str
        return output_dict
        
    # Call the function to get the Terraform output
    tf_output = get_terraform_output().get("static_website_url")

    print(tf_output)

    response = s3.put_object(
        Body=tf_output.encode(),
        Bucket=codegen_bucket_name,
        Key=f'codegen_dynamic/{project_varname}/static_site_url.txt',
        Metadata={{
            'STARK_Description': 'static site url fetching for deployment'
        }}
    )
    """
    return textwrap.dedent(source_code)