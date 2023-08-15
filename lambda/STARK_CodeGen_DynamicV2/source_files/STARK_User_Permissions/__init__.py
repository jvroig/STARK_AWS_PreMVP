#Python Standard Library
import base64
import json
import importlib
from urllib.parse import unquote
import sys

#Extra modules
import azure.functions as func
import uuid
import copy
import logging

#STARK
import stark_core
from stark_core import utilities
from stark_core import validation
from stark_core import data_abstraction

#######
#CONFIG
mdb_collection    = stark_core.mdb_database["STARK_User_Permissions"]
file_storage      = stark_core.file_storage
region_name       = stark_core.region_name
page_limit        = stark_core.page_limit
file_storage_url  = stark_core.file_storage_url
file_storage_tmp  = stark_core.file_storage_tmp
pk_field          = "Username"
default_sk        = "STARK|user|permissions"
sort_fields       = ["Username", ]
relationships     = []
entity_upload_dir = stark_core.upload_dir + "STARK_User_Permissions/"
metadata          = {
    'Username': {
        'value': '',
        'required': True,
        'max_length': '',
        'data_type': 'String',
        'state': None,
        'feedback': ''
    },
    'Permissions': {
        'value': '',
        'required': False,
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
    'view': 'User Permissions|View',
    'add': 'User Permissions|Add',
    'delete': 'User Permissions|Delete',
    'edit': 'User Permissions|Edit',
    'report': 'User Permissions|Report'
}

def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    responseStatusCode = 200
    #Get request type
    request_type = req.params.get("rt", "")

    global username
    username = req.headers.get('x-STARK-Username', '')

    if request_type == '':
        ########################
        #Handle non-GET requests

        #Get specific request method
        method = req.method
        payload = json.loads(req.get_body().decode()).get('STARK_User_Permissions',"")

        data    = {}

        if payload == "":
            return func.HttpResponse(
                "Client payload missing",
                status_code = 400,
                headers = {
                    "Content-Type": "application/json",
                }
            )
        else:
            isInvalidPayload = False
            data['pk'] = payload.get('Username')
            data['Permissions'] = payload.get('Permissions','')
            if payload.get('STARK_isReport', False) == False:
                data['orig_pk'] = payload.get('orig_Username','')
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
                return func.HttpResponse(
                    "Missing operators",
                    status_code = 400,
                    headers = {
                        "Content-Type": "application/json",
                    }
                )


        if method == "DELETE":
            if(stark_core.sec.az_is_authorized(stark_permissions['delete'], req)):
                response = delete_v2(data)
            else:
                responseStatusCode, response = stark_core.sec.authFailResponse

        elif method == "PUT":
            if(stark_core.sec.az_is_authorized(stark_permissions['edit'], req)):
                payload = data
                payload['Username'] = data['pk']
                invalid_payload = validation.validate_form(payload, metadata)
                if len(invalid_payload) > 0:
                        return func.HttpResponse(
                            json.dumps(invalid_payload),
                            status_code = 400,
                            headers = {
                                "Content-Type": "application/json",
                            }
                        )
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
                if(stark_core.sec.az_is_authorized(stark_permissions['report'], req)):
                    response = report(data, default_sk)
                else:
                    responseStatusCode, response = stark_core.sec.authFailResponse
            else:
                if(stark_core.sec.az_is_authorized(stark_permissions['add'], req)):
                    payload = data
                    payload['Username'] = data['pk']
                    invalid_payload = validation.validate_form(payload, metadata)
                    if len(invalid_payload) > 0:
                        return func.HttpResponse(
                            json.dumps(invalid_payload),
                            status_code = responseStatusCode,
                            headers = {
                                "Content-Type": "application/json",
                            }
                        )
                    else:
                        response = add(data)
                else:
                        responseStatusCode, response = stark_core.sec.authFailResponse

        else:
            return func.HttpResponse(
                "Could not handle API request",
                status_code = 400,
                headers = {
                    "Content-Type": "application/json",
                }
            )

    else:
        ####################
        #Handle GET requests
        if request_type == "all":
            #check for submitted token
            lv_token = req.params.get('nt', None)
            if lv_token != None:
                lv_token = unquote(lv_token)
                lv_token = json.loads(lv_token)

            items, next_token = get_all(default_sk, lv_token)

            response = {
                'Next_Token': json.dumps(next_token),
                'Items': items
            }

        elif request_type == "detail":

            pk = req.params.get('Username','')
            sk = req.params.get('sk','')
            if sk == "":
                sk = default_sk

            response = get_by_pk(pk, sk)
        else:
            return func.HttpResponse(
                "Could not handle GET request - unknown request type",
                status_code = 400,
                headers = {
                    "Content-Type": "application/json",
                }
            )

    return func.HttpResponse(
            json.dumps(response),
            status_code = responseStatusCode,
            headers = {
                "Content-Type": "application/json",
            }
        )

def get_all(sk=default_sk, lv_token=None):

    ojbect_expression_values = {
        'STARK-Is-Deleted' : {'$exists': False},
    }
    items = []
    next_token = ""
    documents = list(mdb_collection.find(ojbect_expression_values))
    for record in documents:
        record[pk_field] = record["_id"]
        items.append(record)


    return items, next_token

def get_by_pk(pk, sk=default_sk, db_handler = None):
    ojbect_expression_values = {
        "_id": pk,
        'STARK-Is-Deleted' : {'$exists': False} 
    }
    documents = list(mdb_collection.find(ojbect_expression_values))
    for record in documents:
        record[pk_field] = record["_id"]

    response =  {"item": record}

    return response

def delete_v2(data, db_handler = None):

    pk = data.get('pk','')
    set_values = {
        "$set": utilities.az_append_record_metadata('delete', username)
    }

    ojbect_expression_values = { 
        "_id": pk,
        'STARK-Is-Deleted' : {'$exists': False} 
    }

    mdb_collection.update_one(ojbect_expression_values, set_values)
    return "OK"

def delete(data, db_handler = None):
    pk = data.get('pk','')
    identifier_query = { "_id": pk }
    response = mdb_collection.delete_one(identifier_query)

    global resp_obj
    resp_obj = response

    return "OK"

def edit(data, db_handler = None):           
    pk = data.get('pk', '')
    sk = data.get('sk', '')
    if sk == '': sk = default_sk
    Permissions = str(data.get('Permissions', ''))

    temp_values = {
                'Permissions': Permissions, 
    }
    update_values = {
        '$set' : temp_values | utilities.az_append_record_metadata('edit', username)
    }

    object_expression_values = { "_id": pk }
    response = mdb_collection.update_one(object_expression_values, update_values)


    global resp_obj
    resp_obj = response

    return "OK"

def add(data, method='POST', db_handler=None):
    pk = data.get('pk', '')
    sk = data.get('sk', '')
    if sk == '': sk = default_sk
    Permissions = str(data.get('Permissions', ''))

    item = utilities.az_append_record_metadata('add', username)
    item['_id'] =  pk
    item['sk'] =  sk
    item['Permissions'] =  Permissions
    response = mdb_collection.insert_one(item)

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
    # ddb_arguments['TableName'] = ddb_table
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
        response = {}
        # response = ddb.query(**ddb_arguments)
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
        
    csv_bucket_key = file_storage_tmp + csv_file
    pdf_bucket_key = file_storage_tmp + pdf_file

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

def map_results(record):
    item = {}
    item['Username'] = record.get('pk', {}).get('S','')
    item['sk'] = record.get('sk',{}).get('S','')
    item['Permissions'] = record.get('Permissions',{}).get('S','')
    return item
