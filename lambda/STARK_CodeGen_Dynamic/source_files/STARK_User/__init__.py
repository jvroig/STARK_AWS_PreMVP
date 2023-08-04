#Python Standard Library
import base64
import json
import importlib
from urllib.parse import unquote
import stark_scrypt as scrypt
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
pk_field          = "Username"
default_sk        = "STARK|user|info"
sort_fields       = ["Username", ]
relationships     = []
# relationships     = [{'parent': 'Users', 'child': 'STARK_User_Permissions', 'attribute': 'Users'}]
entity_upload_dir = stark_core.upload_dir + "STARK_User/"
metadata          = {
    'Username': {
        'value': '',
        'required': True,
        'max_length': '',
        'data_type': 'String',
        'state': None,
        'feedback': ''
    },
    'Full_Name': {
        'value': '',
        'required': True,
        'max_length': '',
        'data_type': 'String',
        'state': None,
        'feedback': ''
    },
    'Nickname': {
        'value': '',
        'required': True,
        'max_length': '',
        'data_type': 'String',
        'state': None,
        'feedback': ''
    },
    # 'Password_Hash': {
    #     'value': '',
    #     'required': True,
    #     'max_length': '',
    #     'data_type': 'String',
    #     'state': None,
    #     'feedback': ''
    # },
    'Role': {
        'value': '',
        'required': True,
        'max_length': '',
        'data_type': 'String',
        'state': None,
        'feedback': ''
    },
}
resp_obj = None
username = ""

############
#PERMISSIONS
stark_permissions = {
    'view': 'Users|View',
    'add': 'Users|Add',
    'delete': 'Users|Delete',
    'edit': 'Users|Edit',
    'report': 'Users|Report'
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
            payload = json.loads(base64.b64decode(event.get('body'))).get('STARK_User',"")
        else:    
            payload = json.loads(event.get('body')).get('STARK_User',"")

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
            data['pk'] = payload.get('Username')
            data['Full_Name'] = payload.get('Full_Name','')
            data['Nickname'] = payload.get('Nickname','')
            data['Role'] = payload.get('Role','')
            if payload.get('STARK_isReport', False) == False:
                data['orig_pk'] = payload.get('orig_Username','')
                data['sk'] = payload.get('sk', '')
                data['Password_Hash'] = payload.get('Password_Hash','')
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
                payload['Username'] = data['pk']
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
                    payload['Username'] = data['pk']
                    print(payload)
                    print(metadata)
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

        elif request_type == "detail":

            pk = event.get('queryStringParameters').get('Username','')
            sk = event.get('queryStringParameters').get('sk','')
            if sk == "":
                sk = default_sk

            response = get_by_pk(pk, sk)
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
        "statusCode": 200,
        "body": json.dumps(response),
        "headers": {
            "Content-Type": "application/json",
        }
    }

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
    Full_Name = str(data.get('Full_Name', ''))
    Nickname = str(data.get('Nickname', ''))
    Password_Hash = str(data.get('Password_Hash', ''))
    Role = str(data.get('Role', ''))

    UpdateExpressionString = "SET #Full_Name = :Full_Name, #Nickname = :Nickname, #Role = :Role" 
    ExpressionAttributeNamesDict = {
        '#Full_Name' : 'Full_Name',
        '#Nickname' : 'Nickname',
        '#Role' : 'Role',
        '#STARKUpdatedBy': 'STARK-Updated-By',
        '#STARKUpdatedTs': 'STARK-Updated-TS'
    }
    tempExpressionAttributeValuesDict = {
        ':Full_Name' : {'S' : Full_Name },
        ':Nickname' : {'S' : Nickname },
        ':Role' : {'S' : Role },
    }

    #If Password_Hash is not an empty string, this means it's a password reset request.
    if Password_Hash != '':
        UpdateExpressionString += ", #Password_Hash = :Password_Hash"
        ExpressionAttributeNamesDict['#Password_Hash'] = 'Password_Hash'
        tempExpressionAttributeValuesDict[':Password_Hash'] = {'S': scrypt.create_hash(Password_Hash)}

    STARK_ListView_sk = data.get('STARK-ListView-sk','')
    if STARK_ListView_sk == '':
        STARK_ListView_sk = create_listview_index_value(data)

    UpdateExpressionString += ", #STARKListViewsk = :STARKListViewsk, #STARKUpdatedBy = :STARKUpdatedBy, #STARKUpdatedTs = :STARKUpdatedTS"
    ExpressionAttributeNamesDict['#STARKListViewsk']  = 'STARK-ListView-sk'
    tempExpressionAttributeValuesDict[':STARKListViewsk'] = {'S' : data['STARK-ListView-sk']}
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

    # for relation in relationships['has_one']:
    #     cascade_pk_change_to_child(data, relation['entity'], relation['attribute'])

    assign_role_permissions({'Username': pk, 'Role': Role })

    global resp_obj
    resp_obj = response
    return "OK"

