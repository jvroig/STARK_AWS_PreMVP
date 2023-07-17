import requests
import json
import base64
import boto3
import stark_core
import datetime
import time
import zipfile
import re

ssm = boto3.client('ssm')
response = ssm.get_parameter(
    Name='[[STARK_PROJECT_VARNAME]]_GENAI_LAMBDA_FUNC',
    WithDecryption=False
)
GenAI_Function = response.get('Parameter',{}).get('Value','')

time_range = 300 #time range in minutes to scan logs

def lambda_handler(event, context):
      
    if event.get('isBase64Encoded') == True :
        stark_core.log.msg('isBase64Encoded = True')
        payload = json.loads(base64.b64decode(event.get('body'))).get('ObservabilityPayload',"")
        type    = json.loads(base64.b64decode(event.get('body'))).get('ObservabilityType',"")
    else:    
        stark_core.log.msg('isBase64Encoded = False')
        payload = json.loads(event.get('body')).get('ObservabilityPayload',"")
        type    = json.loads(event.get('body')).get('ObservabilityType',"")

    if type == 'log_review' or type == 'code_review':
        response = log_scanner(payload, type)
    else:
        stark_core.log.msg('Error - invalid type submitted, or no type submitted')
        #Error - invalid type submitted, or no type submitted
        pass

    # TODO implement
    
    return {
        'statusCode': 200,
        'body': json.dumps({'observability_response': response}),
      }   


def invoke_GenAI(payload, type):
    lambda_client = boto3.client('lambda')
    GenAI_Payload = payload

    # Define the payload to send to the 'GenAI' Lambda function
    test_payload = {
        'body': json.dumps({  # Convert the inner dictionary to a JSON string
            'GenAIPayload': GenAI_Payload,
            'GenAIType': type,
        })
    }
    
    stark_core.log.msg('GenAI Payload test at invoke_GenAI  %s' %test_payload)
    # Invoke the 'GenAI' Lambda function
    GenAIresponse = lambda_client.invoke(
        FunctionName=GenAI_Function,
        InvocationType='RequestResponse',  # Synchronous invocation
        Payload=json.dumps(test_payload)
    )
    stark_core.log.msg('invoke_GenAI response: %s' %GenAIresponse)
    response = json.loads(GenAIresponse['Payload'].read())
    return response


def log_scanner(payload, type):
    # Create a CloudWatch Logs client
    logs_client = boto3.client('logs')

    # Get current date and time
    end_time   = datetime.datetime.now()
    start_time = end_time - datetime.timedelta(minutes=time_range)

    # Convert to timestamp
    start_timestamp = int(time.mktime(start_time.timetuple()) * 1000)
    end_timestamp = int(time.mktime(end_time.timetuple()) * 1000)
    
    stark_core.log.msg('log_scanner - Payload: %s' %payload)
    limit = 5 #limit of number of logs to return
    log_group_name = payload
    combined_data = {}
    if type == "log_review":
        filter_pattern ='ERROR'
    elif type == "code_review":
        filter_pattern ='ERROR Syntax error'

 
    # Retrieve ERROR log events from a specified CloudWatch log group
    stark_core.log.msg('Retrieving logs from: %s' %log_group_name)
    retrieved_CWlogs = logs_client.filter_log_events(
        logGroupName=log_group_name,
        limit=limit,
        filterPattern=filter_pattern,
        startTime=start_timestamp,
        endTime=end_timestamp
    )
    stark_core.log.msg('Retrieved logs: %s' %retrieved_CWlogs)

    # Filter GenAI payload to only include relevant data
    relevant_logs = []
    for event in retrieved_CWlogs['events']:
        relevant_logs.append({
            'logStreamName': event['logStreamName'],
            'timestamp': event['timestamp'],
            'message': event['message']
        })
    combined_data['logs'] = relevant_logs
    stark_core.log.msg('filter_pattern: %s' %filter_pattern)
    #if filter_pattern is 'ERROR Syntax error' then retrive lambda code
    if type == 'code_review':
       line_errors = search_lines_with_error(retrieved_CWlogs)
       #FIXME: Remove hard coded value
       lambda_function_name = 'STARK-project-DebbieTest202-STARKBackendApiForItem-JZyKw7AVt6NW'
       lambda_code = retrive_lambda_code(lambda_function_name, line_errors) 
       combined_data['source_code'] = lambda_code
    
    stark_core.log.msg('Sending ERROR log events to GenAI for review: %s' %combined_data)
    response = invoke_GenAI(combined_data, type)
    GenAI_logs = {
        'Logs': retrieved_CWlogs,
        'GenAI Response': response
    }
    stark_core.log.msg('GenAI results retrived at log_scanner: %s' %response)
    save_logs = save_logs_to_S3(GenAI_logs, 'GenAI_logs')
    stark_core.log.msg('Saved GenAI review logs to S3 %s' %save_logs)
           
    return response

