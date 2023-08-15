#Python Standard Library
import base64
import json

def parse(data):

    entities        = data['entities']
    data_model      = data['data_model']
    project_varname = data['project_varname']

    #DDB-SETTINGS-START
    #Lots of DDB config to get from data model, or just use defaults
    ddb_table_name            = ""
    ddb_auto_scaling          = False
    ddb_surge_protection      = False
    ddb_surge_protection_fifo = False
    ddb_capacity_type         = "PAY_PER_REQUEST"
    ddb_rcu_provisioned       = 3
    ddb_wcu_provisioned       = 3

    for key in data_model:
        if key == "__STARK_advanced__":
            ddb_table_name            = data_model[key].get('ddb_table_name', "")
            ddb_surge_protection      = data_model[key].get('ddb_surge_protection', False)
            ddb_surge_protection_fifo = data_model[key].get('ddb_surge_protection_fifo', False)
            ddb_auto_scaling          = data_model[key].get('ddb_auto_scaling', False)
            ddb_capacity_type         = data_model[key].get('ddb_capacity_type', "PAY_PER_REQUEST")
            ddb_rcu_provisioned       = data_model[key].get('ddb_rcu_provisioned', 3)
            ddb_wcu_provisioned       = data_model[key].get('ddb_wcu_provisioned', 3)

    if ddb_table_name == "":
        ddb_table_name = "STARK_" + project_varname

    if ddb_auto_scaling:
        ddb_auto_scaling = "ENABLED"
    else:
        ddb_auto_scaling = "OFF"

    parsed = {
        "Table Name": ddb_table_name,
        "Capacity Type": ddb_capacity_type,
        "Surge Protection": ddb_surge_protection,
        "Surge Protection FIFO": ddb_surge_protection_fifo,
    }

    if ddb_capacity_type == "PROVISIONED":
        parsed["RCU"]          = ddb_rcu_provisioned
        parsed["WCU"]          = ddb_wcu_provisioned
        parsed["Auto Scaling"] = ddb_auto_scaling


    return parsed