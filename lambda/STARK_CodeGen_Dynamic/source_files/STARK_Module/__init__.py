#Python Standard Library
import base64
import json
import importlib
from urllib.parse import unquote
import sys

#Extra modules
import boto3
import uuid

#STARK
import stark_core
from stark_core import utilities
from stark_core import validation
from stark_core import data_abstraction

ddb = boto3.client('dynamodb')
s3_res = boto3.resource('s3')

#######
#CONFIG
ddb_table         = stark_core.ddb_table
bucket_name       = stark_core.bucket_name
region_name       = stark_core.region_name
page_limit        = stark_core.page_limit
bucket_url        = stark_core.bucket_url
bucket_tmp        = stark_core.bucket_tmp
pk_field          = "Module_Name"
default_sk        = "STARK|module"
sort_fields       = ["Module_Name", ]
relationships     = []
entity_upload_dir = stark_core.upload_dir + "STARK_Module/"
metadata          = {
    'Module_Name': {
        'value': '',
        'required': True,
        'max_length': '',
        'data_type': 'String',
        'state': None,
        'feedback': ''
    },
    'Descriptive_Title': {
        'value': '',
        'required': True,
        'max_length': '',
        'data_type': 'String',
        'state': None,
        'feedback': ''
    },
    'Target': {
        'value': '',
        'required': True,
        'max_length': '',
        'data_type': 'String',
        'state': None,
        'feedback': ''
    },
    'Description': {
        'value': '',
        'required': True,
        'max_length': '',
        'data_type': 'String',
        'state': None,
        'feedback': ''
    },
    'Module_Group': {
        'value': '',
        'required': True,
        'max_length': '',
        'data_type': 'String',
        'state': None,
        'feedback': ''
    },
    'Is_Menu_Item': {
        'value': '',
        'required': False,
        'max_length': '',
        'data_type': 'String',
        'state': None,
        'feedback': ''
    },
    'Is_Enabled': {
        'value': '',
        'required': False,
        'max_length': '',
        'data_type': 'String',
        'state': None,
        'feedback': ''
    },
    'Icon': {
        'value': '',
        'required': False,
        'max_length': '',
        'data_type': 'String',
        'state': None,
        'feedback': ''
    },
    'Priority': {
        'value': '',
        'required': True,
        'max_length': '',
        'data_type': 'Number',
        'state': None,
        'feedback': ''
    },
}
resp_obj = None
username = ""

############
#PERMISSIONS
stark_permissions = {
    'view': 'System Modules|View',
    'add': 'System Modules|Add',
    'delete': 'System Modules|Delete',
    'edit': 'System Modules|Edit',
    'report': 'System Modules|Report'
}

