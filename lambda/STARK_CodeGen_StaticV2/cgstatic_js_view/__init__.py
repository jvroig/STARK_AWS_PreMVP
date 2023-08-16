#STARK Code Generator component.
#Produces the customized static content for a STARK system

#Python Standard Library
import textwrap
import os
import importlib
from wsgiref import validate

#Private modules
prepend_dir = ""
if 'libstark' in os.listdir():
    prepend_dir = "libstark.STARK_CodeGen_Static."

cg_coltype = importlib.import_module(f"{prepend_dir}cgstatic_controls_coltype")  
import convert_friendly_to_system as converter

def create(data):
    print('data')
    print(data)
    entity         = data["Entity"]
    cols           = data["Columns"]
    pk             = data['PK']
    relationships  = data["Relationships"]
    rel_model      = data["Rel Model"]
    sequence       = data["Sequence"]

    entity_varname = converter.convert_to_system_name(entity)
    entity_app     = entity_varname + '_app'
    pk_varname     = converter.convert_to_system_name(pk)

    #file upload controls
    with_upload         = False
    with_upload_on_many = False
    ext_string          = ""
    allowed_size_string = ""
    upload_elems_string = ""
    
    for rel in rel_model:
        rel_cols = rel_model[rel]["data"]
        for rel_col, rel_col_type in rel_cols.items():
            if isinstance(rel_col_type, dict):
                if rel_col_type["type"] == 'file-upload': 
                    with_upload_on_many = True

    source_code = f"""\
        var root = new Vue({{
            el: "#vue-root",
            data: {{
                metadata: {{
                    '{pk_varname}': {{
                        'value': '',"""
    if len(sequence) > 0:
        required = "false"
    else:
        required = "true"
        
    source_code += f"""
                        'required': {required},"""
    source_code += f"""                
                        'max_length': '',
                        'data_type': 'String'
                    }},"""
    
    for col, col_type in cols.items():
        col_varname = converter.convert_to_system_name(col)
        data_type = set_data_type(col_type)
        if isinstance(col_type, dict) and col_type["type"] == "relationship":
            has_many_ux = col_type.get('has_many_ux', None)
            if has_many_ux == None:
                source_code += f"""
                    '{col_varname}': {{
                        'value': '',
                        'required': true,
                        'max_length': '',
                        'data_type': '{data_type}'
                    }},""" 
        else:
            source_code += f"""
                    '{col_varname}': {{
                        'value': '',
                        'required': true,
                        'max_length': '',
                        'data_type': '{data_type}'
                    }},""" 
    
    for rel_ent in rel_model:
        rel_cols = rel_model[rel_ent]["data"]
        rel_pk = rel_model[rel_ent]["pk"]
        var_pk = rel_ent.replace(' ', '_') + '_' + rel_pk.replace(' ', '_')
        source_code += f"""
                    '{var_pk}': {{
                        'value': '',
                        'required': false,
                        'max_length': '',
                        'data_type': '',
                    }},""" 
        for rel_col, rel_col_type in rel_cols.items():
            var_data = rel_ent.replace(' ', '_') + '_' + rel_col.replace(' ', '_')
            source_code += f"""
                    '{var_data}': {{
                        'value': '',
                        'required': false,
                        'max_length': '',
                        'data_type': '',
                    }},"""
                    
    source_code += f"""
                    'STARK_Report_Type': {{
                        'value': '',
                        'required': true,
                        'max_length': '',
                        'data_type': 'String'
                    }},
                    'STARK_Chart_Type': {{
                        'value': '',
                        'required': true,
                        'max_length': '',
                        'data_type': 'String'
                    }},
                    'STARK_X_Data_Source': {{
                        'value': '',
                        'required': true,
                        'max_length': '',
                        'data_type': 'String'
                    }},
                    'STARK_Y_Data_Source': {{
                        'value': '',
                        'required': true,
                        'max_length': '',
                        'data_type': 'String'
                    }},
                }},

                validation_properties: {{
                    '{pk_varname}': {{
                        'state': null,
                        'feedback': ''
                    }},"""
    
    for col, col_type in cols.items():
        col_varname = converter.convert_to_system_name(col)
        data_type = set_data_type(col_type)
        if isinstance(col_type, dict) and col_type["type"] == "relationship":
            has_many_ux = col_type.get('has_many_ux', None)
            if has_many_ux == None:
                source_code += f"""
                    '{col_varname}': {{
                        'state': null,
                        'feedback': ''
                    }},""" 
        else:
            source_code += f"""
                    '{col_varname}': {{
                        'state': null,
                        'feedback': ''
                    }},""" 
                    
    source_code += f"""
                    'STARK_Report_Type': {{
                        'state': null,
                        'feedback': ''
                    }},
                    'STARK_Chart_Type': {{
                        'state': null,
                        'feedback': ''
                    }},
                    'STARK_X_Data_Source': {{
                        'state': null,
                        'feedback': ''
                    }},
                    'STARK_Y_Data_Source': {{
                        'state': null,
                        'feedback': ''
                    }},
                }},

                auth_config: {{ }},

                auth_list: {{
                    'View': {{'permission': '{entity}|View', 'allowed': false}},
                    'Add': {{'permission': '{entity}|Add', 'allowed': false}},
                    'Delete': {{'permission': '{entity}|Delete', 'allowed': false}},
                    'Edit': {{'permission': '{entity}|Edit', 'allowed': false}},
                    'Report': {{'permission': '{entity}|Report', 'allowed': false}}
                }},

                listview_table: '',
                STARK_report_fields: [],
                {entity_varname}: {{
                    '{pk_varname}': '',
                    'sk': '',"""

    for col in cols:
        col_varname = converter.convert_to_system_name(col)
        source_code += f"""
                    '{col_varname}': '',""" 

    source_code += f"""
                    'STARK_uploaded_s3_keys':{{}}
                }},
                custom_report:{{
                    '{pk_varname}': {{"operator": "", "value": "", "type":"S"}},"""
    for col, col_type in cols.items():
        col_varname = converter.convert_to_system_name(col)
        col_type_id = set_type(col_type)
        source_code += f"""
                    '{col_varname}':  {{"operator": "", "value": "", "type":"{col_type_id}"}},""" 

    for rel_ent in rel_model:
        rel_cols = rel_model[rel_ent]["data"]
        rel_pk = rel_model[rel_ent]["pk"]
        var_pk = rel_ent.replace(' ', '_') + '_' + rel_pk.replace(' ', '_')
        source_code += f"""
                    '{var_pk}':  {{"operator": "", "value": "", "type":"S"}},"""
        for rel_col, rel_col_type in rel_cols.items():
            var_data = rel_ent.replace(' ', '_') + '_' + rel_col.replace(' ', '_')
            source_code += f"""
                    '{var_data}':  {{"operator": "", "value": "", "type":"S"}},"""

    source_code += f"""
                    'STARK_isReport':true,
                    'STARK_report_fields':[],
                    'STARK_Report_Type': '',
                    'STARK_Chart_Type': '',
                    'STARK_X_Data_Source': '',
                    'STARK_Y_Data_Source': '',
                    'STARK_sum_fields': [],
                    'STARK_count_fields': [],
                    'STARK_group_by_1': '',
                }},
                lists: {{
                    'Report_Operator': [
                        {{ value: '', text: '' }},
                        {{ value: '=', text: 'EQUAL TO (=)' }},
                        {{ value: '<>', text: 'NOT EQUAL TO (!=)' }},
                        {{ value: '<', text: 'LESS THAN (<)' }},
                        {{ value: '<=', text: 'LESS THAN OR EQUAL TO (<=)' }},
                        {{ value: '>', text: 'GREATER THAN (>)' }},
                        {{ value: '>=', text: 'GREATER THAN OR EQUAL TO (>=)' }},
                        {{ value: 'contains', text: 'CONTAINS (%..%)' }},
                        {{ value: 'begins_with', text: 'BEGINS WITH (..%)' }},
                        {{ value: 'IN', text: 'IN (value1, value2, value3, ... valueN)' }},
                        {{ value: 'between', text: 'BETWEEN (value1, value2)' }},
                    ],
                    'STARK_Chart_Type': [
                        {{ value: 'Bar Chart', text: 'Bar Chart' }},
                        {{ value: 'Pie Chart', text: 'Pie Chart' }},
                        {{ value: 'Line Chart', text: 'Line Chart' }},
                    ],
                    'STARK_Report_Type': [
                        {{ value: 'Tabular', text: 'Tabular' }},
                        {{ value: 'Graph', text: 'Graph' }},
                    ],
                    'STARK_Data_Source': [

                    ],"""

    for rel in rel_model:
        rel_cols = rel_model[rel]["data"]
        for col, col_type in rel_cols.items():
            if isinstance(col_type, dict) and col_type["type"] == "relationship":
                has_one = col_type.get('has_one', '')
                if has_one != '':
                    source_code += f"""
                    '{has_one}': [
                    ],"""
        
                    

    for col, col_type in cols.items():
        col_varname = converter.convert_to_system_name(col)
        js_list_code = cg_coltype.create_list({
            "col": col,
            "col_type": col_type,
            "col_varname": col_varname
        })

        if js_list_code != None:
            source_code += f"""
                    {js_list_code}"""

    source_code += f"""
                }},
                list_status: {{"""

    #FIXME: These kinds of logic (determining col types, lists, retreiving settings, etc) are repetitive, should be refactored shipped to a central lib
    for col, col_type in cols.items():
        if isinstance(col_type, dict) and col_type["type"] == "relationship":
            has_one = col_type.get('has_one', '')
            has_many = col_type.get('has_many', '')
            has_many_ux = col_type.get('has_many_ux', '')
            if  has_one != '' or has_many != '':
                if has_many_ux == '':
                #simple 1-1 relationship
                    col_varname = converter.convert_to_system_name(col)

                    source_code += f"""
                    '{col_varname}': 'empty',"""



    source_code += f"""
                }},
                multi_select_values: {{"""

    #FIXME: These kinds of logic (determining col types, lists, retreiving settings, etc) are repetitive, should be refactored shipped to a central lib
    for col, col_type in cols.items():
        if isinstance(col_type, dict):
            col_varname = converter.convert_to_system_name(col)
            col_values = col_type.get("values", "")
            if col_type["type"] == "relationship":
                has_many = col_type.get('has_many', '')
                has_many_ux = col_type.get('has_many_ux', '')
                if  has_many != '':
                    if has_many_ux == '':
                        source_code += f"""
                        '{col_varname}': [],"""
            elif isinstance(col_values, list):
                    source_code += f"""
                        '{col_varname}': [],"""
                
    source_code += f"""

                }},
                visibility: 'hidden',
                next_token: '',
                next_disabled: true,
                prev_token: '',
                prev_disabled: true,
                page_token_map: {{1: ''}},
                curr_page: 1,
                showReport: false,
                object_url_prefix: "",
                temp_csv_link: "",
                temp_pdf_link: "",
                showError: false,
                no_operator: [],
                error_message: '',
                authFailure: false,
                authTry: false,
                all_selected: true,"""
    field_strings = f"['{pk}',"
    for col, col_type in cols.items():
        if isinstance(col_type, dict) and col_type["type"] == "relationship":
            has_many_ux = col_type.get('has_many_ux', None)
            if has_many_ux == None:
                field_strings += f"""'{col}',"""
        else:
            field_strings += f"""'{col}',"""

    for rel_ent in rel_model:
        rel_cols = rel_model[rel_ent]["data"]
        rel_pk = rel_model[rel_ent]["pk"]
        var_pk = rel_ent.replace(' ', '_') + '_' + rel_pk.replace(' ', '_')
        field_strings += f"""'{var_pk.replace('_', ' ')}',"""
        for rel_col, rel_col_type in rel_cols.items():
            var_data = rel_ent.replace(' ', '_') + '_' + rel_col.replace(' ', '_')
            field_strings += f"""'{var_data.replace('_', ' ')}',"""

    field_strings += f"""]"""
    source_code += f"""
                temp_checked_fields: {field_strings},
                checked_fields: {field_strings},"""
                
    search_string       = ""
    for col, col_type in cols.items():
        col_varname = converter.convert_to_system_name(col)
        if isinstance(col_type, dict):
            col_values = col_type.get("values", "")
            if col_type["type"] == "relationship" or isinstance(col_values, list):
                has_many = col_type.get('has_many', '')
                search_string += f"""
                    {col_varname}: '',"""
            if col_type["type"] == 'file-upload': 
                with_upload = True 
                ext_string += f"""
                         "{col_varname}": {col_type.get("allowed_ext",[])},"""
                allowed_size = col_type.get("max_upload_size", 1)
                allowed_size_string += f"""
                         "{col_varname}": {float(allowed_size)},"""
                upload_elems_string += f"""
                        "{col_varname}": {{"file": '', "progress_bar_val": 0, "tmp_location": ""}},"""
    if with_upload or with_upload_on_many:
        source_code += f"""
                s3_access: "","""
    if with_upload:
        source_code += f"""
                STARK_upload_elements: {{{upload_elems_string}
                }},
                ext_whitelist: {{{ext_string}
                }},
                allowed_size: {{{allowed_size_string}
                }},
                ext_whitelist_table: "",
                allowed_size_table: 0,"""
    source_code += f"""
                search:{{{search_string}
                }},
                showGraph: false,
                showChartFields: false,
                showXAxisFields: false,
                series_data: [],
                graphOption: [],
                fieldLabel: '',
                STARK_sum_fields: [],
                STARK_count_fields: [],
                STARK_group_by_1: '',
                Y_Data: [],
                showOperations: true,
                many_entity: {{"""
            
    if relationships.get('has_many', '') != '':
        for relation in relationships.get('has_many'):
            if relation.get('type') == 'repeater':
                many_entity = relation.get('entity')
                many_entity_varname = converter.convert_to_system_name(many_entity)
                source_code += f"""    
                    '{many_entity_varname}': many_{many_entity_varname},"""
    
    source_code += f"""
                }},
            }},
            methods: {{

    
                show: function () {{
                    this.visibility = 'visible';
                }},

                hide: function () {{
                    this.visibility = 'hidden';
                }},

                add: function () {{
                    console.log("VIEW: Inserting!")"""
    for col, col_type in cols.items():
        col_varname = converter.convert_to_system_name(col)
        if isinstance(col_type, dict) and col_type["type"] == "relationship":
            has_many = col_type.get('has_many', '')
            has_many_ux = col_type.get('has_many_ux', '')
            if has_many != "" and has_many_ux != 'repeater':
                source_code += f"""
                    this.{entity_varname}.{col_varname} = (root.multi_select_values.{col_varname}.sort()).join(', ')"""
    
    source_code += f"""
                    response = STARK.validate_form(root.metadata, root.{entity_varname}""" 
    if with_upload:
        source_code += f", root.STARK_upload_elements"

    source_code += f""")
                    this.validation_properties = response['validation_properties']"""
    validation = ''
    for col, col_type in cols.items():
        if isinstance(col_type, dict):
            col_varname = converter.convert_to_system_name(col)
            col_values = col_type.get("values", "")
            has_many_ux = col_type.get('has_many_ux', '')
            if col_type["type"] == "relationship":
                has_many = col_type.get('has_many', '')
                if has_many != '':
                    if has_many_ux == 'repeater':
                        source_code += f"""
                    many_{col_varname}_validation = many_{col_varname}.many_validation()"""
                        validation += f" && many_{col_varname}_validation"
                        
    source_code += f"""
                    if(response['is_valid_form']{validation}) {{
                        loading_modal.show()"""
    for col, col_type in cols.items():
        if isinstance(col_type, dict):
            col_varname = converter.convert_to_system_name(col)
            col_values = col_type.get("values", "")
            has_many_ux = col_type.get('has_many_ux', '')
            if col_type["type"] == "relationship":
                has_many = col_type.get('has_many', '')
                if has_many != '':
                    if has_many_ux == 'repeater':
                        source_code += f"""
                        this.{entity_varname}.{col_varname} = JSON.stringify(root.many_entity.{col_varname}.module_fields)"""

                    if with_upload_on_many:
                        source_code += f"""
                        for (const key in root.many_entity) {{
                            if (Object.hasOwnProperty.call(root.many_entity, key)) {{
                                var element = root.many_entity[key];
                                this.{entity_varname}.STARK_uploaded_s3_keys[`many_${{key}}`] = element.STARK_uploaded_s3_keys
                            }}
                        }}"""
                        
    source_code += f"""    
                        let data = {{ {entity_varname}: this.{entity_varname} }}

                        {entity_app}.add(data).then( function(data) {{
                            loading_modal.hide()
                            if(data != "OK")
                            {{
                                for (var key in data) {{
                                    if (data.hasOwnProperty(key)) {{
                                        root.validation_properties[key]['state'] = false
                                        root.validation_properties[key]['feedback'] = data[key]
                                    }}
                                }}
                                return false
                            }}
                            console.log("VIEW: INSERTING DONE!");
                            STARK.local_storage_delete_key('Listviews', '{entity_varname}');
                            root.refresh_child()
                            window.location.href = "{entity_varname}.html";
                        }}).catch(function(error) {{
                            console.log("Encountered an error! [" + error + "]")
                            alert("Request Failed: System error or you may not have enough privileges")
                            loading_modal.hide()
                        }});
                    }}
                }},

                delete: function () {{
                    loading_modal.show()
                    console.log("VIEW: Deleting!")

                    let data = {{ {entity_varname}: this.{entity_varname} }}

                    {entity_app}.delete(data).then( function(data) {{
                        console.log("VIEW: DELETE DONE!");
                        STARK.local_storage_delete_key('Listviews', '{entity_varname}');
                        root.refresh_child()
                        loading_modal.hide()
                        window.location.href = "{entity_varname}.html";
                    }})
                    .catch(function(error) {{
                        console.log("Encountered an error! [" + error + "]")
                        alert("Request Failed: System error or you may not have enough privileges")
                        loading_modal.hide()
                    }});
                }},

                update: function () {{
                    console.log("VIEW: Updating!")"""
    for col, col_type in cols.items():
        col_varname = converter.convert_to_system_name(col)
        if isinstance(col_type, dict) and col_type["type"] == "relationship":
            has_many = col_type.get('has_many', '')
            has_many_ux = col_type.get('has_many_ux', '')
            if has_many != "":
                if has_many_ux == '':
                    source_code += f"""
                    this.{entity_varname}.{col_varname} = (root.multi_select_values.{col_varname}.sort()).join(', ')"""
    
    source_code += f"""
                    response = STARK.validate_form(root.metadata, root.{entity_varname}""" 
    if with_upload:
        source_code += f", root.STARK_upload_elements"

    source_code += f""")
                    this.validation_properties = response['validation_properties']"""
    validation = ''
    for col, col_type in cols.items():
        if isinstance(col_type, dict):
            col_varname = converter.convert_to_system_name(col)
            col_values = col_type.get("values", "")
            has_many_ux = col_type.get('has_many_ux', '')
            if col_type["type"] == "relationship":
                has_many = col_type.get('has_many', '')
                if has_many != '':
                    if has_many_ux == 'repeater':
                        source_code += f"""
                    many_{col_varname}_validation = many_{col_varname}.many_validation()"""
                        validation += f" && many_{col_varname}_validation"  
                        
    source_code += f"""
                    if(response['is_valid_form']{validation}) {{
                        loading_modal.show()"""
    for col, col_type in cols.items():
        if isinstance(col_type, dict):
            col_varname = converter.convert_to_system_name(col)
            col_values = col_type.get("values", "")
            has_many_ux = col_type.get('has_many_ux', '')
            if col_type["type"] == "relationship":
                has_many = col_type.get('has_many', '')
                if has_many != '':
                    if has_many_ux == 'repeater':
                        # print(has_many)
                        source_code += f"""
                        this.{entity_varname}.{col_varname} = JSON.stringify(root.many_entity.{col_varname}.module_fields)"""

    source_code += f"""
                        let data = {{ {entity_varname}: this.{entity_varname} }}

                        {entity_app}.update(data).then( function(data) {{
                            loading_modal.hide()
                            if(data != "OK")
                            {{
                                for (var key in data) {{
                                    if (data.hasOwnProperty(key)) {{
                                        root.validation_properties[key]['state'] = false
                                        root.validation_properties[key]['feedback'] = data[key]
                                    }}
                                }}
                                return false
                            }}
                            console.log("VIEW: UPDATING DONE!");
                            STARK.local_storage_delete_key('Listviews', '{entity_varname}');
                            root.refresh_child()
                            window.location.href = "{entity_varname}.html";
                        }})
                        .catch(function(error) {{
                            console.log("Encountered an error! [" + error + "]")
                            alert("Request Failed: System error or you may not have enough privileges")
                            loading_modal.hide()
                        }});
                    }}
                }},

                get: function () {{
                    const queryString = window.location.search;
                    const urlParams = new URLSearchParams(queryString);
                    //Get whatever params are needed here (pk, sk, filters...)
                    data = {{}}
                    data['{pk_varname}'] = urlParams.get('{pk_varname}');

                    if(data['{pk_varname}'] == null) {{
                        root.show();
                        for (const key in root.many_entity) {{
                            if (Object.hasOwnProperty.call(root.many_entity, key)) {{
                                var element = root.many_entity[key];
                                element.add_row()
                            }}
                        }}
                    }}
                    else {{
                        loading_modal.show();
                        console.log("VIEW: Getting!")

                        {entity_app}.get(data).then( function(data) {{
                            root.{entity_varname} = data["item"];"""
    if with_upload or with_upload_on_many:
        source_code += f"""
                            root.object_url_prefix = data['object_url_prefix']"""
    source_code += f"""
                            root.{entity_varname}.orig_{pk_varname} = root.{entity_varname}.{pk_varname};"""
    for col, col_type in cols.items():
        col_varname = converter.convert_to_system_name(col)
        if isinstance(col_type, dict) and col_type['type'] == 'file-upload':
            source_code += f"""
                            root.{entity_varname}.STARK_uploaded_s3_keys['{col_varname}'] = root.{entity_varname}.{col_varname} != "" ? root.{entity_varname}.STARK_uploaded_s3_keys.{col_varname} : ""
                            root.{entity_varname}.orig_STARK_uploaded_s3_keys = structuredClone(Object.fromEntries(Object.entries(data["item"]['STARK_uploaded_s3_keys'])))
                            root.STARK_upload_elements['{col_varname}'].file = root.{entity_varname}.{col_varname} != "" ? root.{entity_varname}.{col_varname} : ""
                            root.STARK_upload_elements['{col_varname}'].progress_bar_val = root.{entity_varname}.{col_varname} != "" ? 100 : 0
                            root.STARK_upload_elements['{col_varname}'].tmp_location = `https://${{root.object_url_prefix}}${{root.{entity_varname}.STARK_uploaded_s3_keys.{col_varname}}}`
                            
                            """

    #If there are 1:1 rel fields, we need to assign their initial value to the still-unpopulated drop-down list so that it displays 
    #   a value even before the lazy-loading is triggered.
    for col, col_type in cols.items():
        if isinstance(col_type, dict) and col_type["type"] == "relationship":
            has_one = col_type.get('has_one', '')
            has_many = col_type.get('has_many', '')
            has_many_ux = col_type.get('has_many_ux', '')
            
            foreign_entity  = converter.convert_to_system_name(has_one if has_one != '' else has_many)
            foreign_field   = converter.convert_to_system_name(col_type.get('value', foreign_entity))
            # foreign_display = converter.convert_to_system_name(col_type.get('display', foreign_field))

            if  has_one != '':
                #simple 1-1 relationship
                source_code += f"""
                            root.lists.{foreign_field} = [  {{ value: root.{entity_varname}.{foreign_field}, text: root.{entity_varname}.{foreign_field} }},]
                            root.list_{foreign_entity}()"""
            
            elif has_many != "" and has_many_ux != 'repeater':
                source_code += f"""
                            root.multi_select_values.{foreign_entity} = root.{entity_varname}.{foreign_entity}.split(', ')
                            root.list_{foreign_entity}()"""

    for rel, rel_data in rel_model.items():
        col_varname = converter.convert_to_system_name(rel)
        source_code += f"""
                            if(data["{col_varname}"].length > 0) {{"""
        if with_upload_on_many:
            source_code += f"""
                                root.many_entity.{col_varname}.STARK_uploaded_s3_keys = root.{entity_varname}.STARK_uploaded_s3_keys['many_{col_varname}']"""
        source_code += f"""
                                var many_object = JSON.parse(data["{col_varname}"])
                                many_object.forEach(element => {{
                                    root.many_entity.{col_varname}.add_row(element)
                                }});
                            }}"""
        for col, col_type in rel_data.get('data').items():
            if isinstance(col_type, dict) and col_type["type"] == "relationship":
                rel_foreign_entity = converter.convert_to_system_name(col)
                source_code += f"""
                            root.many_entity.{col_varname}.list_{rel_foreign_entity}()"""
    
    source_code += f"""
                            console.log("VIEW: Retreived module data.")
                            root.show()
                            loading_modal.hide()
                        }})
                        .catch(function(error) {{
                            console.log("Encountered an error! [" + error + "]")
                            alert("Request Failed: System error or you may not have enough privileges")
                            loading_modal.hide()
                        }});
                    }}
                }},

               list: function (lv_token='', btn='') {{
                    spinner.show()
                    
                    payload = []
                    if (btn == 'next') {{
                        root.curr_page++;
                        console.log(root.curr_page);
                        payload['Next_Token'] = lv_token;
                        root.prev_disabled = false;    
                        root.next_disabled = true;
                    }}
                    else if (btn == "prev") {{
                        root.curr_page--;
                        if (root.curr_page > 1) {{
                            root.prev_disabled = false
                        }}
                        else {{
                            root.prev_disabled = true
                            root.prev_token = ""
                        }}
                    }}

                    var listview_data = STARK.get_local_storage_item('Listviews', '{entity_varname}')
                    var fetch_from_db = false;
                    
                    if(listview_data) {{
                        root.listview_table = listview_data[root.curr_page]
                        root.next_token = listview_data['next_token'];
                
                        if(listview_data[root.curr_page + 1]) {{
                            root.next_disabled = false
                        }}
                        if(root.next_token != "null") {{
                            fetch_from_db = true
                        }}
                        
                        spinner.hide()
                    }}
                    else {{
                        fetch_from_db = true
                    }}
                    
                    if(fetch_from_db) {{
                        {entity_app}.list(payload).then( function(data) {{"""

    for col, col_type in cols.items():
        col_varname = converter.convert_to_system_name(col)
        if isinstance(col_type, dict) and col_type["type"] == "relationship":
            has_many = col_type.get('has_many', '')
            has_many_ux = col_type.get('has_many_ux', '')
            if has_many != "" and has_many_ux != 'repeater':
                foreign_entity  = converter.convert_to_system_name(has_many)
                source_code += f"""
                            for (let x = 0; x < (data['Items']).length; x++) {{
                                data['Items'][x]['{foreign_entity}'] = ((data['Items'][x]['{foreign_entity}'].split(', ')).sort()).join(', ')      
                            }}
                """
                        
    source_code += f"""
                            token = data['Next_Token'];
                            root.listview_table = data['Items'];
                            var data_to_store = {{}}
                            data_to_store[root.curr_page] = data['Items']
                            data_to_store['next_token'] = token
                            STARK.set_local_storage_item('Listviews', '{entity_varname}', data_to_store)
                            console.log("DONE! Retrieved list.");
                            spinner.hide()

                            if (token != "null") {{
                                root.next_disabled = false;
                                root.next_token = token;
                            }}
                            else {{
                                root.next_disabled = true;
                            }}

                        }})
                        .catch(function(error) {{
                            console.log("Encountered an error! [" + error + "]")
                            alert("Request Failed: System error or you may not have enough privileges")
                            spinner.hide()
                        }});
                    }}
                }},

                formValidation: function () {{
                    root.error_message = ""
                    let no_operator = []
                    let isValid = true;
                    root.showError = false
                    for (element in root.custom_report) {{
                        if(root.custom_report[element].value != '' && root.custom_report[element].operator == '')
                        {{
                            root.showError = true
                            //fetch all error
                            if(root.custom_report[element].operator == '')
                            {{
                                isValid = false
                                no_operator.push(element.replace('_', ' '))
                            }}
                        }}
                    }}
                    root.no_operator = no_operator;
                    //display error
                    root.error_message = "Put operator/s on: " + no_operator ;
                    return isValid
                }},

                generate: function () {{
                    if(root.custom_report.STARK_Report_Type == 'Tabular') {{
                        root.metadata['STARK_Chart_Type'].required = false
                        root.metadata['STARK_X_Data_Source'].required = false
                        root.metadata['STARK_Y_Data_Source'].required = false
                        if(root.custom_report.STARK_group_by_1 != '')
                        {{
                            root.showOperations = false
                        }}
                    }}
                    else {{
                        root.metadata['STARK_Chart_Type'].required = true
                        root.metadata['STARK_X_Data_Source'].required = true
                        root.metadata['STARK_Y_Data_Source'].required = true
                    }}
                    response = STARK.validate_form(root.metadata, root.custom_report)
                    this.validation_properties = response['validation_properties']
                    // console.log(response['is_valid_form'])
                    if(response['is_valid_form']) {{
                        if(root.custom_report.STARK_Report_Type == 'Graph') {{
                            root.showGraph = true
                        }}

                        root.custom_report['STARK_report_fields'] = root.checked_fields"""
    for col, col_type in cols.items():
        col_varname = converter.convert_to_system_name(col)
        if isinstance(col_type, dict):
            col_values = col_type.get("values", "")
            if isinstance(col_values, list):
                source_code += f"""
                        root.custom_report['{col_varname}']['value'] = root.custom_report['{col_varname}']['value'] == "" ? root.multi_select_values['{col_varname}'].join(', '): root.custom_report['{col_varname}']['value']"""
    source_code += f"""
                        let report_payload = {{ {entity_varname}: root.custom_report }}
                        if(root.formValidation())
                        {{
                            loading_modal.show()
                            {entity_app}.report(report_payload).then( function(data) {{
                                root.listview_table = data[0];
                                if(root.listview_table.length > 0) {{
                                    if(root.custom_report.STARK_Report_Type == 'Tabular') {{
                                        if(root.custom_report.STARK_group_by_1 != '')
                                        {{
                                            root.STARK_report_fields = Object.keys(root.listview_table[0])
                                        }}
                                        else {{
                                            root.STARK_report_fields = root.checked_fields 
                                        }}
                                        root.temp_csv_link = data[1];
                                        root.temp_pdf_link = data[2];
                                    }} else {{
                                        root.STARK_report_fields = Object.keys(root.listview_table[0])
                                    }}
                                }}
                                console.log("DONE! Retrieved report.");
                                loading_modal.hide()
                                if(root.custom_report.STARK_Report_Type == 'Tabular') {{
                                    root.showReport = true
                                }}
                                else {{
                                    if(root.listview_table.length > 0)
                                    {{   
                                        var element = document.getElementById("chart-container");
                                        element.style.backgroundColor = "#ffffff";
                                        root.activate_graph_download()
                                        X_Data = root.custom_report.STARK_X_Data_Source
                                        Y_Data = root.custom_report.STARK_Y_Data_Source

                                        X_Data_Source = []
                                        Y_Data_Source = []
                                        Data_Source_Series = []
                                        data[0].forEach(function(arrayItem) {{
                                            if(root.custom_report.STARK_Chart_Type == 'Pie Chart') {{
                                                value  = arrayItem[Y_Data]
                                                text   = arrayItem[X_Data]
                                                Data_Source_Series.push({{ value: value, name: text }}) 
                                            }}
                                            else {{
                                                X_Data_Source.push(arrayItem[X_Data])
                                                Y_Data_Source.push(arrayItem[Y_Data])
                                            }}
                                        }})
                                        var subtext = root.conso_subtext()
                                        if(root.custom_report.STARK_Chart_Type == 'Pie Chart') {{
                                            root.pieChart(Data_Source_Series, subtext)
                                        }}
                                        else if(root.custom_report.STARK_Chart_Type == 'Bar Chart') {{
                                            root.barChart(X_Data_Source, Y_Data_Source, subtext)
                                        }}
                                        else if(root.custom_report.STARK_Chart_Type == 'Line Chart') {{
                                            root.lineChart(X_Data_Source, Y_Data_Source, subtext)
                                        }}
                                    }}
                                }}
                            }})
                            .catch(function(error) {{
                                console.log("Encountered an error! [" + error + "]")
                                alert("Request Failed: System error or you may not have enough privileges")
                                loading_modal.hide()
                            }});
                        }}
                    }}
                }},
                download_report(file_type = "csv") {{
                    let link = "https://" + (file_type == "csv" ? root.temp_csv_link : root.temp_pdf_link)
                    window.location.href = link
                }},

                loadImage: function(src) {{
                    return new Promise((resolve, reject) => {{
                    const img = new Image();
                    img.onload = () => resolve(img);
                    img.onerror = reject;
                    img.src = src;
                    }});
                }},

                activate_graph_download: function () {{
                    window.html2canvas = html2canvas
                    window.jsPDF = window.jspdf.jsPDF
                    filename = STARK.create_UUID()

                    const btnExportHTML = document.getElementById("exportByHTML")
                    btnExportHTML.addEventListener("click", async () => {{
                        console.log("exporting...");
                        try {{
                            const doc = new jsPDF({{
                                unit: "px",
                                orientation: "l",
                                hotfixes: ["px_scaling"]
                            }});

                            const canvas = await html2canvas(document.querySelector("#chart-container"))
                            const img = await root.loadImage(canvas.toDataURL())
                            doc.addImage(img.src, 'PNG', 50, 100, 1000, 500)
                            await doc.save(filename)
                        }} catch (e) {{
                            console.error("failed to export", e);
                        }}
                        console.log("exported");
                    }})
                }},

                toggle_all(checked) {{
                    temp_list = []
                    if(root.custom_report['STARK_group_by_1'] != "") {{
                        temp_list.push((root.custom_report['STARK_group_by_1']).replaceAll("_", " "))
                    }}
                    
                    root.checked_fields = checked ? root.temp_checked_fields.slice() : temp_list
                    root.all_selected = checked
                }},

                toggle_group_by(event) {{
                    field = event.target.id
                    root.checked_fields = [field.replaceAll("_", " ")]
                    root.all_selected = false
                }},
        """
    if with_upload or with_upload_on_many:
        source_code += f"""
                init_s3_access: function(){{

                    if(root.s3_access == "") {{
                        STARK.get_s3_credentials().then( function(data){{
                            access_key_id = data[0]['access_key_id']
                            secret_access_key = data[0]['secret_access_key']

                            root.s3_access = new AWS.S3({{
                                params: {{Bucket: STARK.bucket_name}},
                                region: STARK.region_name,
                                apiVersion: '2006-03-01',
                                accessKeyId: access_key_id,
                                secretAccessKey: secret_access_key,
                            }});

                            console.log("S3 authorized")
                        }}).catch(function(error) {{
                            console.log("Can't retrieve S3 creds! [" + error + "]")
                        }});
                    }}
                    
                }},"""
    if with_upload:
        source_code += f"""
                show_preview(filename) {{
                    if(typeof filename == 'string') {{
                        ext = filename.split('.').pop()
                        console.log(ext)
                        arr_previewable = ['jpg', 'jpeg', 'png', 'bmp', 'svg', 'gif']
                        if(arr_previewable.findIndex(elem => elem == ext) >= 0) {{
                            return true
                        }}
                        else {{
                            return false
                        }}
                    }}
                }},
                process_upload_file(file_upload_element) {{
                    var upload_processed = {{
                            'message': 'initial'
                        }}
                    var uuid = ""
                    var ext = ""
                    var file = root.STARK_upload_elements[file_upload_element].file;
                    is_valid = true;
                    error_message = ""

                    if(file) {{
                        uuid = STARK.create_UUID()
                        ext = file.name.split('.').pop()

                        valid_file = STARK.get_file_ext_whitelist(root.ext_whitelist[file_upload_element], root.ext_whitelist_table).includes(ext)
                        allowed_file_size = STARK.get_allowed_upload_size(root.allowed_size[file_upload_element], root.allowed_size_table)
                        if(!valid_file) {{
                            //check if file type is valid
                            error_message = `Invalid file type: ${{ext.toUpperCase()}}`
                        }}
                        else if(file.size > allowed_file_size) {{
                            // check if file size is allowed
                            error_message = `Uploaded file exceeded allowed file size of ${{allowed_file_size / 1024 / 1024}}MB`
                        }}

                        if(error_message == "") {{
                            upload_processed = {{
                                'message'   : error_message,
                                'file_body' : file,
                                'filename'  : file.name,
                                's3_key'    : uuid + '.' + ext
                            }}
                        }}
                        else {{
                            upload_processed = {{
                                'message'   : error_message
                            }}
                        }}
                    }}

                    return upload_processed
                }},
                s3upload: function(file_upload_element) {{

                    root.STARK_upload_elements[file_upload_element].progress_bar_val = 0
                    var upload_processed = root.process_upload_file(file_upload_element)
                    if(upload_processed['message'] == "") {{
                        root.{entity_varname}[file_upload_element] = upload_processed['filename']
                        var filePath = 'tmp/' + upload_processed['s3_key'];
                        root.{entity_varname}.STARK_uploaded_s3_keys[file_upload_element] = upload_processed['s3_key']
                        root.s3_access.upload({{
                            Key: filePath,
                            Body: upload_processed['file_body'],
                            ACL: 'public-read'
                            }}, function(err, data) {{
                                console.log(data)
                                root.STARK_upload_elements[file_upload_element]['tmp_location'] = data.Location
                                if(err) {{
                                    console.log(err)
                                }}
                            }}).on('httpUploadProgress', function (progress) {{
                            root.STARK_upload_elements[file_upload_element].progress_bar_val = parseInt((progress.loaded * 100) / progress.total);
                            root.validation_properties[file_upload_element].state = true
                            root.validation_properties[file_upload_element].feedback = "" 
                        }});
                    }}
                    else {{
                        //do not show alert when file upload is opened then closed
                        if(upload_processed['message'] != 'initial') {{
                            root.validation_properties[file_upload_element].state = false
                            root.validation_properties[file_upload_element].feedback = upload_processed['message'] 
                        }}
                    }}

                }},"""
    source_code += f"""
                onOptionClick({{ option, addTag }}, reference) {{
                    addTag(option.value)
                    this.search[reference] = ''
                    this.$refs[reference].show(true)
                }},
                refresh_list () {{
                    root.listview_table = ''
                    STARK.local_storage_delete_key('Listviews', '{entity_varname}');
                    root.list()
                }},
                refresh_child () {{
                    //NOTE: this is empty if this entity does not have a child, might need refactoring
                """
    if relationships.get('has_one', '') != '':
        for relation in relationships.get('has_one'):
                source_code += f""" 
                            STARK.local_storage_delete_key('Listviews', '{relation.get('entity')}');"""
    source_code += f"""
                }},
                """

    for col, col_type in cols.items():
        if isinstance(col_type, dict) and col_type["type"] == "relationship":
            has_one = col_type.get('has_one', '')
            has_many = col_type.get('has_many', '')
            has_many_ux = col_type.get('has_many_ux', '')
            if  has_one != '' or (has_many != '' and has_many_ux != 'repeater'):
                foreign_entity  = converter.convert_to_system_name(has_one if has_one != '' else has_many)
                foreign_field_display = col_type.get('display', foreign_entity)
                foreign_field_value   = converter.convert_to_system_name(col_type.get('value', foreign_entity))
                
                new_arr_field = []
                for display_value in foreign_field_display:
                    new_arr_field.append(str(converter.convert_to_system_name(display_value)))
                print(new_arr_field)   

                arr_fields = new_arr_field + [foreign_field_value] if foreign_field_value not in new_arr_field else new_arr_field

                separator = " + ' - ' + " 
                array_of_strings = ["arrayItem['" + item + "']" + separator for item in new_arr_field]
                foreign_display = ''
                for array_item in array_of_strings:
                    foreign_display += array_item
                foreign_display = foreign_display[:-len(separator)]

                source_code += f"""
                list_{foreign_entity}: function () {{
                    if (this.list_status.{foreign_entity} == 'empty') {{
                        loading_modal.show();
                        root.lists.{foreign_entity} = []

                        //FIXME: for now, generic list() is used. Can be optimized to use a list function that only retrieves specific columns
                        fields = {arr_fields}
                        
                        {foreign_entity}_app.get_fields(fields).then( function(data) {{
                            data.forEach(function(arrayItem) {{"""  
                source_code += f"""
                                text = {foreign_display}
                                value = arrayItem['{foreign_field_value}']"""
                
                source_code += f"""            
                                root.lists.{foreign_entity}.push({{ value: value, text: text }})"""

                source_code += f""" 
                }})
                            root.list_status.{foreign_entity} = 'populated'
                            loading_modal.hide();
                        }}).catch(function(error) {{
                            console.log("Encountered an error! [" + error + "]")
                            loading_modal.hide();
                        }});
                    }}
                }},
                """
                if has_many != '':
                    source_code += f"""
                split_string: function(str) {{
                    var arr = str.split(", ")
                    var return_str = ''
                    arr.forEach(element => {{
                        return_str += this.tag_display_text(element).concat(", ")
                    }});
                    return return_str
                }},

                tag_display_text: function (tag) {{
                    display_text = ""
                    if(typeof tag =='string')
                    {{
                        display_text = tag
                    }}
                    else
                    {{
                        var index = this.lists.{foreign_entity}.findIndex(opt => tag == opt.value)
                        display_text = this.lists.{foreign_entity}[index].text
                    }}
                    return display_text
                }},
                    """

    source_code += f"""
                //Charting ------------------------------------------------
                set_x_data_source: function (field) {{
                    X_Data_Source = (field).replace(/_/g," ")
                    root.custom_report.STARK_X_Data_Source = X_Data_Source
                }},

                set_y_data_source: function (field) {{
                    Y_Data_Source = (field).replace(/_/g," ")
                    data = {{ value: Y_Data_Source, text: Y_Data_Source }}
                    if(document.querySelector('#'+field).checked == true) {{
                        (root.Y_Data).push(data)
                    }}
                    else {{
                        (root.Y_Data).pop(data)
                    }}
                    root.lists.STARK_Data_Source = root.Y_Data
                }},

                uniqueArr: function(value, index, self) {{
                    return self.indexOf(value) === index;
                }},

                barChart: function (x_data, y_data, subtext) {{
                    var dom = document.getElementById('chart-container')
                    var myChart = echarts.init(dom, null, {{
                            renderer: 'canvas',
                            useDirtyRect: false
                    }});
                    
                    var app = {{}};
                    var option;
                    
                    option = {{
                        title: {{
                            text: '{entity} Report',
                            subtext: '',
                            right: 'center',
                            top: 20,
                            bottom: 20
                        }},
                        xAxis: {{
                            type: 'category',
                            data: []
                        }},
                        yAxis: {{
                            type: 'value'
                        }},
                        series: [
                            {{
                                data: [],
                                type: 'bar'
                            }}
                        ],
                        grid: {{
                            y: 120,
                            y2: 60,
                        }},
                        tooltip: {{

                        }}
                    }};
                    option.xAxis.data = x_data
                    option.series[0].data = y_data
                    option.title.subtext = subtext
                    
                    if (option && typeof option === 'object') {{
                        myChart.setOption(option);
                    }}

                    window.addEventListener('resize', myChart.resize);
                }},

                lineChart: function (x_data, y_data, subtext) {{
                    //START - Line Chart Components
                    var dom = document.getElementById('chart-container')
                    var myChart = echarts.init(dom, null, {{
                            renderer: 'canvas',
                            useDirtyRect: false
                    }});
                    
                    var app = {{}};
                    var option;
                    
                    option = {{
                        title: {{
                            text: '{entity} Report',
                            subtext: '',
                            right: 'center',
                            top: 20,
                            bottom: 20
                        }},
                        xAxis: {{
                            type: 'category',
                            data: []
                        }},
                        yAxis: {{
                            type: 'value'
                        }},
                        series: [
                            {{
                                data: [],
                                type: 'line'
                            }}
                        ],
                        grid: {{
                            y: 120,
                            y2: 60,
                        }},
                        tooltip: {{
                            
                        }}
                    }};
                    option.xAxis.data = x_data
                    option.series[0].data = y_data
                    option.title.subtext = subtext
                    
                    if (option && typeof option === 'object') {{
                        myChart.setOption(option);
                    }}

                    window.addEventListener('resize', myChart.resize);
                //END - Line Chart Components
                }},

                pieChart: function (y_data, subtext) {{
                    //START - Pie Chart Components
                    var dom = document.getElementById('chart-container');
                    var myChart = echarts.init(dom, null, {{
                            renderer: 'canvas',
                            useDirtyRect: false
                    }});

                    var app = {{}};
                    var option;
                    
                    option = {{
                        series: [
                            {{
                                name: 'Access From',
                                type: 'pie',
                                radius: '60%',
                                data: [],
                                emphasis: {{
                                    itemStyle: {{
                                    shadowBlur: 10,
                                    shadowOffsetX: 0,
                                    shadowColor: 'rgba(0, 0, 0, 0.5)'
                                    }}
                                }}
                            }}
                        ],
                        title: {{
                            text: '{entity} Report',
                            subtext: '',
                            right: 'center',
                            top: 20,
                            bottom: 20
                        }},
                        tooltip: {{
                            trigger: 'item'
                        }},
                        legend: {{
                            orient: 'vertical',
                            left: 'left',
                            
                        }},
                        grid: {{
                            y: 120,
                            y2: 60,
                        }}
                    }};
                    //Pass new value for data series
                    option.series[0].data = y_data
                    option.title.subtext = subtext
                    
                    if (option && typeof option === 'object') {{
                        myChart.setOption(option);
                    }}

                    window.addEventListener('resize', myChart.resize);
                    //END - Pie Chart Components
                }}, 

                showFields: function () {{
                    // console.log(root.custom_report.STARK_Report_Type)
                    if(root.custom_report.STARK_Chart_Type == 'Pie Chart') {{
                        root.showChartFields = true
                        root.fieldLabel = 'Pie Data Source'
                        // root.showXAxisFields = false
                    }}
                    else if (root.custom_report.STARK_Chart_Type == 'Bar Chart' || root.custom_report.STARK_Chart_Type == 'Line Chart') {{
                        // root.showXAxisFields = true
                        root.showChartFields = true
                        root.fieldLabel = 'X Axis Data Source'
                    }} 
                    
                }},

                showChartWizard: function () {{
                    if(root.custom_report.STARK_Report_Type == 'Graph') {{
                        root.showChartFields = true
                    }}
                    else {{
                        root.showChartFields = false
                    }}
                }},

                conso_subtext: function () {{
                    conso_subtext = ''
                    subtext_length = 0
                    subtext = ''
                    for (element in root.custom_report) {{

                        if(root.custom_report[element].operator != '' && root.custom_report[element].operator != undefined)
                        {{
                            field = element.replace("_", " ")
                            operator = (root.custom_report[element].operator).replace("_", " ")
                            val = root.custom_report[element].value
                            subtext = field + " " + operator + " " + val + " | "
                            conso_subtext = conso_subtext.concat(subtext)
                            
                            subtext_length += subtext.length
                            if(subtext_length >= 100) {{
                                conso_subtext += "\\n"
                                subtext_length = 0
                            }}
                        }}
                    }}
                    return conso_subtext
                }},"""
                
    source_code+= f"""  
            }},
            computed: {{"""
    for col, col_type in cols.items():
        col_varname = converter.convert_to_system_name(col)
        if isinstance(col_type, dict):
            col_values = col_type.get("values","")
            if (col_type["type"] == "relationship") or isinstance(col_values, list):
                has_many = col_type.get('has_many', '')
                has_many_ux = col_type.get('has_many_ux', '')
                if has_many_ux != 'repeater':
                    source_code += f"""
            {col_varname}_criteria() {{
                return this.search['{col_varname}'].trim().toLowerCase()
            }},
            {col_varname}() {{
                const {col_varname}_criteria = this.{col_varname}_criteria
                // Filter out already selected options
                const options = this.lists.{col_varname}.filter(opt => this.multi_select_values.{col_varname}.indexOf(opt.value) === -1)
                if ({col_varname}_criteria) {{
                // Show only options that match {col_varname}_criteria
                return options.filter(opt => (opt.text).toLowerCase().indexOf({col_varname}_criteria) > -1);
                }}
                // Show all options available
                return options
            }},
            {col_varname}_search_desc() {{
                if (this.{col_varname}_criteria && this.{col_varname}.length === 0) {{
                return 'There are no tags matching your search criteria'
                }}
                return ''
            }},"""
    source_code += f"""
            }}    
        }})
        
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

def set_data_type(col_type):

    #Default is 'S'. Defined here so we don't need duplicate Else statements below
    data_type = 'String'

    if isinstance(col_type, dict):
        #special/complex types
        if col_type["type"] in [ "int-spinner" ]:
            data_type = 'Number'

        if col_type["type"] in [ "decimal-spinner" ]:
            data_type = 'Float'
        
        if col_type["type"] in [ "tags", "multiple choice" ]:
            data_type = 'List'

        if col_type["type"] == 'file-upload':
            data_type = 'File'
    
    elif col_type in [ "int", "number" ]:
        data_type = 'Number'

    return data_type
