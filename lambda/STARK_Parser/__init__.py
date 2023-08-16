#Handles the POST action of the STARK PARSE POC

#Python Standard Library
import base64
import json
import os
from collections import OrderedDict 

#Extra modules
import yaml
import boto3
import datetime
from io import StringIO
import csv

#Private modules
import importlib
prepend_dir = ""
if 'libstark' in os.listdir():
    prepend_dir = "libstark.STARK_Parser."

api_gateway_parser = importlib.import_module(f"{prepend_dir}parse_api_gatewayv2")
dynamodb_parser    = importlib.import_module(f"{prepend_dir}parse_dynamodb")
model_parser       = importlib.import_module(f"{prepend_dir}parse_datamodel")
lambda_parser      = importlib.import_module(f"{prepend_dir}parse_lambda")
layer_parser       = importlib.import_module(f"{prepend_dir}parse_layers")
s3_parser          = importlib.import_module(f"{prepend_dir}parse_s3")
cloudfront_parser  = importlib.import_module(f"{prepend_dir}parse_cloudfront")
analytics_parser   = importlib.import_module(f"{prepend_dir}parse_analytics")

## unused imports
# import parse_api_gateway as api_gateway_parser
# import parse_sqs as sqs_parser


import convert_friendly_to_system as converter
import stark_scrypt as scrypt

#Get environment variable - this will allow us to take different branches depending on whether we are LOCAL or PROD (or any other future valid value)
ENV_TYPE = os.environ['STARK_ENVIRONMENT_TYPE']
if ENV_TYPE == "PROD":
    default_response_headers = { "Content-Type": "application/json" }
    s3  = boto3.client('s3')

    #Get resource ids from STARK configuration document
    codegen_bucket_name  = os.environ['CODEGEN_BUCKET_NAME']
    response = s3.get_object(
        Bucket=codegen_bucket_name,
        Key=f'STARKConfiguration/STARK_config.yml'
    )
    config = yaml.safe_load(response['Body'].read().decode('utf-8')) 
    CFWriter_FuncName = config['CFWriter_ARN']

    #And of course a Lambda client, so we can invoke the function whose ARN we retrieved above
    lambda_client = boto3.client('lambda')

else:
    #We only have to do this because `SAM local start-api` doesn't follow CORS info from template.yml, which is bullshit
    default_response_headers = { 
        "Content-Type": "application/json", 
        "Access-Control-Allow-Origin": "*"
    }

    CFWriter_FuncName = 'stub for local testing'