def lambda_handler(event, context):
    responseStatusCode = 200

    #Get request type
    request_type = event.get('queryStringParameters',{}).get('rt','')
    global username
    username = event.get('requestContext',{}).get('authorizer',{}).get('lambda',{}).get('Username','')

    if request_type == '':
        ########################
        #Handle non-GET requests

        #Get specific request method
        method  = event.get('requestContext').get('http').get('method')

        if event.get('isBase64Encoded') == True :
            payload = json.loads(base64.b64decode(event.get('body'))).get('STARK_Module',"")
        else:    
            payload = json.loads(event.get('body')).get('STARK_Module',"")

        data    = {}

        if payload == "":
            return {
                "isBase64Encoded": False,
                "statusCode": 400,
                "body": json.dumps("Client payload missing"),
                "headers": {
                    "Content-Type": "application/json",
                }
            }
        else:
            isInvalidPayload = False
            data['pk'] = payload.get('Module_Name')
            data['Descriptive_Title'] = payload.get('Descriptive_Title','')
            data['Target'] = payload.get('Target','')
            data['Description'] = payload.get('Description','')
            data['Module_Group'] = payload.get('Module_Group','')
            data['Is_Menu_Item'] = payload.get('Is_Menu_Item','')
            data['Is_Enabled'] = payload.get('Is_Enabled','')
            data['Icon'] = payload.get('Icon','')
            data['Priority'] = payload.get('Priority','')
            if payload.get('STARK_isReport', False) == False:
                data['orig_pk'] = payload.get('orig_Module_Name','')
                data['sk'] = payload.get('sk', '')
                if data['sk'] == "":
                    data['sk'] = default_sk
                ListView_index_values = []
                for field in sort_fields:
                    ListView_index_values.append(payload.get(field))
                data['STARK-ListView-sk'] = "|".join(ListView_index_values)
            else:
                #FIXME: Reporting payload processing:
                # - identifying filter fields
                # - operators validator
                for index, attributes in data.items():
                    if attributes['value'] != "":
                        if attributes['operator'] == "":
                            isInvalidPayload = True
                data['STARK_report_fields'] = payload.get('STARK_report_fields',[])
                data['STARK_isReport'] = payload.get('STARK_isReport', False)
                data['STARK_sum_fields'] = payload.get('STARK_sum_fields', [])
                data['STARK_count_fields'] = payload.get('STARK_count_fields', [])
                data['STARK_group_by_1'] = payload.get('STARK_group_by_1', '')

            data['STARK_uploaded_s3_keys'] = payload.get('STARK_uploaded_s3_keys',{})

            if isInvalidPayload:
                return {
                    "isBase64Encoded": False,
                    "statusCode": 400,
                    "body": json.dumps("Missing operators"),
                    "headers": {
                        "Content-Type": "application/json",
                    }
                }

        if method == "DELETE":
            if(stark_core.sec.is_authorized(stark_permissions['delete'], event, ddb)):
                response = delete_v2(data)
            else:
                responseStatusCode, response = stark_core.sec.authFailResponse

        elif method == "PUT":
            if(stark_core.sec.is_authorized(stark_permissions['edit'], event, ddb)):
                payload = data
                payload['Module_Name'] = data['pk']
                invalid_payload = validation.validate_form(payload, metadata)
                if len(invalid_payload) > 0:
                    return {
                        "isBase64Encoded": False,
                        "statusCode": responseStatusCode,
                        "body": json.dumps(invalid_payload),
                        "headers": {
                            "Content-Type": "application/json",
                        }
                    }
                else:
                #We can't update DDB PK, so if PK is different, we need to do ADD + DELETE
                    if data['orig_pk'] == data['pk']:
                        response = edit(data)
                    else:
                        response   = add(data, method)
                        data['pk'] = data['orig_pk']
                        response   = delete(data)
            else:
                responseStatusCode, response = stark_core.sec.authFailResponse

        elif method == "POST":
            if 'STARK_isReport' in data:
                if(stark_core.sec.is_authorized(stark_permissions['report'], event, ddb)):
                    response = report(data, default_sk)
                else:
                    responseStatusCode, response = stark_core.sec.authFailResponse
            else:
                if(stark_core.sec.is_authorized(stark_permissions['add'], event, ddb)):
                    payload = data
                    payload['Module_Name'] = data['pk']
                    invalid_payload = validation.validate_form(payload, metadata)
                    if len(invalid_payload) > 0:
                        return {
                            "isBase64Encoded": False,
                            "statusCode": responseStatusCode,
                            "body": json.dumps(invalid_payload),
                            "headers": {
                                "Content-Type": "application/json",
                            }
                        }

                    else:
                        response = add(data)
                else:
                    responseStatusCode, response = stark_core.sec.authFailResponse

        else:
            return {
                "isBase64Encoded": False,
                "statusCode": 400,
                "body": json.dumps("Could not handle API request"),
                "headers": {
                    "Content-Type": "application/json",
                }
            }

    else:
        ####################
        #Handle GET requests
        if request_type == "all":
            #check for submitted token
            lv_token = event.get('queryStringParameters',{}).get('nt', None)
            if lv_token != None:
                lv_token = unquote(lv_token)
                lv_token = json.loads(lv_token)

            items, next_token = get_all(default_sk, lv_token)

            response = {
                'Next_Token': json.dumps(next_token),
                'Items': items
            }
        
        elif request_type == "get_fields":
            fields = event.get('queryStringParameters').get('fields','')
            fields = fields.split(",")
            response = get_fields(fields, default_sk)

        elif request_type == "detail":

            pk = event.get('queryStringParameters').get('Module_Name','')
            sk = event.get('queryStringParameters').get('sk','')
            if sk == "":
                sk = default_sk

            response = get_by_pk(pk, sk)

        elif request_type == "usermodules":
            #FIXME: Getting the username should be a STARK Core framework utility. Only here for now for MVP implem, to not hold up more urgent dependent features
            #FIXME: When framework-ized, getting the requestContext should be at the beginning of the handler, and will exit if handler needs the Username and is not present (i.e., not properly authorized)
            #FIXME: Make sure for this framework-ized implementation that it will still work when Framework components call each other directly through the STARK registry instead of through API Gateway.
            
            response = get_user_modules(username, default_sk)

        else:
            return {
                "isBase64Encoded": False,
                "statusCode": 400,
                "body": json.dumps("Could not handle GET request - unknown request type"),
                "headers": {
                    "Content-Type": "application/json",
                }
            }

    return {
        "isBase64Encoded": False,
        "statusCode": responseStatusCode,
        "body": json.dumps(response),
        "headers": {
            "Content-Type": "application/json",
        }
    }

