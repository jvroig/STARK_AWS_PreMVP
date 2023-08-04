#Python Standard Library
import json
from moto import mock_dynamodb
import boto3
import pytest

import STARK_User_Roles as stark_user_roles
import stark_core as core
from stark_core import security
from stark_core import validation
from stark_core import utilities
from stark_core import data_abstraction

def test_map_results(get_stark_user_roles_data):

    mapped_item = stark_user_roles.map_results(get_stark_user_roles_data)
    pass

def test_create_listview_index_value(set_stark_user_roles_payload):
    assert set_stark_user_roles_payload['pk'] == stark_user_roles.create_listview_index_value(set_stark_user_roles_payload)
    
@mock_dynamodb
def test_add(use_moto,set_stark_user_roles_payload_sequence, monkeypatch):
    use_moto()
    ddb = boto3.client('dynamodb', region_name=core.test_region)

    def mock_get_sequence(pk, db_handler = None):
        return set_stark_user_roles_payload_sequence['pk']
    monkeypatch.setattr(data_abstraction, "get_sequence", mock_get_sequence)

    stark_user_roles.add(set_stark_user_roles_payload_sequence, 'POST', ddb)
    assert  stark_user_roles.resp_obj['ResponseMetadata']['HTTPStatusCode'] == 200


@mock_dynamodb
def test_get_by_pk_sequence(use_moto,set_stark_user_roles_payload_sequence, monkeypatch):
    use_moto()
    ddb = boto3.client('dynamodb', region_name=core.test_region)

    def mock_get_sequence(pk, db_handler = None):
        return set_stark_user_roles_payload_sequence['pk']
    monkeypatch.setattr(data_abstraction, "get_sequence", mock_get_sequence)

    stark_user_roles.add(set_stark_user_roles_payload_sequence, 'POST', ddb)
    response  = stark_user_roles.get_by_pk(set_stark_user_roles_payload_sequence['pk'], set_stark_user_roles_payload_sequence['sk'], ddb)

    assert set_stark_user_roles_payload_sequence['pk'] == response['item']['Role_Name']


@mock_dynamodb
def test_get_all(use_moto,set_stark_user_roles_payload_sequence, monkeypatch):
    use_moto()
    ddb = boto3.client('dynamodb', region_name=core.test_region)
    def mock_get_sequence(pk, db_handler = None):
        return set_stark_user_roles_payload_sequence['pk']
    monkeypatch.setattr(data_abstraction, "get_sequence", mock_get_sequence)

    stark_user_roles.add(set_stark_user_roles_payload_sequence, 'POST', ddb)
    set_stark_user_roles_payload_sequence['pk'] = 'Test3'
    stark_user_roles.add(set_stark_user_roles_payload_sequence, 'POST', ddb)
    set_stark_user_roles_payload_sequence['pk'] = 'Test4'
    stark_user_roles.add(set_stark_user_roles_payload_sequence, 'POST', ddb)
    set_stark_user_roles_payload_sequence['pk'] = 'Test1'
    stark_user_roles.add(set_stark_user_roles_payload_sequence, 'POST', ddb)
    response  = stark_user_roles.get_all('stark_user_roles|info', None, ddb)
    # print(response)
    assert len(response[0]) == 4

@mock_dynamodb
def test_edit(use_moto,set_stark_user_roles_payload_sequence, monkeypatch):
    use_moto()
    ddb = boto3.client('dynamodb', region_name=core.test_region)

    def mock_get_sequence(pk, db_handler = None):
        return set_stark_user_roles_payload_sequence['pk']
    monkeypatch.setattr(data_abstraction, "get_sequence", mock_get_sequence)

    stark_user_roles.add(set_stark_user_roles_payload_sequence, 'POST', ddb)
    set_stark_user_roles_payload_sequence['Description'] = 'Testing Edit'
    stark_user_roles.edit(set_stark_user_roles_payload_sequence, ddb)

    assert set_stark_user_roles_payload_sequence['Description'] == stark_user_roles.resp_obj['Attributes']['Description']['S']

