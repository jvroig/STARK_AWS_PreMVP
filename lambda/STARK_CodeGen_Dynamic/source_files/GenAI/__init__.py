import json
import base64
import boto3
import openai
import stark_core

ssm = boto3.client('ssm')
response = ssm.get_parameter(
    Name='[[STARK_PROJECT_VARNAME]]_OPENAI_API_KEY',
    WithDecryption=True
)
openai.api_key = response.get('Parameter',{}).get('Value','')

def lambda_handler(event, context):

    if event.get('isBase64Encoded') == True :
        stark_core.log.msg('isBase64Encoded = True')
        payload = json.loads(base64.b64decode(event.get('body'))).get('GenAIPayload',"")
        type    = json.loads(base64.b64decode(event.get('body'))).get('GenAIType',"")
    else:    
        stark_core.log.msg('isBase64Encoded = False')
        payload = json.loads(event.get('body')).get('GenAIPayload',"")
        type    = json.loads(event.get('body')).get('GenAIType',"")

    if type == 'customer_feedback':
        response = customer_feedback(payload)
    elif type == 'code_review':
        response = code_review(payload)
    elif type == 'log_review':
        response = log_review(payload)
    elif type == 'marketing':
        response = marketing(payload)
    else:
        #Error - invalid type submitted, or no type submitted
        stark_core.log.msg('Error - invalid type submitted, or no type submitted')
        pass

    #stark_core.log.msg('Lambda handler response: %s' %response)
    return {
        'statusCode': 200,
        'body': json.dumps({'genai_text': response}),
        #'body': json.dumps({'genai_text': response['body']}),
        #'context': json.dumps({'genai_context': response['context']}),
    }


def get_completion(prompt, model="gpt-3.5-turbo"):
    temperature=0.5
    messages = [{"role": "user", "content": prompt}]
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature, # this is the degree of randomness of the model's output
    )
 
    stark_core.log.msg('Temperature: %s' %temperature) 
    stark_core.log.msg('get_completion settings:')
    
    return {
        'body': response.choices[0].message["content"],
        'context': {
            'ChatGPT model': response.model,
            'temperature': temperature,
            'ChatGPT token usage': response.usage,
            'prompt': prompt,
        }
    }

def marketing(payload):
    stark_core.log.msg('Processing GenAI request for marketing payload: %s' %payload)
    sample_output = 'A sleek and minimalist dining table influenced by the elegant simplicity of Japanese aesthetics.'
    
    desired_keys = ['Furniture_Name','Style','Color_Variations','Material','Furniture_Type','Product_Category','Weight_in_kg','Lenght_in_meters', 'Width_in_meters', 'Height_in_meters']
    #remove unwanted keys from payload
    product_specs_dict = {key: payload[key] for key in desired_keys if key in payload} 

    prompt = f"""Your task is to extract relevant information for a copywriter and create a product description for a marketing website of a furniture store.
    The product specifications and sample output are given below which is delimited with triple backticks. 
    You don't need to include the exact product specifications but you can use keywords to provide a creative description of the product.
    Refrain from mentioning the exact dimensions.
    Limit the description to less than 50 words. 
    Product specifications: ```{product_specs_dict}```
    sample output: ```{sample_output}```  
    """ 
    stark_core.log.msg('Prompt: %s' %prompt)
    response = get_completion(prompt)
    stark_core.log.msg(response) 
    return response


def customer_feedback(payload):
    #stub sample, if we had gen AI use case about customer feedback
    pass


def code_review(payload):
    stark_core.log.msg('Processing GenAI request for code_review payload:')
    #retrive desired keys from payload
    logs = payload.get('logs',"")
    source_code = payload.get('source_code',"")

    output_format = {
        'Resolution': 'Recommended changes in the source code',
        'Explanation': 'Explain the recommended changes in detail',
        'Additional Information': 'Ask questions or request for additional information or code if needed, to be able to provide a more accurate solution',
    }
  
    prompt = f"""You are a Python developer working on a Python code. Your task is to look for syntax errors and provide recommendations on how to resolve the issues.The Cloudwatch log stream error and lambda python code are provided below which is delimited with triple backticks. 
    Note that there can be multiple errors in the code.
    Logs: ```{logs}```
    Code snippet from init.py module: ```{source_code}```
    Your recommendations should be in the output format provided below.
    Output format: ```{output_format}```
    """ 
    stark_core.log.msg('Prompt: %s' %prompt)
    response = get_completion(prompt)
    stark_core.log.msg(response)
    return response

def log_review(payload):
    stark_core.log.msg('Processing GenAI request for code_review payload:')
    log_streams = payload
    output_format = {
        'Error_code': 'Error_code',
        'Error_message': 'Explain in detail what the error message means',
        'logStreamName': 'logStreamName - where the error was found',
        'Possible cause': 'Explain the possible cause of the error',
        'Resolution': 'Provide the steps needed to resolve the issue and explain why',
    }
  
    prompt = f"""Your task is to review CloudWatch log streams for errors. Log streams are provided below which is delimited with triple backticks. 
    Log steams: ```{log_streams}```
    Provide recommendations on the possible root cause and ways to debug and resolve the issue following the output format provided below.
    Output format: ```{output_format}``` 
    """ 
    stark_core.log.msg('Prompt: %s' %prompt)
    response = get_completion(prompt)
    stark_core.log.msg(response)
    return response