def report(data, sk=default_sk):
    #FIXME: THIS IS A STUB, WILL NEED TO BE UPDATED WITH
    #   ENHANCED LISTVIEW LOGIC LATER WHEN WE ACTUALLY IMPLEMENT REPORTING

    temp_string_filter = ""
    object_expression_value = {':sk' : {'S' : sk}}
    report_param_dict = {}
    for key, index in data.items():
        if key not in ["STARK_isReport", "STARK_report_fields", "STARK_uploaded_s3_keys", 
                        "STARK_sum_fields", 'STARK_count_fields', 'STARK_group_by_1']:																			  
            if index['value'] != "":
                processed_operator_and_parameter_dict = utilities.compose_report_operators_and_parameters(key, index, metadata) 
                temp_string_filter += processed_operator_and_parameter_dict['filter_string']
                object_expression_value.update(processed_operator_and_parameter_dict['expression_values'])
                report_param_dict.update(processed_operator_and_parameter_dict['report_params'])
    string_filter = temp_string_filter[1:-3]

    next_token = 'initial'
    items = []
    ddb_arguments = {}
    aggregated_results = {}
    ddb_arguments['TableName'] = ddb_table
    ddb_arguments['IndexName'] = "STARK-ListView-Index"
    ddb_arguments['Select'] = "ALL_ATTRIBUTES"
    ddb_arguments['Limit'] = 2
    ddb_arguments['ReturnConsumedCapacity'] = 'TOTAL'
    ddb_arguments['KeyConditionExpression'] = 'sk = :sk'
    ddb_arguments['ExpressionAttributeValues'] = object_expression_value

    if temp_string_filter != "":
        ddb_arguments['FilterExpression'] = string_filter

    while next_token != None:
        next_token = '' if next_token == 'initial' else next_token

        if next_token != '':
            ddb_arguments['ExclusiveStartKey']=next_token

        response = ddb.query(**ddb_arguments)
        raw = response.get('Items')
        next_token = response.get('LastEvaluatedKey')
        aggregate_report = False if data['STARK_group_by_1'] == '' else True
        for record in raw:
            item = map_results(record)
            if aggregate_report:
                aggregate_key = data['STARK_group_by_1']
                aggregate_key_value = item.get(aggregate_key)
                if aggregate_key_value in aggregated_results:
                    for field in data['STARK_count_fields']:
                        count_index_name = f"Count of {field}"
                        aggregated_results[aggregate_key_value][count_index_name] += 1

                    for field in data['STARK_sum_fields']:
                        sum_index_name = f"Sum of {field}"
                        sum_value = float(item.get(field))
                        aggregated_results[aggregate_key_value][sum_index_name] = round(aggregated_results[aggregate_key_value][sum_index_name], 1) + sum_value

                    for column in data['STARK_report_fields']:
                        if column != aggregate_key:  
                            aggregated_results[aggregate_key_value][column] = item.get(column.replace(" ","_"))

                else:
                    temp_dict = { aggregate_key : aggregate_key_value}
                    for field in data['STARK_count_fields']:
                        count_index_name = f"Count of {field}"
                        temp_dict.update({
                            count_index_name:  1
                        })

                    for field in data['STARK_sum_fields']:
                        sum_index_name = f"Sum of {field}"
                        sum_value = float(item.get(field))
                        temp_dict.update({
                            sum_index_name: sum_value
                        })

                    for column in data['STARK_report_fields']:
                        if column != aggregate_key:  
                            temp_dict.update({
                                column: item.get(column.replace(" ","_"))
                            })

                    aggregated_results[aggregate_key_value] = temp_dict
            else:
                items.append(item)

    report_list = []
    csv_file = ''
    pdf_file = ''
    report_header = []
    diff_list = []
    if aggregate_report:
        temp_list = []
        for key, val in aggregated_results.items():
            temp_header = []
            for index in val.keys():
                temp_header.append(index.replace("_"," "))
            temp_list.append(val)
            report_header = temp_header
        items = temp_list
    else:
        display_fields = data['STARK_report_fields']
        master_fields = []
        for key in metadata.keys():
            master_fields.append(key.replace("_"," "))
        if len(display_fields) > 0:
            report_header = display_fields
            diff_list = list(set(master_fields) - set(display_fields))
        else:
            report_header = master_fields
							   

    if len(items) > 0:
        for key in items:
            temp_dict = {}
            #remove primary identifiers and STARK attributes
            if not aggregate_report:
                key.pop("sk")
            for index, value in key.items():
                temp_dict[index.replace("_"," ")] = value
            report_list.append(temp_dict)

        

        report_list = utilities.filter_report_list(report_list, diff_list)
        csv_file, file_buff_value = utilities.create_csv(report_list, report_header)
        utilities.save_object_to_bucket(file_buff_value, csv_file)
        pdf_file, pdf_output = utilities.prepare_pdf_data(report_list, report_header, report_param_dict, metadata, pk_field)
        utilities.save_object_to_bucket(pdf_output, pdf_file)

    csv_bucket_key = bucket_tmp + csv_file
    pdf_bucket_key = bucket_tmp + pdf_file

    if not aggregate_report:
        report_list = items
        new_report_list = []
        for row in report_list:
            temp_dict = {}
            for index, value in row.items():
                temp_dict[index.replace("_"," ")] = value
            new_report_list.append(temp_dict)
        report_list = new_report_list

    return report_list, csv_bucket_key, pdf_bucket_key

