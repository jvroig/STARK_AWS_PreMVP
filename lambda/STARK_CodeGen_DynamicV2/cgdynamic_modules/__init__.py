#STARK Code Generator component.
#Produces the customized dynamic content for a STARK system

#Python Standard Library
import base64
import textwrap

#Private modules
import convert_friendly_to_system as converter

def create(data):
    print('data')
    print(data)
    pk             = data["PK"]
    entity         = data["Entity"]
    sequence       = data["Sequence"]
    columns        = data["Columns"]
    ddb_table_name = data["DynamoDB Name"]
    bucket_name    = data['Bucket Name']
    relationships  = data["Relationships"]
    rel_model      = data["Rel Model"]
    print('sequence')
    print(sequence)
    #Convert human-friendly names to variable-friendly names
    entity_varname = converter.convert_to_system_name(entity)
    pk_varname     = converter.convert_to_system_name(pk)

    default_sk     = entity_varname + "|info"
    
    with_upload         = False
    with_upload_on_many = False
 
    #Create the column dict we'll use in the code as a declaration
    col_dict = '{ "pk": pk, "sk": sk, '
    for col in columns:
        col_varname = converter.convert_to_system_name(col)
        col_dict += f'"{col_varname}": {col_varname}, '
    col_dict = col_dict[:-2]
    col_dict += ' }'

    #Create the dict value retrieval code for the add/edit function body
    
    dict_to_var_code = f"""pk = data.get('pk', '')
        sk = data.get('sk', '')    
        if sk == '': sk = default_sk"""

    

    #Check for file upload in child if 1-M is available
    for rel in rel_model:
        rel_cols = rel_model[rel]["data"]
        for rel_col, rel_col_type in rel_cols.items():
            if isinstance(rel_col_type, dict):
                if rel_col_type["type"] == 'file-upload': 
                    with_upload_on_many = True

    for col, col_type in columns.items():
        col_varname = converter.convert_to_system_name(col)
        
        #check for file upload
        if isinstance(col_type, dict) and col_type['type'] == 'file-upload':
            with_upload = True
        
        col_type_id = set_type(col_type)

        if col_type_id in ['S', 'N']: 
            dict_to_var_code += f"""
        {col_varname} = str(data.get('{col_varname}', ''))"""

        else:
            dict_to_var_code += f"""
        {col_varname} = data.get('{col_varname}', '')"""
    
    # if relationships.get('has_many', '') != '':
    #     for relation in relationships.get('has_many'):
    #         if relation.get('type') != 'repeater':
    #             entity = relation.get('entity')
    #             print(entity)
    repeater_fields = remove_repeater_col(relationships, columns)

    #This is for our DDB update call
    update_expression = ""
    for col in columns:
        if col in repeater_fields:
            pass
        else:
            col_varname = converter.convert_to_system_name(col)
            update_expression += f"""
                    '{col_varname}': {col_varname}, """
    # update_expression += " #STARKListViewsk = :STARKListViewsk, #STARKUpdatedBy = :STARKUpdatedBy, #STARKUpdatedTs = :STARKUpdatedTS"
    if with_upload or with_upload_on_many:
        update_expression += ", 'STARK_uploaded_s3_keys': STARK_uploaded_s3_keys"

    source_code = f"""\
    #Python Standard Library
    import base64
    import json
    import importlib
    from urllib.parse import unquote

    #Extra modules
    from pymongo import MongoClient
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
    mdb_collection    = stark_core.mdb_database["{entity_varname}"]
    file_storage      = stark_core.file_storage
    region_name       = stark_core.region_name
    page_limit        = stark_core.page_limit
    file_storage_url  = stark_core.file_storage_url
    file_storage_tmp  = stark_core.file_storage_tmp
    pk_field          = "{pk_varname}"
    default_sk        = "{default_sk}"
    sort_fields       = ["{pk_varname}", ]
    relationships     = {relationships}
    entity_upload_dir = stark_core.upload_dir + "{entity_varname}/"
    entity_name       = "{entity}"
    metadata          = {{
                "{pk_varname}": {{
                    'value': '',
                    'key': 'pk',"""

    if len(sequence) > 0:
        required = False
    else:
        required = True
        
    source_code += f"""
                    'required': {required},"""
                    
    source_code += f"""                
                    'max_length': '',
                    'data_type': 'string',
                    'state': None,
                    'feedback': '',
                    'relationship': ''
                }},"""
    
        
    
    for col, col_type in columns.items():
        col_varname = converter.convert_to_system_name(col)
        data_type = set_data_type(col_type)
        rel = ''
        if isinstance(col_type, dict) and col_type["type"] == "relationship":
            has_many_ux = col_type.get('has_many_ux', None)
            if has_many_ux == 'repeater': 
                rel = '1-M'
                
        source_code += f"""
                '{col_varname}': {{
                    'value': '',
                    'key': '',
                    'required': True,
                    'max_length': '',
                    'data_type': '{data_type}',
                    'state': None,
                    'feedback': '',
                    'relationship': '{rel}'
                }},""" 

    source_code += f"""
    }}
    resp_obj = None
    username = ""

    ############
    #PERMISSIONS
    stark_permissions = {{
        'view': '{entity}|View',
        'add': '{entity}|Add',
        'delete': '{entity}|Delete',
        'edit': '{entity}|Edit',
        'report': '{entity}|Report'
    }}

    def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
        responseStatusCode = 200

        #Get request type
        request_type = req.params.get("rt", "")

        global username
        username = req.headers.get('x-STARK-Username', username)
        if request_type == '':
            ########################
            #Handle non-GET requests
    
            #Get specific request method
            method = req.method
            payload = json.loads(req.get_body().decode()).get('{entity_varname}', "")

            data    = {{}}

            if payload == "":
                return func.HttpResponse(
                    "Client payload missing",
                    status_code = 400,
                    headers = {{
                        "Content-Type": "application/json",
                    }}
                )
            else:
                isInvalidPayload = False
                data['pk'] = payload.get('{pk_varname}')"""
    for col, col_type in columns.items():
        col_varname = converter.convert_to_system_name(col)
        source_code +=f"""
                data['{col_varname}'] = payload.get('{col_varname}','')"""
    
    

    source_code +=f"""

                if payload.get('STARK_isReport', False) == False:"""
                
                #FIXME: should be refactored to use metadata of child entities
    if relationships.get('has_many', '') != '':
        for relation in relationships.get('has_many'):
            if relation.get('type') == 'repeater':
                entity = converter.convert_to_system_name(relation.get('entity'))
                source_code +=f"""
                    data['{entity}'] = payload.get('{entity}','')"""
    
    for rel_ent in rel_model:
        rel_cols = rel_model[rel_ent]["data"]
        rel_pk = rel_model[rel_ent]["pk"]
        var_pk = rel_ent.replace(' ', '_') + '_' + rel_pk.replace(' ', '_')
        source_code +=f"""
                    data['{var_pk}'] = payload.get('{var_pk}','')"""
        for rel_col, rel_col_type in rel_cols.items():
            var_data = rel_ent.replace(' ', '_') + '_' + rel_col.replace(' ', '_')
            source_code +=f"""
                    data['{var_data}'] = payload.get('{var_data}','')"""

    source_code +=f"""
                    data['orig_pk'] = payload.get('orig_{pk_varname}','')
                    data['sk'] = payload.get('sk', '')
                    if data['sk'] == "":
                        data['sk'] = default_sk
                    #FIXME: THIS IS A STUB, MIGHT BE USED IN REPORTING
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
                    data['STARK_group_by_1'] = payload.get('STARK_group_by_1', '')"""
    
    for rel_ent in rel_model:
        rel_ent_varname = converter.convert_to_system_name(rel_ent)
        rel_cols = rel_model[rel_ent]["data"]
        rel_pk = rel_model[rel_ent]["pk"]
        rel_pk_varname = converter.convert_to_system_name(rel_pk)
        var_pk = rel_ent + '_' + rel_pk
        var_pk_varname = converter.convert_to_system_name(var_pk)
        source_code +=f"""
                    temp_{rel_ent_varname} = {{
                        '{rel_pk_varname}': payload.get('{var_pk_varname}',''),"""
        for rel_col, rel_col_type in rel_cols.items():
            var_data = rel_ent + '_' + rel_col
            rel_col_varname = converter.convert_to_system_name(rel_col)
            data_varname = converter.convert_to_system_name(var_data)
            source_code +=f"""
                        '{rel_col_varname}': payload.get('{data_varname}',''),"""
        source_code += f"""
                    }}
                    data['{rel_ent_varname}'] = temp_{rel_ent_varname}
                    
                    """
    source_code +=f"""

                data['STARK_uploaded_s3_keys'] = payload.get('STARK_uploaded_s3_keys',{{}})
                data['orig_STARK_uploaded_s3_keys'] = payload.get('orig_STARK_uploaded_s3_keys',{{}})

                if isInvalidPayload:
                    return func.HttpResponse(
                        "Missing operators",
                        status_code = 400,
                        headers = {{
                            "Content-Type": "application/json",
                        }}
                    )

            if method == "DELETE":
                if(stark_core.sec.az_is_authorized(stark_permissions['delete'], req)):
                    response = delete_v2(data)
                else:
                    responseStatusCode, response = stark_core.sec.authFailResponse

            elif method == "PUT":
                if(stark_core.sec.az_is_authorized(stark_permissions['edit'], req)):
                    payload = data
                    payload[pk_field] = data['pk']
                    invalid_payload = validation.validate_form(payload, metadata)
                    if len(invalid_payload) > 0:
                        return func.HttpResponse(
                            json.dumps(invalid_payload),
                            status_code = 400,
                            headers = {{
                                "Content-Type": "application/json",
                            }}
                        )
                        
                    else:
                        if data['orig_pk'] == data['pk']:
                            response = edit(data)
                        else:
                            #We can't update DDB PK, so if PK is different, we need to do ADD + DELETE
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
                        payload[pk_field] = data['pk']
                        invalid_payload = validation.validate_form(payload, metadata)
                        if len(invalid_payload) > 0:
                            return func.HttpResponse(
                                json.dumps(invalid_payload),
                                status_code = responseStatusCode,
                                headers = {{
                                    "Content-Type": "application/json",
                                }}
                            )
                            
                        else:
                            response = add(data)
                    else:
                        responseStatusCode, response = stark_core.sec.authFailResponse

            else:
                return func.HttpResponse(
                    "Could not handle API request",
                    status_code = 400,
                    headers = {{
                        "Content-Type": "application/json",
                    }}
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

                response = {{
                    'Next_Token': json.dumps(next_token),
                    'Items': items
                }}
            
            elif request_type == "get_fields":
                fields = req.params.get('fields','')
                fields = fields.split(",")
                response = data_abstraction.az_get_fields(fields, pk_field, mdb_collection)

            elif request_type == "detail":

                pk = req.params.get('{pk_varname}','')
                sk = req.params.get('sk','')
                if sk == "":
                    sk = default_sk

                response = get_by_pk(pk, sk)
            else:
                return func.HttpResponse(
                    "Could not handle GET request - unknown request type",
                    status_code = 400,
                    headers = {{
                        "Content-Type": "application/json",
                    }}
                )

        return func.HttpResponse(
                json.dumps(response),
                status_code = responseStatusCode,
                headers = {{
                    "Content-Type": "application/json",
                }}
            )

    def report(data, sk=default_sk):
        #FIXME: THIS IS A STUB, WILL NEED TO BE UPDATED WITH
        #   ENHANCED LISTVIEW LOGIC LATER WHEN WE ACTUALLY IMPLEMENT REPORTING
        object_expression_values = [{{
                'STARK-Is-Deleted' : {{'$exists': False}}
            }}]
        report_param_dict = {{}}
        for key, index in data.items():
            #FIXME: : 1-M SEARCH CRITERIA: do not include fields with 1-M relationship in composing of operators and parameters for now
            # Fetch all records for now then do necessary logic thru python for each operator in 1-M fields
            if "STARK_" not in key and metadata.get(key,{{}}).get('relationship','') != "1-M":
                if index['value'] != "":
                    processed_operator_and_parameter_dict = utilities.az_compose_report_operators_and_parameters(key, index, metadata) 
                    object_expression_values.extend(processed_operator_and_parameter_dict['operators'])
                    report_param_dict.update(processed_operator_and_parameter_dict['report_params'])


        #FIXME: 1-M SEARCH CRITERIA: filter result of 1-M report operators here
        composed_operator_for_one_to_many = {{}}

        for key, attribute in metadata.items():
            if attribute['relationship'] == '1-M':
                temp_import = importlib.import_module(key)
                for many_key, many_attribute in data[key].items():
                    if many_attribute['value'] != "":
                        temp_dict = {{
                            f"{{key}}_{{many_key}}" : {{
                                "operator": many_attribute.get("operator"), 
                                "value": many_attribute.get('value'),
                                "data_type": temp_import.metadata[many_key]['data_type']
                                }}
                            }}
                        composed_operator_for_one_to_many.update(temp_dict)

        items = []
        ddb_arguments = {{}}
        aggregated_results = {{}}

        if len(object_expression_values) > 1:
            final_query = {{ "$and": object_expression_values }}
        else:
            final_query = object_expression_values[0]

        documents = list(mdb_collection.find(final_query))
        
        aggregate_report = False if data['STARK_group_by_1'] == '' else True
        # Checker if report has many in report fields
        has_many = False
        many_sk = []
        many_entity = []
        for rel in relationships.get('has_many', ''):
            for report_fields in data['STARK_report_fields']:
                if rel.get('entity').replace('_', ' ') in report_fields:
                    has_many = True 
                    # Get 1-M entity
                    # Make List of 1-M entity
                    rel_entity = rel.get('entity')
                    many_entity.append(rel_entity.replace('_', ' ')) 
                    
        many_entity_dict = {{}}
        for ent in many_entity:
            ent_filter = ent
            many_val = []
            for report_fields in data['STARK_report_fields']:
                if ent in report_fields:
                    many_val.append(report_fields.replace(ent_filter, '').replace(' ', '_').replace("_", "", 1))
            many_entity_dict.update({{ent.replace(' ', '_') : many_val}})

        for record in documents:
            item = []
            record[pk_field] = record['_id']
            item.append(record)

            new_item = []
            for each_item in item:
                if(has_many):
                    # Get transaction number per report result
                    many_pk = each_item.get(pk_field)
                    for many_rel_entity, many_rel_field in many_entity_dict.items():
                        many_sk = '{entity_varname}|' + many_rel_entity
                        
                        many_result = data_abstraction.get_many_by_pk(many_pk, many_sk)
                        response = None
                        response = json.loads(many_result[0].get(many_sk, '').get('S'))
                        temp_list = []
                        for res in response:  
                            temp_item = {{}}
                            is_included = True
                            for item_key, item_val in each_item.items():
                                temp_item.update({{item_key: item_val}})
                            consolidated_items = {{}}
                            for rel_field in many_rel_field:
                                rel_entity = many_rel_entity.replace(' ', '_')
                                many_field = rel_field.replace(' ', '_')
                                new_rel_field = rel_entity + '_' + many_field

                                temp_item.update({{new_rel_field : res[rel_field]}})
                                
                            no_val_items = {{}}
                            for dict in data['STARK_report_fields']:
                                if dict.replace(' ', '_') not in temp_item:
                                    no_val_items.update({{dict.replace(' ', '_') : ''}})       
                            consolidated_items = temp_item | no_val_items
                        
                            if len(composed_operator_for_one_to_many) > 0:
                                is_included = False

                            for field_name, field_criteria in composed_operator_for_one_to_many.items():
                                is_included = utilities.filter_criteria_for_many_fields(consolidated_items[field_name], field_criteria)
                                if is_included == False:
                                    break
                            
                            if is_included:
                                new_item.append(consolidated_items)
                else:
                    new_item = item

            for each_item in new_item:

                if aggregate_report:
                    aggregate_key = data['STARK_group_by_1'].replace(" ","_")
                    aggregate_key_value = each_item.get(aggregate_key)
                    if aggregate_key_value in aggregated_results:
                        for field in data['STARK_count_fields']:
                            field_name = field.replace(" ","_")
                            count_index_name = f"Count of {{field_name}}"
                            aggregated_results[aggregate_key_value][count_index_name] += 1

                        for field in data['STARK_sum_fields']:
                            field_name = field.replace(" ","_")
                            sum_index_name = f"Sum of {{field_name}}"
                            if each_item.get(field) != '':
                                sum_value = float(each_item.get(field))
                            else:
                                sum_value = 0.00
                            aggregated_results[aggregate_key_value][sum_index_name] = round(aggregated_results[aggregate_key_value][sum_index_name], 1) + sum_value

                        for column in data['STARK_report_fields']:
                            if column != aggregate_key:  
                                aggregated_results[aggregate_key_value][column.replace(" ","_")] = each_item.get(column.replace(" ","_"))

                    else:
                        temp_dict = {{ aggregate_key : aggregate_key_value}}
                        for field in data['STARK_count_fields']:
                            field_name = field.replace(" ","_")
                            count_index_name = f"Count of {{field_name}}"
                            temp_dict.update({{
                                count_index_name:  1
                            }})

                        for field in data['STARK_sum_fields']:
                            field_name = field.replace(" ","_")
                            sum_index_name = f"Sum of {{field_name}}"
                            if each_item.get(field) != None:
                                sum_value = float(each_item.get(field))
                            else:
                                sum_value = 0.00
                            temp_dict.update({{
                                sum_index_name: sum_value
                            }})

                        for column in data['STARK_report_fields']:
                            if column != aggregate_key:  
                                temp_dict.update({{
                                    column.replace(" ","_"): each_item.get(column.replace(" ","_"))
                                }})

                        aggregated_results[aggregate_key_value] = temp_dict
                else:
                    items.append(each_item)


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
                temp_dict = {{}}
                #remove primary identifiers and STARK attributes
                if not aggregate_report:
                    key.pop("_id")"""
    if with_upload or with_upload_on_many:
        source_code += f"""
                    key.pop("STARK_uploaded_s3_keys")"""
    source_code += f"""
                for index, value in key.items():
                    temp_dict[index.replace("_"," ")] = value
                report_list.append(temp_dict)

            for dict in diff_list:      
                for report in report_list:
                    if dict not in report:
                        report.update({{dict : ''}})

            report_list = utilities.filter_report_list(report_list, diff_list)
            # csv_file, file_buff_value = utilities.create_csv(report_list, report_header)
            # utilities.save_object_to_bucket(file_buff_value, csv_file)"""
            
    if len(rel_model) > 0:
                source_code += f"""
            merge_metadata = {{}}
            for relation in relationships.get('has_many', []):
                if relation.get('type', '') == 'repeater':
                    temp_import = importlib.import_module(relation.get('entity', ''))
                    child_metadata = temp_import.metadata
                    new_child_metadata = {{}}
                    for child_entity, child_data in child_metadata.items():
                        new_child_ent = relation['entity'] + '_' + child_entity
                        new_child_metadata.update({{new_child_ent: child_data}})
                    merge_metadata.update(new_child_metadata)
            metadata.update(merge_metadata)"""

    source_code += f"""
            # pdf_file, pdf_output = utilities.prepare_pdf_data(report_list, report_header, report_param_dict, metadata, pk_field)
            # utilities.save_object_to_bucket(pdf_output, pdf_file)

        # csv_file_storage_key = file_storage_tmp + csv_file
        # pdf_file_storage_key = file_storage_tmp + pdf_file
        
        csv_file_storage_key = ""
        pdf_file_storage_key = ""
        
        if not aggregate_report:
            report_list = items
            new_report_list = []
            for row in report_list:
                temp_dict = {{}}
                for index, value in row.items():
                    temp_dict[index.replace("_"," ")] = value
                new_report_list.append(temp_dict)
            report_list = new_report_list

        return report_list, csv_file_storage_key, pdf_file_storage_key

    def get_all(sk=default_sk, lv_token=None, db_handler = None):

        ojbect_expression_values = {{
            'STARK-Is-Deleted' : {{'$exists': False}},
        }}
        items = []
        next_token = ""
        documents = list(mdb_collection.find(ojbect_expression_values))
        for record in documents:
            record[pk_field] = record["_id"]
            items.append(record)

        return items, next_token

    def get_by_pk(pk, sk=default_sk, db_handler = None):
        ojbect_expression_values = {{
            "_id": pk,
            'STARK-Is-Deleted' : {{'$exists': False}} 
        }}
        documents = list(mdb_collection.find(ojbect_expression_values))
        for record in documents:
            record[pk_field] = record["_id"]
            
        response =  {{"item": record}}"""
    
    if len(rel_model) > 0:
        source_code+= f"""
        many_rel = relationships['has_many']
        for rel in many_rel:
            entity = rel['entity']
            temp_import = importlib.import_module(entity)
            collection = stark_core.mdb_database[entity]
            many_result = data_abstraction.get_many_by_foreign_key(pk, pk_field, collection, temp_import.pk_field)
            response[entity] = json.dumps(many_result)
        """

    if with_upload or with_upload_on_many: 
        source_code +=f"""
        response['object_url_prefix'] = file_storage_url + entity_upload_dir"""
    source_code+= f"""

        return response"""

    source_code+= f"""
    def delete_v2(data, db_handler = None):

        pk = data.get('pk','')
        set_values = {{
            "$set": utilities.az_append_record_metadata('delete', username)
        }}

        ojbect_expression_values = {{ 
            "_id": pk,
            'STARK-Is-Deleted' : {{'$exists': False}} 
        }}

        mdb_collection.update_one(ojbect_expression_values, set_values)
        return "OK"

    def delete(data, db_handler = None):
        pk = data.get('pk','')
        identifier_query = {{ "_id": pk }}
        response = mdb_collection.delete_one(identifier_query)

        global resp_obj
        resp_obj = response
        """

    if len(rel_model) > 0:
            source_code+= f"""
        many_rel = relationships['has_many']
        for rel in many_rel:
            entity = rel['entity']
            sk = '{entity_varname}|' + entity
            # delete_many(pk, sk)"""

    source_code+= f"""
        return "OK"
    """
    if len(rel_model) > 0:
        source_code+= f"""
    def delete_many(pk, sk, db_handler = None):
        if db_handler == None:
            db_handler = ddb

        ddb_arguments = {{}}
        ddb_arguments['TableName'] = ddb_table
        ddb_arguments['Key'] = {{
                'pk' : {{'S' : pk}},
                'sk' : {{'S' : sk}}
            }}
        print(ddb_arguments)
        response = db_handler.delete_item(**ddb_arguments)
        global resp_obj
        resp_obj = response
        """

    source_code+= f"""
    def edit(data, db_handler = None):  
        {dict_to_var_code}"""

    if with_upload or with_upload_on_many:
        source_code += f"""
        #FIXME: Simplify comparison using metadata after metadata separation in child entities
        temp_s3_keys = data.get('STARK_uploaded_s3_keys', {{}}) 
        orig_s3_keys = data.get('orig_STARK_uploaded_s3_keys', {{}}) 
        updated_s3_keys = compareDict(orig_s3_keys, temp_s3_keys)

        for updated_key, updated_items in updated_s3_keys.items():
            if isinstance(updated_items, dict):
                for updated_sub_key, updated_sub_items in updated_items.items():
                    for updated_s3_key in updated_sub_items:
                        utilities.copy_object_to_bucket(updated_s3_key, entity_upload_dir)
            else:
                utilities.copy_object_to_bucket(updated_items, entity_upload_dir)

        STARK_uploaded_s3_keys = {{}}
        for key, items in temp_s3_keys.items():
            upload_data = {{}}
            if isinstance(items, dict):
                upload_dict_data = {{}}
                for sub_key, sub_items in items.items():
                    upload_dict_data[sub_key] = {{'S':'||'.join(sub_items)}}
                upload_data = {{'M': upload_dict_data}}
            else:  
                upload_data = {{'S': items}}
            STARK_uploaded_s3_keys[key] = upload_data
        """
    source_code += f"""
        temp_values = {{
            {update_expression}
        }}"""
            
    source_code += f"""
        update_values = {{
            '$set' : temp_values | utilities.az_append_record_metadata('edit', username)
        }}

        object_expression_values = {{ "_id": pk }}
        response = mdb_collection.update_one(object_expression_values, update_values)
        """

    # if len(rel_model) > 0:
    #     source_code+= f"""
    #     many_rel = relationships['has_many']
    #     for rel in many_rel:
    #         entity = rel['entity']
    #         sk = '{entity_varname}|' + entity
    #         many_data = data.get(entity, '')
    #         edit_many(pk, sk, many_data)"""

    if len(relationships) > 0:
        source_code += f"""
        for relation in relationships.get('has_one', []):
            cascade_pk_change_to_child(data, relation['entity'], relation['attribute'])
        """
    source_code += f"""
        many_rel = relationships['has_many']
        for rel in many_rel:
            entity = rel['entity']
            temp_import = importlib.import_module(entity)
            many_data = json.loads(data.get(entity, ''))
            for data in many_data:
                item = {{
                    pk_field : pk
                }}
                for key, attribute in data.items():
                    if key == temp_import.pk_field:
                        item['pk'] = attribute
                    else:
                        item[key] = attribute
                        
                temp_import.username = username
                temp_import.edit(item)

        for relation in relationships.get('belongs_to', []):
            logging.info(relation)
            if relation['rel_type'] == 'has_many':
                foreign_key = relation['pk_field']
                temp_values[foreign_key] = data[foreign_key]

        global resp_obj
        resp_obj = response
        return "OK"
        """

    # if len(rel_model) > 0:
    #         source_code+= f"""
    # def edit_many(pk, sk, data, db_handler = None):
    #     if db_handler == None:
    #         db_handler = ddb  
        
    #     UpdateExpressionString = "SET #field = :data"
    #     ExpressionAttributeNamesDict = {{
    #         # '#' + sk : sk
    #         '#field' : sk
    #     }}
    #     ExpressionAttributeValuesDict = {{
    #         ':data' : {{'S' : data }}
    #     }}
        
    #     ddb_arguments = {{}}
    #     ddb_arguments['TableName'] = ddb_table
    #     ddb_arguments['Key'] = {{
    #             'pk' : {{'S' : pk}},
    #             'sk' : {{'S' : sk}}
    #         }}
    #     ddb_arguments['ReturnValues'] = 'UPDATED_NEW'
    #     ddb_arguments['UpdateExpression'] = UpdateExpressionString
    #     ddb_arguments['ExpressionAttributeNames'] = ExpressionAttributeNamesDict
    #     ddb_arguments['ExpressionAttributeValues'] = ExpressionAttributeValuesDict

    #     response = db_handler.update_item(**ddb_arguments)"""
            
    source_code+= f"""
    def add(data, method='POST', db_handler=None):
    """

    if len(sequence) > 0:
        dict_to_var_code_add = f"""pk = data_abstraction.get_sequence(entity_name)
        sk = data.get('sk', '')    
        if sk == '': sk = default_sk"""
    else:
        dict_to_var_code_add = f"""pk = data.get('pk', '')
        sk = data.get('sk', '')    
        if sk == '': sk = default_sk"""
    
    #Check for file upload in child if 1-M is available
    for rel in rel_model:
        rel_cols = rel_model[rel]["data"]
        for rel_col, rel_col_type in rel_cols.items():
            if isinstance(rel_col_type, dict):
                if rel_col_type["type"] == 'file-upload': 
                    with_upload_on_many = True

    for col, col_type in columns.items():
        col_varname = converter.convert_to_system_name(col)
        
        #check for file upload
        if isinstance(col_type, dict) and col_type['type'] == 'file-upload':
            with_upload = True
        
        col_type_id = set_type(col_type)

        if col_type_id in ['S', 'N']: 
            dict_to_var_code_add += f"""
        {col_varname} = str(data.get('{col_varname}', ''))"""

        else:
            dict_to_var_code_add += f"""
        {col_varname} = data.get('{col_varname}', '')"""

    source_code+= f"""
        {dict_to_var_code_add}"""


    if with_upload or with_upload_on_many:
        source_code += f"""
        temp_s3_keys = data.get('STARK_uploaded_s3_keys', {{}}) 
        orig_s3_keys = data.get('orig_STARK_uploaded_s3_keys', {{}})
        STARK_uploaded_s3_keys = {{}}
        for key, items in temp_s3_keys.items():
            upload_data = {{}}
            if isinstance(items, dict):
                upload_dict_data = {{}}
                for sub_key, sub_items in items.items():
                    upload_dict_data[sub_key] = {{'S':'||'.join(sub_items)}}
                    for s3_key in sub_items:
                        utilities.copy_object_to_bucket(s3_key, entity_upload_dir)
                upload_data = {{'M': upload_dict_data}}
            else:  
                utilities.copy_object_to_bucket(items, entity_upload_dir)
                upload_data = {{'S': items}}
            STARK_uploaded_s3_keys[key] = upload_data
        """
    source_code += f"""
        item = utilities.az_append_record_metadata('add', username)
        
        for relation in relationships.get('belongs_to', []):
            if relation['rel_type'] == 'has_many':
                foreign_key = relation['pk_field']
                item[foreign_key] = data[foreign_key]

        item['_id'] = pk"""

    for col, col_type in columns.items():
        col_varname = converter.convert_to_system_name(col)
        col_type_id = set_type(col_type)

        source_code +=f"""
        item['{col_varname}'] = {col_varname}"""

    # if with_upload or with_upload_on_many:
    #     source_code += f"""
    #     item['STARK_uploaded_s3_keys'] = {{'M' : STARK_uploaded_s3_keys}}"""

    source_code += f"""

        if data.get('STARK-ListView-sk','') == '':"""

    if len(sequence) > 0:
        source_code += f"""    
            data['pk'] = pk"""
    
    source_code += f"""    
            item['STARK-ListView-sk'] = {{'S' : create_listview_index_value(data)}}"""
        
    source_code += f"""
        else:
            item['STARK-ListView-sk'] = {{'S' : data['STARK-ListView-sk']}}

        response = mdb_collection.insert_one(item)
        """
    if len(relationships) > 0:
        source_code += f"""
        if method == 'POST':
            data['orig_pk'] = pk

        for relation in relationships.get('has_one', []):
            cascade_pk_change_to_child(data, relation['entity'], relation['attribute'])
        """

    if len(rel_model) > 0:
            source_code+= f"""
        many_rel = relationships['has_many']
        for rel in many_rel:
            entity = rel['entity']
            temp_import = importlib.import_module(entity)
            many_data = json.loads(data.get(entity, ''))
            for data in many_data:
                item = {{
                    pk_field : pk
                }}
                for key, attribute in data.items():
                    if key == temp_import.pk_field:
                        item['pk'] = attribute
                    else:
                        item[key] = attribute
                logging.info(item)
                temp_import.username = username
                temp_import.add(item)"""
    
    source_code += f"""
        global resp_obj
        resp_obj = response
        return "OK"
        """

    if len(rel_model) > 0:
            source_code+= f"""
    def add_many(pk, sk, data, db_handler=None):
        if db_handler == None:
            db_handler = ddb

        item={{}}
        item['pk'] = {{'S' : pk}}
        item['sk'] = {{'S' : sk}}
        item[sk] = {{'S' : data}}
        print(item)

        ddb_arguments = {{}}
        ddb_arguments['TableName'] = ddb_table
        ddb_arguments['Item'] = item
        response = db_handler.put_item(**ddb_arguments)

        global resp_obj
        resp_obj = response
        return "OK"
        """
            
    source_code+= f"""
    
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
        item = {{}}
        item['{pk_varname}'] = record.get('pk', {{}}).get('S','')
        item['sk'] = record.get('sk',{{}}).get('S','')"""
    for col, col_type in columns.items():
        col_varname = converter.convert_to_system_name(col)
        col_type_id = set_type(col_type)

        source_code +=f"""
        item['{col_varname}'] = record.get('{col_varname}',{{}}).get('{col_type_id}','')"""

    if with_upload or with_upload_on_many:
        source_code += f"""
        STARK_uploaded_s3_keys = {{}}

        for key, map_item in (record.get('STARK_uploaded_s3_keys',{{}}).get('M',{{}})).items():
            for sub_key, sub_map_item in map_item.items():
                if sub_key == 'S':
                    STARK_uploaded_s3_keys[key] = sub_map_item
                elif sub_key == 'M':
                    for third_key, third_item in sub_map_item.items():
                        list_s3_keys = list(third_item['S'].split('||'))
                        if key in STARK_uploaded_s3_keys:
                            STARK_uploaded_s3_keys[key].update({{third_key: list_s3_keys}}) 
                        else:
                            STARK_uploaded_s3_keys[key] = {{third_key: list_s3_keys}}

        item['STARK_uploaded_s3_keys'] = STARK_uploaded_s3_keys"""
    source_code += f"""
        return item

    def get_all_by_old_parent_value(old_pk_val, attribute, sk = default_sk):

    #     string_filter = " attribute_not_exists(#isDeleted) AND #Attribute = :old_parent_value"
    #     object_expression_value = {{':sk' : {{'S' : sk}},
    #                                 ':old_parent_value': {{'S' : old_pk_val}}}}
    #     ExpressionAttributeNamesDict = {{
    #         '#Attribute' : attribute,
    #         '#isDeleted' : 'STARK-Is-Deleted'
    #     }}

    #     ddb_arguments = {{}}
    #     # ddb_arguments['TableName'] = ddb_table
    #     ddb_arguments['IndexName'] = "STARK-ListView-Index"
    #     ddb_arguments['Select'] = "ALL_ATTRIBUTES"
    #     ddb_arguments['ReturnConsumedCapacity'] = 'TOTAL'
    #     ddb_arguments['FilterExpression'] = string_filter
    #     ddb_arguments['KeyConditionExpression'] = 'sk = :sk'
    #     ddb_arguments['ExpressionAttributeValues'] = object_expression_value
    #     ddb_arguments['ExpressionAttributeNames'] = ExpressionAttributeNamesDict

    #     next_token = 'initial'
        items = []
    #     while next_token != None:
    #         next_token = '' if next_token == 'initial' else next_token

    #         if next_token != '':
    #             ddb_arguments['ExclusiveStartKey']=next_token

    #         # response = ddb.query(**ddb_arguments)
    #         raw = response.get('Items')
    #         next_token = response.get('LastEvaluatedKey')
    #         for record in raw:
    #             item = map_results(record)
    #             #add pk as literal 'pk' value
    #             #and STARK-ListView-Sk
    #             item['pk'] = record.get('pk', {{}}).get('S','')
    #             item['STARK-ListView-sk'] = record.get('STARK-ListView-sk',{{}}).get('S','')
    #             items.append(item)
                
        return items
    """
    
    if len(relationships) > 0:
        source_code += f"""    
    def cascade_pk_change_to_child(params, child_entity_name, attribute):
        temp_import = importlib.import_module(child_entity_name)

        #fetch all records from child using old pk value
        response = temp_import.get_all_by_old_parent_value(params['orig_pk'], attribute)

        #loop through response and update each record
        for record in response:
            record[attribute] = params['pk']
            record['orig_pk'] = params['pk']
            temp_import.edit(record)

        return "OK"
    """
    if with_upload or with_upload_on_many:
        source_code += f"""        
    def compareDict(old_dict, new_dict):
        diff_orig = set(old_dict) - set(new_dict)
        diff_temp = set(new_dict) - set(old_dict)
        intersect_keys = set(old_dict.keys()).intersection(set(new_dict.keys()))
        modified = {{}}
        for i in intersect_keys:
            if old_dict[i] != new_dict[i]: 
                if isinstance(old_dict[i], dict) and isinstance(old_dict[i], dict):
                    modified[i]=compareDict(old_dict[i], new_dict[i])
                elif isinstance(old_dict[i], list) and isinstance(old_dict[i], list):
                    lst = []
                    
                    # diff_temp = set(new_dict) - set(old_dict)
                    # for a in old_dict[i]:
                    #     # diff_orig_set = set(old_dict[i]) - set(new_dict[i])
                    #     if a not in new_dict[i]:
                    #         lst.append(a)
                    #         modified.update({{i : lst}})

                    for b in new_dict[i]:
                        if b not in old_dict[i]:
                            lst.append(b)
                            modified.update({{i : lst}})
                else:
                    modified.update({{i : new_dict[i]}})

        for a in diff_orig:
            modified.update({{a : old_dict[a]}})

        for b in diff_temp:
            modified.update({{b : new_dict[b]}})
                
        return copy.deepcopy(modified)"""

    return textwrap.dedent(source_code)


