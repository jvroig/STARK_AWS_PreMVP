def get_data():
    data = {}
    data['pk']            = {'S' : 'Test Module'}
    data['sk']            = {'S' : 'stark_user|info'}
    data['Full_Name']     = {'S' : 'Test Full name'}
    data['Nickname']      = {'S' : ''}
    data['Password_Hash'] = {'S' : ''}
    data['Role']          = {'S' : 'Admin'}
    return data

def set_payload_sequence():
    payload = {}
    payload['pk']                = 'C-000001'
    payload['orig_pk']           = 'C-000001'
    payload['sk']                = 'stark_user|info'
    payload['Full_Name']         = 'Test Full name'
    payload['Nickname']          = ''
    payload['Password_Hash']     = ''
    payload['Role']              = 'Admin'
    payload['STARK-ListView-sk'] = 'Test Module2'
    return payload

def set_payload():
    payload = {}
    payload['pk']                     = 'Test2'
    payload['orig_pk']                = 'Test2'
    payload['sk']                     = 'stark_user|info'
    payload['Full_Name']              = 'Test Full name'
    payload['Nickname']               = ''
    payload['Password_Hash']          = ''
    payload['Role']                   = 'Admin'
    payload['STARK-ListView-sk']      = 'Test2'
    payload['STARK_uploaded_s3_keys'] = {}
    return payload

def get_raw_payload():
    raw_payload = {
        "STARK_User": {
           'Username'        : 'Test2',
           'orig_Username'   : 'Test2',
           'Full_Name'          : 'Test Full name',
           'Nickname'           : '',
           'Password_Hash'      : '',
           'Role'               : 'Admin',
           'sk'                 : 'stark_user|info',
        }
    }
    return raw_payload

def get_raw_report_payload():
    raw_payload = {
        "STARK_User": {
            'Username'           : {'operator': "=",'type': "S",'value': "Hello"},
            'Full_Name'          : {'operator': "",'type': "S",'value': ""},
            'Nickname'           : {'operator': "",'type': "S",'value': ""},
            'Password_Hash'      : {'operator': "",'type': "S",'value': ""},
            'Role'               : {'operator': "",'type': "S",'value': ""},
            'STARK_Chart_Type'   : "",
            'STARK_Report_Type'  : "Tabular",
            'STARK_X_Data_Source': "",
            'STARK_Y_Data_Source': "",
            'STARK_count_fields' : [],
            'STARK_group_by_1'   : "",
            'STARK_isReport'     : True,
            'STARK_report_fields': ["Username", "Full_Name", "Role"],
            'STARK_sum_fields'   : []
        }
    }
    return raw_payload