def get_all(sk=default_sk, lv_token=None, db_handler = None):
    if db_handler == None:
        db_handler = ddb

    ExpressionAttributeNamesDict = {
        '#isDeleted' : 'STARK-Is-Deleted',
    }
    items = []
    ddb_arguments = {}
    ddb_arguments['TableName'] = ddb_table
    ddb_arguments['IndexName'] = "STARK-ListView-Index"
    ddb_arguments['Select'] = "ALL_ATTRIBUTES"
    ddb_arguments['Limit'] = page_limit
    ddb_arguments['ReturnConsumedCapacity'] = 'TOTAL'
    ddb_arguments['KeyConditionExpression'] = 'sk = :sk'
    ddb_arguments['FilterExpression'] = 'attribute_not_exists(#isDeleted)'
    ddb_arguments['ExpressionAttributeValues'] = { ':sk' : {'S' : sk } }
    ddb_arguments['ExpressionAttributeNames'] = ExpressionAttributeNamesDict

    if lv_token != None:
        ddb_arguments['ExclusiveStartKey'] = lv_token

    next_token = ''
    while len(items) < page_limit and next_token is not None:
        if next_token != '':
            ddb_arguments['ExclusiveStartKey']=next_token

        response = db_handler.query(**ddb_arguments)
        raw = response.get('Items')
        next_token = response.get('LastEvaluatedKey')

        for record in raw:
            items.append(map_results(record))

    #Get the "next" token, pass to calling function. This enables a "next page" request later.
    next_token = response.get('LastEvaluatedKey')

    return items, next_token

def get_by_pk(pk, sk=default_sk, db_handler = None):
    if db_handler == None:
        db_handler = ddb

    ddb_arguments = {}
    ddb_arguments['TableName'] = ddb_table
    ddb_arguments['Select'] = "ALL_ATTRIBUTES"
    ddb_arguments['KeyConditionExpression'] = "#pk = :pk and #sk = :sk"
    ddb_arguments['ExpressionAttributeNames'] = {
                                                '#pk' : 'pk',
                                                '#sk' : 'sk'
                                            }
    ddb_arguments['ExpressionAttributeValues'] = {
                                                ':pk' : {'S' : pk },
                                                ':sk' : {'S' : sk }
                                            }
    response = db_handler.query(**ddb_arguments)
    raw = response.get('Items')

    #Map to expected structure
    response = {}
    response['item'] = map_results(raw[0])

    return response

