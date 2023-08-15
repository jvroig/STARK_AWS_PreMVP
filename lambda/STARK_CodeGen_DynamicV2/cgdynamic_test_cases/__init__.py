#STARK Code Generator component.
#Produces the test cases for modules of a STARK system

#Python Standard Library
import base64
from random import randint
import textwrap

#Private modules
import convert_friendly_to_system as converter

def create(data):
  
    pk             = data["PK"]
    entity         = data["Entity"]
    columns        = data["Columns"]
    ddb_table_name = data["DynamoDB Name"]
    bucket_name    = data['Bucket Name']
    relationships  = data["Relationships"]
    rel_model      = data["Rel Model"]
    sequence       = data['Sequence']
    
    #Convert human-friendly names to variable-friendly names
    entity_varname  = converter.convert_to_system_name(entity)
    entity_to_lower = entity_varname.lower()
    pk_varname     = converter.convert_to_system_name(pk)

    default_sk     = entity_varname + "|info"
    with_upload    = False

    cascade_function_string = ""
    for one_to_one_relation in relationships.get("has_one",[]):
        cascade_function_string += f"""
        def mock_cascade_pk_change_to_child(data, entity, attribute):
                return 'OK'
        monkeypatch.setattr({entity_to_lower}, "cascade_pk_change_to_child", mock_cascade_pk_change_to_child)
        """

    col_list = []
    ## removes child of many field in the selection of valid columns
    valid_columns = []
    for key, attributes in columns.items():
        valid_column = True
        if isinstance(attributes,dict):
            if attributes.get('has_many'):
                valid_column = False

        if valid_column:
            valid_columns.append(key)

    for key in valid_columns:
        col_list.append(key)

    col_to_edit = col_list[randint(0,len(col_list) - 1)]
    col_type = set_type(columns[col_to_edit])
    test_data_for_edit = "'Testing Edit'"
    if col_type == 'SS':
        test_data_for_edit = ["Testing Edit"]
    elif col_type == 'N':
        test_data_for_edit = "'20'"

    col_to_edit_varname = converter.convert_to_system_name(col_to_edit)
    
    source_code = f"""\
    #Python Standard Library
    import json
    from moto import mock_dynamodb
    import boto3
    import pytest

    import {entity_varname} as {entity_to_lower}
    import stark_core as core
    from stark_core import security
    from stark_core import validation
    from stark_core import utilities
    from stark_core import data_abstraction

    def test_map_results(get_{entity_to_lower}_data):

        mapped_item = {entity_to_lower}.map_results(get_{entity_to_lower}_data)
        pass
        
    def test_create_listview_index_value(set_{entity_to_lower}_payload):

        assert set_{entity_to_lower}_payload['pk'] == {entity_to_lower}.create_listview_index_value(set_{entity_to_lower}_payload)"""
    
    if len(sequence) > 0:
        concat_seq = "_sequence"
    else:
        concat_seq = ""
        
    source_code += f"""
    @mock_dynamodb
    def test_add(use_moto,set_{entity_to_lower}_payload{concat_seq}, monkeypatch):
        use_moto()
        ddb = boto3.client('dynamodb', region_name=core.test_region)
        {cascade_function_string}
    """


    if len(sequence) > 0:
        source_code += f"""
        def mock_get_sequence(pk, db_handler = None):
            return set_{entity_to_lower}_payload_sequence['pk']
        monkeypatch.setattr(data_abstraction, "get_sequence", mock_get_sequence)
        """

    source_code += f"""
        {entity_to_lower}.add(set_{entity_to_lower}_payload{concat_seq}, 'POST', ddb)
        assert  {entity_to_lower}.resp_obj['ResponseMetadata']['HTTPStatusCode'] == 200
    
    """

    if len(sequence) > 0:
        source_code += f"""    
    @mock_dynamodb
    def test_get_by_pk_sequence(use_moto,set_{entity_to_lower}_payload_sequence, monkeypatch):
        use_moto()
        ddb = boto3.client('dynamodb', region_name=core.test_region)

        def mock_get_sequence(pk, db_handler = None):
            return set_{entity_to_lower}_payload_sequence['pk']
        monkeypatch.setattr(data_abstraction, "get_sequence", mock_get_sequence)

        {entity_to_lower}.add(set_{entity_to_lower}_payload_sequence, 'POST', ddb)
        response  = {entity_to_lower}.get_by_pk(set_{entity_to_lower}_payload_sequence['pk'], set_{entity_to_lower}_payload_sequence['sk'], ddb)

        assert set_{entity_to_lower}_payload_sequence['pk'] == response['item']['{pk_varname}']"""
    else:
        source_code += f"""    
    @mock_dynamodb
    def test_get_by_pk(use_moto,set_{entity_to_lower}_payload, monkeypatch):
        use_moto()
        ddb = boto3.client('dynamodb', region_name=core.test_region)

        {entity_to_lower}.add(set_{entity_to_lower}_payload, 'POST', ddb)
        response  = {entity_to_lower}.get_by_pk(set_{entity_to_lower}_payload['pk'], set_{entity_to_lower}_payload['sk'], ddb)

        assert set_{entity_to_lower}_payload['pk'] == response['item']['{pk_varname}']"""

    if len(sequence) > 0:
        concat_seq = "_sequence"
    else:
        concat_seq = ""

    source_code += f"""
    @mock_dynamodb
    def test_get_all(use_moto,set_{entity_to_lower}_payload{concat_seq}, monkeypatch):
        use_moto()
        ddb = boto3.client('dynamodb', region_name=core.test_region)"""

    if len(sequence) > 0:
        source_code += f"""
        def mock_get_sequence(pk, db_handler = None):
            return set_{entity_to_lower}_payload_sequence['pk']
        monkeypatch.setattr(data_abstraction, "get_sequence", mock_get_sequence)
        """

    source_code += f"""        
        {entity_to_lower}.add(set_{entity_to_lower}_payload{concat_seq}, 'POST', ddb)
        set_{entity_to_lower}_payload{concat_seq}['pk'] = 'Test3'
        {entity_to_lower}.add(set_{entity_to_lower}_payload{concat_seq}, 'POST', ddb)
        set_{entity_to_lower}_payload{concat_seq}['pk'] = 'Test4'
        {entity_to_lower}.add(set_{entity_to_lower}_payload{concat_seq}, 'POST', ddb)
        set_{entity_to_lower}_payload{concat_seq}['pk'] = 'Test1'
        {entity_to_lower}.add(set_{entity_to_lower}_payload{concat_seq}, 'POST', ddb)
        response  = {entity_to_lower}.get_all('{default_sk}', None, ddb)
        # print(response)
        assert len(response[0]) == 4

    @mock_dynamodb
    def test_edit(use_moto,set_{entity_to_lower}_payload{concat_seq}, monkeypatch):
        use_moto()
        ddb = boto3.client('dynamodb', region_name=core.test_region)
        {cascade_function_string}"""

    if len(sequence) > 0:
        source_code += f"""
        def mock_get_sequence(pk, db_handler = None):
            return set_{entity_to_lower}_payload_sequence['pk']
        monkeypatch.setattr(data_abstraction, "get_sequence", mock_get_sequence)
        """
    source_code += f"""
        {entity_to_lower}.add(set_{entity_to_lower}_payload{concat_seq}, 'POST', ddb)
        set_{entity_to_lower}_payload{concat_seq}['{col_to_edit_varname}'] = {test_data_for_edit}
        {entity_to_lower}.edit(set_{entity_to_lower}_payload{concat_seq}, ddb)

        assert set_{entity_to_lower}_payload{concat_seq}['{col_to_edit_varname}'] == {entity_to_lower}.resp_obj['Attributes']['{col_to_edit_varname}']['{col_type}']

    @mock_dynamodb
    def test_delete(use_moto,set_{entity_to_lower}_payload{concat_seq}, monkeypatch):
        use_moto()
        ddb = boto3.client('dynamodb', region_name=core.test_region)"""

    if len(sequence) > 0:
        source_code += f"""
        def mock_get_sequence(pk, db_handler = None):
            return set_{entity_to_lower}_payload_sequence['pk']
        monkeypatch.setattr(data_abstraction, "get_sequence", mock_get_sequence)
        """
    source_code += f"""
        {entity_to_lower}.add(set_{entity_to_lower}_payload{concat_seq}, 'POST', ddb)
        {entity_to_lower}.delete(set_{entity_to_lower}_payload{concat_seq}, ddb)
        response  = {entity_to_lower}.get_all('{default_sk}', None, ddb)
        assert len(response[0]) == 0
    
    def test_lambda_handler_rt_fail():
        response = {entity_to_lower}.lambda_handler({{'queryStringParameters':{{'rt':'incorrect_request_type'}}}}, '')
        assert '"Could not handle GET request - unknown request type"' == response['body']
        
    def test_lambda_handler_rt_all(monkeypatch):
        def mock_get_all(sk, lv_token):
            return "always success", ''
        monkeypatch.setattr({entity_to_lower}, "get_all", mock_get_all)
        response = {entity_to_lower}.lambda_handler({{'queryStringParameters':{{'rt':'all'}}}}, '')
        assert 200 == response['statusCode']

    def test_lambda_handler_rt_detail(monkeypatch): 
        def mock_get_by_pk(pk, sk):
            return "always success"
        monkeypatch.setattr({entity_to_lower}, "get_by_pk", mock_get_by_pk)
        response = {entity_to_lower}.lambda_handler({{'queryStringParameters':{{'rt':'detail','{pk_varname}':'0001', 'sk': '{default_sk}'}}}}, '')
        assert 200 == response['statusCode']
        
    def test_lambda_handler_method_no_payload():
        event = {{
            'requestContext':{{
                'http': {{'method':"POST"}}
                }},
            'body':json.dumps({{'No':'Payload'}})
            }}
        response = {entity_to_lower}.lambda_handler(event, '')
    
        assert '"Client payload missing"' == response['body']
        
    def test_lambda_handler_method_fail(get_{entity_to_lower}_raw_payload):
        event = {{
            'requestContext':{{
                'http': {{'method':"POSTS"}}
                }},
            'body':json.dumps(get_{entity_to_lower}_raw_payload)
            }}
        response = {entity_to_lower}.lambda_handler(event, '')

        assert '"Could not handle API request"' == response['body']
        
    def test_lambda_handler_method_report_fail(get_{entity_to_lower}_raw_report_payload):
        get_{entity_to_lower}_raw_report_payload['{entity_varname}']['{pk_varname}']['operator'] = ''
        event = {{
            'requestContext':{{
                'http': {{'method':"POST"}}
                }},
            'body':json.dumps(get_{entity_to_lower}_raw_report_payload)
            }}
        response = {entity_to_lower}.lambda_handler(event, '')

        assert '"Missing operators"' == response['body']
        
    def test_lambda_handler_delete_unauthorized(get_{entity_to_lower}_raw_payload,monkeypatch):
        event = {{
            'requestContext':{{
                'http': {{'method':"DELETE"}}
                }},
            'body':json.dumps(get_{entity_to_lower}_raw_payload)
            }}
        def mock_is_authorized(permission, event, ddb):
            return False

        monkeypatch.setattr(security, "is_authorized", mock_is_authorized)
        monkeypatch.setattr(security, "authFailResponse", [security.authFailCode, f"Could not find {entity}|delete for test_user"])
        response = {entity_to_lower}.lambda_handler(event, '')
    
        assert '"Could not find {entity}|delete for test_user"' == response['body']
        
    def test_lambda_handler_edit_unauthorized(get_{entity_to_lower}_raw_payload, monkeypatch):
        event = {{
            'requestContext':{{
                'http': {{'method':"PUT"}}
                }},
            'body':json.dumps(get_{entity_to_lower}_raw_payload)
            }}
        def mock_is_authorized(permission, event, ddb):
            return False

        monkeypatch.setattr(security, "is_authorized", mock_is_authorized)
        monkeypatch.setattr(security, "authFailResponse", [security.authFailCode, f"Could not find {entity}|edit for test_user"])
        response = {entity_to_lower}.lambda_handler(event, '')
        
        assert '"Could not find {entity}|edit for test_user"' == response['body']

    def test_lambda_handler_add_unauthorized(get_{entity_to_lower}_raw_payload, monkeypatch):
        event = {{
            'requestContext':{{
                'http': {{'method':"POST"}}
                }},
            'body':json.dumps(get_{entity_to_lower}_raw_payload)
            }}
        def mock_is_authorized(permission, event, ddb):
            return False

        monkeypatch.setattr(security, "is_authorized", mock_is_authorized)
        monkeypatch.setattr(security, "authFailResponse", [security.authFailCode, f"Could not find {entity}|add for test_user"])
        response = {entity_to_lower}.lambda_handler(event, '')
        
        assert '"Could not find {entity}|add for test_user"' == response['body']

    def test_lambda_handler_report_unauthorized(get_{entity_to_lower}_raw_report_payload, monkeypatch):
        event = {{
            'requestContext':{{
                'http':{{'method':"POST"}}
                }},
            'body':json.dumps(get_{entity_to_lower}_raw_report_payload)
            }}
        def mock_is_authorized(permission, event, ddb):
            return False

        monkeypatch.setattr(security, "is_authorized", mock_is_authorized)
        monkeypatch.setattr(security, "authFailResponse", [security.authFailCode, f"Could not find {entity}|report for test_user"])
        response = {entity_to_lower}.lambda_handler(event, '')
        
        assert '"Could not find {entity}|report for test_user"' == response['body']

    def test_lambda_handler_delete(get_{entity_to_lower}_raw_payload, set_{entity_to_lower}_payload, monkeypatch):
        event = {{
            'requestContext':{{
                'http':{{'method':"DELETE"}}
                }},
            'body':json.dumps(get_{entity_to_lower}_raw_payload)
            }}

        def mock_is_authorized(permission, event, ddb):
            return True

        def mock_delete(data):
            assert set_{entity_to_lower}_payload == data
            return "OK"

        monkeypatch.setattr(security, "is_authorized", mock_is_authorized)
        monkeypatch.setattr({entity_to_lower}, "delete", mock_delete)
        {entity_to_lower}.lambda_handler(event, '')
        
    def test_lambda_handler_edit(get_{entity_to_lower}_raw_payload, set_{entity_to_lower}_payload, monkeypatch):
        event = {{
            'requestContext':{{
                'http':{{'method':"PUT"}}
                }},
            'body':json.dumps(get_{entity_to_lower}_raw_payload)
            }}

        def mock_is_authorized(permission, event, ddb):
            return True

        def mock_validate_form(payload, metadata):
            return []

        def mock_edit(data):
            data.pop('{pk_varname}')
            assert set_{entity_to_lower}_payload == data
            return "OK"

        monkeypatch.setattr(security, "is_authorized", mock_is_authorized)
        monkeypatch.setattr(validation, "validate_form", mock_validate_form)
        monkeypatch.setattr({entity_to_lower}, "edit", mock_edit)
        {entity_to_lower}.lambda_handler(event, '')

    def test_lambda_handler_edit_add(get_{entity_to_lower}_raw_payload, set_{entity_to_lower}_payload, monkeypatch):
        get_{entity_to_lower}_raw_payload['{entity_varname}']['{pk_varname}'] = 'Test1'
        event = {{
            'requestContext':{{
                'http':{{'method':"PUT"}}
                }},
            'body':json.dumps(get_{entity_to_lower}_raw_payload)
            }}

        def mock_is_authorized(permission, event, ddb):
            return True

        def mock_validate_form(payload, metadata):
            return []

        def mock_add(data, method):
            data.pop('{pk_varname}')
            set_{entity_to_lower}_payload['pk'] = 'Test1'
            set_{entity_to_lower}_payload['STARK-ListView-sk'] = 'Test1'
            assert set_{entity_to_lower}_payload == data
            return "OK"

        def mock_delete(data):
            set_{entity_to_lower}_payload['pk'] = 'Test2'
            assert set_{entity_to_lower}_payload == data
            return "OK"

        monkeypatch.setattr(security, "is_authorized", mock_is_authorized)
        monkeypatch.setattr(validation, "validate_form", mock_validate_form)
        monkeypatch.setattr({entity_to_lower}, "add", mock_add)
        monkeypatch.setattr({entity_to_lower}, "delete", mock_delete)
        {entity_to_lower}.lambda_handler(event, '')

    def test_lambda_handler_add(get_{entity_to_lower}_raw_payload, set_{entity_to_lower}_payload, monkeypatch):
        event = {{
            'requestContext':{{
                'http':{{'method':"POST"}}
                }},
            'body':json.dumps(get_{entity_to_lower}_raw_payload)
            }}

        def mock_is_authorized(permission, event, ddb):
            return True

        def mock_validate_form(payload, metadata):
            return []

        def mock_add(data):
            data.pop('{pk_varname}')
            assert set_{entity_to_lower}_payload == data
            return "OK"


        monkeypatch.setattr(security, "is_authorized", mock_is_authorized)
        monkeypatch.setattr(validation, "validate_form", mock_validate_form)
        monkeypatch.setattr({entity_to_lower}, "add", mock_add)
        {entity_to_lower}.lambda_handler(event, '')

    """

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