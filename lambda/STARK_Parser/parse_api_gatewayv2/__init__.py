#Python Standard Library
import base64
import json
import convert_friendly_to_system

def parse(data):

    #API Gateway URL will be updated later (it will not have been created by the time the Parser runs)
    #   The task now is to just create the section and key for it.
    #   The System PreLaunch will take care of updating it with the API G URL value later.

    #As for other clouds, api gateway's information will be composed here since we need to supply it to the terraform script.
    if data['cloud_provider'] == 'AWS':
        parsed = { "URL": '' }
    else:
        # we will be manually composing the url here
        #by combining the parsed project name and the azure api url
        parsed_project_name = convert_friendly_to_system.to_az_api_management_name(data['project_name'])
        parsed_project_name =  parsed_project_name + f"{data['unique_id']}"
        url = "https://"+parsed_project_name+".azure-api.net"
        parsed = { 
            "URL": url,
            "Name": parsed_project_name
        }

    return parsed