def lambda_handler(event, context):

    if CFWriter_FuncName == '':
        #We should totally bail now, because this means there's an
        #internal error with the STARK infra
        return {
          "isBase64Encoded": False,
          "statusCode": 500,
          "body": json.dumps("STARK Internal Error - no CFWriter function name found!"),
          "headers": default_response_headers
        }
    response_message = "Success"
    isBase64Encoded = event.get('isBase64Encoded', False)
    raw_data = event.get('body', '')

    if isBase64Encoded:
        raw_data = base64.b64decode(raw_data).decode()

    jsonified_payload = json.loads(raw_data)
    data_model = yaml.safe_load(jsonified_payload["data_model"])
    validation_results = jsonified_payload["validation_results"]
    
    #Debugging only
    #print("****************************")
    #print(data_model.get('__STARK_project_name__'))

    entities = []
    project_name = ""
    project_varname = ""
    project_name_unique_id = converter.generate_unique_id()

    with_cloudfront = False

    for key in data_model:
        if "__STARK" in key:
            if key == "__STARK_project_name__":
                project_name = data_model[key]
                if not project_name:                
                    return {
                        "isBase64Encoded": False,
                        "statusCode": 200,
                        "body": json.dumps("Code:NoProjectName"),
                        "headers": default_response_headers
                }
                project_varname = converter.convert_to_system_name(project_name)

            elif key == "__STARK_advanced__":
                for advance_config in data_model[key]:
                    if advance_config == 'CloudFront':
                        pass
                    
        else:
            entities.append(key)
    if ENV_TYPE == 'PROD':
        time_zone = datetime.timezone(datetime.timedelta(hours=8))
        ts_in_hms = datetime.datetime.now(time_zone).strftime("%H:%M:%S")

        error_list = []
        warning_list = []
        for element, element_data in validation_results.items():
            for index in element_data.get("error_messages",[]):
                temp_dict = {"Table": element, "Message": index}
                error_list.append(temp_dict)

            for index in element_data.get("warning_messages",[]):
                temp_dict = {"Table": element, "Message": index}
                warning_list.append(temp_dict)

        if len(error_list) > 0:
            file_buff = StringIO()
            writer = csv.DictWriter(file_buff, fieldnames=['Table','Message'],quoting=csv.QUOTE_ALL)
            writer.writeheader()
            for rows in error_list:
                writer.writerow(rows)

            error_csv_file = "error_logs.csv"
            response = s3.put_object(
                Body=file_buff.getvalue(),
                Bucket=codegen_bucket_name,
                Key=f'logs/{project_varname}/{ts_in_hms}/{error_csv_file}',
                Metadata={
                    'STARK_Description': 'Log file for the generation'
                }
            )

            

        if len(warning_list) > 0:
            file_buff = StringIO()
            writer = csv.DictWriter(file_buff, fieldnames=['Table','Message'],quoting=csv.QUOTE_ALL)
            writer.writeheader()
            for rows in warning_list:
                writer.writerow(rows)
                
            warning_csv_file = "warning_logs.csv"
            response = s3.put_object(
                Body=file_buff.getvalue(),
                Bucket=codegen_bucket_name,
                Key=f'logs/{project_varname}/{ts_in_hms}/{warning_csv_file}',
                Metadata={
                    'STARK_Description': 'Log file for the generation'
                }
            )

        response = s3.put_object(
            Body=ts_in_hms,
            Bucket=codegen_bucket_name,
            Key=f'codegen_dynamic/{project_varname}/log_directory.txt',
            Metadata={
                'STARK_Description': 'Log filename for the generation'
            }
        )

        
    if len(error_list) < 1:
        
        
    #####################################################
    ###START OF INFRA LIST CREATION #####################

        cloud_resources = {}
        cloud_resources = {"Project Name": project_name} 
        cloud_provider =  data_model.get('__STARK_advanced__', {}).get('Cloud Provider', 'AWS')
        data = {
            'entities': entities,
            'data_model': data_model,
            'project_name': project_name,
            'project_varname': project_varname,
            'cloud_provider': cloud_provider,
            'unique_id': project_name_unique_id
        }
        
        response = s3.put_object(
            Body=scrypt.create_hash(data['data_model']['__STARK_default_password__']),
            Bucket=codegen_bucket_name,
            Key=f'codegen_dynamic/{project_varname}/default_password.txt',
            Metadata={
                'STARK_Description': 'Default pass'
            }
        )


        # Cloud Provider    
        cloud_resources["Cloud Provider"] = cloud_provider

        # #Default Password
        # cloud_resources["Default Password"] = scrypt.create_hash(data['data_model']['__STARK_default_password__'])

        #Data Model ###
        cloud_resources["Data Model"] = model_parser.parse(data)

        #S3 Bucket ###
        cloud_resources["S3 webserve"] = s3_parser.parse(data)

        #API Gateway ###
        data.update({'raw_data_model': cloud_resources["Data Model"]})
        cloud_resources["API Gateway"] = api_gateway_parser.parse(data)

        #DynamoDB ###
        cloud_resources["DynamoDB"] = dynamodb_parser.parse(data)

        #Lambda ###
        cloud_resources["Lambda"] = lambda_parser.parse(data)

        #Lambda Layers###
        cloud_resources["Layers"] = layer_parser.parse(data)

        #CloudFront ##################
        cloud_resources["CloudFront"] = cloudfront_parser.parse(data)

        #Analytics ##################
        cloud_resources["Analytics"] = analytics_parser.parse(data)

        #SQS #######################
        #Disable for now, not yet implemented, just contains stub
        #cloud_resources["SQS"] = sqs_parser.parse(data)
        

        #For debugging: pretty-print the resulting JSON
        #json_formatted_str = json.dumps(cloud_resources, indent=2)
        #print(json_formatted_str)

        #############################################################
        #FUTURE: STARK-specific settings parsing will be done here 
        #cloud_resources["STARK_settings"] = stark_settings_parser.parse(data)
        #Above is just a stub; in the future, settings parser may be the first call,
        #and its results passed to all other sub-parsers above, as these STARK
        #settings may be used to modify the default behavior of the sub-parsers


        ##############################################################
        #PAYLOAD FORMAT NOTE:
        #   If parser needs to specifically pass a YAML document, use:
        #       Payload=json.dumps(yaml.dump(cloud_resources))

        if ENV_TYPE == "PROD":
            # print(data['data_model']['__STARK_default_password__'])
            response = lambda_client.invoke(
                FunctionName = CFWriter_FuncName,
                InvocationType = 'RequestResponse',
                LogType= 'Tail',
                Payload=json.dumps(cloud_resources)
            )
            
        else:
            print(json.dumps(cloud_resources))
    else:
        response_message = "YAML Error"
    return {
        "isBase64Encoded": False,
        "statusCode": 200,
        "body": json.dumps(response_message),
        "headers": default_response_headers
    }