@mock_dynamodb
def test_delete(use_moto,set_stark_user_roles_payload_sequence, monkeypatch):
    use_moto()
    ddb = boto3.client('dynamodb', region_name=core.test_region)
    def mock_get_sequence(pk, db_handler = None):
        return set_stark_user_roles_payload_sequence['pk']
    monkeypatch.setattr(data_abstraction, "get_sequence", mock_get_sequence)

    stark_user_roles.add(set_stark_user_roles_payload_sequence, 'POST', ddb)
    stark_user_roles.delete(set_stark_user_roles_payload_sequence, ddb)
    response  = stark_user_roles.get_all('stark_module|info', None, ddb)
    assert len(response[0]) == 0

def test_lambda_handler_rt_fail():
    response = stark_user_roles.lambda_handler({'queryStringParameters':{'rt':'incorrect_request_type'}}, '')
    assert '"Could not handle GET request - unknown request type"' == response['body']

def test_lambda_handler_rt_all(monkeypatch):
    def mock_get_all(sk, lv_token):
        return "always success", ''
    monkeypatch.setattr(stark_user_roles, "get_all", mock_get_all)
    response = stark_user_roles.lambda_handler({'queryStringParameters':{'rt':'all'}}, '')
    assert 200 == response['statusCode']

def test_lambda_handler_rt_detail(monkeypatch): 
    def mock_get_by_pk(pk, sk):
        return "always success"
    monkeypatch.setattr(stark_user_roles, "get_by_pk", mock_get_by_pk)
    response = stark_user_roles.lambda_handler({'queryStringParameters':{'rt':'detail','Role_Name':'0001', 'sk': 'stark_module|info'}}, '')
    assert 200 == response['statusCode']

def test_lambda_handler_method_no_payload():
    event = {
        'requestContext':{
            'http': {'method':"POST"}
            },
        'body':json.dumps({'No':'Payload'})
        }
    response = stark_user_roles.lambda_handler(event, '')

    assert '"Client payload missing"' == response['body']

def test_lambda_handler_method_fail(get_stark_user_roles_raw_payload):
    event = {
        'requestContext':{
            'http': {'method':"POSTS"}
            },
        'body':json.dumps(get_stark_user_roles_raw_payload)
        }
    response = stark_user_roles.lambda_handler(event, '')

    assert '"Could not handle API request"' == response['body']

def test_lambda_handler_method_report_fail(get_stark_user_roles_raw_report_payload):
    get_stark_user_roles_raw_report_payload['STARK_User_Roles']['Role_Name']['operator'] = ''
    event = {
        'requestContext':{
            'http': {'method':"POST"}
            },
        'body':json.dumps(get_stark_user_roles_raw_report_payload)
        }
    response = stark_user_roles.lambda_handler(event, '')

    assert '"Missing operators"' == response['body']

def test_lambda_handler_delete_unauthorized(get_stark_user_roles_raw_payload,monkeypatch):
    event = {
        'requestContext':{
            'http': {'method':"DELETE"}
            },
        'body':json.dumps(get_stark_user_roles_raw_payload)
        }
    def mock_is_authorized(permission, event, ddb):
        return False

    monkeypatch.setattr(security, "is_authorized", mock_is_authorized)
    monkeypatch.setattr(security, "authFailResponse", [security.authFailCode, f"Could not find stark_module|delete for test_user"])
    response = stark_user_roles.lambda_handler(event, '')

    assert '"Could not find stark_module|delete for test_user"' == response['body']

def test_lambda_handler_edit_unauthorized(get_stark_user_roles_raw_payload, monkeypatch):
    event = {
        'requestContext':{
            'http': {'method':"PUT"}
            },
        'body':json.dumps(get_stark_user_roles_raw_payload)
        }
    def mock_is_authorized(permission, event, ddb):
        return False

    monkeypatch.setattr(security, "is_authorized", mock_is_authorized)
    monkeypatch.setattr(security, "authFailResponse", [security.authFailCode, f"Could not find stark_module|edit for test_user"])
    response = stark_user_roles.lambda_handler(event, '')

    assert '"Could not find stark_module|edit for test_user"' == response['body']

def test_lambda_handler_add_unauthorized(get_stark_user_roles_raw_payload, monkeypatch):
    event = {
        'requestContext':{
            'http': {'method':"POST"}
            },
        'body':json.dumps(get_stark_user_roles_raw_payload)
        }
    def mock_is_authorized(permission, event, ddb):
        return False

    monkeypatch.setattr(security, "is_authorized", mock_is_authorized)
    monkeypatch.setattr(security, "authFailResponse", [security.authFailCode, f"Could not find stark_module|add for test_user"])
    response = stark_user_roles.lambda_handler(event, '')

    assert '"Could not find stark_module|add for test_user"' == response['body']

