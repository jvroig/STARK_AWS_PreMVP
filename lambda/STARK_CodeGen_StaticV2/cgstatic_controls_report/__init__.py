#STARK Code Generator component.
#Produces HTML code for different controls in reporting, depending on column type

#Python Standard Library
import base64
import textwrap
import os
import importlib

#Private Modules
prepend_dir = ""
if 'libstark' in os.listdir():
    prepend_dir = "libstark.STARK_CodeGen_Static."

cg_coltype    = importlib.import_module(f"{prepend_dir}cgstatic_controls_coltype")  
import convert_friendly_to_system as converter

def create(data):

    col             = data['col']
    col_type        = data['col_type']
    col_varname     = data['col_varname']
    entity          = data['entity']
    entity_varname  = data['entity_varname']
    html_code       = ""
    default_control = False

    if isinstance(col_type, dict):
        col_values = col_type.get("values", "")
        if isinstance(col_values, list):
            col_type['type'] = "multi select combo"
            col_type['dropup'] = "true"
            html_code= cg_coltype.create({
                "col": col,
                "col_type": col_type,
                "col_varname": col_varname,
                "entity" : entity,
                "entity_varname": entity_varname,
                "is_many_control": False
            })
        else:
            default_control = True
    else:
        default_control = True

    if default_control:
        html_code = f"""<input type="text" class="form-control" id="{col_varname}_filter_value" placeholder="" v-model="custom_report.{col_varname}.value">"""

    
    return html_code