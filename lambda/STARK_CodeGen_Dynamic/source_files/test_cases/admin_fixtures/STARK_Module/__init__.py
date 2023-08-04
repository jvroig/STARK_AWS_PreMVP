def get_data():
    data = {}
    data['pk'] = {'S' : 'Test Module'}
    data['sk'] = {'S' : 'stark_module|info'}
    data['Descriptive_Title'] = {'S' : 'Sample_Descriptive_Title'}
    data['Target'] = {'S' : 'sample_target.html'}
    data['Description'] = {'S' : 'Sample Description'}
    data['Module_Group'] = {'S' : 'Test Module Group'}
    data['Is_Menu_Item'] = {'BOOL' : False}
    data['Is_Enabled'] = {'BOOL' : False}
    data['Icon'] = {'S' : 'images/tag.svg'}
    data['Priority'] = {'N' : '1'}
    return data

def set_payload_sequence():
    payload = {}
    payload['pk']                = 'C-000001'
    payload['orig_pk']           = 'C-000001'
    payload['sk']                = 'stark_module|info'
    payload['Descriptive_Title'] = 'Sample_Descriptive_Title seq'
    payload['Target']            = 'sample_target.html'
    payload['Description']       = 'Sample Description'
    payload['Module_Group']      = 'Test Module Group'
    payload['Is_Menu_Item']      = False
    payload['Is_Enabled']        = False
    payload['Icon']              = 'images/tag.svg'
    payload['Priority']          = '1'
    payload['STARK-ListView-sk'] = 'Test Module2'
    return payload

def set_payload():
    payload = {}
    payload['pk']                           = 'Test2'
    payload['orig_pk']                      = 'Test2'
    payload['sk']                           = 'stark_module|info'
    payload['Descriptive_Title']            = 'Sample_Descriptive_Title'
    payload['Target']                       = 'sample_target.html'
    payload['Description']                  = 'Sample Description'
    payload['Module_Group']                 = 'Test Module Group'
    payload['Is_Menu_Item']                 = False
    payload['Is_Enabled']                   = False
    payload['Icon']                         = 'images/tag.svg'
    payload['Priority']                     = '1'
    payload['STARK-ListView-sk']            = 'Test2'
    payload['STARK_uploaded_s3_keys']       = {}
    return payload

def get_raw_payload():
    raw_payload = {
        "STARK_Module": {
           'Module_Name'        : 'Test2',
           'orig_Module_Name'   : 'Test2',
           'Descriptive_Title'  : 'Sample_Descriptive_Title',
           'Target'             : 'sample_target.html',
           'Description'        : 'Sample Description',
           'Module_Group'       : 'Test Module Group',
           'Is_Menu_Item'       : False,
           'Is_Enabled'         : False,
           'Icon'               : 'images/tag.svg',
           'Priority'           : '1',
           'sk'                 : 'stark_module|info',
        }
    }
    return raw_payload

def get_raw_report_payload():
    raw_payload = {
        "STARK_Module": {
            'Module_Name'        : {'operator': "=",'type': "S",'value': "Hello"},
            'Descriptive_Title'  : {'operator': "",'type': "S",'value': ""},
            'Target'             : {'operator': "",'type': "S",'value': ""},
            'Description'        : {'operator': "",'type': "S",'value': ""},
            'Module_Group'       : {'operator': "",'type': "S",'value': ""},
            'Is_Menu_Item'       : {'operator': "",'type': "S",'value': ""},
            'Is_Enabled'         : {'operator': "",'type': "S",'value': ""},
            'Icon'               : {'operator': "",'type': "S",'value': ""},
            'Priority'           : {'operator': "",'type': "S",'value': ""},
            'STARK_Chart_Type'   : "",
            'STARK_Report_Type'  : "Tabular",
            'STARK_X_Data_Source': "",
            'STARK_Y_Data_Source': "",
            'STARK_count_fields' : [],
            'STARK_group_by_1'   : "",
            'STARK_isReport'     : True,
            'STARK_report_fields': ["Module_Name", "Descriptive_Title", "Module_Group", 'Target'],
            'STARK_sum_fields'   : []
        }
    }
    return raw_payload