def add(data, method='POST', db_handler=None):
    if db_handler == None:
        db_handler = ddb
    pk = data.get('pk', '')
    sk = data.get('sk', '')
    if sk == '': sk = default_sk
    Full_Name = str(data.get('Full_Name', ''))
    Nickname = str(data.get('Nickname', ''))
    Password_Hash = str(data.get('Password_Hash', ''))
    Role = str(data.get('Role', ''))

    item = utilities.append_record_metadata('add', username)
    item['pk'] = {'S' : pk}
    item['sk'] = {'S' : sk}
    item['Full_Name'] = {'S' : Full_Name}
    item['Nickname'] = {'S' : Nickname}
    item['Password_Hash'] = {'S' : scrypt.create_hash(Password_Hash)}
    item['Role'] = {'S' : Role}

    if data.get('STARK-ListView-sk','') == '':
        item['STARK-ListView-sk'] = {'S' : create_listview_index_value(data)}
    else:
        item['STARK-ListView-sk'] = {'S' : data['STARK-ListView-sk']}

    ddb_arguments = {}
    ddb_arguments['TableName'] = ddb_table
    ddb_arguments['Item'] = item
    response = db_handler.put_item(**ddb_arguments)

    assign_role_permissions({'Username': pk, 'Role': Role })
    print(assign_role_permissions({'Username': pk, 'Role': Role }))

    # for relation in relationships['has_one']:
    #     cascade_pk_change_to_child(data, relation['entity'], relation['attribute'])
    global resp_obj
    resp_obj = response
    return "OK"

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

def compose_report_operators_and_parameters(key, data):
    composed_filter_dict = {"filter_string":"","expression_values": {}}
    if data['operator'] == "IN":
        string_split = data['value'].split(',')
        composed_filter_dict['filter_string'] += f" {key} IN "
        temp_in_string = ""
        in_string = ""
        in_counter = 1
        composed_filter_dict['report_params'] = {key : f"Is in {data['value']}"}
        for in_index in string_split:
            in_string += f" :inParam{in_counter}, "
            composed_filter_dict['expression_values'][f":inParam{in_counter}"] = {data['type'] : in_index.strip()}
            in_counter += 1
        temp_in_string = in_string[1:-2]
        composed_filter_dict['filter_string'] += f"({temp_in_string}) AND"
    elif data['operator'] in [ "contains", "begins_with" ]:
        composed_filter_dict['filter_string'] += f" {data['operator']}({key}, :{key}) AND"
        composed_filter_dict['expression_values'][f":{key}"] = {data['type'] : data['value'].strip()}
        composed_filter_dict['report_params'] = {key : f"{data['operator'].capitalize().replace('_', ' ')} {data['value']}"}
    elif data['operator'] == "between":
        from_to_split = data['value'].split(',')
        composed_filter_dict['filter_string'] += f" ({key} BETWEEN :from{key} AND :to{key}) AND"
        composed_filter_dict['expression_values'][f":from{key}"] = {data['type'] : from_to_split[0].strip()}
        composed_filter_dict['expression_values'][f":to{key}"] = {data['type'] : from_to_split[1].strip()}
        composed_filter_dict['report_params'] = {key : f"Between {from_to_split[0].strip()} and {from_to_split[1].strip()}"}
    else:
        composed_filter_dict['filter_string'] += f" {key} {data['operator']} :{key} AND"
        composed_filter_dict['expression_values'][f":{key}"] = {data['type'] : data['value'].strip()}
        operator_string_equivalent = ""
        if data['operator'] == '=':
            operator_string_equivalent = 'Is equal to'
        elif data['operator'] == '>':
            operator_string_equivalent = 'Is greater than'
        elif data['operator'] == '>=':
            operator_string_equivalent = 'Is greater than or equal to'
        elif data['operator'] == '<':
            operator_string_equivalent = 'Is less than'
        elif data['operator'] == '<=':
            operator_string_equivalent = 'Is greater than or equal to'
        elif data['operator'] == '<=':
            operator_string_equivalent = 'Is not equal to'
        else:
            operator_string_equivalent = 'Invalid operator'
        composed_filter_dict['report_params'] = {key : f" {operator_string_equivalent} {data['value'].strip()}" }

    return composed_filter_dict

def map_results(record):
    item = {}
    item['Username'] = record.get('pk', {}).get('S','')
    item['sk'] = record.get('sk',{}).get('S','')
    item['Full_Name'] = record.get('Full_Name',{}).get('S','')
    item['Nickname'] = record.get('Nickname',{}).get('S','')
    item['Role'] = record.get('Role',{}).get('S','')
    return item

# def generate_reports(mapped_results = [], display_fields=[], report_params = {}): 
#     diff_list = []
#     master_fields = ['Username', 'Full Name', 'Nickname', 'Role', ]
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

def create_listview_index_value(data):
    ListView_index_values = []
    for field in sort_fields:
        if field == pk_field:
            ListView_index_values.append(data['pk'])
        else:
            ListView_index_values.append(data.get(field))
    STARK_ListView_sk = "|".join(ListView_index_values)
    return STARK_ListView_sk

def assign_role_permissions(data):
    print("Line 643")

    username_from_data  = data['Username']
    role_name = data['Role']
 
    from os import getcwd 
    STARK_folder = getcwd() + '/STARK_User_Roles'
    sys.path = [STARK_folder] + sys.path
    import STARK_User_Roles as user_roles

    response = user_roles.get_by_pk(role_name)
    print("Line 652")
    print(response)
    permissions = response["item"]['Permissions']
    
    sys.path[0] = getcwd() + '/STARK_User_Permissions'
    import STARK_User_Permissions as user_permissions
    data = {
        'pk': username_from_data,
        'Permissions': permissions,
        'username': username
    }
    print(data)
    response = user_permissions.add(data)

    return "OK"

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

def cascade_pk_change_to_child(params, child_entity_name, attribute):
    temp_import = importlib.import_module(child_entity_name)

    #fetch all records from child using old pk value
    response = temp_import.get_all_by_old_parent_value(params['orig_pk'], attribute)

    #loop through response and update each record
    for record in response:
        record[attribute] = params['pk']
        temp_import.edit(record)

    return "OK"