def delete_v2(data, db_handler = None):
    if db_handler == None:
        db_handler = ddb

    UpdateExpressionString = "SET #STARKDeletedBy = :STARKDeletedBy, #STARKDeletedTs = :STARKDeletedTS, #STARKIsDeleted = :STARKIsDeleted, #ttl = :ttl" 
    ExpressionAttributeNamesDict = {
        '#STARKDeletedBy': 'STARK-Deleted-By',
        '#STARKDeletedTs': 'STARK-Deleted-TS',
        '#STARKIsDeleted': 'STARK-Is-Deleted',
        '#ttl': 'TTL'
    }
    ExpressionAttributeValuesDict = utilities.append_record_metadata('delete', username)

    pk = data.get('pk','')
    sk = data.get('sk','')
    if sk == '': sk = default_sk

    ddb_arguments = {}
    ddb_arguments['TableName'] = ddb_table
    ddb_arguments['Key'] = {
            'pk' : {'S' : pk},
            'sk' : {'S' : sk}
        }

    ddb_arguments['ReturnValues'] = 'UPDATED_NEW'
    ddb_arguments['UpdateExpression'] = UpdateExpressionString
    ddb_arguments['ExpressionAttributeNames'] = ExpressionAttributeNamesDict
    ddb_arguments['ExpressionAttributeValues'] = ExpressionAttributeValuesDict

    response = db_handler.update_item(**ddb_arguments)
    global resp_obj
    resp_obj = response
    return "OK"

def delete(data, db_handler = None):
    if db_handler == None:
        db_handler = ddb

    pk = data.get('pk','')
    sk = data.get('sk','')
    if sk == '': sk = default_sk

    ddb_arguments = {}
    ddb_arguments['TableName'] = ddb_table
    ddb_arguments['Key'] = {
            'pk' : {'S' : pk},
            'sk' : {'S' : sk}
        }

    response = db_handler.delete_item(**ddb_arguments)
    global resp_obj
    resp_obj = response

    return "OK"

def edit(data, db_handler = None):
    if db_handler == None:
        db_handler = ddb
    pk = data.get('pk', '')
    sk = data.get('sk', '')
    if sk == '': sk = default_sk
    Descriptive_Title = str(data.get('Descriptive_Title', ''))
    Target = str(data.get('Target', ''))
    Description = str(data.get('Description', ''))
    Module_Group = str(data.get('Module_Group', ''))
    Is_Menu_Item = data.get('Is_Menu_Item', False)
    Is_Enabled = data.get('Is_Enabled', False)
    Icon = str(data.get('Icon', ''))
    Priority = str(data.get('Priority', ''))

    UpdateExpressionString = "SET #Descriptive_Title = :Descriptive_Title, #Target = :Target, #Description = :Description, #Module_Group = :Module_Group, #Is_Menu_Item = :Is_Menu_Item, #Is_Enabled = :Is_Enabled, #Icon = :Icon, #Priority = :Priority, #STARKListViewsk = :STARKListViewsk, #STARKUpdatedBy = :STARKUpdatedBy, #STARKUpdatedTs = :STARKUpdatedTS" 
    ExpressionAttributeNamesDict = {
        '#Descriptive_Title' : 'Descriptive_Title',
        '#Target' : 'Target',
        '#Description' : 'Description',
        '#Module_Group' : 'Module_Group',
        '#Is_Menu_Item' : 'Is_Menu_Item',
        '#Is_Enabled' : 'Is_Enabled',
        '#Icon' : 'Icon',
        '#Priority' : 'Priority',
        '#STARKListViewsk' : 'STARK-ListView-sk',
        '#STARKUpdatedBy': 'STARK-Updated-By',
        '#STARKUpdatedTs': 'STARK-Updated-TS'
    }
    tempExpressionAttributeValuesDict = {
        ':Descriptive_Title' : {'S' : Descriptive_Title },
        ':Target' : {'S' : Target },
        ':Description' : {'S' : Description },
        ':Module_Group' : {'S' : Module_Group },
        ':Is_Menu_Item' : {'BOOL' : Is_Menu_Item },
        ':Is_Enabled' : {'BOOL' : Is_Enabled },
        ':Icon' : {'S' : Icon },
        ':Priority' : {'N' : Priority },
		':STARKListViewsk' : {'S' : data['STARK-ListView-sk']}
    }
    ExpressionAttributeValuesDict = tempExpressionAttributeValuesDict | utilities.append_record_metadata('edit', username)
    ddb_arguments = {}
    ddb_arguments['TableName'] = ddb_table
    ddb_arguments['Key'] = {
            'pk' : {'S' : pk},
            'sk' : {'S' : sk}
        }
    ddb_arguments['ReturnValues'] = 'UPDATED_NEW'
    ddb_arguments['UpdateExpression'] = UpdateExpressionString
    ddb_arguments['ExpressionAttributeNames'] = ExpressionAttributeNamesDict
    ddb_arguments['ExpressionAttributeValues'] = ExpressionAttributeValuesDict

    response = db_handler.update_item(**ddb_arguments)


    global resp_obj
    resp_obj = response
    return "OK"