def save_logs_to_S3(payload, log_source):
    now = datetime.datetime.now()
    timestamp_str = now.strftime("%Y_%m_%d_%H_%M_%S")

    stark_core.log.msg('Processing payload to save_logs_to_S3 : %s' %payload)
   
    # Create an S3 client
    s3_client = boto3.client('s3')
    
    # Save the logs to S3
    bucket_name = 'stark-observability-logs'
    file_name = f"STARK_logs/{log_source}/{timestamp_str}.json"
        # Convert the payload dictionary to a JSON string
    logs = json.dumps(payload)
    
    stark_core.log.msg('Saving logs to S3 with File name: %s' %file_name)
    stark_core.log.msg('Saved logs: %s' %logs)
    s3_client.put_object(Body=logs, Bucket=bucket_name, Key=file_name)
    
    return {
        'statusCode': 200,
        'body': json.dumps('CloudWatch logs saved to S3.')
    }

def retrive_lambda_code(payload, line_errors):
    # Retrieve the code for the specified Lambda function
    lambda_function_name  = payload
    stark_core.log.msg('Retrieving lambda code from lambda_function_name: %s' %lambda_function_name)
    lambda_client = boto3.client('lambda')
    # get the lambda function's info
    lambda_info = lambda_client.get_function(FunctionName=lambda_function_name)

    # the response contains a 'Code' field which is a dict including 'Location' which is a presigned URL to download the code
    code_url = lambda_info['Code']['Location']
    r = requests.get(code_url)
    
    with open('/tmp/lambda_code.zip', 'wb') as f:
        f.write(r.content) 

    #unzip the lambda code
    with zipfile.ZipFile('/tmp/lambda_code.zip', 'r') as zip_ref:
        zip_ref.extractall('/tmp/')

    import os
    print(os.listdir('/tmp/'))

    # Read the code from the file
    with open('/tmp/__init__.py', 'r') as f:
        lambda_code = f.read()

    # Extract the portion of code
    #start_line = line_errors[0]-10
    #end_line = line_errors[-1]+10
    extracted_code = extract_code_errors(lambda_code, line_errors)

    stark_core.log.msg('Retrieved lambda code: %s' %extracted_code)
    return extracted_code

def extract_code_errors(code, line_errors):
    # Extract the portion of code with errors
    if not line_errors:
        return None
    lines = code.split('\n')
    total_lines = len(lines)
    start_line = max(line_errors[0]-5, 1)
    end_line = min(line_errors[-1]+5, total_lines)
    return '\n'.join(lines[start_line-1:end_line]) 

def search_lines_with_error(payload):
    line_numbers = set()
    error_phrase = "Syntax error in module '__init__': invalid syntax (__init__.py, line"

    for event in payload['events']:
        if error_phrase in event['message']:
            match = re.search(r"\(__init__.py, line (\d+)\)", event['message'])
            if match:
                line_numbers.add(int(match.group(1)))  # Add to set
    
    # Convert the set of line numbers to a sorted list
    line_numbers = sorted(list(line_numbers))
    
    # Print the number of filtered logs
    print(f"Found {len(line_numbers)} syntax errors")
     # Print the line numbers with syntax errors
    print(f"Syntax error in __init__.py at lines: {line_numbers}")
    return line_numbers