def set_type(col_type):

    #Default is 'S'. Defined here so we don't need duplicate Else statements below
    col_type_id = 'S'

    if isinstance(col_type, dict):
        #special/complex types
        if col_type["type"] in [ "int-spinner", "decimal-spinner" ]:
            col_type_id = 'N'
        
        if col_type["type"] in [ "tags", "multiple choice" ]:
            col_type_id = 'SS'
    
    elif col_type in [ "int", "number" ]:
        col_type_id = 'N'

    return col_type_id

def remove_repeater_col(relationships, columns):
    repeater_fields = []
    if relationships.get('has_many', '') != '':
        for relation in relationships.get('has_many'):
            if relation.get('type') == 'repeater':
                new_entity = (relation.get('entity')).replace('_', ' ')
                repeater_fields.append(new_entity)

    return repeater_fields

def set_data_type(col_type):

    #Default is 'S'. Defined here so we don't need duplicate Else statements below
    data_type = 'string'

    if isinstance(col_type, dict):
        #special/complex types
        if col_type["type"] in [ "int-spinner" ]:
            data_type = 'integer'

        if col_type["type"] in [ "decimal-spinner" ]:
            data_type = 'float'
        
        if col_type["type"] in [ "tags", "multiple choice" ]:
            data_type = 'list'

        if col_type["type"] == 'file-upload':
            data_type = 'file'
    
    elif col_type in [ "int", "number" ]:
        data_type = 'integer'

    elif col_type == 'date':
        data_type = 'date'

    return data_type