def add(data, method='POST', db_handler=None):
    if db_handler == None:
        db_handler = ddb
    pk = data.get('pk', '')
    sk = data.get('sk', '')
    if sk == '': sk = default_sk
    Descriptive_Title = str(data.get('Descriptive_Title', ''))
    Target = str(data.get('Target', ''))
    Description = str(data.get('Description', ''))
    Module_Group = str(data.get('Module_Group', ''))
    Is_Menu_Item = data.get('Is_Menu_Item', False)
    Is_Enabled = data.get('Is_Enabled', False)
    Icon = str(data.get('Icon', ''))
    Priority = str(data.get('Priority', ''))

    item = utilities.append_record_metadata('add', username)
    item['pk'] = {'S' : pk}
    item['sk'] = {'S' : sk}
    item['Descriptive_Title'] = {'S' : Descriptive_Title}
    item['Target'] = {'S' : Target}
    item['Description'] = {'S' : Description}
    item['Module_Group'] = {'S' : Module_Group}
    item['Is_Menu_Item'] = {'BOOL' : Is_Menu_Item}
    item['Is_Enabled'] = {'BOOL' : Is_Enabled}
    item['Icon'] = {'S' : Icon}
    item['Priority'] = {'N' : Priority}

    if data.get('STARK-ListView-sk','') == '':
        item['STARK-ListView-sk'] = {'S' : create_listview_index_value(data)}
    else:
        item['STARK-ListView-sk'] = {'S' : data['STARK-ListView-sk']}

    ddb_arguments = {}
    ddb_arguments['TableName'] = ddb_table
    ddb_arguments['Item'] = item
    response = db_handler.put_item(**ddb_arguments)

    global resp_obj
    resp_obj = response
    return "OK"
	
def create_listview_index_value(data):
    ListView_index_values = []
    for field in sort_fields:
        if field == pk_field:
            ListView_index_values.append(data['pk'])												  
        else:
            ListView_index_values.append(data.get(field))
    STARK_ListView_sk = "|".join(ListView_index_values)
    return STARK_ListView_sk


def map_results(record):
    item = {}
    item['Module_Name'] = record.get('pk', {}).get('S','')
    item['sk'] = record.get('sk',{}).get('S','')
    item['Descriptive_Title'] = record.get('Descriptive_Title',{}).get('S','')
    item['Target'] = record.get('Target',{}).get('S','')
    item['Description'] = record.get('Description',{}).get('S','')
    item['Module_Group'] = record.get('Module_Group',{}).get('S','')
    item['Is_Menu_Item'] = record.get('Is_Menu_Item',{}).get('BOOL','')
    item['Is_Enabled'] = record.get('Is_Enabled',{}).get('BOOL','')
    item['Icon'] = record.get('Icon',{}).get('S','')
    item['Priority'] = record.get('Priority',{}).get('N','')
    return item

# def generate_reports(mapped_results = [], display_fields=[], report_params = {}): 
#     diff_list = []
#     master_fields = ['Module Name', 'Descriptive Title', 'Target', 'Description', 'Module Group', 'Is Menu Item', 'Is Enabled', 'Icon', 'Priority', ]
#     if len(display_fields) > 0:
#         csv_header = display_fields
#         diff_list = list(set(master_fields) - set(display_fields))
#     else:
#         csv_header = master_fields

#     report_list = []
#     for key in mapped_results:
#         temp_dict = {}
#         #remove primary identifiers and STARK attributes
#         key.pop("sk")
#         for index, value in key.items():
#             temp_dict[index.replace("_"," ")] = value
#         report_list.append(temp_dict)