def test_lambda_handler_report_unauthorized(get_stark_user_roles_raw_report_payload, monkeypatch):
    event = {
        'requestContext':{
            'http':{'method':"POST"}
            },
        'body':json.dumps(get_stark_user_roles_raw_report_payload)
        }
    def mock_is_authorized(permission, event, ddb):
        return False

    monkeypatch.setattr(security, "is_authorized", mock_is_authorized)
    monkeypatch.setattr(security, "authFailResponse", [security.authFailCode, f"Could not find System Modules|Report for test_user"])
    response = stark_user_roles.lambda_handler(event, '')

    assert '"Could not find System Modules|Report for test_user"' == response['body']

def test_lambda_handler_delete(get_stark_user_roles_raw_payload, set_stark_user_roles_payload, monkeypatch):
    event = {
        'requestContext':{
            'http':{'method':"DELETE"}
            },
        'body':json.dumps(get_stark_user_roles_raw_payload)
        }

    def mock_is_authorized(permission, event, ddb):
        return True

    def mock_delete(data):
        assert set_stark_user_roles_payload == data
        return "OK"

    monkeypatch.setattr(security, "is_authorized", mock_is_authorized)
    monkeypatch.setattr(stark_user_roles, "delete", mock_delete)
    stark_user_roles.lambda_handler(event, '')

def test_lambda_handler_edit(get_stark_user_roles_raw_payload, set_stark_user_roles_payload, monkeypatch):
    event = {
        'requestContext':{
            'http':{'method':"PUT"}
            },
        'body':json.dumps(get_stark_user_roles_raw_payload)
        }

    def mock_is_authorized(permission, event, ddb):
        return True

    def mock_validate_form(payload, metadata):
        return []

    def mock_edit(data):
        data.pop('Role_Name')
        assert set_stark_user_roles_payload == data
        return "OK"

    monkeypatch.setattr(security, "is_authorized", mock_is_authorized)
    monkeypatch.setattr(validation, "validate_form", mock_validate_form)
    monkeypatch.setattr(stark_user_roles, "edit", mock_edit)
    stark_user_roles.lambda_handler(event, '')

def test_lambda_handler_edit_add(get_stark_user_roles_raw_payload, set_stark_user_roles_payload, monkeypatch):
    get_stark_user_roles_raw_payload['STARK_User_Roles']['Role_Name'] = 'Test2'
    event = {
        'requestContext':{
            'http':{'method':"PUT"}
            },
        'body':json.dumps(get_stark_user_roles_raw_payload)
        }

    def mock_is_authorized(permission, event, ddb):
        return True

    def mock_validate_form(payload, metadata):
        return []

    def mock_add(data, method):
        data.pop('Role_Name')
        set_stark_user_roles_payload['pk'] = 'Test2'
        set_stark_user_roles_payload['STARK-ListView-sk'] = 'Test2'
        assert set_stark_user_roles_payload == data
        return "OK"

    def mock_delete(data):
        set_stark_user_roles_payload['pk'] = 'Test2'
        assert set_stark_user_roles_payload == data
        return "OK"

    monkeypatch.setattr(security, "is_authorized", mock_is_authorized)
    monkeypatch.setattr(validation, "validate_form", mock_validate_form)
    monkeypatch.setattr(stark_user_roles, "add", mock_add)
    monkeypatch.setattr(stark_user_roles, "delete", mock_delete)
    stark_user_roles.lambda_handler(event, '')

def test_lambda_handler_add(get_stark_user_roles_raw_payload, set_stark_user_roles_payload, monkeypatch):
    event = {
        'requestContext':{
            'http':{'method':"POST"}
            },
        'body':json.dumps(get_stark_user_roles_raw_payload)
        }

    def mock_is_authorized(permission, event, ddb):
        return True

    def mock_validate_form(payload, metadata):
        return []

    def mock_add(data):
        data.pop('Role_Name')
        assert set_stark_user_roles_payload == data
        return "OK"


    monkeypatch.setattr(security, "is_authorized", mock_is_authorized)
    monkeypatch.setattr(validation, "validate_form", mock_validate_form)
    monkeypatch.setattr(stark_user_roles, "add", mock_add)
    stark_user_roles.lambda_handler(event, '')

