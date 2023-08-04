    # item['pk'] = {'S' : pk}
    # item['sk'] = {'S' : sk}
    # item['Description'] = {'S' : Description}
    # item['Icon'] = {'S' : Icon}
    # item['Priority'] = {'N' : Priority}


def get_data():
    data = {}
    data['pk'] = {'S' : 'Test Module'}
    data['sk'] = {'S' : 'stark_module_groups|info'}
    data['Description'] = {'S' : ''}
    data['Icon'] = {'S' : ''}
    data['Priority'] = {'N' : '1'}
    return data

def set_payload_sequence():
    payload = {}
    payload['pk']                = 'C-000001'
    payload['orig_pk']           = 'C-000001'
    payload['sk']                = 'stark_module_groups|info'
    payload['Description']       = ''
    payload['Icon']              = ''
    payload['Priority']          = '1'
    payload['STARK-ListView-sk'] = 'Test Module2'
    return payload

def set_payload():
    payload = {}
    payload['pk']                     = 'Test2'
    payload['orig_pk']                = 'Test2'
    payload['sk']                     = 'stark_module_groups|info'
    payload['sk']                     = 'stark_module_groups|info'
    payload['Description']            = ''
    payload['Icon']                   = ''
    payload['Priority']               = '1'  
    payload['STARK-ListView-sk']      = 'Test2'
    payload['STARK_uploaded_s3_keys'] = {}
    return payload

def get_raw_payload():
    raw_payload = {
        "STARK_Module_Groups": {
           'Group_Name'        : 'Test2',
           'orig_Group_Name'   : 'Test2',
           'Description'        : '',
           'Icon'               : '',
           'Priority'           : '1',
           'sk'                 : 'stark_module_groups|info',
        }
    }
    return raw_payload

def get_raw_report_payload():
    raw_payload = {
        "STARK_Module_Groups": {
            'Group_Name'        : {'operator': "=",'type': "S",'value': "Hello"},
            'Description'        : {'operator': "",'type': "S",'value': ""},
            'Icon'               : {'operator': "",'type': "S",'value': ""},
            'Priority'           : {'operator': "",'type': "S",'value': ""},
            'STARK_Chart_Type'   : "",
            'STARK_Report_Type'  : "Tabular",
            'STARK_X_Data_Source': "",
            'STARK_Y_Data_Source': "",
            'STARK_count_fields' : [],
            'STARK_group_by_1'   : "",
            'STARK_isReport'     : True,
            'STARK_report_fields': ["Group_Name", "Description"],
            'STARK_sum_fields'   : []
        }
    }
    return raw_payload


