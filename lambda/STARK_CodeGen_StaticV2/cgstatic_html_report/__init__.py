#STARK Code Generator component.
#Produces the customized static content for a STARK system

#Python Standard Library
import base64
import textwrap
import os
import importlib

#Private modules
prepend_dir = ""
if 'libstark' in os.listdir():
    prepend_dir = "libstark.STARK_CodeGen_Static."

cg_header   = importlib.import_module(f"{prepend_dir}cgstatic_html_generic_header")
cg_footer   = importlib.import_module(f"{prepend_dir}cgstatic_html_generic_footer")
cg_bodyhead = importlib.import_module(f"{prepend_dir}cgstatic_html_generic_bodyhead")
cg_loadmod  = importlib.import_module(f"{prepend_dir}cgstatic_html_generic_loadingmodal")
cg_loadspin = importlib.import_module(f"{prepend_dir}cgstatic_html_generic_loadingspinner")
cg_colreport = importlib.import_module(f"{prepend_dir}cgstatic_controls_report")

import convert_friendly_to_system as converter

def create(data):

    project = data["Project Name"]
    entity  = data["Entity"]
    cols    = data["Columns"]
    pk      = data["PK"]
    rel_model      = data["Rel Model"]

    #Convert human-friendly names to variable-friendly names
    entity_varname = converter.convert_to_system_name(entity)
    pk_varname = converter.convert_to_system_name(pk)

    source_code  = cg_header.create(data, "Report")
    source_code += cg_bodyhead.create(data, "Report")

    source_code += f"""\
            <!-- <div class="container-unauthorized" v-if="!stark_permissions['{entity}|Report']">UNAUTHORIZED!</div>
            <div class="main-continer" v-if="stark_permissions['{entity}|Report']"> -->
                <div class="container" v-if="!showReport && !showGraph">
                    <div class="row">
                        <div class="col">
                            <div class="my-auto">
                                <form class="border p-3">
                                    <div>
                                        <table class="table table-bordered">
                                                    
                                                <div class="alert alert-danger alert-dismissible fade show" v-if="showError">
                                                    <strong>Error!</strong> Put operator/s on:
                                                    <template v-for="column in no_operator" id="no_operator">
                                                        <tr scope="col"> - {{{{ column }}}}</tr>
                                                    </template>
                                                </div>
                                        </table>
                                    </div>
                                    <table class="table table-dark table-striped report">
                                        <tr>
                                            <th>
                                                <input type="checkbox" class="checkbox-med" name="check_checkbox" v-model="all_selected" onchange="root.toggle_all(!root.all_selected)">
                                            </th>
                                            <th style="padding: 10px; min-width: 250px"> Field Name </th>
                                            <th style="padding: 10px"> Operator </th>
                                            <th style="padding: 10px"> Filter Value </th>    
                                            <th style="padding: 10px"> Sum </th>
                                            <th style="padding: 10px"> Count </th>
                                            <th style="padding: 10px"> Group By</th>
                                        </tr>
                                        <tr>
                                            <td>
                                                <input type="checkbox" class="checkbox-med" name="check_checkbox" value="{pk}" id="{pk_varname}" v-model="checked_fields">
                                            </td>
                                            <td>
                                                    <label for="{pk_varname}">{pk}</label>
                                            </td>
                                            <td>
                                                <b-form-select id="{pk_varname}_operator" :options="lists.Report_Operator" v-model="custom_report.{pk_varname}.operator">
                                                    <template v-slot:first>
                                                        <b-form-select-option :value="null" disabled>-- Please select an option --</b-form-select-option>
                                                    </template>
                                                </b-form-select>
                                            </td>
                                            <td>
                                                <input type="text" class="form-control" id="{pk_varname}_filter_value" placeholder="" v-model="custom_report.{pk_varname}.value">
                                            </td>
                                            <td>
                                                <input type="checkbox" class="checkbox-med" name="check_checkbox" value="{pk_varname}" id="Sum_of_Pr{pk_varname}" v-model="custom_report.STARK_sum_fields" :disabled="metadata.{pk_varname}.data_type != 'Number' && metadata.{pk_varname}.data_type != 'Float'" onchange="root.set_y_data_source('Sum_of_{pk_varname}')">
                                            </td>
                                            <td>
                                                <input type="checkbox" class="checkbox-med" name="check_checkbox" value="{pk_varname}" id="Count_of_{pk_varname}" v-model="custom_report.STARK_count_fields" onchange="root.set_y_data_source('Count_of_{pk_varname}')">
                                            </td>
                                            <td>
                                                <input type="radio" onclick="root.toggle_group_by(event)" class="checkbox-med"  name="check_checkbox" value="{pk_varname}" id="{pk_varname}" v-model="custom_report.STARK_group_by_1" onchange="root.set_x_data_source('{pk_varname}')">
                                            </td>
                                        </tr>"""
    

    for col, col_type in cols.items():
        print('col')
        print(col)
        print('col_type')
        print(col_type)
        col_varname = converter.convert_to_system_name(col)
        html_control_code = {
            "col": col,
            "col_type": col_type,
            "col_varname": col_varname,
            "entity" : entity,
            "entity_varname": entity_varname,
            "is_many_control": False
        }
        html_control_code = cg_colreport.create(html_control_code)
        if isinstance(col_type, dict) and col_type["type"] == "relationship":
            has_many_ux = col_type.get('has_many_ux', None)
            if has_many_ux == None:
                source_code += f"""
                                        <tr>
                                            <td>
                                                <input type="checkbox" class="checkbox-med" name="check_checkbox" value="{col}" id="{col_varname}" v-model="checked_fields">
                                            </td>
                                            <td>
                                                    <label for="{col_varname}">{col}</label>
                                            </td>
                                            <td>
                                                <b-form-select id="{col_varname}_operator" :options="lists.Report_Operator" v-model="custom_report.{col_varname}.operator">
                                                    <template v-slot:first>
                                                        <b-form-select-option :value="null" disabled>-- Please select an option --</b-form-select-option>
                                                    </template>
                                                </b-form-select>
                                            </td>
                                            <td>
                                                <div class="report">
                                                    {html_control_code}
                                                </div>
                                            </td>
                                            <td>
                                                <input type="checkbox" class="checkbox-med" name="check_checkbox" value="{col_varname}" id="Sum_of_{col_varname}" v-model="custom_report.STARK_sum_fields" :disabled="metadata.{col_varname}.data_type != 'Number' && metadata.{col_varname}.data_type != 'Float'" onchange="root.set_y_data_source('Sum_of_{col_varname}')">
                                            </td>
                                            <td>
                                                <input type="checkbox" class="checkbox-med" name="check_checkbox" value="{col_varname}" id="Count_of_{col_varname}" v-model="custom_report.STARK_count_fields" onchange="root.set_y_data_source('Count_of_{col_varname}')">
                                            </td>
                                            <td>
                                                <input type="radio" onclick="root.toggle_group_by(event)" class="checkbox-med" name="check_checkbox" value="{col_varname}" id="{col_varname}" v-model="custom_report.STARK_group_by_1" onchange="root.set_x_data_source('{col_varname}')">
                                            </td>
                                        </tr>
                                    """                      
        else:
            source_code += f"""
                                        <tr>
                                            <td>
                                                <input type="checkbox" class="checkbox-med" name="check_checkbox" value="{col}" id="{col_varname}" v-model="checked_fields">
                                            </td>
                                            <td>
                                                    <label for="{col_varname}">{col}</label>
                                            </td>
                                            <td>
                                                <b-form-select id="{col_varname}_operator" :options="lists.Report_Operator" v-model="custom_report.{col_varname}.operator">
                                                    <template v-slot:first>
                                                        <b-form-select-option :value="null" disabled>-- Please select an option --</b-form-select-option>
                                                    </template>
                                                </b-form-select>
                                            </td>
                                            <td>
                                                <div class="report">
                                                    {html_control_code}
                                                </div>
                                            </td>
                                            <td>
                                                <input type="checkbox" class="checkbox-med" name="check_checkbox" value="{col_varname}" id="Sum_of_{col_varname}" v-model="custom_report.STARK_sum_fields" :disabled="metadata.{col_varname}.data_type != 'Number' && metadata.{col_varname}.data_type != 'Float'" onchange="root.set_y_data_source('Sum_of_{col_varname}')">
                                            </td>
                                            <td>
                                                <input type="checkbox" class="checkbox-med" name="check_checkbox" value="{col_varname}" id="Count_of_{col_varname}" v-model="custom_report.STARK_count_fields" onchange="root.set_y_data_source('Count_of_{col_varname}')">
                                            </td>
                                            <td>
                                                <input type="radio" onclick="root.toggle_group_by(event)" class="checkbox-med" name="check_checkbox" value="{col_varname}" id="{col_varname}" v-model="custom_report.STARK_group_by_1" onchange="root.set_x_data_source('{col_varname}')">
                                            </td>
                                        </tr>
                                    """
                                    
    for rel_ent in rel_model:
        rel_cols = rel_model[rel_ent]["data"]
        rel_pk = rel_model[rel_ent]["pk"]
        var_pk = rel_ent.replace(' ', '_') + '_' + rel_pk.replace(' ', '_')
        pk_label = '[' + rel_ent + '] ' + rel_pk
        source_code += f"""
                                        <tr>
                                            <td>
                                                <input type="checkbox" class="checkbox-med" name="check_checkbox" value="{var_pk.replace('_', ' ')}" id="{var_pk}" v-model="checked_fields">
                                            </td>
                                            <td>
                                                    <label for="{var_pk}">{pk_label}</label>
                                            </td>
                                            <td>
                                                <b-form-select id="{var_pk}_operator" :options="lists.Report_Operator" v-model="custom_report.{var_pk}.operator">
                                                    <template v-slot:first>
                                                        <b-form-select-option :value="null" disabled>-- Please select an option --</b-form-select-option>
                                                    </template>
                                                </b-form-select>
                                            </td>
                                            <td>
                                                <input type="text" class="form-control" id="{var_pk}_filter_value" placeholder="" v-model="custom_report.{var_pk}.value">
                                            </td>
                                            <td>
                                                <input type="checkbox" class="checkbox-med" name="check_checkbox" value="{var_pk}" id="Sum_of_{var_pk}" v-model="custom_report.STARK_sum_fields" :disabled="metadata.{var_pk}.data_type != 'Number' && metadata.{var_pk}.data_type != 'Float'" onchange="root.set_y_data_source('Sum_of_{var_pk}')">
                                            </td>
                                            <td>
                                                <input type="checkbox" class="checkbox-med" name="check_checkbox" value="{var_pk}" id="Count_of_{var_pk}" v-model="custom_report.STARK_count_fields" onchange="root.set_y_data_source('Count_of_{var_pk}')">
                                            </td>
                                            <td>
                                                <input type="radio" onclick="root.toggle_group_by(event)" class="checkbox-med" name="check_checkbox" value="{var_pk}" id="{var_pk}" v-model="custom_report.STARK_group_by_1" onchange="root.set_x_data_source('{var_pk}')">
                                            </td>
                                        </tr>
                            """
        for rel_col, rel_col_type in rel_cols.items():
            var_data = rel_ent.replace(' ', '_') + '_' + rel_col.replace(' ', '_')
            data_label = '[' + rel_ent + '] ' + rel_col
            source_code += f"""
                                        <tr>
                                            <td>
                                                <input type="checkbox" class="checkbox-med" name="check_checkbox" value="{var_data.replace('_', ' ')}" id="{var_data}" v-model="checked_fields">
                                            </td>
                                            <td>
                                                    <label for="{var_data}">{data_label}</label>
                                            </td>
                                            <td>
                                                <b-form-select id="{var_data}_operator" :options="lists.Report_Operator" v-model="custom_report.{var_data}.operator">
                                                    <template v-slot:first>
                                                        <b-form-select-option :value="null" disabled>-- Please select an option --</b-form-select-option>
                                                    </template>
                                                </b-form-select>
                                            </td>
                                            <td>
                                                <input type="text" class="form-control" id="{var_data}_filter_value" placeholder="" v-model="custom_report.{var_data}.value">
                                            </td>
                                            <td>
                                                <input type="checkbox" class="checkbox-med" name="check_checkbox" value="{var_data}" id="Sum_of_{var_data}" v-model="custom_report.STARK_sum_fields" :disabled="metadata.{var_data}.data_type != 'Number' && metadata.{var_data}.data_type != 'Float'" onchange="root.set_y_data_source('Sum_of_{var_data}')">
                                            </td>
                                            <td>
                                                <input type="checkbox" class="checkbox-med" name="check_checkbox" value="{var_data}" id="Count_of_{var_data}" v-model="custom_report.STARK_count_fields" onchange="root.set_y_data_source('Count_of_{var_data}')">
                                            </td>
                                            <td>
                                                <input type="radio" onclick="root.toggle_group_by(event)" class="checkbox-med" name="check_checkbox" value="{var_data}" id="{var_data}" v-model="custom_report.STARK_group_by_1" onchange="root.set_x_data_source('{var_data}')">
                                            </td>
                                        </tr>
                            """

                                    

    source_code += f"""
                                    </table>    
                                    <table class="table table-dark table-striped report">
                                        <tr>
                                            <hr>
                                            <td></td>
                                            <td>Report Type</td>
                                            <td>
                                                <b-form-group class="form-group" label="" label-for="Report_Type" :state="validation_properties.STARK_Report_Type.state" :invalid-feedback="validation_properties.STARK_Report_Type.feedback" >
                                                    <b-form-select id="Report_Type" v-model="custom_report.STARK_Report_Type" :options="lists.STARK_Report_Type" :state="validation_properties.STARK_Report_Type.state" @change="root.showChartWizard()">
                                                    <template v-slot:first>
                                                        <b-form-select-option :value="null" disabled>-- Please select an option --</b-form-select-option>
                                                    </template>
                                                </b-form-select>
                                                </b-form-group>
                                            </td>
                                            <td></td>
                                        </tr>
                                    </table>
                                    <table v-if="showChartFields" class="table table-dark table-striped report">
                                        <tr>
                                            <hr v-if="showChartFields"> <h5 v-if="showChartFields">Chart Wizard</h5> <hr v-if="showChartFields">
                                        </tr>
                                        <tr>
                                            <td></td>
                                            <td>Chart Type</td>
                                            <td>
                                            <b-form-group class="form-group" label="" label-for="Chart_Type" :state="validation_properties.STARK_Chart_Type.state" :invalid-feedback="validation_properties.STARK_Chart_Type.feedback" >
                                                <b-form-select id="Chart_Type" v-model="custom_report.STARK_Chart_Type" :options="lists.STARK_Chart_Type" :state="validation_properties.STARK_Chart_Type.state" @change="root.showFields()">
                                                <template v-slot:first>
                                                    <b-form-select-option :value="null" disabled>-- Please select an option --</b-form-select-option>
                                                </template>
                                            </b-form-select>
                                            </b-form-group>
                                            </td>
                                            <td></td>
                                        </tr>
                                        <tr>
                                            <td></td>
                                            <td>X Data Source</td>
                                            <td>
                                            <b-form-group class="form-group" label-for="" :state="validation_properties.STARK_X_Data_Source.state" :invalid-feedback="validation_properties.STARK_X_Data_Source.feedback">
                                                <b-form-input type="text" class="form-control" id="STARK_X_Data_Source" placeholder="" v-model="custom_report.STARK_X_Data_Source" :state="validation_properties.STARK_X_Data_Source.state" disabled></b-form-input>
                                            </b-form-group>
                                            </td>
                                            <td></td>
                                        </tr>
                                        <tr>
                                            <td></td>
                                            <td>Y Data Source</td>
                                            <td>
                                                <b-form-group class="form-group" label-for="Data_Source" :state="validation_properties.STARK_Y_Data_Source.state" :invalid-feedback="validation_properties.STARK_Y_Data_Source.feedback">
                                                    <b-form-select id="Data_Source" v-model="custom_report.STARK_Y_Data_Source" :options="lists.STARK_Data_Source" :state="validation_properties.STARK_Y_Data_Source.state">
                                                    <template v-slot:first>
                                                        <b-form-select-option :value="null" disabled>-- Please select an option --</b-form-select-option>
                                                    </template>
                                                </b-form-select>
                                                </b-form-group>
                                            </td>
                                            <td></td>
                                        </tr>
                                    </table>
                                    <button type="button" class="btn btn-secondary" onClick="window.location.href='{entity_varname}.html'">Back</button>
                                    <button type="button" class="btn btn-primary float-right" onClick="root.generate()">Generate</button>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>"""

    source_code += f"""
                <div v-if="!showReport && showGraph">
                    <div class="row">
                        <div class="col-6 text-left d-inline-block">
                            <button id="prev" type="button" class="btn btn-secondary mb-2" onClick="root.showGraph = false, root.showError = false"> Back </button>
                            <button type="button" id="exportByHTML" class="btn btn-danger mb-2" :disabled="listview_table.length < 1"> Export as PDF</button>
                            <button id="refresh" type="button" class="btn btn-primary mb-2" onClick="root.generate()" :disabled="listview_table.length < 1"> Refresh </button>
                        </div>
                        <div class="col-6"></div>
                        <div class="col-6 text-left d-inline-block">
                            <table class="table">
                                <template v-if="listview_table.length < 1">
                                    No records found
                                </template>
                            </table>
                        </div>
                    </div>
                    <div id="chart-container"></div>
                </div>
                <div v-if="showReport && !showGraph">
                    <div class="row">
                        <div class="col-6 text-left d-inline-block">
                            <button id="prev" type="button" class="btn btn-secondary mb-2" onClick="root.showReport = false, root.showError = false"> Back </button>
                            <button type="button" class="btn btn-success mb-2" onClick="root.download_report('csv')" :disabled="listview_table.length < 1"> Export as CSV</button>
                            <button type="button" class="btn btn-danger mb-2" onClick="root.download_report('pdf')" :disabled="listview_table.length < 1"> Export as PDF</button>
                            <button id="refresh" type="button" class="btn btn-primary mb-2" onClick="root.generate()" :disabled="listview_table.length < 1"> Refresh </button>
                        </div>
                        <div class="col-6">
                        </div>
                    </div>

                    <div class="row">
                        <div class="col overflow-auto">
                            <table class="table  table-hover table-striped table-dark">
                                <thead class="thead-dark">
                                    <tr>
                                        <th v-if="showOperations" scope="col" width = "20px"> Operations </th>
                                        <template v-for="column in STARK_report_fields" id="STARK_report_fields">
                                            <th scope="col">{{{{column}}}}</th>
                                        </template>"""
    source_code += f"""         
                                    </tr>
                                </thead>
                                <tbody>
                                    <template v-for="{entity_varname} in listview_table" id="listview-table">
                                        <tr>
                                            <td v-if="showOperations">
                                                <a :href="'{entity_varname}_edit.html?{pk_varname}=' + {entity_varname}['{pk}']" target="_blank" v-if="auth_list.Edit.allowed"><img src="images/pencil-square.svg" class="bg-info"></a>
                                                <a :href="'{entity_varname}_delete.html?{pk_varname}=' + {entity_varname}['{pk}']" target="_blank" v-if="auth_list.Delete.allowed"><img src="images/x-square.svg" class="bg-danger"></a>
                                            </td>
                                            <template v-for="column in STARK_report_fields">
                                                <td>{{{{ {entity_varname}[column] }}}}</td>
                                            </template>"""
    source_code += f"""             
                                    </tr>
                                </template>
                                <template v-if="listview_table.length < 1">
                                    No records found
                                </template>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    """
    source_code += cg_loadmod.create()
    source_code += cg_footer.create()

    return textwrap.dedent(source_code)