#     file_buff = StringIO()
#     writer = csv.DictWriter(file_buff, fieldnames=csv_header)
#     writer.writeheader()
#     for rows in report_list:
#         for index in diff_list:
#             rows.pop(index)
#         writer.writerow(rows)
#     filename = f"{str(uuid.uuid4())}"
#     csv_file = f"{filename}.csv"
#     pdf_file = f"{filename}.pdf"
#     s3_action = s3.put_object(
#         ACL='public-read',
#         Body= file_buff.getvalue(),
#         Bucket=bucket_name,
#         Key='tmp/'+csv_file
#     )

#     prepare_pdf_data(report_list, csv_header, pdf_file, report_params)

#     csv_bucket_key = bucket_tmp + csv_file
#     pdf_bucket_key = bucket_tmp + pdf_file

#     return csv_bucket_key, pdf_bucket_key

																		
def create_listview_index_value(data):
    ListView_index_values = []
    for field in sort_fields:
        if field == pk_field:
            ListView_index_values.append(data['pk'])
        else:
            ListView_index_values.append(data.get(field))
    STARK_ListView_sk = "|".join(ListView_index_values)
    return STARK_ListView_sk

def get_all_by_old_parent_value(old_pk_val, attribute, sk = default_sk):

    string_filter = " #Attribute = :old_parent_value"
    object_expression_value = {':sk' : {'S' : sk},
                                ':old_parent_value': {'S' : old_pk_val}}
    ExpressionAttributeNamesDict = {
        '#Attribute' : attribute,
    }

    ddb_arguments = {}
    ddb_arguments['TableName'] = ddb_table
    ddb_arguments['IndexName'] = "STARK-ListView-Index"
    ddb_arguments['Select'] = "ALL_ATTRIBUTES"
    ddb_arguments['ReturnConsumedCapacity'] = 'TOTAL'
    ddb_arguments['FilterExpression'] = string_filter
    ddb_arguments['KeyConditionExpression'] = 'sk = :sk'
    ddb_arguments['ExpressionAttributeValues'] = object_expression_value
    ddb_arguments['ExpressionAttributeNames'] = ExpressionAttributeNamesDict

    next_token = 'initial'
    items = []
    while next_token != None:
        next_token = '' if next_token == 'initial' else next_token

        if next_token != '':
            ddb_arguments['ExclusiveStartKey']=next_token
																				  
						  

        response = ddb.query(**ddb_arguments)
        raw = response.get('Items')
        next_token = response.get('LastEvaluatedKey')
        for record in raw:
            item = map_results(record)
            #add pk as literal 'pk' value
            #and STARK-ListView-Sk
            item['pk'] = record.get('pk', {}).get('S','')
            item['STARK-ListView-sk'] = record.get('STARK-ListView-sk',{}).get('S','')
            items.append(item)

    return items

# def prepare_pdf_data(data_to_tuple, master_fields, pdf_filename, report_params):
#     #FIXME: PDF GENERATOR: can be outsourced to a layer, for refining 
#     master_fields.insert(0, '#')
#     numerical_columns = {}
#     for key, items in metadata.items():
#         if items['data_type'] == 'number':
#             numerical_columns.update({key: 0})
#     row_list = []
#     counter = 1 
#     for key in data_to_tuple:
#         column_list = []
#         for index in master_fields:
#             if(index != '#'):
#                 if index in numerical_columns.keys():
#                     numerical_columns[index] += int(key[index])
#                 column_list.append(key[index])
#         column_list.insert(0, str(counter)) 
#         row_list.append(tuple(column_list))
#         counter += 1

#     if len(numerical_columns) > 0:
#         column_list = []
#         for values in master_fields:
#             if values in numerical_columns:
#                 column_list.append(str(numerical_columns.get(values, '')))
#             else:
#                 column_list.append('')
#         row_list.append(column_list)

#     header_tuple = tuple(master_fields) 
#     data_tuple = tuple(row_list)

#     pdf = utilities.create_pdf(header_tuple, data_tuple, report_params, pk_field, metadata)
#     s3_action = s3.put_object(
#         ACL='public-read',
#         Body= pdf.output(),
#         Bucket=bucket_name,
#         Key='tmp/'+pdf_filename
#     )

