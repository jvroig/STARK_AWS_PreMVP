#STARK Code Generator component.
#Produces the config test file of a STARK system

#Python Standard Library
import base64
import textwrap

#Private modules
import convert_friendly_to_system as converter

def create(data):
    print('data conftest')
    print(data)
    entities       = data["Entities"]
    #Convert human-friendly names to variable-friendly names

    source_code = f"""\
        import pytest
        from moto import mock_dynamodb
        import boto3
        import os
        import sys
        import stark_core as core

        #Entity Fixtures
        STARK_folder = os.getcwd() + '/lambda/test_cases'
        sys.path = [STARK_folder] + sys.path"""
    for entity in entities:
        entity_varname  = converter.convert_to_system_name(entity)
        source_code += f"""
        from fixtures import {entity_varname} as {entity_varname.lower()}"""

    source_code += f"""    
        from admin_fixtures import STARK_Module as stark_module
        from admin_fixtures import STARK_Module_Groups as stark_module_groups
        from admin_fixtures import STARK_User as stark_user
        from admin_fixtures import STARK_User_Roles as stark_user_roles
        from admin_fixtures import STARK_User_Permissions as stark_user_permissions
        from admin_fixtures import STARK_User_Sessions as stark_user_sessions"""
    
    source_code += f"""
    
        @pytest.fixture
        def use_moto():
            @mock_dynamodb
            def ddb_client():
                ddb = boto3.resource('dynamodb', region_name=core.test_region)
                ddb.create_table(
                    TableName=core.ddb_table,
                    GlobalSecondaryIndexes=[
                        {{
                            'IndexName': 'STARK-ListView-Index',
                            'KeySchema':[
                            {{
                                'AttributeName': 'sk',
                                'KeyType': 'HASH'
                            }},
                            {{
                                'AttributeName': 'STARK-ListView-sk',
                                'KeyType': 'RANGE'
                            }}],
                            'Projection': 
                                {{'ProjectionType': 'ALL'}}
                        }}
                    ],
                    AttributeDefinitions=[
                        {{
                            'AttributeName': 'pk',
                            'AttributeType': 'S'
                        }},
                        {{
                            'AttributeName': 'sk',
                            'AttributeType': 'S'
                        }},
                        {{
                            'AttributeName': 'STARK-ListView-sk',
                            'AttributeType': 'S'
                        }},
                    ],
                    KeySchema=[
                            {{
                                'AttributeName': 'pk',
                                'KeyType': 'HASH'
                            }},
                            {{
                                'AttributeName': 'sk',
                                'KeyType': 'RANGE'
                            }},

                    ],
                    BillingMode='PAY_PER_REQUEST'
                )
                return ddb
            return ddb_client

        # @pytest.fixture(scope='function')
        # def aws_credentials():
        ##     Mocked AWS Credentials for moto.
        #     os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
        #     os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
        #     os.environ['AWS_SECURITY_TOKEN'] = 'testing'
        #     os.environ['AWS_SESSION_TOKEN'] = 'testing'
        #     os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
        """
    for entity in entities:
        entity_varname  = converter.convert_to_system_name(entity)
        source_code += f"""
        @pytest.fixture
        def get_{entity_varname.lower()}_data():
            return {entity_varname.lower()}.get_data()
            """

        if len(data['Models'][entity].get("sequence", {})) > 0:
                # print('here')
                source_code += f"""
        @pytest.fixture
        def set_{entity_varname.lower()}_payload_sequence():
            return {entity_varname.lower()}.set_payload_sequence()
            """
            
        source_code += f"""
        @pytest.fixture
        def set_{entity_varname.lower()}_payload():
            return {entity_varname.lower()}.set_payload()
            """

        source_code += f""" 
        @pytest.fixture
        def get_{entity_varname.lower()}_raw_payload():
            return {entity_varname.lower()}.get_raw_payload()

        @pytest.fixture
        def get_{entity_varname.lower()}_raw_report_payload():
            return {entity_varname.lower()}.get_raw_report_payload()
        """

    source_code +=f"""
        # ==================================================
        @pytest.fixture
        def get_stark_module_data():
            return stark_module.get_data()

        @pytest.fixture
        def set_stark_module_payload_sequence():
            return stark_module.set_payload_sequence()

        @pytest.fixture
        def set_stark_module_payload():
            return stark_module.set_payload()

        @pytest.fixture
        def get_stark_module_raw_payload():
            return stark_module.get_raw_payload()

        @pytest.fixture
        def get_stark_module_raw_report_payload():
            return stark_module.get_raw_report_payload()

        # ==================================================
        @pytest.fixture
        def get_stark_module_groups_data():
            return stark_module_groups.get_data()

        @pytest.fixture
        def set_stark_module_groups_payload_sequence():
            return stark_module_groups.set_payload_sequence()

        @pytest.fixture
        def set_stark_module_groups_payload():
            return stark_module_groups.set_payload()

        @pytest.fixture
        def get_stark_module_groups_raw_payload():
            return stark_module_groups.get_raw_payload()

        @pytest.fixture
        def get_stark_module_groups_raw_report_payload():
            return stark_module_groups.get_raw_report_payload()

        # ==================================================
        @pytest.fixture
        def get_stark_user_data():
            return stark_user.get_data()

        @pytest.fixture
        def set_stark_user_payload_sequence():
            return stark_user.set_payload_sequence()

        @pytest.fixture
        def set_stark_user_payload():
            return stark_user.set_payload()

        @pytest.fixture
        def get_stark_user_raw_payload():
            return stark_user.get_raw_payload()

        @pytest.fixture
        def get_stark_user_raw_report_payload():
            return stark_user.get_raw_report_payload()

        # ==================================================
        @pytest.fixture
        def get_stark_user_roles_data():
            return stark_user_roles.get_data()

        @pytest.fixture
        def set_stark_user_roles_payload_sequence():
            return stark_user_roles.set_payload_sequence()

        @pytest.fixture
        def set_stark_user_roles_payload():
            return stark_user_roles.set_payload()

        @pytest.fixture
        def get_stark_user_roles_raw_payload():
            return stark_user_roles.get_raw_payload()

        @pytest.fixture
        def get_stark_user_roles_raw_report_payload():
            return stark_user_roles.get_raw_report_payload()

        # ==================================================
        @pytest.fixture
        def get_stark_user_permissions_data():
            return stark_user_permissions.get_data()

        @pytest.fixture
        def set_stark_user_permissions_payload_sequence():
            return stark_user_permissions.set_payload_sequence()

        @pytest.fixture
        def set_stark_user_permissions_payload():
            return stark_user_permissions.set_payload()

        @pytest.fixture
        def get_stark_user_permissions_raw_payload():
            return stark_user_permissions.get_raw_payload()

        @pytest.fixture
        def get_stark_user_permissions_raw_report_payload():
            return stark_user_permissions.get_raw_report_payload()

        # ==================================================
        @pytest.fixture
        def get_stark_user_sessions_data():
            return stark_user_sessions.get_data()

        @pytest.fixture
        def set_stark_user_sessions_payload_sequence():
            return stark_user_sessions.set_payload_sequence()

        @pytest.fixture
        def set_stark_user_sessions_payload():
            return stark_user_sessions.set_payload()

        @pytest.fixture
        def get_stark_user_sessions_raw_payload():
            return stark_user_sessions.get_raw_payload()

        @pytest.fixture
        def get_stark_user_sessions_raw_report_payload():
            return stark_user_sessions.get_raw_report_payload()
        """
    
    return textwrap.dedent(source_code)