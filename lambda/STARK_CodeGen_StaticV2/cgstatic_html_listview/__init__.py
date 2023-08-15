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

import convert_friendly_to_system as converter

def create(data):

    project = data["Project Name"]
    entity  = data["Entity"]
    cols    = data["Columns"]
    pk      = data["PK"]
    rel_model   = data["Rel Model"]

    #Convert human-friendly names to variable-friendly names
    entity_varname = converter.convert_to_system_name(entity)
    pk_varname = converter.convert_to_system_name(pk)

    source_code  = cg_header.create(data, "Listview")
    source_code += cg_bodyhead.create(data, "_Listview")

    source_code += f"""\
            <div class="row">
                <div class="col-6">
                    <button type="button" class="btn btn-primary mb-2" onClick="window.location.href='{entity_varname}_add.html'" v-if="auth_list.Add.allowed"> <b>+</b> Add </button>
                    <button type="button" class="btn btn-info mb-2" onClick="window.location.href='{entity_varname}_report.html'" v-if="auth_list.Report.allowed"> Reports </button>
                    <button type="button" class="btn btn-secondary mb-2" onClick="root.refresh_list()"> Refresh </button>
                </div>
                <div class="col-6 text-right d-inline-block">        
                    <button id="prev" type="button" class="btn btn-secondary" :disabled="prev_disabled" onClick="root.list(root.prev_token, 'prev')"> < </button>
                    <button id="next" type="button" class="btn btn-secondary" :disabled="next_disabled" onClick="root.list(root.next_token, 'next')"> > </button>
                </div>
            </div>

            <div class="row">
                <div class="col overflow-auto">
                    <table class="table  table-hover table-striped table-dark">
                        <thead class="thead-dark">
                            <tr>
                                <th scope="col">Edit</th>
                                <th scope="col">{pk}</th>"""

    for col, col_type in cols.items():
        if isinstance(col_type, dict) and col_type["type"] == "relationship":
            has_many_ux = col_type.get('has_many_ux', None)
            if has_many_ux == None:
                source_code += f"""
                                <th scope="col">{col}</th>"""
        else:
            source_code += f"""
                                <th scope="col">{col}</th>"""

    source_code += f"""
                                <th scope="col">Del</th>
                            </tr>
                        </thead>
                        <tbody>
                            <template v-for="{entity_varname} in listview_table" id="listview-table">
                                <tr>
                                    <td>
                                        <a :href="'{entity_varname}_edit.html?{pk_varname}=' + {entity_varname}.{pk_varname}"><img src="images/pencil-square.svg" class="bg-info" v-if="auth_list.Edit.allowed"></a>
                                    </td>
                                    <th scope="row">
                                        <template id="detail-view" v-if="auth_list.View.allowed">
                                            <a :href="'{entity_varname}_view.html?{pk_varname}=' + {entity_varname}.{pk_varname}">{{{{ {entity_varname}.{pk_varname} }}}}</a>
                                        </template>
                                        <template id="detail-view" v-if="!auth_list.View.allowed">
                                            {{{{ {entity_varname}.{pk_varname} }}}}
                                        </template>
                                    </th>"""

    for col, col_type in cols.items():
        col_varname = converter.convert_to_system_name(col)
        if isinstance(col_type, dict) and col_type["type"] == "relationship":
            has_many_ux = col_type.get('has_many_ux', None)
            
            if has_many_ux == None:
                source_code += f"""
                                    <td>{{{{ {entity_varname}.{col_varname} }}}}</td>"""
        else:
            source_code += f"""
                                    <td>{{{{ {entity_varname}.{col_varname} }}}}</td>"""

    source_code += f"""
                                    <td><a :href="'{entity_varname}_delete.html?{pk_varname}=' + {entity_varname}.{pk_varname}"><img src="images/x-square.svg" class="bg-danger" v-if="auth_list.Delete.allowed"></a></td>
                                </tr>
                            </template>
                    </tbody>
                    </table>
                </div>
            </div>
        </div>
"""
    source_code += cg_loadspin.create()
    source_code += cg_loadmod.create()
    source_code += cg_footer.create()

    return textwrap.dedent(source_code)