def get_fields(fields, sk = default_sk):

    ExpressionAttributeNamesDict = {
        '#isDeleted' : 'STARK-Is-Deleted',
    }
    ddb_arguments = {}
    next_token = 'initial'
    items = []
    while next_token != None:
        next_token = '' if next_token == 'initial' else next_token
        ddb_arguments['TableName']=ddb_table
        ddb_arguments['IndexName']="STARK-ListView-Index"
        ddb_arguments['Limit']=5
        ddb_arguments['ReturnConsumedCapacity']='TOTAL'
        ddb_arguments['KeyConditionExpression']='sk = :sk'
        ddb_arguments['FilterExpression'] = 'attribute_not_exists(#isDeleted)'
        ddb_arguments['ExpressionAttributeValues'] = { ':sk' : {'S' : sk}}
        ddb_arguments['ExpressionAttributeNames'] = ExpressionAttributeNamesDict

        if next_token != '':
            ddb_arguments['ExclusiveStartKey']=next_token

        response = ddb.query(**ddb_arguments)
        raw = response.get('Items')

        for record in raw:

            item = {}
            for field in fields:
                if field == pk_field:
                    get_record = record.get('pk',{}).get('S','')
                else:
                    get_record = record.get(field,{}).get('S','')

                item[field] = get_record
            items.append(item)
        #Get the "next" token, pass to calling function. This enables a "next page" request later.
        next_token = response.get('LastEvaluatedKey')

    return items

def unique(list1):
 
    # initialize a null list
    unique_list = []
 
    # traverse for all elements
    for x in list1:
        # check if exists in unique_list or not
        if x not in unique_list:
            unique_list.append(x)
    
    return unique_list

def get_user_modules(username, sk=default_sk):
    ########################
    #1.GET USER PERMISSIONS
    #FIXME: Getting user permissions should be a STARK Core framework utility, only here for now for urgent MVP implementation,
    #       to not hold up related features that need implementation ASAP
    response = ddb.query(
        TableName=ddb_table,
        Select='ALL_ATTRIBUTES',
        ReturnConsumedCapacity='TOTAL',
        KeyConditionExpression='pk = :pk and sk = :sk',
        ExpressionAttributeValues={
            ':pk' : {'S' : username},
            ':sk' : {'S' : "STARK|user|permissions"}
        }
    )

    raw = response.get('Items')
    permissions = []
    for record in raw:
        permission_string = record.get('Permissions',{}).get('S','')
    
    #Split permission_string by the delimeter (comma+space / ", ")
    permissions_list = permission_string.split(", ")

    ##################################
    #GET SYSTEM MODULES (ENABLED ONLY)
    response = ddb.query(
        TableName=ddb_table,
        IndexName="STARK-ListView-Index",
        Select='ALL_ATTRIBUTES',
        ReturnConsumedCapacity='TOTAL',
        KeyConditionExpression='sk = :sk',
        ExpressionAttributeValues={
            ':sk' : {'S' : sk}
        }
    )

    raw = response.get('Items')

    items = []
    grps = []
    for record in raw:
        if record.get('Is_Enabled',{}).get('BOOL','') == True:
            if record.get('Is_Menu_Item',{}).get('BOOL','') == True:
                if record.get('pk', {}).get('S','') in permissions_list:
                    #Only modules that are ENABLED, are MENU ITEMS, and are found in the user's permissions list are registered
                    item = {}
                    item['title'] = record.get('Descriptive_Title',{}).get('S','')
                    item['image'] = record.get('Icon',{}).get('S','')
                    #item['image_alt'] = record.get #FIXME: This isn't in the system modules model, because it wasn't in Cobalt as well... add please.
                    item['href'] = record.get('Target',{}).get('S','')
                    item['group'] = record.get('Module_Group',{}).get('S','')
                    item['priority'] = record.get('Priority',{}).get('N','')
                    grps.append(item['group'])
                    items.append(item)

    report_items = []
    for record in raw:
        if 'pk' in record and '|Report' in record['pk']['S'] and 'STARK_' not in record.get('Target', {}).get('S'):
            if record.get('pk', {}).get('S','') in permissions_list:
                item = {}
                item = record.get('Descriptive_Title',{}).get('S','').replace('Report ', '')
                report_items.append(item)
    
    grps = unique(grps) 

    from os import getcwd 
    STARK_folder = getcwd() + '/STARK_Module_Groups'
    sys.path = [STARK_folder] + sys.path
    import STARK_Module_Groups as module_groups
    module_grps = module_groups.get_module_groups(grps)

    return {
        'items': items,
        'module_grps': module_grps,
        'report_items': report_items
    }