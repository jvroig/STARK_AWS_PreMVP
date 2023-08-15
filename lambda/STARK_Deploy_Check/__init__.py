#Tracks status of CF Deploy after it is successfully triggered by STARK_Deploy

#Python Standard Library
import base64
import json
import textwrap
from time import sleep

#Extra modules
import yaml
import boto3
import botocore
import os

#Private modules
import convert_friendly_to_system as converter

cfn = boto3.client('cloudformation')
s3  = boto3.client('s3')

stack_map = {
    0: 'CI/CD Pipeline',
    1: 'System Bootstrapper',
    2: 'Main Application' 
} 

def lambda_handler(event, context):


    isBase64Encoded = event.get('isBase64Encoded', False)
    raw_data_model  = event.get('body', '')

    if isBase64Encoded:
        raw_data_model = base64.b64decode(raw_data_model).decode()

    jsonified_payload = json.loads(raw_data_model)
    current_stack     = jsonified_payload['current_stack']
    data_model        = yaml.safe_load(jsonified_payload['data_model'])
    project_name      = data_model.get('__STARK_project_name__')
    project_stackname = converter.convert_to_system_name(project_name, 'cf-stack')
    cloud_provider    = data_model.get('__STARK_advanced__',{}).get("Cloud Provider", 'AWS')
    codegen_bucket_name = os.environ['CODEGEN_BUCKET_NAME']

    #Stack to track is either the CI/CD Pipeline stack, the bootstrapper, or the main application
    #   The bootstrapper and the main application operate on the same stack (same name)
    if cloud_provider == 'Azure':
        CF_stack_name = f"CICD-pipeline-{project_stackname}"

    else:
        if current_stack == 0:
            CF_stack_name = f"CICD-pipeline-{project_stackname}"
        else:
            CF_stack_name = f"STARK-project-{project_stackname}"

    print('Sleeping for 10!')
    sleep(10)

    try:
        response          = cfn.describe_stacks( StackName=CF_stack_name )
        print(response)
        stack_status      = response['Stacks'][0]['StackStatus']
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ValidationError':
            if CF_stack_name == f"STARK-project-{project_stackname}":
                #We should just wait again, the application sometimes takes a while.
                #   We'll let the client decide how long to retry when it comes to ValidationErrors here
                #   Implementing client-side retries makes more sense, since our lambda function is stateless.
                payload = {
                    'current_stack': current_stack,
                    'status': 'STACK_NOT_FOUND',
                    'retry': True,
                    'result': 'STACK_NOT_FOUND',
                    'url': ''
                }

                return {
                    "isBase64Encoded": False,
                    "statusCode": 200,
                    "body": json.dumps(payload),
                    "headers": {
                        "Content-Type": "application/json",
                    }
                }

    print("Current stack: " + str(current_stack))
    print("Stack status: " + stack_status)

    url           = ''
    result        = ''
    if stack_status in [ 'CREATE_COMPLETE', 'UPDATE_COMPLETE' ]:

        stack_description = response['Stacks'][0]['Description']
        print("Stack description: " + stack_description)
        if current_stack < 2:
            result = 'SUCCESS'
            retry = True
            #Tell client to ask for tracking of the next stack
            current_stack = current_stack + 1

        elif current_stack == 2 and cloud_provider == 'AWS' and stack_description != "Bootstrapper": 
            response = cfn.describe_stack_resource(
                StackName=CF_stack_name,
                LogicalResourceId='STARKSystemBucket'
            )

            result          = 'SUCCESS'
            retry           = False
            bucket_name     = response['StackResourceDetail']['PhysicalResourceId']
            response        = s3.get_bucket_location(Bucket=bucket_name)
            bucket_location = response['LocationConstraint']

            #We need a map here because website endpoints use either a dash or a dot
            #   betweeb "s3-website" and "$REGION", depending on the region, instead of just
            #   being standard all around, so we can't do just a quick concat assuming the separator is constant :(
            #   And in cn-northwest-1, the url ends with ".com.cn" instead of just ".com" - so even that has to be accounted for.
            #   Just having a map of regions to endpoints is just the easiest and most comprehensive way to solve this, the tradeoff
            #   being new regions would have to be added - to mitigate that, we can make a reasonable default (either dash or dot, ending in ".com")
            website_endpoint_map = {
                "us-east-2": "s3-website.us-east-2.amazonaws.com/",
                "us-east-1": "s3-website-us-east-1.amazonaws.com/",
                "us-west-1": "s3-website-us-west-1.amazonaws.com/",
                "us-west-2": "s3-website-us-west-2.amazonaws.com/",
                "af-south-1": "s3-website.af-south-1.amazonaws.com/",
                "ap-east-1": "s3-website.ap-east-1.amazonaws.com/",
                "ap-south-1": "s3-website.ap-south-1.amazonaws.com/",
                "ap-northeast-3": "s3-website.ap-northeast-3.amazonaws.com/",
                "ap-northeast-2": "s3-website.ap-northeast-2.amazonaws.com/",
                "ap-southeast-1": "s3-website-ap-southeast-1.amazonaws.com/",
                "ap-southeast-2": "s3-website-ap-southeast-2.amazonaws.com/",
                "ap-northeast-1": "s3-website-ap-northeast-1.amazonaws.com/",
                "ca-central-1": "s3-website.ca-central-1.amazonaws.com/",
                "cn-northwest-1": "s3-website.cn-northwest-1.amazonaws.com.cn/",
                "eu-central-1": "s3-website.eu-central-1.amazonaws.com/",
                "eu-west-1": "s3-website-eu-west-1.amazonaws.com/",
                "eu-west-2": "s3-website.eu-west-2.amazonaws.com/",
                "eu-south-1": "s3-website.eu-south-1.amazonaws.com/",
                "eu-west-3": "s3-website.eu-west-3.amazonaws.com/",
                "eu-north-1": "s3-website.eu-north-1.amazonaws.com/",
                "ap-southeast-3": "s3-website.ap-southeast-3.amazonaws.com/",
                "me-south-1": "s3-website.me-south-1.amazonaws.com/",
                "sa-east-1": "s3-website-sa-east-1.amazonaws.com/",
                "us-gov-east-1": "s3-website.us-gov-east-1.amazonaws.com/",
                "us-gov-west-1": "s3-website-us-gov-west-1.amazonaws.com/",
            }

            if bucket_location in website_endpoint_map:
                website_endpoint = website_endpoint_map[bucket_location]
                url = f"http://{bucket_name}.{website_endpoint}"
            else:
                #We caught a new region before our map was updated, fall back to using
                #a dot instead of dash before the region (this seems to be the preferred separator
                #for newer regions), and ends in just ".com"
                url = f"http://{bucket_name}.s3-website.{bucket_location}.amazonaws.com/"
        elif current_stack == 2 and cloud_provider == 'Azure' and stack_description != "Bootstrapper":
            codebuild = boto3.client('codebuild')
            project_varname = converter.convert_to_system_name(project_name)
            CB_project_name = f"STARK_{project_varname}_build"

            response = codebuild.list_builds_for_project(projectName=CB_project_name)
            build_summaries = codebuild.batch_get_builds(ids=response['ids']).get("builds", {})
            
            if len(build_summaries) > 1 :
                for build in build_summaries:
                    #check for build #2 since this is where the building of terraform files is being done
                    if build.get("buildNumber") == 2:
                        if build.get("buildStatus") == 'IN_PROGRESS':
                            retry         = True
                            result        = ''
                            current_stack = 2
                        else:
                            retry = False
                    
                            s3_resp = s3.get_object(Bucket=codegen_bucket_name, Key=f"codegen_dynamic/{project_varname}/static_site_url.txt")
                            url_txt = s3_resp['Body'].read().decode('utf-8')
                            url= url_txt.strip('"')
                            if url == '':
                                result = "FAILED"
                            else:
                                result = "SUCCESS"
            else:  
                retry         = True
                result        = ''
                current_stack = 2

        else:
            #Tell client to keep tracking stack 2. We're still waiting for the
            #   CI/CD pipeline to update the stack from bootstrapper to main application
            retry         = True
            result        = ''
            current_stack = 2


    elif stack_status == 'CREATE_FAILED':
        result = 'FAILED'
        retry = False

    elif stack_status == 'ROLLBACK_IN_PROGRESS':
        result = 'FAILED'
        retry = False

    elif stack_status == 'ROLLBACK_COMPLETE':
        result = 'FAILED'
        retry = False

    elif stack_status == 'DELETE_IN_PROGRESS':
        result = 'FAILED'
        retry = False

    elif stack_status == 'DELETE_COMPLETE':
        result = 'FAILED'
        retry = False
        
    else:
        result = ''
        retry = True


    payload = {
        'current_stack': current_stack,
        'status': stack_status,
        'retry': retry,
        'result': result,
        'url': url
    }

    return {
        "isBase64Encoded": False,
        "statusCode": 200,
        "body": json.dumps(payload),
        "headers": {
            "Content-Type": "application/json",
        }
    }