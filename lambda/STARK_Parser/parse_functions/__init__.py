#Python Standard Library
import base64
import json
import get_relationship as get_rel

def parse(data):

    entities = data['entities']
    data_model = data['raw_data_model']
    
 
    #Each entity will be its own lambda function, and will become integrations for API gateway routes
    parsed = {
        "authorizer_default": {
            "Memory": 128,
            "Arch": "arm64",
            "Timeout": 5,
        },
        "stark_auth": {
            "Memory": 128,
            "Arch": "arm64",
            "Timeout": 5,
        },
        "stark_login": {
            "Memory": 1790,
            "Arch": "arm64",
            "Timeout": 5,
            "Layers": [
                "STARKScryptLayer"
            ]
        },
        "stark_logout": {
            "Memory": 128,
            "Arch": "arm64",
            "Timeout": 5
        },
        "stark_sysmodules": {
            "Memory": 128,
            "Arch": "arm64",
            "Timeout": 5
        },
        "STARK_Analytics": {
            "Memory": 128,
            "Arch": "arm64",
            "Timeout": 5,
            "Dependencies": entities
        },
        "STARK_User": {
            "Memory": 128,
            "Arch": "arm64",
            "Timeout": 5,
            "Layers": [
                "STARKScryptLayer"
            ],
            "Dependencies": [
                "STARK_User_Roles",
                "STARK_User_Permissions",
            ]
        },
        "STARK_Module": {
            "Memory": 128,
            "Arch": "arm64",
            "Timeout": 5,
            "Dependencies": [
                "STARK_Module_Groups"
            ]
        },
        "STARK_User_Roles": {
            "Memory": 128,
            "Arch": "arm64",
            "Timeout": 5,
            "Dependencies": [
                "STARK_User",
                "STARK_User_Permissions",
            ]
        },
        "STARK_User_Permissions": {
            "Memory": 128,
            "Arch": "arm64",
            "Timeout": 5
        },
        "STARK_User_Sessions": {
            "Memory": 128,
            "Arch": "arm64",
            "Timeout": 5
        },
        "STARK_Module_Groups": {
            "Memory": 128,
            "Arch": "arm64",
            "Timeout": 5,
            "Dependencies": [
                "STARK_Module"
            ]
        }
    }
    
    for entity in entities:
        relationships = get_rel.get_relationship(data_model, entity)
        dependencies = []
        if relationships.get('has_one', '') != '':
            for relation in relationships.get('has_one'):
                dependencies.append(relation['entity'])
                nested_dependency = get_rel.get_relationship(data_model, relation['entity'])
                if nested_dependency.get('has_one', '') != '':
                    for relation in nested_dependency.get('has_one'):
                        dependencies.append(relation['entity'])
        elif relationships.get('has_many', '') != '':
            for relation in relationships.get('has_many'):
                if relation['type'] == 'repeater':
                    dependencies.append(relation['entity'])

        parsed[entity] = {
            "Memory": 128,
            "Arch": "arm64",
            "Timeout": 30
        }

        if len(dependencies) > 0:
            parsed[entity]["Dependencies"] = dependencies

    return parsed