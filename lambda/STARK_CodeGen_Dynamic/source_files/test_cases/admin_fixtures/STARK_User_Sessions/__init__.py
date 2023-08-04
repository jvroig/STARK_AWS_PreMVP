def get_data():
    data = {}
    data['pk']          = {'S' : 'Test Module'}
    data['sk']          = {'S' : 'stark_user_sessions|info'}
    data['Username']    = {'S' : ''}
    data['Sess_Start']  = {'S' : ''}
    data['TTL']         = {'N' : ''}
    data['Permissions'] = {'S' : ''}
    return data

def set_payload_sequence():
    payload = {}
    payload['pk']                = 'C-000001'
    payload['orig_pk']           = 'C-000001'
    payload['sk']                = 'stark_user_sessions|info'
    payload['Username']          = ''
    payload['Sess_Start']        = ''
    payload['TTL']               = ''
    payload['Permissions']       = ''
    payload['STARK-ListView-sk'] = 'Test Module2'
    return payload

def set_payload():
    payload = {}
    payload['pk']                     = 'Test2'
    payload['orig_pk']                = 'Test2'
    payload['sk']                     = 'stark_user_sessions|info'
    payload['Username']               = ''
    payload['Sess_Start']             = ''
    payload['TTL']                    = ''
    payload['Permissions']            = ''
    payload['STARK-ListView-sk']      = 'Test2'
    payload['STARK_uploaded_s3_keys'] = {}
    return payload

def get_raw_payload():
    raw_payload = {
        "STARK_User_Sessions": {
            'Session_ID'      : 'Test2',
            'orig_Session_ID' : 'Test2',
            'Username'        : '',
            'Sess_Start'      : '',
            'TTL'             : '',
            'Permissions'     : '',
            'sk'              : 'stark_user_sessions|info',
        }
    }
    return raw_payload

def get_raw_report_payload():
    raw_payload = {
        "STARK_User_Sessions": {
            'Session_ID'         : {'operator': "=",'type': "S",'value': "Hello"},
            'Username'           : {'operator': "",'type': "",'value': ""},
            'Sess_Start'         : {'operator': "",'type': "",'value': ""},
            'TTL'                : {'operator': "",'type': "",'value': ""},
            'Permissions'        : {'operator': "",'type': "",'value': ""},
            'STARK_Chart_Type'   : "",
            'STARK_Report_Type'  : "Tabular",
            'STARK_X_Data_Source': "",
            'STARK_Y_Data_Source': "",
            'STARK_count_fields' : [],
            'STARK_group_by_1'   : "",
            'STARK_isReport'     : True,
            'STARK_report_fields': ["Session_ID", "Permissions"],
            'STARK_sum_fields'   : []
        }
    }
    return raw_payload


